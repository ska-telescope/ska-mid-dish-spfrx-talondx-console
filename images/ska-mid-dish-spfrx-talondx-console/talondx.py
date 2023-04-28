#!/usr/bin/env python3
import argparse
import copy
import getpass
import logging
import os
import re
import subprocess
import time
from enum import Enum

import requests
import tango
from bite_device_client.bite_client import BiteClient
from lmc_interface import LmcInterface
from requests.structures import CaseInsensitiveDict
from talondx_config.talondx_config import TalonDxConfig
from tango import DeviceProxy
from tqdm import tqdm

LOG_FORMAT = "[talondx.py: line %(lineno)s]%(levelname)s: %(message)s"


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    OK = "\x1b[6;30;42m"
    FAIL = "\x1b[0;30;41m"
    ENDC = "\x1b[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class Target(Enum):
    TALON_1 = "talon1"
    TALON_2 = "talon2"
    TALON_3 = "talon3"
    TALON_4 = "talon4"
    DELL = "dell"


class Version:
    """
    Class to facilitate extracting and comparing version numbers in filenames.

    :param filename: string containing a version substring in the x.y.z format, where x,y,z are numbers.
    """

    def __init__(self, filename):
        [ver_x, ver_y, ver_z] = re.findall("[0-9]+", filename)
        self.X = int(ver_x)
        self.Y = int(ver_y)
        self.Z = int(ver_z)

    def match(self, ver):
        """
        Compare two Version object and return true if the versions match.

        :param ver: Version object being compared to this one.
        """
        return self.X == ver.X and self.Y == ver.Y and self.Z == ver.Z


POWER_SWITCH_USER = os.environ.get("POWER_SWITCH_USER")
POWER_SWITCH_PASS = os.environ.get("POWER_SWITCH_PASS")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACTS_DIR = os.path.join(PROJECT_DIR, "artifacts")
TALONDX_CONFIG_FILE = os.path.join(ARTIFACTS_DIR, "talondx-config.json")
DOWNLOAD_CHUNK_BYTES = 1024

TALONDX_STATUS_OUTPUT_DIR = os.environ.get("TALONDX_STATUS_OUTPUT_DIR")

TALON_UNDER_TEST = os.environ.get("TALON_UNDER_TEST")

GITLAB_PROJECTS_URL = "https://gitlab.drao.nrc.ca/api/v4/projects/"
GITLAB_API_HEADER = {
    "PRIVATE-TOKEN": f'{os.environ.get("GIT_ARTIFACTS_TOKEN")}'
}

NEXUS_API_URL = "https://artefact.skatelescope.org/service/rest/v1/"
RAW_REPO_USER = os.environ.get("RAW_USER_ACCOUNT")
RAW_REPO_PASS = os.environ.get("RAW_USER_PASS")


class PowerSwitchState(Enum):
    ON = "ON"
    OFF = "OFF"
    UNKNOWN = "???"


class PowerSwitch:
    """
    Class to manage the network-controlled power switch.
    """

    def __init__(self):
        self._base_url = "http://192.168.0.100/restapi/relay/outlets/"
        # self.state = PowerSwitchState(PowerSwitchState.UNKNOWN)
        self.outlets = "0"  # Only one Talon LRU currently supported

    def state(self):
        """
        Queries the power switch state and returns the result as PowerSwitchState enum
        """
        api_url = f"{self._base_url}={self.outlets}/state/"
        header = CaseInsensitiveDict()
        header["Accept"] = "application/json"
        response = requests.get(
            url=api_url,
            headers=header,
            auth=(POWER_SWITCH_USER, POWER_SWITCH_PASS),
        )
        if response.status_code in [
            requests.codes.ok,  # pylint: disable=no-member
            requests.codes.multi_status,  # pylint: disable=no-member
        ]:
            return self.convert_reponse_to_state(response.text)
        else:
            logger_.info(
                f"Error: unrecognized or failed power switch response: {response}"
            )
            return PowerSwitchState.UNKNOWN

    @staticmethod
    def convert_reponse_to_state(response):
        if "true" in response and "false" not in response:
            return PowerSwitchState.ON
        elif "false" in response and "true" not in response:
            return PowerSwitchState.OFF
        else:
            return PowerSwitchState.UNKNOWN

    def off(self):
        """
        Check the switch state, then powers it off if the switch state is not already off; otherwise no action.
        NOTE: it is strongly recommended to shut down the Talon boards prior to powering off.
        """
        pwr_state = self.state()
        if pwr_state != PowerSwitchState.OFF:
            logger_.info("Powering off...")
            header = CaseInsensitiveDict()
            header["Accept"] = "application/json"
            header["X-CSRF"] = "x"
            header["Content-Type"] = "application/x-www-form-urlencoded"
            data = "value=false"
            response = requests.put(
                url=f"{self._base_url}={self.outlets}/state/",
                data=data,
                headers=header,
                auth=(POWER_SWITCH_USER, POWER_SWITCH_PASS),
            )
            if response.status_code in [
                requests.codes.ok,  # pylint: disable=no-member
                requests.codes.multi_status,  # pylint: disable=no-member
            ]:
                countdown_message(
                    message="Waiting to ensure power off ...", count=5
                )
                # check state after power off
                logger_.info(
                    f"Power Switch (outlets: {self.outlets}): {self.state().value}"
                )
            else:
                logger_.info(
                    f"Power off request failed - response: {response.status_code}, {response.text}"
                )
        else:
            logger_.info(
                f"No action - power switch (outlets: {self.outlets}): {pwr_state.value}"
            )


def countdown_message(message, count, delay_step=1):
    countdown = tqdm(range(count))
    for c in countdown:
        countdown.set_description(f"{message} [{(count - c):>2}]")
        time.sleep(1)
    logger_.info("")


def make_dir(target, dir):
    logger_.info(f"Creating directory {dir} on {target.value} ...")
    try:
        proc = subprocess.Popen(
            ["ssh", f"root@{target.value}", f"mkdir -p {dir}"]
        )
        count = 0
        while proc.poll() is None:
            count += 1
            logger_.info("." * count, end="\r")
            time.sleep(0.2)
    except Exception as e:
        logger_.info(f"Directory creation failed (Exception: {e}).")


def get_device_version_info(config_commands):
    """
    Reads and displays the `dsVersionId`, `dsBuildDateTime`, and `dsGitCommitHash` attributes
    of each HPS Tango device running on the Talon DX boards, as specified in the configuration
    commands -- ref `"config_commands"` in the talondx-config JSON file.

    :param config_commands: JSON array of configure commands
    :type config_commands: str
    """
    targets = [Target.TALON_1, Target.TALON_2, Target.TALON_3]
    for target in targets:
        logger_.info("================")
        logger_.info(f"Target: {target.value}")
        logger_.info("================")
        config_cmd = [
            cmd for cmd in config_commands if cmd.get("target") == target.value
        ][0]

        devices = config_cmd["devices"]
        devices.insert(0, "dshpsmaster")

        for dev_name in get_device_fqdns(
            devices, config_cmd["server_instance"]
        ):
            try:
                dev_proxy = DeviceProxy(dev_name)

                if dev_proxy.import_info().exported:
                    logger_.info(f"{dev_proxy.info().dev_class:<20}{dev_name}")
                    attr_names = [
                        "dsVersionId",
                        "dsBuildDateTime",
                        "dsGitCommitHash",
                    ]
                    for attr_name in attr_names:
                        try:
                            attr_value = dev_proxy.read_attribute(attr_name)
                            logger_.info(
                                f"  {attr_value.name:<20}: {attr_value.value}"
                            )
                        except Exception as attr_except:
                            logger_.info(
                                f"Error reading attribute: {attr_except}"
                            )
                else:
                    logger_.info(f"{dev_name}   DEVICE NOT EXPORTED!")
            except Exception as proxy_except:
                logger_.info(
                    f"Error on DeviceProxy ({dev_name}): {proxy_except}"
                )


def get_device_fqdn_list():
    """
    Get full list of fully-qualified device names (FQDNs) from the Tango database, excluding "sys" and "dserver" names.

    Ref: https://tango-controls.readthedocs.io/en/latest/tutorials-and-howtos/how-tos/how-to-pytango.html

    :returns: alphabetically-sorted list of FQDNs (str)
    """
    try:
        db = tango.Database()
    except Exception as db_except:
        logger_.info(f"Database error: {db_except}")
        exit()

    instances = []
    for server in db.get_server_list():
        # Filter out the unwanted items from the list to get just the FQDNs of our devices...
        # the full list from get_device_class_list() has the structure:
        # [device name, class name, device name, class name, ...]
        # and also includes the admin server (dserver/exec_name/instance)
        instances += [
            dev
            for dev in db.get_device_class_list(server)
            if "/" in dev
            and not dev.startswith("dserver")
            and not dev.startswith("sys")
        ]

    return sorted(instances)


def get_device_fqdns(devices, server_inst):
    """
    Generate list of fully-qualified device names (FQDNs) from Tango database for the
    given list of devices and server instance.

    Ref: https://tango-controls.readthedocs.io/en/latest/tutorials-and-howtos/how-tos/how-to-pytango.html

    :param devices: device names
    :type devices: list of str
    :param server_inst: server instance
    :type server_inst: string

    :returns: list of FQDNs (str)
    """
    try:
        db = tango.Database()
    except Exception as db_except:
        logger_.info(f"Database error: {db_except}")
        exit()

    dev_names = []
    server_list = db.get_server_list()
    for ds in devices:
        for server in server_list:
            if server_inst in server and ds in server:
                # Filter out the unwanted items from the list to get just the FQDNs of our devices...
                # the full list from get_device_class_list() has the structure:
                # [device name, class name, device name, class name, ...]
                # and also includes the admin server (dserver/exec_name/instance)
                dev_names += [
                    dev
                    for dev in db.get_device_class_list(server)
                    if "/" in dev and not dev.startswith("dserver")
                ]

    return dev_names


def get_device_status(config_commands):
    """
    Reads and displays the state and status of each HPS Tango device running on the
    Talon DX boards, as specified in the configuration commands -- ref `"config_commands"`
    in the talondx-config JSON file.

    :param config_commands: JSON array of configure commands
    :type config_commands: str
    """
    targets = [Target.TALON_1, Target.TALON_2]
    for target in targets:
        logger_.info("================")
        logger_.info(f"Target: {target.value}")
        logger_.info("================")
        config_cmd = [
            cmd for cmd in config_commands if cmd.get("target") == target.value
        ][0]

        devices = copy.deepcopy(config_cmd["devices"])
        devices.insert(0, "dshpsmaster")

        for dev_name in get_device_fqdns(
            devices, config_cmd["server_instance"]
        ):
            try:
                dev_proxy = DeviceProxy(dev_name)
            except Exception as proxy_except:
                logger_.info(
                    f"Error on DeviceProxy {dev_name}: {proxy_except}"
                )
                break
            if dev_proxy.import_info().exported:
                try:
                    ds_state = str(dev_proxy.state())
                    ds_status = dev_proxy.status()
                    logger_.info(
                        f"{dev_name:<50}: state {ds_state:<8}  status={ds_status}"
                    )
                except Exception as status_except:
                    logger_.info(
                        f"Error reading state or status of {dev_name}: {status_except}"
                    )
            else:
                logger_.info(f"{dev_name}   DEVICE NOT EXPORTED!")


if __name__ == "__main__":
    logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
    logger_ = logging.getLogger("talondx.py")
    logger_.info(f"User: {getpass.getuser()}")
    parser = argparse.ArgumentParser(description="Talon DX Utility")
    parser.add_argument(
        "-v",
        "--verbose",
        help="increase output verbosity",
        action="store_true",
    )
    parser.add_argument(
        "--db-list",
        help="list the FQDNs (fully qualified domain names) of the HPS and MCS devices in the Tango database",
        action="store_true",
    )
    parser.add_argument(
        "--dish-packet-capture",
        help="Start the Dish Packet Capture",
        action="store_true",
    )
    parser.add_argument(
        "--talon-version",
        help="get the version information of the Tango devices running on the Talon DX boards",
        action="store_true",
    )
    parser.add_argument(
        "--talon-status",
        help="get the status information of the Tango devices running on the Talon DX boards",
        action="store_true",
    )
    parser.add_argument(
        "--talon-power-status",
        help="get the status of the Talon LRU power supply",
        action="store_true",
    )
    parser.add_argument(
        "--mcs-off",
        help="run the MCS Off command sequence",
        action="store_true",
    )
    parser.add_argument(
        "--mcs-on", help="run the MCS On command sequence", action="store_true"
    )
    parser.add_argument(
        "--rdma-on-commands",
        help="set the rdma on commands to connect to tx and transfer data",
        action="store_true",
    )
    parser.add_argument(
        "--mcs-vcc-scan", help="run the scan vcc commands", action="store_true"
    )
    parser.add_argument(
        "--mcs-fsp-scan", help="run the scan fsp commands", action="store_true"
    )
    parser.add_argument(
        "--write-talon-status",
        help="write talon board status to file",
        action="store_true",
    )
    args = parser.parse_args()

    if args.db_list:
        logger_.info("DB List")
        for inst in get_device_fqdn_list():
            logger_.info(inst)
    elif args.dish_packet_capture:
        logger_.info("Dish Packet Capture")
        subprocess.run(
            "python3 ./mellanox_dish_packet_capture/src/PlotSampleData.py ./mellanox_dish_packet_capture/src/default_inputs.json ./mellanox_dish_packet_capture/src/default_inputs.json",
            shell=True,
        )
    elif args.talon_version:
        logger_.info("Talon Version Information")
        config = TalonDxConfig(config_file=TALONDX_CONFIG_FILE)
        get_device_version_info(config.config_commands())
    elif args.talon_status:
        logger_.info("Talon Status Information")
        config = TalonDxConfig(config_file=TALONDX_CONFIG_FILE)
        while True:
            os.system("clear")
            get_device_status(config.config_commands())
            time.sleep(2)
    elif args.talon_power_status:
        pwr = PowerSwitch()
        logger_.info(
            f"Power Switch (outlets: {pwr.outlets}): {pwr.state().value}"
        )
    elif args.mcs_off:
        lmc_interface = LmcInterface()
        lmc_interface.off_command()
    elif args.mcs_on:
        lmc_interface = LmcInterface()
        lmc_interface.on_command()
    elif args.mcs_vcc_scan:
        lmc_interface = LmcInterface()
        lmc_interface.vcc_scan()
    elif args.mcs_fsp_scan:
        lmc_interface = LmcInterface()
        lmc_interface.fsp_scan()
    elif args.rdma_on_commands:
        config = TalonDxConfig(config_file=TALONDX_CONFIG_FILE)
        for command in config.config_commands():
            if command["server_instance"] == TALON_UNDER_TEST:
                lmc_interface = LmcInterface()
                lmc_interface.rdma_on_commands(
                    rdma_rx_fqdn=command["ds_rdma_rx_fqdn"]
                )
    elif args.write_talon_status:
        logger_.info("Print Talon Status")
        config = TalonDxConfig(config_file=TALONDX_CONFIG_FILE)
        for command in config.config_commands():
            if "ska-talondx-status-ds" in command["devices"]:
                bite = BiteClient(command["server_instance"], False)
                bite.init_devices(
                    "bite_device_client/json/device_server_list.json"
                )
                bite.write_talon_status(
                    "bite_device_client/json/status_attr_list.json",
                    TALONDX_STATUS_OUTPUT_DIR,
                )
    else:
        logger_.info("Hello from Mid CBF Engineering Console!")
