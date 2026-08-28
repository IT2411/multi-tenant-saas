import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundException
from app.models.team import Team, TeamMember
from app.repositories.team import TeamRepository
from app.repositories.user import UserRepository
from app.schemas.team import TeamCreate, TeamMemberResponse, TeamResponse
from app.services.base import BaseService


class TeamService(BaseService):
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        super().__init__(session)
        self.organization_id = organization_id
        self.team_repo = TeamRepository(session, organization_id)
        self.user_repo = UserRepository(session)

    async def create_team(self, payload: TeamCreate) -> Team:
        async with self.uow.transaction():
            return await self.team_repo.create(
                name=payload.name.strip(),
                slug=payload.slug.lower().strip(),
                description=payload.description,
            )

    async def add_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> None:
        async with self.uow.transaction():
            team = await self.team_repo.get_by_id(team_id)
            if not team:
                raise EntityNotFoundException("Team", team_id)

            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise EntityNotFoundException("User", user_id)

            member = TeamMember(
                organization_id=self.organization_id,
                team_id=team_id,
                user_id=user_id,
            )
            self.session.add(member)
            await self.session.flush()

    async def get_team_detail(self, team_id: uuid.UUID) -> TeamResponse:
        team = await self.team_repo.get_team_with_members(team_id)
        if not team:
            raise EntityNotFoundException("Team", team_id)

        members_out = [
            TeamMemberResponse(
                id=m.id,
                user_id=m.user_id,
                email=m.user.email,
                full_name=m.user.full_name,
                joined_at=m.created_at,
            )
            for m in team.members
        ]

        return TeamResponse(
            id=team.id,
            organization_id=team.organization_id,
            name=team.name,
            slug=team.slug,
            description=team.description,
            created_at=team.created_at,
            members=members_out,
        )
