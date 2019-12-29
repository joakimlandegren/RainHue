#!/usr/bin/python
import json
import logging
import os
import platform
import requests

from phue import Bridge, USER_HOME, logger, Light, is_string
import localconfig as cfg
from forecastiopy import *


class Bridge(object):

    def __init__(self, uri=None, username=None, config_file_path=None):
        """ Initialization function.

        Parameters:
        ------------
        Remote API URI : string
        username : string, optional

        """

        if config_file_path is not None:
            self.config_file_path = config_file_path
        elif os.getenv(USER_HOME) is not None and os.access(os.getenv(USER_HOME), os.W_OK):
            self.config_file_path = os.path.join(os.getenv(USER_HOME), '.python_hue')
        elif 'iPad' in platform.machine() or 'iPhone' in platform.machine() or 'iPad' in platform.machine():
            self.config_file_path = os.path.join(os.getenv(USER_HOME), 'Documents', '.python_hue')
        else:
            self.config_file_path = os.path.join(os.getcwd(), '.python_hue')

        self.uri = uri
        self.username = username
        self.lights_by_id = {}
        self.lights_by_name = {}
        self.sensors_by_id = {}
        self.sensors_by_name = {}
        self._name = None

        self.connect()

    def connect(self):
        """ Connect to the Hue bridge """
        logger.info('Attempting to connect to the bridge...')
        # If the uri and username were provided at class init
        if self.uri is not None and self.username is not None:
            logger.info('Using uri: ' + self.uri)
            logger.info('Using username: ' + self.username)
            return

    def get_light_objects(self, mode='list'):
        """Returns a collection containing the lights, either by name or id (use 'id' or 'name' as the mode)
        The returned collection can be either a list (default), or a dict.
        Set mode='id' for a dict by light ID, or mode='name' for a dict by light name.   """
        auth_token = 'gunDxsjsBiOxDAGeJKIWm7UtJOeE'
        header = {
            'Authorization': 'Bearer ' + auth_token,
            'Content-type': 'application/x-www-form-urlencoded'
        }

        if self.lights_by_id == {}:
            lights = requests.get(self.uri + 'bridge/' + self.username + '/lights/', headers=header)
            for light in lights:
                try:
                    self.lights_by_id[int(light)] = Light(self, int(light))
                except ValueError:
                    pass
                try:
                    self.lights_by_name[lights[light][
                        'name']] = self.lights_by_id[int(light)]
                except ValueError:
                    pass
        if mode == 'id':
            return self.lights_by_id
        if mode == 'name':
            return self.lights_by_name
        if mode == 'list':
            return self.lights_by_id.values()



def connect_to_hue_bridge_and_fetch_lamps():
    b = Bridge(cfg.API_BASE_URI, cfg.USER_NAME)
    global light_names
    light_names = b.get_light_objects('name')

def init_lamps(lamp):
    #Turn lamp on and Set Lamp colors
    light_names[lamp].on = True

def change_lamp_color(lampColor, lamp):
    light_names[lamp].brightness = lampColor[0]
    light_names[lamp].hue = lampColor[1]
    light_names[lamp].saturation = lampColor[2]
    logging.info('Color of %s set to %s, %s, %s', lamp, lampColor[0], lampColor[1], lampColor[2])

def get_weather():
    fio = ForecastIO.ForecastIO(cfg.API_KEY, units=ForecastIO.ForecastIO.UNITS_SI,
                                lang=ForecastIO.ForecastIO.LANG_ENGLISH, latitude=cfg.coordinates[0],
                                longitude=cfg.coordinates[1])
    try:
        fio.has_hourly()
        hourly_weather = FIOHourly.FIOHourly(fio)
        return hourly_weather
    except Exception:
        logging.warning('No Hourly data')


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
                logging.info(hourly_weather.get_hour(hour)["summary"])
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
