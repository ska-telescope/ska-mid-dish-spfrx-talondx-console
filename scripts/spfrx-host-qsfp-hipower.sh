#!/bin/bash

display_usage() {
    echo -e "\nsfprx-host-qsfp-hipower script"
    echo -e "--------------------------------\n"
    echo -e "Configure the host QSFP to hi-power mode. Note that this requires sudo."
    echo -e "\nUsage:"
    echo -e "   $0 QSFP_CONTROL_PATH"
    echo -e "QSFP_CONTROL_PATH : The absolute host path for qsfp_control executable"
}

qsfp_path=${1}

if [ $# -lt 1 ]
then
    display_usage
    exit 1
fi

sudo ${qsfp_path}/qsfp_control -p 1

#sudo /usr/share/bittware/520nmx/cots/utilities/qsfp_control/bin/qsfp_control -p 1