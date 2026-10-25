import psycopg
import pytest

from tests.conftest import TABLES


def table_names(conn):
    rows = conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    ).fetchall()
    return {row[0] for row in rows}


def test_schema_creates_four_tables(conn, schema_sql):
    conn.execute(schema_sql)
    assert set(TABLES) <= table_names(conn)


def test_duplicate_fact_is_rejected_even_with_null_period_start(conn, schema_sql):
    conn.execute(schema_sql)
    conn.execute("INSERT INTO companies VALUES (1, 'TEST', 'Test Co')")
    insert = (
        "INSERT INTO facts (cik, taxonomy, tag, unit, period_start, period_end, val, accn, form, filed) "
        "VALUES (1, 'us-gaap', 'Assets', 'USD', NULL, '2025-08-31', 100, 'a-1', '10-K', '2025-10-08')"
    )
    conn.execute(insert)
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(insert)
