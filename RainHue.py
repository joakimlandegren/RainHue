#!/usr/bin/python
from phue import Bridge
import requests
import json
import localconfig as cfg

#Connect to Philips Hue Bridge
bridge = cfg.bridge
b = Bridge(bridge)
b.connect()

#Set array with lamp names
light_names = b.get_light_objects('name')

#Fetch weather data for the next 12 hours
url = 'https://api.darksky.net/forecast/32d05244bc0a675ae12c7afc94f7ba2c/59.35512,17.908545'
response = requests.get(url)
data = response.json()

#Set Lamp colors
lamp = cfg.selectedLamp
def setLampBlue():
        light_names[lamp].brightness = 130
        light_names[lamp].hue = 46920

def setLampYellow():
        light_names[lamp].brightness = 254
        light_names[lamp].hue = 10000

#Defines possible weather strings from API to trigger on
weatherTypes = ['Rain','Light Rain','Drizzle','Heavy Rain']

#Change lamp color based on weather forecast
light_names[lamp].on = True
for i in range(0,12):
    if data['hourly']['data'][i]['summary'] in weatherTypes:
        setLampBlue()
        break
    else:
        setLampYellow()
        print data['hourly']['data'][i]['summary']
