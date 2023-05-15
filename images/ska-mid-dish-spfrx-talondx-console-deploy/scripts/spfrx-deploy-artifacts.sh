#!/bin/bash

# copy relevant artifacts to the SPFRx at $1 (default provided by ?= in Makefile)
#
# $1 is the SPFRx IP ADDRESS (provided by ?= in Makefile)
# $2 is the local directory where artifacts have been downloaded (defaults to mnt/spfrx-config)
# $3 is the target directory on the SPFRx system (default defined by ?= in Makefile)

display_usage() {
    echo -e "\nsfprx-deploy-artifacts script"
    echo -e "-------------------------------\n"
    echo -e "Copy artifacts from the host machine to the SPFRx HPS."
    echo -e "\nUsage:"
    echo -e "   $0 SPFRX_IP SPFRX_LOCAL_DIR SPFRX_BIN"
    echo -e "\n"
    echo -e "SPFRX_IP : The IPv4 address of the SPFRX RXPU"
    echo -e "SPFRX_LOCAL_DIR : The local host directory containing artifacts to be copied."
    echo -e "SPFRX_BIN : The directory on SPFRX RXPU containing executables"
}

spfrx_ip=${1}
spfrx_local_dir=${2}
spfrx_bin=${3}

if [ $# -lt 3 ]
then
    display_usage
    exit 1
fi

scp ${spfrx_local_dir}/ska-mid-spfrx-controller-ds/bin/ska-mid-spfrx-controller-ds root@${spfrx_ip}:${spfrx_bin}/.
scp ${spfrx_local_dir}/ska-mid-spfrx-system-ds/bin/ska-mid-spfrx-system-ds root@${spfrx_ip}:${spfrx_bin}/.
scp ${spfrx_local_dir}/ska-talondx-bsp-ds/bin/ska-talondx-bsp-ds root@${spfrx_ip}:${spfrx_bin}/.
scp ${spfrx_local_dir}/ska-talondx-temperature-monitor-ds/bin/ska-talondx-temperature-monitor-ds root@${spfrx_ip}:${spfrx_bin}/.

scp images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/remote/spfrx-start.sh root@${spfrx_ip}:${spfrx_bin}/spfrx-start
scp images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/remote/spfrx-stop.sh root@${spfrx_ip}:${spfrx_bin}/spfrx-stop

scp images/ska-mid-dish-spfrx-talondx-console-deploy/scripts/remote/program-bitstream.sh root@${spfrx_ip}:${spfrx_bin}/program-bitstream
