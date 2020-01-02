#!/usr/bin/python
import json
import logging
import os
import platform
import socket

import requests

from phue import Bridge, USER_HOME, logger, Light, is_string, PY3K, PhueRequestTimeout
import localconfig as cfg
from forecastiopy import *

auth_token = 'hauhAMjlqHmUb8t8LgILiNu8zaG8'
header_get = {
    'Authorization': 'Bearer ' + auth_token,
    'Content-type': 'application/x-www-form-urlencoded'
}
header_put = {
    'Authorization': 'Bearer ' + auth_token,
    'Content-type': 'application/json'
}


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

        if self.lights_by_id == {}:
            lights = self.request('GET', self.uri + 'bridge/' + self.username + '/lights/', header_get)
            for light in lights:
                self.lights_by_id[int(light)] = Light(self, int(light))
                self.lights_by_name[lights[light]['name']] = self.lights_by_id[int(light)]
        if mode == 'id':
            return self.lights_by_id
        if mode == 'name':
            return self.lights_by_name
        if mode == 'list':
            return self.lights_by_id.values()

    def request(self, mode=None, address=None, header=None, data=None): #TODO Add support for sending parameters in request
        """ Utility function for HTTP GET/PUT requests for the API"""
        try:
            if mode == 'GET':
                response = requests.get(address, headers=header, params=data)
            elif mode == 'DELETE':
                response = requests.delete(address, headers=header, params=data)
            elif mode == 'PUT':
                response = requests.put(address, headers=header, params=data)
            elif mode == 'POST':
                response = requests.post(address, headers=header, params=data)
            else:
                raise ConnectionError('No mode provided for the request method')
            logger.debug("{0} {1} {2}".format(mode, address, str(data)))

        except socket.timeout:
            error = "{} Request to {}{} timed out.".format(mode, self.uri, address)

            logger.exception(error)
            raise PhueRequestTimeout(None, error)

        if PY3K:
            logger.info(type(json.dumps(response.text)))
            logger.debug(json.loads(response.text))
            return json.loads(response.text)
        else:
            logger.debug(response)
            return json.loads(response)

    @property
    def lights(self):
        """ Access lights as a list """
        return self.get_light_objects()

    def get_api(self):
        """ Returns the full api dictionary """
        return self.request('GET', '/api/' + self.username)

    def get_light(self, light_id=None, parameter=None):
        """ Gets state by light_id and parameter"""

        if is_string(light_id):
            light_id = self.get_light_id_by_name(light_id)
        if light_id is None:
            return self.request('GET', '/api/' + self.username + '/lights/')
        state = self.request(
            'GET', '/api/' + self.username + '/lights/' + str(light_id))
        if parameter is None:
            return state
        if parameter == 'name':
            return state[parameter]
        else:
            try:
                return state['state'][parameter]
            except KeyError as e:
                raise KeyError(
                    'Not a valid key, parameter %s is not associated with light %s)'
                    % (parameter, light_id))

    def set_light(self, light_id, parameter, value=None, transitiontime=None):
        """ Adjust properties of one or more lights.

        light_id can be a single lamp or an array of lamps
        parameters: 'on' : True|False , 'bri' : 0-254, 'sat' : 0-254, 'ct': 154-500

        transitiontime : in **deciseconds**, time for this transition to take place
                         Note that transitiontime only applies to *this* light
                         command, it is not saved as a setting for use in the future!
                         Use the Light class' transitiontime attribute if you want
                         persistent time settings.

        """
        if isinstance(parameter, dict):
            data = parameter
        else:
            data = {parameter: value}

        if transitiontime is not None:
            data['transitiontime'] = int(round(
                transitiontime))  # must be int for request format

        light_id_array = light_id
        if isinstance(light_id, int) or is_string(light_id):
            light_id_array = [light_id]
        result = []
        for light in light_id_array:
            logger.info(str(data))
            if parameter == 'name':
                result.append(self.request('PUT', self.uri + 'bridge/' + self.username + '/lights/' + str(converted_light) + '/state', header_put, json.dumps(data)))
                logging.debug(self.request('PUT', self.uri + 'bridge/' + self.username + '/lights/' + str(converted_light) + '/state', header_put, json.dumps(data)))
            else:
                if is_string(light):
                    converted_light = self.get_light_id_by_name(light)
                else:
                    converted_light = light
                result.append(self.request('PUT', self.uri + 'bridge/' + self.username + '/lights/' + str(converted_light) + '/state', header_put, json.dumps(data)))
                logging.debug(self.request('PUT', self.uri + 'bridge/' + self.username + '/lights/' + str(converted_light) + '/state', header_put, json.dumps(data)))
            # if 'error' in list(result[-1][0].keys()):
            #     logger.warn("ERROR: {0} for light {1}".format(
            #         result[-1][0]['error']['description'], light))

        logger.debug(result)
        return result


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
    logging.basicConfig(filename="logs/info.log", filemode="a", level=logging.DEBUG)
    logging.debug('Starting application ********************')
    connect_to_hue_bridge_and_fetch_lamps()
    lamp = cfg.selectedLamp
    init_lamps(lamp)
    weather = get_weather()
    weather_color = set_weather_color(weather)
    change_lamp_color(weather_color, lamp)

main()
