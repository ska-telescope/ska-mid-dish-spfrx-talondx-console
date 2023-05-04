import argparse
import getpass
import logging
import time

from pytango_client_wrapper import PyTangoClientWrapper

import PyTango as tango

MIN_BAND = 1
MAX_BAND = 3
MIN_ATTEN = 0
MAX_ATTEN = 31.75
POL_H = 0
POL_V = 1
POLS = ("H", "V")

SPFRX_DEVICE = "psi-spfrx"
SPFRX_NAME = "rxpu"

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


def getFqdn(alias: str,
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


def validateBand(band: int) -> bool:
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


def validateAtten(atten: float) -> bool:
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


def getConfiguredAtten(band: int,
                       device: str = SPFRX_DEVICE,
                       name: str = SPFRX_NAME) -> tuple:
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


def getConfiguredBand(device: str = SPFRX_DEVICE,
                      name: str = SPFRX_NAME) -> int:
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


def configureBand(band: int, synchronize: bool,
                  device: str = SPFRX_DEVICE,
                  name: str = SPFRX_NAME) -> bool:
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


def configureAtten(band: int,
                   pol: int,
                   atten: float,
                   device: str = SPFRX_DEVICE,
                   name: str = SPFRX_NAME) -> bool:
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


def invertSpectralSense(sense: bool = True,
                        device: str = SPFRX_DEVICE,
                        name: str = SPFRX_NAME) -> bool:
    """
    Invert the spectral sense

    :param sense: True to invert (default), False to revert to original config
    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: True on success.
    """

    spfrx_bp12 = PyTangoClientWrapper()
    spfrx_bp12.create_tango_client(
        getFqdn(SPFRX_DEVICE_LIST["bp12"], device, name)
    )
    spfrx_bp12.set_timeout_millis(5000)

    spfrx_bp3 = PyTangoClientWrapper()
    spfrx_bp12.create_tango_client(
        getFqdn(SPFRX_DEVICE_LIST["bp3"], device, name)
    )
    spfrx_bp3.set_timeout_millis(5000)

    attr = "spec_inv"

    try:
        spfrx_bp12.write_attribute(attr, int(sense))
    except tango.DevFailed:
        tango.Except.throw_exception(
            f"UNABLE TO WRITE TO {attr} on bandprocessor123-0",
            f"invertSpectralSense({sense})",
        )
        return False

    try:
        spfrx_bp3.write_attribute(attr, int(not sense))
    except tango.DevFailed:
        tango.Except.throw_exception(
            f"UNABLE TO WRITE TO {attr} on bandprocessor123-1",
            f"invertSpectralSense({sense})",
        )
        return False

    return True


def setFanPwm(value: int,
              device: str = SPFRX_DEVICE,
              name: str = SPFRX_DEVICE) -> bool:
    """
    Set the fan speed

    :param value: new fan pwm value [0-255]
    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: True on success.
    """

    if value < 100:
        logger_.warning(f"Overriding low fan speed {value}/255 -> 100/255.")
        value = 100
    if value > 255:
        logger_.info("Maximum fan speed is 255/255. Setting to MAX.")
        value = 255

    spfrx_fan = PyTangoClientWrapper()
    spfrx_fan.create_tango_client(
        getFqdn(SPFRX_DEVICE_LIST["fan"], device, name)
    )
    spfrx_fan.set_timeout_millis(5000)
    # set the fan speed


def configureNoiseDiode(enable: bool,
                        duty: int,
                        period: int,
                        device: str = SPFRX_DEVICE,
                        name: str = SPFRX_NAME) -> bool:
    """
    Configure the noise diode

    :param enable: True to enable, False to disable.
                   duty & period ignored if disabling
    :param duty: The noise diode duty cycle
    :param period: The noise diode period
    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: True on success.
    """

    spfrx_bp12 = PyTangoClientWrapper()
    spfrx_bp12.create_tango_client(
        getFqdn(SPFRX_DEVICE_LIST["bp12"], device, name)
    )
    spfrx_bp12.set_timeout_millis(5000)
    # configure the noise diode


def enableSpectrometer(enable: bool,
                       device: str = SPFRX_DEVICE,
                       name: str = SPFRX_NAME) -> bool:
    """
    Enable or disable the spectrometer

    :param enable: True to enable, False to disable
    :param device: Optional - TANGO FQDN Device (defaults to SPFRX_DEVICE)
    :param name: Optional - TANGO FQDN Name (defaults to SPFRX_NAME)
    :returns: True on success.
    """

    spfrx_bp12 = PyTangoClientWrapper()
    spfrx_bp12.create_tango_client(
        getFqdn(SPFRX_DEVICE_LIST["bp12"], device, name)
    )
    spfrx_bp12.set_timeout_millis(5000)
    # enable or disable the spectrometer


if __name__ == "__main__":
    logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
    logger_ = logging.getLogger("spfrx-talondx.py")
    logger_.info(f"User: {getpass.getuser()}")
    parser = argparse.ArgumentParser(description="MID DISH SPFRx Console Ops.")
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Print version",
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
        action="store_true",
        help="Invert spectral sense.",
    )
    spfrx_action.add_argument(
        "-rev",
        "--revert_spectral_sense",
        action="store_true",
        help="Revert spectral sense.",
    )
    spfrx_action.add_argument(
        "-nd",
        "--noise_diode_config",
        type=int,
        nargs=3,
        metavar=("ENABLE", "PWM_DUTY_CYCLE", "PWM_PERIOD"),
        help="Configure the Noise Diode. " +
             "Provide 0 (disable) or 1 (enable as first arg)",
    )
    spfrx_action.add_argument(
        "-f",
        "--set_fan_pwm",
        type=int,
        metavar="FAN_PWM",
        help="Set the fan pwm value [100-255].",
    )
    spfrx_action.add_argument(
        "-sp",
        "--spectrometer_enable",
        type=int,
        metavar="SPECTROMETER_STATE",
        help="Provide 1 to enable, 0 to disable spectrometer.",
    )
    args = parser.parse_args()

    print(args)

    if args.version:
        logger_.info(
            f"VERSION: {VERSION}"
        )

    if args.band is not None:
        logger_.info(
            f"Initiating band configuration to BAND:{args.band} "
            f"SYNC:{args.synchronize_on_band_config}"
        )
        result = configureBand(
            args.band,
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
        result = configureAtten(args.atten[0], POL_H, args.atten[1],
                                args.device, args.name)
        if result:
            logger_.info(f"BAND:{args.atten[0]} POL_H attenuator set to "
                         f"{args.atten[1]} SUCCESSFULLY")
        else:
            logger_.warning(f"BAND:{args.atten[0]} "
                            f" POL_H attenuator config FAILED")

        result = configureAtten(args.atten[0], POL_V, args.atten[2],
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
        result = configureAtten(args.atten[0], POL_V, args.atten[2],
                                args.device, args.name)
        if result:
            logger_.info(f"BAND:{args.atten[0]} POL_V attenuator set to "
                         f"{args.atten[2]} SUCCESSFULLY")
        else:
            logger_.warning(f"BAND:{args.atten[0]} "
                            f"POL_V attenuator config FAILED")

    if args.attenh is not None:
        logger_.info(
            f"Initiating attenuator config for BAND:{args.attenh[0]} "
            f"POL_H:{args.attenh[1]}"
        )
        result = configureAtten(args.atten[0], POL_H, args.atten[1],
                                args.device, args.name)
        if result:
            logger_.info(f"BAND:{args.atten[0]} POL_H attenuator set to "
                         f"{args.atten[1]} SUCCESSFULLY")
        else:
            logger_.warning(f"BAND:{args.atten[0]} "
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
        attens = getConfiguredAtten(args.verify_atten, args.device, args.name)
        logger_.info(
            f"Configured attenuator values for BAND:{args.verify_atten}\n"
            f"  POL_H : {attens[0]}    POL_V : {attens[1]}"
        )

    if args.invert_spectral_sense:
        logger_.info(
            "Inverting spectral sense."
        )
        if invertSpectralSense(args.device, args.name):
            logger_.info("Spectral sense inversion SUCCESSFUL")
        else:
            logger_.warning("Spectral sense inversion FAILED")

    if args.revert_spectral_sense:
        logger_.info(
            "Reverting spectral sense."
        )
        if invertSpectralSense(False, args.device, args.name):
            logger_.info("Spectral sense reverted SUCCESSFULLY")
        else:
            logger_.warning("Spectral sense reversion FAILED")

    if args.set_fan_pwm is not None:
        logger_.info(
            f"Setting fan speed to {args.set_fan_pwm}"
        )
        if setFanPwm(args.set_fan_pwm, args.device, args.name):
            logger_.info("Fan speed setting SUCCESSFUL")
        else:
            logger_.warning("Fan speed setting FAILED")

    if args.noise_diode_config is not None:
        if args.noise_diode_config[0] != 0:
            logger_.info(f"Enabling noise diode "
                         f"DUTY:{args.noise_diode_config[1]} "
                         f"PERIOD:{args.noise_diode_config[2]}"
                         )
            if configureNoiseDiode(True,
                                   args.noise_diode_config[1],
                                   args.noise_diode_config[2],
                                   args.device,
                                   args.name
                                   ):
                logger_.info(f"Noise diode configured SUCCESSFULLY "
                             f"DUTY:{args.noise_diode_config[1]} "
                             f"PERIOD:{args.noise_diode_config[2]}")
            else:
                logger_.warning("Noise diode configuration FAILED.")
        else:
            logger_.info("Disabling noise diode")
            if configureNoiseDiode(False, 0, 0,
                                   device=args.device,
                                   name=args.name
                                   ):
                logger_.info("Noise diode DISABLED")
            else:
                logger_.warning("Problem whilc disabling noise diode")

    if args.spectrometer_enable == 0:
        logger_.info("Disabling spectrometer.")
        if enableSpectrometer(False, args.device, args.name):
            logger_.info("Spectrometer DISABLED.")
        else:
            logger_.warning("Problem while disabling spectrometer.")

    if args.spectrometer_enable == 1:
        logger_.info("Enabling spectrometer.")
        if enableSpectrometer(True, args.device, args.name):
            logger_.info("Spectrometer ENABLED.")
        else:
            logger_.warning("Problem while enabling spectrometer.")
