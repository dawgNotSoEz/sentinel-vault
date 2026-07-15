from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.secret import Secret
    from app.models.user import User


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("name", "created_by", name="uq_categories_name_created_by"),
        Index("ix_categories_name", "name"),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_by: Mapped[str] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    created_by_user: Mapped[User] = relationship(back_populates="categories")
    secrets: Mapped[list[Secret]] = relationship(back_populates="category")
