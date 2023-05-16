#!/bin/sh

display_usage() {
    echo -e "\nspfrx-start"
    echo -e "-----------"
    echo "Start the SPFRX RXPU TANGO device servers.\n"
    echo -e "\nUsage: $0 [server instance] [logging level]\n"
}

instance=${1}
log_level=${2}

if [ $# -lt 2 ]
then
    display_usage
    exit 1
fi

echo "Starting Talon-DX BSP..."
ska-talondx-bsp-ds ${instance} -v${log_level} &
sleep 1

echo "Starting Talon-DX FPGA Temperature Monitor..."
ska-talondx-temperature-monitor-ds ${instance} -v${log_level} &
sleep 1

echo "Starting SPFRx Multi-Class Low Level Device Server..."
ska-mid-spfrx-system-ds ${instance} -v${log_level} &
sleep 1

echo "Starting SPFRx Controller DS..."
ska-mid-spfrx-controller-ds ${instance} -v${log_level} &

