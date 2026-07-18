"""Tests for registration and login."""

from conftest import auth_headers, login_user, register_user


def test_register_success(client):
    resp = register_user(client, "alice@example.com")
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert body["id"] > 0
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email_rejected(client):
    register_user(client, "alice@example.com")
    resp = register_user(client, "alice@example.com")
    assert resp.status_code == 409


def test_register_short_password_rejected(client):
    resp = register_user(client, "bob@example.com", password="123")
    assert resp.status_code == 422


def test_login_success(client):
    register_user(client, "alice@example.com")
    resp = client.post(
        "/auth/login",
        data={"username": "alice@example.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client):
    register_user(client, "alice@example.com")
    resp = client.post(
        "/auth/login",
        data={"username": "alice@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post(
        "/auth/login",
        data={"username": "ghost@example.com", "password": "secret123"},
    )
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    assert client.get("/tasks").status_code == 401


def test_protected_route_rejects_bad_token(client):
    resp = client.get("/tasks", headers=auth_headers("not-a-real-token"))
    assert resp.status_code == 401


def test_valid_token_grants_access(client):
    register_user(client, "alice@example.com")
    token = login_user(client, "alice@example.com")
    resp = client.get("/tasks", headers=auth_headers(token))
    assert resp.status_code == 200
