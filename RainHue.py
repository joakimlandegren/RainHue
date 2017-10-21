#!/usr/bin/python
from phue import Bridge
import requests
import json
import localconfig as cfg
from forecastiopy import *

#Connect to Philips Hue Bridge
b = Bridge(cfg.bridge)
b.connect()

#Set array with lamp names
light_names = b.get_light_objects('name')

#Get forecast data
fio = ForecastIO.ForecastIO(cfg.API_KEY, units=ForecastIO.ForecastIO.UNITS_SI, lang=ForecastIO.ForecastIO.LANG_ENGLISH, latitude = cfg.coordinates[0], longitude = cfg.coordinates[1])

#Defines possible weather strings from API to trigger on
rainTypes = ['Rain','Light Rain','Drizzle','Heavy Rain']
snowTypes = ['Snow','Hail','Heavy Snow','Light Snow']

#Turn lamp on and Set Lamp colors
lamp = cfg.selectedLamp
light_names[lamp].on = True

def setLampColor(lampColor):
        light_names[lamp].brightness = lampColor[0]
        light_names[lamp].hue = lampColor[1]
        light_names[lamp].saturation = lampColor[2]

#Get weather forecast for next 12 hours and set lamp color to blue if it will rain
if fio.has_hourly() is True:
	hourly = FIOHourly.FIOHourly(fio)
	for hour in range(0, 12):
            if hourly.get_hour(hour)["summary"] in rainTypes:
                setLampColor(cfg.rainColor)
                break
            elif hourly.get_hour(hour)["summary"] in snowTypes:
                setLampColor(cfg.snowColor)
                break
            else:
                setLampColor(cfg.defaultColor)
                print hourly.get_hour(hour)["summary"]
else:
	print 'No Hourly data'
