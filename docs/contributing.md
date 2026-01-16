# Contributing

## Project layout
- `backend/`: Flask API and SQLite data layer
- `frontend/`: React dashboard
- `agent/`: Hardware sensor polling agent
- `docs/`: Documentation source

## Code style
- Keep modules focused and loosely coupled.
- Add docstrings for new classes and functions.
- Prefer tested, common libraries over custom solutions.

## Tests
- Run all tests: `pytest`
- Backend only: `pytest backend/tests`
- Agent only: `pytest agent/tests`

## Documentation
- Install docs dependencies: `pip install -r docs/requirements.txt`
- Preview docs locally: `mkdocs serve`
- Build docs for deployment: `mkdocs build`
