#!/usr/bin/env python3

import argparse
import getpass
import logging

import matplotlib
import matplotlib.animation as anim
import matplotlib.pyplot as plt
import numpy as np

from pytango_client_wrapper import PyTangoClientWrapper

# matplotlib.use("TkAgg")

LOG_FORMAT = (
    "[spfrx-spectrum-plotter.py: line %(lineno)s]%(levelname)s: %(message)s"
)
VERSION = "0.0.1"

SPFRX_DEVICE = "psi-spfrx"
SPFRX_NAME = "rxpu"
SPFRX_CTRL_ALIAS = "controller"
SPFRX_PKTCAP_ALIAS = "pktcap"

DEFAULT_THROTTLE_INTERVAL = 100
DEFAULT_NUM_PACKETS = 50
DEFAULT_UPDATE_INTERVAL = 1000


class SpectrumPlotter:

    _test_mode: bool
    _raw = []

    _ax1 = None
    _ax2 = None
    _ax3 = None
    _ax4 = None
    _textbox = None

    _data_xx = []
    _data_yy = []
    _data_xy_re = []
    _data_xy_im = []

    _device = SPFRX_DEVICE
    _name = SPFRX_NAME
    _ctrl = SPFRX_CTRL_ALIAS
    _pktcap = SPFRX_PKTCAP_ALIAS

    _throttle_interval: int
    _n_packets: int
    _update_interval: int
    _mag: bool

    def __init__(self,
                 throttle_interval: int,
                 n_packets: int,
                 update_interval: int,
                 mag: bool,
                 device: str = SPFRX_DEVICE,
                 name: str = SPFRX_NAME,
                 ctrl: str = SPFRX_CTRL_ALIAS,
                 pktcap: str = SPFRX_PKTCAP_ALIAS,
                 test_mode: bool = False) -> None:
        """
        Initialize the plot object

        :param trottle_interval: The throttle interval for the Gated
                                 Spectrometer expressed in ms.
        :param n_packets: The number of packets to capture in each interval.
        :param update_interval: The interval in ms in which to read the
                                spectrum and reset the Gated Spectrometer
        :param mag: A boolean to indicate display of cross product magnitude
                    is requested rather than read/imaginary
        :param device: (Optional) Override the device part of FQDN
        :param name: (Optional) Override the name part of FQDN
        :param ctrl: (Optional) Override the alias part of controller device
        :param pktcap: (Optional) Override the alias part of pktcap device
        :param test_mode: (Optional) Run in test mode if True.
                          Default is False.
        """

        self._device = device
        self._name = name
        self._ctrl = ctrl
        self._pktcap = pktcap

        self._throttle_interval = throttle_interval
        self._n_packets = n_packets
        self._update_interval = update_interval
        self._mag = mag

        self._test_mode = test_mode

        logger_.info(
            "SPFRx Gated Spectrometer Plotter parameters:\n"
            f"  SPFRx controller device: {self.getFqdn(self._ctrl)}\n"
            f"  SPFRx packet cap device: {self.getFqdn(self._pktcap)}\n"
            f"  Throttle Interval: {self._throttle_interval} ms\n"
            f"  Number of Packets: {self._n_packets} packets\n"
            f"  Update interval: {self._update_interval} ms\n"
            f"  Plot type: {'Magnitudes' if self._mag else 'Real/Imaginary'}\n"
            f"  Test mode: {'ENGAGED' if self._test_mode else 'NOT ACTIVE'}"
            )

        self.plotInit()

    def getFqdn(self, alias: str) -> str:
        """
        Construct the TANGO FQDN from supplied string values in the
        following form:

        device/name/alias

        :param alias: Alias string
        :param device: Device string, defaults to SPFRX_DEVICE
        :param name: Name string, defaults to SPFRX_NAME
        :returns: A TANGO FQDN string
        """
        return f"{self._device}/{self._name}/{alias}"

    def plotInit(self):
        """
        Initialize the plot object
        """

        logger_.info("Initializing the Gated Spectrometer Plotter")
        spfrx_pktcap = PyTangoClientWrapper()
        spfrx_pktcap.create_tango_client(self.getFqdn(self._pktcap))
        spfrx_pktcap.set_timeout_millis(5000)

        if not self._test_mode:
            spfrx_pktcap.write_attribute(
                "spectrometer_throttle_interval",
                self._throttle_interval
            )
            spfrx_pktcap.write_attribute(
                "spectrometer_num_packets",
                self._n_packets
            )

        fig = self.createPlot()

        anim.FuncAnimation(fig, self.update, frames=1, repeat=True)
        plt.show()

    def createPlot(self) -> plt.Figure:
        """
        Create the matplotlib Figure object
        """

        fig = plt.figure(figsize=(16, 6))
        self._ax1 = fig.add_subplot(141)

        self._textbox = self._ax1.text(
            0.05, 0.95, "", transform=plt.gcf().transFigure
        )
        self._ax2 = fig.add_subplot(142, sharey=self._ax1)
        self._ax3 = fig.add_subplot(143)
        self._ax4 = fig.add_subplot(144)

        return fig

    def update(self) -> None:
        """
        Update the data within the plot.
        """

        spfrx_ctrl = PyTangoClientWrapper()
        spfrx_ctrl.create_tango_client(self.getFqdn(self._ctrl))
        spfrx_ctrl.set_timeout_millis(5000)

        spfrx_pktcap = PyTangoClientWrapper()
        spfrx_pktcap.create_tango_client(self.getFqdn(self._pktcap))
        spfrx_pktcap.set_timeout_millis(5000)

        attH = ""
        attV = ""

        if self._test_mode:
            self._raw = range(8202)
        else:
            spfrx_pktcap.command_read_write(
                "spectrometer_retrieve_result",
                None
            )
            self._raw = spfrx_pktcap.read_attribute(
                "spectrometer_spectrum_result"
            )
            attH = spfrx_ctrl.read_attribute(
                "attenuationPolH"
            )
            attV = spfrx_ctrl.read_attribute(
                "attenuationPolV"
            )
            if attH is None:
                attH = -1
            if attV is None:
                attV = -1

        timestamp = self.parseData()
        self.updatePlot(timestamp, attH, attV)

        if timestamp % 10 == 0:
            spfrx_ctrl.command_read_write("MonitorPing")
        plt.pause(self._update_interval / 1000)

    def parseData(self) -> int:
        """
        Parse the raw spectrometer data.

        :returns: An integer timestamp
        """
        timestamp = self._raw[0]  # | (raw_data[1] << 16)

        self._data_xx = np.array([self._raw[2:1027], self._raw[4102:5127]])
        self._data_xx = np.where(self._data_xx != 0, self._data_xx, 1)
        self._data_xx = 10 * np.log10(self._data_xx)

        self._data_yy = np.array([self._raw[1027:2052], self._raw[5127:6152]])
        self._data_yy = np.where(self._data_yy != 0, self._data_yy, 1)
        self._data_yy = 10 * np.log10(self._data_yy)

        self._data_xy_re = np.array(
            [self._raw[2052:3077], self._raw[6152:7177]]
        )
        self._data_xy_re = np.where(self._data_xy_re != 0, self._data_xy_re, 1)

        self._data_xy_im = np.array(
            [self._raw[3077:4102], self._raw[7177:8202]]
        )
        self._data_xy_im = np.where(self._data_xy_im != 0, self._data_xy_im, 1)

        return timestamp

    def updatePlot(self,
                   timestamp: int,
                   attH: float = -1,
                   attV: float = -1) -> None:
        """
        Update the plot figure object.
        """

        spfrx_ctrl = PyTangoClientWrapper()
        spfrx_ctrl.create_tango_client(self.getFqdn(self._ctrl))
        spfrx_ctrl.set_timeout_millis(5000)

        mag = self._mag

        kvalue = spfrx_ctrl.read_attribute("kValue")
        band = spfrx_ctrl.read_attribute("configuredBand")

        if band == 3:
            range_low = (3.168e9 + (kvalue * 1440)) / 2 / 1e6
            range_high = (3.168e9 + (kvalue * 1440)) / 1e6
        else:
            range_low = 0
            range_high = (3.96e9 + (1 / 1800)) / 2 / 1e6

        self._ax1.cla()
        self._ax1.plot(self._data_xx[1], "r", self._data_xx[0], "b")
        self._ax1.legend(["ND Off", "ND On"])
        self._ax1.set_xlabel("Frequency (MHz)")
        self._ax1.set_ylabel("Power (dB, uncal)")
        self._ax1.set_title("Vertical Polarization")
        self._ax1.set_ylim(20, 95)
        self._ax1.set_xlim(1, 1024)
        self._ax1.grid()

        plt.setp(
            self._ax1,
            xticks=(np.linspace(0, 1025, 7)),
            xticklabels=(
                np.linspace(range_low, int(range_high), 7, dtype=int)
            ),
        )
        if attH >= 0:
            self._ax1.annotate(
                f"Atten: {attH} dB", xy=(0.15, 0.8), xycoords="figure fraction"
            )

        self._textbox = self._ax1.text(
            0.05, 0.95, "", transform=plt.gcf().transFigure
        )
        anno_str = f"BAND {band}  kValue {kvalue}  time {str(timestamp)}"
        self._textbox.set_text(anno_str)

        self._ax2.cla()
        self._ax2.plot(self._data_yy[1], "r", self._data_yy[0], "b")
        self._ax2.legend(["ND Off", "ND On"])
        self._ax2.set_xlabel("Frequency (MHz)")
        self._ax2.set_ylabel("Power (dB, uncal)")
        self._ax2.set_title("Horizontal Polarization")
        self._ax2.set_ylim(20, 95)
        self._ax2.set_xlim(1, 1024)
        self._ax2.grid()

        plt.setp(
            self._ax2,
            xticks=(np.linspace(0, 1025, 7)),
            xticklabels=(np.linspace(range_low, range_high, 7, dtype=int)),
        )
        if attV >= 0:
            self._ax2.annotate(
                f"Atten: {attV} dB", xy=(0.35, 0.8), xycoords="figure fraction"
            )

        if mag:
            # calculate power values
            data_xy_mag_ndoff = 5.0 * np.log(
                np.sqrt(
                    np.square(self._data_xy_re[1])
                    + np.square(self._data_xy_im[1])
                )
            )
            data_xy_mag_ndon = 5.0 * np.log(
                np.sqrt(
                    np.square(self._data_xy_re[0])
                    + np.square(self._data_xy_im[0])
                )
            )

        self._ax3.cla()
        if mag:
            self._ax3.plot(data_xy_mag_ndoff, "r", data_xy_mag_ndon, "b")
            self._ax3.set_ylabel("Magnitude (dB)")
            self._ax3.set_ylim(0, 95)
            self._ax3.set_title("Magnitude")
        else:
            self._ax3.plot(self._data_xy_re[1], "r", self._data_xy_re[0], "b")
            # , data_xy_re[1], 'g', data_xy_im[1], 'y')
            self._ax3.set_ylabel("Power")
            self._ax3.set_ylim(-30000, 30000)
            self._ax3.set_title("Cross Power (Real)")

        self._ax3.legend(["ND Off", "ND On"])  # , 'XY* Re', 'XY* Im'])
        self._ax3.set_xlabel("Frequency (MHz)")
        self._ax3.yaxis.set_label_coords(-0.1, 0.5)
        self._ax3.set_xlim(1, 1024)
        self._ax3.grid()

        plt.setp(
            self._ax3,
            xticks=(np.linspace(0, 1025, 7)),
            xticklabels=(np.linspace(range_low, range_high, 7, dtype=int)),
        )

        if mag:
            # calculate phase values
            data_xy_phase_ndoff = np.rad2deg(
                np.arctan2(self._data_xy_im[1], self._data_xy_re[1])
            )
            data_xy_phase_ndon = np.rad2deg(
                np.arctan2(self._data_xy_im[0], self._data_xy_re[0])
            )

        self._ax4.cla()
        if mag:
            self._ax4.scatter(
                range(1025),
                data_xy_phase_ndoff,
                c="r",
                marker=".",
                linewidths=0.5,
            )
            self._ax4.scatter(
                range(1025),
                data_xy_phase_ndon,
                c="b",
                marker=".",
                linewidths=0.5,
            )
            self._ax4.set_ylabel("Phase")
            self._ax4.set_ylim(-240, 240)
            self._ax4.set_title("Phase")
        else:
            self._ax4.plot(
                self._data_xy_im[1], "r", self._data_xy_im[0], "b"
            )  # , data_xy_re[1], 'g', data_xy_im[1], 'y')
            self._ax4.set_ylabel("Power")
            self._ax4.set_ylim(-30000, 30000)
            self._ax4.set_title("Cross Power (Imaginary)")
        self._ax4.legend(["ND Off", "ND On"])  # , 'XY* Re', 'XY* Im'])
        self._ax4.set_xlabel("Frequency (MHz)")
        self._ax4.yaxis.set_label_coords(-0.1, 0.5)
        self._ax4.set_xlim(1, 1024)
        self._ax4.grid()

        plt.setp(
            self._ax4,
            xticks=(np.linspace(0, 1025, 7)),
            xticklabels=(np.linspace(range_low, range_high, 7, dtype=int)),
        )
        if mag:
            piover2 = np.rad2deg([np.pi / 2, np.pi / 2])
            self._ax4.plot([0, 1025], piover2, color="black", linestyle="--")
            self._ax4.plot([0, 1025], [0, 0], color="black", linestyle="--")
            self._ax4.plot(
                [0, 1025], -1.0 * piover2, color="black", linestyle="--"
            )
        plt.show()


if __name__ == "__main__":
    logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
    logger_ = logging.getLogger("spfrx-talondx.py")
    logger_.info(f"User: {getpass.getuser()}")

    parser = argparse.ArgumentParser()
    #
    parser.add_argument(
        "-t",
        "--throttle_interval",
        type=int,
        metavar="THROTTLE_INTERVAL",
        default=DEFAULT_THROTTLE_INTERVAL,
        help="Provide the throttle interval in milliseconds for the "
        + f"Gated Spectrometer (Default is {DEFAULT_THROTTLE_INTERVAL} ms)",
    )
    parser.add_argument(
        "-p",
        "--packets",
        type=int,
        metavar="N_PACKETS",
        default=DEFAULT_NUM_PACKETS,
        help="Provide the number of packets to capture every "
        + f"throttle interval (Default is {DEFAULT_NUM_PACKETS} packets)",
    )
    # Optional Arguments
    parser.add_argument(
        "-d",
        "--device",
        type=str,
        metavar="DEVICE",
        default=SPFRX_DEVICE,
        help=f"Override the default FQDN device (Default is '{SPFRX_DEVICE}')"
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        metavar="NAME",
        default=SPFRX_NAME,
        help=f"Override the default FQDN name (Default is '{SPFRX_NAME}')"
    )
    parser.add_argument(
        "-ctrl",
        "--controller_name",
        type=str,
        metavar="ALIAS",
        default=SPFRX_CTRL_ALIAS,
        help="Override the default FQDN alias for the controller device. "
             f"(Default is '{SPFRX_CTRL_ALIAS}')",
    )
    parser.add_argument(
        "-pktcap",
        "--packet_capture_name",
        type=str,
        metavar="ALIAS",
        default=SPFRX_PKTCAP_ALIAS,
        help="Override the default FQDN alias for the packet capture device. "
             f"(Default is '{SPFRX_PKTCAP_ALIAS}')",
    )
    parser.add_argument(
        "-u",
        "--update_interval",
        type=int,
        metavar="UPDATE_INTERVAL",
        default=DEFAULT_UPDATE_INTERVAL,
        help="Provide the interval in milliseconds to read the spectrum "
             "result attribute and reset the Gated Spectrometer "
             f"(Default is {DEFAULT_UPDATE_INTERVAL} ms)"
    )
    parser.add_argument(
        "-tm",
        "--test_mode",
        action="store_true",
        help="Run the spectrometer gui in 'test' mode",
    )
    parser.add_argument(
        "-m",
        "--mag",
        action="store_true",
        help="Use this argument to display cross products as magnitude "
        + "& phase (Default is to display cross power as real/imaginary)",
    )
    parser.add_argument(
        "-v",
        "--plotter_version",
        action="store_true",
        help="Print the plotter version",
    )
    args = parser.parse_args()

    if args.plotter_version:
        logger_.info(f"spfrx-spectrum-plotter VERSION:{VERSION}")
        exit(0)

    print(args)

    sp = SpectrumPlotter(
        args.throttle_interval,
        args.packets,
        args.update_interval,
        args.mag,
        args.device,
        args.name,
        args.controller_name,
        args.packet_capture_name,
        args.test_mode
    )
