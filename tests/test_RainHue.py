#!/usr/bin/python

import unittest
from RainHue import connect_to_hue_bridge_and_fetch_lamps


class TestRequests(unittest.TestCase):
    def test_init_remote_bridge(self):
        connect_to_hue_bridge_and_fetch_lamps()
        assert True


