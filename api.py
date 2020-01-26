#!/usr/bin/python
from RemoteBridge import RemoteBridge
import RainHue
import localconfig as cfg
from flask import Flask, jsonify, request
import logging

# initiate api
app = Flask(__name__)


def simple_app(start_response):
    status = '200 OK'
    response_headers = [('Content-Length', '13')]
    start_response(status, response_headers)
    return ['Hello World!\n']


@app.route("/weather", methods=["GET"])
def return_weather_conditions():
    weather = RainHue.get_weather()
    forecast = []
    for hour in range(0, 12):
        forecast.append(weather.get_hour(hour)["summary"])
    return jsonify(forecast)


@app.route("/weather", methods=["POST"])
def set_lamp_color_to_weather():
    if request.args.get('lamp'):
        lamp = request.args.get('lamp')
    else:
        lamp = cfg.selectedLamp
    RainHue.init_lamps(lamp, light_names)
    weather = RainHue.get_weather()
    weather_color = RainHue.set_weather_color(weather)
    RainHue.change_lamp_color(light_names, weather_color, lamp)
    return "{}'s lamp color was set to {}".format(lamp, weather_color)


if __name__ == '__main__':
    logging.basicConfig(filename='logs/info.log', filemode='a', level=logging.INFO)
    logging.info('Starting application *************************')
    # Connect to Philips Hue Bridge
    b = RemoteBridge(cfg.uri)
    b.connect()

    # Set array with lamp names
    light_names = RainHue.connect_to_hue_bridge_and_fetch_lamps()

    app.run(port=5000, debug=True)
