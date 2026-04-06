from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Challenge(Base):
    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    box_id: Mapped[int] = mapped_column(Integer, ForeignKey("boxes.id"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    flag_prefix: Mapped[str] = mapped_column(String(20), nullable=False)

    box = relationship("Box", back_populates="challenges")
    submissions = relationship("Submission", back_populates="challenge", lazy="selectin")
