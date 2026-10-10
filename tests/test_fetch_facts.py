import json
import os
import time
from pathlib import Path

import httpx
import pytest

from ingest import fetch_facts
from ingest.fetch_facts import RateLimiter, fetch_company_facts, get_cik

FIXTURES = Path(__file__).parent / "fixtures"
TICKERS = json.loads((FIXTURES / "company_tickers_sample.json").read_text())
FACTS = json.loads((FIXTURES / "companyfacts_sample.json").read_text())


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SEC_USER_AGENT", "Test User test@example.com")
    monkeypatch.setenv("RAW_DATA_DIR", str(tmp_path))
    # Real limiter would slow tests down; it has its own test below.
    monkeypatch.setattr(fetch_facts, "limiter", RateLimiter(1000))


@pytest.fixture
def fake_sec():
    """Fake SEC client. `requests` records every request made."""
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("company_tickers.json"):
            return httpx.Response(200, json=TICKERS)
        if request.url.path.endswith("CIK0000909832.json"):
            return httpx.Response(200, json=FACTS)
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return client, requests


def test_get_cik_is_case_insensitive(fake_sec):
    client, _ = fake_sec
    assert get_cik("cost", client) == 909832


def test_unknown_ticker_raises(fake_sec):
    client, _ = fake_sec
    with pytest.raises(ValueError):
        get_cik("NOPE", client)


def test_fetch_sends_user_agent_and_returns_facts(fake_sec):
    client, requests = fake_sec
    assert fetch_company_facts("COST", client) == FACTS
    assert all(r.headers["User-Agent"] == "Test User test@example.com" for r in requests)


def test_second_call_uses_cache(fake_sec):
    client, requests = fake_sec
    fetch_company_facts("COST", client)
    count = len(requests)  # ticker file + facts
    fetch_company_facts("COST", client)
    assert len(requests) == count


def test_stale_cache_is_redownloaded(fake_sec):
    client, requests = fake_sec
    fetch_company_facts("COST", client)
    path = Path(os.environ["RAW_DATA_DIR"]) / "companyfacts_CIK0000909832.json"
    old = time.time() - 31 * 24 * 60 * 60
    os.utime(path, (old, old))
    count = len(requests)
    fetch_company_facts("COST", client)
    assert len(requests) == count + 1


def test_missing_user_agent_raises(fake_sec, monkeypatch):
    client, requests = fake_sec
    monkeypatch.delenv("SEC_USER_AGENT")
    with pytest.raises(RuntimeError):
        fetch_company_facts("COST", client)
    assert requests == []


def test_rate_limiter_spaces_calls():
    now = [0.0]
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds

    limiter = RateLimiter(10, clock=lambda: now[0], sleep=fake_sleep)
    limiter.wait()  # first call: no wait
    limiter.wait()  # immediately after: must wait 0.1s
    assert sleeps == [pytest.approx(0.1)]
