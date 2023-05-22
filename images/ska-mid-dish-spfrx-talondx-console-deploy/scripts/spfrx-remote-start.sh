#!/bin/bash

display_usage() {
    echo -e "\nsfprx-remote-start script"
    echo -e "---------------------------\n"
    echo -e "Start the RXPU software remotely."
    echo -e "\nUsage:"
    echo -e "   $0 SPFRX_TANGO_HOST SPFRX_IP SPFRX_BIN SPFRX_TANGO_INSTANCE SPFRX_LOGGING_LEVEL"
    echo -e "\n"
    echo -e "SPFRX_TANGO_HOST : The TANGO DB IP Address + port"
    echo -e "SPFRX_IP : The IPv4 address of the SPFRX RXPU (up/down)"
    echo -e "SPFRX_BIN : The directory on SPFRX RXPU containing start/stop scripts (up/down)"
    echo -e "SPFRX_TANGO_INSTANCE : The TANGO instance string confgured in the TANGO DB (up only)"
    echo -e "SPFRX_LOGGING_LEVEL_DEFAULT : The integer default logging level for device servers (up only)"
}

tango_ip=${1}
spfrx_ip=${2}
spfrx_bin=${3}
tango_instance=${4}
log_level_default=${5}

if [ $# -lt 5 ]
then
    display_usage
    exit 1
fi
    
echo "set remote TANGO_HOST = ${tango_ip}"
echo "BRINGUP SPFRx RXPU instance ${tango_instance} ON ${spfrx_ip}"
echo "LOGGING LEVEL ${log_level_default}"
ssh root@${spfrx_ip} "export TANGO_HOST=${tango_ip} && ${spfrx_bin}/spfrx-start ${spfrx_bin} ${tango_instance} ${log_level_default} &"

