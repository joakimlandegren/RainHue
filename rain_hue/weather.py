"""Weather fetching for RainHue v2 — Open-Meteo, no API key required.

Fetches hourly precipitation probability/amount/snowfall for the next 12h
plus today's max temperature, and condenses them into a small Forecast
dataclass consumed by the color-decision logic.
"""

import logging
import time
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
    temp_min_c: float  # today's minimum temperature

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

    Makes at most three attempts for transient failures, waiting 2s then 5s.
    Raises RuntimeError on permanent failure, exhausted retries or malformed response.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation_probability,precipitation,snowfall",
        "daily": "temperature_2m_max,temperature_2m_min",
        "timezone": timezone,
        "forecast_days": 1,
    }

    response = None
    for attempt in range(3):
        try:
            response = requests.get(_API_URL, params=params, timeout=timeout)
            response.raise_for_status()
            break
        except requests.RequestException as exc:
            retryable = isinstance(exc, (requests.Timeout, requests.ConnectionError)) or (
                isinstance(exc, requests.HTTPError)
                and exc.response is not None
                and exc.response.status_code in (429, 500, 502, 503, 504)
            )
            if not retryable or attempt == 2:
                logger.error("Failed to fetch weather data: %s", exc)
                raise RuntimeError(f"Failed to fetch weather data from Open-Meteo: {exc}") from exc
            delay = (2, 5)[attempt]
            logger.warning("Weather attempt %d/3 failed: %s; retrying in %ds", attempt + 1, exc, delay)
            time.sleep(delay)

    assert response is not None
    try:
        data = response.json()
        hourly = data["hourly"]
        probs = [p or 0 for p in hourly["precipitation_probability"]][:forecast_hours]
        precip = [p or 0 for p in hourly["precipitation"]][:forecast_hours]
        snowfall = [s or 0 for s in hourly["snowfall"]][:forecast_hours]
        temp_max = float(data["daily"]["temperature_2m_max"][0])
        temp_min = float(data["daily"]["temperature_2m_min"][0])
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
        temp_min_c=temp_min,
    )
    logger.info(
        "Forecast: %.2fmm precip, %.2fcm snow, %.0f%% max prob, %.1f°C max, %.1f°C min",
        forecast.total_precip_mm,
        forecast.total_snowfall_cm,
        forecast.max_precip_probability,
        forecast.temp_max_c,
        forecast.temp_min_c,
    )
    return forecast
