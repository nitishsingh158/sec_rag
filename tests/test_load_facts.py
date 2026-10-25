import copy
from datetime import date

import pytest

from ingest.load_facts import load_company_facts

# Three facts: a duration with a frame, a balance-sheet fact with no start, and a dei fact with no fy/fp.
FACTS = {
    "cik": 909832,
    "entityName": "COSTCO WHOLESALE CORP /NEW",
    "facts": {
        "us-gaap": {
            "CostOfGoodsAndServicesSold": {
                "units": {
                    "USD": [
                        {
                            "start": "2024-09-02", "end": "2025-08-31", "val": 239886000000,
                            "accn": "0000909832-25-000101", "fy": 2025, "fp": "FY",
                            "form": "10-K", "filed": "2025-10-08", "frame": "CY2025",
                        }
                    ]
                }
            },
            "Assets": {
                "units": {
                    "USD": [
                        {
                            "end": "2025-08-31", "val": 77000000000,
                            "accn": "0000909832-25-000101", "fy": 2025, "fp": "FY",
                            "form": "10-K", "filed": "2025-10-08",
                        }
                    ]
                }
            },
        },
        "dei": {
            "EntityCommonStockSharesOutstanding": {
                "units": {
                    "shares": [
                        {
                            "end": "2025-10-01", "val": 443000000,
                            "accn": "0000909832-25-000101", "form": "10-K", "filed": "2025-10-08",
                        }
                    ]
                }
            }
        },
    },
}


@pytest.fixture
def db(conn, schema_sql):
    conn.execute(schema_sql)
    return conn


def count_facts(db):
    return db.execute("SELECT count(*) FROM facts").fetchone()[0]


def test_loads_company_and_every_fact(db):
    load_company_facts(db, "COST", FACTS)
    assert db.execute("SELECT cik, ticker, name FROM companies").fetchall() == [
        (909832, "COST", "COSTCO WHOLESALE CORP /NEW")
    ]
    assert count_facts(db) == 3
    cogs = db.execute(
        "SELECT period_start, period_end, val, form FROM facts WHERE tag = 'CostOfGoodsAndServicesSold'"
    ).fetchone()
    assert cogs == (date(2024, 9, 2), date(2025, 8, 31), 239886000000, "10-K")


def test_missing_optional_fields_become_null(db):
    load_company_facts(db, "COST", FACTS)
    assets = db.execute("SELECT period_start, frame FROM facts WHERE tag = 'Assets'").fetchone()
    assert assets == (None, None)
    dei = db.execute("SELECT fy, fp FROM facts WHERE taxonomy = 'dei'").fetchone()
    assert dei == (None, None)


def test_loading_twice_does_not_duplicate(db):
    load_company_facts(db, "COST", FACTS)
    load_company_facts(db, "COST", FACTS)
    assert count_facts(db) == 3
    assert db.execute("SELECT count(*) FROM companies").fetchone()[0] == 1


def test_reload_replaces_old_rows(db):
    load_company_facts(db, "COST", FACTS)
    smaller = copy.deepcopy(FACTS)
    del smaller["facts"]["dei"]
    load_company_facts(db, "COST", smaller)
    assert count_facts(db) == 2
