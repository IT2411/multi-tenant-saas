import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.team import Team, TeamMember
from app.repositories.base import TenantScopedRepository


class TeamRepository(TenantScopedRepository[Team]):
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        super().__init__(Team, session, organization_id)

    async def get_team_with_members(self, team_id: uuid.UUID) -> Team | None:
        stmt = (
            select(Team)
            .where(
                Team.id == team_id,
                Team.organization_id == self.organization_id,
            )
            .options(
                selectinload(Team.members).joinedload(TeamMember.user),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_teams_with_members(self) -> Sequence[Team]:
        stmt = (
            select(Team)
            .where(Team.organization_id == self.organization_id)
            .options(
                selectinload(Team.members).joinedload(TeamMember.user),
            )
            .order_by(Team.name.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
