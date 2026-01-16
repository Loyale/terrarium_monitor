"""WSGI entrypoint for production deployments."""

from backend.app import create_app

app = create_app()
