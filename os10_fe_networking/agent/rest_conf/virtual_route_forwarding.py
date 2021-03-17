class VirtualRouteForwarding:

    def __init__(self, name):
        self.name = name
        self.path = {
            "vrf-config": "/restconf/data/dell-vrf:vrf-config",
            "routing": "/restconf/data/dell-routing:routing",
            "dhcp-relay-vrf-configs": "/restconf/data/dell-dhcp:dhcp-relay-vrf-configs"
        }

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
