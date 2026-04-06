"""CTFd challenge type definition for CTFLab.

Each CTFLab challenge maps to a single flag_prefix inside a shared Docker
container.  The ``attempt()`` method validates ONLY the flag that matches
this challenge's ``flag_prefix``.
"""

import json

from CTFd.models import Fails, Solves, db
from CTFd.plugins.challenges import BaseChallenge
from CTFd.utils.user import get_current_user

from .models import CTFLabChallengeModel, LabInstance


class CTFLabChallenge(BaseChallenge):
    """Challenge type that provisions isolated Docker lab instances."""

    id = "ctflab"
    name = "ctflab"
    templates = {
        "create": "/plugins/ctflab/assets/create.html",
        "update": "/plugins/ctflab/assets/update.html",
        "view": "/plugins/ctflab/assets/view.html",
    }
    scripts = {
        "create": "/plugins/ctflab/assets/create.js",
        "update": "/plugins/ctflab/assets/update.js",
        "view": "/plugins/ctflab/assets/view.js",
    }
    route = "/plugins/ctflab/assets/"
    blueprint = None
    challenge_model = CTFLabChallengeModel

    @classmethod
    def create(cls, request):
        """Process challenge creation request."""
        data = request.form or request.get_json()
        challenge = CTFLabChallengeModel(
            name=data["name"],
            description=data.get("description", ""),
            value=int(data.get("value", 0)),
            category=data.get("category", ""),
            type="ctflab",
            state=data.get("state", "visible"),
            docker_image=data.get("docker_image", ""),
            flag_prefix=data.get("flag_prefix", ""),
            instance_timeout=int(data.get("instance_timeout", 14400)),
            box_env_json=data.get("box_env_json", "{}"),
        )
        db.session.add(challenge)
        db.session.commit()
        return challenge

    @classmethod
    def read(cls, challenge):
        """Return challenge data including instance info for current user."""
        data = {
            "id": challenge.id,
            "name": challenge.name,
            "description": challenge.description,
            "value": challenge.value,
            "category": challenge.category,
            "state": challenge.state,
            "max_attempts": challenge.max_attempts,
            "type": challenge.type,
            "type_data": {
                "id": cls.id,
                "name": cls.name,
                "templates": cls.templates,
                "scripts": cls.scripts,
            },
            "docker_image": challenge.docker_image,
            "flag_prefix": challenge.flag_prefix,
            "instance_timeout": challenge.instance_timeout,
            "box_env_json": challenge.box_env_json,
        }

        user = None
        try:
            user = get_current_user()
        except Exception:
            pass

        if user:
            instance = (
                LabInstance.query.filter_by(
                    user_id=user.id,
                    docker_image=challenge.docker_image,
                )
                .filter(LabInstance.status.in_(["starting", "running"]))
                .first()
            )
            if instance:
                data["instance"] = {
                    "id": instance.id,
                    "status": instance.status,
                    "container_ip": instance.container_ip,
                    "expires_at": (
                        instance.expires_at.isoformat()
                        if instance.expires_at
                        else None
                    ),
                    "has_vpn": bool(instance.vpn_config),
                }
        return data

    @classmethod
    def update(cls, challenge, request):
        """Process challenge update request."""
        data = request.form or request.get_json()
        for attr in [
            "name",
            "description",
            "value",
            "category",
            "state",
            "max_attempts",
        ]:
            if attr in data:
                setattr(challenge, attr, data[attr])

        if "docker_image" in data:
            challenge.docker_image = data["docker_image"]
        if "flag_prefix" in data:
            challenge.flag_prefix = data["flag_prefix"]
        if "instance_timeout" in data:
            challenge.instance_timeout = int(data["instance_timeout"])
        if "box_env_json" in data:
            challenge.box_env_json = data["box_env_json"]

        db.session.commit()
        return challenge

    @classmethod
    def delete(cls, challenge):
        """Delete challenge and clean up containers if no sibling challenges remain.

        Because multiple challenges can share the same docker_image, we only
        destroy a running container when the *last* challenge for that image
        is deleted.
        """
        docker_image = challenge.docker_image

        # Count sibling challenges that share this image (excluding self).
        sibling_count = (
            CTFLabChallengeModel.query.filter(
                CTFLabChallengeModel.docker_image == docker_image,
                CTFLabChallengeModel.id != challenge.id,
            ).count()
        )

        if sibling_count == 0:
            # Last challenge for this image -- destroy all instances.
            instances = (
                LabInstance.query.filter_by(docker_image=docker_image)
                .filter(LabInstance.status.in_(["starting", "running"]))
                .all()
            )
            if instances:
                from .docker_utils import DockerManager

                mgr = DockerManager()
                for inst in instances:
                    try:
                        mgr.destroy_instance(inst.container_id, inst.network_id)
                    except Exception:
                        pass
                    inst.status = "stopped"

            LabInstance.query.filter_by(docker_image=docker_image).delete()

        Fails.query.filter_by(challenge_id=challenge.id).delete()
        Solves.query.filter_by(challenge_id=challenge.id).delete()
        CTFLabChallengeModel.query.filter_by(id=challenge.id).delete()
        db.session.commit()

    @classmethod
    def attempt(cls, challenge, request):
        """Validate flag submission against this challenge's flag_prefix only."""
        data = request.form or request.get_json()
        submission = data.get("submission", "").strip()

        user = get_current_user()
        if not user:
            return False, "You must be logged in"

        instance = (
            LabInstance.query.filter_by(
                user_id=user.id,
                docker_image=challenge.docker_image,
            )
            .filter(LabInstance.status == "running")
            .first()
        )

        if not instance:
            return False, "You need a running instance to submit flags"

        flags = json.loads(instance.flags_json) if instance.flags_json else {}

        # Only check the flag that belongs to this challenge's prefix.
        expected_flag = flags.get(challenge.flag_prefix, "")
        if expected_flag and submission == expected_flag:
            return True, "Correct!"

        return False, "Incorrect flag"

    @classmethod
    def solve(cls, user, team, challenge, request):
        """Record a solve."""
        super().solve(user, team, challenge, request)

    @classmethod
    def fail(cls, user, team, challenge, request):
        """Record a failed attempt."""
        super().fail(user, team, challenge, request)
