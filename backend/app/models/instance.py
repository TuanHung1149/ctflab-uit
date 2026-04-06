import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InstanceStatus(str, enum.Enum):
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class Instance(Base):
    __tablename__ = "instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    box_id: Mapped[int] = mapped_column(Integer, ForeignKey("boxes.id"), nullable=False)
    slot: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    container_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    network_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    network_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    container_ip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=InstanceStatus.PENDING.value, nullable=False
    )
    flags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="instances")
    box = relationship("Box", back_populates="instances")
