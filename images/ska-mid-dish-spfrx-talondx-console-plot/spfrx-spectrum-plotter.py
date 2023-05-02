import argparse

import matplotlib
import matplotlib.animation as anim
import matplotlib.pyplot as plt
import numpy as np
import pytango_client_wrapper as pcw

# import os


matplotlib.use("TkAgg")


class SpectrumPlotter:

    _test_mode = False
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

    def __init__(self):
        self._args = self.parseInputArguments()

        self._test_mode = self._args.test_mode

        self.proxyInit()
        self.plotInit()

    def donothing(self):
        pass

    def proxyInit(self):
        self._pcap = self.clientSetUp(self._args.device_name)
        self._ctrl = self.clientSetUp(self._args.controller_name)

    def clientSetUp(self, device_name):

        # Create the tango client
        proxy = pcw.PyTangoClientWrapper()
        proxy.create_tango_client(device_name)

        return proxy

    def createPlot(self):

        fig = plt.figure(figsize=(16, 6))
        self._ax1 = fig.add_subplot(141)

        self._textbox = self._ax1.text(
            0.05, 0.95, "", transform=plt.gcf().transFigure
        )
        self._ax2 = fig.add_subplot(142, sharey=self._ax1)
        self._ax3 = fig.add_subplot(143)
        self._ax4 = fig.add_subplot(144)

        return fig

    def plotInit(self):

        if not self._test_mode:
            self._pcap.write_attribute(
                "spectrometer_throttle_interval", self._args.throttle_interval
            )
            self._pcap.write_attribute(
                "spectrometer_num_packets", self._args.packets
            )

        fig = self.createPlot()

        anim.FuncAnimation(fig, self.update, frames=1, repeat=True)
        plt.show()

    def update(self, i):

        attH = ""
        attV = ""

        if self._test_mode:
            self._raw = range(8202)
        else:
            self._pcap.command_read_write("spectrometer_retrieve_result", None)
            self._raw = self._pcap.read_attribute(
                "spectrometer_spectrum_result"
            )
            attH = self._ctrl.read_attribute("attenuationPolH")
            attV = self._ctrl.read_attribute("attenuationPolV")
            if attH is None:
                attH = -1
            if attV is None:
                attV = -1

        timestamp = self.parseData()
        self.updatePlot(timestamp, attH, attV)

        if timestamp % 10 == 0:
            self._ctrl.command_noargs("MonitorPing")
        plt.pause(self._args.update_interval / 1000)

    def parseData(self):

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

    def updatePlot(self, timestamp, attH=-1, attV=-1):

        mag = self._args.mag

        kvalue = self._ctrl.read_attribute("kValue")
        band = self._ctrl.read_attribute("configuredBand")

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

    def parseInputArguments(self):
        """
        parseInputArguments handles the processing of all command
        line input arguments.
        """
        # thispath = os.path.abspath(os.path.dirname(__file__))  # this file.
        parser = argparse.ArgumentParser()
        #
        # Optional Arguments
        parser.add_argument(
            "-d",
            "--device_name",
            type=str,
            required=True,
            help="Provide the TANGO device name of the ska-mid-spfrx-packet"
            + "-capture-ds device server.",
        )
        parser.add_argument(
            "-c",
            "--controller_name",
            type=str,
            required=True,
            help="Provide the TANGO device name of the ska-mid-spfrx-"
            + "controller-ds device server.",
        )
        parser.add_argument(
            "-t",
            "--throttle_interval",
            type=int,
            required=True,
            help="Provide the throttle interval in milliseconds for the "
            + "Gated Spectrometer.",
        )
        parser.add_argument(
            "-p",
            "--packets",
            type=int,
            required=True,
            help="Provide the number of packets to capture every "
            + "throttle interval.",
        )
        parser.add_argument(
            "-u",
            "--update_interval",
            type=int,
            default=1000,
            help="Provide the interval in milliseconds to read the spectrum "
            + "result attribute and reset the Gated Spectrometer.",
        )
        parser.add_argument(
            "-tm",
            "--test_mode",
            action="store_true",
            help="Run the spectrometer gui in 'test' mode",
        )
        parser.add_argument(
            "-b",
            "--band",
            type=int,
            default=1,
            help="Provide the band number to be plotted [1,2,3]",
        )
        parser.add_argument(
            "-m",
            "--mag",
            action="store_true",
            help="Use this argument to display cross products as magnitude "
            + "& phase. Default is to display cross power of real/imaginary",
        )

        return parser.parse_args()


def main():
    sp = SpectrumPlotter()
    sp.donothing()


if __name__ == "__main__":
    main()
