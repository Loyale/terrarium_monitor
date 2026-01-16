"""Tests for basic health endpoints."""


def test_health_endpoint(tmp_path, monkeypatch):
    """Ensure the health endpoint returns an ok status."""
    monkeypatch.setenv("TERRARIUM_DB_PATH", str(tmp_path / "test.db"))
    from backend.app import create_app

    app = create_app()
    client = app.test_client()
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
