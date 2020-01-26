# -*- coding: utf-8 -*-

import unittest
import localconfig as cfg
import authorization
from requests import exceptions

valid_params_dict = {
    'client_id': cfg.CLIENT_ID,
    'app_id': cfg.APP_ID,
    'device_id': cfg.DEVICE_ID,
    'state': cfg.STATE,
    'response_type': cfg.RESPONSE_TYPE
}

invalid_client_id_params_dict = {
    'client_id': 'fail',
    'app_id': cfg.APP_ID,
    'device_id': cfg.DEVICE_ID,
    'state': cfg.STATE,
    'response_type': cfg.RESPONSE_TYPE
}

empty_params_dict = {}

class Test_AccessTokens(unittest.TestCase):

    def test_get_access_token_with_valid_params(self):
        try:
            resp = authorization.get_access_token(valid_params_dict)
            assert resp.status_code == 200
        except exceptions.ConnectionError as e:
            print(e)

    def test_get_access_token_with_invalid_params(self):
        try:
            resp = authorization.get_access_token(invalid_client_id_params_dict)
            assert resp.status_code == 500
        except exceptions.ConnectionError as e:
            print(e)
    def test_get_access_token_with_empty_request(self):
        try:
            resp = authorization.get_access_token(empty_params_dict)
            assert resp.status_code == 400
        except exceptions.ConnectionError as e:
            print(e)

    def test_refresh_access_token(self):
        assert True