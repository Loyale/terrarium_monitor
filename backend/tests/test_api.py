"""Tests for terrarium monitor API behavior."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _iso(dt: datetime) -> str:
    """Return an ISO 8601 timestamp in UTC."""
    return dt.astimezone(timezone.utc).isoformat()


def test_sensors_seeded(client):
    """Ensure the database seeds default sensors on startup."""
    response = client.get("/api/sensors")

    assert response.status_code == 200
    payload = response.get_json()
    keys = {sensor["key"] for sensor in payload["sensors"]}
    assert {
        "ambient_bme280",
        "uv_ltr390",
        "probe_ds18b20",
        "ambient_bh1750",
    }.issubset(keys)


def test_measurement_ingest_and_fetch(client):
    """Ingest measurements and retrieve them via query filters."""
    now = datetime.now(timezone.utc)
    payload = {
        "readings": [
            {
                "sensor_key": "ambient_bme280",
                "sensor_name": "Ambient Air",
                "metric": "temperature",
                "value": 26.4,
                "unit": "c",
                "recorded_at": _iso(now - timedelta(minutes=2)),
            },
            {
                "sensor_key": "ambient_bme280",
                "sensor_name": "Ambient Air",
                "metric": "temperature",
                "value": 27.1,
                "unit": "c",
                "recorded_at": _iso(now - timedelta(minutes=1)),
            },
        ]
    }

    ingest = client.post("/api/measurements", json=payload)
    assert ingest.status_code == 200
    assert ingest.get_json()["ingested"] == 2

    response = client.get(
        "/api/measurements",
        query_string={
            "sensor_key": "ambient_bme280",
            "metric": "temperature",
            "order": "asc",
        },
    )
    assert response.status_code == 200
    measurements = response.get_json()["measurements"]
    assert len(measurements) == 2
    assert measurements[0]["value"] == 26.4
    assert measurements[1]["value"] == 27.1
    assert measurements[0]["sensor_key"] == "ambient_bme280"


def test_measurements_date_range_filters(client):
    """Return only readings inside the requested time range."""
    now = datetime.now(timezone.utc)
    payload = {
        "readings": [
            {
                "sensor_key": "ambient_bme280",
                "metric": "temperature",
                "value": 24.5,
                "unit": "c",
                "recorded_at": _iso(now - timedelta(hours=3)),
            },
            {
                "sensor_key": "ambient_bme280",
                "metric": "temperature",
                "value": 25.0,
                "unit": "c",
                "recorded_at": _iso(now - timedelta(hours=2)),
            },
            {
                "sensor_key": "ambient_bme280",
                "metric": "temperature",
                "value": 26.0,
                "unit": "c",
                "recorded_at": _iso(now - timedelta(hours=1)),
            },
        ]
    }
    ingest = client.post("/api/measurements", json=payload)
    assert ingest.status_code == 200

    response = client.get(
        "/api/measurements",
        query_string={
            "sensor_key": "ambient_bme280",
            "metric": "temperature",
            "start": _iso(now - timedelta(hours=2, minutes=30)),
            "end": _iso(now - timedelta(hours=1, minutes=30)),
        },
    )
    assert response.status_code == 200
    measurements = response.get_json()["measurements"]
    assert len(measurements) == 1
    assert measurements[0]["value"] == 25.0


def test_measurements_desc_order(client):
    """Return measurements in descending order when requested."""
    now = datetime.now(timezone.utc)
    payload = {
        "readings": [
            {
                "sensor_key": "ambient_bme280",
                "metric": "temperature",
                "value": 22.0,
                "unit": "c",
                "recorded_at": _iso(now - timedelta(minutes=5)),
            },
            {
                "sensor_key": "ambient_bme280",
                "metric": "temperature",
                "value": 23.0,
                "unit": "c",
                "recorded_at": _iso(now - timedelta(minutes=1)),
            },
        ]
    }
    ingest = client.post("/api/measurements", json=payload)
    assert ingest.status_code == 200

    response = client.get(
        "/api/measurements",
        query_string={
            "sensor_key": "ambient_bme280",
            "metric": "temperature",
            "order": "desc",
        },
    )
    assert response.status_code == 200
    measurements = response.get_json()["measurements"]
    assert measurements[0]["value"] == 23.0
    assert measurements[1]["value"] == 22.0


def test_measurements_invalid_timestamp(client):
    """Reject invalid date filters for measurement queries."""
    response = client.get(
        "/api/measurements",
        query_string={
            "sensor_key": "ambient_bme280",
            "metric": "temperature",
            "start": "not-a-timestamp",
        },
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_measurements_require_filters(client):
    """Return a 400 error when required query params are missing."""
    response = client.get("/api/measurements")

    assert response.status_code == 400
    assert response.get_json()["error"] == "sensor_key and metric are required"


def test_measurement_validation_error(client):
    """Reject measurement payloads missing required fields."""
    response = client.post("/api/measurements", json={"readings": [{}]})

    assert response.status_code == 400
    assert "sensor_key" in response.get_json()["error"]


def test_measurement_value_validation(client):
    """Reject measurement payloads with non-numeric values."""
    response = client.post(
        "/api/measurements",
        json={
            "readings": [
                {
                    "sensor_key": "ambient_bme280",
                    "metric": "temperature",
                    "value": "not-a-number",
                    "unit": "c",
                }
            ]
        },
    )

    assert response.status_code == 400
    assert "value must be a number" in response.get_json()["error"]


def test_summary_returns_latest_per_metric(client):
    """Ensure summary output includes only the latest measurement per metric."""
    now = datetime.now(timezone.utc)
    payload = {
        "readings": [
            {
                "sensor_key": "ambient_bme280",
                "metric": "temperature",
                "value": 24.0,
                "unit": "c",
                "recorded_at": _iso(now - timedelta(minutes=10)),
            },
            {
                "sensor_key": "ambient_bme280",
                "metric": "temperature",
                "value": 25.5,
                "unit": "c",
                "recorded_at": _iso(now - timedelta(minutes=5)),
            },
            {
                "sensor_key": "ambient_bme280",
                "metric": "humidity",
                "value": 55.0,
                "unit": "pct",
                "recorded_at": _iso(now - timedelta(minutes=7)),
            },
        ]
    }
    ingest = client.post("/api/measurements", json=payload)
    assert ingest.status_code == 200

    response = client.get("/api/summary")
    assert response.status_code == 200
    sensors = response.get_json()["sensors"]
    summary = next(sensor for sensor in sensors if sensor["key"] == "ambient_bme280")
    metrics = {metric["metric"]: metric["value"] for metric in summary["metrics"]}

    assert metrics["temperature"] == 25.5
    assert metrics["humidity"] == 55.0


def test_sensor_auto_create(client):
    """Create a sensor automatically when ingesting new readings."""
    payload = {
        "readings": [
            {
                "sensor_key": "new_sensor",
                "sensor_name": "Custom Sensor",
                "sensor_model": "Custom",
                "metric": "temperature",
                "value": 21.5,
                "unit": "c",
            }
        ]
    }
    ingest = client.post("/api/measurements", json=payload)
    assert ingest.status_code == 200

    response = client.get("/api/sensors")
    assert response.status_code == 200
    keys = {sensor["key"] for sensor in response.get_json()["sensors"]}
    assert "new_sensor" in keys


def test_alert_create_and_list(client):
    """Create an alert rule and ensure it appears in the list endpoint."""
    payload = {
        "metric": "temperature",
        "min_value": "22",
        "max_value": "30",
        "channel": "webhook",
        "target": "https://example.com/alert",
    }
    created = client.post("/api/alerts", json=payload)
    assert created.status_code == 200
    assert created.get_json()["created"] is True

    response = client.get("/api/alerts")
    assert response.status_code == 200
    alerts = response.get_json()["alerts"]
    assert any(alert["metric"] == "temperature" for alert in alerts)


def test_alert_validation_error(client):
    """Reject alert payloads without required fields."""
    response = client.post("/api/alerts", json={"metric": "temperature"})

    assert response.status_code == 400
    assert "metric" in response.get_json()["error"]


def test_alert_threshold_validation(client):
    """Reject alert payloads with non-numeric threshold values."""
    response = client.post(
        "/api/alerts",
        json={
            "metric": "temperature",
            "min_value": "bad",
            "channel": "email",
            "target": "alerts@example.com",
        },
    )

    assert response.status_code == 400
    assert "min_value" in response.get_json()["error"]
