from neutron.plugins.ml2.plugin import Ml2Plugin
from neutron.plugins.ml2 import rpc
from neutron.plugins.ml2 import db
from neutron.plugins.ml2 import driver_context
from neutron.api.rpc.handlers import securitygroups_rpc
from neutron.api.rpc.handlers import dvr_rpc
from neutron.api.rpc.handlers import dhcp_rpc
from neutron.api.rpc.handlers import metadata_rpc
from neutron.api.rpc.handlers import resources_rpc
from neutron.common import utils
from neutron_lib import constants as const
from neutron_lib.db import api as db_api
from neutron_lib.plugins import directory
from neutron_lib.plugins import utils as p_utils
from neutron_lib.api.definitions import portbindings
from neutron.db import models_v2
from neutron.db import agents_db
from sqlalchemy.orm import exc as sa_exc
from oslo_log import log

LOG = log.getLogger(__name__)


class OS10Ml2Plugin(Ml2Plugin):
    def _setup_rpc(self):
        """Initialize components to support agent communication."""
        self.endpoints = [
            RpcCallbacks(self.notifier, self.type_manager),
            securitygroups_rpc.SecurityGroupServerRpcCallback(),
            dvr_rpc.DVRServerRpcCallback(),
            dhcp_rpc.DhcpRpcCallback(),
            agents_db.AgentExtRpcCallback(),
            metadata_rpc.MetadataRpcCallback(),
            resources_rpc.ResourcesPullRpcCallback()
        ]

    @utils.transaction_guard
    @db_api.retry_if_session_inactive(context_var_name='plugin_context')
    def get_frontend_bound_port_contexts(self, plugin_context, host=None,
                                         cached_networks=None):
        port_contexts = []
        with db_api.CONTEXT_READER.using(plugin_context) as session:
            try:
                ports_db = (session.query(models_v2.Port).
                            enable_eagerloads(False).
                            all())
            except sa_exc.NoResultFound:
                LOG.info("No ports found")

            for port_db in ports_db:
                port = self._make_port_dict(port_db)

                is_frontend_port = True
                if port.get('binding:profile'):
                    profile = port["binding:profile"]

                    if profile.get("local_link_information"):
                        for local_link_information in profile["local_link_information"]:
                            if not local_link_information.get("switch_info") or \
                                    "frontend" not in local_link_information["switch_info"]:
                                is_frontend_port = False
                                break
                    elif profile.get("provisioning-fsf"):
                        is_frontend_port = True
                    else:
                        is_frontend_port = False
                else:
                    is_frontend_port = False

                if not is_frontend_port:
                    continue

                network = (cached_networks or {}).get(port['network_id'])

                if not network:
                    network = self.get_network(plugin_context, port['network_id'])

                if port['device_owner'] == const.DEVICE_OWNER_DVR_INTERFACE:
                    binding = db.get_distributed_port_binding_by_host(
                        plugin_context, port['id'], host)
                    if not binding:
                        LOG.error("Binding info for DVR ports %s not found",
                                  port)
                        continue
                    levels = db.get_binding_level_objs(
                        plugin_context, port_db.id, host)
                    port_context = driver_context.PortContext(
                        self, plugin_context, port, network, binding, levels)
                else:
                    # since eager loads are disabled in port_db query
                    # related attribute port_binding could disappear in
                    # concurrent ports deletion.
                    # It's not an error condition.
                    binding = p_utils.get_port_binding_by_status_and_host(
                        port_db.port_bindings, const.ACTIVE)
                    if not binding:
                        LOG.info("Binding info for ports %s was not found, "
                                 "it might have been deleted already.",
                                 port)
                        continue
                    levels = db.get_binding_level_objs(
                        plugin_context, port_db.id, binding.host)
                    port_context = driver_context.PortContext(
                        self, plugin_context, port, network, binding, levels)

                port_contexts.append(self._bind_port_if_needed(port_context))

        return port_contexts


class RpcCallbacks(rpc.RpcCallbacks):

    def get_frontend_devices_details_list(self, rpc_context, **kwargs):
        agent_id = kwargs.get("agent_id")
        host = kwargs.get("host")

        # cached networks used for reducing number of network db calls
        # for server internal usage only
        cached_networks = kwargs.get('cached_networks')
        LOG.info("Frontend devices details list requested by agent "
                 "%(agent_id)s with host %(host)s",
                 {'agent_id': agent_id, 'host': host})

        plugin = directory.get_plugin()
        port_contexts = plugin.get_frontend_bound_port_contexts(rpc_context,
                                                                host,
                                                                cached_networks)

        results = []
        for port_context in port_contexts:
            port = port_context.current
            result = self._get_device_details(rpc_context, agent_id=agent_id,
                                              host=host, device=port["mac_address"],
                                              port_context=port_context)
            result["host"] = port_context.current[portbindings.HOST_ID]

            if 'network_id' in result:
                # success so we update status
                new_status = self._get_new_status(host, port_context)
                if new_status:
                    plugin.update_port_status(rpc_context,
                                              port["id"],
                                              new_status,
                                              host,
                                              port_context.network.current)
            results.append(result)

        return results
