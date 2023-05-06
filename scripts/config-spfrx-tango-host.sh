#!/bin/bash

display_usage() {
    echo -e "\nconfig-spfrx-tango-host script"
    echo -e "--------------------------------\n"
    echo -e "Remotely set the TANGO_HOST environment variable."
    echo -e "\nUsage:"
    echo -e "   $0 SPFRX_IP SPFRX_NAMESPACE DOMAIN TANGO_PORT"
    echo -e "\n"
    echo -e "SPFRX_IP : The IPv4 address of the SPFRX RXPU"
    echo -e "SPFRX_NAMESPACE : The k8s namespace for the SPFRX (default is ?= defined in Makefile)"
    echo -e "DOMAIN : The k8s domain (default is ?= defined in Makefile)"
    echo -e "TANGO_PORT : The TANGO_HOST port number (default is ?= 10000 in Makefile)"
}

# $1 = the IP address of the SPFRx (?= defined in Makefile)
# $2 = the SPFRx namespace within the k8s cluster (?= defined in Makefile)
# $3 = the k8s domain (?= defined in Makefile)
# $4 = the TANGO port (?= defined at 10000 in Makefile)
#
# The TANGO_HOST is composed of $2.svc.$3
#
# To run this script:
#  make config-spfrx-tango-host

spfrx_ip=${1}
spfrx_namespace=${2}
k8s_domain=${3}
tango_port=${4}

if [ $# -lt 4 ]
then
    display_usage
    exit 1
fi

ssh root@${spfrx_ip} "export TANGO_HOST=${spfrx_namespace}.svc.${k8s_domain}:${tango_port}"