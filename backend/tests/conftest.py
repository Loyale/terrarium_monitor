"""Shared pytest fixtures for backend API tests."""

from __future__ import annotations

from pathlib import Path

import pytest


def _build_test_db_path(tmp_path: Path) -> Path:
    """Return a SQLite database path rooted in the pytest temp directory."""
    return tmp_path / "test.db"


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Create a Flask app instance backed by a temporary SQLite database."""
    monkeypatch.setenv("TERRARIUM_DB_PATH", str(_build_test_db_path(tmp_path)))
    from backend.app import create_app

    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    """Return a Flask test client for making API requests."""
    return app.test_client()
