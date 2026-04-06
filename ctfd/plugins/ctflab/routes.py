"""Flask blueprint with API routes for CTFLab instance management."""

import io
import json
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


def _find_free_slot():
    """Find the lowest available slot number."""
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


@ctflab_bp.route("/instances", methods=["POST"])
@authed_only
def create_instance():
    """Launch a new lab instance for the current user."""
    user = get_current_user()
    data = request.get_json()
    challenge_id = data.get("challenge_id")

    challenge = CTFLabChallengeModel.query.filter_by(id=challenge_id).first()
    if not challenge:
        return jsonify({"error": "Challenge not found"}), 404

    existing = (
        LabInstance.query.filter_by(user_id=user.id)
        .filter(LabInstance.status.in_(["starting", "running"]))
        .first()
    )
    if existing:
        return (
            jsonify(
                {
                    "error": "You already have a running instance. "
                    "Destroy it first."
                }
            ),
            409,
        )

    slot = _find_free_slot()
    if slot is None:
        return (
            jsonify({"error": "No slots available. Try again later."}),
            503,
        )

    env_data = (
        json.loads(challenge.box_env_json) if challenge.box_env_json else {}
    )
    prefixes = [f"NBL{str(i).zfill(2)}" for i in range(1, 8)]
    flags = generate_flags(prefixes)

    timeout_seconds = challenge.instance_timeout or 14400
    instance = LabInstance(
        user_id=user.id,
        challenge_id=challenge_id,
        slot=slot,
        status="starting",
        flags_json=json.dumps(flags),
        expires_at=datetime.utcnow() + timedelta(seconds=timeout_seconds),
    )
    db.session.add(instance)
    db.session.commit()

    try:
        container_id, network_id, container_ip = docker_mgr.create_instance(
            image=challenge.docker_image,
            slot=slot,
            flags=flags,
            env_overrides=env_data,
        )
        instance.container_id = container_id
        instance.network_id = network_id
        instance.container_ip = container_ip
        instance.status = "running"

        vpn_config = docker_mgr.generate_vpn_config(slot, container_ip)
        instance.vpn_config = vpn_config

        db.session.commit()
    except Exception as e:
        instance.status = "error"
        db.session.commit()
        return (
            jsonify({"error": f"Failed to start instance: {str(e)}"}),
            500,
        )

    return jsonify(
        {
            "id": instance.id,
            "status": instance.status,
            "container_ip": instance.container_ip,
            "expires_at": instance.expires_at.isoformat(),
        }
    )


@ctflab_bp.route("/instances", methods=["GET"])
@authed_only
def get_instance():
    """Get the current user's active lab instance."""
    user = get_current_user()
    instance = (
        LabInstance.query.filter_by(user_id=user.id)
        .filter(LabInstance.status.in_(["starting", "running"]))
        .first()
    )

    if not instance:
        return jsonify({"instance": None})

    return jsonify(
        {
            "instance": {
                "id": instance.id,
                "challenge_id": instance.challenge_id,
                "status": instance.status,
                "container_ip": instance.container_ip,
                "expires_at": (
                    instance.expires_at.isoformat()
                    if instance.expires_at
                    else None
                ),
                "has_vpn": bool(instance.vpn_config),
            }
        }
    )


@ctflab_bp.route("/instances/<int:instance_id>", methods=["DELETE"])
@authed_only
def destroy_instance(instance_id):
    """Destroy a running lab instance."""
    user = get_current_user()
    instance = LabInstance.query.filter_by(
        id=instance_id, user_id=user.id
    ).first()
    if not instance:
        return jsonify({"error": "Instance not found"}), 404

    instance.status = "stopping"
    db.session.commit()

    try:
        docker_mgr.destroy_instance(
            container_id=instance.container_id,
            network_id=instance.network_id,
        )
    except Exception:
        pass

    instance.status = "stopped"
    db.session.commit()
    return jsonify({"status": "stopped"})


@ctflab_bp.route("/instances/<int:instance_id>/reset", methods=["POST"])
@authed_only
def reset_instance(instance_id):
    """Reset a running lab instance to its initial state."""
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


@ctflab_bp.route("/instances/<int:instance_id>/vpn", methods=["GET"])
@authed_only
def download_vpn(instance_id):
    """Download the OpenVPN config file for a lab instance."""
    user = get_current_user()
    instance = LabInstance.query.filter_by(
        id=instance_id, user_id=user.id
    ).first()
    if not instance or not instance.vpn_config:
        return jsonify({"error": "VPN config not available"}), 404

    buf = io.BytesIO(instance.vpn_config.encode())
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"ctflab-{user.name}-slot{instance.slot}.ovpn",
        mimetype="application/x-openvpn-profile",
    )
