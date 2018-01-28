#!/usr/bin/python
from phue import Bridge
import localconfig as cfg
from forecastiopy import *

# Connect to Philips Hue Bridge
b = Bridge(cfg.bridge)
b.connect()

# Set array with lamp names
light_names = b.get_light_objects('name')

# Get forecast data
fio = ForecastIO.ForecastIO(cfg.API_KEY, units=ForecastIO.ForecastIO.UNITS_SI, lang=ForecastIO.ForecastIO.LANG_ENGLISH, latitude = cfg.coordinates[0], longitude = cfg.coordinates[1])

# Defines possible weather strings from API to trigger on
rain_weather_types = ['Rain','Light Rain','Drizzle','Heavy Rain','Possible Light Rain']
snow_weather_types = ['Snow','Hail','Heavy Snow','Light Snow','Possible Light Snow and Breezy','Possible Light Snow','Light Snow and Breezy']

# Turn lamp on and Set Lamp colors
lamp = cfg.selectedLamp
light_names[lamp].on = True

def setLampColor(lampColor):
    light_names[lamp].brightness = lampColor[0]
    light_names[lamp].hue = lampColor[1]
    light_names[lamp].saturation = lampColor[2]

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