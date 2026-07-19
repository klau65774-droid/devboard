"""Tests for the /tasks/stats aggregate endpoint."""

from datetime import datetime, timedelta, timezone

from conftest import auth_headers, login_user, register_user


def make_user(client, email="alice@example.com"):
    register_user(client, email)
    return auth_headers(login_user(client, email))


def create_task(client, headers, title="Task", status="todo", **extra):
    resp = client.post(
        "/tasks",
        json={"title": title, "description": "desc", "status": status, **extra},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_stats_empty_user_is_all_zero(client):
    headers = make_user(client)
    resp = client.get("/tasks/stats", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["by_status"] == {"todo": 0, "in_progress": 0, "done": 0}
    assert body["completion_rate"] == 0
    assert body["overdue"] == 0
    # Full 7-day series, all zeros, so trend charts render without gaps.
    assert len(body["completed_last_7_days"]) == 7
    assert all(d["count"] == 0 for d in body["completed_last_7_days"])


def test_stats_only_count_own_tasks(client):
    alice = make_user(client, "alice@example.com")
    bob = make_user(client, "bob@example.com")
    create_task(client, alice, title="A1", status="done")
    create_task(client, alice, title="A2", status="in_progress")
    create_task(client, bob, title="B1", status="todo")

    alice_stats = client.get("/tasks/stats", headers=alice).json()
    assert alice_stats["total"] == 2
    assert alice_stats["by_status"] == {"todo": 0, "in_progress": 1, "done": 1}
    assert alice_stats["completion_rate"] == 0.5

    bob_stats = client.get("/tasks/stats", headers=bob).json()
    assert bob_stats["total"] == 1
    assert bob_stats["by_status"] == {"todo": 1, "in_progress": 0, "done": 0}
    assert bob_stats["completion_rate"] == 0


def test_stats_completion_trend_and_completed_at_lifecycle(client):
    headers = make_user(client)
    task = create_task(client, headers, title="Finish me")

    # Marking done stamps completed_at and counts towards today's bucket.
    resp = client.patch(
        f"/tasks/{task['id']}", json={"status": "done"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["completed_at"] is not None

    stats = client.get("/tasks/stats", headers=headers).json()
    today = datetime.now(timezone.utc).date().isoformat()
    today_bucket = next(
        d for d in stats["completed_last_7_days"] if d["date"] == today
    )
    assert today_bucket["count"] == 1
    assert stats["completion_rate"] == 1.0

    # Moving away from done clears completed_at and the trend count.
    resp = client.patch(
        f"/tasks/{task['id']}", json={"status": "in_progress"}, headers=headers
    )
    assert resp.json()["completed_at"] is None

    stats = client.get("/tasks/stats", headers=headers).json()
    today_bucket = next(
        d for d in stats["completed_last_7_days"] if d["date"] == today
    )
    assert today_bucket["count"] == 0


def test_stats_overdue_counts_unfinished_past_due(client):
    headers = make_user(client)
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    create_task(client, headers, title="Overdue", due_date=yesterday)
    create_task(client, headers, title="Done late", status="done", due_date=yesterday)
    create_task(client, headers, title="Future", due_date=tomorrow)
    create_task(client, headers, title="No due date")

    stats = client.get("/tasks/stats", headers=headers).json()
    assert stats["total"] == 4
    # Only the unfinished task whose due date has passed is overdue.
    assert stats["overdue"] == 1
