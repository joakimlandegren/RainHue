# RainHue

Controls a Philips Hue lamp based on the weather forecast. Every morning it
checks the next 12 hours and sets the lamp color:

| Condition (next 12h)                | Color                                |
|-------------------------------------|--------------------------------------|
| Rain (≥ 0.1mm)                      | Blue — deeper/brighter when heavy    |
| Snow (≥ 0.1cm)                      | Cold white — brighter when heavy     |
| No precip, max temp > 30°C          | Red                                  |
| No precip, max temp > 25°C          | Orange                               |
| Otherwise                           | Neutral warm-white                   |

Precipitation always beats temperature. Snow beats rain in a wintry mix.
All thresholds are configurable via env vars.

Weather data: [Open-Meteo](https://open-meteo.com/) — free, no API key.
Lamp control: Philips Hue **remote** (cloud OAuth) API — works from anywhere,
no local network required.

## Architecture (v2)

```
rain_hue/
  config.py    # env-based config + thresholds (python-dotenv)
  weather.py   # Open-Meteo fetch -> condensed 12h Forecast
  colors.py    # pure decision function: Forecast -> ColorDecision
  hue.py       # remote CLIP v2 client with OAuth token refresh
  core.py      # one weather->color cycle (shared by CLI and API)
  __main__.py  # CLI: python -m rain_hue morning
  api.py       # Flask HTTP API: POST /set-color, GET /weather
```

Scheduling is **external** (cron/systemd) — the CLI does one run and exits.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a Hue developer app at https://developers.meethue.com/my-apps/
   (any name; note the **Client ID** and **Client Secret**).

3. Run the OAuth pairing flow once (manual, browser-based):
   - Open the authorize URL (replace the values):
     ```
     https://api.meethue.com/v2/oauth2/authorize?client_id=YOUR_CLIENT_ID&response_type=code&state=rainhue
     ```
     Approve — the browser lands on your app's callback URL with `?code=...`.
   - Exchange the code for tokens (digest auth = client id/secret):
     ```
     curl -u CLIENT_ID:CLIENT_SECRET \
       -X POST "https://api.meethue.com/oauth2/token?grant_type=authorization_code&code=THE_CODE"
     ```
     The JSON response contains `access_token` and `refresh_token`.
   - Create the bridge whitelist user (HUE_USERNAME) with the access token:
     ```
     curl -X POST https://api.meethue.com/route/api \
       -H "Authorization: Bearer ACCESS_TOKEN" \
       -H "Content-Type: application/json" \
       -d '{"devicetype":"rainhue#server"}'
     ```
     (Press the bridge link button first if asked.) The response's `username`
     is your `HUE_USERNAME`.

4. Generate `.env`:
   ```
   python3 createconfig.py
   ```
   or copy `.env.example` to `.env` and fill it in.

## Usage

One morning run (designed for cron):
```
python -m rain_hue morning
python -m rain_hue morning --lamp "Kitchen"   # override lamp
```

Cron example (06:00 daily, Europe/Stockholm host time):
```
0 6 * * * cd /path/to/RainHue && /path/to/.venv/bin/python -m rain_hue morning >> logs/cron.log 2>&1
```

HTTP API (manual remote trigger):
```
python -m rain_hue.api        # or: flask --app rain_hue.api:create_app run
```
- `GET /` — web UI (mobile-friendly, LAN-only, no auth): lamp status card
  (name, on/off, live color swatch), last-decision card (reason + weather),
  manual mode buttons (rain/snow/heat/extreme/neutral) and "run morning
  logic now".
- `POST /set-color` — run one cycle now; `?lamp=Name` to override.
- `GET /weather` — the condensed 12h forecast (no lamp changes).
- `GET /api/status` — lamp state + last decision seen by this process.
- `POST /api/mode/<name>` — apply a manual mode (rain/snow/heat/extreme/neutral).
- `POST /api/morning` — run the morning logic now.

Note: "last decision" is persisted to a small JSON state file
(`~/.rainhue-state.json`, override with `RAINHUE_STATE_FILE`) on every run —
cron CLI runs and web/API triggers all appear on the decision card.

## Token refresh

Access tokens expire (~hours). When a call returns 401, `hue.py` exchanges
`HUE_REFRESH_TOKEN` for a new pair and retries once. Hue **rotates** refresh
tokens, and the CLI is stateless, so the new pair is printed to the logs —
copy it back into `.env` when you see that message. (A cron wrapper that
rewrites .env would remove this manual step; deliberately not built in v2.)

## Configuration (.env)

| Variable            | Description                                        |
|---------------------|----------------------------------------------------|
| `HUE_CLIENT_ID`     | Hue developer app OAuth client id                  |
| `HUE_CLIENT_SECRET` | Hue developer app OAuth client secret              |
| `HUE_TOKEN`         | OAuth access token                                 |
| `HUE_REFRESH_TOKEN` | OAuth refresh token (auto-renews access token)     |
| `HUE_USERNAME`      | Bridge whitelist user ("application key")          |
| `HUE_URI`           | Remote API base (default https://api.meethue.com)  |
| `HUE_LAMP`          | Default lamp name                                  |
| `LATITUDE`          | Forecast latitude (default 59.33, Stockholm)       |
| `LONGITUDE`         | Forecast longitude (default 18.07)                 |
| `TIMEZONE`          | Forecast timezone (default Europe/Stockholm)       |
| `RAIN_MIN_MM`       | 12h precip mm that counts as rain (default 0.1)    |
| `RAIN_HEAVY_MM`     | beyond → deep blue (default 5.0)                   |
| `SNOW_MIN_CM`       | 12h snowfall cm that counts as snow (default 0.1)  |
| `SNOW_HEAVY_CM`     | beyond → brighter white (default 2.0)              |
| `TEMP_ORANGE_C`     | max temp above → orange (default 25)               |
| `TEMP_RED_C`        | max temp above → red (default 30)                  |

## Migrating from v1

- v1 used the local bridge via `phue` — v2 is remote-only (OAuth). Run the
  pairing flow above; `HUE_TOKEN` from v1 is **not** reusable.
- v1's `[bri, hue, sat]` colors are gone — v2 uses CIE xy + brightness via the
  CLIP v2 API.
- Config moved from scattered module constants to the env vars above.
  `.env.example` documents everything; `createconfig.py` regenerates `.env`.

## Testing

```
pip install -r requirements-dev.txt
pytest
```
