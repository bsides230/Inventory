from __future__ import annotations

from alembic import command
from alembic.config import Config

from db.database import get_session
from db.repositories import UserRepository


DEFAULT_USER_EXTERNAL_ID = "dev-admin"


def run() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")

    with get_session() as session:
        users = UserRepository(session)
        existing = users.get_by_external_id(DEFAULT_USER_EXTERNAL_ID)
        if existing is None:
            users.create(
                external_id=DEFAULT_USER_EXTERNAL_ID,
                email="dev-admin@example.com",
                display_name="Dev Admin",
            )
            print("Created seed user dev-admin@example.com")
        else:
            print("Seed user already exists")


if __name__ == "__main__":
    run()
