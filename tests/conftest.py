"""Shared pytest fixtures for RainHue test suite.

These fixtures assume the post-Phase-4 architecture:
- Weather class accepts latitude/longitude, uses Open-Meteo API
- Lamps class accepts a token parameter
- create_app() factory stores lamps and weather on app.config
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_weather_response():
    """Return a sample Open-Meteo API response with hourly weathercodes.

    The response mimics the structure returned by:
    https://api.open-meteo.com/v1/forecast?latitude=...&longitude=...&hourly=weathercode&forecast_hours=12
    """
    return {
        "latitude": 52.52,
        "longitude": 13.41,
        "generationtime_ms": 0.5,
        "utc_offset_seconds": 0,
        "timezone": "GMT",
        "timezone_abbreviation": "GMT",
        "elevation": 38.0,
        "hourly_units": {
            "time": "iso8601",
            "weathercode": "wmo code"
        },
        "hourly": {
            "time": [
                "2026-02-20T00:00", "2026-02-20T01:00",
                "2026-02-20T02:00", "2026-02-20T03:00",
                "2026-02-20T04:00", "2026-02-20T05:00",
                "2026-02-20T06:00", "2026-02-20T07:00",
                "2026-02-20T08:00", "2026-02-20T09:00",
                "2026-02-20T10:00", "2026-02-20T11:00",
            ],
            "weathercode": [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
        }
    }


@pytest.fixture
def app():
    """Create a Flask test app with mocked Lamps and Weather dependencies.

    Uses create_app() factory from rain_hue.api, but replaces the real
    Lamps and Weather instances with mocks so tests don't hit external APIs.
    """
    mock_lamps = MagicMock()
    mock_lamps.get_available_lamps.return_value = ["Desk Lamp", "Living Room"]
    mock_lamps.turn_on_lamp.return_value = None
    mock_lamps.change_lamp_color.return_value = None

    mock_weather = MagicMock()
    mock_weather.get_weather.return_value = None
    mock_weather.print_weather_conditions.return_value = [
        "Clear sky", "Mainly clear", "Partly cloudy", "Overcast",
        "Clear sky", "Mainly clear", "Partly cloudy", "Overcast",
        "Clear sky", "Mainly clear", "Partly cloudy", "Overcast",
    ]
    mock_weather.set_weather_color.return_value = [254, 46920, 254]

    with patch("rain_hue.api.Lamps", return_value=mock_lamps), \
         patch("rain_hue.api.Weather", return_value=mock_weather):
        from rain_hue.api import create_app
        test_app = create_app()

    test_app.config["TESTING"] = True
    # Ensure the mocks are accessible on app.config for assertions
    test_app.config["lamps"] = mock_lamps
    test_app.config["weather"] = mock_weather

    yield test_app


@pytest.fixture
def client(app):
    """Flask test client for making requests to the app."""
    return app.test_client()
