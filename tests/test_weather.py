"""Tests for the Weather class (Open-Meteo based).

The Weather class:
- Accepts latitude and longitude in __init__
- Uses requests.get() to fetch from Open-Meteo API
- Stores hourly data (including weathercodes) internally
- set_weather_color(rain_color, snow_color, default_color) returns one color list
- Rain WMO codes: 51,53,55,61,63,65,80,81,82,95,96,99
- Snow WMO codes: 71,73,75,77,85,86
- print_weather_conditions() returns list of 12 human-readable summaries
"""

import pytest
from unittest.mock import patch, MagicMock
import requests

from rain_hue.weather import Weather


# --- WMO code reference for building test fixtures ---
# Clear/fair: 0, 1, 2, 3
# Rain codes: 51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99
# Snow codes: 71, 73, 75, 77, 85, 86

RAIN_COLOR = [254, 46920, 254]
SNOW_COLOR = [254, 0, 254]
DEFAULT_COLOR = [254, 12750, 254]


def _make_meteo_response(weathercodes):
    """Helper to build a mock Open-Meteo response with given weathercodes."""
    return {
        "latitude": 52.52,
        "longitude": 13.41,
        "hourly_units": {"time": "iso8601", "weathercode": "wmo code"},
        "hourly": {
            "time": [f"2026-02-20T{h:02d}:00" for h in range(len(weathercodes))],
            "weathercode": weathercodes,
        },
    }


def _setup_mock_get(mock_get, weathercodes):
    """Configure a mock requests.get to return a valid Open-Meteo response."""
    mock_response = MagicMock()
    mock_response.json.return_value = _make_meteo_response(weathercodes)
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    return mock_response


class TestGetWeather:
    """Tests for Weather.get_weather() which fetches data from Open-Meteo."""

    @patch("rain_hue.weather.requests.get")
    def test_get_weather_success(self, mock_get):
        """Mock requests.get, verify hourly data is stored on the Weather instance."""
        weathercodes = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
        _setup_mock_get(mock_get, weathercodes)

        weather = Weather(latitude=52.52, longitude=13.41)
        weather.get_weather()

        mock_get.assert_called_once()
        call_args = mock_get.call_args

        url = call_args[0][0]
        assert "api.open-meteo.com" in url

        params = call_args[1].get("params", {})
        assert str(params.get("latitude")) == "52.52"
        assert str(params.get("longitude")) == "13.41"
        assert params.get("hourly") == "weathercode"
        assert params.get("forecast_hours") == 12

        conditions = weather.print_weather_conditions()
        assert isinstance(conditions, list)
        assert len(conditions) == 12

    @patch("rain_hue.weather.requests.get")
    def test_get_weather_network_error(self, mock_get):
        """Mock requests.get to raise a network error, verify exception propagates."""
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Failed to establish connection"
        )

        weather = Weather(latitude=52.52, longitude=13.41)

        with pytest.raises((requests.exceptions.ConnectionError, RuntimeError)):
            weather.get_weather()


class TestSetWeatherColor:
    """Tests for Weather.set_weather_color() which maps forecast to a color."""

    @patch("rain_hue.weather.requests.get")
    def test_set_weather_color_rain(self, mock_get):
        """Provide forecast with rain WMO code 61 (moderate rain), verify rain color."""
        weathercodes = [61, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        _setup_mock_get(mock_get, weathercodes)

        weather = Weather(latitude=52.52, longitude=13.41)
        weather.get_weather()
        result = weather.set_weather_color(RAIN_COLOR, SNOW_COLOR, DEFAULT_COLOR)

        assert result == RAIN_COLOR

    @patch("rain_hue.weather.requests.get")
    def test_set_weather_color_snow(self, mock_get):
        """Provide forecast with snow WMO code 71 (light snow), verify snow color."""
        weathercodes = [0, 0, 71, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        _setup_mock_get(mock_get, weathercodes)

        weather = Weather(latitude=52.52, longitude=13.41)
        weather.get_weather()
        result = weather.set_weather_color(RAIN_COLOR, SNOW_COLOR, DEFAULT_COLOR)

        assert result == SNOW_COLOR

    @patch("rain_hue.weather.requests.get")
    def test_set_weather_color_clear(self, mock_get):
        """Provide forecast with only clear/fair codes, verify default color."""
        weathercodes = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]
        _setup_mock_get(mock_get, weathercodes)

        weather = Weather(latitude=52.52, longitude=13.41)
        weather.get_weather()
        result = weather.set_weather_color(RAIN_COLOR, SNOW_COLOR, DEFAULT_COLOR)

        assert result == DEFAULT_COLOR

    @patch("rain_hue.weather.requests.get")
    def test_set_weather_color_rain_priority(self, mock_get):
        """Rain at hour 3 and snow at hour 6: rain should win (detected first)."""
        weathercodes = [0, 0, 0, 63, 0, 0, 75, 0, 0, 0, 0, 0]
        _setup_mock_get(mock_get, weathercodes)

        weather = Weather(latitude=52.52, longitude=13.41)
        weather.get_weather()
        result = weather.set_weather_color(RAIN_COLOR, SNOW_COLOR, DEFAULT_COLOR)

        assert result == RAIN_COLOR


class TestPrintWeatherConditions:
    """Tests for Weather.print_weather_conditions()."""

    @patch("rain_hue.weather.requests.get")
    def test_print_weather_conditions(self, mock_get):
        """Verify returns list of 12 human-readable summaries."""
        weathercodes = [0, 1, 2, 3, 51, 61, 71, 80, 95, 85, 55, 99]
        _setup_mock_get(mock_get, weathercodes)

        weather = Weather(latitude=52.52, longitude=13.41)
        weather.get_weather()
        conditions = weather.print_weather_conditions()

        assert isinstance(conditions, list)
        assert len(conditions) == 12

        for i, condition in enumerate(conditions):
            assert isinstance(condition, str), (
                f"Hour {i}: expected string, got {type(condition)}"
            )
            assert len(condition) > 0, f"Hour {i}: summary should not be empty"

        assert conditions[0] == "Clear sky"
        assert conditions[1] == "Mainly clear"
        assert conditions[2] == "Partly cloudy"
        assert conditions[3] == "Overcast"
