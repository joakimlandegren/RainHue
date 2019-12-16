import requests
import localconfig as cfg


def get_access_token(params_dict):
    response = requests.get(cfg.AUTHORIZE_URL, params_dict)
    return response
