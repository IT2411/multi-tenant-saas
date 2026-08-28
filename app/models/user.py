from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.audit import AuditLog, Notification
    from app.models.organization import OrganizationMember
    from app.models.team import TeamMember


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    memberships: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    team_memberships: Mapped[list["TeamMember"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="recipient",
        foreign_keys="Notification.user_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    audit_actions: Mapped[list["AuditLog"]] = relationship(
        back_populates="actor",
        foreign_keys="AuditLog.actor_id",
        passive_deletes=True,
    )
