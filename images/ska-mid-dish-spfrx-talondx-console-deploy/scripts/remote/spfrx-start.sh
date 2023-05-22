#!/bin/sh

display_usage() {
    echo -e "\nspfrx-start"
    echo -e "-----------"
    echo "Start the SPFRX RXPU TANGO device servers.\n"
    echo -e "\nUsage: $0 [tango ds bin dir] [server instance] [logging level]\n"
}

bin_dir=${1}
instance=${2}
log_level=${3}

if [ $# -lt 3 ]
then
    display_usage
    exit 1
fi

echo "Starting Talon-DX BSP..."
${bin_dir}/ska-talondx-bsp-ds ${instance} -v${log_level} &
sleep 1

echo "Starting Talon-DX FPGA Temperature Monitor..."
${bin_dir}/ska-talondx-temperature-monitor-ds ${instance} -v${log_level} &
sleep 1

echo "Starting SPFRx Multi-Class Low Level Device Server..."
${bin_dir}/ska-mid-spfrx-system-ds ${instance} -v${log_level} &
sleep 1

echo "Starting SPFRx Controller DS..."
${bin_dir}/ska-mid-spfrx-controller-ds ${instance} -v${log_level} &

