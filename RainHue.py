#!/usr/bin/python
import logging

from RemoteBridge import RemoteBridge
import localconfig as cfg
from forecastiopy import *


def connect_to_hue_bridge_and_fetch_lamps():
    b = RemoteBridge(cfg.uri, cfg.username, )
    light_names = b.get_light_objects('name')
    return light_names


def init_lamps(lamp, light_names):
    # Turn lamp on and Set Lamp colors
    light_names[lamp].on = True


def change_lamp_color(light_names, lamp_color, lamp):
    light_names[lamp].brightness = lamp_color[0]
    light_names[lamp].hue = lamp_color[1]
    light_names[lamp].saturation = lamp_color[2]
    logging.info('Color of %s set to %s, %s, %s', lamp, lamp_color[0], lamp_color[1], lamp_color[2])


def get_weather():
    fio = ForecastIO.ForecastIO(cfg.API_KEY, units=ForecastIO.ForecastIO.UNITS_SI,
                                lang=ForecastIO.ForecastIO.LANG_ENGLISH, latitude=cfg.coordinates[0],
                                longitude=cfg.coordinates[1])
    try:
        fio.has_hourly()
        hourly_weather = FIOHourly.FIOHourly(fio)
        return hourly_weather
    except Exception:
        logging.error('No Hourly data')


# Get weather forecast for next 12 hours and set lamp color to blue if it will rain
def set_weather_color(hourly_weather):
    # Defines possible weather strings from API to trigger on
    rain_types = ['Rain', 'Light Rain', 'Drizzle', 'Heavy Rain']
    snow_types = ['Snow', 'Hail', 'Heavy Snow', 'Light Snow']

    for hour in range(0, 12):
        if hourly_weather.get_hour(hour)["summary"] in rain_types:
            color = cfg.rainColor
            break
        elif hourly_weather.get_hour(hour)["summary"] in snow_types:
            color = cfg.snowColor
            break
        else:
            logging.info(hourly_weather.get_hour(hour)["summary"])
            print(hourly_weather.get_hour(hour)["summary"])
        color = cfg.defaultColor
    return color
