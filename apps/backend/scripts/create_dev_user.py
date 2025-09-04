"""Idempotent dev user creation script.

Run inside the backend container or locally with the repo's environment loaded.

Usage (local):
  uv run python apps/backend/scripts/create_dev_user.py

Usage (Makefile target runs it in container):
  make create-dev-user
"""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

from sqlalchemy import select

from core.security import get_password_hash
from dependencies.db import AsyncSessionLocal
from models.users import User


DEV_USERNAME = os.getenv("DEV_USER_USERNAME", "dev")
DEV_EMAIL = os.getenv("DEV_USER_EMAIL", "dev@example.com")
DEV_PASSWORD = os.getenv("DEV_USER_PASSWORD", "devdevdev")


async def main() -> None:
    async with AsyncSessionLocal() as session:
        # Check for existing user by username or email
        stmt = (
            select(User.id)
            .where((User.username == DEV_USERNAME) | (User.email == DEV_EMAIL))
            .limit(1)
        )
        existing_id = await session.scalar(stmt)
        if existing_id is not None:
            print(f"Dev user already exists (id={existing_id}) - skipping")
            return

        hashed = get_password_hash(DEV_PASSWORD)
        user = User(
            id=uuid4(),
            username=DEV_USERNAME,
            email=DEV_EMAIL,
            hashed_password=hashed,
        )
        session.add(user)
        await session.commit()
        print(f"Created dev user: {DEV_USERNAME} <{DEV_EMAIL}>")


if __name__ == "__main__":
    asyncio.run(main())
