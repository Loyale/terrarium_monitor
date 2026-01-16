# Operations

## Backups
The SQLite database is stored in the Docker volume `terrarium_data`. Use `docker volume inspect terrarium_data` to locate it and copy the `terrarium.db` file for backups.

## Upgrades
1. Pull the latest repo updates.
2. Rebuild the Docker image: `docker compose up --build`
3. Restart the sensor agent if its config changed.

## Data retention
SQLite is lightweight and can handle months of minute-level data on the Pi. If storage becomes a concern, consider:
- Increasing sensor intervals.
- Archiving old rows to a CSV export.

## Alerting
Alert rules can be created via the API today. Delivery channels (webhook and SMTP) are planned for a later release.
