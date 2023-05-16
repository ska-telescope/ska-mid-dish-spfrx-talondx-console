#!/bin/sh

display_usage() {
    echo -e "\nSPFRx set fanspeed"
    echo -3 "--------------------\n"
    echo "Set the fan speeds of SPFRx RXPU fans 1, 2, and 3.\n"
    echo -e "\nUsage: $0 HWMON_ID FAN_SPEED"
    echo -e "\n"
    echo -e "SPFRX_IP : The SPFRx TALON-DX HPS IP Address"
    echo -e "FAN_SPEED : Integer between 150-255 to set PWM value"
    echo -e "SPFRX_BSP_HWMON : (Optional) The numerical digit of HWMON ID for fan control device"
    echo -e "           (Defaults to 1)"
}

if [ $# -lt 2]
then
    display_usage
    exit 1
fi

SPFRX_IP=${1}
SPEED=${2}
HWMON=${3:1}

HWMON_DIR=/sys/devices/platform/soc/ffc02800.i2c/i2c-0/0-0020/hwmon/hwmon${HWMON}

if [ ${SPEED} -lt 150 ] || [ -z ${SPEED} ]
then
    echo "Requested fan speed is lower than 150. Please choose a higher value."
    exit 1
fi

if [ ${SPEED} -gt 255 ] || [ -z ${SPEED} ]
then
    echo "Requested fan speed is greater than 255. Truncated to max speed."
    SPEED=255
fi

echo "Setting fan speeds to : " ${SPEED}
echo "${SPEED}" > ${HWMON_DIR}/pwm1
echo "${SPEED}" > ${HWMON_DIR}/pwm2
echo "${SPEED}" > ${HWMON_DIR}/pwm3


