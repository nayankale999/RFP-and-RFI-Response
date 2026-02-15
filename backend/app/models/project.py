import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="draft"
    )  # draft, in_progress, review, completed, archived
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner = relationship("User", back_populates="projects", lazy="selectin")
    documents = relationship("Document", back_populates="project", lazy="selectin", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="project", lazy="selectin", cascade="all, delete-orphan")
    responses = relationship("Response", back_populates="project", lazy="selectin", cascade="all, delete-orphan")
    schedule_events = relationship("ScheduleEvent", back_populates="project", lazy="selectin", cascade="all, delete-orphan")
    pricing_items = relationship("PricingItem", back_populates="project", lazy="selectin", cascade="all, delete-orphan")
    response_plan = relationship("ResponsePlan", back_populates="project", uselist=False, lazy="selectin", cascade="all, delete-orphan")
