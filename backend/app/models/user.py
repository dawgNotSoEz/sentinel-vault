from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.category import Category
    from app.models.refresh_token import RefreshToken
    from app.models.role import Role
    from app.models.secret import Secret


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email", unique=True),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role_id: Mapped[str | None] = mapped_column(PostgresUUID(as_uuid=True), ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Account Lockout fields
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    role: Mapped[Role | None] = relationship(back_populates="users")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(back_populates="user")
    secrets: Mapped[list[Secret]] = relationship(back_populates="created_by_user")
    categories: Mapped[list[Category]] = relationship(back_populates="created_by_user")
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="user")
