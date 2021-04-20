import json
import os
from unittest import TestCase

import requests
import requests_mock
from oslo_config import cfg

from os10_fe_networking.agent.os10_fe_fabric_manager import LeafManager, OS10FEFabricManager
from os10_fe_networking.agent.rest_conf.interface import PortChannelInterface, Interface, VLanInterface

CONF = cfg.CONF
CONF.import_group("FRONTEND_SWITCH_FABRIC", "os10_fe_networking.agent.config")


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
        # self.ff_manager_leaf1 = OS10FEFabricManager(CONF)
        # self.ff_manager_leaf2 = OS10FEFabricManager(CONF)

    def test_find_hole(self):
        self.assertEqual(LeafManager.find_hole({}), 1)
        self.assertEqual(LeafManager.find_hole({1, 2, 5, 7}), 3)
        self.assertEqual(LeafManager.find_hole({1, 2, 3, 4}), 5)

    def test_leaf_ensure_configuration(self):
        CONF(["--config-file", "./leaf1.ini"])
        self.ff_manager_leaf1 = OS10FEFabricManager.create(CONF)

        all_interfaces_leaf1 = read_file_data("all_interfaces_leaf1.json", "restconf/")

        with requests_mock.Mocker() as m:
            m.get(self.ff_manager_leaf1.client.base_url + Interface.path_all,
                  json=all_interfaces_leaf1, status_code=200)
            m.patch(self.ff_manager_leaf1.client.base_url + Interface.path,
                    status_code=204)

            self.ff_manager_leaf1.ensure_configuration("100.127.0.125", "ethernet1/1/1:1", "2222",
                                                       "FunctionalTestCustomer1", False, "access", True)

    def test_spine_ensure_configuration(self):
        CONF(["--config-file", "./spine1.ini"])
        self.ff_manager_spine1 = OS10FEFabricManager.create(CONF)

        all_interfaces_spine1 = read_file_data("all_interfaces_spine1.json", "restconf/")

        with requests_mock.Mocker() as m:
            m.get(self.ff_manager_spine1.client.base_url + Interface.path_all,
                  json=all_interfaces_spine1, status_code=200)
            m.patch(self.ff_manager_spine1.client.base_url + Interface.path,
                    status_code=204)

            self.ff_manager_spine1.ensure_configuration("100.127.0.127", "ethernet1/1/1:1", "2222",
                                                        "FunctionalTestCustomer1", False, "access")
