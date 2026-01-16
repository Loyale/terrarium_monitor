# Architecture

## Data flow
1. The sensor agent polls hardware sensors at configured intervals.
2. The agent posts batches of readings to the Flask ingestion endpoint.
3. The backend stores readings in SQLite and exposes query endpoints.
4. The React UI queries the API and renders cards and charts.

## Components
### Sensor agent
- Runs on the Pi host for direct I2C and 1-Wire access.
- Uses modular sensor adapters to read metrics.
- Schedules each sensor independently based on config.

### Backend service
- Flask app with SQLAlchemy models.
- SQLite file stored in a persistent volume.
- Serves the React build for single-container deployments.

### Frontend dashboard
- Overview cards show latest readings per metric.
- A trend panel visualizes time-series data.
- Local time formatting and unit toggles for temperature.

## Database model
- sensors: metadata, location, polling interval, unit preference
- measurements: metric, value, unit, recorded_at
- alert_rules: threshold configuration for future alerting

## Metrics and units
The agent and API use metric-specific units to keep storage consistent.

| Metric | Unit | Notes |
| --- | --- | --- |
| temperature | c | Celsius, converted to F in the UI |
| humidity | pct | Relative humidity percent |
| pressure | hpa | Hectopascals |
| uv_index | uv_index | UV index |
| ambient_light | als | LTR390 ALS raw value |
| illuminance | lux | BH1750 illuminance |

## Time handling
- All stored timestamps are UTC ISO 8601.
- The UI renders timestamps in the Pi locale.
