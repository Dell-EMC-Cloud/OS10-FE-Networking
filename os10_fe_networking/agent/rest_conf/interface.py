from enum import Enum

from requests import status_codes


class Interface:
    path = "/restconf/data/ietf-interfaces:interfaces"
    path_all = "/restconf/data/ietf-interfaces:interfaces/interface?content=config"
    path_by_name = "/restconf/data/ietf-interfaces:interfaces/interface/{name}"

    class Type:
        VLan = "iana-if-type:l2vlan"
        PortChannel = "iana-if-type:ieee8023adLag"
        Ethernet = "iana-if-type:ethernetCsmacd"

    _modes = {
        "trunk": "MODE_L2HYBRID",
        "access": "MODE_L2"
    }

    def __init__(self, desc, enabled, if_type):
        self.desc = desc
        self.enabled = enabled
        self.if_type = if_type

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def content(self):
        body = {
            "ietf-interfaces:interfaces": {
                "interface": []
            }
        }
        body["ietf-interfaces:interfaces"]["interface"].extend(self.interface_content())

        return body

    def interface_content(self) -> []:
        return []

    @staticmethod
    def handle_get_all(resp, if_type=None):
        interface_list = []
        if resp.status_code == status_codes.codes["ok"]:
            json_resp = resp.json()
            for interface in json_resp["ietf-interfaces:interface"]:
                if if_type is None or interface["type"] == if_type:
                    interface_list.append(interface)

        return interface_list

    @staticmethod
    def handle_get_all_by_type(resp):
        vlan_dict = {}
        port_channel_dict = {}
        ethernet_dict = {}

        if resp.status_code == status_codes.codes["ok"]:
            json_resp = resp.json()
            for interface in json_resp["ietf-interfaces:interface"]:
                if interface["type"] == Interface.Type.VLan:
                    vlan_dict[interface["name"]] = interface
                elif interface["type"] == Interface.Type.PortChannel:
                    port_channel_dict[interface["name"]] = interface
                elif interface["type"] == Interface.Type.Ethernet:
                    ethernet_dict[interface["name"]] = interface

        return vlan_dict, port_channel_dict, ethernet_dict

    @staticmethod
    def handle_get(resp):
        if resp.status_code == status_codes.codes["ok"]:
            return resp.json()
        else:
            return None


class VVRPGroup:

    def __init__(self, vvrp_id, priority, virtual_addresses):
        self.vvrp_id = vvrp_id
        self.priority = priority
        self.virtual_addresses = virtual_addresses

    def content(self):
        return {
            "vrrp-instance": [
                {
                    "vrid": self.vvrp_id,
                    "priority": self.priority,
                    "virtual-ip-address": self.virtual_addresses
                }
            ]
        }


class VLanInterface(Interface):
    class PortMode(Enum):
        ACCESS = "access"
        TRUNK = "trunk"

    def __init__(self, vlan_id, desc=None, enabled=None, vrf=None, address=None,
                 vvrp_group=None, port=None, port_detach=None, port_mode=None):
        super(VLanInterface, self).__init__(desc, enabled, Interface.Type.VLan)
        self.vlan_id = vlan_id
        self.vrf = vrf
        self.address = address
        self.vvrp_group = vvrp_group
        self.port = port
        self.port_detach = port_detach
        self.port_mode = port_mode

    def content(self):
        if self.port is not None and self.port_mode == self.PortMode.TRUNK:
            body = {
                "ietf-interfaces:interfaces": {
                    "dell-interface-range:interface-range": []
                }
            }

            body["ietf-interfaces:interfaces"]["dell-interface-range:interface-range"].extend(self.interface_content())

            return body
        else:
            return super(VLanInterface, self).content()

    def interface_content(self) -> []:
        body = {
            "name": "vlan" + self.vlan_id,
            "type": "iana-if-type:l2vlan"
        }

        # configure vlan for port-channel or ethernet interface
        if self.port is not None:
            if self.port_mode == self.PortMode.TRUNK:
                body["name"] = self.vlan_id
                body["config-template"] = {
                    "dell-interface:tagged-ports": [
                        self.port
                    ],
                    "delete-object": [
                        "tagged-ports"
                    ]
                }

                if self.port_detach is not True:
                    body["config-template"].pop("delete-object")

            elif self.port_mode == self.PortMode.ACCESS:
                body["dell-interface:untagged-ports"] = [
                    self.port
                ]
        # configure vlan for ethernet interface
        # elif self.ethernet_if is not None:
        #     body["dell-interface:untagged-ports"] = [
        #         "ethernet" + self.ethernet_if
        #     ]
        #     body.pop("type")
        else:
            if self.desc is not None:
                body["description"] = self.desc

            if self.enabled is not None:
                body["enabled"] = self.enabled

            if self.vrf is not None:
                body["dell-vrf:vrf"] = {
                    "name": self.vrf
                }

            if self.address is not None:
                body["dell-ip:ipv4"] = {
                    "address": {
                        "primary-addr": self.address
                    }
                }

            if self.vvrp_group is not None:
                body["dell-vrrp:vrrp-ipv4"] = self.vvrp_group.content()

        return [body]

    @staticmethod
    def extract_numeric_id(if_id):
        return int(if_id[4:])


class PortChannelInterface(Interface):
    path_get_untagged_vlan = "/restconf/data/dell-cms-internal:cms-interface-backptr/" \
                             "interface-in-candidate=port-channel{channel_id}"

    path_delete_untagged_vlan = "/restconf/data/ietf-interfaces:interfaces/interface={untagged_vlan}/" \
                                "dell-interface:untagged-ports=port-channel{channel_id}"

    path_get = "/restconf/data/ietf-interfaces:interfaces/interface=port-channel{channel_id}"

    class SpanningTree:

        def __init__(self, enabled, bpdu, edge_port):
            self.enabled = enabled
            self.bpdu = bpdu
            self.edge_port = edge_port

        def __bool__(self):
            for val in self.__dict__.values():
                if val is not None:
                    return True
            return False

        def content(self):
            body = {
                "br-index": 0,
            }

            if self.enabled is False:
                body["enable"] = str(self.enabled).lower()

            if self.bpdu is True:
                if not body.get("config"):
                    body["config"] = {}

                body["config"]["bpdu-guard"] = "enable"

            if self.edge_port is True:
                if not body.get("config"):
                    body["config"] = {}

                body["config"]["edge-port-basic"] = "enable"

            return body

    class LACPFallback:

        def __init__(self, enabled, timeout, preemption):
            self.enabled = enabled
            self.timeout = timeout
            self.preemption = preemption

        def __bool__(self):
            for val in self.__dict__.values():
                if val is not None:
                    return True
            return False

        def content(self):
            body = {}

            if self.enabled is True:
                body["enable"] = True

            if self.timeout is not None:
                body["timeout"] = self.timeout

            if self.preemption is False:
                body["port-preempt"] = False

            return body

    def __init__(self, channel_id, desc=None, enabled=None, mode=None, access_vlan_id=None, trunk_allowed_vlan_ids=None,
                 mtu=None, vlt_port_channel_id=None, spanning_tree=None, bpdu=None, edge_port=None, lacp_fallback=None,
                 lacp_timeout=None, lacp_preempt=None, ethernet_if=None):
        super(PortChannelInterface, self).__init__(desc=desc, enabled=enabled, if_type=Interface.Type.PortChannel)
        self.channel_id = channel_id
        self.mode = mode
        self.access_vlan_id = access_vlan_id
        self.trunk_allowed_vlan_ids = trunk_allowed_vlan_ids
        self.mtu = mtu
        self.vlt_port_channel_id = vlt_port_channel_id
        self.spanning_tree = PortChannelInterface.SpanningTree(spanning_tree, bpdu, edge_port)
        self.lacp = PortChannelInterface.LACPFallback(lacp_fallback, lacp_timeout, lacp_preempt)
        self.ethernet_if = ethernet_if

    def interface_content(self) -> []:
        body = {
            "name": "port-channel" + self.channel_id,
            "type": "iana-if-type:ieee8023adLag"
        }

        # configure port-channel for ethernet interface
        if self.ethernet_if is not None:
            body["dell-interface:lag-mode"] = "DYNAMIC"
            body["dell-interface:member-ports"] = [
                {
                    "name": "ethernet" + self.ethernet_if,
                    "lacp-mode": "ACTIVE"
                }
            ]
        else:
            if self.enabled is not None:
                body["enabled"] = self.enabled

            if self.mode is not None:
                body["dell-interface:mode"] = self._modes[self.mode]

            if self.desc is not None:
                body["description"] = self.desc

            if self.spanning_tree:
                body["dell-xstp:xstp-cfg"] = {
                    "interface-common": [
                        self.spanning_tree.content()
                    ]
                }

            if self.mtu is not None:
                body["dell-interface:mtu"] = self.mtu

            if self.vlt_port_channel_id is not None:
                body["dell-vlt:vlt"] = {
                    "vlt-id": self.vlt_port_channel_id
                }

            if self.lacp:
                body["dell-lacp:lacp-fallback"] = self.lacp.content()

        return [body]

    @staticmethod
    def parse_untagged_vlan(resp):
        untagged_vlan = None
        if resp.status_code == status_codes.codes["ok"]:
            json_resp = resp.json()
            if "dell-cms-internal:interface-in-candidate" in json_resp and \
                    "untagged-vlan" in json_resp["dell-cms-internal:interface-in-candidate"][0]:
                untagged_vlan = json_resp["dell-cms-internal:interface-in-candidate"][0]["untagged-vlan"]
        return untagged_vlan

    @staticmethod
    def extract_numeric_id(if_id):
        return int(if_id[12:])


class EthernetInterface(Interface):
    path_detach_port = "/restconf/data/ietf-interfaces:interfaces/interface={interface}/" \
                               "dell-interface:member-ports=ethernet{eif_id}"

    def __init__(self, eif_id, desc=None, enabled=None, mode=None, access_vlan_id=None, trunk_allowed_vlan_ids=None,
                 mtu=None, flow_control_receive=None, flow_control_transmit=None, channel_group=None,
                 disable_switch_port=None):
        super(EthernetInterface, self).__init__(desc=desc, enabled=enabled, if_type=Interface.Type.Ethernet)
        self.eif_id = eif_id
        self.mode = mode
        self.access_vlan_id = access_vlan_id
        self.trunk_allowed_vlan_ids = trunk_allowed_vlan_ids
        self.mtu = mtu
        self.flow_control_receive = flow_control_receive
        self.flow_control_transmit = flow_control_transmit
        self.channel_group = channel_group
        self.disable_switch_port = disable_switch_port

    def interface_content(self) -> []:
        body = {
            "name": "ethernet" + self.eif_id,
            "type": "iana-if-type:ethernetCsmacd"
        }

        if self.enabled is not None:
            body["enabled"] = self.enabled

        if self.desc is not None:
            body["description"] = self.desc

        if self.mtu is not None:
            body["dell-interface:mtu"] = self.mtu

        if self.mode is not None:
            body["dell-interface:mode"] = self._modes[self.mode]

        if self.flow_control_receive is not None:
            body["dell-qos:qos-cfg"] = {
                "flow-control-rx": self.flow_control_receive
            }

        if self.flow_control_transmit is not None:
            body["dell-qos:qos-cfg"] = {
                "flow-control-tx": self.flow_control_transmit
            }

        if self.disable_switch_port is True:
            body["dell-interface:mode"] = "MODE_L2DISABLED"

        return [body]

    @staticmethod
    def extract_numeric_id(if_id):
        return int(if_id[8:])
