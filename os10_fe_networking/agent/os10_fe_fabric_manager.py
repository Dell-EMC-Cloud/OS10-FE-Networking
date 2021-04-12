import base64
from enum import Enum

from os10_fe_networking.agent.os10_fe_restconf_client import OS10FERestConfClient
from os10_fe_networking.agent.rest_conf.interface import Interface, VLanInterface, PortChannelInterface, \
    EthernetInterface


class OS10FEFabricManager:
    class Category(Enum):
        SPINE = "spine"
        LEAF = "leaf"

    def __init__(self, conf):
        self.address = conf.FRONTEND_SWITCH_FABRIC.switch_ip
        self.peer_address = None
        self.category = self.Category.LEAF if conf.FRONTEND_SWITCH_FABRIC.category == "leaf" else self.Category.SPINE
        self.enable_port_channel = conf.FRONTEND_SWITCH_FABRIC.enable_port_channel
        self.client = OS10FERestConfClient(self.address,
                                           conf.FRONTEND_SWITCH_FABRIC.username,
                                           self._decode_password(conf.FRONTEND_SWITCH_FABRIC.password))

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

    def _match_pair(self, address):
        return self._match_switch(address) or self._match_peer(address)

    def _match_peer(self, address):
        return address == self.peer_address

    def _match_switch(self, address):
        return address == self.address

    @staticmethod
    def _get_interface_from_cache(if_id, desc, interfaces, if_type):
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

    def _calc_port_channel_id(self, ethernet_interface):
        """
        ethernet1/2/3:4 ==> 3
        """
        return ethernet_interface.split("/")[-1].split(":")[0]

    @staticmethod
    def _check_ethernet_interface_id(eif_id):
        return eif_id[8:] if "ethernet" in eif_id else eif_id

    # TODO(Phil Zhang), no port channel version should be supported in the future
    def ensure_configuration(self, switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode):
        if not self._match_switch(switch_ip):
            return
        # get all interfaces by type
        all_interfaces = self._get_all_interfaces_by_type()

        vlan_if = self._ensure_vlan(cluster, all_interfaces, vlan)

        port = vlan
        if self.enable_port_channel:
            port = self._ensure_port_channel(all_interfaces, switch_ip, cluster, vlan, vlan_if,
                                             ethernet_interface, preemption)

        self._ensure_ethernet(cluster, ethernet_interface, port, access_mode)

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

    def _ensure_port_channel(self, all_interfaces, switch_ip, cluster, vlan, vlan_if, ethernet_interface, preemption):
        # ensure port-channel
        port_channel_id = self._calc_port_channel_id(ethernet_interface)
        port_channel_if = self._get_interface_from_cache("port-channel" + port_channel_id, cluster, all_interfaces,
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

    def _ensure_vlan(self, cluster, all_interfaces, vlan):
        vlan_if = self._get_interface_from_cache("vlan%s" % vlan, cluster, all_interfaces, Interface.Type.VLan)
        if vlan_if is None:
            self.client.configure_vlan(VLanInterface(vlan_id=vlan,
                                                     desc=cluster,
                                                     enabled=True))
        return vlan_if

    def release_ethernet_interface(self, ethernet_interface, vlan, access_mode):
        if self.enable_port_channel:
            port_channel_id = "port-channel" + self._calc_port_channel_id(ethernet_interface)
            ethernet_interface = self._check_ethernet_interface_id(ethernet_interface)
            self.client.detach_port_channel_from_ethernet_interface(ethernet_interface, port_channel_id)
        else:
            self.client.detach_vlan_from_ethernet_interface(ethernet_interface, vlan, access_mode)

    def delete_port_channel_vlan(self, ethernet_interface, vlan):
        if self.enable_port_channel:
            port_channel_id = self._calc_port_channel_id(ethernet_interface)
            self.client.delete_interface("port-channel" + port_channel_id)
        self.client.delete_interface("vlan" + vlan)
