from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_or_create_user(
    session: AsyncSession,
    google_sub: Optional[str],
    email: Optional[str],
    display_name: Optional[str],
    user_id: Optional[int] = None,
    allow_create: bool = True,
) -> User:
    """
    If user_id is provided, fetch by id. Otherwise, use google_sub/email to find or create.
    """
    if user_id:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        return user

    if not google_sub or not email:
        raise ValueError("google_sub and email are required to create user")

    result = await session.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()
    if user:
        return user

    if not allow_create:
        raise ValueError("User creation is not allowed in this flow")

    new_user = User(google_sub=google_sub, email=email, display_name=display_name or email)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user
