from oslo_config import cfg

from neutron._i18n import _

grp = cfg.OptGroup('FRONTEND_SWITCH_FABRIC')

switch_opts = [
    cfg.StrOpt('switch_ip',
               help=_("The frontend switch IP address.")),
    cfg.StrOpt('username',
               default="admin",
               help=_("The frontend switch IP address.")),
    cfg.StrOpt('password',
               default="REBuZ2Vyb3VzMQ==",
               help=_("The frontend switch IP address.")),
    cfg.BoolOpt("enable_port_channel",
                default=False,
                help=_("Whether or not to enable port-channel configuration on target switch.")),
    cfg.StrOpt('category',
               help=_("Corresponding switch category (leaf|spine).")),
    cfg.DictOpt('link_port_channel_mapping',
                default={},
                help=_("Pre-defined port channel and its corresponding link.")),
    cfg.DictOpt('port_channel_ethernet_mapping',
                default={'ethernet1/1/1': 'port-channel1',
                         'ethernet1/1/2': 'port-channel1',
                         'ethernet1/1/3': 'port-channel1',
                         'ethernet1/1/4': 'port-channel1'},
                help=_("Pre-defined port channel and its member ports.")),
]

cfg.CONF.register_group(grp)

cfg.CONF.register_opts(switch_opts, group=grp)

