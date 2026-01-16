# Terrarium Monitor

Terrarium Monitor is a Raspberry Pi friendly stack for collecting, storing, and visualizing reptile terrarium sensor data. It uses a host-level sensor agent for hardware access, a Flask + SQLite backend, and a React dashboard for a clean, modern UI.

## Highlights
- Modular sensor agent with per-sensor polling intervals
- Simple ingestion API with time-series storage in SQLite
- React dashboard with unit toggles and trend charts
- Docker-first deployment for reproducible Pi setups

## Quick links
- Setup steps: see Setup
- Sensor agent config: see Sensor Agent
- API details: see API Reference

## Components
- Sensor agent: reads BME280, LTR390, DS18B20, and BH1750 sensors and posts readings
- Flask backend: stores readings, serves JSON API, and serves the built UI
- React frontend: renders overview cards and charts with local time formatting

## Status
The current build focuses on data collection and visualization. Alerting and notifications are planned for a future release.
