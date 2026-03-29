# Belly-Debugger

A personal nutrition and body stats tracker with a FastAPI backend and a Jinja2/HTMX UI, backed by InfluxDB.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start infrastructure (InfluxDB + Grafana)
docker compose up -d influxdb grafana

# Run API locally (port 8000)
python main.py

# Run UI locally (port 8501)
uvicorn ui:app --host 0.0.0.0 --port 8501 --reload

# Full server stack
docker compose up -d

# Restart UI service on server
sudo systemctl restart belly-ui
```

## Architecture

Two FastAPI services:

- `main.py` — API on port 8000, runs in Docker
- `ui.py` — UI on port 8501, runs as a systemd service

The UI calls the API for writes (`POST /log-meal`, `POST /log-weight`) and talks to InfluxDB directly for reads and edits.

### InfluxDB measurements

- `nutrition` — meal entries
- `body_stats` — weight, waist, chest

### Environment variables

- `LOCAL_INFLUXDB_URL` — used by `ui.py` for direct InfluxDB access
- `INFLUXDB_URL` — used by the dockerized API (resolves to container name)

### Templates

Jinja2 templates live in `templates/`. `base.html` uses Pico.css with a dark theme and teal accent.

### tools/

One-off InfluxDB migration scripts (timestamp fixing). Not part of normal operation.

## Key patterns

- **Form parsing**: all endpoints use `await request.form()` directly; comma→dot decimal conversion via `.replace(",", ".")` before `float()`
- **InfluxDB edit**: delete a 1-second window around the old timestamp, then rewrite the new point
- **Template context**: `_ctx(request, **kwargs)` helper injects `app_name` into every template context
