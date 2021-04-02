from os10_fe_networking.agent.os10_fe_restconf_client import OS10FERestConfClient
import logging
from http.client import HTTPConnection  # py3

from os10_fe_networking.agent.rest_conf.border_gateway_protocol import *
from os10_fe_networking.agent.rest_conf.interface import VVRPGroup, VLanInterface, PortChannelInterface, \
    EthernetInterface

log = logging.getLogger('urllib3')
log.setLevel(logging.DEBUG)

# logging from urllib3 to console
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
log.addHandler(ch)

# print statements from `http.client.HTTPConnection` to console/stdout
HTTPConnection.debuglevel = 1


def test_port_group():
    client = OS10FERestConfClient("100.127.0.122")
    client.create_port_group("1/1/1", "unrestricted")
    client.configure_port_group("1/1/1", [{"id": "1/1/1", "eth_mode": "100GIGE"}])
    client.configure_port_group("1/1/1", [{"id": "1/1/2", "eth_mode": "100GIGE"}])


def test_vrf():
    client = OS10FERestConfClient("100.127.0.122")
    client.configure_virtual_route_forwarding("default")


def test_vlan():
    client = OS10FERestConfClient("100.127.0.122")
    client.configure_vlan(VLanInterface(vlan_id="1", desc="default", enabled=True))
    client.configure_vlan(VLanInterface(vlan_id="2001",
                                        desc="BGPUplink2-Customer1",
                                        enabled=True,
                                        vrf="Customer1",
                                        address="169.254.45.162/29"))
    client.configure_vlan(VLanInterface(vlan_id="3002",
                                        desc="Isilon-FrontEnd-Cluster2",
                                        enabled=True,
                                        vrf="Customer2",
                                        address="10.3.0.3/20",
                                        vvrp_group=VVRPGroup(vvrp_id=102,
                                                             priority=110,
                                                             virtual_addresses=[
                                                                 "10.3.0.1",
                                                                 "10.250.0.1"
                                                             ])
                                        ))


def test_port_channel():
    client = OS10FERestConfClient("100.127.0.122")
    client.configure_port_channel(PortChannelInterface(channel_id="2",
                                                       desc=None,
                                                       enabled=True,
                                                       mode="trunk",
                                                       access_vlan_id=None,
                                                       trunk_allowed_vlan_ids="1001,2001",
                                                       mtu=None,
                                                       vlt_port_channel_id=None,
                                                       spanning_tree=False))
    client.configure_port_channel(PortChannelInterface(channel_id="10",
                                                       desc=None,
                                                       enabled=True,
                                                       mode="trunk",
                                                       access_vlan_id=None,
                                                       trunk_allowed_vlan_ids="1001,2001",
                                                       mtu=9216,
                                                       vlt_port_channel_id=10,
                                                       spanning_tree=None))
    client.configure_port_channel(PortChannelInterface(channel_id="103",
                                                       desc=None,
                                                       enabled=True,
                                                       mode="trunk",
                                                       access_vlan_id="1",
                                                       trunk_allowed_vlan_ids="1001,2001",
                                                       mtu=9216,
                                                       vlt_port_channel_id=103,
                                                       spanning_tree=None))


def test_ethernet_interface():
    client = OS10FERestConfClient("100.127.0.122")
    client.configure_ethernet_interface(EthernetInterface(eif_id="1/1/1",
                                                          enabled=True,
                                                          access_vlan_id="1",
                                                          mtu=1554,
                                                          flow_control_receive=False,
                                                          flow_control_transmit=False))
    client.configure_ethernet_interface(EthernetInterface(eif_id="1/1/5",
                                                          desc="R103U45-46",
                                                          enabled=True,
                                                          access_vlan_id="1",
                                                          mtu=9216,
                                                          flow_control_receive=True,
                                                          flow_control_transmit=False,
                                                          channel_group="103",
                                                          disable_switch_port=True))
    client.configure_ethernet_interface(EthernetInterface(eif_id="1/1/64",
                                                          desc="Google Uplink2",
                                                          enabled=True,
                                                          access_vlan_id=None,
                                                          mtu=1554,
                                                          flow_control_receive=False,
                                                          flow_control_transmit=False,
                                                          channel_group="2",
                                                          disable_switch_port=True))


def test_configure_ethernet_interface_64_R101U43_44_9264():
    client = OS10FERestConfClient("100.127.0.122")
    client.configure_vlan(VLanInterface(vlan_id="91", desc=None, enabled=True))
    client.configure_vlan(VLanInterface(vlan_id="2001",
                          desc="BGPUplink2-Customer1",
                          enabled=True,
                          vrf="Customer1",
                          address="169.254.45.162/29"))
    client.configure_vlan(VLanInterface(vlan_id="2002",
                          desc="BGPUplink2-Customer2",
                          enabled=True,
                          vrf="Customer2",
                          address="169.254.223.138/29"))
    client.configure_vlan(VLanInterface(vlan_id="2051",
                          desc="BGPUplink2-Customer1",
                          enabled=True,
                          vrf="Customer1",
                          address="169.254.10.250/29"))

    client.configure_port_channel(PortChannelInterface(channel_id="2",
                                  desc=None,
                                  enabled=True,
                                  mode="trunk",
                                  access_vlan_id=None,
                                  trunk_allowed_vlan_ids="91,2001-2002,2051",
                                  mtu=None,
                                  vlt_port_channel_id=None,
                                  spanning_tree=False))

    client.configure_ethernet_interface(EthernetInterface(eif_id="1/1/64",
                                        desc="Google Uplink2",
                                        enabled=True,
                                        access_vlan_id=None,
                                        mtu=1554,
                                        flow_control_receive=False,
                                        flow_control_transmit=False,
                                        channel_group="2",
                                        disable_switch_port=True))


def test_configure_ethernet_interface_64_R101U45_46_9264():
    client = OS10FERestConfClient("100.127.0.121")
    client.configure_vlan(VLanInterface(vlan_id="91", desc=None, enabled=True))
    client.configure_vlan(VLanInterface(vlan_id="1001",
                          desc="BGPUplink1-Customer1",
                          enabled=True,
                          vrf="Customer1",
                          address="169.254.204.18/29"))
    client.configure_vlan(VLanInterface(vlan_id="1002",
                          desc="BGPUplink1-Customer2",
                          enabled=True,
                          vrf="Customer2",
                          address="169.254.51.154/29"))
    client.configure_vlan(VLanInterface(vlan_id="1051",
                          desc="BGPUplink1-Customer1",
                          enabled=True,
                          vrf="Customer1",
                          address="169.254.223.250/29"))

    client.configure_port_channel(PortChannelInterface(channel_id="1",
                                  desc=None,
                                  enabled=True,
                                  mode="trunk",
                                  access_vlan_id="1",
                                  trunk_allowed_vlan_ids="90,1001-1002,1051",
                                  mtu=None,
                                  vlt_port_channel_id=None,
                                  spanning_tree=False))

    client.configure_ethernet_interface(EthernetInterface(eif_id="1/1/64",
                                        desc="Google Uplink1",
                                        enabled=True,
                                        access_vlan_id=None,
                                        mtu=1554,
                                        flow_control_receive=False,
                                        flow_control_transmit=False,
                                        channel_group="1",
                                        disable_switch_port=True))


test_configure_ethernet_interface_64_R101U43_44_9264()
# test_configure_ethernet_interface_64_R101U45_46_9264()


def test_bgp():
    client = OS10FERestConfClient("100.127.0.122")
    bgp = BorderGatewayProtocol([
        VirtualRoutingForwarding(name="default",
                                 local_as_number="4200008194",
                                 neighbors=[
                                     Neighbor(address="10.250.0.2",
                                              timers=Timers(1, 3)),
                                     Neighbor(address="169.254.114.201",
                                              timers=Timers(1, 3)),
                                     Neighbor(address="10.3.0.2"),
                                 ]),
        VirtualRoutingForwarding(name="Customer1",
                                 best_path_as_path_multipath_relax=True,
                                 router_id="10.250.0.3",
                                 router_at_common_config=RouterAtCommonConfig(True),
                                 neighbors=[
                                     Neighbor(address="10.250.0.2",
                                              fall_over=True,
                                              remote_as=4200008194,
                                              timers=Timers(1, 3),
                                              shutdown=False,
                                              ipv4_unicast=Ipv4Unicast(True)),
                                     Neighbor(address="169.254.45.161",
                                              desc="Google-VL2001-UL-us-east4-z2-pod1-1",
                                              ebpg_multihop=4,
                                              fall_over=True,
                                              remote_as=4200008193,
                                              timers=Timers(20, 60),
                                              shutdown=False),
                                     Neighbor(address="169.254.10.249",
                                              desc="Google-VL2051-UL-us-east4-z2-pod1-1",
                                              ebpg_multihop=4,
                                              fall_over=True,
                                              remote_as=4200008193,
                                              timers=Timers(20, 60),
                                              shutdown=False)
                                 ]),
        VirtualRoutingForwarding(name="Customer2",
                                 best_path_as_path_multipath_relax=True,
                                 graceful_restart=True,
                                 router_id="10.3.0.3",
                                 router_at_common_config=RouterAtCommonConfig(True),
                                 neighbors=[
                                     Neighbor(address="10.3.0.2",
                                              fall_over=True,
                                              remote_as=4200008194,
                                              timers=Timers(1, 3),
                                              shutdown=False,
                                              ipv4_unicast=Ipv4Unicast(True)),
                                     Neighbor(address="169.254.223.137",
                                              desc="Google-VL2002-UL-us-east4-z1-pod1-0",
                                              ebpg_multihop=4,
                                              fall_over=True,
                                              local_as=4200008194,
                                              remote_as=4200008193,
                                              timers=Timers(1, 3),
                                              shutdown=False)
                                 ])
    ])
    client.configure_bgp(bgp)

# test_bgp()
