from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DuplicateUserError
from models.users import User
from schemas.user_preferences import UserProfileUpdate


class UserCRUD:
    """CRUD operations for users."""

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        """Get a user by their email address."""
        statement = select(User).where(User.email == email)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_username(self, db: AsyncSession, username: str) -> User | None:
        """Get a user by their username."""
        statement = select(User).where(User.username == username)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, user_id: UUID) -> User | None:
        """Get a user by their ID."""
        statement = select(User).where(User.id == user_id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        email: str,
        username: str,
        hashed_password: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        """Create a new user."""
        new_user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
        )
        try:
            db.add(new_user)
            await db.commit()
        except IntegrityError as exc:
            # Duplicate email/username, ensure transaction is clean before re-raising
            await db.rollback()
            raise DuplicateUserError from exc
        # Refresh after successful commit to load any DB defaults
        await db.refresh(new_user)
        return new_user

    async def update(
        self, db: AsyncSession, db_user: User, user_update: UserProfileUpdate
    ) -> User:
        """Update an existing user."""
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)

        try:
            await db.commit()
            await db.refresh(db_user)
        except IntegrityError as exc:
            await db.rollback()
            raise DuplicateUserError from exc

        return db_user

    async def set_verified(self, db: AsyncSession, user: User) -> User:
        """Mark a user's email as verified."""
        try:
            user.is_verified = True
            await db.commit()
            await db.refresh(user)
        except Exception:
            await db.rollback()
            raise
        return user

    async def update_password(
        self, db: AsyncSession, user: User, hashed_password: str
    ) -> User:
        """Update a user's password."""
        try:
            user.hashed_password = hashed_password
            await db.commit()
            await db.refresh(user)
        except Exception:
            await db.rollback()
            raise
        return user


# Create singleton instance
user_crud = UserCRUD()


# Keep backward compatibility with existing function-based API
async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get a user by their email address."""
    return await user_crud.get_by_email(db, email)


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Get a user by their username."""
    return await user_crud.get_by_username(db, username)


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Get a user by their ID."""
    return await user_crud.get_by_id(db, user_id)


async def create_user(
    db: AsyncSession,
    email: str,
    username: str,
    hashed_password: str,
    first_name: str | None = None,
    last_name: str | None = None,
) -> User:
    """Create a new user."""
    return await user_crud.create(
        db, email, username, hashed_password, first_name, last_name
    )
