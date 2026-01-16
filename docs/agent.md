# Sensor agent

The sensor agent runs on the Pi host and polls hardware sensors using I2C and 1-Wire. It posts readings to the Flask ingestion endpoint in batches.

## Install
1. Install dependencies:
   - `pip install -r agent/requirements.txt`
2. Copy the example config to `/etc/terrarium-agent/config.yaml` and edit it.
3. Start the agent:
   - `python agent/agent.py --config /etc/terrarium-agent/config.yaml`

## Configuration
The config file is YAML and defines the API URL plus a list of sensors.

```yaml
api:
  url: http://localhost:8000/api/measurements
  timeout_sec: 10
sensors:
  - key: ambient_bme280
    type: bme280
    name: Ambient Air
    location: Upper canopy
    address: 0x76
    interval_sec: 60
    metrics:
      - temperature_c
      - humidity_pct
      - pressure_hpa
```

## Sensor types
- `bme280`: temperature, humidity, pressure
- `ltr390`: uv index, ambient light ALS
- `ds18b20`: temperature probe
- `bh1750`: illuminance (lux)

## Polling behavior
- Each sensor has its own `interval_sec`.
- Readings include metadata such as sensor name and location.
- Failures are logged and do not stop the loop.

## Systemd service
A sample unit file is provided at `agent/systemd/terrarium-agent.service`.
Adjust the `User`, `WorkingDirectory`, and `ExecStart` values for your Pi.
