"""Tests for the rule-based AI fallback parser and the /tasks/ai-parse endpoint.

The rule layer is tested with an explicitly injected "now" so results are
deterministic. Endpoint tests force AI_API_KEY to be empty (monkeypatch) so
no real API key or network access is needed.
"""

from datetime import datetime, timedelta

import pytest

from app.ai_parser import parse_task
from app.config import settings

from conftest import auth_headers, login_user, register_user

# Fixed reference time: 2026-07-19 is a Sunday.
NOW = datetime(2026, 7, 19, 10, 30)


@pytest.fixture(autouse=True)
def no_ai_key(monkeypatch):
    """Ensure the endpoint always takes the fallback path in tests."""
    monkeypatch.setattr(settings, "AI_API_KEY", "")


# ---------- Rule-based parser ----------


def test_parse_tomorrow_afternoon():
    parsed = parse_task("明天下午交周报", NOW)
    assert parsed.due_date is not None
    assert parsed.due_date.date() == (NOW + timedelta(days=1)).date()
    assert parsed.title == "交周报"


def test_parse_next_wednesday():
    parsed = parse_task("下周三前把简历改完", NOW)
    assert parsed.due_date is not None
    # Sunday 2026-07-19 -> next week's Wednesday is 2026-07-22.
    assert parsed.due_date.date().isoformat() == "2026-07-22"
    assert parsed.title == "简历改完"


def test_parse_tonight_uses_18h():
    parsed = parse_task("今晚记得倒垃圾", NOW)
    assert parsed.due_date is not None
    assert parsed.due_date.date() == NOW.date()
    assert parsed.due_date.hour == 18
    assert parsed.title == "倒垃圾"


def test_parse_n_days_later():
    parsed = parse_task("三天后交房租", NOW)
    assert parsed.due_date is not None
    assert parsed.due_date.date() == (NOW + timedelta(days=3)).date()


def test_parse_english_tomorrow_and_weekday():
    parsed = parse_task("call mom tomorrow", NOW)
    assert parsed.due_date is not None
    assert parsed.due_date.date() == (NOW + timedelta(days=1)).date()
    assert parsed.title == "call mom"

    parsed = parse_task("finish report by Friday", NOW)
    assert parsed.due_date is not None
    assert parsed.due_date.date().isoformat() == "2026-07-24"  # next Friday
    assert parsed.title == "finish report"


def test_parse_without_date():
    parsed = parse_task("buy milk", NOW)
    assert parsed.due_date is None
    assert parsed.title == "buy milk"


# ---------- /tasks/ai-parse endpoint ----------


def _auth(client):
    register_user(client, "ai@example.com")
    return auth_headers(login_user(client, "ai@example.com"))


def test_ai_parse_requires_auth(client):
    resp = client.post("/tasks/ai-parse", json={"text": "明天交周报"})
    assert resp.status_code == 401


def test_ai_parse_fallback_without_key(client):
    resp = client.post(
        "/tasks/ai-parse",
        json={"text": "下周三前把简历改完"},
        headers=_auth(client),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "fallback"
    assert data["title"] == "简历改完"
    assert "description" in data
    assert data["due_date"] is not None
    # The parsed due date must be a Wednesday in the future.
    due = datetime.fromisoformat(data["due_date"])
    assert due.weekday() == 2
    assert due.date() >= datetime.now().date()


def test_ai_parse_fallback_no_date(client):
    resp = client.post(
        "/tasks/ai-parse",
        json={"text": "buy milk"},
        headers=_auth(client),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "fallback"
    assert data["title"] == "buy milk"
    assert data["due_date"] is None


def test_ai_parse_ai_failure_falls_back(client, monkeypatch):
    """A configured key whose request blows up still yields a fallback."""
    monkeypatch.setattr(settings, "AI_API_KEY", "fake-key")
    monkeypatch.setattr(settings, "AI_BASE_URL", "http://127.0.0.1:1")
    resp = client.post(
        "/tasks/ai-parse",
        json={"text": "明天下午交周报"},
        headers=_auth(client),
    )
    assert resp.status_code == 200
    assert resp.json()["source"] == "fallback"
