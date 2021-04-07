import json
import os
from unittest import TestCase

import requests
import requests_mock

from os10_fe_networking.agent.rest_conf.interface import VLanInterface, VVRPGroup, PortChannelInterface


def prettyPrint(obj):
    print(json.dumps(obj, indent=4))


def read_file_data(filename, path):
    os.chdir(path)
    with open(filename, encoding="utf8") as data_file:
        json_data = json.load(data_file)
    return json_data


def key_func(e):
    return int(e["name"][12:])


class TestVLanInterface(TestCase):

    def setUp(self):
        pass

    def test_equal_vlan(self):
        vlan1 = VLanInterface(vlan_id=1, desc="abc")
        vlan2 = VLanInterface(vlan_id=1, desc="abc")
        print(vlan1 == vlan2)
        print(vlan1 is vlan2)

    def test_vlan_interface_simple(self):
        vlan_interface = VLanInterface(vlan_id="1", desc="default", enabled=True)
        prettyPrint(vlan_interface.content())

    def test_vlan_interface(self):
        vlan_interface = VLanInterface(vlan_id="2001",
                                       desc="BGPUplink2-Customer1",
                                       enabled=True,
                                       vrf="Customer1",
                                       address="169.254.45.162/29")
        prettyPrint(vlan_interface.content())

    def test_vlan_interface_with_vrrp(self):
        vlan_interface = VLanInterface(vlan_id="3002",
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
                                       )
        prettyPrint(vlan_interface.content())

    def test_vlan_interface_vlan_access(self):
        vlan_interface = VLanInterface(vlan_id="3002",
                                       desc="Isilon-FrontEnd-Cluster2",
                                       enabled=True,
                                       port_channel="123",
                                       port_channel_mode=VLanInterface.PortChannelMode.ACCESS)
        prettyPrint(vlan_interface.content())

    def test_vlan_interface_vlan_trunk_allowed(self):
        vlan_interface = VLanInterface(vlan_id="3002",
                                       desc="Isilon-FrontEnd-Cluster2",
                                       enabled=True,
                                       port_channel="123",
                                       port_channel_mode=VLanInterface.PortChannelMode.TRUNK)
        prettyPrint(vlan_interface.content())

        vlan_interface = VLanInterface(vlan_id="3002,3004,3008-3100",
                                       desc="Isilon-FrontEnd-Cluster2",
                                       enabled=True,
                                       port_channel="123",
                                       port_channel_mode=VLanInterface.PortChannelMode.TRUNK)
        prettyPrint(vlan_interface.content())

    def test_vlan_interface_with_ethernet_interface(self):
        vlan_interface = VLanInterface("1", ethernet_if="1/1/2")
        prettyPrint(vlan_interface.content())

    def test_port_channel_interface(self):
        port_channel = PortChannelInterface(channel_id="2",
                                            desc=None,
                                            enabled=True,
                                            mode="trunk",
                                            access_vlan_id=None,
                                            trunk_allowed_vlan_ids="1001,2001",
                                            mtu=None,
                                            vlt_port_channel_id=None,
                                            spanning_tree=False,
                                            lacp_fallback=True,
                                            lacp_timeout=10,
                                            )
        prettyPrint(port_channel.content())

    def test_port_channel_interface1(self):
        port_channel = PortChannelInterface(channel_id="10",
                                            desc=None,
                                            enabled=True,
                                            mode="trunk",
                                            access_vlan_id=None,
                                            trunk_allowed_vlan_ids="1001,2001",
                                            mtu=9216,
                                            vlt_port_channel_id=10,
                                            spanning_tree=None,
                                            lacp_fallback=True,
                                            lacp_timeout=10,
                                            lacp_preempt=False,
                                            bpdu=True)
        prettyPrint(port_channel.content())

    def test_port_channel_interface2(self):
        port_channel = PortChannelInterface(channel_id="103",
                                            desc=None,
                                            enabled=True,
                                            mode="trunk",
                                            access_vlan_id="1",
                                            trunk_allowed_vlan_ids="1001,2001",
                                            mtu=9216,
                                            vlt_port_channel_id=103,
                                            spanning_tree=None,
                                            bpdu=True,
                                            edge_port=True)
        prettyPrint(port_channel.content())

    def test_port_channel_interface_for_ethernet_interface(self):
        port_channel = PortChannelInterface(channel_id="103", ethernet_if="1/1/3")
        prettyPrint(port_channel.content())

    def test_123(self):
        all_interfaces = read_file_data("all_interfaces_spine1.json", "./")
        # prettyPrint(all_interfaces)

        with requests_mock.Mocker() as m:
            m.get('http://test.com', json=all_interfaces, status_code=200)
            resp = requests.get('http://test.com')
            # prettyPrint(resp.json())
            lst = PortChannelInterface.handle_get_all(resp)

            lst.sort(key=lambda e: int(e["name"][12:]))
            prettyPrint(lst)
