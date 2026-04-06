"""SQLAlchemy models for CTFLab plugin."""

import datetime

from CTFd.models import Challenges, db


class CTFLabChallengeModel(Challenges):
    """Extended challenge model for CTFLab boxes."""

    __mapper_args__ = {"polymorphic_identity": "ctflab"}

    id = db.Column(
        db.Integer,
        db.ForeignKey("challenges.id", ondelete="CASCADE"),
        primary_key=True,
    )
    docker_image = db.Column(db.String(256))
    box_env_json = db.Column(db.Text, default="{}")
    instance_timeout = db.Column(db.Integer, default=14400)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class LabInstance(db.Model):
    """Tracks running box instances per user."""

    __tablename__ = "lab_instances"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    challenge_id = db.Column(
        db.Integer,
        db.ForeignKey("challenges.id", ondelete="CASCADE"),
        nullable=False,
    )
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
