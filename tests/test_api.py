"""Integration tests for Flask API routes.

After all phases are applied, the API has:
- GET  /weather  -> returns 12-hour forecast as JSON list, or 502 on failure
- POST /weather  -> sets lamp color by weather, returns JSON with lamp/color info
                    ?lamp=<name> selects a lamp; omit for config default
                    Returns 404 if lamp not found, 502 on weather API failure

The Weather and Lamps classes are fully mocked via the conftest.py fixtures.
"""

from unittest.mock import patch

import pytest


class TestGetWeather:
    """Tests for GET /weather endpoint."""

    def test_get_weather_returns_json(self, client, app):
        """GET /weather returns 200 with JSON list of 12 weather summaries."""
        response = client.get("/weather")

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 12

        for item in data:
            assert isinstance(item, str)

        mock_weather = app.config["weather"]
        mock_weather.get_weather.assert_called_once()
        mock_weather.print_weather_conditions.assert_called_once()

    def test_get_weather_api_failure(self, client, app):
        """When weather fetch fails, GET /weather returns 502 with error JSON."""
        mock_weather = app.config["weather"]
        mock_weather.get_weather.side_effect = RuntimeError(
            "Failed to fetch weather data from Open-Meteo"
        )

        response = client.get("/weather")

        assert response.status_code == 502
        data = response.get_json()
        assert "error" in data


class TestPostWeather:
    """Tests for POST /weather endpoint."""

    def test_post_weather_sets_color(self, client, app):
        """POST /weather returns 200 with lamp and color info."""
        response = client.post("/weather?lamp=Desk%20Lamp")

        assert response.status_code == 200
        data = response.get_json()

        assert "lamp" in data
        assert data["lamp"] == "Desk Lamp"
        assert "color" in data

        mock_lamps = app.config["lamps"]
        mock_lamps.turn_on_lamp.assert_called()
        mock_lamps.change_lamp_color.assert_called()

    def test_post_weather_invalid_lamp(self, client, app):
        """POST /weather?lamp=nonexistent returns 404."""
        response = client.post("/weather?lamp=nonexistent")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    def test_post_weather_default_lamp(self, client, app):
        """POST /weather with no lamp param uses config default lamp."""
        with patch("rain_hue.api.cfg") as mock_cfg:
            mock_cfg.selectedLamp = "Desk Lamp"
            mock_cfg.rainColor = [120, 45000, 254]
            mock_cfg.snowColor = [120, 25000, 254]
            mock_cfg.defaultColor = [254, 10000, 0]

            response = client.post("/weather")

        assert response.status_code == 200
        data = response.get_json()

        assert "lamp" in data
        assert data["lamp"] == "Desk Lamp"
