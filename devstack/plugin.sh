#!/usr/bin/env bash
# plugin.sh - DevStack plugin.sh dispatch script template

echo_summary "OS10-FE-Networking devstack plugin.sh called: $1/$2"
source $DEST/OS10-FE-Networking/devstack/lib/OS10-FE-Networking

enable_python3_package OS10-FE-Networking

# check for service enabled
if is_service_enabled os10_fe_networking; then

    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        # Perform installation of service source
        echo_summary "Installing OS10 FE Networking ML2"
        install_os10_fe_networking

    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        # Configure after the other layer 1 and 2 services have been configured
        echo_summary "Configuring OS10 FE Networking Ml2"
        configure_os10_fe_networking
        echo_summary "Configuring OS10 FE Networking Neutron Agent"
        configure_os10_fe_networking_neutron_agent
    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        echo_summary "Starting OS10 FE Networking Neutron Agent"
        start_os10_fe_networking_neutron_agent
    elif [[ "$1" == "stack" && "$2" == "test-config" ]]; then
        echo_summary "Creating OS10 FE Networks"
        create_os10_fe_networks
    fi

    if [[ "$1" == "unstack" ]]; then
        echo_summary "Deleting OS10 FE Networks"
        delete_os10_fe_networks
        echo_summary "Cleaning OS10 FE Networking Ml2"
        cleanup_os10_fe_networking
        echo_summary "Cleaning Networking Baremtal Neutron Agent"
        stop_os10_fe_networking_neutron_agent
    fi
fi
