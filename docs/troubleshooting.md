# Troubleshooting

## Dashboard shows no data
- Confirm the sensor agent is running and posting to `/api/measurements`.
- Check the backend logs for ingestion errors.
- Verify the `sensor_key` values in the agent config.

## Sensor agent cannot access hardware
- Ensure I2C and 1-Wire are enabled on the Pi.
- Verify device permissions for `/dev/i2c-1` and `/sys/bus/w1`.
- Run `i2cdetect -y 1` to confirm sensor addresses.

## CORS errors in development
- Set `TERRARIUM_ALLOW_CORS=1` when running Flask locally.
- Use the Vite proxy in `frontend/vite.config.js`.

## Unexpected timestamp gaps
- Check for clock drift on the Pi.
- Confirm the agent has a stable power supply and network.

## Sensor-specific notes
- BME280: check the I2C address, typically `0x76` or `0x77`.
- LTR390: confirm the address `0x53`.
- DS18B20: enable `dtoverlay=w1-gpio` in `/boot/config.txt`.
