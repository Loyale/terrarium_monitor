# terrarium_monitor
A Raspberry Pi web app for monitoring and logging reptile terrarium sensor data.

## Stack
- Flask API with SQLite storage
- React dashboard frontend
- Optional host-level sensor agent for BME280, LTR390, DS18B20, and BH1750 sensors

## Architecture
- The sensor agent polls physical sensors and posts batches to the Flask ingestion API.
- The Flask service stores measurements in SQLite and serves the React UI.
- The UI renders a live dashboard with unit toggles and trend charts.

## Quick start (Docker)
1. `docker compose up --build`
2. Visit `http://localhost:8000`

The SQLite database is stored in a Docker volume named `terrarium_data`.

## Development setup
Backend:
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r backend/requirements.txt`
3. `python -m backend.app`

Frontend:
1. `cd frontend`
2. `npm install`
3. `npm run dev`

If the frontend runs separately, set `TERRARIUM_ALLOW_CORS=1` for the Flask server.

## Sensor agent
1. Copy `agent/config.example.yaml` to `/etc/terrarium-agent/config.yaml` and update it.
2. Install dependencies on the Pi: `pip install -r agent/requirements.txt`
3. Run the agent: `python agent/agent.py --config /etc/terrarium-agent/config.yaml`

An example systemd unit is included at `agent/systemd/terrarium-agent.service`.
The `bh1750` entry is a placeholder for the small light sensor; update the type/metrics to match your hardware.

## API quick reference
POST `/api/measurements`
```json
{
  "readings": [
    {
      "sensor_key": "ambient_bme280",
      "sensor_name": "Ambient Air",
      "sensor_model": "BME280",
      "sensor_location": "Upper canopy",
      "metric": "temperature",
      "value": 26.4,
      "unit": "c",
      "recorded_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

GET `/api/summary` returns the latest measurements per sensor/metric.

GET `/api/measurements?sensor_key=ambient_bme280&metric=temperature&start=...&end=...`
returns time-series data for charts.

## Documentation
Documentation is built with MkDocs Material.

- Install docs dependencies: `pip install -r docs/requirements.txt`
- Preview locally: `mkdocs serve`
- Build static site: `mkdocs build`
