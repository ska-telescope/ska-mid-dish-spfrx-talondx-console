#!/bin/bash

display_usage() {
    echo -e "\nconfig-spfrx-tango-host script"
    echo -e "--------------------------------\n"
    echo -e "Remotely set the TANGO_HOST environment variable."
    echo -e "\nUsage:"
    echo -e "   $0 SPFRX_IP SPFRX_TANGO_HOST"
    echo -e "\n"
    echo -e "SPFRX_IP : The IPv4 address of the SPFRX RXPU"
    echo -e "SPFRX_TANGO_HOST : The TANGO DB HOST IP address + port (default is ?= defined in Makefile)"
}

# $1 = the IP address of the SPFRx (?= defined in Makefile)
# $2 = the TANGO DB HOST IP (?= defined in Makefile)
#
# To run this script:
#  make config-spfrx-tango-host.sh

spfrx_ip=${1}
spfrx_tango_host=${2}

if [ $# -lt 2 ]
then
    display_usage
    exit 1
fi

echo "Setting TANGO_HOST=${spfrx_tango_host} on ${spfrx_ip}"
ssh root@${spfrx_ip} "export TANGO_HOST=${spfrx_tango_host}"