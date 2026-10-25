import os
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv

# Tests read TEST_DATABASE_URL from .env
load_dotenv()

SCHEMA = Path(__file__).parent.parent / "ingest" / "schema.sql"
TABLES = ["metric_map", "facts", "metrics", "companies"]


@pytest.fixture
def conn():
    """Connection to the TEST database, with all four tables dropped before and after."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("TEST_DATABASE_URL is not set (see .env)")
    with psycopg.connect(url, autocommit=True) as conn:
        for table in TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        yield conn
        for table in TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


@pytest.fixture
def schema_sql():
    return SCHEMA.read_text()
