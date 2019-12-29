import requests

import base64
from oauth2_client.credentials_manager import CredentialManager, ServiceInformation, _logger

import localconfig as cfg

# def get_access_token(params_dict):
#     response = requests.get(cfg.AUTHORIZE_URL, params_dict)
#     return response

from oauth2_client.credentials_manager import CredentialManager, ServiceInformation, _logger
scopes = ['scope_1', 'scope_2']
service_information = ServiceInformation(cfg.AUTHORIZE_URL,
                                         cfg.ACCESS_TOKEN_URL,
                                         cfg.CLIENT_ID,
                                         cfg.CLIENT_SECRET,
                                          scopes)
manager = CredentialManager(service_information,
                            proxies=dict(http='http://localhost:3128', https='http://localhost:3128'))
redirect_uri = 'http://localhost:8080/oauth/code'

# Builds the authorization url and starts the local server according to the redirect_uri parameter
# url = manager.init_authorize_code_process(redirect_uri, 'state_test')
# _logger.info('Open this url in your browser\n%s', url)

# code = manager.wait_and_terminate_authorize_code_process()
# From this point the http server is opened on 8080 port and wait to receive a single GET request
# All you need to do is open the url and the process will go on
# (as long you put the host part of your redirect uri in your host file)
# when the server gets the request with the code (or error) in its query parameters
#_logger.debug('Code got = %s', code)
# manager.init_with_authorize_code(redirect_uri, code)
# _logger.debug('Access got = %s', manager._access_token)
# Here access and refresh token may be used with self.refresh_token


realm = 'oauth2_client@api.meethue.com'
nonce = '78c44dba24d661274c2a420029d03926'
client_id = 'NAB6dQmQdW3uGOaEAx0imB4fIhqe4Pmo'
secret = 'FKa2Pfa3'
seed = client_id+":"+secret
encodedSeed = base64.b64encode(seed.encode('utf-8'))

url = cfg.ACCESS_TOKEN_URL

body = {
    "code": "ahTbAG7e",
    "grant_type": "authorization_code"
    }

headers = {
    'Content-Type': "application/json",
    'Authorization': "Basic "+str(encodedSeed, 'utf-8')
    }

response = requests.request("POST", url, data=body, headers=headers)

print(response.text)