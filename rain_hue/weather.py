"""Weather module using the Open-Meteo API.

Replaces the previous DarkSky/forecastiopy implementation with the free,
open Open-Meteo forecast API.  No API key is required.
"""

import logging

import requests


# WMO Weather interpretation codes (WW) mapped to human-readable summaries.
WMO_CODE_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm w/ slight hail",
    99: "Thunderstorm w/ heavy hail",
}

# WMO codes that indicate rain-like precipitation.
RAIN_CODES = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}

# WMO codes that indicate snow-like precipitation.
SNOW_CODES = {71, 73, 75, 77, 85, 86}

# Open-Meteo base URL.
_API_URL = "https://api.open-meteo.com/v1/forecast"


class Weather:
    """Fetch and interpret weather data from the Open-Meteo API.

    Parameters
    ----------
    latitude : str or float
        Latitude of the location to query.
    longitude : str or float
        Longitude of the location to query.
    """

    def __init__(self, latitude, longitude):
        self._latitude = str(latitude)
        self._longitude = str(longitude)
        self._weather_codes = None
        self._times = None
        self._forecast_color = None

    def __repr__(self):
        return f"Weather(lat={self._latitude}, lon={self._longitude}, codes={self._weather_codes!r})"

    def get_weather(self):
        """Fetch hourly weather-code data for the next 12 hours.

        Raises
        ------
        RuntimeError
            If the HTTP request fails or the response is malformed.
        """
        params = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "hourly": "weathercode",
            "forecast_hours": 12,
        }

        try:
            response = requests.get(_API_URL, params=params, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            logging.error("Failed to fetch weather data: %s", exc)
            raise RuntimeError(
                f"Failed to fetch weather data from Open-Meteo: {exc}"
            ) from exc

        try:
            data = response.json()
            hourly = data["hourly"]
            self._times = hourly["time"]
            self._weather_codes = hourly["weathercode"]
        except (KeyError, ValueError) as exc:
            logging.error("Malformed weather response: %s", exc)
            raise RuntimeError(
                f"Unexpected response format from Open-Meteo: {exc}"
            ) from exc

        if not self._weather_codes:
            raise RuntimeError("Open-Meteo returned no hourly weather data")

    def print_weather_conditions(self):
        """Return a list of 12 hourly weather summaries as strings.

        Returns
        -------
        list[str]
            Human-readable summary for each of the next 12 hours.

        Raises
        ------
        RuntimeError
            If ``get_weather()`` has not been called yet.
        """
        if self._weather_codes is None:
            raise RuntimeError(
                "No weather data available. Call get_weather() first."
            )

        forecast = []
        for hour in range(min(12, len(self._weather_codes))):
            code = self._weather_codes[hour]
            summary = WMO_CODE_DESCRIPTIONS.get(code, f"Unknown ({code})")
            forecast.append(summary)
        return forecast

    def set_weather_color(self, rain_color, snow_color, default_color):
        """Determine the lamp color based on the 12-hour forecast.

        Parameters
        ----------
        rain_color : list
            ``[brightness, hue, saturation]`` to use when rain is forecast.
        snow_color : list
            ``[brightness, hue, saturation]`` to use when snow is forecast.
        default_color : list
            ``[brightness, hue, saturation]`` to use otherwise.

        Returns
        -------
        list
            The selected ``[brightness, hue, saturation]`` color.

        Raises
        ------
        RuntimeError
            If ``get_weather()`` has not been called yet.
        """
        if self._weather_codes is None:
            raise RuntimeError(
                "No weather data available. Call get_weather() first."
            )

        for hour in range(min(12, len(self._weather_codes))):
            code = self._weather_codes[hour]
            if code in RAIN_CODES:
                self._forecast_color = rain_color
                return self._forecast_color
            if code in SNOW_CODES:
                self._forecast_color = snow_color
                return self._forecast_color
            logging.info(
                "Hour %d: %s",
                hour,
                WMO_CODE_DESCRIPTIONS.get(code, f"Unknown ({code})"),
            )

        self._forecast_color = default_color
        return self._forecast_color
