import socket
import sys
from urllib import parse as urlparse

import eventlet

# oslo_messaging/notify/listener.py documents that monkeypatching is required
eventlet.monkey_patch()
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
from oslo_service import loopingcall
from oslo_service import service
from oslo_utils import timeutils
from oslo_utils import uuidutils
from tooz import hashring
from neutron.api.rpc.handlers import securitygroups_rpc as sg_rpc
from neutron.agent import securitygroups_rpc as agent_sg_rpc
from neutron.plugins.ml2.drivers.l2pop.rpc_manager \
    import l2population_rpc as l2pop_rpc
from neutron.plugins.ml2.drivers.agent import _agent_manager_base as amb
from os10_fe_networking.agent.os10_fe_restconf_client import OS10FERestConfClient
from os10_fe_networking import constants
from os10_fe_networking import ironic_client

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
CONF.import_group('AGENT', 'neutron.plugins.ml2.drivers.agent.config')


def list_opts():
    return [('agent', agent_config.AGENT_STATE_OPTS)]


class OS10FENeutronAgent(service.ServiceBase):

    def __init__(self):
        self.context = context.get_admin_context_without_session()
        self.agent_id = uuidutils.generate_uuid(dashed=True)
        self.agent_host = socket.gethostname()
        self.reported_nodes = {}
        # TBD
        # This is a hard code ip
        self.client = OS10FERestConfClient("100.127.0.122")
        self.ironic_client = ironic_client.get_client()
        LOG.info('Agent OS10-FE-Networking initialized.')

    def start(self):
        LOG.info('Starting agent OS10-FE-Networking.')
        self.setup_rpc()
        self.heartbeat = loopingcall.FixedIntervalLoopingCall(
            self._report_state)
        self.heartbeat.start(interval=CONF.AGENT.report_interval,
                             initial_delay=CONF.AGENT.report_interval)
        self.connection.consume_in_threads()

    def setup_rpc(self):
        self.plugin_rpc = agent_rpc.PluginApi(topics.PLUGIN)
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
        self.heartbeat.stop()

    def reset(self):
        LOG.info('Resetting agent OS10-FE-Networking.')
        self.heartbeat.stop()

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
                self.heartbeat.stop()
                # Don't continue reporting the remaining agents in this case.
                return
            except Exception:
                LOG.exception("Failed reporting state!")
                # Don't continue reporting the remaining nodes if one failed.
                return
            self.reported_nodes.update(
                {state['host']: state['configurations']})


class OS10FERpcCallbacks(sg_rpc.SecurityGroupAgentRpcCallbackMixin,
                         amb.CommonAgentManagerRpcCallBackBase):
    # Set RPC API version to 1.0 by default.
    target = oslo_messaging.Target(version='1.5')

    def network_delete(self, context, **kwargs):
        LOG.info("network_delete received")

    def network_update(self, context, **kwargs):
        LOG.info("network_update received")

    def port_update(self, context, **kwargs):
        LOG.info("port_update received")

    def port_delete(self, context, **kwargs):
        LOG.info("port_delete received")

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


if __name__ == "__main__":
    sys.exit(main())
