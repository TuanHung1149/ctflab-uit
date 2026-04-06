"""Flask blueprint with API routes for CTFLab instance management.

Instances are keyed by ``docker_image`` rather than ``challenge_id`` so that
multiple challenges sharing the same image reuse a single container per user.
"""

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


def _collect_prefixes_for_image(docker_image):
    """Return all flag_prefix values defined for challenges with the given image."""
    challenges = CTFLabChallengeModel.query.filter_by(
        docker_image=docker_image
    ).all()
    prefixes = [c.flag_prefix for c in challenges if c.flag_prefix]
    if not prefixes:
        # Fallback: generate the legacy NBL01..NBL07 set.
        prefixes = [f"NBL{str(i).zfill(2)}" for i in range(1, 8)]
    return prefixes


@ctflab_bp.route("/instances", methods=["POST"])
@authed_only
def create_instance():
    """Launch a new lab instance for the current user.

    The caller sends ``challenge_id``; we resolve the ``docker_image`` from
    the challenge and check whether the user already has a running instance
    for that image.  If so, the existing instance is returned (not an error).
    """
    user = get_current_user()
    data = request.get_json()
    challenge_id = data.get("challenge_id")

    challenge = CTFLabChallengeModel.query.filter_by(id=challenge_id).first()
    if not challenge:
        return jsonify({"error": "Challenge not found"}), 404

    docker_image = challenge.docker_image

    # Reuse an existing instance for the same image.
    existing = (
        LabInstance.query.filter_by(
            user_id=user.id,
            docker_image=docker_image,
        )
        .filter(LabInstance.status.in_(["starting", "running"]))
        .first()
    )

    if existing:
        return jsonify(
            {
                "id": existing.id,
                "status": existing.status,
                "container_ip": existing.container_ip,
                "expires_at": (
                    existing.expires_at.isoformat()
                    if existing.expires_at
                    else None
                ),
                "has_vpn": bool(existing.vpn_config),
            }
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
            image=docker_image,
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
            "has_vpn": bool(instance.vpn_config),
        }
    )


@ctflab_bp.route("/instances", methods=["GET"])
@authed_only
def get_instance():
    """Get the current user's active lab instance.

    Accepts an optional ``docker_image`` query parameter to scope the lookup
    to a specific image.  Without it the first active instance is returned.
    """
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

    return jsonify(
        {
            "instance": {
                "id": instance.id,
                "docker_image": instance.docker_image,
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
