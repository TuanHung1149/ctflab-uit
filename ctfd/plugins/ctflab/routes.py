"""Flask blueprint with API routes for CTFLab instance management.

HTB-style model:
- Each user gets ONE .ovpn file (downloaded from /api/ctflab/vpn)
- When user spawns a box, CCD is updated to push route to their box
- User keeps same VPN connection, route updates on reconnect
"""

import io
import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta

from CTFd.models import db
from CTFd.utils.decorators import authed_only, admins_only
from CTFd.utils.user import get_current_user
from flask import Blueprint, jsonify, request, send_file, render_template
from sqlalchemy import text

from .docker_utils import DockerManager
from .flag_utils import generate_flags
from .host_ops import ensure_user_vpn, rebuild_network_isolation, update_vpn_route
from .models import CTFLabChallengeModel, LabInstance, ActivityLog

ctflab_bp = Blueprint(
    "ctflab",
    __name__,
    url_prefix="/api/ctflab",
    template_folder="templates",
)

docker_mgr = DockerManager()
logger = logging.getLogger(__name__)

MAX_SLOT = 50
SERVER_IP = os.environ.get("OVPN_SERVER_IP", "152.42.233.178")
SLOT_LOCK_NAME = "ctflab_slot_allocate"


def _log_action(action, detail=None, user_id=None):
    """Log user action for admin monitoring."""
    try:
        ip = request.remote_addr if request else None
        if not user_id:
            try:
                u = get_current_user()
                user_id = u.id if u else None
            except Exception:
                pass
        log = ActivityLog(user_id=user_id, action=action, detail=detail, ip_address=ip)
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass


def _find_free_slot():
    used = {
        i.slot
        for i in LabInstance.query.filter(
            LabInstance.status.in_(["starting", "running", "stopping"])
        ).all()
    }
    for s in range(1, MAX_SLOT + 1):
        if s not in used:
            return s
    return None


@contextmanager
def _slot_lock(timeout=10):
    """Serialize slot allocation across concurrent requests."""
    dialect = getattr(db.session.bind, "dialect", None)
    dialect_name = getattr(dialect, "name", "")

    if dialect_name not in {"mysql", "mariadb"}:
        yield
        return

    acquired = db.session.execute(
        text("SELECT GET_LOCK(:name, :timeout)"),
        {"name": SLOT_LOCK_NAME, "timeout": timeout},
    ).scalar()
    if acquired != 1:
        raise RuntimeError("Failed to acquire slot allocation lock")

    try:
        yield
    finally:
        try:
            db.session.execute(
                text("SELECT RELEASE_LOCK(:name)"),
                {"name": SLOT_LOCK_NAME},
            )
        except Exception:
            logger.exception("Failed to release slot allocation lock")


def _collect_prefixes_for_image(docker_image):
    challenges = CTFLabChallengeModel.query.filter_by(
        docker_image=docker_image
    ).all()
    prefixes = []
    for c in challenges:
        if c.flag_prefix:
            # If prefix is generic like "NBL", expand to NBL01-NBL07
            if len(c.flag_prefix) <= 3:
                prefixes.extend([f"{c.flag_prefix}{str(i).zfill(2)}" for i in range(1, 8)])
            else:
                prefixes.append(c.flag_prefix)
    if not prefixes:
        prefixes = [f"NBL{str(i).zfill(2)}" for i in range(1, 8)]
    return prefixes


# ── VPN download (per-user, like HTB) ──────────────────────────────

@ctflab_bp.route("/vpn", methods=["GET"])
@authed_only
def download_user_vpn():
    """Download the user's .ovpn file (one per user, reusable for all boxes)."""
    user = get_current_user()
    try:
        ovpn_path = ensure_user_vpn(user.name, SERVER_IP)
    except Exception as e:
        logger.exception("Failed to provision VPN for %s", user.name)
        return jsonify({"error": f"VPN config not available: {str(e)}"}), 500

    if not ovpn_path or not os.path.isfile(ovpn_path):
        return jsonify({"error": "VPN config not available. Contact admin."}), 500

    content = open(ovpn_path).read()
    _log_action("vpn_download")
    buf = io.BytesIO(content.encode())
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"{user.name}.ovpn",
        mimetype="application/x-openvpn-profile",
    )


# ── Instance management ────────────────────────────────────────────

@ctflab_bp.route("/instances", methods=["POST"])
@authed_only
def create_instance():
    """Spawn a box for the current user (Start Machine)."""
    user = get_current_user()
    data = request.get_json() or {}
    challenge_id = data.get("challenge_id")

    challenge = CTFLabChallengeModel.query.filter_by(id=challenge_id).first()
    if not challenge:
        return jsonify({"error": "Challenge not found"}), 404

    docker_image = challenge.docker_image

    env_data = json.loads(challenge.box_env_json) if challenge.box_env_json else {}
    prefixes = _collect_prefixes_for_image(docker_image)
    flags = generate_flags(prefixes)
    timeout_seconds = challenge.instance_timeout or 14400

    with _slot_lock():
        existing = (
            LabInstance.query.filter_by(user_id=user.id, docker_image=docker_image)
            .filter(LabInstance.status.in_(["starting", "running"]))
            .first()
        )
        if existing:
            return jsonify({
                "id": existing.id,
                "status": existing.status,
                "container_ip": existing.container_ip,
                "expires_at": existing.expires_at.isoformat() if existing.expires_at else None,
            })

        any_active = (
            LabInstance.query.filter_by(user_id=user.id)
            .filter(LabInstance.status.in_(["starting", "running"]))
            .first()
        )
        if any_active:
            return jsonify({
                "error": "You already have a running instance. Stop it first."
            }), 409

        slot = _find_free_slot()
        if slot is None:
            return jsonify({"error": "No slots available. Try again later."}), 503

        instance = LabInstance(
            user_id=user.id,
            docker_image=docker_image,
            slot=slot,
            status="starting",
            flags_json=json.dumps(flags),
            expires_at=datetime.utcnow() + timedelta(seconds=timeout_seconds),
        )
        db.session.add(instance)
        db.session.commit()

    container_id = None
    network_id = None

    try:
        container_id, network_id, container_ip = docker_mgr.create_instance(
            image=docker_image, slot=slot, flags=flags, env_overrides=env_data,
        )
        instance.container_id = container_id
        instance.network_id = network_id
        instance.container_ip = container_ip
        instance.status = "running"

        ensure_user_vpn(user.name, SERVER_IP)
        update_vpn_route(user.name, slot)
        rebuild_network_isolation()

        _log_action("start_machine", f"IP={container_ip}, slot={slot}, image={docker_image}")
        db.session.commit()
    except Exception as e:
        logger.exception("Failed to create instance for user %s", user.name)
        try:
            update_vpn_route(user.name, None)
            rebuild_network_isolation()
        except Exception:
            logger.exception("Failed to roll back VPN/firewall state for %s", user.name)
        if container_id and network_id:
            try:
                docker_mgr.destroy_instance(container_id, network_id)
            except Exception:
                logger.exception("Failed to clean up partial instance for slot %s", instance.slot)
        instance.status = "error"
        db.session.commit()
        return jsonify({"error": f"Failed to start: {str(e)}"}), 500

    return jsonify({
        "id": instance.id,
        "status": instance.status,
        "container_ip": instance.container_ip,
        "expires_at": instance.expires_at.isoformat(),
    })


@ctflab_bp.route("/instances", methods=["GET"])
@authed_only
def get_instance():
    """Get current user's active instance."""
    user = get_current_user()
    docker_image = request.args.get("docker_image", "")

    query = LabInstance.query.filter_by(user_id=user.id).filter(
        LabInstance.status.in_(["starting", "running"])
    )
    if docker_image:
        query = query.filter_by(docker_image=docker_image)

    instance = query.first()
    if not instance:
        return jsonify({"instance": None})

    return jsonify({
        "instance": {
            "id": instance.id,
            "docker_image": instance.docker_image,
            "status": instance.status,
            "container_ip": instance.container_ip,
            "expires_at": instance.expires_at.isoformat() if instance.expires_at else None,
        }
    })


@ctflab_bp.route("/instances/<int:instance_id>", methods=["DELETE"])
@authed_only
def destroy_instance(instance_id):
    """Stop Machine - destroy instance and remove VPN route."""
    user = get_current_user()
    instance = LabInstance.query.filter_by(id=instance_id, user_id=user.id).first()
    if not instance:
        return jsonify({"error": "Instance not found"}), 404

    instance.status = "stopping"
    db.session.commit()

    try:
        docker_mgr.destroy_instance(instance.container_id, instance.network_id)
    except Exception:
        pass

    try:
        update_vpn_route(user.name, None)
        rebuild_network_isolation()
    except Exception:
        logger.exception("Failed to refresh VPN/firewall state while stopping slot %s", instance.slot)

    instance.status = "stopped"
    _log_action("stop_machine", f"slot={instance.slot}")
    db.session.commit()
    return jsonify({"status": "stopped"})


@ctflab_bp.route("/instances/<int:instance_id>/reset", methods=["POST"])
@authed_only
def reset_instance(instance_id):
    """Reset Machine to initial state."""
    user = get_current_user()
    instance = LabInstance.query.filter_by(
        id=instance_id, user_id=user.id, status="running"
    ).first()
    if not instance:
        return jsonify({"error": "No running instance found"}), 404

    try:
        docker_mgr.reset_instance(instance.container_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    _log_action("reset_machine", f"slot={instance.slot}")
    return jsonify({"status": "reset"})


# Keep old per-instance VPN download for backward compatibility
@ctflab_bp.route("/instances/<int:instance_id>/vpn", methods=["GET"])
@authed_only
def download_instance_vpn(instance_id):
    """Download VPN config (redirects to per-user VPN)."""
    return download_user_vpn()


# ── Admin routes ───────────────────────────────────────────────────

@ctflab_bp.route("/admin/instances", methods=["GET"])
@admins_only
def admin_instances():
    """Admin: list all active instances."""

    instances = LabInstance.query.filter(
        LabInstance.status.in_(["starting", "running"])
    ).all()

    return jsonify({
        "instances": [{
            "id": i.id,
            "user_id": i.user_id,
            "username": i.user.name if i.user else "?",
            "docker_image": i.docker_image,
            "slot": i.slot,
            "container_ip": i.container_ip,
            "status": i.status,
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "expires_at": i.expires_at.isoformat() if i.expires_at else None,
        } for i in instances]
    })


@ctflab_bp.route("/admin/instances/history", methods=["GET"])
@admins_only
def admin_instance_history():
    """Admin: all instances (including stopped)."""

    instances = LabInstance.query.order_by(LabInstance.id.desc()).limit(100).all()

    return jsonify({
        "instances": [{
            "id": i.id,
            "user_id": i.user_id,
            "username": i.user.name if i.user else "?",
            "docker_image": i.docker_image,
            "slot": i.slot,
            "container_ip": i.container_ip,
            "status": i.status,
            "created_at": i.created_at.isoformat() if i.created_at else None,
            "expires_at": i.expires_at.isoformat() if i.expires_at else None,
        } for i in instances]
    })


@ctflab_bp.route("/admin/suspicious", methods=["GET"])
@admins_only
def admin_suspicious():
    """Admin: list suspected flag sharing."""

    from .models import SuspiciousSubmission
    subs = SuspiciousSubmission.query.order_by(
        SuspiciousSubmission.id.desc()
    ).limit(100).all()

    results = []
    for s in subs:
        # Get matched user name
        matched_user = None
        if s.matched_user_id:
            from CTFd.models import Users
            mu = Users.query.get(s.matched_user_id)
            matched_user = mu.name if mu else f"user#{s.matched_user_id}"

        results.append({
            "id": s.id,
            "user_id": s.user_id,
            "username": s.user.name if s.user else "?",
            "challenge_id": s.challenge_id,
            "submitted_flag": s.submitted_flag,
            "matched_user": matched_user,
            "matched_instance_id": s.matched_instance_id,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    return jsonify({"suspicious": results})


@ctflab_bp.route("/admin/stats", methods=["GET"])
@admins_only
def admin_stats():
    """Admin: platform statistics."""

    from CTFd.models import Users, Solves, Fails
    from .models import SuspiciousSubmission

    active_instances = LabInstance.query.filter(
        LabInstance.status.in_(["starting", "running"])
    ).count()
    total_instances = LabInstance.query.count()
    total_users = Users.query.count()
    total_solves = Solves.query.count()
    total_fails = Fails.query.count()
    total_suspicious = SuspiciousSubmission.query.count()

    return jsonify({
        "active_instances": active_instances,
        "total_instances": total_instances,
        "total_users": total_users,
        "total_solves": total_solves,
        "total_fails": total_fails,
        "total_suspicious": total_suspicious,
    })


@ctflab_bp.route("/admin/logs", methods=["GET"])
@admins_only
def admin_logs():
    """Admin: view activity logs. Optional ?action=start_machine&limit=50"""

    action_filter = request.args.get("action", "")
    limit = min(int(request.args.get("limit", 200)), 500)

    query = ActivityLog.query.order_by(ActivityLog.id.desc())
    if action_filter:
        query = query.filter_by(action=action_filter)
    logs = query.limit(limit).all()

    return jsonify({
        "logs": [{
            "id": l.id,
            "user_id": l.user_id,
            "username": l.user.name if l.user else None,
            "action": l.action,
            "detail": l.detail,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        } for l in logs]
    })


@ctflab_bp.route("/admin/container-logs/<int:slot>", methods=["GET"])
@admins_only
def admin_container_logs(slot):
    """Admin: get Docker container logs for a specific slot."""
    try:
        container_name = f"ctflab_box_{slot}"
        result = docker_mgr.get_container_logs(container_name)
        return jsonify({"logs": result})
    except Exception as e:
        return jsonify({"logs": f"Error: {str(e)}"})


@ctflab_bp.route("/admin/dashboard", methods=["GET"])
@admins_only
def admin_dashboard():
    """Admin: web dashboard page."""
    return render_template("ctflab/admin.html")
