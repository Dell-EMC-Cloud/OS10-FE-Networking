import json
import socket
import sys
import time

import eventlet

eventlet.monkey_patch()

# oslo_messaging/notify/listener.py documents that monkeypatching is required
from os10_fe_networking.agent.config import switch_opts
from os10_fe_networking.agent.os10_fe_fabric_manager import OS10FEFabricManager

from neutron.agent import rpc as agent_rpc
from neutron.common import config as common_config
from neutron.conf.agent import common as agent_config
from neutron_lib.agent import topics
from neutron_lib import constants as n_const
from neutron_lib import context
from openstack import exceptions as sdk_exc
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging
from oslo_service import service
from oslo_utils import uuidutils
from neutron.api.rpc.handlers import securitygroups_rpc as sg_rpc
from neutron.agent import securitygroups_rpc as agent_sg_rpc
from neutron.plugins.ml2.drivers.agent import _agent_manager_base as amb
from os10_fe_networking import constants
from os10_fe_networking import ironic_client

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
CONF.import_group('AGENT', 'neutron.plugins.ml2.drivers.agent.config')
CONF.import_group("FRONTEND_SWITCH_FABRIC", "os10_fe_networking.agent.config")

DEVICES_DIR = "/sys/class/net"
PREFIX_TAP = "tap"


def list_opts():
    return [('agent', agent_config.AGENT_STATE_OPTS),
            ("FRONTEND_SWITCH_FABRIC", switch_opts)]


class PluginApi(agent_rpc.PluginApi):
    def get_frontend_devices_details_list(self, context, agent_id, host=None):
        cctxt = self.client.prepare(version='1.3')
        return cctxt.call(context, 'get_frontend_devices_details_list',
                          agent_id=agent_id, host=host)


class OS10FENeutronAgent(service.ServiceBase):

    def __init__(self):
        self.context = context.get_admin_context_without_session()
        self.agent_id = uuidutils.generate_uuid(dashed=True)
        self.agent_host = socket.gethostname()
        self.reported_nodes = {}
        self.polling_interval = CONF.AGENT.polling_interval
        self.agent_type = constants.OS10FE_AGENT_TYPE

        # cache objects
        self.cached_devices_details_list = None
        self.updated_ports = set()
        self.deleted_ports = set()
        self.deleted_networks = set()

        # TODO This is a hard code ip
        self.ironic_client = ironic_client.get_client()
        self.fabric_manager = OS10FEFabricManager.create(CONF)
        LOG.info('Agent OS10-FE-Networking initialized.')

    def start(self):
        LOG.info('Starting agent OS10-FE-Networking.')
        self.setup_rpc()
        #        self.heartbeat = loopingcall.FixedIntervalLoopingCall(
        #            self._report_state)
        #        self.heartbeat.start(interval=CONF.AGENT.report_interval,
        #                             initial_delay=CONF.AGENT.report_interval)
        self.connection.consume_in_threads()
        self.daemon_loop()

    def setup_rpc(self):
        self.plugin_rpc = PluginApi(topics.PLUGIN)
        self.sg_plugin_rpc = sg_rpc.SecurityGroupServerRpcApi(topics.PLUGIN)
        self.sg_agent = agent_sg_rpc.SecurityGroupAgentRpc(
            self.context, self.sg_plugin_rpc, defer_refresh_firewall=True)

        self.topic = topics.AGENT
        self.state_rpc = agent_rpc.PluginReportStateAPI(topics.REPORTS)
        # RPC network init
        # Handle updates from service
        self.rpc_callbacks = self.get_rpc_callbacks(self.context, self, self.sg_agent)
        self.endpoints = [self.rpc_callbacks]
        self._validate_rpc_endpoints()
        # Define the listening consumers for the agent
        consumers = self.get_rpc_consumers()
        self.connection = agent_rpc.create_consumers(self.endpoints,
                                                     self.topic,
                                                     consumers,
                                                     start_listening=False)

    def get_rpc_consumers(self):
        consumers = [[topics.PORT, topics.UPDATE],
                     [topics.PORT, topics.DELETE],
                     [topics.NETWORK, topics.DELETE],
                     [topics.NETWORK, topics.UPDATE],
                     [topics.SECURITY_GROUP, topics.UPDATE],
                     [topics.PORT_BINDING, topics.DEACTIVATE],
                     [topics.PORT_BINDING, topics.ACTIVATE]]
        return consumers

    def get_rpc_callbacks(self, context, agent, sg_agent):
        return OS10FERpcCallbacks(context, agent, sg_agent)

    def _validate_rpc_endpoints(self):
        if not isinstance(self.endpoints[0],
                          amb.CommonAgentManagerRpcCallBackBase):
            LOG.error("RPC Callback class must inherit from "
                      "CommonAgentManagerRpcCallBackBase to ensure "
                      "CommonAgent works properly.")
            sys.exit(1)

    def stop(self):
        LOG.info('Stopping agent OS10-FE-Networking.')
        # self.heartbeat.stop()

    def reset(self):
        LOG.info('Resetting agent OS10-FE-Networking.')
        # self.heartbeat.stop()

    def wait(self):
        pass

    @staticmethod
    def get_template_node_state(node_uuid):
        return {
            'binary': constants.OS10FE_BINARY,
            'host': node_uuid,
            'topic': n_const.L2_AGENT_TOPIC,
            'configurations': {
                'bridge_mappings': {},
                'log_agent_heartbeats': CONF.AGENT.log_agent_heartbeats,
            },
            'start_flag': False,
            'agent_type': constants.OS10FE_AGENT_TYPE}

    def _report_state(self):
        node_states = {}
        ironic_ports = self.ironic_client.ports(details=True)
        # NOTE: the above calls returns a generator, so we need to handle
        # exceptions that happen just before the first loop iteration, when
        # the actual request to ironic happens
        try:
            for port in ironic_ports:
                node = port.node_id
                template_node_state = self.get_template_node_state(node)
                node_states.setdefault(node, template_node_state)
                mapping = node_states[
                    node]["configurations"]["bridge_mappings"]
                if port.physical_network is not None:
                    mapping[port.physical_network] = "yes"
        except sdk_exc.OpenStackCloudException:
            LOG.exception("Failed to get ironic ports data! "
                          "Not reporting state.")
            return

        for state in node_states.values():
            # If the node was not previously reported with current
            # configuration set the start_flag True.
            if not state['configurations'] == self.reported_nodes.get(
                    state['host']):
                state.update({'start_flag': True})
                LOG.info('Reporting state for host agent %s with new '
                         'configuration: %s',
                         state['host'], state['configurations'])
            try:
                LOG.debug('Reporting state for host: %s with configuration: '
                          '%s', state['host'], state['configurations'])
                self.state_rpc.report_state(self.context, state)
            except AttributeError:
                # This means the server does not support report_state
                LOG.exception("Neutron server does not support state report. "
                              "State report for this agent will be disabled.")
                # self.heartbeat.stop()
                # Don't continue reporting the remaining agents in this case.
                return
            except Exception:
                LOG.exception("Failed reporting state!")
                # Don't continue reporting the remaining nodes if one failed.
                return
            self.reported_nodes.update(
                {state['host']: state['configurations']})

    def _get_and_clear_member_set(self, member):
        if member not in self.__dict__:
            raise RuntimeError("Can not find member {member} in object".format(member=member))

        return_set = self.__dict__[member]
        self.__dict__[member] = set()
        return return_set

    def refresh_devices_details_list(self):
        try:
            devices_details_list = self.plugin_rpc.get_frontend_devices_details_list(
                self.context, self.agent_id, host=cfg.CONF.host)
        except Exception:
            LOG.exception("Unable to get port details")
            # resync is needed
            return True

        for device_detail in devices_details_list:
            if "profile" not in device_detail:
                continue

            if device_detail["profile"].get("local_link_information"):
                for local_link_information in device_detail['profile']['local_link_information']:
                    switch_info = local_link_information['switch_info']
                    local_link_information['switch_info'] = json.loads(switch_info.replace("'", "\""))

        self.cached_devices_details_list = devices_details_list

        return False

    @staticmethod
    def get_local_link_info(local_link_information):
        switch_port = local_link_information['port_id']
        switch_ip = local_link_information['switch_info']['switch_ip']
        cluster = local_link_information['switch_info']['cluster']
        preemption = local_link_information['switch_info']['preemption']
        access_mode = local_link_information['switch_info']['access_mode']
        return cluster, switch_ip, switch_port, preemption, access_mode

    @staticmethod
    def get_provisioning_info(device_detail):
        cluster = None
        switch_ip = device_detail["host"]
        switch_port = None
        preemption = None
        access_mode = None
        return cluster, switch_ip, switch_port, preemption, access_mode

    def daemon_loop(self):
        LOG.info("%s Agent RPC Daemon Started!", self.agent_type)

        start_up = True
        previous_ports = set()

        while True:
            start = time.time()

            updated_ports = self._get_and_clear_member_set("updated_ports") | previous_ports
            previous_ports = set()
            deleted_ports = self._get_and_clear_member_set("deleted_ports")
            deleted_networks = self._get_and_clear_member_set("deleted_networks")

            if len(updated_ports) or len(deleted_ports) or len(deleted_networks):
                LOG.info("daemon_loop: updated_ports: {updated_ports}".format(updated_ports=updated_ports))
                LOG.info("daemon_loop: deleted_ports: {deleted_ports}".format(deleted_ports=deleted_ports))
                LOG.info("daemon_loop: deleted_networks: {deleted_networks}".format(deleted_networks=deleted_networks))

            for port_id in deleted_ports:
                for device_detail in self.cached_devices_details_list:
                    if port_id == device_detail["port_id"]:
                        segment = device_detail['segmentation_id']

                        if device_detail["profile"].get("provisioning-fsf"):
                            enable_port_channel = None
                            cluster, switch_ip, switch_port, preemption, access_mode = self.get_provisioning_info(
                                device_detail)
                            self.fabric_manager.detach_port_from_vlan(switch_ip, switch_port, segment,
                                                                      access_mode, enable_port_channel)
                        elif device_detail["profile"].get("local_link_information"):
                            enable_port_channel = len(device_detail['profile']['local_link_information']) > 1
                            for local_link_information in device_detail['profile']['local_link_information']:
                                cluster, switch_ip, switch_port, preemption, access_mode = self.get_local_link_info(
                                    local_link_information)

                                self.fabric_manager.detach_port_from_vlan(switch_ip, switch_port, segment,
                                                                          access_mode, enable_port_channel)

            for network_id in deleted_networks:
                for device_detail in self.cached_devices_details_list:
                    if network_id == device_detail["network_id"]:
                        segment = device_detail['segmentation_id']

                        if device_detail["profile"].get("provisioning-fsf"):
                            enable_port_channel = None
                            cluster, switch_ip, switch_port, preemption, access_mode = self.get_provisioning_info(
                                device_detail)
                            self.fabric_manager.delete_vlan(switch_ip, switch_port,
                                                            segment, enable_port_channel)
                        elif device_detail["profile"].get("local_link_information"):
                            enable_port_channel = len(device_detail['profile']['local_link_information']) > 1
                            for local_link_information in device_detail['profile']['local_link_information']:
                                cluster, switch_ip, switch_port, preemption, access_mode = self.get_local_link_info(
                                    local_link_information)

                                self.fabric_manager.delete_vlan(switch_ip, switch_port,
                                                                segment, enable_port_channel)

            if start_up or updated_ports:
                start_up = False
                resync = self.refresh_devices_details_list()

                # Agent is out of sync with neutron
                # save the updated ports and wait for next sync
                if resync:
                    previous_ports = previous_ports | updated_ports
                    continue

                for device_detail in self.cached_devices_details_list:
                    if updated_ports and device_detail["port_id"] not in updated_ports:
                        continue

                    segment = device_detail['segmentation_id']
                    if device_detail["profile"].get("provisioning-fsf"):
                        enable_port_channel = None
                        cluster, switch_ip, switch_port, preemption, access_mode = self.get_provisioning_info(
                            device_detail)

                        # ensure above configuration
                        self.fabric_manager.ensure_configuration(switch_ip=switch_ip,
                                                                 ethernet_interface=switch_port,
                                                                 vlan=segment,
                                                                 cluster=cluster,
                                                                 preemption=preemption,
                                                                 access_mode=access_mode,
                                                                 enable_port_channel=enable_port_channel)
                    elif device_detail["profile"].get("local_link_information"):
                        enable_port_channel = len(device_detail['profile']['local_link_information']) > 1
                        for local_link_information in device_detail['profile']['local_link_information']:
                            cluster, switch_ip, switch_port, preemption, access_mode = self.get_local_link_info(
                                local_link_information)

                            # ensure above configuration
                            self.fabric_manager.ensure_configuration(switch_ip=switch_ip,
                                                                     ethernet_interface=switch_port,
                                                                     vlan=segment,
                                                                     cluster=cluster,
                                                                     preemption=preemption,
                                                                     access_mode=access_mode,
                                                                     enable_port_channel=enable_port_channel)

            # sleep till end of polling interval
            elapsed = (time.time() - start)
            if elapsed < self.polling_interval:
                time.sleep(self.polling_interval - elapsed)
            else:
                LOG.debug("Loop iteration exceeded interval "
                          "(%(polling_interval)s vs. %(elapsed)s)!",
                          {'polling_interval': self.polling_interval,
                           'elapsed': elapsed})


class OS10FERpcCallbacks(sg_rpc.SecurityGroupAgentRpcCallbackMixin,
                         amb.CommonAgentManagerRpcCallBackBase):
    # Set RPC API version to 1.0 by default.
    target = oslo_messaging.Target(version='1.5')

    def network_delete(self, context, **kwargs):
        LOG.info("network_delete received")
        self.agent.deleted_networks.add(kwargs["network_id"])

    def network_update(self, context, **kwargs):
        LOG.info("network_update received")

    def port_update(self, context, **kwargs):
        port = kwargs["port"]
        network_type = kwargs["network_type"]
        segmentation_id = kwargs["segmentation_id"]
        physical_network = kwargs["physical_network"]
        LOG.info("port_update received: {port}".format(port=port))
        LOG.info("segmentation_id: {segmentation_id}".format(segmentation_id=segmentation_id))

        self.agent.updated_ports.add(port["id"])

    def port_delete(self, context, **kwargs):
        LOG.info("port_delete received")
        self.agent.deleted_ports.add(kwargs["port_id"])

    def binding_deactivate(self, context, **kwargs):
        LOG.info("binding_deactivate received")

    def binding_activate(self, context, **kwargs):
        LOG.info("binding_activate received")


def _unregister_deprecated_opts():
    CONF.reset()
    CONF.unregister_opts(
        [CONF._groups[ironic_client.IRONIC_GROUP]._opts[opt]['opt']
         for opt in ironic_client._deprecated_opts],
        group=ironic_client.IRONIC_GROUP)


def main():
    _unregister_deprecated_opts()
    common_config.init(sys.argv[1:])
    common_config.setup_logging()
    agent = OS10FENeutronAgent()
    launcher = service.launch(cfg.CONF, agent, restart_method='mutate')
    launcher.wait()


# if __name__ == "__main__":
#     sys.exit(main())
