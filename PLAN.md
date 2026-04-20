# RainHue Remediation Plan

Addresses issues identified in code review, ordered by priority.
Each phase is independently shippable — later phases build on earlier ones but the project improves after each merge.

---

## Phase 1 — Critical Bug Fixes & Security (must-fix)

### 1.1 Remove hardcoded bearer token from `remote_bridge.py`
**File:** `remote_bridge.py:10`
- Delete the `TOKEN` module-level constant.
- Add `token` as a field on `RemoteBridge`, passed in via `__init__`.
- Add `hue_token` to the config template in `createconfig.py`.
- Update `lamps.py` to pass `cfg.hue_token` when constructing `RemoteBridge`.
- Add `localconfig.py` to `.gitignore` (already present — verify).

### 1.2 Fix `converted_light` NameError in `set_light`
**File:** `remote_bridge.py:130-141`
- Move the `converted_light` resolution block **before** the `if parameter == 'name'` branch so the variable is always defined when used.

### 1.3 Fix bare `except` and `None` weather state
**File:** `weather.py:22-26`
- Let `get_weather()` raise on failure (remove bare `except Exception`).
- Catch specific exceptions (`requests.RequestException`, `AttributeError` for missing hourly data).
- Have `get_weather()` return a boolean or raise, so callers can respond.
- In `api.py`, wrap the weather call and return HTTP 502 with a message on failure.

### 1.4 Fix `set_weather_color` default-color placement
**File:** `weather.py:35-47`
- Move `self._forecast_color = cfg.defaultColor` out of the loop body.
- Use a `for...else` pattern: the `else` block (runs when loop completes without `break`) sets the default color.

### 1.5 Fix global state / `__main__` guard in Flask app
**File:** `api.py:39-46`
- Introduce a `create_app()` factory function that:
  - Creates and configures the Flask app.
  - Instantiates `Lamps` and `Weather` and stores them on `app.config` (or uses Flask's `g`/extensions pattern).
  - Configures logging.
- Move the `if __name__ == '__main__'` block to call `create_app()` then `app.run()`.
- Update route handlers to pull `lamps`/`weather` from app context instead of globals.
- Remove `debug=True` from the run call (or gate it behind an env var).

---

## Phase 2 — Input Validation & Error Handling

### 2.1 Add error handling to API routes
**File:** `api.py`
- Add `try/except` blocks to both route handlers.
- Return proper HTTP status codes: 400 for bad lamp name, 502 for weather API failure, 500 for unexpected errors.
- Return JSON error bodies (`{"error": "message"}`).

### 2.2 Validate `lamp` query parameter
**File:** `api.py:28-29`
- Check that the requested lamp name exists in `lamps._light_names` before using it.
- Return 404 with a helpful message listing available lamp names if not found.

### 2.3 Fix code injection risk in `createconfig.py`
**File:** `createconfig.py`
- Replace raw string concatenation with a safe serialization method.
- Option A: Write a JSON config file instead of a `.py` file, and update the app to read JSON.
- Option B: At minimum, sanitize/validate inputs (e.g., IP format, numeric lat/lon, alphanumeric lamp name).
- Fix `raw_input()` → `input()` for Python 3 compatibility.

---

## Phase 3 — Code Cleanup & Dead Code Removal

### 3.1 Remove dead WSGI function
**File:** `api.py:12-16`
- Delete the `hue_weather_app()` function entirely.

### 3.2 Remove unused import
**File:** `weather.py:2`
- Remove `from flask import jsonify`.

### 3.3 Fix trailing comma and style issues
**File:** `lamps.py:9`
- Remove trailing comma in `RemoteBridge(cfg.uri, cfg.username, )`.
- Standardize string formatting to f-strings throughout (Python 3 only codebase).

### 3.4 Ensure `logs/` directory is created
**File:** `api.py:40`
- Add `os.makedirs('logs', exist_ok=True)` before configuring logging.

### 3.5 Add missing LICENSE file
- Add a LICENSE file (confirm license choice with maintainer — MIT is typical for this kind of project).

---

## Phase 4 — Dependency & Infrastructure Updates

### 4.1 Pin and update dependencies
**File:** `requirements.txt`
- Pin Flask to a specific version (e.g., `flask==3.0.*`).
- Update `requests` to latest stable (`requests>=2.31`).
- Replace `forecastiopy` git dependency (see 4.2).
- Add `python-dotenv` for env-based config (see 4.3).

### 4.2 Migrate from DarkSky to a live weather API
**Files:** `weather.py`, `requirements.txt`, `createconfig.py`
- Replace `forecastiopy` / DarkSky with **Open-Meteo** (free, no API key required) or **OpenWeatherMap**.
- Update `Weather` class to use the new API's hourly forecast format.
- Update config template to remove DarkSky API key (or replace with new provider's key).
- Preserve the same interface: `get_weather()`, `set_weather_color()`, `print_weather_conditions()`.

### 4.3 Replace `localconfig.py` with environment-based config
**Files:** `createconfig.py`, all files importing `localconfig`
- Use `python-dotenv` to load a `.env` file.
- Create a `config.py` module that reads env vars with defaults and validation.
- Update `createconfig.py` to generate a `.env` file instead of a `.py` file (eliminates code injection risk).
- Update `.gitignore` to include `.env`.

---

## Phase 5 — Testing

### 5.1 Add unit tests for `Weather` class
**File:** `tests/test_weather.py` (new)
- Mock the weather API responses.
- Test rain detection, snow detection, default color, and edge cases (empty forecast).
- Test that the `set_weather_color` loop logic is correct.

### 5.2 Add unit tests for `RemoteBridge`
**File:** `tests/test_remote_bridge.py` (new)
- Mock HTTP requests.
- Test `set_light` with both string and integer light IDs.
- Test the `parameter == 'name'` branch specifically (currently has the `converted_light` bug).

### 5.3 Add integration tests for API routes
**File:** `tests/test_api.py` (new)
- Use Flask's test client.
- Mock `Lamps` and `Weather` dependencies.
- Test GET `/weather` returns JSON.
- Test POST `/weather` with valid and invalid lamp names.
- Test error responses.

### 5.4 Add test infrastructure
- Add `pytest` and `pytest-mock` to `requirements.txt` (or a separate `requirements-dev.txt`).
- Add a basic `pytest.ini` or `pyproject.toml` with test configuration.

---

## Implementation Order

```
Phase 1 (Critical)  →  Phase 2 (Validation)  →  Phase 3 (Cleanup)  →  Phase 4 (Dependencies)  →  Phase 5 (Tests)
```

Phases 1–3 can be completed quickly with minimal risk. Phase 4 (especially the weather API migration) is the largest effort. Phase 5 should ideally be done in parallel with Phase 4 — writing tests against the current interface first, then updating them as the API provider changes.

---

## Out of Scope (noted for future)

- Scheduling / cron integration for periodic weather checks
- Support for multiple lamps with different color profiles
- Web UI / dashboard
- Docker containerization
- CI/CD pipeline
