import os
import uuid
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.manager import BaseUserManager, UUIDIDMixin
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.user import User


AUTH_SECRET = os.getenv("AUTH_SECRET", "change-this-secret")

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=AUTH_SECRET, lifetime_seconds=60 * 60)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


async def get_user_db(session: AsyncSession = Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = AUTH_SECRET
    verification_token_secret = AUTH_SECRET

    async def on_after_register(  # pragma: no cover - hook for future use
        self, user: User, request: Optional[Request] = None
    ) -> None:
        return


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)


current_active_user = fastapi_users.current_user(active=True)


__all__ = [
    "AUTH_SECRET",
    "auth_backend",
    "bearer_transport",
    "fastapi_users",
    "current_active_user",
    "get_user_db",
    "get_user_manager",
    "UserManager",
]
