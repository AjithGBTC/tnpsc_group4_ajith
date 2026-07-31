from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import Role, User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession): self.db = db
    async def by_email(self, email: str) -> User | None:
        return await self.db.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))
    async def permissions(self, user_id) -> list[str]:
        result = await self.db.scalars(select(Role.permissions).join(UserRole, Role.id == UserRole.role_id).where(UserRole.user_id == user_id, Role.deleted_at.is_(None)))
        return sorted({item for permissions in result.all() for item in permissions})
    async def role_names(self, user_id) -> list[str]:
        result = await self.db.scalars(select(Role.name).join(UserRole, Role.id == UserRole.role_id).where(UserRole.user_id == user_id))
        return result.all()
