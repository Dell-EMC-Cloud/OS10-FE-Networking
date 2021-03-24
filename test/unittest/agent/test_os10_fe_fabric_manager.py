import json
import os
from unittest import TestCase

import requests
import requests_mock

from os10_fe_networking.agent.os10_fe_fabric_manager import OS10FEFabricManager
from os10_fe_networking.agent.rest_conf.interface import PortChannelInterface, Interface


def prettyPrint(obj):
    print(json.dumps(obj, indent=4))


def read_file_data(filename, path):
    with open(path + filename, encoding="utf8") as data_file:
        json_data = json.load(data_file)
    return json_data


class TestOS10FEFabricManager(TestCase):

    def setUp(self):
        self.ff_manager = OS10FEFabricManager()

    def test_find_hole(self):
        self.assertEqual(self.ff_manager.find_hole({}), 1)
        self.assertEqual(self.ff_manager.find_hole({1, 2, 5, 7}), 3)
        self.assertEqual(self.ff_manager.find_hole({1, 2, 3, 4}), 5)

    def test_get_available_port_channel(self):
        all_interfaces_spine1 = read_file_data("all_interfaces_spine1.json", "restconf/")
        all_interfaces_spine2 = read_file_data("all_interfaces_spine2.json", "restconf/")

        with requests_mock.Mocker() as m:
            m.get(self.ff_manager.active_switch_group().spines[0].base_url + PortChannelInterface.path_get_all,
                  json=all_interfaces_spine1, status_code=200)
            m.get(self.ff_manager.active_switch_group().spines[1].base_url + PortChannelInterface.path_get_all,
                  json=all_interfaces_spine2, status_code=200)

            port_channel_id = self.ff_manager.get_available_interface(if_type=Interface.Type.PortChannel)
            self.assertEqual(port_channel_id, 3)

    def test_get_available_vlan(self):
        all_interfaces_spine1 = read_file_data("all_interfaces_spine1.json", "restconf/")
        all_interfaces_spine2 = read_file_data("all_interfaces_spine2.json", "restconf/")

        with requests_mock.Mocker() as m:
            m.get(self.ff_manager.active_switch_group().spines[0].base_url + PortChannelInterface.path_get_all,
                  json=all_interfaces_spine1, status_code=200)
            m.get(self.ff_manager.active_switch_group().spines[1].base_url + PortChannelInterface.path_get_all,
                  json=all_interfaces_spine2, status_code=200)

            vlan_id = self.ff_manager.get_available_interface(if_type=Interface.Type.VLan)
            self.assertEqual(vlan_id, 3)
