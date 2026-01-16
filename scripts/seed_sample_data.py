"""Seed the SQLite database with sample sensor data for UI previews."""

from __future__ import annotations

import argparse
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List

from backend.config import load_config
from backend.db import build_engine, create_session_factory, init_db, session_scope
from backend.models import AlertRule, Measurement, Sensor
from backend.seed import seed_default_sensors


SENSOR_KEYS = {
    "ambient_bme280": "Ambient Air",
    "uv_ltr390": "UV + Light",
    "probe_ds18b20": "Warm Hide Probe",
    "ambient_bh1750": "Ambient Light",
}


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for sample data generation."""
    parser = argparse.ArgumentParser(description="Seed sample terrarium sensor data")
    parser.add_argument("--hours", type=int, default=12)
    parser.add_argument("--interval-min", type=int, default=5)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--clear", action="store_true")
    return parser.parse_args()


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp a floating point value into an inclusive range."""
    return max(min_value, min(max_value, value))


def build_series(
    start: datetime,
    steps: int,
    interval: timedelta,
    rng: random.Random,
) -> Iterable[Dict[str, object]]:
    """Yield timestamped metric values for each sensor."""
    for index in range(steps):
        timestamp = start + interval * index
        position = index / max(1, steps - 1)
        cycle = math.sin(2 * math.pi * position - 0.4)
        daylight = max(0.0, math.sin(math.pi * position))

        ambient_temp = 25.2 + 1.8 * cycle + rng.uniform(-0.2, 0.2)
        hide_temp = 29.5 + 1.2 * cycle + rng.uniform(-0.2, 0.2)
        humidity = clamp(60 - 6 * cycle + rng.uniform(-1.5, 1.5), 35, 90)
        pressure = 1012 + 1.4 * math.sin(2 * math.pi * position + 0.6) + rng.uniform(-0.4, 0.4)

        uv_index = max(0.0, daylight * 4.2 + rng.uniform(-0.2, 0.2))
        als = max(0.0, daylight * 2200 + rng.uniform(-40, 40))
        illuminance = max(0.0, daylight * 1200 + rng.uniform(-30, 30))

        yield {
            "timestamp": timestamp,
            "ambient_temp": ambient_temp,
            "hide_temp": hide_temp,
            "humidity": humidity,
            "pressure": pressure,
            "uv_index": uv_index,
            "als": als,
            "illuminance": illuminance,
        }


def build_measurements(series: Iterable[Dict[str, object]], sensors: Dict[str, Sensor]) -> List[Measurement]:
    """Convert the metric series into SQLAlchemy Measurement objects."""
    measurements: List[Measurement] = []
    for entry in series:
        recorded_at = entry["timestamp"]
        measurements.extend(
            [
                Measurement(
                    sensor_id=sensors["ambient_bme280"].id,
                    metric="temperature",
                    value=float(entry["ambient_temp"]),
                    unit="c",
                    recorded_at=recorded_at,
                ),
                Measurement(
                    sensor_id=sensors["ambient_bme280"].id,
                    metric="humidity",
                    value=float(entry["humidity"]),
                    unit="pct",
                    recorded_at=recorded_at,
                ),
                Measurement(
                    sensor_id=sensors["ambient_bme280"].id,
                    metric="pressure",
                    value=float(entry["pressure"]),
                    unit="hpa",
                    recorded_at=recorded_at,
                ),
                Measurement(
                    sensor_id=sensors["uv_ltr390"].id,
                    metric="uv_index",
                    value=float(entry["uv_index"]),
                    unit="uv_index",
                    recorded_at=recorded_at,
                ),
                Measurement(
                    sensor_id=sensors["uv_ltr390"].id,
                    metric="ambient_light",
                    value=float(entry["als"]),
                    unit="als",
                    recorded_at=recorded_at,
                ),
                Measurement(
                    sensor_id=sensors["probe_ds18b20"].id,
                    metric="temperature",
                    value=float(entry["hide_temp"]),
                    unit="c",
                    recorded_at=recorded_at,
                ),
                Measurement(
                    sensor_id=sensors["ambient_bh1750"].id,
                    metric="illuminance",
                    value=float(entry["illuminance"]),
                    unit="lux",
                    recorded_at=recorded_at,
                ),
            ]
        )
    return measurements


def load_sensors(session) -> Dict[str, Sensor]:
    """Load or create default sensors for the sample data."""
    seed_default_sensors(session)
    session.flush()
    sensors = session.query(Sensor).all()
    return {sensor.key: sensor for sensor in sensors}


def clear_measurements(session) -> None:
    """Remove existing measurements from the database when requested."""
    session.query(Measurement).delete()


def main() -> None:
    """Generate and insert sample sensor data into the database."""
    args = parse_args()
    config = load_config()

    engine = build_engine(config.db_path)
    session_factory = create_session_factory(engine)
    init_db(engine, [Sensor, Measurement, AlertRule])

    rng = random.Random(args.seed)
    interval = timedelta(minutes=args.interval_min)
    steps = int(args.hours * 60 / args.interval_min) + 1
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=args.hours)

    with session_scope(session_factory) as session:
        sensors = load_sensors(session)
        missing = [key for key in SENSOR_KEYS if key not in sensors]
        if missing:
            raise RuntimeError(f"Missing sensors: {', '.join(missing)}")
        if args.clear:
            clear_measurements(session)
        series = build_series(start_time, steps, interval, rng)
        session.add_all(build_measurements(series, sensors))

    print(
        "Seeded sample data to", config.db_path, f"({steps} points per metric over {args.hours}h)"
    )


if __name__ == "__main__":
    main()
