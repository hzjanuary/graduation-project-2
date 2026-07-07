"""User repository helpers."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User
from app.repositories import CRUDRepository


class UserRepository(CRUDRepository[User]):
    """Database access for user authentication lookups."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        """Return one user by email address."""
        statement = select(User).where(User.email == email)
        result = await self.session.scalars(statement)
        return result.one_or_none()

    async def get_with_roles(self, user_id: UUID) -> User | None:
        """Return one user with roles eagerly loaded."""
        statement = (
            select(User).options(selectinload(User.roles)).where(User.id == user_id)
        )
        result = await self.session.scalars(statement)
        return result.one_or_none()
