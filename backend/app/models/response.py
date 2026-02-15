import uuid
from datetime import datetime

from sqlalchemy import String, Text, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("requirements.id"), nullable=False, unique=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    compliance_status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # fully_compliant, partially_compliant, configurable, custom_dev, not_applicable
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_refs: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # references to KB entries used
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    requirement = relationship("Requirement", back_populates="response")
    project = relationship("Project", back_populates="responses")
