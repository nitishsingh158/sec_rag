INSERT_FACT = """
    INSERT INTO facts
        (cik, taxonomy, tag, unit, period_start, period_end, val, accn, form, filed, fy, fp, frame)
    VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def fact_rows(cik, data):
    """Yield one tuple per fact in a companyfacts JSON, in INSERT_FACT column order."""
    for taxonomy, tags in data["facts"].items():
        for tag, tag_data in tags.items():
            for unit, rows in tag_data["units"].items():
                for row in rows:
                    yield (
                        cik, taxonomy, tag, unit,
                        row.get("start"), row["end"], row["val"],
                        row["accn"], row["form"], row["filed"],
                        row.get("fy"), row.get("fp"), row.get("frame"),
                    )


def load_company_facts(conn, ticker, data):
    """Replace a company's rows in `companies` and `facts` with the companyfacts JSON.

    Runs in one transaction: either the whole reload happens or nothing changes.
    """
    cik = data["cik"]
    with conn.transaction():
        conn.execute(
            """
            INSERT INTO companies (cik, ticker, name) VALUES (%s, %s, %s)
            ON CONFLICT (cik) DO UPDATE SET ticker = EXCLUDED.ticker, name = EXCLUDED.name
            """,
            (cik, ticker.upper(), data["entityName"]),
        )
        conn.execute("DELETE FROM facts WHERE cik = %s", (cik,))
        with conn.cursor() as cur:
            cur.executemany(INSERT_FACT, fact_rows(cik, data))
