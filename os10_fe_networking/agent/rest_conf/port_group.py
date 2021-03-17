class PortGroup:

    def __init__(self, pg_id, profile, ports=None):
        self.pg_id = pg_id
        self.profile = profile
        self.ports = ports
        self.path = "/restconf/data/dell-port-group:port-groups"

    def create_request(self):
        return {
            "dell-port-group:port-groups": {
                "hybrid-group": [
                    {
                        "id": "port-group" + self.pg_id
                    }
                ]
            }
        }

    def profile_request(self):
        return {
            "dell-port-group:port-groups": {
                "hybrid-group": [
                    {
                        "id": "port-group" + self.pg_id,
                        "profile": self.profile
                    }
                ]
            }
        }

    def ports_request(self):
        body = {
            "dell-port-group:port-groups": {
                "hybrid-group": [
                    {
                        "id": "port-group" + self.pg_id,
                        "port": []
                    }
                ]
            }
        }

        for port in self.ports:
            port_body = {
                "port-id": "phy-eth" + port["id"],
                "phy-mode": "ETHERNET",
                "breakout-mode": "BREAKOUT_1x1",
                "port-speed": port["eth_mode"]
            }
            body["dell-port-group:port-groups"]["hybrid-group"][0]["port"].append(port_body)

        return body


