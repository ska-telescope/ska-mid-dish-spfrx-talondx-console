#!/usr/bin/env python3
import argparse
import getpass
import logging
import spfrx
import tango
import time

from pytango_client_wrapper import PyTangoClientWrapper
from tango import DeviceProxy

SPFRX_DEVICE = "ska001"
SPFRX_NAME = "spfrxpu"

LOG_FORMAT = (
    "[spfrx_sat_pll.py: line %(lineno)s]%(levelname)s: %(message)s"
)
VERSION = "0.0.1"


def pll_read_register(
        reg: int
    ) -> int:
    return 0


def pll_write_register(
        reg: int,
        value: int
    ) -> int:
    return 0


def pll_get_status() -> None:
    pass


def pll_set_k(
    k: int = 0,
    ) -> bool:
    logger_.info(f"Set k-value to {k}.")
    pll_write_register()


def pll_setup(
        timeout: int = 3600
    ) -> bool:
    """
    Setup the SAT-PLL and wait for lock
    Return True if lock occurs within timeout.

    :param timeout: Timeout in seconds to wait for lock
    :return: True if successful, false otherwise
    """
    logger_.info(f"Seting up PLL and waiting {timeout} for lock")
    correct_k = False
    lock = False

    while int(pll_get_status(),16) == 0:
        logger_.info("Wait for PLL to wake, sleep 5s")
        time.sleep(5)
    
    # Set k value
    
    return True


if __name__ == "__main__":
    logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)
    logger_ = logging.getLogger("spfrx.py")
    logger_.info(f"User: {getpass.getuser()}")

    parser = argparse.ArgumentParser(description="MID DISH SPFRx SAT-PLL Console Ops.")
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        help="Print version information for this module.",
    )
    pll_action = parser.add_mutually_exclusive_group()
    pll_action.add_argument(
        "--pll_get_status",
        action="store_true",
        help="Print PLL Status register values.",
    )

    args = parser.parse_args()

    if args.version:
        logger_.info(
            f"VERSION: {VERSION}"
        )

    if args.pll_get_status(
        logger_.info(
            "Reading SPFRx PLL Status Registers"
            )
        pll_get_status()
    )

    else:
        logger_.info("Hello from Mid DISH SPFRx SAT-PLL Console")
