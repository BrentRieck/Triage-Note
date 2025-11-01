import argparse
import asyncio
import getpass
from typing import Optional

from fastapi_users import exceptions

from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

from app.auth import UserManager
from app.db import async_session_maker
from app.models.user import User
from app.user_schemas import UserCreate, UserUpdate


async def create_user(email: str, password: str, superuser: bool) -> None:
    async with async_session_maker() as session:
        user_db = SQLAlchemyUserDatabase(session, User)
        manager = UserManager(user_db)
        try:
            await manager.get_by_email(email)
        except exceptions.UserNotExists:
            pass
        else:
            raise SystemExit(f"User with email {email!r} already exists")

        await manager.create(
            UserCreate(email=email, password=password, is_superuser=superuser),
            safe=True,
        )
        print(f"Created user {email}")


async def reset_password(
    email: str, password: str, is_superuser: Optional[bool]
) -> None:
    async with async_session_maker() as session:
        user_db = SQLAlchemyUserDatabase(session, User)
        manager = UserManager(user_db)
        try:
            user = await manager.get_by_email(email)
        except exceptions.UserNotExists as exc:  # pragma: no cover - CLI feedback
            raise SystemExit(f"User with email {email!r} does not exist") from exc

        update = UserUpdate(password=password)
        if is_superuser is not None:
            update.is_superuser = is_superuser

        await manager.update(update, user, safe=False)
        print(f"Password reset for user {email}")


def _prompt_password(provided: Optional[str]) -> str:
    if provided:
        return provided
    pwd = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if pwd != confirm:
        raise SystemExit("Passwords do not match")
    return pwd


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage application users")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a new user")
    create_parser.add_argument("email", help="Email for the user")
    create_parser.add_argument(
        "--password",
        help="Password for the user; if omitted you will be prompted",
    )
    create_parser.add_argument(
        "--superuser",
        action="store_true",
        help="Create the user with superuser privileges",
    )

    reset_parser = subparsers.add_parser(
        "reset-password", help="Reset an existing user's password"
    )
    reset_parser.add_argument("email", help="Email for the user")
    reset_parser.add_argument(
        "--password",
        help="New password for the user; if omitted you will be prompted",
    )
    reset_parser.add_argument(
        "--superuser",
        choices=["true", "false"],
        help="Update the superuser flag while resetting the password",
    )

    args = parser.parse_args()
    password = _prompt_password(getattr(args, "password", None))

    if args.command == "create":
        asyncio.run(create_user(args.email, password, bool(args.superuser)))
    elif args.command == "reset-password":
        superuser_flag: Optional[bool]
        if args.superuser is None:
            superuser_flag = None
        else:
            superuser_flag = args.superuser.lower() == "true"
        asyncio.run(reset_password(args.email, password, superuser_flag))


if __name__ == "__main__":
    main()
