from os10_fe_networking.agent.os10_fe_fabric_manager import OS10FEFabricManager
import logging
from http.client import HTTPConnection  # py3

from os10_fe_networking.agent.rest_conf.interface import VLanInterface

log = logging.getLogger('urllib3')
log.setLevel(logging.DEBUG)

# logging from urllib3 to console
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
log.addHandler(ch)

# print statements from `http.client.HTTPConnection` to console/stdout
HTTPConnection.debuglevel = 1

leaf1 = OS10FEFabricManager("100.127.0.125", "100.127.0.126", OS10FEFabricManager.Category.LEAF)
leaf2 = OS10FEFabricManager("100.127.0.126", "100.127.0.125", OS10FEFabricManager.Category.LEAF)

import pdb
pdb.set_trace()
leaf1.ensure_configuration("100.127.0.125", "ethernet1/1/3", "90", "CustomerTest1")
leaf2.ensure_configuration("100.127.0.125", "ethernet1/1/3", "90", "CustomerTest1")

leaf1.release_ethernet_interface("ethernet1/1/3", "90")
leaf1.delete_port_channel_vlan("ethernet1/1/3", "90")

leaf2.delete_port_channel_vlan("ethernet1/1/3", "90")
