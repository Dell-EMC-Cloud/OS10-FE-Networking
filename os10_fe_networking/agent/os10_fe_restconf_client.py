from urllib.parse import quote_plus

import requests
from requests import status_codes
from requests.auth import HTTPBasicAuth
from oslo_log import log as logging

from os10_fe_networking.agent.rest_conf.border_gateway_protocol import BorderGatewayProtocol
from os10_fe_networking.agent.rest_conf.port_group import PortGroup
from os10_fe_networking.agent.rest_conf.virtual_route_forwarding import IPVirtualRouteForwarding
from os10_fe_networking.agent.rest_conf.interface import VLanInterface, PortChannelInterface, EthernetInterface, \
    Interface

LOG = logging.getLogger(__name__)


class OS10FERestConfClient:

    def __init__(self, mgmt_ip, username="admin", password="D@ngerous1"):
        self.username = username
        self.password = password
        self.verify = False
        self.headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        self.mgmt_ip = mgmt_ip
        self.base_url = "https://" + mgmt_ip

    def _get(self, url, parameters):
        resp = requests.get(url,
                            params=parameters,
                            auth=HTTPBasicAuth(self.username, self.password),
                            verify=self.verify,
                            headers=self.headers)
        print(resp.json())
        return resp

    def _post(self, url, parameters, body):
        resp = requests.post(url,
                             params=parameters,
                             json=body,
                             auth=HTTPBasicAuth(self.username, self.password),
                             verify=self.verify,
                             headers=self.headers)
        print(resp)
        return resp

    def _put(self, url, parameters, body):
        resp = requests.put(url,
                            params=parameters,
                            json=body,
                            auth=HTTPBasicAuth(self.username, self.password),
                            verify=self.verify,
                            headers=self.headers)
        print(resp)
        return resp

    def _delete(self, url, parameters):
        resp = requests.delete(url,
                               params=parameters,
                               auth=HTTPBasicAuth(self.username, self.password),
                               verify=self.verify,
                               headers=self.headers)
        print(resp)
        return resp

    def _patch(self, url, parameters, body):
        resp = requests.patch(url,
                              params=parameters,
                              json=body,
                              auth=HTTPBasicAuth(self.username, self.password),
                              verify=self.verify,
                              headers=self.headers)
        print(resp)
        return resp

    def _get_error_message(self, resp):
        if "ietf-restconf:errors" in resp and "error" in resp["ietf-restconf:errors"] and \
                "error-message" in resp["ietf-restconf:errors"]["error"][0]:
            return resp["ietf-restconf:errors"]["error"][0]["error-message"]
        else:
            return None

    def _patch_and_post(self, url, parameters, body):
        resp = self._patch(url, parameters, body)
        if resp.status_code == status_codes.codes['not_found']:
            error_msg = self._get_error_message(resp.json())
            if error_msg == "require-instance test failed":
                # fallback to post, since object doesn't exist
                resp = self._post(url, parameters, body)

        return resp

    def create_port_group(self, pg_id, profile=None):
        pg = PortGroup(pg_id, profile)
        url = self.base_url + PortGroup.path
        resp = self._patch_and_post(url, None, pg.create_request())

        if not profile:
            resp = self._patch_and_post(url, None, pg.profile_request())

    def configure_port_group(self, pg_id, ports):
        pg = PortGroup(pg_id, None, ports)
        url = self.base_url + PortGroup.path
        resp = self._patch_and_post(url, None, pg.ports_request())

    def get_virtual_route_forwarding(self, name=None):
        resp1 = self._get(self.base_url +
                          IPVirtualRouteForwarding.path_by_name["vrf-config"].format(name=name), None)
        resp2 = self._get(self.base_url +
                          IPVirtualRouteForwarding.path_by_name["routing"].format(name=name), None)
        resp3 = self._get(self.base_url +
                          IPVirtualRouteForwarding.path_by_name["dhcp-relay-vrf-configs"].format(name=name), None)
        return resp1.status_code == status_codes.codes["ok"] and \
               resp2.status_code == status_codes.codes["ok"] and \
               resp3.status_code == status_codes.codes["ok"]

    def configure_virtual_route_forwarding(self, name):
        vrf = IPVirtualRouteForwarding(name)
        resp = self._patch_and_post(self.base_url + IPVirtualRouteForwarding.path["vrf-config"], None,
                                    vrf.vrf_config_request())
        resp = self._patch_and_post(self.base_url + IPVirtualRouteForwarding.path["routing"], None,
                                    vrf.routing_request())
        resp = self._patch_and_post(self.base_url + IPVirtualRouteForwarding.path["dhcp-relay-vrf-configs"], None,
                                    vrf.dhcp_relay_vrf_config())

    def delete_virtual_route_forwarding(self, name):
        resp = self._delete(self.base_url +
                            IPVirtualRouteForwarding.path_by_name["routing"].format(name=name), None)
        resp = self._delete(self.base_url +
                            IPVirtualRouteForwarding.path_by_name["dhcp-relay-vrf-configs"].format(name=name), None)
        resp = self._delete(self.base_url +
                            IPVirtualRouteForwarding.path_by_name["vrf-config"].format(name=name), None)

    def get_all_interfaces(self, if_type=None):
        url = self.base_url + Interface.path_all
        resp = self._get(url, None)

        return Interface.handle_get_all(resp, if_type)

    def get_all_interfaces_by_type(self):
        url = self.base_url + Interface.path_all
        resp = self._get(url, None)

        return Interface.handle_get_all_by_type(resp)

    def get_interface(self, name):
        url = self.base_url + Interface.path_by_name.format(name=name)
        resp = self._get(url, None)

        return Interface.handle_get(resp)

    def delete_interface(self, name):
        url = self.base_url + Interface.path_by_name.format(name=name)
        resp = self._delete(url, None)

        return resp.ok

    def configure_vlan(self, vlan_interface):
        url = self.base_url + VLanInterface.path
        resp = self._patch_and_post(url, None, vlan_interface.content())

        return resp

    def _get_untagged_vlan_from_port_channel(self, port_channel):
        url = self.base_url + PortChannelInterface.path_get_untagged_vlan.format(channel_id=port_channel.channel_id)
        resp = self._get(url, None)
        return port_channel.parse_untagged_vlan(resp)

    def _delete_untagged_vlan_in_port_channel(self, untagged_vlan, port_channel):
        url = self.base_url + PortChannelInterface.path_delete_untagged_vlan.format(untagged_vlan=untagged_vlan,
                                                                                    channel_id=port_channel.channel_id)
        resp = self._delete(url, None)
        return resp

    def configure_port_channel(self, port_channel):
        url = self.base_url + PortChannelInterface.path
        resp = self._patch_and_post(url, None, port_channel.content())

        if port_channel.access_vlan_id is not None:
            resp = self._patch_and_post(url, None, VLanInterface(vlan_id=port_channel.access_vlan_id,
                                                                 port_channel_mode=VLanInterface.PortChannelMode.ACCESS,
                                                                 port_channel=port_channel.channel_id,).content(),)
        # else:
        #     # switch port access vlan is auto-created, if there is no access_vlan_id in port_channel, delete it.
        #     untagged_vlan = self._get_untagged_vlan_from_port_channel(port_channel)
        #     if untagged_vlan is not None:
        #         # Delete this untagged vlan
        #         self._delete_untagged_vlan_in_port_channel(untagged_vlan, port_channel)

        if port_channel.trunk_allowed_vlan_ids is not None:
            resp = self._patch_and_post(url, None, VLanInterface(vlan_id=port_channel.trunk_allowed_vlan_ids,
                                                                 port_channel_mode=VLanInterface.PortChannelMode.TRUNK,
                                                                 port_channel=port_channel.channel_id).content())

        return resp

    def configure_ethernet_interface(self, ethernet_interface):
        url = self.base_url + EthernetInterface.path
        resp = self._patch_and_post(url, None, ethernet_interface.content())

        if ethernet_interface.access_vlan_id is not None:
            resp = self._patch_and_post(url, None, VLanInterface(vlan_id=ethernet_interface.access_vlan_id,
                                                                 ethernet_if=ethernet_interface.eif_id).content())

        if ethernet_interface.channel_group is not None:
            resp = self._patch_and_post(url, None, PortChannelInterface(channel_id=ethernet_interface.channel_group,
                                                                        ethernet_if=ethernet_interface.eif_id
                                                                        ).content())

        return resp

    def detach_port_channel_from_ethernet_interface(self, eif_id, port_channel_id):
        url = self.base_url + EthernetInterface.path_detach_port_channel.format(
            port_channel_id=port_channel_id, eif_id=quote_plus(eif_id))

        resp = self._delete(url, None)

    def configure_bgp(self, bgp):
        url = self.base_url + BorderGatewayProtocol.path
        resp = self._patch_and_post(url, None, bgp.content())

        return resp
