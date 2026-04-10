from __future__ import annotations

from typing import Optional

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, CreatedAtMixin, UUIDMixin


class PaperVersion(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "paper_versions"
    __table_args__ = (
        UniqueConstraint("paper_id", "version_number", name="uq_paper_version"),
    )

    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("papers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    latex_file_key: Mapped[Optional[str]] = mapped_column(String(500))
    pdf_file_key: Mapped[Optional[str]] = mapped_column(String(500))
    markdown_file_keys: Mapped[Optional[list]] = mapped_column(JSONB)
    change_summary: Mapped[Optional[str]] = mapped_column(Text)

    paper = relationship("Paper", back_populates="versions")
    reviews = relationship("Review", back_populates="paper_version")
