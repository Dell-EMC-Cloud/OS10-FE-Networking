from os10_fe_networking.agent.os10_fe_fabric_manager import OS10FEFabricManager, SwitchGroup
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

manager = OS10FEFabricManager(switch_groups=[
    SwitchGroup(spine_addresses=[
        "100.127.0.121",
        "100.127.0.122"
    ],
        leaf_addresses=[
            "100.127.0.125",
            "100.127.0.126"
        ],
        active=True)
])


def configure(vlan_interfaces, port_channel, ethernet_interface):
    pass




configure()
