import requests
from requests import status_codes
from requests.auth import HTTPBasicAuth
from oslo_log import log as logging

from os10_fe_networking.agent.rest_conf.port_group import PortGroup
from os10_fe_networking.agent.rest_conf.virtual_route_forwarding import IPVirtualRouteForwarding
from os10_fe_networking.agent.rest_conf.interface import VLanInterface, PortChannelInterface, \
    EthernetInterface

LOG = logging.getLogger(__name__)


class OS10RestConfClient:

    def __init__(self, mgmt_ip):
        self.username = "admin"
        self.password = "D@ngerous1"
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
        url = self.base_url + pg.path
        resp = self._patch_and_post(url, None, pg.create_request())

        if not profile:
            resp = self._patch_and_post(url, None, pg.profile_request())

    def configure_port_group(self, pg_id, ports):
        pg = PortGroup(pg_id, None, ports)
        url = self.base_url + pg.path
        resp = self._patch_and_post(url, None, pg.ports_request())

    def configure_virtual_route_forwarding(self, name):
        vrf = IPVirtualRouteForwarding(name)
        resp = self._patch_and_post(self.base_url + vrf.path["vrf-config"], None, vrf.vrf_config_request())
        resp = self._patch_and_post(self.base_url + vrf.path["routing"], None, vrf.routing_request())
        resp = self._patch_and_post(self.base_url + vrf.path["dhcp-relay-vrf-configs"], None,
                                    vrf.dhcp_relay_vrf_config())

    def configure_vlan(self, vlan_interface):
        url = self.base_url + vlan_interface.path

        # create empty vlan interface, and patch the left properties later
        # create vlan interface with all its properties results in ERROR: "DATA, L3 configs present on this interface"
        resp = self._patch_and_post(url, None, VLanInterface(vlan_id=vlan_interface.vlan_id).content())

        # patch the left properties
        resp = self._patch_and_post(url, None, vlan_interface.content())

        return resp

    def _get_untagged_vlan_from_port_channel(self, port_channel):
        url = self.base_url + port_channel.path_get_untagged_vlan.format(channel_id=port_channel.channel_id)
        resp = self._get(url, None)
        return port_channel.parse_untagged_vlan(resp)

    def _delete_untagged_vlan_in_port_channel(self, untagged_vlan, port_channel):
        url = self.base_url + port_channel.path_delete_untagged_vlan.format(untagged_vlan=untagged_vlan,
                                                                            channel_id=port_channel.channel_id)
        resp = self._delete(url, None)
        return resp

    def configure_port_channel(self, port_channel):
        url = self.base_url + port_channel.path
        resp = self._patch_and_post(url, None, port_channel.content())

        if port_channel.access_vlan_id is not None:
            resp = self._patch_and_post(url, None, VLanInterface(vlan_id=port_channel.access_vlan_id,
                                                                 port_channel=port_channel.channel_id).content())
        else:
            # switch port access vlan is auto-created, if there is no access_vlan_id in port_channel, delete it.
            untagged_vlan = self._get_untagged_vlan_from_port_channel(port_channel)
            if untagged_vlan is not None:
                # Delete this untagged vlan
                self._delete_untagged_vlan_in_port_channel(untagged_vlan, port_channel)

        if port_channel.trunk_allowed_vlan_ids is not None:
            resp = self._patch_and_post(url, None, VLanInterface(vlan_id=port_channel.trunk_allowed_vlan_ids,
                                                                 port_channel=port_channel.channel_id).content())

        return resp

    def configure_ethernet_interface(self, ethernet_interface):
        url = self.base_url + ethernet_interface.path
        resp = self._patch_and_post(url, None, ethernet_interface.content())

        if ethernet_interface.access_vlan_id is not None:
            resp = self._patch_and_post(url, None, VLanInterface(vlan_id=ethernet_interface.access_vlan_id,
                                                                 ethernet_if=ethernet_interface.eif_id).content())

        if ethernet_interface.channel_group is not None:
            resp = self._patch_and_post(url, None, PortChannelInterface(channel_id=ethernet_interface.channel_group,
                                                                        ethernet_if=ethernet_interface.eif_id
                                                                        ).content())

        return resp

    def configure_bgp(self, bgp):
        url = self.base_url + bgp.path
        resp = self._patch_and_post(url, None, bgp.content())

        return resp


