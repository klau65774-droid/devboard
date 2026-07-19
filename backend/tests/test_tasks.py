"""Tests for task CRUD, pagination, filtering and per-user isolation."""

from conftest import auth_headers, login_user, register_user


def make_user(client, email="alice@example.com"):
    register_user(client, email)
    return auth_headers(login_user(client, email))


def create_task(client, headers, title="Task", status="todo"):
    resp = client.post(
        "/tasks",
        json={"title": title, "description": "desc", "status": status},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_and_get_task(client):
    headers = make_user(client)
    task = create_task(client, headers, title="Write tests")
    assert task["title"] == "Write tests"
    assert task["status"] == "todo"

    resp = client.get(f"/tasks/{task['id']}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == task["id"]


def test_list_tasks_pagination(client):
    headers = make_user(client)
    for i in range(25):
        create_task(client, headers, title=f"T{i}")

    page1 = client.get("/tasks?page=1&size=10", headers=headers).json()
    page3 = client.get("/tasks?page=3&size=10", headers=headers).json()
    assert page1["total"] == 25
    assert len(page1["items"]) == 10
    assert len(page3["items"]) == 5


def test_list_tasks_filter_by_status(client):
    headers = make_user(client)
    create_task(client, headers, title="A", status="todo")
    create_task(client, headers, title="B", status="done")
    create_task(client, headers, title="C", status="done")

    resp = client.get("/tasks?status=done", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert all(t["status"] == "done" for t in body["items"])


def test_update_task_status_and_title(client):
    headers = make_user(client)
    task = create_task(client, headers, title="Old title")

    resp = client.patch(
        f"/tasks/{task['id']}",
        json={"status": "in_progress", "title": "New title"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "in_progress"
    assert body["title"] == "New title"


def test_delete_task(client):
    headers = make_user(client)
    task = create_task(client, headers)

    assert client.delete(f"/tasks/{task['id']}", headers=headers).status_code == 204
    assert client.get(f"/tasks/{task['id']}", headers=headers).status_code == 404


def test_users_cannot_see_each_others_tasks(client):
    alice = make_user(client, "alice@example.com")
    bob = make_user(client, "bob@example.com")
    create_task(client, alice, title="Alice's task")
    create_task(client, bob, title="Bob's task")

    bob_list = client.get("/tasks", headers=bob).json()
    assert bob_list["total"] == 1
    assert bob_list["items"][0]["title"] == "Bob's task"


def test_user_cannot_access_modify_or_delete_others_task(client):
    alice = make_user(client, "alice@example.com")
    bob = make_user(client, "bob@example.com")
    task = create_task(client, alice, title="Alice's task")

    assert client.get(f"/tasks/{task['id']}", headers=bob).status_code == 404
    assert (
        client.patch(
            f"/tasks/{task['id']}", json={"status": "done"}, headers=bob
        ).status_code
        == 404
    )
    assert client.delete(f"/tasks/{task['id']}", headers=bob).status_code == 404
    # The task must be untouched for its real owner.
    assert client.get(f"/tasks/{task['id']}", headers=alice).status_code == 200


def test_invalid_status_rejected(client):
    headers = make_user(client)
    resp = client.post(
        "/tasks", json={"title": "X", "status": "nonsense"}, headers=headers
    )
    assert resp.status_code == 422


def test_create_task_with_due_date(client):
    headers = make_user(client)
    resp = client.post(
        "/tasks",
        json={"title": "Dated task", "due_date": "2026-08-01T10:00:00"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["due_date"] == "2026-08-01T10:00:00"


def test_create_task_without_due_date_defaults_to_null(client):
    headers = make_user(client)
    task = create_task(client, headers, title="No due date")
    assert task["due_date"] is None


def test_update_task_due_date(client):
    headers = make_user(client)
    task = create_task(client, headers, title="Reschedule me")
    assert task["due_date"] is None

    resp = client.patch(
        f"/tasks/{task['id']}",
        json={"due_date": "2026-09-15T00:00:00"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["due_date"] == "2026-09-15T00:00:00"

    # The updated value is persisted and returned on subsequent reads.
    got = client.get(f"/tasks/{task['id']}", headers=headers).json()
    assert got["due_date"] == "2026-09-15T00:00:00"
