"""Sensor polling agent that posts readings to the Flask API."""

from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

import requests
import yaml


@dataclass
class SensorReading:
    """Represents a single sensor reading ready for ingestion."""

    sensor_key: str
    metric: str
    value: float
    unit: str
    recorded_at: str
    sensor_name: Optional[str] = None
    sensor_model: Optional[str] = None
    sensor_location: Optional[str] = None
    poll_interval_sec: Optional[int] = None


class SensorBase:
    """Base class for sensor adapters."""

    def __init__(self, config: Dict[str, object]) -> None:
        """Store sensor configuration and derive common metadata."""
        self.key = str(config.get("key"))
        self.name = config.get("name") or self.key.replace("_", " ").title()
        self.model = config.get("model") or config.get("type")
        self.location = config.get("location")
        self.interval_sec = int(config.get("interval_sec", 60))
        self.metrics = list(config.get("metrics", []))

    def read(self) -> List[SensorReading]:
        """Read measurements from the sensor and return readings."""
        raise NotImplementedError

    def _reading(self, metric: str, value: float, unit: str) -> SensorReading:
        """Create a SensorReading with consistent metadata."""
        return SensorReading(
            sensor_key=self.key,
            metric=metric,
            value=value,
            unit=unit,
            recorded_at=datetime.now(timezone.utc).isoformat(),
            sensor_name=self.name,
            sensor_model=self.model,
            sensor_location=self.location,
            poll_interval_sec=self.interval_sec,
        )


class Bme280Sensor(SensorBase):
    """Sensor adapter for the BME280 temperature/humidity/pressure module."""

    def __init__(self, config: Dict[str, object]) -> None:
        """Initialize the BME280 sensor instance."""
        super().__init__(config)
        address = int(str(config.get("address", "0x76")), 16)
        import board
        import adafruit_bme280

        i2c = board.I2C()
        self._sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=address)

    def read(self) -> List[SensorReading]:
        """Read temperature, humidity, and pressure values."""
        readings: List[SensorReading] = []
        if not self.metrics or "temperature_c" in self.metrics:
            readings.append(self._reading("temperature", float(self._sensor.temperature), "c"))
        if not self.metrics or "humidity_pct" in self.metrics:
            readings.append(self._reading("humidity", float(self._sensor.humidity), "pct"))
        if not self.metrics or "pressure_hpa" in self.metrics:
            readings.append(self._reading("pressure", float(self._sensor.pressure), "hpa"))
        return readings


class Ltr390Sensor(SensorBase):
    """Sensor adapter for the LTR390 UV/ALS module."""

    def __init__(self, config: Dict[str, object]) -> None:
        """Initialize the LTR390 sensor instance."""
        super().__init__(config)
        address = int(str(config.get("address", "0x53")), 16)
        import board
        import adafruit_ltr390

        i2c = board.I2C()
        self._sensor = adafruit_ltr390.LTR390(i2c, address=address)

    def read(self) -> List[SensorReading]:
        """Read UV index and ambient light readings."""
        readings: List[SensorReading] = []
        if not self.metrics or "uv_index" in self.metrics:
            readings.append(self._reading("uv_index", float(self._sensor.uvi), "uv_index"))
        if not self.metrics or "ambient_light" in self.metrics:
            readings.append(self._reading("ambient_light", float(self._sensor.light), "als"))
        return readings


class Ds18b20Sensor(SensorBase):
    """Sensor adapter for DS18B20 1-Wire temperature probes."""

    def __init__(self, config: Dict[str, object]) -> None:
        """Initialize the DS18B20 sensor instance."""
        super().__init__(config)
        from w1thermsensor import W1ThermSensor

        sensor_id = config.get("sensor_id")
        self._sensor = W1ThermSensor(sensor_id=sensor_id) if sensor_id else W1ThermSensor()

    def read(self) -> List[SensorReading]:
        """Read the probe temperature in Celsius."""
        if self.metrics and "temperature_c" not in self.metrics:
            return []
        temperature = float(self._sensor.get_temperature())
        return [self._reading("temperature", temperature, "c")]


class Bh1750Sensor(SensorBase):
    """Sensor adapter for the BH1750 ambient light sensor."""

    def __init__(self, config: Dict[str, object]) -> None:
        """Initialize the BH1750 sensor instance."""
        super().__init__(config)
        address = int(str(config.get("address", "0x23")), 16)
        import board
        import adafruit_bh1750

        i2c = board.I2C()
        self._sensor = adafruit_bh1750.BH1750(i2c, address=address)

    def read(self) -> List[SensorReading]:
        """Read ambient light lux values."""
        if self.metrics and "illuminance" not in self.metrics:
            return []
        return [self._reading("illuminance", float(self._sensor.lux), "lux")]


@dataclass
class SensorTask:
    """Scheduler metadata for a sensor polling task."""

    sensor: SensorBase
    next_run: float


def load_config(path: str) -> Dict[str, object]:
    """Load the YAML configuration file for the agent."""
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_sensor(config: Dict[str, object]) -> SensorBase:
    """Instantiate a sensor adapter based on the config type."""
    sensor_type = config.get("type")
    if sensor_type == "bme280":
        return Bme280Sensor(config)
    if sensor_type == "ltr390":
        return Ltr390Sensor(config)
    if sensor_type == "ds18b20":
        return Ds18b20Sensor(config)
    if sensor_type == "bh1750":
        return Bh1750Sensor(config)
    raise ValueError(f"Unknown sensor type: {sensor_type}")


def build_tasks(sensor_configs: Iterable[Dict[str, object]]) -> List[SensorTask]:
    """Create scheduled tasks for each configured sensor."""
    tasks: List[SensorTask] = []
    for config in sensor_configs:
        sensor = build_sensor(config)
        tasks.append(SensorTask(sensor=sensor, next_run=time.time()))
    return tasks


def post_readings(api_url: str, readings: List[SensorReading], timeout: int) -> None:
    """Post a batch of readings to the backend ingestion endpoint."""
    payload = {"readings": [reading.__dict__ for reading in readings]}
    response = requests.post(api_url, json=payload, timeout=timeout)
    response.raise_for_status()


def poll_loop(api_url: str, tasks: List[SensorTask], timeout: int) -> None:
    """Continuously poll sensors and post readings to the backend."""
    while True:
        now = time.time()
        next_times = []
        for task in tasks:
            if now >= task.next_run:
                try:
                    readings = task.sensor.read()
                    if readings:
                        post_readings(api_url, readings, timeout)
                except Exception as exc:
                    logging.exception("Sensor read failed: %s", exc)
                task.next_run = now + task.sensor.interval_sec
            next_times.append(task.next_run)
        sleep_for = max(0.5, min(next_times) - time.time()) if next_times else 1.0
        time.sleep(sleep_for)


def configure_logging(debug: bool) -> None:
    """Configure logging for the agent process."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    """Entry point for running the sensor agent."""
    parser = argparse.ArgumentParser(description="Terrarium sensor agent")
    parser.add_argument("--config", default="/etc/terrarium-agent/config.yaml")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    configure_logging(args.debug)
    config = load_config(args.config)
    api_url = config.get("api", {}).get("url")
    if not api_url:
        raise ValueError("api.url is required in the config")
    timeout = int(config.get("api", {}).get("timeout_sec", 10))
    sensor_configs = config.get("sensors", [])
    tasks = build_tasks(sensor_configs)
    poll_loop(api_url, tasks, timeout)


if __name__ == "__main__":
    main()
