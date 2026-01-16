"""API routes for sensor metadata, measurements, and summaries."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from flask import Blueprint, jsonify, request
from sqlalchemy import desc
from sqlalchemy.orm import Session, sessionmaker

from backend.db import session_scope
from backend.models import AlertRule, Measurement, Sensor
from backend.utils import parse_iso8601, utcnow


def create_api_blueprint(session_factory: sessionmaker[Session]) -> Blueprint:
    """Create the Flask blueprint that serves the JSON API."""
    bp = Blueprint("api", __name__, url_prefix="/api")

    @bp.get("/health")
    def health() -> Any:
        """Return a basic health payload for uptime checks."""
        return jsonify({"status": "ok"})

    @bp.get("/sensors")
    def get_sensors() -> Any:
        """Return the list of configured sensors."""
        with session_scope(session_factory) as session:
            sensors = session.query(Sensor).order_by(Sensor.name).all()
            return jsonify({"sensors": [serialize_sensor(sensor) for sensor in sensors]})

    @bp.get("/summary")
    def get_summary() -> Any:
        """Return the latest measurements for each sensor/metric pair."""
        limit = min(int(request.args.get("limit", 400)), 2000)
        with session_scope(session_factory) as session:
            measurements = (
                session.query(Measurement)
                .order_by(desc(Measurement.recorded_at))
                .limit(limit)
                .all()
            )
            summary = build_summary_payload(measurements)
            return jsonify({"generated_at": utcnow().isoformat(), "sensors": summary})

    @bp.get("/measurements")
    def get_measurements() -> Any:
        """Return measurements filtered by sensor, metric, and optional time range."""
        sensor_key = request.args.get("sensor_key")
        metric = request.args.get("metric")
        if not sensor_key or not metric:
            return jsonify({"error": "sensor_key and metric are required"}), 400

        start_param = request.args.get("start")
        end_param = request.args.get("end")
        limit = min(int(request.args.get("limit", 1440)), 10000)
        order = request.args.get("order", "asc")

        try:
            start_dt = parse_optional_datetime(start_param)
            end_dt = parse_optional_datetime(end_param)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        with session_scope(session_factory) as session:
            query = (
                session.query(Measurement)
                .join(Sensor)
                .filter(Sensor.key == sensor_key, Measurement.metric == metric)
            )
            if start_dt:
                query = query.filter(Measurement.recorded_at >= start_dt)
            if end_dt:
                query = query.filter(Measurement.recorded_at <= end_dt)
            if order == "desc":
                query = query.order_by(desc(Measurement.recorded_at))
            else:
                query = query.order_by(Measurement.recorded_at)
            measurements = query.limit(limit).all()

        payload = [serialize_measurement(measurement, include_sensor=True) for measurement in measurements]
        return jsonify({"measurements": payload})

    @bp.post("/measurements")
    def post_measurements() -> Any:
        """Ingest one or more measurement readings."""
        payload = request.get_json(silent=True) or {}
        readings = payload.get("readings")
        if not isinstance(readings, list) or not readings:
            return jsonify({"error": "readings must be a non-empty list"}), 400

        created = 0
        with session_scope(session_factory) as session:
            for reading in readings:
                try:
                    data = normalize_reading(reading)
                except ValueError as exc:
                    return jsonify({"error": str(exc)}), 400
                sensor = get_or_create_sensor(session, data)
                measurement = Measurement(
                    sensor_id=sensor.id,
                    metric=data["metric"],
                    value=data["value"],
                    unit=data["unit"],
                    recorded_at=data["recorded_at"],
                )
                session.add(measurement)
                created += 1

        return jsonify({"ingested": created})

    @bp.get("/alerts")
    def get_alerts() -> Any:
        """Return the list of configured alert rules."""
        with session_scope(session_factory) as session:
            alerts = session.query(AlertRule).order_by(AlertRule.metric).all()
            return jsonify({"alerts": [serialize_alert(alert) for alert in alerts]})

    @bp.post("/alerts")
    def post_alerts() -> Any:
        """Create a new alert rule entry."""
        payload = request.get_json(silent=True) or {}
        try:
            alert = normalize_alert(payload)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        with session_scope(session_factory) as session:
            session.add(alert)

        return jsonify({"created": True})

    return bp


def serialize_sensor(sensor: Sensor) -> Dict[str, Any]:
    """Convert a Sensor model into a JSON-ready dictionary."""
    return {
        "id": sensor.id,
        "key": sensor.key,
        "name": sensor.name,
        "model": sensor.model,
        "location": sensor.location,
        "enabled": sensor.enabled,
        "poll_interval_sec": sensor.poll_interval_sec,
        "unit_preference": sensor.unit_preference,
    }


def serialize_measurement(measurement: Measurement, include_sensor: bool) -> Dict[str, Any]:
    """Convert a Measurement model into a JSON-ready dictionary."""
    data = {
        "metric": measurement.metric,
        "value": measurement.value,
        "unit": measurement.unit,
        "recorded_at": measurement.recorded_at.isoformat(),
    }
    if include_sensor:
        data["sensor_key"] = measurement.sensor.key
    return data


def serialize_alert(alert: AlertRule) -> Dict[str, Any]:
    """Convert an AlertRule model into a JSON-ready dictionary."""
    return {
        "id": alert.id,
        "metric": alert.metric,
        "min_value": alert.min_value,
        "max_value": alert.max_value,
        "channel": alert.channel,
        "target": alert.target,
        "enabled": alert.enabled,
    }


def build_summary_payload(measurements: Iterable[Measurement]) -> List[Dict[str, Any]]:
    """Build a summary payload keyed by sensor and metric."""
    summary_map: Dict[str, Dict[str, Any]] = {}
    metrics_seen: Dict[str, set] = {}
    for measurement in measurements:
        sensor = measurement.sensor
        entry = summary_map.setdefault(
            sensor.key,
            {
                "key": sensor.key,
                "name": sensor.name,
                "model": sensor.model,
                "location": sensor.location,
                "metrics": [],
            },
        )
        seen = metrics_seen.setdefault(sensor.key, set())
        if measurement.metric in seen:
            continue
        seen.add(measurement.metric)
        entry["metrics"].append(serialize_measurement(measurement, include_sensor=False))
    return list(summary_map.values())


def normalize_reading(reading: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize an incoming reading payload."""
    sensor_key = reading.get("sensor_key")
    metric = reading.get("metric")
    value = reading.get("value")
    unit = reading.get("unit")
    if not sensor_key or not metric or value is None or unit is None:
        raise ValueError("sensor_key, metric, value, and unit are required")
    try:
        value_float = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("value must be a number") from exc

    recorded_at = reading.get("recorded_at")
    if recorded_at:
        recorded_dt = parse_iso8601(recorded_at)
    else:
        recorded_dt = utcnow()

    return {
        "sensor_key": sensor_key,
        "sensor_name": reading.get("sensor_name"),
        "sensor_model": reading.get("sensor_model"),
        "sensor_location": reading.get("sensor_location"),
        "poll_interval_sec": reading.get("poll_interval_sec"),
        "metric": metric,
        "value": value_float,
        "unit": unit,
        "recorded_at": recorded_dt,
    }


def get_or_create_sensor(session: Session, data: Dict[str, Any]) -> Sensor:
    """Find an existing sensor by key, or create it if missing."""
    sensor = session.query(Sensor).filter(Sensor.key == data["sensor_key"]).one_or_none()
    if sensor:
        return sensor

    name = data.get("sensor_name") or data["sensor_key"].replace("_", " ").title()
    sensor = Sensor(
        key=data["sensor_key"],
        name=name,
        model=data.get("sensor_model"),
        location=data.get("sensor_location"),
        poll_interval_sec=data.get("poll_interval_sec") or 60,
    )
    session.add(sensor)
    session.flush()
    return sensor


def normalize_alert(payload: Dict[str, Any]) -> AlertRule:
    """Validate and normalize an alert payload into an AlertRule instance."""
    metric = payload.get("metric")
    channel = payload.get("channel")
    target = payload.get("target")
    if not metric or not channel or not target:
        raise ValueError("metric, channel, and target are required")
    min_value = coerce_optional_float(payload.get("min_value"))
    max_value = coerce_optional_float(payload.get("max_value"))
    return AlertRule(
        metric=metric,
        min_value=min_value,
        max_value=max_value,
        channel=channel,
        target=target,
        enabled=payload.get("enabled", True),
    )


def coerce_optional_float(value: Optional[object]) -> Optional[float]:
    """Convert a payload value to float when present, returning None otherwise."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("min_value and max_value must be numbers") from exc


def parse_optional_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse an optional ISO 8601 timestamp, returning None if absent."""
    if not value:
        return None
    return parse_iso8601(value)
