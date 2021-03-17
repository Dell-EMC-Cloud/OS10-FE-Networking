class Interface:

    def __init__(self, desc, enabled):
        self.desc = desc
        self.enabled = enabled


class VVRPGroup:

    def __init__(self, vvrp_id, priority, virtual_addresses):
        self.vvrp_id = vvrp_id
        self.priority = priority
        self.virtual_addresses = virtual_addresses


class VLanInterface(Interface):

    def __init__(self, desc, enabled, vlan_id, vrf, address, vvrp_group):
        super(VLanInterface, self).__init__(desc, enabled)
        self.vlan_id = vlan_id
        self.vrf = vrf
        self.address = address
        self.vvrp_group = vvrp_group

        self.path = "/restconf/data/ietf-interfaces:interfaces"

    def create_request(self):
        return {
            "ietf-interfaces:interfaces": {
                "interface": [
                    {
                        "name": "vlan" + self.vlan_id,
                        "type": "iana-if-type:l2vlan"
                    }
                ]
            }
        }

    def desc_request(self):
        return {
            "ietf-interfaces:interfaces": {
                "interface": [
                    {
                        "name": "vlan" + self.vlan_id,
                        "description": self.desc
                    }
                ]
            }
        }

    def enable_request(self):
        return {
            "ietf-interfaces:interfaces": {
                "interface": [
                    {
                        "name": "vlan" + self.vlan_id,
                        "enabled": self.enabled
                    }
                ]
            }
        }

    def vrf_request(self):
        return {
            "ietf-interfaces:interfaces": {
                "interface": [
                    {
                        "name": "vlan" + self.vlan_id,
                        "dell-vrf:vrf": {
                            "name": self.vrf
                        }
                    }
                ]
            }
        }

    def address_request(self):
        return {
            "ietf-interfaces:interfaces": {
                "interface": [
                    {
                        "name": "vlan" + self.vlan_id,
                        "dell-ip:ipv4": {
                            "address": {
                                "primary-addr": self.address
                            }
                        }
                    }
                ]
            }
        }

    def vvrp_create_request(self):
        return {
            "ietf-interfaces:interfaces": {
                "interface": [
                    {
                        "name": "vlan" + self.vlan_id,
                        "dell-vrrp:vrrp": {

                        },
                        "dell-vrrp:vrrp-ipv4": {
                            "vrrp-instance": [
                                {
                                    "vrid": self.vvrp_group.vvrp_id
                                }
                            ]
                        }
                    }
                ]
            }
        }

    def vvrp_priority_request(self):
        return {
            "ietf-interfaces:interfaces": {
                "interface": [
                    {
                        "name": "vlan" + self.vlan_id,
                        "dell-vrrp:vrrp-ipv4": {
                            "vrrp-instance": [
                                {
                                    "vrid": self.vvrp_group.vvrp_id,
                                    "priority": self.vvrp_group.priority
                                }
                            ]
                        }
                    }
                ]
            }
        }

    def vvrp_virtual_addresses_request(self):
        return {
            "ietf-interfaces:interfaces": {
                "interface": [
                    {
                        "name": "vlan" + self.vlan_id,
                        "dell-vrrp:vrrp-ipv4": {
                            "vrrp-instance": [
                                {
                                    "vrid": self.vvrp_group.vvrp_id,
                                    "virtual-ip-address": self.vvrp_group.virtual_addresses
                                }
                            ]
                        }
                    }
                ]
            }
        }

