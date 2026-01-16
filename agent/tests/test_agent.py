"""Unit tests for the sensor agent helpers and scheduling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import sys

import pytest

from agent import agent as agent_module


@dataclass
class _FakeSensor:
    """Simple sensor stub for scheduling tests."""

    interval_sec: int
    readings: list[agent_module.SensorReading]

    def read(self) -> list[agent_module.SensorReading]:
        """Return the configured readings payload."""
        return self.readings


@dataclass
class _FailingSensor:
    """Simple sensor stub that raises when read is called."""

    interval_sec: int

    def read(self) -> list[agent_module.SensorReading]:
        """Raise a runtime error to simulate a sensor failure."""
        raise RuntimeError("sensor failure")


class _StubSensor(agent_module.SensorBase):
    """Stub sensor for build_sensor tests that avoids hardware imports."""

    def __init__(self, config: dict) -> None:
        """Initialize the stub sensor without hardware dependencies."""
        super().__init__(config)

    def read(self) -> list[agent_module.SensorReading]:
        """Return no readings for stub sensors."""
        return []


@dataclass
class _CapturePost:
    """Capture outgoing POST payloads for inspection."""

    payload: dict | None = None
    url: str | None = None
    timeout: int | None = None

    def __call__(self, url, json, timeout):
        """Capture the outgoing request payload."""
        self.payload = json
        self.url = url
        self.timeout = timeout

        class _Response:
            """Minimal response stub for raise_for_status."""

            def raise_for_status(self_inner):
                """No-op status check for tests."""
                return None

        return _Response()


class _ExitLoop(Exception):
    """Custom exception used to break the polling loop in tests."""



def test_load_config_reads_yaml(tmp_path):
    """Load agent configuration from a YAML file."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("api:\n  url: http://localhost:8000\n", encoding="utf-8")

    config = agent_module.load_config(str(config_path))

    assert config["api"]["url"] == "http://localhost:8000"


@pytest.mark.parametrize(
    ("sensor_type", "attribute"),
    [
        ("bme280", "Bme280Sensor"),
        ("ltr390", "Ltr390Sensor"),
        ("ds18b20", "Ds18b20Sensor"),
        ("bh1750", "Bh1750Sensor"),
    ],
)

def test_build_sensor_selects_adapter(monkeypatch, sensor_type, attribute):
    """Build the correct sensor adapter based on config type."""
    monkeypatch.setattr(agent_module, attribute, _StubSensor)

    sensor = agent_module.build_sensor({"type": sensor_type, "key": "test_sensor"})

    assert isinstance(sensor, _StubSensor)



def test_build_sensor_unknown_type():
    """Raise a ValueError for unknown sensor types."""
    with pytest.raises(ValueError, match="Unknown sensor type"):
        agent_module.build_sensor({"type": "unknown", "key": "sensor"})



def test_build_tasks_uses_time_and_build_sensor(monkeypatch):
    """Use build_sensor for each config and set next_run timestamps."""
    sensor = _FakeSensor(interval_sec=60, readings=[])
    calls = []

    def _fake_build_sensor(config):
        """Return a shared sensor instance and record calls."""
        calls.append(config["key"])
        return sensor

    monkeypatch.setattr(agent_module, "build_sensor", _fake_build_sensor)
    monkeypatch.setattr(agent_module.time, "time", lambda: 123.0)

    tasks = agent_module.build_tasks([
        {"type": "bme280", "key": "one"},
        {"type": "ltr390", "key": "two"},
    ])

    assert [task.next_run for task in tasks] == [123.0, 123.0]
    assert calls == ["one", "two"]



def test_sensor_reading_includes_metadata():
    """Include metadata fields on generated readings."""
    sensor = agent_module.SensorBase(
        {
            "key": "ambient",
            "name": "Ambient Air",
            "model": "BME280",
            "location": "Top",
            "interval_sec": 42,
        }
    )
    reading = sensor._reading("temperature", 23.5, "c")

    assert reading.sensor_key == "ambient"
    assert reading.sensor_name == "Ambient Air"
    assert reading.sensor_model == "BME280"
    assert reading.sensor_location == "Top"
    assert reading.poll_interval_sec == 42
    parsed = datetime.fromisoformat(reading.recorded_at)
    assert parsed.tzinfo is not None



def test_post_readings_sends_payload(monkeypatch):
    """Post readings to the backend with the expected payload format."""
    capture = _CapturePost()
    monkeypatch.setattr(agent_module.requests, "post", capture)

    readings = [
        agent_module.SensorReading(
            sensor_key="ambient",
            metric="temperature",
            value=22.1,
            unit="c",
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )
    ]

    agent_module.post_readings("http://localhost/api/measurements", readings, timeout=5)

    assert capture.url == "http://localhost/api/measurements"
    assert capture.timeout == 5
    assert capture.payload == {"readings": [readings[0].__dict__]}



def test_poll_loop_posts_and_schedules(monkeypatch):
    """Poll sensors, post readings, and schedule the next run."""
    readings = [
        agent_module.SensorReading(
            sensor_key="ambient",
            metric="temperature",
            value=25.0,
            unit="c",
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )
    ]
    sensor = _FakeSensor(interval_sec=60, readings=readings)
    task = agent_module.SensorTask(sensor=sensor, next_run=0.0)
    posted = []

    def _fake_post(api_url, batch, timeout):
        """Capture outgoing batch payloads."""
        posted.append((api_url, batch, timeout))

    monkeypatch.setattr(agent_module, "post_readings", _fake_post)
    monkeypatch.setattr(agent_module.time, "time", lambda: 100.0)

    def _fake_sleep(_duration):
        """Abort the polling loop after one cycle."""
        raise _ExitLoop()

    monkeypatch.setattr(agent_module.time, "sleep", _fake_sleep)

    with pytest.raises(_ExitLoop):
        agent_module.poll_loop("http://localhost/api/measurements", [task], timeout=5)

    assert posted
    assert task.next_run == 160.0



def test_poll_loop_handles_read_errors(monkeypatch):
    """Continue polling after read failures and log the error."""
    sensor = _FailingSensor(interval_sec=30)
    task = agent_module.SensorTask(sensor=sensor, next_run=0.0)
    logged = []

    def _fake_exception(message, exc):
        """Capture logged exceptions for assertions."""
        logged.append((message, exc))

    monkeypatch.setattr(agent_module.logging, "exception", _fake_exception)
    monkeypatch.setattr(agent_module.time, "time", lambda: 100.0)

    def _fake_sleep(_duration):
        """Abort the polling loop after one cycle."""
        raise _ExitLoop()

    monkeypatch.setattr(agent_module.time, "sleep", _fake_sleep)

    with pytest.raises(_ExitLoop):
        agent_module.poll_loop("http://localhost/api/measurements", [task], timeout=5)

    assert logged



def test_main_requires_api_url(monkeypatch):
    """Raise a ValueError when api.url is missing from config."""
    monkeypatch.setattr(agent_module, "load_config", lambda _path: {})
    monkeypatch.setattr(agent_module, "configure_logging", lambda _debug: None)
    monkeypatch.setattr(sys, "argv", ["agent.py"])

    with pytest.raises(ValueError, match="api.url is required"):
        agent_module.main()



def test_main_runs_poll_loop(monkeypatch):
    """Invoke poll_loop with the configured API URL and timeout."""
    config = {
        "api": {"url": "http://localhost/api/measurements", "timeout_sec": 7},
        "sensors": [],
    }
    calls = {}

    monkeypatch.setattr(agent_module, "load_config", lambda _path: config)
    monkeypatch.setattr(agent_module, "configure_logging", lambda _debug: None)
    monkeypatch.setattr(agent_module, "build_tasks", lambda _sensors: [])
    monkeypatch.setattr(sys, "argv", ["agent.py"])

    def _fake_poll_loop(api_url, tasks, timeout):
        """Capture poll_loop arguments and stop execution."""
        calls["api_url"] = api_url
        calls["tasks"] = tasks
        calls["timeout"] = timeout
        raise _ExitLoop()

    monkeypatch.setattr(agent_module, "poll_loop", _fake_poll_loop)

    with pytest.raises(_ExitLoop):
        agent_module.main()

    assert calls["api_url"] == "http://localhost/api/measurements"
    assert calls["timeout"] == 7
    assert calls["tasks"] == []
