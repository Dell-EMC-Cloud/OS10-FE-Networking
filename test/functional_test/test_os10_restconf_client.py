from os10_fe_networking.agent.os10_restconf_client import OS10RestConfClient
import logging
from http.client import HTTPConnection  # py3

from os10_fe_networking.agent.rest_conf.interface import VVRPGroup

log = logging.getLogger('urllib3')
log.setLevel(logging.DEBUG)

# logging from urllib3 to console
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
log.addHandler(ch)

# print statements from `http.client.HTTPConnection` to console/stdout
HTTPConnection.debuglevel = 1

client = OS10RestConfClient("100.127.0.122")

client.create_port_group("1/1/1", "unrestricted")
client.configure_port_group("1/1/1", [{"id": "1/1/1", "eth_mode": "100GIGE"}])
client.configure_port_group("1/1/1", [{"id": "1/1/2", "eth_mode": "100GIGE"}])


client.create_virtual_route_forwarding("default")


client.create_vlan("1", desc="default", enabled=True)
client.create_vlan("2001",
                   desc="BGPUplink2-Customer1",
                   enabled=True,
                   vrf="Customer1",
                   address="169.254.45.162/29")
client.create_vlan("3002",
                   desc="Isilon-FrontEnd-Cluster2",
                   enabled=True,
                   vrf="Customer2",
                   address="10.3.0.3/20",
                   vvrp_group=VVRPGroup(vvrp_id=102,
                                        priority=110,
                                        virtual_addresses=[
                                            "10.3.0.1",
                                            "10.250.0.1"
                                        ]))





