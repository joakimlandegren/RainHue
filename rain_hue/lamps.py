#!/usr/bin/python
import logging
from rain_hue.remote_bridge import RemoteBridge
import localconfig as cfg


class Lamps:
    def __init__(self):
        self._bridge = RemoteBridge(cfg.uri, cfg.username, )
        self._light_names = self._bridge.get_light_objects('name')

    def turn_on_lamp(self, lamp):
        self._light_names[lamp].on = True

    def change_lamp_color(self, lamp_color, lamp):
        self._light_names[lamp].brightness = lamp_color[0]
        self._light_names[lamp].hue = lamp_color[1]
        self._light_names[lamp].saturation = lamp_color[2]
        logging.info('Color of %s set to %s, %s, %s', lamp, lamp_color[0], lamp_color[1], lamp_color[2])