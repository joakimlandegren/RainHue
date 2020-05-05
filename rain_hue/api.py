#!/usr/bin/python
from rain_hue.weather import Weather
from rain_hue.lamps import Lamps
import localconfig as cfg
from flask import Flask, request, jsonify
import logging

# initiate api
app = Flask(__name__)


def hue_weather_app(start_response):
    status = '200 OK'
    response_headers = [('Content-Length', '13')]
    start_response(status, response_headers)
    return ["Changes your lamp color's based on weather forecast !\n"]


@app.route("/weather", methods=["GET"])
def return_weather_as_json():
    weather.get_weather()
    forecast = weather.print_weather_conditions()
    return jsonify(forecast)


@app.route("/weather", methods=["POST"])
def set_lamp_color_by_weather():
    if request.args.get('lamp'):
        lamp = request.args.get('lamp')
    else:
        lamp = cfg.selectedLamp
    lamps.turn_on_lamp(lamp)
    weather.get_weather()
    weather_color = weather.set_weather_color()
    lamps.change_lamp_color(weather_color, lamp)
    return "{}'s lamp color was set to {}".format(lamp, weather_color)


if __name__ == '__main__':
    logging.basicConfig(filename='logs/info.log', filemode='a', level=logging.INFO)
    logging.info('Starting application *************************')
    lamps = Lamps()
    weather = Weather()


    app.run(port=5000, debug=True)
