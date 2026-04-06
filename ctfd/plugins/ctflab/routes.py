"""Flask blueprint with API routes for CTFLab instance management.

HTB-style model:
- Each user gets ONE .ovpn file (downloaded from /api/ctflab/vpn)
- When user spawns a box, CCD is updated to push route to their box
- User keeps same VPN connection, route updates on reconnect
"""

import io
import json
import os
import subprocess
from datetime import datetime, timedelta

from CTFd.models import db
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_user
from flask import Blueprint, jsonify, request, send_file

from .docker_utils import DockerManager
from .flag_utils import generate_flags
from .models import CTFLabChallengeModel, LabInstance

ctflab_bp = Blueprint(
    "ctflab",
    __name__,
    url_prefix="/api/ctflab",
    template_folder="templates",
)

docker_mgr = DockerManager()

MAX_SLOT = 50
SERVER_IP = os.environ.get("OVPN_SERVER_IP", "152.42.233.178")


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


def _collect_prefixes_for_image(docker_image):
    challenges = CTFLabChallengeModel.query.filter_by(
        docker_image=docker_image
    ).all()
    prefixes = [c.flag_prefix for c in challenges if c.flag_prefix]
    if not prefixes:
        prefixes = [f"NBL{str(i).zfill(2)}" for i in range(1, 8)]
    return prefixes


def _update_vpn_route(username, slot=None):
    """Update OpenVPN CCD to push route for user's active box."""
    script = "/opt/ctflab-uit/scripts/update-vpn-route.sh"
    if not os.path.isfile(script):
        return
    try:
        action = str(slot) if slot else "remove"
        subprocess.run(
            ["bash", script, username, action],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass


def _ensure_user_vpn(username):
    """Generate VPN cert + .ovpn for user if not exists."""
    script = "/opt/ctflab-uit/scripts/setup-vpn-user.sh"
    ovpn_path = f"/opt/ctflab-uit/vpn-configs/{username}.ovpn"
    if os.path.isfile(ovpn_path):
        return ovpn_path
    if os.path.isfile(script):
        try:
            subprocess.run(
                ["bash", script, username, SERVER_IP],
                capture_output=True, timeout=30,
            )
        except Exception:
            pass
    return ovpn_path if os.path.isfile(ovpn_path) else None


def _fix_routing():
    """Run fix-vpn-routing.sh to clear Docker nft drops."""
    try:
        subprocess.run(
            ["bash", "/opt/ctflab-uit/fix-vpn-routing.sh"],
            capture_output=True, timeout=10,
        )
    except Exception:
        pass


# ── VPN download (per-user, like HTB) ──────────────────────────────

@ctflab_bp.route("/vpn", methods=["GET"])
@authed_only
def download_user_vpn():
    """Download the user's .ovpn file (one per user, reusable for all boxes)."""
    user = get_current_user()
    ovpn_path = _ensure_user_vpn(user.name)

    if not ovpn_path or not os.path.isfile(ovpn_path):
        return jsonify({"error": "VPN config not available. Contact admin."}), 500

    content = open(ovpn_path).read()
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
    data = request.get_json()
    challenge_id = data.get("challenge_id")

    challenge = CTFLabChallengeModel.query.filter_by(id=challenge_id).first()
    if not challenge:
        return jsonify({"error": "Challenge not found"}), 404

    docker_image = challenge.docker_image

    # Reuse existing instance for same image
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

    # Check no other active instance (1 instance at a time, like HTB)
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

    env_data = json.loads(challenge.box_env_json) if challenge.box_env_json else {}
    prefixes = _collect_prefixes_for_image(docker_image)
    flags = generate_flags(prefixes)

    timeout_seconds = challenge.instance_timeout or 14400
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

    try:
        container_id, network_id, container_ip = docker_mgr.create_instance(
            image=docker_image, slot=slot, flags=flags, env_overrides=env_data,
        )
        instance.container_id = container_id
        instance.network_id = network_id
        instance.container_ip = container_ip
        instance.status = "running"

        # Ensure user has VPN cert
        _ensure_user_vpn(user.name)

        # Update VPN route to push this slot to user
        _update_vpn_route(user.name, slot)

        # Fix Docker nft rules for VPN routing
        _fix_routing()

        db.session.commit()
    except Exception as e:
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

    # Remove VPN route
    _update_vpn_route(user.name, None)

    instance.status = "stopped"
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

    return jsonify({"status": "reset"})


# Keep old per-instance VPN download for backward compatibility
@ctflab_bp.route("/instances/<int:instance_id>/vpn", methods=["GET"])
@authed_only
def download_instance_vpn(instance_id):
    """Download VPN config (redirects to per-user VPN)."""
    return download_user_vpn()
