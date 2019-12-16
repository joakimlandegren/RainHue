# -*- coding: utf-8 -*-

import unittest
import localconfig as cfg
import socket
import authorization

DEVICE_ID = socket.gethostname()

valid_params_dict = {
    'client_id': cfg.CLIENT_ID,
    'app_id': cfg.APP_ID,
    'device_id': DEVICE_ID,
    'state': cfg.STATE,
    'response_type': cfg.RESPONSE_TYPE
}

invalid_client_id_params_dict = {
    'client_id': 'fail',
    'app_id': cfg.APP_ID,
    'device_id': DEVICE_ID,
    'state': cfg.STATE,
    'response_type': cfg.RESPONSE_TYPE
}

empty_params_dict = {}

class TestOauth2Suite(unittest.TestCase):
    """Authorization test cases."""

    def test_get_access_token_with_200_response(self):
        resp = authorization.get_access_token(valid_params_dict)
        assert resp.status_code == 200

    def test_get_access_token_with_500_response(self):
        resp = authorization.get_access_token(invalid_client_id_params_dict)
        assert resp.status_code == 500

    def test_get_acces_token_with_empty_request(self):
        resp = authorization.get_access_token(empty_params_dict)
        assert resp.status_code == 400  

    def test_refresh_access_token(self):
        assert True
