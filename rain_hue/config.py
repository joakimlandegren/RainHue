"""Configuration for RainHue v2.

All values come from environment variables (loaded from .env via
python-dotenv). Defaults match the locked color-logic requirements.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return float(raw)


@dataclass(frozen=True)
class HueConfig:
    """Philips Hue remote (cloud OAuth) settings."""

    client_id: str = os.environ.get("HUE_CLIENT_ID", "")
    client_secret: str = os.environ.get("HUE_CLIENT_SECRET", "")
    access_token: str = os.environ.get("HUE_TOKEN", "")
    refresh_token: str = os.environ.get("HUE_REFRESH_TOKEN", "")
    username: str = os.environ.get("HUE_USERNAME", "")  # bridge/whitelist user (application key)
    base_url: str = os.environ.get("HUE_URI", "https://api.meethue.com")
    default_lamp: str = os.environ.get("HUE_LAMP", "Desk Lamp")


@dataclass(frozen=True)
class Thresholds:
    """Color-decision thresholds (all overridable via env)."""

    # Rain: total precipitation (mm) over the next 12h that counts as "rain".
    rain_min_mm: float = _float("RAIN_MIN_MM", 0.1)
    # Rain beyond this total is "heavy" (deeper/more saturated blue).
    rain_heavy_mm: float = _float("RAIN_HEAVY_MM", 5.0)
    # Snow: total snowfall (cm) over the next 12h that counts as "snow".
    snow_min_cm: float = _float("SNOW_MIN_CM", 0.1)
    # Snow beyond this total is "heavy" (brighter cold-white).
    snow_heavy_cm: float = _float("SNOW_HEAVY_CM", 2.0)
    # Daily max temperature (°C) heat overrides.
    temp_orange_c: float = _float("TEMP_ORANGE_C", 25.0)  # > this and <= red -> orange
    temp_red_c: float = _float("TEMP_RED_C", 30.0)  # > this -> red
    # Daily min temperature (°C) strictly below this -> freezing cold-white.
    temp_freezing_c: float = _float("TEMP_FREEZING_C", 0.0)


@dataclass(frozen=True)
class Config:
    """Top-level application config."""

    latitude: float = _float("LATITUDE", 59.33)  # Stockholm
    longitude: float = _float("LONGITUDE", 18.07)
    timezone: str = os.environ.get("TIMEZONE", "Europe/Stockholm")
    forecast_hours: int = 12
    hue: HueConfig = HueConfig()
    thresholds: Thresholds = Thresholds()


def load() -> Config:
    """Return the application config (reads env at call time)."""
    return Config()
