# Setup

## Requirements
- Raspberry Pi with I2C and 1-Wire enabled
- Docker and Docker Compose
- Optional: Python 3.11 + pip for the sensor agent

## Docker deployment
1. Build and start the stack:
   - `docker compose up --build`
2. Open `http://localhost:8000` on the Pi.

The SQLite database is persisted in the `terrarium_data` Docker volume.

## Development workflow
### Backend
1. Create a Python environment and install deps:
   - `pip install -r backend/requirements.txt`
2. Run the Flask server:
   - `python -m backend.app`

### Frontend
1. Install dependencies:
   - `cd frontend`
   - `npm install`
2. Start the Vite dev server:
   - `npm run dev`

If the frontend runs on a different port, set `TERRARIUM_ALLOW_CORS=1` for the backend.

## Sample data
To preview the UI with realistic readings, seed the SQLite database:

- `PYTHONPATH=. python scripts/seed_sample_data.py --hours 12 --interval-min 5`

Use `--seed` to change the random pattern or `--clear` to wipe existing measurements before reseeding.

If your backend uses a non-default database path, set `TERRARIUM_DB_PATH` to the same value
when running the script.

## Environment variables
| Variable | Purpose | Default |
| --- | --- | --- |
| TERRARIUM_DB_PATH | SQLite database path | `./data/terrarium.db` |
| TERRARIUM_TIMEZONE | Display timezone for UI | `local` |
| TERRARIUM_ALLOW_CORS | Enable CORS for dev | unset |
| PORT | Backend listen port | `8000` |
