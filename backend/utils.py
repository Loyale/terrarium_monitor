"""Utility helpers for time parsing and conversions."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def parse_iso8601(value: str) -> datetime:
    """Parse an ISO 8601 timestamp into a timezone-aware UTC datetime."""
    if not value:
        raise ValueError("Timestamp value is required")
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
