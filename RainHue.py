#!/usr/bin/python
from phue import Bridge
import localconfig as cfg
from forecastiopy import *

def connect_to_hue_bridge_and_fetch_lamps():
    b = Bridge(cfg.bridge)
    b.connect()
    global light_names
    light_names = b.get_light_objects('name')

def init_lamps(lamp):
    #Turn lamp on and Set Lamp colors
    light_names[lamp].on = True

def change_lamp_color(lampColor, lamp):
    light_names[lamp].brightness = lampColor[0]
    light_names[lamp].hue = lampColor[1]
    light_names[lamp].saturation = lampColor[2]

def get_weather():
    fio = ForecastIO.ForecastIO(cfg.API_KEY, units=ForecastIO.ForecastIO.UNITS_SI,
                                lang=ForecastIO.ForecastIO.LANG_ENGLISH, latitude=cfg.coordinates[0],
                                longitude=cfg.coordinates[1])
    if fio.has_hourly() is True:
        hourly_weather = FIOHourly.FIOHourly(fio)
        return hourly_weather
    else:
        return 'No Hourly data'


#Get weather forecast for next 12 hours and set lamp color to blue if it will rain
def set_weather_color(hourly_weather):
    # Defines possible weather strings from API to trigger on
    rainTypes = ['Rain', 'Light Rain', 'Drizzle', 'Heavy Rain']
    snowTypes = ['Snow', 'Hail', 'Heavy Snow', 'Light Snow']

    for hour in range(0, 12):
            if hourly_weather.get_hour(hour)["summary"] in rainTypes:
                color = cfg.rainColor
                break
            elif hourly_weather.get_hour(hour)["summary"] in snowTypes:
                color = cfg.snowColor
                break
            else:
                print(hourly_weather.get_hour(hour)["summary"])
            color = cfg.defaultColor
    return color

def main():
    connect_to_hue_bridge_and_fetch_lamps()
    lamp = cfg.selectedLamp
    init_lamps(lamp)
    weather = get_weather()
    weather_color = set_weather_color(weather)
    change_lamp_color(weather_color, lamp)

main()
