"""Database seeding helpers for default sensor records."""

from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from backend.models import Sensor

DEFAULT_SENSORS = (
    {
        "key": "ambient_bme280",
        "name": "Ambient Air",
        "model": "BME280",
        "location": "Upper canopy",
        "poll_interval_sec": 60,
    },
    {
        "key": "uv_ltr390",
        "name": "UV + Light",
        "model": "LTR390",
        "location": "Basking zone",
        "poll_interval_sec": 60,
    },
    {
        "key": "probe_ds18b20",
        "name": "Warm Hide Probe",
        "model": "DS18B20",
        "location": "Warm hide",
        "poll_interval_sec": 60,
    },
    {
        "key": "ambient_bh1750",
        "name": "Ambient Light",
        "model": "BH1750",
        "location": "Mid canopy",
        "poll_interval_sec": 60,
    },
)


def seed_default_sensors(session: Session, sensors: Iterable[dict] = DEFAULT_SENSORS) -> None:
    """Insert default sensors if the table is empty."""
    existing = session.query(Sensor).count()
    if existing:
        return
    for sensor in sensors:
        session.add(Sensor(**sensor))
