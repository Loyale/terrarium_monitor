"""Configuration loading for the Flask application."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    """Configuration values for the terrarium monitor backend."""

    db_path: Path
    env: str
    timezone: str
    frontend_dist: Path
    allow_cors: bool


def load_config() -> AppConfig:
    """Load configuration values from environment variables."""
    repo_root = Path(__file__).resolve().parents[1]
    default_db = repo_root / "data" / "terrarium.db"
    db_path = Path(os.getenv("TERRARIUM_DB_PATH", str(default_db))).expanduser()
    env = os.getenv("FLASK_ENV", os.getenv("TERRARIUM_ENV", "production"))
    timezone = os.getenv("TERRARIUM_TIMEZONE", "local")
    frontend_dist = repo_root / "frontend" / "dist"
    allow_cors = os.getenv("TERRARIUM_ALLOW_CORS", "").lower() in {"1", "true", "yes"}
    return AppConfig(
        db_path=db_path,
        env=env,
        timezone=timezone,
        frontend_dist=frontend_dist,
        allow_cors=allow_cors,
    )
