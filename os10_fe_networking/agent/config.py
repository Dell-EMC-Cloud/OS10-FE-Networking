from oslo_config import cfg

from neutron._i18n import _

grp = cfg.OptGroup('FRONTEND_SWITCH_FABRIC')

switch_opts = [
    cfg.StrOpt('switch_ip',
               help=_("The frontend switch IP address.")),
    cfg.BoolOpt("enable_port_channel",
                default=False,
                help=_("Whether or not to enable port-channel configuration on target switch")),
    cfg.StrOpt('category',
               help=_("Corresponding switch category (leaf|spine).")),
]

cfg.CONF.register_group(grp)

cfg.CONF.register_opts(switch_opts, group=grp)

