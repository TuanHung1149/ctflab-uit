from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Box(Base):
    __tablename__ = "boxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    docker_image: Mapped[str] = mapped_column(String(255), nullable=False)
    port_mappings: Mapped[dict] = mapped_column(JSON, nullable=False)
    flag_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    env_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    challenges = relationship("Challenge", back_populates="box", lazy="selectin")
    instances = relationship("Instance", back_populates="box", lazy="selectin")
