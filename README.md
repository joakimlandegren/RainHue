# RainHue

A Python application that controls Philips Hue lights based on weather forecasts. When rain or snow is predicted within the next 12 hours, it changes your lamp color accordingly.

Uses the free [Open-Meteo API](https://open-meteo.com/) for weather data — no API key required.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the interactive configuration script:
   ```
   python3 createconfig.py
   ```

   This creates a `.env` file with your Philips Hue bridge credentials and GPS coordinates. You can also create `.env` manually — see `.env.example` for the required variables.

3. Start the application:
   ```
   python3 -m rain_hue.api
   ```

## API

- **GET /weather** — Returns the 12-hour weather forecast as JSON.
- **POST /weather** — Sets your lamp color based on the weather forecast. Pass `?lamp=Name` to target a specific lamp, or omit to use the default.

## Configuration

All configuration is read from environment variables (loaded from `.env` via python-dotenv):

| Variable       | Description                          |
|----------------|--------------------------------------|
| `HUE_URI`      | Philips Hue remote API URI           |
| `HUE_USERNAME` | Hue bridge username                  |
| `HUE_TOKEN`    | Hue OAuth bearer token               |
| `HUE_LAMP`     | Default lamp name                    |
| `LATITUDE`     | GPS latitude for weather forecast    |
| `LONGITUDE`    | GPS longitude for weather forecast   |

## Testing

```
pip install -r requirements-dev.txt
pytest
```
