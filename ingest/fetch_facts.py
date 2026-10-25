
import json
import os
import threading
import time
from pathlib import Path

import httpx

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

MAX_REQUESTS_PER_SECOND = 5
FACTS_MAX_AGE_DAYS = 30


class RateLimiter:
    """Allow at most `per_second` calls per second by spacing them out."""

    def __init__(self, per_second, clock=time.monotonic, sleep=time.sleep):
        self.min_interval = 1 / per_second
        self.clock = clock
        self.sleep = sleep
        self.lock = threading.Lock()
        self.last_call = None

    def wait(self):
        with self.lock:
            if self.last_call is not None:
                elapsed = self.clock() - self.last_call
                if elapsed < self.min_interval:
                    self.sleep(self.min_interval - elapsed)
            self.last_call = self.clock()

limiter = RateLimiter(MAX_REQUESTS_PER_SECOND)


def raw_dir():
    path = Path(os.environ.get("RAW_DATA_DIR", "data/raw"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def sec_get(url, client):
    """GET a SEC URL with the required User-Agent, respecting the rate limit."""
    user_agent = os.environ.get("SEC_USER_AGENT")
    if not user_agent:
        raise RuntimeError("SEC_USER_AGENT is not set (use 'Name email@example.com')")
    limiter.wait()
    response = client.get(url, headers={"User-Agent": user_agent})
    response.raise_for_status()
    return response.json()


def load_tickers(client):
    """Return the SEC ticker file. Cached forever: it rarely changes."""
    path = raw_dir() / "company_tickers.json"
    if path.exists():
        return json.loads(path.read_text())
    data = sec_get(TICKERS_URL, client)
    path.write_text(json.dumps(data))
    return data


def get_cik(ticker, client):
    """Look up the CIK for a ticker"""
    for entry in load_tickers(client).values():
        if entry["ticker"].upper() == ticker.upper():
            return entry["cik_str"]
    raise ValueError(f"Ticker not found in SEC ticker file: {ticker}")


def is_fresh(path, max_age_days):
    age_seconds = time.time() - path.stat().st_mtime
    return age_seconds < max_age_days * 24 * 60 * 60


def fetch_company_facts(ticker, client=None, force=False):
    """Return company facts JSON for a ticker, using the cache when fresh."""
    client = client or httpx.Client(timeout=30)
    cik = str(get_cik(ticker, client)).zfill(10)

    path = raw_dir() / f"companyfacts_CIK{cik}.json"
    if not force and path.exists() and is_fresh(path, FACTS_MAX_AGE_DAYS):
        return json.loads(path.read_text())

    data = sec_get(FACTS_URL.format(cik=cik), client)
    path.write_text(json.dumps(data))
    return data
