class Timers:

    def __init__(self, keep_alive, hold_time):
        self.keep_alive = keep_alive
        self.hold_time = hold_time

    def content(self):
        return {
            "config-keepalive": self.keep_alive,
            "config-hold-time": self.hold_time
        }


class RouterAtCommonConfig:

    def __init__(self, redistribute_connected=True):
        self.redistribute_connected = redistribute_connected
        self.key = "ipv4-unicast"

    def content(self):
        body = {
            "redistribute-connected": {
                "enable": []
            }
        }

        if self.redistribute_connected is True:
            return body
        else:
            return None


class Ipv4Unicast:

    def __init__(self, next_hop_self=True):
        self.next_hop_self = next_hop_self
        self.key = "ipv4-unicast"

    def content(self):
        return {
            "next-hop-self": self.next_hop_self
        }


class Neighbor:

    def __init__(self, address, desc=None, fall_over=None, remote_as=None, local_as=None, timers=None, shutdown=None,
                 ipv4_unicast=None, ebpg_multihop=None):
        self.address = address
        self.desc = desc
        self.fall_over = fall_over
        self.remote_as = remote_as
        self.local_as = local_as
        self.timers = timers
        self.shutdown = shutdown
        self.ipv4_unicast = ipv4_unicast
        self.ebpg_multihop = ebpg_multihop
        self.key = "peer-config"

    def content(self):
        body = {
            "remote-address": self.address
        }

        if self.desc is not None:
            body["description"] = self.desc

        if self.fall_over is True:
            body["fall-over"] = []

        if self.local_as is not None:
            body["local-as"] = {
                "as-number": self.local_as
            }

        if self.remote_as is not None:
            body["remote-as"] = self.remote_as

        if self.timers is not None:
            body["timers"] = self.timers.content()

        if self.shutdown is not None:
            body["shutdown-status"] = self.shutdown

        if self.ipv4_unicast is not None:
            body["ipv4-unicast"] = self.ipv4_unicast.content()

        if self.ebpg_multihop is not None:
            body["ebgp-multihop-count"] = self.ebpg_multihop

        return body


class VirtualRoutingForwarding:

    def __init__(self, name, local_as_number=None, best_path_as_path_multipath_relax=None, graceful_restart=None,
                 router_id=None, router_at_common_config=None, neighbors=None):
        self.name = name
        self.local_as_number = local_as_number
        self.best_path_as_path_multipath_relax = best_path_as_path_multipath_relax
        self.graceful_restart = graceful_restart
        self.router_id = router_id
        self.router_at_common_config = router_at_common_config
        self.neighbors = neighbors

    def content(self):
        body = {
            "vrf-name": self.name
        }

        if self.local_as_number is not None:
            body["local-as-number"] = self.local_as_number

        if self.best_path_as_path_multipath_relax is True:
            body["bestpath"] = {
                "aspath-multipath-relax": []
            }

        if self.router_id is not None:
            body["router-id"] = self.router_id

        if self.router_at_common_config is not None:
            body["ipv4-unicast"] = self.router_at_common_config.content()

        if self.graceful_restart is True:
            body["graceful-restart"] = {
                "helper-only": self.graceful_restart
            }

        if self.neighbors is not None:
            body["peer-config"] = []
            for nb in self.neighbors:
                body["peer-config"].append(nb.content())

        return body


class BorderGatewayProtocol:

    path = "/restconf/data/dell-bgp:bgp-router"

    def __init__(self, vrfs):
        self.vrfs = vrfs

    def content(self):
        body = {
            "dell-bgp:bgp-router": {
                "vrf": []
            }
        }

        for vrf in self.vrfs:
            body["dell-bgp:bgp-router"]["vrf"].append(vrf.content())

        return body
