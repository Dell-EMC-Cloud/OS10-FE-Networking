import json
import os
from unittest import TestCase

import requests
import requests_mock

from os10_fe_networking.agent.os10_fe_fabric_manager import OS10FEFabricManager
from os10_fe_networking.agent.rest_conf.interface import PortChannelInterface, Interface, VLanInterface


def prettyPrint(obj):
    print(json.dumps(obj, indent=4))


def read_file_data(filename, path):
    with open(path + filename, encoding="utf8") as data_file:
        json_data = json.load(data_file)
    return json_data


class TestOS10FEFabricManager(TestCase):

    def setUp(self):
        self.spine1_ip = "100.127.0.121"
        self.spine2_ip = "100.127.0.122"
        self.leaf1_ip = "100.127.0.125"
        self.leaf2_ip = "100.127.0.126"
        self.ff_manager_leaf1 = OS10FEFabricManager(self.leaf1_ip, self.leaf2_ip, OS10FEFabricManager.Category.LEAF)
        self.ff_manager_leaf2 = OS10FEFabricManager(self.leaf2_ip, self.leaf1_ip, OS10FEFabricManager.Category.LEAF)

    def test_find_hole(self):
        self.assertEqual(OS10FEFabricManager.find_hole({}), 1)
        self.assertEqual(OS10FEFabricManager.find_hole({1, 2, 5, 7}), 3)
        self.assertEqual(OS10FEFabricManager.find_hole({1, 2, 3, 4}), 5)

    def test_ensure_configuration(self):
        all_interfaces_leaf1 = read_file_data("all_interfaces_leaf1.json", "restconf/")
        all_interfaces_leaf2 = read_file_data("all_interfaces_leaf2.json", "restconf/")

        with requests_mock.Mocker() as m:
            m.get(self.ff_manager_leaf1.client.base_url + Interface.path_all,
                  json=all_interfaces_leaf1, status_code=200)
            m.patch(self.ff_manager_leaf1.client.base_url + Interface.path,
                    status_code=204)

            # m.get(self.ff_manager_leaf2.client.base_url + Interface.path_all,
            #       json=all_interfaces_leaf2, status_code=200)
            # m.patch(self.ff_manager_leaf2.client.get(self.leaf2_ip).base_url + Interface.path,
            #         status_code=204)

            self.ff_manager_leaf1.ensure_configuration("100.127.0.125", "ethernet1/1/1:1", "90", "Customer1")
            self.ff_manager_leaf1.ensure_configuration("100.127.0.126", "ethernet1/1/1:1", "90", "Customer1")

