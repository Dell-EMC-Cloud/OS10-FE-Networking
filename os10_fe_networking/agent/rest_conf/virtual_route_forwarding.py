class IPVirtualRouteForwarding:

    path = {
        "vrf-config": "/restconf/data/dell-vrf:vrf-config",
        "routing": "/restconf/data/dell-routing:routing",
        "dhcp-relay-vrf-configs": "/restconf/data/dell-dhcp:dhcp-relay-vrf-configs"
    }

    path_by_name = {
        "vrf-config": "/restconf/data/dell-vrf:vrf-config/vrf/{name}",
        "routing": "/restconf/data/dell-routing:routing/instance/{name}",
        "dhcp-relay-vrf-configs": "/restconf/data/dell-dhcp:dhcp-relay-vrf-configs/instance/{name}"
    }

    def __init__(self, name):
        self.name = name

    def vrf_config_request(self):
        return {
            "dell-vrf:vrf-config": {
                "vrf": [
                    {
                        "vrf-name": self.name
                    }
                ]
            }
        }

    def routing_request(self):
        return {
            "dell-routing:routing": {
                "instance": [
                    {
                        "vrf-name": self.name
                    }
                ]
            }
        }

    def dhcp_relay_vrf_config(self):
        return {
            "dell-dhcp:dhcp-relay-vrf-configs": {
                "instance": [
                    {
                        "vrf-name": self.name
                    }
                ]
            }
        }
