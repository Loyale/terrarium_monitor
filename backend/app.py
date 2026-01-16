"""Flask application factory for the terrarium monitor service."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, abort, jsonify, send_from_directory

from backend.api import create_api_blueprint
from backend.config import load_config
from backend.db import build_engine, create_session_factory, init_db, session_scope
from backend.models import AlertRule, Measurement, Sensor
from backend.seed import seed_default_sensors


def create_app() -> Flask:
    """Create and configure the Flask application."""
    config = load_config()
    config.db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = build_engine(config.db_path)
    session_factory = create_session_factory(engine)
    init_db(engine, [Sensor, Measurement, AlertRule])

    with session_scope(session_factory) as session:
        seed_default_sensors(session)

    app = Flask(
        __name__,
        static_folder=str(config.frontend_dist),
        static_url_path="/",
    )

    if config.allow_cors:
        try:
            from flask_cors import CORS

            CORS(app)
        except ImportError:
            pass

    app.register_blueprint(create_api_blueprint(session_factory))

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_frontend(path: str) -> object:
        """Serve the React frontend for non-API routes."""
        if path.startswith("api"):
            abort(404)
        dist_path = Path(app.static_folder)
        if dist_path.is_dir():
            file_path = dist_path / path
            if path and file_path.exists():
                return send_from_directory(dist_path, path)
            if (dist_path / "index.html").exists():
                return send_from_directory(dist_path, "index.html")
        return jsonify({"error": "Frontend build not found"}), 404

    return app


def main() -> None:
    """Run the Flask development server."""
    app = create_app()
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)


if __name__ == "__main__":
    main()
