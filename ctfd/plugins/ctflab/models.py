"""SQLAlchemy models for CTFLab plugin."""

import datetime

from CTFd.models import Challenges, db


class CTFLabChallengeModel(Challenges):
    """Extended challenge model for CTFLab boxes.

    Each challenge has a ``flag_prefix`` (e.g. "NBL01") that identifies which
    flag from the shared container belongs to this challenge.  Multiple
    challenges can share the same ``docker_image``; they will all reuse a
    single running container per user.
    """

    __mapper_args__ = {"polymorphic_identity": "ctflab"}

    id = db.Column(
        db.Integer,
        db.ForeignKey("challenges.id", ondelete="CASCADE"),
        primary_key=True,
    )
    docker_image = db.Column(db.String(256))
    flag_prefix = db.Column(db.String(20))  # e.g. "NBL01", "NBL02"
    box_env_json = db.Column(db.Text, default="{}")
    instance_timeout = db.Column(db.Integer, default=14400)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class LabInstance(db.Model):
    """Tracks running box instances per user.

    Instances are keyed by ``(user_id, docker_image)`` so that all challenges
    sharing the same image reuse one container.
    """

    __tablename__ = "lab_instances"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    docker_image = db.Column(db.String(256), nullable=False)
    slot = db.Column(db.Integer, nullable=False)
    container_id = db.Column(db.String(80))
    network_id = db.Column(db.String(80))
    container_ip = db.Column(db.String(20))
    status = db.Column(db.String(20), default="starting")
    flags_json = db.Column(db.Text, default="{}")
    vpn_config = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    expires_at = db.Column(db.DateTime)

    user = db.relationship("Users", foreign_keys=[user_id])


class ActivityLog(db.Model):
    """Logs all user actions for admin monitoring."""

    __tablename__ = "ctflab_activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # login, start, stop, reset, submit, vpn_download
    detail = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship("Users", foreign_keys=[user_id])


class SuspiciousSubmission(db.Model):
    """Logs when a user submits a flag from another user's instance (flag sharing)."""

    __tablename__ = "suspicious_submissions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    challenge_id = db.Column(db.Integer, nullable=False)
    submitted_flag = db.Column(db.String(200))
    matched_user_id = db.Column(db.Integer)  # whose instance this flag belongs to
    matched_instance_id = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship("Users", foreign_keys=[user_id])
