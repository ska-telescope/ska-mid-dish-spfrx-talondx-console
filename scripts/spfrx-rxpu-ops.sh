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
    echo -e "SPFRX_IP : The IPv4 address of the SPFRX RXPU (up/down)"
    echo -e "SPFRX_BIN : The directory on SPFRX RXPU containing start/stop scripts (up/down)"
    echo -e "SPFRX_TANGO_INSTANCE : The TANGO instance string confgured in the TANGO DB (up only)"
    echo -e "SPFRX_LOGGING_LEVEL_DEFAULT : The integer default logging level for device servers (up only)"
}

if [ $# -lt 3 ]
then
    display_usage
    exit 1
fi

if [ $1 = "up" ]
then
    if [$# -lt 5]
    then 
        display_usage
        exit 1
    fi
    echo "BRINGUP RXPU ON ${2}"
    ssh root@${2} "$3/start-rxpu $3 $4 $5"
fi

if [ $1 = "down" ]
then
    echo "BRINGDOWN RXPU ON ${2}"
    ssh root@${2} "$3/stop-rxpu"
fi

