from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.secret import SecretVersion


class KeyStatus(StrEnum):
    ACTIVE = "active"
    RETIRED = "retired"
    COMPROMISED = "compromised"


class KeyEncryptionKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "keks"
    __table_args__ = (Index("ix_keks_version", "version", unique=True),)

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[KeyStatus] = mapped_column(Enum(KeyStatus), default=KeyStatus.ACTIVE, nullable=False)
    encrypted_key_material: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="local", nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    deks: Mapped[list[DataEncryptionKey]] = relationship(back_populates="kek")


class DataEncryptionKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deks"
    __table_args__ = (Index("ix_deks_kek_id", "kek_id"),)

    kek_id: Mapped[str] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("keks.id"), nullable=False)
    encrypted_key_material: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    kek_version: Mapped[int] = mapped_column(Integer, nullable=False)

    kek: Mapped[KeyEncryptionKey] = relationship(back_populates="deks")
    secret_versions: Mapped[list[SecretVersion]] = relationship(back_populates="dek")
