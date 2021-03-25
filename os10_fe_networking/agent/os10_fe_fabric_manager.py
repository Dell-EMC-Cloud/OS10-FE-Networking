from os10_fe_networking.agent.os10_fe_restconf_client import OS10FERestConfClient
from os10_fe_networking.agent.rest_conf.interface import Interface, VLanInterface, PortChannelInterface, \
    EthernetInterface


class SwitchGroup:

    def __init__(self, spine_addresses, leaf_addresses, active=False):
        self.spines = []
        for address in spine_addresses:
            self.spines.append(OS10FERestConfClient(address))

        self.leaves = []
        for address in leaf_addresses:
            self.leaves.append(OS10FERestConfClient(address))

        self.active = active

    def get_client(self, address):
        for client in self.spines:
            if client.mgmt_ip == address:
                return client

        for client in self.leaves:
            if client.mgmt_ip == address:
                return client

        return None


class OS10FEFabricManager:

    def __init__(self, switch_groups=None):
        self.switch_groups = switch_groups

        if self.switch_groups is None:
            self.switch_groups = [
                SwitchGroup(spine_addresses=[
                    "100.127.0.121",
                    "100.127.0.122"
                ],
                    leaf_addresses=[
                        "100.127.0.125",
                        "100.127.0.126"
                    ],
                    active=True)
            ]

    def active_switch_group(self):
        for switch_group in self.switch_groups:
            if switch_group.active:
                return switch_group

    def select_clients(self, address, spine):
        client_list = []
        if address is not None:
            client = self.active_switch_group().get_client(address)
            if client is None:
                raise RuntimeError("can not find target address {address}".format(address=address))
            client_list.append(client)
        else:
            if spine is True:
                client_list.extend(self.active_switch_group().spines)
            else:
                client_list.extend(self.active_switch_group().leaves)

        return client_list

    def ensure_vrf(self, name, spine=True):
        client_list = self.select_clients(spine=spine)

        for client in client_list:
            exist = client.get_virtual_route_forwarding(name)
            if not exist:
                client.configure_virtual_route_forwarding(name)

    def ensure_vlan(self, vlan_interface, spine=True):
        client_list = self.select_clients(spine=spine)

        for client in client_list:
            exist = client.get_interface("vlan" + vlan_interface.vlan_id)
            if not exist:
                client.configure_vlan(vlan_interface)

    def ensure_vlan_by_desc(self, vlan_interface, spine=True):
        pass

    def ensure_port_channel(self, port_channel, spine=True):
        client_list = self.select_clients(spine=spine)

        for client in client_list:
            exist = client.get_interface("vlan" + port_channel.channel_id)
            if not exist:
                client.configure_vlan(port_channel)

    def ensure_port_channel_by_desc(self, port_channel, spine=True):
        pass

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

    def get_available_interface(self, if_type=Interface.Type.VLan, spine=True):
        # determine spines or leaves
        client_list = self.select_clients(spine=spine)

        # get all interfaces for each client
        interfaces_for_clients = {}
        for client in client_list:
            interfaces_for_clients[client.mgmt_ip] = client.get_all_interfaces(if_type)

        # put all interface ids from all spine/leaf clients in a set
        interface_set = set()
        for _, interfaces in interfaces_for_clients.items():
            for interface in interfaces:
                if_id = Interface.extract_numeric_id(if_type, interface["name"])
                interface_set.add(if_id)

        # find a hole (available) port channel id
        return self.find_hole(sorted(interface_set))

    def configure_vlan(self, vlan_interface, address=None, spine=True):
        self.select_clients(address, spine)




