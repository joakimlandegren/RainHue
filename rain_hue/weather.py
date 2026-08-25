"""Weather fetching for RainHue v2 — Open-Meteo, no API key required.

Fetches hourly precipitation probability/amount/snowfall for the next 12h
plus today's max temperature, and condenses them into a small Forecast
dataclass consumed by the color-decision logic.
"""

import logging
from dataclasses import dataclass

import requests

_API_URL = "https://api.open-meteo.com/v1/forecast"

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Forecast:
    """Condensed 12h forecast used by the color decision."""

    total_precip_mm: float  # total precipitation (rain + showers) over next 12h
    total_snowfall_cm: float  # total snowfall over next 12h
    max_precip_probability: float  # max hourly precipitation probability (0-100)
    temp_max_c: float  # today's maximum temperature

    @property
    def has_rain(self) -> bool:
        return self.total_precip_mm > 0 and self.total_snowfall_cm <= 0

    @property
    def has_snow(self) -> bool:
        return self.total_snowfall_cm > 0


def fetch_forecast(
    latitude: float,
    longitude: float,
    timezone: str = "Europe/Stockholm",
    forecast_hours: int = 12,
    timeout: float = 15.0,
) -> Forecast:
    """Fetch and condense the forecast from Open-Meteo.

    Raises RuntimeError on HTTP failure or malformed response.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation_probability,precipitation,snowfall",
        "daily": "temperature_2m_max",
        "timezone": timezone,
        "forecast_days": 1,
    }

    try:
        response = requests.get(_API_URL, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Failed to fetch weather data: %s", exc)
        raise RuntimeError(f"Failed to fetch weather data from Open-Meteo: {exc}") from exc

    try:
        data = response.json()
        hourly = data["hourly"]
        probs = [p or 0 for p in hourly["precipitation_probability"]][:forecast_hours]
        precip = [p or 0 for p in hourly["precipitation"]][:forecast_hours]
        snowfall = [s or 0 for s in hourly["snowfall"]][:forecast_hours]
        temp_max = float(data["daily"]["temperature_2m_max"][0])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        logger.error("Malformed weather response: %s", exc)
        raise RuntimeError(f"Unexpected response format from Open-Meteo: {exc}") from exc

    if not precip:
        raise RuntimeError("Open-Meteo returned no hourly precipitation data")

    forecast = Forecast(
        total_precip_mm=round(sum(precip), 2),
        total_snowfall_cm=round(sum(snowfall), 2),
        max_precip_probability=max(probs) if probs else 0.0,
        temp_max_c=temp_max,
    )
    logger.info(
        "Forecast: %.2fmm precip, %.2fcm snow, %.0f%% max prob, %.1f°C max",
        forecast.total_precip_mm,
        forecast.total_snowfall_cm,
        forecast.max_precip_probability,
        forecast.temp_max_c,
    )
    return forecast
