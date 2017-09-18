#!/usr/bin/python
from phue import Bridge
import requests
import json

#Connect to Philips Hue Bridge
b = Bridge('192.168.1.9')
b.connect()

#Set array with lamp names
light_names = b.get_light_objects('name')

#Fetch weather data for the next 12 hours
url = 'https://api.darksky.net/forecast/32d05244bc0a675ae12c7afc94f7ba2c/59.35512,17.908545'
response = requests.get(url)
data = response.json()

#Set Lamp colors
def setLampBlue():
        light_names['Barnhall'].brightness = 130
        light_names['Barnhall'].hue = 46920

def setLampYellow():
        light_names['Barnhall'].brightness = 254
        light_names['Barnhall'].hue = 10000

#Defines possible weather strings from API to trigger on
weatherTypes = ['Rain','Light Rain','Drizzle','Heavy Rain']

#Change lamp color based on weather forecast
light_names['Barnhall'].on = True
for i in range(0,12):
    if data['hourly']['data'][i]['summary'] in weatherTypes:
        setLampBlue()
        break
    else:
        setLampYellow()
        print data['hourly']['data'][i]['summary']
