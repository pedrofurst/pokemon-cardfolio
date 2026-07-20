from collections.abc import Iterator

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

# Declarative list of columns that may be missing on pre-existing SQLite DBs
# from earlier phases. Each entry is (table, column, ddl_type_with_default).
# create_all() only creates missing *tables*, it never ALTERs existing ones,
# so any column added to a model after the table already existed in the wild
# needs an explicit migration entry here.
_MIGRATION_COLUMNS: list[tuple[str, str, str]] = [
    ("card", "set_id", "TEXT NOT NULL DEFAULT ''"),
    ("card", "set_total", "INTEGER"),
    ("holding", "variant", "TEXT NOT NULL DEFAULT 'normal'"),
    ("holding", "archived_at", "TIMESTAMP"),
    ("pricesnapshot", "low", "REAL"),
    ("pricesnapshot", "mid", "REAL"),
    ("pricesnapshot", "high", "REAL"),
    ("pricesnapshot", "direct_low", "REAL"),
]


def make_engine(url: str | None = None):
    database_url = url or get_settings().database_url
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


def run_migrations(engine) -> None:
    """Idempotently add columns that later phases introduced to tables that
    may already exist (without those columns) on a user's disk from an
    earlier phase. Safe to call on every startup: tables that don't exist
    yet are skipped (create_all already creates them with the full schema),
    and columns that already exist are left untouched.
    """
    with engine.begin() as connection:
        for table_name, column_name, column_ddl in _MIGRATION_COLUMNS:
            existing_columns = connection.execute(
                text(f"PRAGMA table_info({table_name})")
            ).fetchall()
            if not existing_columns:
                continue  # table doesn't exist yet; create_all will make it correctly
            column_names = {row[1] for row in existing_columns}
            if column_name in column_names:
                continue
            connection.execute(
                text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_ddl}")
            )


def init_db(engine=None) -> None:
    active_engine = engine or get_engine()
    SQLModel.metadata.create_all(active_engine)
    run_migrations(active_engine)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
