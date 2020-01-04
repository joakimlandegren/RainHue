import json
import logging
import os
import platform
import socket

import requests
from phue import Bridge, USER_HOME, Light, is_string, PhueRequestTimeout


class RemoteBridge(Bridge):

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
        logging.info('Attempting to connect to the bridge...')
        # If the uri and username were provided at class init
        if self.uri is not None and self.username is not None:
            logging.info('Using uri: ' + self.uri)
            logging.info('Using username: ' + self.username)
            return

    def get_light_objects(self, mode='list'):
        """Returns a collection containing the lights, either by name or id (use 'id' or 'name' as the mode)
        The returned collection can be either a list (default), or a dict.
        Set mode='id' for a dict by light ID, or mode='name' for a dict by light name.   """

        if self.lights_by_id == {}:
            lights = self.request('GET', self.uri + 'bridge/' + self.username + '/lights/')
            for light in lights:
                self.lights_by_id[int(light)] = Light(self, int(light))
                self.lights_by_name[lights[light]['name']] = self.lights_by_id[int(light)]
        if mode == 'id':
            return self.lights_by_id
        if mode == 'name':
            return self.lights_by_name
        if mode == 'list':
            return self.lights_by_id.values()

    def request(self, mode=None, address=None, data=None):  # TODO Add support for sending parameters in request
        """ Utility function for HTTP GET/PUT requests for the API"""
        auth_token = 'hauhAMjlqHmUb8t8LgILiNu8zaG8'
        header = {
            'Authorization': 'Bearer ' + auth_token,
            'Content-type': 'application/json'
        }
        try:
            if mode == 'GET':
                header = {
                    'Authorization': 'Bearer ' + auth_token,
                    'Content-type': 'application/x-www-form-urlencoded'
                }
                response = requests.get(address, headers=header, data=data)
            elif mode == 'DELETE':
                response = requests.delete(address, headers=header, params=data)
            elif mode == 'PUT':
                response = requests.put(address, headers=header, data=data)
            elif mode == 'POST':
                response = requests.post(address, headers=header, data=data)
            else:
                raise ConnectionError('No mode provided for the request method')
            logging.debug("{0} {1} {2}".format(mode, address, str(data)))

        except socket.timeout:
            error = "{} Request to {}{} timed out.".format(mode, self.uri, address)

            logging.exception(error)
            raise PhueRequestTimeout(None, error)

        return json.loads(response.text)

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
            logging.info(str(data))
            if parameter == 'name':
                result.append(self.request('PUT', self.uri + 'bridge/' + self.username + '/lights/' + str(
                    converted_light) + '/state', json.dumps(data)))
            else:
                if is_string(light):
                    converted_light = self.get_light_id_by_name(light)
                else:
                    converted_light = light
                result.append(self.request('PUT', self.uri + 'bridge/' + self.username + '/lights/' + str(
                    converted_light) + '/state', json.dumps(data)))

        logging.debug(result)
        return result
