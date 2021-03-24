from requests import status_codes


class Interface:

    path = "/restconf/data/ietf-interfaces:interfaces"
    path_get_all = "/restconf/data/ietf-interfaces:interfaces/interface?content=config"

    class Type:
        VLan = "iana-if-type:l2vlan"
        PortChannel = "iana-if-type:ieee8023adLag"
        Ethernet = "iana-if-type:ethernetCsmacd"

    def __init__(self, desc, enabled, if_type):
        self.desc = desc
        self.enabled = enabled
        self.if_type = if_type

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
    def extract_numeric_id(if_type, if_id):
        if if_type == Interface.Type.VLan:
            return VLanInterface.extract_numeric_id(if_id)
        elif if_type == Interface.Type.PortChannel:
            return PortChannelInterface.extract_numeric_id(if_id)
        elif if_type == Interface.Type.Ethernet:
            return EthernetInterface.extract_numeric_id(if_id)


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

    def __init__(self, vlan_id, desc=None, enabled=None, vrf=None, address=None,
                 vvrp_group=None, port_channel=None, ethernet_if=None):
        super(VLanInterface, self).__init__(desc, enabled, Interface.Type.VLan)
        self.vlan_id = vlan_id
        self.vrf = vrf
        self.address = address
        self.vvrp_group = vvrp_group
        self.port_channel = port_channel
        self.ethernet_if = ethernet_if

    def content(self):
        if "," in self.vlan_id or "-" in self.vlan_id:
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

        # configure vlan for port-channel
        if self.port_channel is not None:
            if "," in self.vlan_id or "-" in self.vlan_id:
                body["name"] = self.vlan_id
                body["config-template"] = {
                    "dell-interface:tagged-ports": [
                        "port-channel" + self.port_channel
                    ]
                }
            else:
                body["dell-interface:untagged-ports"] = [
                    "port-channel" + self.port_channel
                ]
        # configure vlan for ethernet interface
        elif self.ethernet_if is not None:
            body["dell-interface:untagged-ports"] = [
                "ethernet" + self.ethernet_if
            ]
            body.pop("type")
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

    def __init__(self, channel_id, desc=None, enabled=None, mode=None, access_vlan_id=None,
                 trunk_allowed_vlan_ids=None, mtu=None, vlt_port_channel_id=None, spanning_tree=None, ethernet_if=None):
        super(PortChannelInterface, self).__init__(desc=desc, enabled=enabled, if_type=Interface.Type.PortChannel)
        self.channel_id = channel_id
        self.mode = mode
        self.access_vlan_id = access_vlan_id
        self.trunk_allowed_vlan_ids = trunk_allowed_vlan_ids
        self.mtu = mtu
        self.vlt_port_channel_id = vlt_port_channel_id
        self.spanning_tree = spanning_tree
        self.ethernet_if = ethernet_if

    _modes = {
        "trunk": "MODE_L2HYBRID",
        "access": "MODE_L2"
    }

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

            if self.spanning_tree is not None:
                body["dell-xstp:xstp-cfg"] = {
                    "interface-common": [
                        {
                            "br-index": 0,
                            "enable": self.spanning_tree
                        }
                    ]
                }

            if self.mtu is not None:
                body["dell-interface:mtu"] = self.mtu

            if self.vlt_port_channel_id is not None:
                body["dell-vlt:vlt"] = {
                    "vlt-id": self.vlt_port_channel_id
                }

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

    def __init__(self, eif_id, desc=None, enabled=None, access_vlan_id=None, mtu=None, flow_control_receive=None,
                 flow_control_transmit=None, channel_group=None, disable_switch_port=None):
        super(EthernetInterface, self).__init__(desc=desc, enabled=enabled, if_type=Interface.Type.Ethernet)
        self.eif_id = eif_id
        self.access_vlan_id = access_vlan_id
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
        return int(if_id[12:])