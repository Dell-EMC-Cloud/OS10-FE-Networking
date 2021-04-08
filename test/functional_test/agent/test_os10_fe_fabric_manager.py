import sys
from oslo_config import cfg

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

CONF = cfg.CONF
CONF.import_group("FRONTEND_SWITCH_FABRIC", "os10_fe_networking.agent.config")
CONF(sys.argv[1:])

leaf1 = OS10FEFabricManager(CONF)

import pdb
pdb.set_trace()
leaf1.ensure_configuration("100.127.0.125", "ethernet1/1/3", "90", "CustomerTest1", True)

leaf1.release_ethernet_interface("ethernet1/1/3", "90")
leaf1.delete_port_channel_vlan("ethernet1/1/3", "90")

