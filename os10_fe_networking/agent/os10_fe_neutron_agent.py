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

sys.path.append("/opt/stack/OS10-FE-Networking")

from os10_fe_networking import constants

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
        self.state_rpc = agent_rpc.PluginReportStateAPI(topics.REPORTS)
        self.reported_nodes = {}
        LOG.info('Agent OS10-FE-Networking initialized.')

    def start(self):
        LOG.info('Starting agent OS10-FE-Networking.')
        self.heartbeat = loopingcall.FixedIntervalLoopingCall(
            self._report_state)
        self.heartbeat.start(interval=CONF.AGENT.report_interval,
                             initial_delay=CONF.AGENT.report_interval)

    def stop(self):
        LOG.info('Stopping agent OS10-FE-Networking.')
        self.heartbeat.stop()

    def reset(self):
        LOG.info('Resetting agent OS10-FE-Networking.')
        self.heartbeat.stop()

    def wait(self):
        pass

    def get_template_node_state(self, node_uuid):
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
        node = self.agent_host
        template_node_state = self.get_template_node_state(node)
        node_states.setdefault(node, template_node_state)

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


def _unregister_deprecated_opts():
    CONF.reset()


def main():
    _unregister_deprecated_opts()
    common_config.init(sys.argv[1:])
    common_config.setup_logging()
    agent = OS10FENeutronAgent()
    launcher = service.launch(cfg.CONF, agent, restart_method='mutate')
    launcher.wait()


if __name__ == "__main__":
    sys.exit(main())
