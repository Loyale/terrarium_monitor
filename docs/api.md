# API reference

Base URL: `http://<host>:8000/api`

## Health
`GET /health`

Response:
```json
{ "status": "ok" }
```

## Sensors
`GET /sensors`

Response:
```json
{
  "sensors": [
    {
      "id": 1,
      "key": "ambient_bme280",
      "name": "Ambient Air",
      "model": "BME280",
      "location": "Upper canopy",
      "enabled": true,
      "poll_interval_sec": 60,
      "unit_preference": "f"
    }
  ]
}
```

## Summary
`GET /summary`

Returns the latest reading per metric for each sensor.

Response:
```json
{
  "generated_at": "2024-01-01T12:00:00+00:00",
  "sensors": [
    {
      "key": "ambient_bme280",
      "name": "Ambient Air",
      "model": "BME280",
      "location": "Upper canopy",
      "metrics": [
        {
          "metric": "temperature",
          "value": 25.4,
          "unit": "c",
          "recorded_at": "2024-01-01T12:00:00+00:00"
        }
      ]
    }
  ]
}
```

## Measurements
`GET /measurements`

Required query params:
- `sensor_key`
- `metric`

Optional query params:
- `start` and `end` (ISO 8601)
- `order` (`asc` or `desc`)
- `limit` (default 1440)

Example:
```
GET /api/measurements?sensor_key=ambient_bme280&metric=temperature&start=2024-01-01T00:00:00Z&end=2024-01-02T00:00:00Z
```

Response:
```json
{
  "measurements": [
    {
      "sensor_key": "ambient_bme280",
      "metric": "temperature",
      "value": 25.4,
      "unit": "c",
      "recorded_at": "2024-01-01T12:00:00+00:00"
    }
  ]
}
```

`POST /measurements`

Request body:
```json
{
  "readings": [
    {
      "sensor_key": "ambient_bme280",
      "sensor_name": "Ambient Air",
      "sensor_model": "BME280",
      "sensor_location": "Upper canopy",
      "metric": "temperature",
      "value": 25.4,
      "unit": "c",
      "recorded_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

Response:
```json
{ "ingested": 1 }
```

## Alerts
`GET /alerts`

Response:
```json
{ "alerts": [] }
```

`POST /alerts`

Request body:
```json
{
  "metric": "temperature",
  "min_value": 22,
  "max_value": 30,
  "channel": "webhook",
  "target": "https://example.com/alert"
}
```

Response:
```json
{ "created": true }
```
