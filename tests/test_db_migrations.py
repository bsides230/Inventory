import os
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

EXPECTED_TABLES = {
    "alembic_version",
    "users",
    "order_drafts",
    "order_draft_items",
    "orders",
    "order_items",
    "app_settings",
}


def _db_url(path: Path) -> str:
    return f"sqlite:///{path}"


def test_migration_upgrade_and_downgrade_smoke(tmp_path):
    db_path = tmp_path / "migration_smoke.db"
    cfg = Config("alembic.ini")

    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = _db_url(db_path)
    try:
        command.upgrade(cfg, "head")

        with sqlite3.connect(db_path) as conn:
            tables = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                if not row[0].startswith("sqlite_")
            }
        assert EXPECTED_TABLES.issubset(tables)

        command.downgrade(cfg, "base")

        with sqlite3.connect(db_path) as conn:
            tables_after = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                if not row[0].startswith("sqlite_")
            }
        assert tables_after == {"alembic_version"}
    finally:
        if original_db_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = original_db_url
