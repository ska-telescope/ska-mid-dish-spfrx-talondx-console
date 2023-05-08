#!/bin/sh

display_usage() {
    echo -e "\nstart-rxpu\n"
    echo "Start the RXPU device servers.\n"
    echo -e "\nUsage: $0 [bin location] [server instance] [logging level]\n"
}

bindir=${1}
instance=${2}
log_level=${3}

if [ $# -lt 3 ]
then
    display_usage
    exit 1
fi

echo "Starting Talon-DX BSP..."
${bindir}/ska-talondx-bsp-ds ${instance} -v${log_level} &
sleep 1

echo "Starting Talon-DX FPGA Temperature Monitor..."
${bindir}/ska-talondx-temperature-monitor-ds ${instance} -v${log_level} &
sleep 1

echo "Starting SPFRx Multi-Class Low Level Device Server..."
${bindir}/ska-mid-spfrx-system-ds ${instance} -v${log_level} &
sleep 1

echo "Starting SPFRx Controller DS..."
${bindir}/ska-mid-spfrx-controller-ds ${instance} -v${log_level} &

