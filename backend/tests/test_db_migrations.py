from sqlalchemy import text
from sqlmodel import create_engine
from sqlmodel.pool import StaticPool

from app.db import init_db, run_migrations


def _make_legacy_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE card (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    set_name TEXT,
                    number TEXT,
                    rarity TEXT,
                    image_url TEXT,
                    tcgplayer_id TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE holding (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT,
                    card_id TEXT,
                    condition TEXT,
                    is_graded BOOLEAN,
                    acquisition_cost REAL,
                    acquisition_date TEXT,
                    quantity INTEGER,
                    notes TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO card (id, name, set_name, number, rarity, image_url, tcgplayer_id)
                VALUES ('base1-4', 'Charizard', 'Base', '4', 'Rare Holo', 'i', NULL)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO holding
                    (id, owner_id, card_id, condition, is_graded, acquisition_cost,
                     acquisition_date, quantity, notes)
                VALUES
                    ('h1', 'me', 'base1-4', 'raw', 0, 120.0, '2026-01-01', 1, '')
                """
            )
        )
    return engine


def _column_names(engine, table_name):
    with engine.connect() as connection:
        rows = connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {row[1] for row in rows}


def test_init_db_adds_missing_card_columns_to_legacy_db():
    engine = _make_legacy_engine()
    init_db(engine)
    assert {"set_id", "set_total"} <= _column_names(engine, "card")


def test_init_db_adds_missing_holding_columns_to_legacy_db():
    engine = _make_legacy_engine()
    init_db(engine)
    assert "variant" in _column_names(engine, "holding")


def test_init_db_preserves_existing_row_data_on_legacy_db():
    engine = _make_legacy_engine()
    init_db(engine)
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT id, name FROM card WHERE id = 'base1-4'")
        ).fetchone()
    assert row is not None


def test_init_db_backfills_default_values_on_migrated_columns():
    engine = _make_legacy_engine()
    init_db(engine)
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT set_id FROM card WHERE id = 'base1-4'")
        ).fetchone()
    assert row[0] == ""


def test_run_migrations_is_idempotent_when_run_twice():
    engine = _make_legacy_engine()
    run_migrations(engine)
    run_migrations(engine)
    assert "variant" in _column_names(engine, "holding")


def test_run_migrations_skips_tables_that_do_not_exist_yet():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    run_migrations(engine)
    assert _column_names(engine, "card") == set()
