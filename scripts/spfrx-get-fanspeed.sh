#!/bin/sh

display_usage() {
    echo -e "\nSPFRx get fanspeed"
    echo -3 "--------------------\n"
    echo "Get the fan speeds of SPFRx RXPU fans 1, 2, and 3.\n"
    echo -e "\nUsage: $0 SPFRX_IP HWMON_ID"
    echo -e "\n"
    echo -e "SPFRX_IP : The SPFRx TALON-DX HPS IP Address"
    echo -e "HWMON_ID : (Optional) The numerical digit of HWMON ID for fan control device"
    echo -e "           (Defaults to 1)"
}

if [ $# -lt 1 ]
then
    display_usage
    exit 1
fi

SPFRX_IP=${1}
HWMON=${2:1}
HWMON_DIR=/sys/devices/platform/soc/ffc02800.i2c/i2c-0/0-0020/hwmon/hwmon${HWMON}

ssh -T root@${SPFRX_IP} <<EOF
	cat ${HWMON_DIR}/pwm1
	cat ${HWMON_DIR}/pwm2
	cat ${HWMON_DIR}/pwm3
EOF
