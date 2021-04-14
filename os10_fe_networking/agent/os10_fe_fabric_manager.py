import base64
from enum import Enum

from os10_fe_networking.agent.os10_fe_restconf_client import OS10FERestConfClient
from os10_fe_networking.agent.rest_conf.interface import Interface, VLanInterface, PortChannelInterface, \
    EthernetInterface


class OS10FEFabricManager:
    class Category(Enum):
        SPINE = "spine"
        LEAF = "leaf"

    @staticmethod
    def create(conf):
        if conf.FRONTEND_SWITCH_FABRIC.category == OS10FEFabricManager.Category.LEAF.value:
            return LeafManager(conf)
        elif conf.FRONTEND_SWITCH_FABRIC.category == OS10FEFabricManager.Category.SPINE.value:
            return SpineManager(conf)

    def __init__(self, conf):
        self.address = conf.FRONTEND_SWITCH_FABRIC.switch_ip
        self.enable_port_channel = conf.FRONTEND_SWITCH_FABRIC.enable_port_channel
        self.client = OS10FERestConfClient(self.address,
                                           conf.FRONTEND_SWITCH_FABRIC.username,
                                           self._decode_password(conf.FRONTEND_SWITCH_FABRIC.password))
        self.port_channel_ethernet_mapping = conf.FRONTEND_SWITCH_FABRIC.port_channel_ethernet_mapping

    @staticmethod
    def _decode_password(password):
        return base64.b64decode(password).decode()

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

    @staticmethod
    def _get_interface_from_cache(if_id, interfaces, if_type):
        for _, interface in interfaces[if_type].items():
            if interface["name"] == if_id:
                return interface

        return None

    @staticmethod
    def _get_interface_from_cache_by_desc(desc, interface_dict, if_type):
        for _, interface in interface_dict[if_type].items():
            if interface.get("description") == desc:
                return interface

        return None

    @staticmethod
    def _check_ethernet_interface_id(eif_id):
        return eif_id[8:] if "ethernet" in eif_id else eif_id

    def _match_switch(self, address):
        return address == self.address

    def _get_all_interfaces_by_type(self):
        """
        :return:
            {
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
            }
        """
        vlan_dict, port_channel_dict, ethernet_dict = self.client.get_all_interfaces_by_type()
        return {
            Interface.Type.VLan: vlan_dict,
            Interface.Type.PortChannel: port_channel_dict,
            Interface.Type.Ethernet: ethernet_dict
        }

    def _calc_available_port_channel(self, all_interfaces):
        port_channel_set = set()
        for _, interface_dict in all_interfaces.items():
            for _, interface in interface_dict[Interface.Type.PortChannel].items():
                if_id = PortChannelInterface.extract_numeric_id(interface["name"])
                port_channel_set.add(if_id)

        # find a hole (available) port channel id
        return self.find_hole(sorted(port_channel_set))

    @staticmethod
    def _calc_port_channel_id(ethernet_interface):
        """
        ethernet1/2/3:4 ==> 3
        """
        return ethernet_interface.split("/")[-1].split(":")[0]

    def ensure_configuration(self, switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode):
        pass

    @staticmethod
    def _parse_preconfig_link(port_channel_ethernet_mapping):
        config = {}
        for _, port_channel in port_channel_ethernet_mapping.items():
            config[port_channel] = []

        for ethernet_interface, port_channel in port_channel_ethernet_mapping.items():
            config[port_channel].append(ethernet_interface)

        return config

    def _ensure_preconfig_link(self, all_interfaces, port_channel_ethernet_mapping, vlan, vlan_if):
        link_config = self._parse_preconfig_link(port_channel_ethernet_mapping)

        for port_channel_name, eif_list in link_config.items():
            # ensure port channel exists
            port_channel_id = str(PortChannelInterface.extract_numeric_id(port_channel_name))

            port_channel_if = self._get_interface_from_cache(port_channel_name, all_interfaces,
                                                             Interface.Type.PortChannel)

            # port channel doesn't exist
            if port_channel_if is None:
                # create port channel
                self.client.configure_port_channel(PortChannelInterface(channel_id=str(port_channel_id),
                                                                        enabled=True,
                                                                        mode="trunk",
                                                                        mtu=9216,
                                                                        vlt_port_channel_id=port_channel_id))
                # attach ethernet interfaces to port channel
                for eif in eif_list:
                    eif_id = self._check_ethernet_interface_id(eif)
                    self.client.configure_ethernet_interface(EthernetInterface(eif_id=eif_id,
                                                                               enabled=True,
                                                                               mtu=9216,
                                                                               flow_control_receive=True,
                                                                               flow_control_transmit=False,
                                                                               channel_group=port_channel_id,
                                                                               disable_switch_port=True))
            # port channel exists
            else:
                # determine ethernet interfaces to be attached
                if port_channel_if.get("dell-interface:member-ports"):
                    for member_port in port_channel_if["dell-interface:member-ports"]:
                        if member_port["name"] in eif_list:
                            eif_list.remove(member_port["name"])

                # attach ethernet interfaces to port channel
                for eif in eif_list:
                    eif_id = self._check_ethernet_interface_id(eif)
                    self.client.configure_ethernet_interface(EthernetInterface(eif_id=eif_id,
                                                                               enabled=True,
                                                                               mtu=9216,
                                                                               flow_control_receive=True,
                                                                               flow_control_transmit=False,
                                                                               channel_group=port_channel_id,
                                                                               disable_switch_port=True))

            # attach port channel to vlan in trunk mode
            if not vlan_if or \
                    not vlan_if.get("dell-interface:tagged-ports") or \
                    port_channel_name not in vlan_if["dell-interface:tagged-ports"]:
                self.client.configure_vlan(
                    VLanInterface(vlan_id=str(vlan),
                                  port=port_channel_name,
                                  port_mode=VLanInterface.PortMode.TRUNK))

    def _ensure_vlan(self, cluster, all_interfaces, vlan):
        vlan_if = self._get_interface_from_cache("vlan%s" % vlan, all_interfaces, Interface.Type.VLan)
        if vlan_if is None:
            self.client.configure_vlan(VLanInterface(vlan_id=str(vlan),
                                                     desc=cluster,
                                                     enabled=True))
        return vlan_if

    def detach_port_from_vlan(self, ethernet_interface, vlan, access_mode):
        port_id = "port-channel" + self._calc_port_channel_id(ethernet_interface) if self.enable_port_channel \
            else ethernet_interface
        self.client.detach_port_from_vlan(port_id, vlan, access_mode)

    def delete_port_channel_vlan(self, ethernet_interface, vlan):
        if self.enable_port_channel:
            port_channel_id = self._calc_port_channel_id(ethernet_interface)
            self.client.delete_interface("port-channel" + port_channel_id)
        self.client.delete_interface("vlan" + vlan)


class SpineManager(OS10FEFabricManager):

    def _ensure_configuration_for_spine(self, ethernet_interface, vlan, cluster, preemption, access_mode):
        # get all interfaces by type
        all_interfaces = self._get_all_interfaces_by_type()

        # ensure the configuration on the link to power scale server
        vlan_if = self._ensure_vlan(cluster, all_interfaces, vlan)

        # ensure the configuration on the link to spine switch
        self._ensure_preconfig_link(all_interfaces, self.port_channel_ethernet_mapping, vlan, vlan_if)

    def ensure_configuration(self, switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode):
        self._ensure_configuration_for_spine(ethernet_interface, vlan, cluster, preemption, access_mode)

    def detach_port_from_vlan(self, ethernet_interface, vlan, access_mode):
        pass


class LeafManager(OS10FEFabricManager):

    def ensure_configuration(self, switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode):
        if not self._match_switch(switch_ip):
            return

        self._ensure_configuration_for_leaf(ethernet_interface, vlan, cluster, preemption, access_mode)

    def _ensure_configuration_for_leaf(self, ethernet_interface, vlan, cluster, preemption, access_mode):
        # get all interfaces by type
        all_interfaces = self._get_all_interfaces_by_type()

        # ensure the configuration on the link to power scale server
        vlan_if = self._ensure_vlan(cluster, all_interfaces, vlan)

        port = vlan
        if self.enable_port_channel:
            port = self._ensure_port_channel(all_interfaces, cluster, vlan, vlan_if,
                                             ethernet_interface, preemption)

        self._ensure_ethernet(cluster, ethernet_interface, port, access_mode)

        # ensure the configuration on the link to spine switch
        self._ensure_preconfig_link(all_interfaces, self.port_channel_ethernet_mapping, vlan, vlan_if)

    def _ensure_ethernet(self, cluster, eif_id, port_id, access_mode):
        eif_id = self._check_ethernet_interface_id(eif_id)

        # configure ethernet interface with port-channel
        if self.enable_port_channel:
            self.client.configure_ethernet_interface(EthernetInterface(eif_id=eif_id,
                                                                       desc=cluster,
                                                                       enabled=True,
                                                                       mtu=1554,
                                                                       flow_control_receive=True,
                                                                       flow_control_transmit=False,
                                                                       channel_group=str(port_id),
                                                                       disable_switch_port=True))
        # configure ethernet interface with vlan directly
        else:
            ethernet_interface = EthernetInterface(eif_id=eif_id,
                                                   desc=cluster,
                                                   enabled=True,
                                                   mtu=1554,
                                                   flow_control_receive=True,
                                                   flow_control_transmit=False)
            if access_mode == "access":
                ethernet_interface.access_vlan_id = str(port_id)
            elif access_mode == "trunk":
                ethernet_interface.mode = "trunk"
                ethernet_interface.trunk_allowed_vlan_ids = str(port_id)
            self.client.configure_ethernet_interface(ethernet_interface)

    def _ensure_port_channel(self, all_interfaces, cluster, vlan, vlan_if, ethernet_interface, preemption):
        # ensure port-channel
        port_channel_id = self._calc_port_channel_id(ethernet_interface)
        port_channel_if = self._get_interface_from_cache("port-channel" + port_channel_id, all_interfaces,
                                                         Interface.Type.PortChannel)
        # port-channel doesn't exist, create
        if port_channel_if is None:

            # create port channel
            lacp_preempt = None if preemption else False
            self.client.configure_port_channel(PortChannelInterface(channel_id=str(port_channel_id),
                                                                    desc=cluster,
                                                                    enabled=True,
                                                                    mode="trunk",
                                                                    trunk_allowed_vlan_ids=vlan,
                                                                    mtu=9216,
                                                                    vlt_port_channel_id=port_channel_id,
                                                                    spanning_tree=None,
                                                                    bpdu=True,
                                                                    edge_port=True,
                                                                    lacp_fallback=True,
                                                                    lacp_timeout=10,
                                                                    lacp_preempt=lacp_preempt))
        # port-channel exists, make sure it's related to our VLan
        else:
            if not vlan_if.get("dell-interface:tagged-ports") or \
                    port_channel_if["name"] not in vlan_if["dell-interface:tagged-ports"]:
                self.client.configure_vlan(
                    VLanInterface(vlan_id=vlan, port=port_channel_if["name"]))
        return port_channel_id

