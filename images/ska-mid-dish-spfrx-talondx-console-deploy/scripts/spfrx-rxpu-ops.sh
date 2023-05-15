#!/bin/bash

display_usage() {
    echo -e "\nsfprx-rxpu-ops script"
    echo -e "-----------------------\n"
    echo -e "Start or stop the RXPU software remotely."
    echo -e "\nUsage: to START:"
    echo -e "   $0 up SPFRX_IP SPFRX_BIN SPFRX_TANGO_INSTANCE SPFRX_LOGGING_LEVEL"
    echo -e "\nUsage: to STOP:"
    echo -e "   $0 down SPFRX_IP SPFRX_BIN"    
    echo -e "\n"
    echo -e "COMMAND : up | down"
    echo -e "SPFRX_IP : The IPv4 address of the SPFRX RXPU (up/down)"
    echo -e "SPFRX_BIN : The directory on SPFRX RXPU containing start/stop scripts (up/down)"
    echo -e "SPFRX_TANGO_INSTANCE : The TANGO instance string confgured in the TANGO DB (up only)"
    echo -e "SPFRX_LOGGING_LEVEL_DEFAULT : The integer default logging level for device servers (up only)"
}

command=${1}
spfrx_ip=${2}
spfrx_bin=${3}
tango_instance=${4}
log_level_default=${5}

if [ $# -lt 3 ]
then
    display_usage
    exit 1
fi

if [ ${command} = "up" ]
then
    if [$# -lt 5]
    then 
        display_usage
        exit 1
    fi
    echo "BRINGUP RXPU ON ${spfrx_ip}"
    ssh root@${spfrx_ip} "${spfrx_bin}/spfrx-start /usr/local/bin ${tango_instance} ${log_level_default}"
fi

if [ ${command} = "down" ]
then
    echo "BRINGDOWN RXPU ON ${spfrx_ip}"
    ssh root@${spfrx_ip} "${spfrx_bin}/spfrx-stop"
fi

