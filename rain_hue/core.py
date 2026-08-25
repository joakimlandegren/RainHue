"""One weather -> lamp-color cycle, shared by the CLI and the HTTP API."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from .colors import ColorDecision, decide_color
from .config import Config
from .hue import HueClient
from .state import write_state
from .weather import Forecast, fetch_forecast

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunResult:
    """Outcome of one cycle."""

    lamp: str
    decision: ColorDecision
    forecast: Forecast | None


def serialize_decision(decision: ColorDecision, lamp: str, forecast: Forecast | None = None) -> dict:
    """JSON-serializable record of a decision (state file + API responses)."""
    return {
        "lamp": lamp,
        "reason": decision.reason,
        "xy": list(decision.xy),
        "brightness": decision.brightness,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "forecast": {
            "total_precip_mm": forecast.total_precip_mm,
            "total_snowfall_cm": forecast.total_snowfall_cm,
            "max_precip_probability": forecast.max_precip_probability,
            "temp_max_c": forecast.temp_max_c,
        }
        if forecast
        else None,
    }


def run_once(config: Config, lamp: str | None = None, hue_client: HueClient | None = None) -> RunResult:
    """Fetch the forecast, decide the color, apply it to the lamp.

    Writes the decision to the state file so every process (cron CLI, API)
    shares the same last-decision record. hue_client is injectable for tests.
    Raises RuntimeError/HueError on failure.
    """
    target_lamp = lamp or config.hue.default_lamp

    forecast = fetch_forecast(
        config.latitude, config.longitude, config.timezone, config.forecast_hours
    )
    decision = decide_color(forecast, config.thresholds)
    logger.info("Decision for '%s': %s", target_lamp, decision.reason)

    client = hue_client or HueClient(config.hue)
    light_id = client.find_light_id(target_lamp)
    client.set_color(light_id, decision.xy, decision.brightness)

    write_state(serialize_decision(decision, target_lamp, forecast))

    return RunResult(lamp=target_lamp, decision=decision, forecast=forecast)
