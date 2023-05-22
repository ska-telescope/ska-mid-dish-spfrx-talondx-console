#!/bin/sh

display_usage() {
    echo -e "\nprogram Talon-DX Bitstream script"
    echo -e "-----------------------------------\n"
    echo -e "Install a bitstream into the SPFRx Talon-DX FPGA."
    echo -e "\nUsage:"
    echo -e "   $0 ARCHIVE_FILE"
    echo -e "\n"
    echo -e "ARCHIVE_FILE : The bitstream tar archive"
}

if [ $# -lt 1 ]
then
    display_usage
    exit 1
fi


archive=${1}
path="/sys/kernel/config/device-tree/overlays"
name="core"

bs_core=`tar --wildcards --get -vf $archive *.rbf`
dtb=`tar --wildcards --get -vf $archive *.dtb`
cp $bs_core $dtb /lib/firmware
rmdir $path/*; mkdir $path/$name # trigger removal of old device tree, the setup next image.
cd /lib/firmware && echo $dtb > $path/$name/path
dmesg | tail -n 3
rm $bs_core $dtb

