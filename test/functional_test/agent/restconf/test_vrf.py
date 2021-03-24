from os10_fe_networking.agent.os10_fe_restconf_client import OS10FERestConfClient
import logging
from http.client import HTTPConnection  # py3

log = logging.getLogger('urllib3')
log.setLevel(logging.DEBUG)

# logging from urllib3 to console
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
log.addHandler(ch)

# print statements from `http.client.HTTPConnection` to console/stdout
HTTPConnection.debuglevel = 1

client = OS10FERestConfClient("100.127.0.122")
vrf_name = "CustomerTest"

import pdb; pdb.set_trace()
client.delete_virtual_route_forwarding(vrf_name)
exist = client.get_virtual_route_forwarding(vrf_name)
print("{vrf_name}")
client.configure_virtual_route_forwarding(vrf_name)
client.delete_virtual_route_forwarding(vrf_name)
