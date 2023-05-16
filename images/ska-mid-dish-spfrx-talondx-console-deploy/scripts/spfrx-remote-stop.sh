#!/bin/bash

display_usage() {
    echo -e "\nsfprx-remote-stop script"
    echo -e "--------------------------\n"
    echo -e "Stop the RXPU software remotely."
    echo -e "\nUsage:"
    echo -e "   $0 SPFRX_IP SPFRX_BIN"    
    echo -e "\n"
    echo -e "SPFRX_IP : The IPv4 address of the SPFRX RXPU (up/down)"
    echo -e "SPFRX_BIN : The directory on SPFRX RXPU containing start/stop scripts (up/down)"
}

spfrx_ip=${1}
spfrx_bin=${2}

if [ $# -lt 2 ]
then
    display_usage
    exit 1
fi

echo "BRINGDOWN RXPU ON ${spfrx_ip}"
ssh root@${spfrx_ip} "${spfrx_bin}/spfrx-stop"


