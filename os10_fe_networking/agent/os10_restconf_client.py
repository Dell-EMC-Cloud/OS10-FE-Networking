import requests
from requests.auth import HTTPBasicAuth
from oslo_log import log as logging

# query = {'lat':'45', 'lon':'180'}
# response = requests.get('http://api.open-notify.org/iss-pass.json', params=query)
# print(response.json())
# # Create a new resource
# response = requests.post('https://httpbin.org/post', data={'key':'value'})
# # Update an existing resource
# requests.put('https://httpbin.org/put', data={'key': 'value'})
# print(response.headers["date"])

LOG = logging.getLogger(__name__)


class OS10RestconfClient:

    def __init__(self):
        self.username = "admin"
        self.password = "admin"

    def get(self, url, parameters):
        resp = requests.get(url, params=parameters, auth=HTTPBasicAuth(self.username, self.password))
        LOG.debug(resp.json())

    def post(self, url, parameters, body):
        resp = requests.post(url, params=parameters, data=body, auth=HTTPBasicAuth(self.username, self.password))
        LOG.debug(resp.json())

    def put(self, url, parameters, body):
        resp = requests.put(url, params=parameters, data=body, auth=HTTPBasicAuth(self.username, self.password))
        LOG.debug(resp.json())

    def delete(self, url, parameters):
        resp = requests.delete(url, params=parameters, auth=HTTPBasicAuth(self.username, self.password))
        LOG.debug(resp.json())

