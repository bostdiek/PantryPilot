from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import DuplicateUserError
from models.users import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get a user by their email address."""
    statement = select(User).where(User.email == email)
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Get a user by their username."""
    statement = select(User).where(User.username == username)
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Get a user by their ID."""
    statement = select(User).where(User.id == user_id)
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def create_user(
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
