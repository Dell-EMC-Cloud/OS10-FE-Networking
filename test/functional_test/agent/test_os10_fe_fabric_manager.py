import sys
from oslo_config import cfg

from os10_fe_networking.agent.os10_fe_fabric_manager import LeafManager, OS10FEFabricManager
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

CONF = cfg.CONF
CONF.import_group("FRONTEND_SWITCH_FABRIC", "os10_fe_networking.agent.config")
CONF(sys.argv[1:])

manager = OS10FEFabricManager.create(CONF)

import pdb
pdb.set_trace()
manager.ensure_configuration("100.127.0.125", "ethernet1/1/3", "1499", "CustomerTest1", True, "access", False)
manager.ensure_configuration("100.127.0.125", "ethernet1/1/3", "1500", "CustomerTest1", True, "trunk", False)

manager.detach_port_from_vlan("ethernet1/1/3", "1499", "access", False)
manager.detach_port_from_vlan("ethernet1/1/3", "1500", "trunk", False)

manager.delete_port_channel_vlan("ethernet1/1/3", "1499", False)
manager.delete_port_channel_vlan("ethernet1/1/3", "1500", False)



