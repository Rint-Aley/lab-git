from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Give each test an isolated on-disk database and initialize it on startup."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test-people.db"))
    with TestClient(app) as test_client:
        yield test_client


def test_health_and_empty_list(client):
    assert client.get("/health").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/api/people")
    assert response.status_code == 200
    assert response.json() == []


def test_create_get_update_and_delete_person(client):
    created_response = client.post(
        "/api/people", json={"name": "  Ada Lovelace  ", "email": "ada@example.com"}
    )
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["name"] == "Ada Lovelace"
    assert created["email"] == "ada@example.com"
    assert isinstance(created["id"], int)
    assert created["created_at"]

    person_id = created["id"]
    assert client.get(f"/api/people/{person_id}").json() == created
    assert client.get("/api/people").json()[0]["id"] == person_id

    updated_response = client.put(
        f"/api/people/{person_id}",
        json={"name": "Ada Byron", "email": "ada.byron@example.com"},
    )
    assert updated_response.status_code == 200
    assert updated_response.json()["name"] == "Ada Byron"
    assert updated_response.json()["email"] == "ada.byron@example.com"

    deleted_response = client.delete(f"/api/people/{person_id}")
    assert deleted_response.status_code == 204
    assert deleted_response.content == b""
    assert client.get(f"/api/people/{person_id}").status_code == 404
    assert client.get("/api/people").json() == []


def test_validation_rejects_blank_name_and_invalid_email(client):
    blank_name = client.post(
        "/api/people", json={"name": "   ", "email": "ada@example.com"}
    )
    assert blank_name.status_code == 422

    invalid_email = client.post(
        "/api/people", json={"name": "Ada", "email": "not-an-email"}
    )
    assert invalid_email.status_code == 422

    missing_field = client.post("/api/people", json={"name": "Ada"})
    assert missing_field.status_code == 422


def test_missing_person_returns_404_for_read_update_and_delete(client):
    assert client.get("/api/people/999").status_code == 404
    assert client.put(
        "/api/people/999", json={"name": "Nobody", "email": "nobody@example.com"}
    ).status_code == 404
    assert client.delete("/api/people/999").status_code == 404


def test_rejects_non_positive_person_id(client):
    assert client.get("/api/people/0").status_code == 422


def test_local_development_frontend_is_served_from_same_origin(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "People Management" in page.text
    assert client.get("/styles.css").status_code == 200
    script = client.get("/app.js")
    assert script.status_code == 200
    assert 'requestJson("/api/people")' in script.text


def test_records_persist_when_application_restarts(tmp_path, monkeypatch):
    database_path = tmp_path / "persistent-people.db"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))

    with TestClient(app) as first_client:
        created = first_client.post(
            "/api/people", json={"name": "Katherine Johnson", "email": "kj@example.com"}
        )
        assert created.status_code == 201
        person_id = created.json()["id"]

    # A second lifespan reopens the same database file, as a restarted process would.
    with TestClient(app) as second_client:
        response = second_client.get(f"/api/people/{person_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Katherine Johnson"
    assert database_path.exists()
