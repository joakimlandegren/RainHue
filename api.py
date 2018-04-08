#!/usr/bin/python
from phue import Bridge
import localconfig as cfg
from forecastiopy import *
from flask import Flask, jsonify

# initiate api
app = Flask(__name__)

# Select lamp
lamp = cfg.selectedLamp


@app.route("/weather", methods=["GET"])
def return_weather_conditions():
    return jsonify(get_weather_conditions_from_darksky())


@app.route("/weather", methods=["POST"])
def set_lamp_color_to_weather():
    light_names[lamp].on = True

    weather = get_weather_conditions_from_darksky()
    forecast = weather.pop()
    if forecast == "Rain":
        set_lamp_color(cfg.rainColor)
    elif forecast == "Snow":
        set_lamp_color(cfg.snowColor)
    else:
        set_lamp_color(cfg.defaultColor)
    return forecast


def set_lamp_color(lampcolor):
    light_names[lamp].brightness = lampcolor[0]
    light_names[lamp].hue = lampcolor[1]
    light_names[lamp].saturation = lampcolor[2]


def get_weather_conditions_from_darksky():
    weather = []
    if fio.has_hourly() is True:
        hourly = FIOHourly.FIOHourly(fio)
        for hour in range(0, 12):
            if hourly.get_hour(hour)["summary"] in rain_weather_types:
                weather = ["Rain"]
                return weather
            if hourly.get_hour(hour)["summary"] in snow_weather_types:
                weather = ["Snow"]
                return weather
            else:
                weather.append(hourly.get_hour(hour)["summary"])
                print(hourly.get_hour(hour)["summary"])
    else:
        return 'No Hourly data'
    return weather


if __name__ == '__main__':
    # Connect to Philips Hue Bridge
    b = Bridge(cfg.bridge)
    b.connect()

    # Set array with lamp names
    light_names = b.get_light_objects('name')

    # Get forecast data
    fio = ForecastIO.ForecastIO(cfg.API_KEY, units=ForecastIO.ForecastIO.UNITS_SI,
                                lang=ForecastIO.ForecastIO.LANG_ENGLISH, latitude=cfg.coordinates[0],
                                longitude=cfg.coordinates[1])

    # Defines possible weather strings from API to trigger on
    rain_weather_types = ['Rain', 'Light Rain', 'Drizzle', 'Heavy Rain', 'Possible Light Rain']
    snow_weather_types = ['Snow', 'Hail', 'Heavy Snow', 'Light Snow', 'Possible Light Snow and Breezy',
                          'Possible Light Snow', 'Light Snow and Breezy']

    app.run(port=5000, debug=True)