from unittest import TestCase
import json
from os10_fe_networking.agent.rest_conf.border_gateway_protocol import *


def prettyPrint(obj):
    print(json.dumps(obj, indent=4))


class TestBorderGatewayProtocol(TestCase):

    def setUp(self):
        pass

    def test_timers(self):
        timers = Timers(1, 3)
        timers_content = timers.content()

        prettyPrint(timers_content)

        self.assertEqual(timers_content['config-keepalive'], 1)
        self.assertEqual(timers_content['config-hold-time'], 3)

    def test_router_at_common_config(self):
        route_at_common_config = RouterAtCommonConfig(True)
        content = route_at_common_config.content()
        prettyPrint(content)

        self.assertEqual(content["redistribute-connected"]["enable"], [])

    def test_ipv4_unicast(self):
        ipv4_unicast = Ipv4Unicast(True)
        content = ipv4_unicast.content()
        prettyPrint(content)

        self.assertEqual(content["next-hop-self"], True)

    def test_neighbor(self):
        neighbor = Neighbor(address="10.250.0.2",
                            desc="neighbor description",
                            fall_over=True,
                            remote_as=4200008194,
                            timers=Timers(1, 3),
                            shutdown=False,
                            ipv4_unicast=Ipv4Unicast(True),
                            ebpg_multihop=4)
        content = neighbor.content()
        prettyPrint(content)

    def test_virtual_route_forwarding(self):
        vrf = VirtualRoutingForwarding(name="Customer1",
                                       local_as_number=None,
                                       best_path_as_path_multipath_relax=True,
                                       graceful_restart=None,
                                       router_id="10.250.0.3",
                                       router_at_common_config=RouterAtCommonConfig(True),
                                       neighbors=[
                                           Neighbor(address="10.250.0.2",
                                                    desc="neighbor description",
                                                    fall_over=True,
                                                    remote_as=4200008194,
                                                    timers=Timers(1, 3),
                                                    shutdown=False,
                                                    ipv4_unicast=Ipv4Unicast(True),
                                                    ebpg_multihop=4)
                                       ])
        content = vrf.content()
        prettyPrint(content)

    def test_border_gateway_protocol(self):
        bgp = BorderGatewayProtocol([
            VirtualRoutingForwarding(name="default",
                                     local_as_number="4200008194",
                                     neighbors=[
                                         Neighbor(address="10.250.0.2",
                                                  timers=Timers(1, 3)),
                                         Neighbor(address="169.254.114.201",
                                                  timers=Timers(1, 3)),
                                         Neighbor(address="10.3.0.2"),
                                     ]),
            VirtualRoutingForwarding(name="Customer1",
                                     best_path_as_path_multipath_relax=True,
                                     router_id="10.250.0.3",
                                     router_at_common_config=RouterAtCommonConfig(True),
                                     neighbors=[
                                         Neighbor(address="10.250.0.2",
                                                  fall_over=True,
                                                  remote_as=4200008194,
                                                  timers=Timers(1, 3),
                                                  shutdown=False,
                                                  ipv4_unicast=Ipv4Unicast(True)),
                                         Neighbor(address="169.254.45.161",
                                                  desc="Google-VL2001-UL-us-east4-z2-pod1-1",
                                                  ebpg_multihop=4,
                                                  fall_over=True,
                                                  remote_as=4200008193,
                                                  timers=Timers(20, 60),
                                                  shutdown=False),
                                         Neighbor(address="169.254.10.249",
                                                  desc="Google-VL2051-UL-us-east4-z2-pod1-1",
                                                  ebpg_multihop=4,
                                                  fall_over=True,
                                                  remote_as=4200008193,
                                                  timers=Timers(20, 60),
                                                  shutdown=False)
                                     ]),
            VirtualRoutingForwarding(name="Customer2",
                                     best_path_as_path_multipath_relax=True,
                                     graceful_restart=True,
                                     router_id="10.3.0.3",
                                     router_at_common_config=RouterAtCommonConfig(True),
                                     neighbors=[
                                         Neighbor(address="10.3.0.2",
                                                  fall_over=True,
                                                  remote_as=4200008194,
                                                  timers=Timers(1, 3),
                                                  shutdown=False,
                                                  ipv4_unicast=Ipv4Unicast(True)),
                                         Neighbor(address="169.254.223.137",
                                                  desc="Google-VL2002-UL-us-east4-z1-pod1-0",
                                                  ebpg_multihop=4,
                                                  fall_over=True,
                                                  local_as=4200008194,
                                                  remote_as=4200008193,
                                                  timers=Timers(1, 3),
                                                  shutdown=False)
                                     ])
        ])

        content = bgp.content()
        prettyPrint(content)

