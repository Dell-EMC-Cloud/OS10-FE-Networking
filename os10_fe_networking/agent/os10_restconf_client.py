import requests
from requests import status_codes
from requests.auth import HTTPBasicAuth
from oslo_log import log as logging


from os10_fe_networking.agent.rest_conf.port_group import PortGroup
from os10_fe_networking.agent.rest_conf.virtual_route_forwarding import VirtualRouteForwarding
from os10_fe_networking.agent.rest_conf.interface import VVRPGroup, VLanInterface

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
        if "ietf-restconf:errors" in resp and "error" in resp["ietf-restconf:errors"] and "error-message" in resp["ietf-restconf:errors"]["error"][0]:
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

    def create_virtual_route_forwarding(self, name):
        vrf = VirtualRouteForwarding(name)
        resp = self._patch_and_post(self.base_url + vrf.path["vrf-config"], None, vrf.vrf_config_request())
        resp = self._patch_and_post(self.base_url + vrf.path["routing"], None, vrf.routing_request())
        resp = self._patch_and_post(self.base_url + vrf.path["dhcp-relay-vrf-configs"], None, vrf.dhcp_relay_vrf_config())

    def create_vlan(self, vlan_id, desc=None, enabled=None, vrf=None, address=None, vvrp_group=None):
        vlan_interface = VLanInterface(desc, enabled, vlan_id, vrf, address, vvrp_group)
        url = self.base_url + vlan_interface.path

        resp = self._patch_and_post(url, None, vlan_interface.create_request())

        if vlan_interface.desc is not None:
            resp = self._patch_and_post(url, None, vlan_interface.desc_request())

        if vlan_interface.enabled is not None:
            resp = self._patch_and_post(url, None, vlan_interface.enable_request())

        if vlan_interface.vrf is not None:
            resp = self._patch_and_post(url, None, vlan_interface.vrf_request())

        if vlan_interface.address is not None:
            resp = self._patch_and_post(url, None, vlan_interface.address_request())

        if vlan_interface.vvrp_group is not None:
            resp = self._patch_and_post(url, None, vlan_interface.vvrp_create_request())
            resp = self._patch_and_post(url, None, vlan_interface.vvrp_priority_request())
            resp = self._patch_and_post(url, None, vlan_interface.vvrp_virtual_addresses_request())












