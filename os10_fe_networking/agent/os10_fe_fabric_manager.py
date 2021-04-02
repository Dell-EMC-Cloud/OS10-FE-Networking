from enum import Enum

from os10_fe_networking.agent.os10_fe_restconf_client import OS10FERestConfClient
from os10_fe_networking.agent.rest_conf.interface import Interface, VLanInterface, PortChannelInterface, \
    EthernetInterface


class SwitchPair:
    class Category(Enum):
        SPINE = "spine"
        LEAF = "leaf"

    def __init__(self, addresses, category):
        self.category = category
        self.addresses = addresses
        self.clients = {address: OS10FERestConfClient(address) for address in addresses}

    def get(self, address):
        return self.clients[address]


class OS10FEFabricManager:

    def __init__(self, switch_pair=None):
        self.switch_pair = switch_pair

        if self.switch_pair is None:
            self.switch_pair = SwitchPair(["100.127.0.125", "100.127.0.126"], SwitchPair.Category.LEAF)

    @staticmethod
    def find_hole(sorted_set):
        prev = None
        hole = None
        for v in sorted_set:
            if prev is None:
                prev = v
                continue
            else:
                if prev + 1 == v:
                    prev = v
                    continue
                else:
                    # find hole in set
                    hole = prev + 1
                    break

        if hole is None:
            # empty set
            if prev is None:
                hole = 1
            # continues set
            else:
                hole = prev + 1

        return hole

    def _get_interface_from_cache(self, if_id, desc, interface_dict, if_type):
        for _, interface in interface_dict[if_type].items():
            if interface["name"] == if_id and interface["description"] == desc:
                return interface

        return None

    def _get_interface_from_cache_by_desc(self, desc, interface_dict, if_type):
        for _, interface in interface_dict[if_type].items():
            if interface.get("description") == desc:
                return interface

        return None

    def _get_all_interfaces(self, client):
        vlan_dict, port_channel_dict, ethernet_dict = client.get_all_interfaces_by_type()
        return client.mgmt_ip, {
            Interface.Type.VLan: vlan_dict,
            Interface.Type.PortChannel: port_channel_dict,
            Interface.Type.Ethernet: ethernet_dict
        }

    def _get_all_interfaces_for_switch_pair(self, switch_pair):
        """
        :return:
            {
                "x.x.x.x": {
                    "iana-if-type:l2vlan": {
                        "vlan1": {...},
                        "vlan2": {...},
                        ...
                    },
                    "iana-if-type:ieee8023adLag": {
                        "port-channel1": {...},
                        "port-channel2": {...},
                        ...
                    },
                    "iana-if-type:ethernetCsmacd": {
                        "ethernet1/1/1:1": {...},
                        "ethernet1/1/1:2": {...},
                        ...
                    }
                },
                ...
            }
        """
        all_interfaces = {}
        for _, client in switch_pair.clients.items():
            mgmt_ip, interfaces = self._get_all_interfaces(client)
            all_interfaces[mgmt_ip] = interfaces

        return all_interfaces

    def _calc_available_port_channel(self, all_interfaces):
        port_channel_set = set()
        for _, interface_dict in all_interfaces.items():
            for _, interface in interface_dict[Interface.Type.PortChannel].items():
                if_id = PortChannelInterface.extract_numeric_id(interface["name"])
                port_channel_set.add(if_id)

        # find a hole (available) port channel id
        return self.find_hole(sorted(port_channel_set))

    def _check_ethernet_interface_id(self, eif_id):
        return eif_id[8:] if "ethernet" in eif_id else eif_id

    # TODO(Phil Zhang), no port channel version should be supported in the future
    def ensure_configuration(self, switch_ip, ethernet_interface, vlan, cluster, host):
        all_interfaces = self._get_all_interfaces_for_switch_pair(self.switch_pair)

        # fetch switch side vlan configuration and ensure configuration
        vlan_pair = {}
        port_channel_id = None
        for switch_ip, interface_dict in all_interfaces.items():
            vlan_if = self._get_interface_from_cache(vlan, cluster, interface_dict, Interface.Type.VLan)
            vlan_pair[switch_ip] = vlan_if
            if vlan_if is None:
                self.switch_pair.get(switch_ip).configure_vlan(VLanInterface(vlan_id=vlan,
                                                                             desc=cluster,
                                                                             enabled=True))

            # ensure port-channel
            # for switch_ip, interface_dict in all_interfaces.items():
            port_channel_if = self._get_interface_from_cache_by_desc(cluster, interface_dict, Interface.Type.PortChannel)

            # port-channel doesn't exist, create
            if port_channel_if is None:
                # allocate a new port channel id, which should not be used by any current configuration
                if port_channel_id is None:
                    port_channel_id = self._calc_available_port_channel(all_interfaces)

                # create port channel
                self.switch_pair.get(switch_ip).configure_port_channel(
                    PortChannelInterface(channel_id=str(port_channel_id),
                                         desc=cluster,
                                         enabled=True,
                                         mode="trunk",
                                         access_vlan_id=None,
                                         trunk_allowed_vlan_ids=vlan,
                                         mtu=9216,
                                         vlt_port_channel_id=port_channel_id,
                                         spanning_tree=False))
            # port-channel exists, make sure it's related to our vlan
            else:
                if not vlan_if.get("dell-interface:tagged-ports") or \
                        port_channel_if["name"] not in vlan_if["dell-interface:tagged-ports"]:
                    self.switch_pair.get(switch_ip).configura_vlan(
                        VLanInterface(vlan_id=vlan, port_channel=port_channel_if["name"]))

        ethernet_interface = self._check_ethernet_interface_id(ethernet_interface)
        self.switch_pair.get(switch_ip).configure_ethernet_interface(EthernetInterface(eif_id=ethernet_interface,
                                                                                       desc=cluster + "-" + host,
                                                                                       enabled=True,
                                                                                       access_vlan_id=None,
                                                                                       mtu=1554,
                                                                                       flow_control_receive=True,
                                                                                       flow_control_transmit=False,
                                                                                       channel_group=str(port_channel_id),
                                                                                       disable_switch_port=True))

        return None
