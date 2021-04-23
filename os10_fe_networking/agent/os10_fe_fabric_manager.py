import base64
from enum import Enum

from os10_fe_networking.agent.os10_fe_fabric_manager_callback import WriteMemoryCallback
from os10_fe_networking.agent.os10_fe_restconf_client import OS10FERestConfClient
from os10_fe_networking.agent.rest_conf.interface import Interface, VLanInterface, PortChannelInterface, \
    EthernetInterface


class RangeAllocator:

    def __init__(self, begin=125, end=128):
        self.begin = int(begin)
        self.end = int(end)

    def alloc(self, shift):
        if isinstance(shift, str):
            shift = int(shift)

        ret = self.begin + shift
        if ret > self.end:
            raise RuntimeError("unable to allocate in range {begin} - {end} for shift {shift}".format(begin=self.begin,
                                                                                                      end=self.end,
                                                                                                      shift=shift))
        return ret


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
        self.client = OS10FERestConfClient(self.address,
                                           conf.FRONTEND_SWITCH_FABRIC.username,
                                           self._decode_password(conf.FRONTEND_SWITCH_FABRIC.password))
        self.port_channel_ethernet_mapping = conf.FRONTEND_SWITCH_FABRIC.port_channel_ethernet_mapping
        self.link_port_channel_mapping = conf.FRONTEND_SWITCH_FABRIC.link_port_channel_mapping

        self.pg_alloc = RangeAllocator(conf.FRONTEND_SWITCH_FABRIC.pg_allocatable_range[0],
                                       conf.FRONTEND_SWITCH_FABRIC.pg_allocatable_range[1])

        self.callbacks = [WriteMemoryCallback(self.client)]

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

    def _run_callback(self, method_name):
        for callback in self.callbacks:
            getattr(callback, method_name)()

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
        ethernet1/2/3:4 ==> 4
        """
        slot = ethernet_interface.split("/")[-1].split(":")[1]
        slot = int(slot) - 1
        return str(self.pg_alloc.alloc(slot))

    @staticmethod
    def _parse_port_channel_ethernet_mapping(port_channel_ethernet_mapping):
        config = {}
        for _, port_channel in port_channel_ethernet_mapping.items():
            config[port_channel] = []

        for ethernet_interface, port_channel in port_channel_ethernet_mapping.items():
            config[port_channel].append(ethernet_interface)

        return config

    @staticmethod
    def _parse_link_port_channel_mapping(link_port_channel_mapping):
        config = {}
        for _, port_channel in link_port_channel_mapping.items():
            config[port_channel] = []

        for switch_ip, port_channel in link_port_channel_mapping.items():
            config[port_channel].append(switch_ip)

        return config

    def _should_attach(self, switch_ip, link_port_channel_config, port_channel):
        """
        Spine: switch_ip should be in the link that the port channel presents
        Leaf:  switch_ip equals to switch_ip, always true

        :param switch_ip:
        :param link_port_channel_config:
        :param port_channel:
        :return:
        """
        return switch_ip in link_port_channel_config[port_channel] or self._match_switch(switch_ip)

    def _ensure_preconfig_link(self, switch_ip, all_interfaces, port_channel_ethernet_mapping,
                               link_port_channel_mapping, vlan, vlan_if):
        port_channel_ethernet_config = self._parse_port_channel_ethernet_mapping(port_channel_ethernet_mapping)
        link_port_channel_config = self._parse_link_port_channel_mapping(link_port_channel_mapping)

        for port_channel_name, eif_list in port_channel_ethernet_config.items():
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

            if self._should_attach(switch_ip, link_port_channel_config, port_channel_name):
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

    def ensure_configuration(self, switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode,
                             enable_port_channel):
        self._run_callback("pre_ensure_configuration")
        if self._ensure_configuration(switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode,
                                      enable_port_channel):
            self._run_callback("post_ensure_configuration")

    def _ensure_configuration(self, switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode,
                              enable_port_channel):
        pass

    def detach_port_from_vlan(self, switch_ip, ethernet_interface, vlan, access_mode, enable_port_channel):
        self._run_callback("pre_detach_port_from_vlan")
        if self._detach_port_from_vlan(switch_ip, ethernet_interface, vlan, access_mode, enable_port_channel):
            self._run_callback("post_detach_port_from_vlan")

    def _detach_port_from_vlan(self, switch_ip, ethernet_interface, vlan, access_mode, enable_port_channel):
        pass

    def delete_vlan(self, switch_ip, ethernet_interface, vlan, enable_port_channel):
        self._run_callback("pre_delete_vlan")
        if self._delete_vlan(switch_ip, ethernet_interface, vlan, enable_port_channel):
            self._run_callback("post_delete_vlan")

    def _delete_vlan(self, switch_ip, ethernet_interface, vlan, enable_port_channel):
        pass


class SpineManager(OS10FEFabricManager):

    def _ensure_configuration_for_spine(self, switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode):
        # get all interfaces by type
        all_interfaces = self._get_all_interfaces_by_type()

        # ensure the configuration on the link to power scale server
        vlan_if = self._ensure_vlan(cluster, all_interfaces, vlan)

        # ensure the configuration on the link to spine switch
        self._ensure_preconfig_link(switch_ip, all_interfaces, self.port_channel_ethernet_mapping,
                                    self.link_port_channel_mapping, vlan, vlan_if)

    def _ensure_configuration(self, switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode,
                              enable_port_channel):
        self._ensure_configuration_for_spine(switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode)
        return True

    def _detach_port_from_vlan(self, switch_ip, ethernet_interface, vlan, access_mode, enable_port_channel):
        return False

    def _delete_vlan(self, switch_ip, ethernet_interface, vlan, enable_port_channel):
        self.client.delete_interface("vlan" + str(vlan))
        return True


class LeafManager(OS10FEFabricManager):

    def _ensure_configuration(self, switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode,
                              enable_port_channel):
        if not self._match_switch(switch_ip):
            return False

        self._ensure_configuration_for_leaf(switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode,
                                            enable_port_channel)

        return True

    def _ensure_configuration_for_leaf(self, switch_ip, ethernet_interface, vlan, cluster, preemption, access_mode,
                                       enable_port_channel):
        # get all interfaces by type
        all_interfaces = self._get_all_interfaces_by_type()

        # ensure the configuration on the link to power scale server
        vlan_if = self._ensure_vlan(cluster, all_interfaces, vlan)

        port = vlan
        if enable_port_channel:
            port = self._ensure_port_channel(all_interfaces, cluster, vlan, vlan_if,
                                             ethernet_interface, access_mode, preemption)

        self._ensure_ethernet(cluster, ethernet_interface, port, access_mode, enable_port_channel)

        # ensure the configuration on the link to spine switch
        self._ensure_preconfig_link(switch_ip, all_interfaces, self.port_channel_ethernet_mapping,
                                    self.link_port_channel_mapping, vlan, vlan_if)

    def _ensure_ethernet(self, cluster, eif_id, port_id, access_mode, enable_port_channel):
        eif_id = self._check_ethernet_interface_id(eif_id)

        # configure ethernet interface with port-channel
        if enable_port_channel:
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

    def _ensure_port_channel(self, all_interfaces, cluster, vlan, vlan_if, ethernet_interface, access_mode, preemption):
        # ensure port-channel
        port_channel_id = self._calc_port_channel_id(ethernet_interface)
        # port_channel_if = self._get_interface_from_cache("port-channel" + port_channel_id, all_interfaces,
        #                                                  Interface.Type.PortChannel)

        # configure port channel
        lacp_preempt = None if preemption else False
        port_channel = PortChannelInterface(channel_id=port_channel_id,
                                            desc=cluster,
                                            enabled=True,
                                            mtu=9216,
                                            vlt_port_channel_id=int(port_channel_id),
                                            spanning_tree=None,
                                            bpdu=True,
                                            edge_port=True,
                                            lacp_fallback=True,
                                            lacp_timeout=10,
                                            lacp_preempt=lacp_preempt)
        if access_mode == "access":
            port_channel.access_vlan_id = str(vlan)
        elif access_mode == "trunk":
            port_channel.mode = "trunk"
            port_channel.trunk_allowed_vlan_ids = str(vlan)

        self.client.configure_port_channel(port_channel)

        return port_channel_id

    def _detach_port_from_vlan(self, switch_ip, ethernet_interface, vlan, access_mode, enable_port_channel):
        if not self._match_switch(switch_ip):
            return False

        if enable_port_channel:
            port_channel_id = self._calc_port_channel_id(ethernet_interface)
            self.client.delete_interface("port-channel" + port_channel_id)
        else:
            self.client.detach_port_from_vlan(ethernet_interface, str(vlan), access_mode)

        return True

    def _delete_vlan(self, switch_ip, ethernet_interface, vlan, enable_port_channel):
        self.client.delete_interface("vlan" + str(vlan))

        return True
