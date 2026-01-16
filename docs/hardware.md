# Hardware Wiring Guide

This guide explains how to wire supported sensors to a Raspberry Pi GPIO header.
All sensors in this project use 3.3V logic. Do not connect them to 5V pins.

## Supported sensors
- BME280 (temperature, humidity, pressure) via I2C
- LTR390 (UV index + ALS) via I2C
- BH1750 (ambient light) via I2C
- DS18B20 (temperature probe) via 1-Wire

## Before you start
1. Enable I2C and 1-Wire on the Pi.
   - `sudo raspi-config` -> Interface Options -> I2C, 1-Wire.
2. Reboot the Pi after enabling.

## GPIO pin reference
| Function | BCM GPIO | Physical pin | Notes |
| --- | --- | --- | --- |
| 3.3V | n/a | 1 or 17 | Power for sensors |
| GND | n/a | 6, 9, 14, 20, 25, 30, 34, 39 | Ground |
| I2C SDA1 | GPIO2 | 3 | Shared data line |
| I2C SCL1 | GPIO3 | 5 | Shared clock line |
| 1-Wire data | GPIO4 | 7 | Default DS18B20 data pin |

## I2C wiring (BME280, LTR390, BH1750)
All I2C sensors share the same SDA/SCL lines. Wire each board like this:

| Sensor pin | Pi pin |
| --- | --- |
| VIN / VCC | 3.3V |
| GND | GND |
| SDA | GPIO2 (SDA1, pin 3) |
| SCL | GPIO3 (SCL1, pin 5) |

### I2C addresses
Use `i2cdetect -y 1` to verify each address.

| Sensor | Default address | Alternate address | How to change |
| --- | --- | --- | --- |
| BME280 | 0x76 | 0x77 | Tie SDO to 3.3V for 0x77 |
| LTR390 | 0x53 | n/a | Fixed on most breakouts |
| BH1750 | 0x23 | 0x5C | Tie ADDR to 3.3V for 0x5C |

## DS18B20 wiring (1-Wire)
The DS18B20 requires a pull-up resistor from data to 3.3V.

| Sensor wire | Pi pin |
| --- | --- |
| VDD (red) | 3.3V |
| GND (black) | GND |
| DATA (yellow/white) | GPIO4 (pin 7) |

Add a 4.7k resistor between 3.3V and DATA:

```
3.3V ---[4.7k]--- DATA --- GPIO4
GND ---------------------- GND
```

If you use multiple DS18B20 probes, connect all DATA wires to the same GPIO4
and keep a single 4.7k pull-up resistor on the bus.

## Verify hardware
Run these checks after wiring:

```
sudo i2cdetect -y 1
ls /sys/bus/w1/devices/
```

Expected results:
- `i2cdetect` shows BME280, LTR390, and BH1750 addresses.
- `w1` devices show one or more `28-xxxxxxxxxxxx` entries.

## Notes for sensor placement
- Keep I2C cable runs short and avoid parallel runs with high-power lines.
- Use shielded or twisted wires if you must extend beyond 30-40 cm.
- Place UV sensors where the lamp shines, and humidity sensors away from misting spray.

## Next steps
Configure the sensor agent to match your wiring in `agent/config.yaml`.
