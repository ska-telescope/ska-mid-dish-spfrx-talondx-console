#!/usr/bin/env python3
import argparse
import getpass
import logging
import tango
import time

from pytango_client_wrapper import PyTangoClientWrapper
from tango import DeviceProxy

MIN_BAND = 1
MAX_BAND = 3
MIN_ATTEN : float = 0.0
MAX_ATTEN : float = 31.75
POL_H = 0
POL_V = 1
POLS = ("H", "V")
ND_MODE = ("OFF", "PERIODIC", "PSEUDO-RANDOM")
ND_STATE = ("UNKNOWN", "ENABLED", "DISABLED")

SPFRX_DEVICE = "ska001"
SPFRX_NAME = "spfrxpu"

LOG_FORMAT = (
    "[spfrx.py: line %(lineno)s]%(levelname)s: %(message)s"
)
VERSION = "0.0.1"

SPFRX_DEVICE_LIST = {
    "ctrl": "controller",
    "odl12": "odl-12",
    "odl3": "odl-3",
    "bp12": "bandprocessor123-0",
    "bp3": "bandprocessor123-1",
    "drx12": "datarx123-0",
    "drx3": "datarx123-1",
    "eth": "100gigeth",
    "pktcap": "pktcap",
    "mux": "mux",
    "sysid": "sysid",
    "temp": "temperature",
    "ltm-1": "ltm-1",
    "ltm-2": "ltm-2",
    "ltm-11": "ltm-11",
    "ltm-12": "ltm-12",
    "fan": "fan",
    "fpgatemp": "fpgatemp-1",
    "mbo-rx1": "mbo-rx1",
    "mbo-rx2": "mbo-rx2",
    "mbo-tx1": "mbo-tx1",
    "mbo-tx2": "mbo-tx2"
}


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


def get_device_status(
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME,
        ) -> None:
    """
    Reads and displays the state and status of each HPS Tango device
    running on the Talon DX boards, as specified in the configuration
    commands -- ref `"config_commands"` in the talondx-config JSON file.

    :param config_commands: JSON array of configure commands
    :type config_commands: str
    """
    logger_.info("================")
    logger_.info(" Target: SFPRx")
    logger_.info("================")

    for dev_name in SPFRX_DEVICE_LIST:
        try:
            dev_proxy = DeviceProxy(
                getFqdn(SPFRX_DEVICE_LIST[dev_name], device, name)
            )
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
                    f"{dev_name:<50}: state {ds_state:<8}  "
                    f"status={ds_status}"
                )
            except Exception as status_except:
                logger_.info(
                    f"Error reading state or status of {dev_name}: "
                    f"{status_except}"
                )
        else:
            logger_.info(f"{dev_name}   DEVICE NOT EXPORTED!")


def get_device_fqdn_list() -> list:
    """
    Get full list of fully-qualified device names (FQDNs) from the Tango
    database, excluding "sys" and "dserver" names.

    Ref: https://tango-controls.readthedocs.io/en/latest/
    tutorials-and-howtos/how-tos/how-to-pytango.html

    :returns: alphabetically-sorted list of FQDNs (str)
    """
    try:
        db = tango.Database()
    except Exception as db_except:
        logger_.info(f"Database error: {db_except}")
        exit()

    instances = []
    for server in db.get_server_list():
        # Filter out the unwanted items from the list to get just the FQDNs
        # of our devices... the full list from get_device_class_list() has
        # the structure:
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


def get_device_version_info(
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME,
        ) -> None:
    """
    Reads and displays the `dsVersionId`, `dsBuildDateTime`, and
    `dsGitCommitHash` attributes of each HPS Tango device running
    on the SPFRx Talon DX boards, as specified in the configuration
    commands -- ref `"config_commands"` in the spfrx-config JSON file.

    :param config_commands: JSON array of configure commands
    :type config_commands: str
    """
    logger_.info("================")
    logger_.info(" Target: SPFRx")
    logger_.info("================")

    for dev_name in SPFRX_DEVICE_LIST:
        try:
            dev_proxy = DeviceProxy(
                getFqdn(SPFRX_DEVICE_LIST[dev_name], device, name)
            )
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


def getFqdn(
        alias: str,
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME,
        ) -> str:
    """
    Construct the TANGO FQDN from supplied string values in the following form:
    device/name/alias

    :param alias: Alias string
    :param device: Device string, defaults to SPFRX_DEVICE
    :param name: Name string, defaults to SPFRX_NAME
    :returns: A TANGO FQDN string
    """
    return f"{device}/{name}/{alias}"


def validateBand(
        band: int
        ) -> bool:
    """
    Validate the provided band value to be within the allowable integer range

    :param band: An integer band value to be validated
    :returns: A boolean True if valid
    """
    if (MIN_BAND <= int(band) <= MAX_BAND) and (int(band) != 0):
        return True
    print(
        f"BAND VALIDATION ERROR:\n"
        f"  Specified band ({band}) is outside of valid range.\n"
        f"  Band must be an integer within range "
        f"[{MIN_BAND},{MAX_BAND}]"
    )
    return False


def validateAtten(
        atten: float
        ) -> bool:
    """
    Validate the provided attenuator value

    :param atten: An attenuation value to be validated (int or float)
    :returns: A boolean True if valid
    """
    if MIN_ATTEN <= atten <= MAX_ATTEN:
        return True
    else:
        print(
            f"ATTENUATION VALUE VALIDATION ERROR:\n"
            f"  Specified attenuation value is "
            f" outside of valid range.\n"
            f"  Attenuation values must be floats within range"
            f"[{MIN_ATTEN},{MAX_ATTEN}]."
        )
    return False


def getConfiguredAtten(
        band: int,
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME
        ) -> tuple:
    """
    Retrieve the currently configured band attenuation values from the SPFRx

    :param band: The integer band ID (this value will be validated)
    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: A tuple containing attenuation values [POL_H,POL_V]
    """

    spfrx_ctrl = PyTangoClientWrapper()
    spfrx_ctrl.create_tango_client(
        getFqdn(SPFRX_DEVICE_LIST["ctrl"], device, name)
    )
    spfrx_ctrl.set_timeout_millis(5000)

    if validateBand(band):
        try:
            atts = spfrx_ctrl.read_attributes(
                [
                    f"b{band}pol{POLS[POL_H]}Attenuation",
                    f"b{band}pol{POLS[POL_V]}Attenuation",
                ]
            )
            if atts is not None:
                return (atts[POL_H].value, atts[POL_V].value)
        except Exception as e:
            print(e)
    return (0.0, 0.0)


def getConfiguredBand(
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME
        ) -> int:
    """
    Retrieves the currently configured SPFRx band ID

    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: The integer band ID of the currently configured band.
              Returns 0 on error.
    """

    spfrx_ctrl = PyTangoClientWrapper()
    spfrx_ctrl.create_tango_client(
        getFqdn(SPFRX_DEVICE_LIST["ctrl"], device, name)
    )
    spfrx_ctrl.set_timeout_millis(5000)

    try:
        value = spfrx_ctrl.read_attribute("configuredBand")
        return int(value)
    except Exception as e:
        print(e)
        return 0


def configureBand(
        band: int, synchronize: bool,
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME
        ) -> bool:
    """
    Attempts to configure the specified band ID in the SPFRx

    :param band: The integer band ID to be configured (value will be validated)
    :param synchronize: Specify True to synchronize.
    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: True on success.
    """

    if validateBand(band):

        currentBand = getConfiguredBand()

        spfrx_ctrl = PyTangoClientWrapper()
        spfrx_ctrl.create_tango_client(
            getFqdn(SPFRX_DEVICE_LIST["ctrl"], device, name)
            )
        spfrx_ctrl.set_timeout_millis(5000)

        try:
            spfrx_ctrl.command_read_write("SetStandbyMode")
            time.sleep(3)

            print(f"Configuring band {band}")
            spfrx_ctrl.command_read_write(f"ConfigureBand{band}", synchronize)
            time.sleep(10)
            operating_mode = spfrx_ctrl.read_attribute("operatingMode")

            if operating_mode != 4:
                tango.Except.throw_exception(
                    "OPERATING_MODE_INCORRECT",
                    "Expected operating mode to be DATA_CAPTURE\n"
                    + f"Query returned (enum): {operating_mode}",
                    f"configureBand({band},{synchronize}",
                )

            currentBand = int(spfrx_ctrl.read_attribute("configuredBand"))

            if band != currentBand:
                print(f"  Unable to configure band {band}")
                return False

            print(f"  Successfully configured band {band}")
            a = getConfiguredAtten(band)
            print(f"  Configured attenuation : H:{a[POL_H]} V:{a[POL_V]}")
            return True

        except tango.DevFailed:
            tango.Except.throw_exception(
                "UNABLE_TO_CONFIGURE_BAND",
                f"Unable to configure band {band}",
                f"configureBand({band},{synchronize}",
            )

    else:
        return False


def configureAtten(
        band: int,
        pol: int,
        atten: float,
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME
        ) -> bool:
    """
    Configure the SPFRx Attenuation values for a specified polarization

    :param band: The band ID (will be validated)
    :param pol: The polarization (POL_H=0, POL_V=1)
    :param atten: The atteunator value (will be validated)
    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: True on success.
    """

    if validateBand(band) and validateAtten(atten) and (pol == 0 or pol == 1):

        spfrx_ctrl = PyTangoClientWrapper()
        spfrx_ctrl.create_tango_client(
            getFqdn(SPFRX_DEVICE_LIST["ctrl"], device, name)
        )
        spfrx_ctrl.set_timeout_millis(5000)

        print(f"Setting band {band} pol {POLS[pol]} attenuator value: {atten}")
        try:
            attr = f"b{band}Pol{POLS[pol]}Attenuation"
            spfrx_ctrl.write_attribute(attr, atten)

            checkval = spfrx_ctrl.read_attribute(attr)
            if abs(atten - float(checkval)) < 0.1:
                print(
                    f"  Successfully configured band {band} "
                    f"pol {POLS[pol]} atten : {float(checkval)}"
                )
                return True
            else:
                print(
                    f"  Unable to configure Band {band} "
                    f"pol {POLS[pol]} attenuator."
                )

        except tango.DevFailed:
            tango.Except.throw_exception(
                "UNABLE_TO_CONFIGURE_ATTENUATOR",
                f"configAtten({band},{POLS[pol]},{atten}",
            )

    return False


def invertSpectralSense(
        band: int,
        sense: bool = True,
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME
        ) -> bool:
    """
    Invert the spectral sense by writing directly to firmware.

    :param sense: True to invert (default), False to revert to original config
    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: True on success.
    """

    spfrx_bp = PyTangoClientWrapper()
    if (band == 1) or (band ==2):
        spfrx_bp.create_tango_client(
            getFqdn(SPFRX_DEVICE_LIST["bp12"], device, name)
        )
    if (band == 3):
        spfrx_bp.create_tango_client(
            getFqdn(SPFRX_DEVICE_LIST["bp3"], device, name)
        )

    spfrx_bp.set_timeout_millis(5000)
    attr = "spec_inv"

    try:
        spfrx_bp.write_attribute(attr, int(sense))
    except tango.DevFailed:
        tango.Except.throw_exception(
            f"UNABLE TO WRITE TO {attr} on band {band}",
            f"invertSpectralSense({band}, {sense})",
        )
        return False

    return True


def enableNoiseDiode(
        enable: bool,
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME
        ) -> bool:
    """
    Enable/Disable the noise diode

    :param enable: True to enable, False to disable.
                   duty & period ignored if disabling
    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: True on success.
    """

    spfrx_ctrl = PyTangoClientWrapper()
    spfrx_ctrl.create_tango_client(
        getFqdn(SPFRX_DEVICE_LIST["ctrl"], device, name)
    )
    spfrx_ctrl.set_timeout_millis(5000)

    try:
        spfrx_ctrl.command_read_write("SetNoiseDiodeState", enable)
        return True
    except tango.DevFailed:
        tango.Except.throw_exception(
            "UNABLE TO EXECUTE COMMAND on controller",
            f"SetNoiseDiodeState({enable})",
        )
        return False


def getNoiseDiodeConfig(
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME
        ) -> None:
    """
    Retrieve and display noise diode control parameters

    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    """

    spfrx_ctrl = PyTangoClientWrapper()
    spfrx_ctrl.create_tango_client(
        getFqdn(SPFRX_DEVICE_LIST["ctrl"], device, name)
    )
    spfrx_ctrl.set_timeout_millis(5000)

    try:
        atts = spfrx_ctrl.read_attributes(
            [
                "noiseDiodeState",
                "noiseDiodeMode",
                "periodicNoiseDiodePars",
                "pseudoRandomNoiseDiodePars"
            ]
        )
        if atts is not None:
            if atts[1].value == 1:
                config = f" Period : {atts[2][0]}\n"
                config += f" Duty Cycle : {atts[2][1]}\n"
                config += f" Phase Shift : {atts[2][2]}"
            elif atts[1].value == 2:
                config = f" Binary Polynomial : {atts[3][0]}\n"
                config += f" Seed : {atts[3][1]}\n"
                config += f" Dwell : {atts[3][2]}"
            else:
                config = "N/A"
            logger_.info(
                "Noise Diode configuration:\n"
                f" Mode : {ND_MODE[atts[1].value]}\n"
                f" State : {ND_STATE[atts[0].value]}\n"
                f" Config : {config}"
            )

    except tango.DevFailed:
        tango.Except.throw_exception(
            "UNABLE TO RETRIEVE ATTRIBUTE VALUES"
        )
        return False


def configureNoiseDiode(
        values: list[int],
        attr: str,
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME
        ) -> bool:
    """
    Configure the noise diode parameters after setting the
    SPFRx into standby mode

    :param values: A 3-integer array containing parameters for
                   the desired noise diode configuration type
    :param attr: The attribute string to write values to
                (Must be either 'periodic' or 'pseudoRandom')
    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: True on success.
    """

    spfrx_ctrl = PyTangoClientWrapper()
    spfrx_ctrl.create_tango_client(
        getFqdn(SPFRX_DEVICE_LIST["ctrl"], device, name)
    )
    spfrx_ctrl.set_timeout_millis(5000)

    try:
        logger_.info("Setting SPFRx into STANDBY mode")
        spfrx_ctrl.command_read_write("SetStandbyMode")
        time.sleep(3)

        spfrx_ctrl.write_attribute(
            f"{attr}NoiseDiodePars",
            values
            )
    except tango.DevFailed:
        tango.Except.throw_exception(
            f"UNABLE TO WRITE TO {attr}NoiseDiodePars on controller",
            f"configureNoiseDiode({values},{attr},{device},{name})",
        )
        return False


def configureNoiseDiodePeriodic(
        values: list[int],
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME
        ) -> bool:
    return configureNoiseDiode(
        values, "periodicNoiseDiodePars", device, name
    )


def configureNoiseDiodePseudoRandom(
        values: list[int],
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME
        ) -> bool:
    return configureNoiseDiode(
        values, "pseudoRandomNoiseDiodePars", device, name
    )


def enableSpectrometer(
        enable: bool,
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME
        ) -> bool:
    """
    Enable or disable the spectrometer

    :param enable: True to enable, False to disable
    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: True on success.
    """

    spfrx_ctrl = PyTangoClientWrapper()
    spfrx_ctrl.create_tango_client(
        getFqdn(SPFRX_DEVICE_LIST["ctrl"], device, name)
    )
    spfrx_ctrl.set_timeout_millis(5000)

    try:
        spfrx_ctrl.command_read_write("SpectrometerCtrl", enable)
        return True
    except tango.DevFailed:
        tango.Except.throw_exception(
            "UNABLE TO EXECUTE COMMAND on controller",
            f"SpectrometerCtrl({enable})",
        )
        return False


def setSpectrometerBridge(
        bridge: int,
        device: str = SPFRX_DEVICE,
        name: str = SPFRX_NAME
        ) -> bool:
    """
    Set the FPGA bridge to use with the Gated Spectrometer.

    :param bridge: Provide '1' for LW bridge, '0' for HP bridge
    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: True on success.
    """

    spfrx_pktcap = PyTangoClientWrapper()
    spfrx_pktcap.create_tango_client(
        getFqdn(SPFRX_DEVICE_LIST["pktcap"], device, name)
    )
    spfrx_pktcap.set_timeout_millis(5000)

    try:
        spfrx_pktcap.command_read_write("spectrometer_set_bridge", bridge)
        return True
    except tango.DevFailed:
        tango.Except.throw_exception(
            "UNABLE TO EXECUTE COMMAND on controller",
            f"spectrometer_set_bridge({bridge})",
        )
        return False


if __name__ == "__main__":
    logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
    logger_ = logging.getLogger("spfrx-talondx.py")
    logger_.info(f"User: {getpass.getuser()}")
    parser = argparse.ArgumentParser(description="MID DISH SPFRx Console Ops.")
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Print version information for this module.",
    )
    parser.add_argument(
        "-sync",
        "--synchronize_on_band_config",
        action="store_true",
        help="Specify sychronization when configuring band. " +
             "Default is FALSE." +
             "Only applicable when configuring a band."
    )
    parser.add_argument(
        "-d",
        "--device",
        type=str,
        metavar="DEVICE",
        default=SPFRX_DEVICE,
        help=f"Override the default FQDN device (default is {SPFRX_DEVICE})."
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        metavar="NAME",
        default=SPFRX_NAME,
        help=f"Override the default FQDN name (default is {SPFRX_NAME})."
    )
    spfrx_action = parser.add_mutually_exclusive_group()
    spfrx_action.add_argument(
        "-vall",
        "--version_tango_all",
        action="store_true",
        help="Print TANGO version information for all device servers.",
    )
    spfrx_action.add_argument(
        "-fqdn",
        "--fqdn_list_all",
        action="store_true",
        help="Print TANGO DB FQDN list.",
    )
    spfrx_action.add_argument(
        "-status",
        "--status_tango_all",
        action="store_true",
        help="Print TANGO Device status.",
    )
    spfrx_action.add_argument(
        "-b",
        "--band",
        type=int,
        metavar="BAND_ID",
        help="Activate switch to the specified band",
    )
    spfrx_action.add_argument(
        "-a",
        "--atten",
        type=str,
        nargs=3,
        metavar=("BAND", "POLH_ATTEN", "POLV_ATTEN"),
        help="Configure both HORIZONTAL POL and VERTICAL POL attenuator "
        + "values for a specific band.\n"
        + "Band is an integer from 1-3\n"
        + "Provide H & V pol attenuation values as float values "
        + "between 0 and 31.75",
    )
    spfrx_action.add_argument(
        "-av",
        "--attenv",
        type=str,
        nargs=2,
        metavar=("BAND", "POLV_ATTEN"),
        help="Configure the VERTICAL POL attenuator value for a "
        + "specific band.\n"
        + "Band is an integer from 1-3\n"
        + "Provide V pol attenuation value as a float "
        + "between 0 and 31.75",
    )
    spfrx_action.add_argument(
        "-ah",
        "--attenh",
        type=str,
        nargs=2,
        metavar=("BAND", "POLH_ATTEN"),
        help="Configure the HORIZONTAL POL attenuator value for a "
        + "specific band.\n"
        + "Band is an integer from 1-3\n"
        + "Provide H pol attenuation value as a float "
        + "between 0 and 31.75",
    )
    spfrx_action.add_argument(
        "-vb",
        "--verify_band",
        action="store_true",
        help="Verify currently configured band.",
    )
    spfrx_action.add_argument(
        "-va",
        "--verify_atten",
        type=int,
        metavar="BAND",
        help="Verify attenuator settings for the specified band.",
    )
    spfrx_action.add_argument(
        "-inv",
        "--invert_spectral_sense",
        type=int,
        metavar="BAND_ID",
        help="Invert spectral sense for the specified band.",
    )
    spfrx_action.add_argument(
        "-rev",
        "--revert_spectral_sense",
        type=int,
        metavar="BAND_ID",
        help="Revert spectral sense for the specified band.",
    )
    spfrx_action.add_argument(
        "-nde",
        "--noise_diode_enable",
        type=int,
        metavar="ENABLE_STATE",
        help="Enable/Disable the Noise Diode. "
             + "Provide 0 (disable) or 1 (enable as first arg)",
    )
    spfrx_action.add_argument(
        "-ndc",
        "--noise_diode_current_config",
        action="store_true",
        help="Retrieve and display current noise diode configuration.",
    )
    spfrx_action.add_argument(
        "-ndcp",
        "--noise_diode_periodic_config",
        type=int,
        nargs=3,
        metavar=("PWM_PERIOD", "PWM_DUTY_CYCLE", "PWM_PHASE_SHIFT"),
        help="Provide periodic noise diode configuration parameters."
             + "Note that invoking this command will put SPFRx "
             + "into standby mode.",
    )
    spfrx_action.add_argument(
        "-ndcr",
        "--noise_diode_random_config",
        type=int,
        nargs=3,
        metavar=("PRM_BINARY_POLYNOMIAL", "PRM_SEED", "PRM_DWELL"),
        help="Provide pseudo-random noise diode configuration "
             + "parameters. Note that invoking this command will "
             + "put SPFRx into standby mode.",
    )
    spfrx_action.add_argument(
        "-sp",
        "--spectrometer_enable",
        type=int,
        metavar="SPECTROMETER_STATE",
        help="Provide 1 to enable, 0 to disable spectrometer.",
    )
    spfrx_action.add_argument(
        "-bridge",
        "--spectrometer_set_bridge",
        type=int,
        metavar="SPECTROMETER_BRIDGE",
        help="1 to configure LW bridge, 0 to configure HP bridge.",
    )

    args = parser.parse_args()

    if args.version:
        logger_.info(
            f"VERSION: {VERSION}"
        )

    if args.version_tango_all:
        logger_.info("Accessing version information for all Device Servers.")
        get_device_version_info(
            args.device,
            args.name
        )

    if args.fqdn_list_all:
        logger_.info("Accessing TANGO DB for full FQDN Device Server list.")
        logger_.info(get_device_fqdn_list())

    if args.status_tango_all:
        logger_.info("Accessing status information for TANGO Device Servers")
        get_device_status()

    if args.band is not None:
        logger_.info(
            f"Initiating band configuration to BAND:{args.band} "
            f"SYNC:{args.synchronize_on_band_config}"
        )
        result = configureBand(
            int(args.band),
            args.synchronize_on_band_config,
            args.device,
            args.name)
        if result:
            logger_.info("Band configuration SUCCESSFUL")
        else:
            logger_.warning("Band configuration FAILED")

    if args.atten is not None:
        logger_.info(
            f"Initiating attenuator config for BAND:{args.atten[0]} "
            f"POL_H:{args.atten[1]} "
            f"POL_V:{args.atten[2]}"
        )
        result = configureAtten(int(args.atten[0]), int(POL_H), 
                                float(args.atten[1]),
                                args.device, args.name)
        if result:
            logger_.info(f"BAND:{args.atten[0]} POL_H attenuator set to "
                         f"{args.atten[1]} SUCCESSFULLY")
        else:
            logger_.warning(f"BAND:{args.atten[0]} "
                            f" POL_H attenuator config FAILED")

        result = configureAtten(int(args.atten[0]), int(POL_V), 
                                float(args.atten[2]),
                                args.device, args.name)
        if result:
            logger_.info(f"BAND:{args.atten[0]} POL_V attenuator set to "
                         f"{args.atten[2]} SUCCESSFULLY")
        else:
            logger_.warning(f"BAND:{args.atten[0]} "
                            f"POL_V attenuator config FAILED")

    if args.attenv is not None:
        logger_.info(
            f"Initiating attenuator config for BAND:{args.attenv[0]} "
            f"POL_V:{args.attenv[1]}"
        )
        result = configureAtten(int(args.attenv[0]), int(POL_V), 
                                float(args.attenv[1]),
                                args.device, args.name)
        if result:
            logger_.info(f"BAND:{args.attenv[0]} POL_V attenuator set to "
                         f"{args.attenv[1]} SUCCESSFULLY")
        else:
            logger_.warning(f"BAND:{args.attenv[0]} "
                            f"POL_V attenuator config FAILED")

    if args.attenh is not None:
        logger_.info(
            f"Initiating attenuator config for BAND:{args.attenh[0]} "
            f"POL_H:{args.attenh[1]}"
        )
        result = configureAtten(int(args.attenh[0]), int(POL_H), 
                                float(args.attenh[1]),
                                args.device, args.name)
        if result:
            logger_.info(f"BAND:{args.attenh[0]} POL_H attenuator set to "
                         f"{args.attenh[1]} SUCCESSFULLY")
        else:
            logger_.warning(f"BAND:{args.attenh[0]} "
                            f"POL_H attenuator config FAILED")

    if args.verify_band:
        logger_.info(
            "Requesting current configured band ID"
        )
        band = getConfiguredBand(args.device, args.name)
        logger_.info(
            f"Configured BAND : {band}"
        )

    if args.verify_atten is not None:
        logger_.info(
            f"Requesting current configured attenuation settings for "
            f"BAND:{args.verify_atten}"
        )
        attens = getConfiguredAtten(int(args.verify_atten), args.device, args.name)
        logger_.info(
            f"Configured attenuator values for BAND:{args.verify_atten}\n"
            f"  POL_H : {attens[0]}    POL_V : {attens[1]}"
        )

    if args.invert_spectral_sense:
        band = int(args.invert_spectral_sense)
        logger_.info(
            "Inverting spectral sense for band {band}."
        )
        if (band > 0) and (band < 4):
            if invertSpectralSense(band, True, args.device, args.name):
                logger_.info("Spectral sense inversion band {band} SUCCESSFUL")
            else:
                logger_.warning("Spectral sense inversion band {band} FAILED")
        else:
            logger_.waring(f"Improper band specification ({band}). "
                           "Band must be 1, 2 or 3")

    if args.revert_spectral_sense:
        band = int(args.invert_spectral_sense)
        logger_.info(
            "Reverting spectral sense for band {band}."
        )
        if (band > 0) and (band < 4):
            if invertSpectralSense(band, False, args.device, args.name):
                logger_.info("Spectral sense reverted band {band} SUCCESSFULLY")
            else:
                logger_.warning("Spectral sense reversion band {band} FAILED")
        else:
            logger_.waring(f"Improper band specification ({band}). "
                           "Band must be 1, 2 or 3")

    if args.noise_diode_enable:
        logger_.info(
            f"{'Enabling' if args.noise_diode_enable == 1 else 'Disabling'} "
            "noise diode."
        )
        if enableNoiseDiode(args.noise_diode_enable,
                            args.device,
                            args.name
                            ):
            logger_.info(
                f"Noise diode state configured SUCCESSFULLY "
                f"{'ENABLED' if args.noise_diode_enable == 1 else 'DISABLED'}."
            )
        else:
            logger_.warning("Noise diode configuration FAILED.")

    if args.noise_diode_current_config:
        logger_.info(
            "Retrieving current Noise Diode configuration parameters."
        )
        getNoiseDiodeConfig(
            args.device,
            args.name
        )

    if args.noise_diode_periodic_config:
        logger_.info(
            f"Configuring Periodic Noise Diode parameters:\n"
            f"  PWM Period : {args.noise_diode_periodic_config[0]}\n"
            f"  PWM Duty Cycle : {args.noise_diode_periodic_config[1]}\n"
            f"  PWM Phase Shift : {args.noise_diode_periodic_config[2]}"
        )
        if configureNoiseDiodePeriodic(
             args.noise_diode_periodic_config,
             args.device,
             args.name
        ):
            logger_.info("SUCCESS")
        else:
            logger_.warning("FAILED")

    if args.noise_diode_random_config:
        logger_.info(
            f"Configuring Pseudo-Random Noise Diode parameters:\n"
            f"  PRM Binary Polynomial : {args.noise_diode_random_config[0]}\n"
            f"  PRM Seed : {args.noise_diode_random_config[1]}\n"
            f"  PRM Dwell : {args.noise_diode_random_config[2]}"
        )
        if configureNoiseDiodePseudoRandom(
             args.noise_diode_random_config,
             args.device,
             args.name
        ):
            logger_.info("SUCCESS")
        else:
            logger_.warning("FAILED")

    if args.spectrometer_enable:
        logger_.info(
            f"{'Enabl' if args.spectrometer_enable == 1 else 'Disabl'}ing "
            "spectrometer."
            )
        if enableSpectrometer(args.spectrometer_enable,
                              args.device,
                              args.name):
            logger_.info("SUCCESS")
        else:
            logger_.warning("FAILED")

    if args.spectrometer_set_bridge:
        logger_.info(
            f"Setting {'LW' if args.spectrometer_set_bridge == 1 else 'HP'} "
            "bridge."
        )
        if setSpectrometerBridge(
            args.spectrometer_set_bridge,
            args.device,
            args.name
        ):
            logger_.info("SUCCESS")
        else:
            logger_.info("FAILED")

    else:
        logger_.info("Hello from Mid DISH SPFRx Console")
