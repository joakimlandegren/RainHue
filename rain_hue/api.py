"""HTTP API for RainHue v2 — small Flask surface for manual remote triggers."""

import logging

from flask import Flask, jsonify, request

from .config import load
from .core import run_once
from .weather import fetch_forecast

logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config["rain_hue_config"] = load()

    @app.post("/set-color")
    def set_color():
        """Run one weather->color cycle. Optional ?lamp=Name override."""
        config = app.config["rain_hue_config"]
        lamp = request.args.get("lamp")
        try:
            result = run_once(config, lamp=lamp)
        except RuntimeError as exc:
            logger.exception("set-color failed")
            return jsonify({"error": str(exc)}), 502
        return jsonify(
            {
                "lamp": result.lamp,
                "reason": result.decision.reason,
                "xy": list(result.decision.xy),
                "brightness": result.decision.brightness,
                "forecast": {
                    "total_precip_mm": result.forecast.total_precip_mm,
                    "total_snowfall_cm": result.forecast.total_snowfall_cm,
                    "max_precip_probability": result.forecast.max_precip_probability,
                    "temp_max_c": result.forecast.temp_max_c,
                },
            }
        )

    @app.get("/weather")
    def weather():
        """Return the condensed 12h forecast (no lamp changes)."""
        config = app.config["rain_hue_config"]
        try:
            f = fetch_forecast(config.latitude, config.longitude, config.timezone, config.forecast_hours)
        except RuntimeError as exc:
            logger.exception("weather fetch failed")
            return jsonify({"error": str(exc)}), 502
        return jsonify(
            {
                "total_precip_mm": f.total_precip_mm,
                "total_snowfall_cm": f.total_snowfall_cm,
                "max_precip_probability": f.max_precip_probability,
                "temp_max_c": f.temp_max_c,
            }
        )

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_app().run(host="0.0.0.0", port=5000)
