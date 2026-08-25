"""One weather -> lamp-color cycle, shared by the CLI and the HTTP API."""

import logging
from dataclasses import dataclass

from .colors import ColorDecision, decide_color
from .config import Config
from .hue import HueClient
from .weather import Forecast, fetch_forecast

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunResult:
    """Outcome of one cycle."""

    lamp: str
    decision: ColorDecision
    forecast: Forecast


def run_once(config: Config, lamp: str | None = None, hue_client: HueClient | None = None) -> RunResult:
    """Fetch the forecast, decide the color, apply it to the lamp.

    hue_client is injectable for tests. Raises RuntimeError/HueError on failure.
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

    return RunResult(lamp=target_lamp, decision=decision, forecast=forecast)
