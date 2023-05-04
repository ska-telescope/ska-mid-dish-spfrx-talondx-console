#!/bin/sh

display_usage() {
    echo -e "\nstart-rxpu\n"
    echo "Start the RXPU device servers.\n"
    echo -e "\nUsage: $0 [bin location] [server instance] [logging level]\n"
}

echo "Starting Talon-DX BSP..."
${1}/ska-talondx-bsp-ds ${2} -v${3} &
sleep 1

echo "Starting Talon-DX FPGA Temperature Monitor..."
${1}/ska-talondx-temperature-monitor-ds ${2} -v${3} &
sleep 1

echo "Starting SPFRx Multi-Class Low Level Device Server..."
${1}/ska-mid-spfrx-system-ds ${2} -v${3} &
sleep 1

echo "Starting SPFRx Controller DS..."
${1}/ska-mid-spfrx-controller-ds ${2} -v${3} &

