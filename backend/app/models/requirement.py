import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, Float, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    req_number: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., FR-001, NFR-001
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # functional, non_functional, commercial, legal, technical
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # security, scalability, integration, compliance, etc.
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    reference_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reference_section: Mapped[str | None] = mapped_column(String(200), nullable=True)
    response_required: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # high, medium, low
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding = mapped_column(Vector(1024), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project = relationship("Project", back_populates="requirements")
    document = relationship("Document", back_populates="requirements")
    response = relationship("Response", back_populates="requirement", uselist=False, lazy="selectin")
