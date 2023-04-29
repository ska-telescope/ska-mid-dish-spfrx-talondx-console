from PyTango import Database, DevFailed, ConnectionFailed
from tango import DeviceProxy
import PyTango as tango
import argparse
import os
import sys
import time

MIN_BAND = 1
MAX_BAND = 3
MIN_ATTEN = 0
MAX_ATTEN = 31.75
POL_H = 0
POL_V = 1
POLS = ("H", "V")


class Spfrx():

    _TANGO_HOST = None
    _TANGO_DB = None

    _currentBand = None

    _ds_ctrl: DeviceProxy
    _deviceList: dict[str : str]

    def __init__(self) -> None:
        args = self.parseInputArguments().parse_args()
        print("Initializing SPFRx-op Application")

        self._currentBand = 0
        self._TANGO_HOST = os.getenv("TANGO_HOST")

        try:
            self.tangoConnect()
        except Exception as e:
            print("Exception while connecting to TANGO DB")
            print(e)
            sys.exit(1)

        if (args.verify_band):
            b = self.getConfiguredBand()
            print(f"  Configured Band : {b}")

        if (args.verify_atten):
            if self.validateBand(args.verify_atten):
                a = self.getConfiguredAtten(int(args.verify_atten))
                print(f"  Band {args.verify_atten} : {a}")

        if (args.band):
            if self.validateBand(args.band):
                self.configureBand(args.band, True)

        if (args.atten):
            if self.validateBand(int(args.atten[0])):
                if (self.validateAtten(float(args.atten[1])) and
                        self.validateAtten(float(args.atten[2]))):
                    self.configureAtten(
                        int(args.atten[0]), POL_H, float(args.atten[1])
                    )
                    self.configureAtten(
                        int(args.atten[0]), POL_V, float(args.atten[2])
                    )

        if (args.attenh):
            if self.validateBand(int(args.attenh[0])):
                if (self.validateAtten(float(args.attenh[1]))):
                    self.configureAtten(
                        int(args.attenh[0]), POL_H, float(args.attenh[1])
                    )

        if (args.attenv):
            if self.validateBand(int(args.attenv[0])):
                if (self.validateAtten(float(args.attenv[1]))):
                    self.configureAtten(
                        int(args.attenv[0]), POL_V, float(args.attenv[1])
                    )

    def validateBand(self, band: int) -> bool:
        if (MIN_BAND <= int(band) <= MAX_BAND) and (int(band) != 0):
            return True
        print(f"BAND VALIDATION ERROR:\n"
              f"  Specified band ({band}) is outside of valid range.\n"
              f"  Band must be an integer within range "
              f"[{MIN_BAND},{MAX_BAND}]"
              )
        return False

    def validateAtten(self, atten) -> bool:
        if (MIN_ATTEN <= atten <= MAX_ATTEN):
            return True
        else:
            print(f"ATTENUATION VALUE VALIDATION ERROR:\n"
                  f"  Specified attenuation value is "
                  f" outside of valid range.\n"
                  f"  Attenuation values must be floats within range"
                  f"[{MIN_ATTEN},{MAX_ATTEN}]."
                  )
        return False

    def dbConnect(self) -> None:
        if self._TANGO_HOST is not None:
            try:
                self._TANGO_DB = Database()
                print(f"  Connected to TANGO DB at {self._TANGO_HOST}")
            except ConnectionFailed as cf:
                errors = []
                errors.append(cf)
                w = Warning(f"Failed to connect to TANGO DB at "
                            f"{self._TANGO_HOST}. Exiting"
                            )
                errors.append(w)
                raise errors
        else:
            raise Exception("Set TANGO_HOST environment variable.")

    def verifyTangoDevices(self, devList) -> bool:
        """
        Method to verify input deviceList against exported device
        server instances within the TANGO DB.
        deviceList is a dict that may contain multiple elements. The
        key-value pair is string:string where
        the key is a descriptor for the device server, and the value
        is the Unique TANGO domain name ( domain/family/name ) of
        the associated device server.
        """
        if (self._TANGO_DB is not None):
            try:
                for d in devList.keys():
                    edl = self._TANGO_DB.get_device_exported(devList[d])
                    if (not devList[d] in edl):
                        print(f"Unable to find device {d} ({devList[d]}) "
                              f"exported in TangoDB"
                              )
                        return False
            except DevFailed as df:
                errors = []
                errors.append(df)
                errors.append(
                    Warning(
                        "Failed to verify required devices are exported in " +
                        "TangoDB"
                        )
                    )
                raise errors

            return True

        return False

    def tangoConnect(self) -> bool:
        # Connect to TANGO DB and create device proxies for
        # required device servers
        self._deviceList = {
            'ctrl': 'spfrx/rxpu/controller',
            'odl12': 'spfrx/rxpu/odl-12',
            'odl3': 'spfrx/rxpu/odl-3',
            'bp12': 'spfrx/rxpu/bandprocessor123-0',
            'bp3': 'spfrx/rxpu/bandprocessor123-1',
            'drx12': 'spfrx/rxpu/datarx123-0',
            'drx3': 'spfrx/rxpu/datarx123-1',
            'eth': 'spfrx/rxpu/100gigeth',
            'pktcap': 'spfrx/rxpu/pktcap',
            'mux': 'spfrx/rxpu/mux',
            'sysid': 'spfrx/rxpu/sysid',
            'bsp-temp': 'spfrx/rxpu-bsp/temperature',
            'bsp-ltm-1': 'spfrx/rxpu-bsp/ltm-1',
            'bsp-ltm-2': 'spfrx/rxpu-bsp/ltm-2',
            'bsp-ltm-11': 'spfrx/rxpu-bsp/ltm-11',
            'bsp-ltm-12': 'spfrx/rxpu-bsp/ltm-12',
            'bsp-fan': 'spfrx/rxpu-bsp/fan',
            'bsp-fpgatemp': 'spfrx/rxpu-bsp/fpgatemp-1',
            'bsp-mbo-rx1': 'spfrx/rxpu-bsp/mbo-rx1',
            'bsp-mbo-rx2': 'spfrx/rxpu-bsp/mbo-rx2',
            'bsp-mbo-tx1': 'spfrx/rxpu-bsp/mbo-tx1',
            'bsp-mbo-tx2': 'spfrx/rxpu-bsp/mbo-tx2'
            }

        self.dbConnect()

        tangoOK = self.verifyTangoDevices(self._deviceList)

        if (tangoOK):
            try:
                self._ds_ctrl = DeviceProxy(self._deviceList['ctrl'])

            except ConnectionFailed as cf:
                print("Exception in tangoConnect: " +
                      "Failed to create device proxy. Exiting")
                raise cf

        return True

    def getConfiguredAtten(self, band: int) -> tuple:
        if (band in range(1, 3)):
            try:
                atts = self._ds_ctrl.read_attributes(
                    [f'b{band}pol{POLS[POL_H]}Attenuation',
                     f'b{band}pol{POLS[POL_V]}Attenuation']
                )
                return (atts[POL_H].value, atts[POL_V].value)
            except Exception as e:
                print(e)
        return (0.0, 0.0)

    def getConfiguredBand(self) -> int:
        try:
            value = self._ds_ctrl.read_attribute("configuredBand").value
            return int(value)
        except Exception as e:
            print(e)
            return 0

    def configureBand(self, band: int, synchronize: bool) -> bool:

        self._currentBand = self.getConfiguredBand()
        try:
            self.setStandbyMode()

            print(f"Configuring band {band}")
            configure_band_name = f"ConfigureBand{band}"
            self._ds_ctrl.command_inout(configure_band_name, synchronize)
            time.sleep(10)
            operating_mode = self._ds_ctrl.read_attribute(
                "operatingMode"
                ).value

            if (operating_mode != 4):
                tango.Except.throw_exception(
                    "OPERATING_MODE_INCORRECT",
                    "Expected operating mode to be DATA_CAPTURE\n" +
                    f"Query returned (enum): {operating_mode}",
                    f"configureBand({band},{synchronize}")

            self._currentBand = int(
                self._ds_ctrl.read_attribute("configuredBand").value
                )

            if (band != self._currentBand):
                print(f"  Unable to configure band {band}")
                return False

            print(f"  Successfully configured band {band}")
            a = self.getConfiguredAtten(band)
            print(f"  Configured attenuation : H:{a[POL_H]} V:{a[POL_V]}")
            return True

        except tango.DevFailed:
            tango.Except.throw_exception(
                "UNABLE_TO_CONFIGURE_BAND",
                f"Unable to configure band {band}",
                f"configureBand({band},{synchronize}")

    def setStandbyMode(self) -> None:
        print("Setting Standby Mode")
        self._ds_ctrl.command_inout("SetStandbyMode")
        time.sleep(3)

    def configureAtten(self, band: int, pol: int, atten: float) -> bool:

        print(f"Setting band {band} pol {POLS[pol]} attenuator value: {atten}")
        try:
            attr = f"b{band}Pol{POLS[pol]}Attenuation"
            self._ds_ctrl.write_attribute(attr, atten)

            checkval = self._ds_ctrl.read_attribute(attr).value
            if (abs(atten-float(checkval)) < 0.1):
                print(f"  Successfully configured band {band} "
                      f"pol {POLS[pol]} atten : {float(checkval)}")
                return True
            else:
                print(f"  Unable to configure Band {band} "
                      f"pol {POLS[pol]} attenuator.")

        except tango.DevFailed:
            tango.Except.throw_exception(
                "UNABLE_TO_CONFIGURE_ATTENUATOR",
                f"configAtten({band},{POLS[pol]},{atten}")

        return False

    def invertSpectralSense(self, sense=True):
        attr = "spec_inv"
        try:
            bandproc0 = DeviceProxy(self._deviceList['bp12'])
            bandproc1 = DeviceProxy(self._deviceList['bp3'])
        except tango.DevFailed:
            tango.Except.throw_exception(
                "UNABLE TO CONNECT TO BAND PROCESSOR(S)",
                f"invertSpectralSense({sense})"
            )
        try:
            bandproc0.write_attribute(attr, int(sense))
        except tango.DevFailed:
            tango.Except.throw_exception(
                f"UNABLE TO WRITE TO {attr} on bandprocessor123-0",
                f"invertSpectralSense({sense})"
            )
        try:
            bandproc1.write_attribute(attr, int(not sense))
        except tango.DevFailed:
            tango.Except.throw_exception(
                f"UNABLE TO WRITE TO {attr} on bandprocessor123-1",
                f"invertSpectralSense({sense})"
            )

    def parseInputArguments(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser()

        spfrx_action = parser.add_mutually_exclusive_group()
        spfrx_action.add_argument(
            '-b', '--band', type=int, metavar='BAND_ID',
            help="Activate switch to the specified band"
            )
        spfrx_action.add_argument(
            '-a', '--atten', type=str, nargs=3,
            metavar=("BAND", "POLH_ATTEN", "POLV_ATTEN"),
            help="Configure both HORIZONTAL POL and VERTICAL POL attenuator " +
                 "values for a specific band.\n" +
                 "Band is an integer from 1-3\n" +
                 "Provide H & V pol attenuation values as float values " +
                 "between 0 and 31.75"
            )
        spfrx_action.add_argument(
            '-av', '--attenv', type=str, nargs=2,
            metavar=("BAND", "POLV_ATTEN"),
            help="Configure the VERTICAL POL attenuator value for a " +
                 "specific band.\n" +
                 "Band is an integer from 1-3\n" +
                 "Provide V pol attenuation value as a float " +
                 "between 0 and 31.75"
            )
        spfrx_action.add_argument(
            '-ah', '--attenh', type=str, nargs=2,
            metavar=("BAND", "POLH_ATTEN"),
            help="Configure the HORIZONTAL POL attenuator value for a " +
                 "specific band.\n" +
                 "Band is an integer from 1-3\n" +
                 "Provide H pol attenuation value as a float " +
                 "between 0 and 31.75"
            )
        spfrx_action.add_argument(
            '-v', '--verify_band', action='store_true',
            help="Verify currently configured band."
            )
        spfrx_action.add_argument(
            '-va', '--verify_atten', type=int, metavar="BAND",
            help="Verify attenuator settings for the specified band."
            )

        return parser


def main() -> None:
    spfrx = Spfrx()


if __name__ == '__main__':
    main()

