# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

RainHue is a Python Flask application that watches the 12-hour weather forecast (via the free Open-Meteo API) and changes a Philips Hue lamp's color when rain or snow is predicted. No weather API key is needed.

## Commands

```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install dev/test dependencies (adds pytest, pytest-mock)
pip install -r requirements-dev.txt

# Run the app
python3 -m rain_hue.api

# Interactive setup wizard — generates a .env file
python3 createconfig.py

# Run all tests
pytest

# Run a single test file
pytest tests/test_weather.py

# Run a single test by name
pytest tests/test_weather.py::TestSetWeatherColor::test_set_weather_color_rain
```

## Architecture

The application is split into four modules under `rain_hue/`:

- **`config.py`** — reads all settings from environment variables (via `python-dotenv`). Imports as `from rain_hue import config as cfg` throughout the app. Color values are hardcoded here as `[brightness, hue, saturation]` triples.
- **`weather.py`** — `Weather` class wraps the Open-Meteo `/v1/forecast` endpoint. Call `get_weather()` first to populate internal state, then `set_weather_color()` or `print_weather_conditions()`. WMO weather codes are mapped to rain/snow/clear buckets via module-level sets (`RAIN_CODES`, `SNOW_CODES`).
- **`remote_bridge.py`** — `RemoteBridge` subclasses `phue.Bridge` and overrides `request()` to inject a Bearer token into every HTTP call. It talks directly to the Philips Hue remote API (`https://api.meethue.com/`).
- **`lamps.py`** — `Lamps` wraps `RemoteBridge`, caches light objects by name on construction, and exposes `turn_on_lamp()` / `change_lamp_color()`.
- **`api.py`** — Flask app created via `create_app()` factory. `Lamps` and `Weather` instances are stored on `app.config` (not globals) and retrieved inside each route handler.

### Data flow for POST /weather

```
POST /weather?lamp=<name>
  → validate lamp name against Lamps.get_available_lamps()
  → Lamps.turn_on_lamp(lamp)
  → Weather.get_weather()         # fetches Open-Meteo, stores WMO codes
  → Weather.set_weather_color()   # scans first 12 hours, returns [bri, hue, sat]
  → Lamps.change_lamp_color()     # sets brightness/hue/saturation via RemoteBridge
  → returns JSON {lamp, color}
```

## Configuration

All runtime config comes from `.env` (copy `.env.example` to get started):

| Variable       | Purpose                                      |
|----------------|----------------------------------------------|
| `HUE_URI`      | Hue remote API base URL (e.g. `https://api.meethue.com/`) |
| `HUE_USERNAME` | Hue bridge username                          |
| `HUE_TOKEN`    | OAuth bearer token for the Hue remote API    |
| `HUE_LAMP`     | Default lamp name used when `?lamp=` is omitted |
| `LATITUDE`     | GPS latitude for the weather forecast        |
| `LONGITUDE`    | GPS longitude for the weather forecast       |

Color thresholds (`rainColor`, `snowColor`, `defaultColor`) are hardcoded in `rain_hue/config.py` as `[brightness, hue, saturation]` lists.

## Testing approach

Tests live in `tests/` and use `pytest` + `unittest.mock`.

- `conftest.py` provides two key fixtures: `app` (Flask test app with fully-mocked `Lamps` and `Weather`) and `client` (Flask test client). The `app` fixture patches at the `rain_hue.api` import level so the real Hue/Open-Meteo network is never reached.
- `test_weather.py` patches `rain_hue.weather.requests.get` directly and constructs minimal Open-Meteo response dicts via the `_make_meteo_response` helper.
- `test_remote_bridge.py` patches HTTP calls on `RemoteBridge`.

When adding new route behaviour, mock both `Lamps` and `Weather` on `app.config` via the `app` fixture rather than patching lower-level modules.
