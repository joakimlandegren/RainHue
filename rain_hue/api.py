#!/usr/bin/python
import os
from rain_hue.weather import Weather
from rain_hue.lamps import Lamps
from rain_hue import config as cfg
from flask import Flask, request, jsonify
import logging


def create_app():
    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(filename='logs/info.log', filemode='a', level=logging.INFO)
    logging.info('Starting application *************************')

    app = Flask(__name__)

    app.config['lamps'] = Lamps(token=cfg.hue_token)
    app.config['weather'] = Weather(cfg.coordinates[0], cfg.coordinates[1])

    @app.route("/weather", methods=["GET"])
    def return_weather_as_json():
        """Return 12-hour weather forecast as JSON."""
        weather = app.config['weather']
        try:
            weather.get_weather()
            forecast = weather.print_weather_conditions()
            return jsonify(forecast)
        except Exception as e:
            return jsonify({"error": "Failed to fetch weather data", "details": str(e)}), 502

    @app.route("/weather", methods=["POST"])
    def set_lamp_color_by_weather():
        """Set lamp color based on weather forecast."""
        lamps = app.config['lamps']
        weather = app.config['weather']

        lamp = request.args.get('lamp', cfg.selectedLamp)

        # Validate lamp name exists
        available_lamps = list(lamps.get_available_lamps())
        if lamp not in available_lamps:
            return jsonify({
                "error": f"Lamp '{lamp}' not found",
                "available_lamps": available_lamps
            }), 404

        try:
            lamps.turn_on_lamp(lamp)
            weather.get_weather()
            weather_color = weather.set_weather_color(cfg.rainColor, cfg.snowColor, cfg.defaultColor)
            lamps.change_lamp_color(weather_color, lamp)
            return jsonify({
                "lamp": lamp,
                "color": {"brightness": weather_color[0], "hue": weather_color[1], "saturation": weather_color[2]}
            })
        except KeyError as e:
            return jsonify({"error": f"Lamp '{lamp}' not found", "details": str(e)}), 404
        except Exception as e:
            return jsonify({"error": "Failed to set lamp color", "details": str(e)}), 502

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(port=5000)
