import requests
import localconfig as cfg


def get_access_token(params_dict):
    try:
        response = requests.get(cfg.AUTHORIZE_URL, params_dict)
    except (ConnectionError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
        print("We have a connection problem!")
    return response
