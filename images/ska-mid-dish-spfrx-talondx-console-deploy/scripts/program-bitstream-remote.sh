#!/bin/bash

display_usage() {
    echo -e "\nprogram Talon-DX Bitstream remote script"
    echo -e "------------------------------------------\n"
    echo -e "Install a bitstream into the SPFRx Talon-DX FPGA over SSH."
    echo -e "\nUsage:"
    echo -e "   $0 ARCHIVE_FILE BOARD_IP"
    echo -e "\n"
    echo -e "ARCHIVE_FILE : The bitstream tar archive"
    echo -e "BOARD_IP : The IP address of the SPFRx TALON-DX HPS"
}

archive=${1}
board=${2}
path="/sys/kernel/config/device-tree/overlays"
name="core"

if [ $# -lt 2 ]
then
    display_usage
    exit 1
fi

bs_core=`tar --wildcards --get -vf $archive *.rbf`
dtb=`tar --wildcards --get -vf $archive *.dtb`
scp $bs_core $dtb root@$board:/lib/firmware
ssh root@$board -n "rmdir $path/*; mkdir $path/$name" # trigger removal of old device tree, the setup next image.
ssh root@$board -n "cd /lib/firmware && echo $dtb > $path/$name/path"
ssh root@$board -n "dmesg | tail -n 10"
rm $bs_core $dtb

