from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.key import DataEncryptionKey
    from app.models.user import User


class Secret(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "secrets"
    __table_args__ = (
        Index("ix_secrets_name", "name"),
        Index("ix_secrets_category_id", "category_id"),
        Index("ix_secrets_created_by", "created_by"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    category_id: Mapped[str | None] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("categories.id"))
    created_by: Mapped[str] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped[Category | None] = relationship(back_populates="secrets")
    created_by_user: Mapped[User] = relationship(back_populates="secrets")
    versions: Mapped[list[SecretVersion]] = relationship(
        back_populates="secret",
        cascade="all, delete-orphan",
    )


class SecretVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "secret_versions"
    __table_args__ = (
        UniqueConstraint("secret_id", "version", name="uq_secret_versions_secret_id_version"),
        Index("ix_secret_versions_secret_id", "secret_id"),
        Index("ix_secret_versions_dek_id", "dek_id"),
    )

    secret_id: Mapped[str] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("secrets.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    auth_tag: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    dek_id: Mapped[str] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("deks.id"), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    secret: Mapped[Secret] = relationship(back_populates="versions")
    dek: Mapped[DataEncryptionKey] = relationship(back_populates="secret_versions")
