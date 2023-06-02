"""
dbPopulate
A python module intended to allow a TANGO developer to create, modify and
destroy instances of Devices and Device Servers within a TANGO Database for
prototyping and testing purposes.

Created on Oct. 30, 2019
Modified Sept 29, 2020

@author: delrizzo
"""

import os
import re

from tango import Database, DbDevInfo
from time import sleep

DEFAULT_SLEEP_TIME : float = 0.01

class DbPopulate:
    # id is the unique ID for a given Talon-DX board. This string becomes
    # a component of the unique TANGO identifier for all devices added to
    # the database.
    id = ""

    # dbHost is a string containing the IP address of the TANGO DB to use
    dbHost = ""

    # db is a TANGO Database instance
    db = None

    json = None

    sleep_time : float

    ##
    # Initialize the class module
    def __init__(self, json, sleep_time : float = DEFAULT_SLEEP_TIME):
        # Store the input JSON file as a dict
        self.json = json

        self.sleep_time = sleep_time

        # determine whether we have a default TANGO DB specified in the
        # environment variables. If not specified, exit.
        self.dbHost = os.environ["TANGO_HOST"]
        if not len(self.dbHost) > 0:
            self.printStatus(
                "__init__", "TANGO_HOST environment variable not set."
            )
            exit(0)
        self.printStatus("__init__", f"Detected TANGO_HOST {self.dbHost}")

        # Establish connection to TANGO DB
        self.dbConnect()

    def printStatus(self, funcName, msg):
        """
        Print a formatted status message to the terminal
        """
        print(f"{__class__.__name__} [{funcName:^18s}] : {msg}")

    def dbConnect(self):
        """
        Establishes a connection to the TANGO DB specified by the TANGO_HOST
        environment variable on the host machine.
        """
        if self.dbHost != "":
            self.printStatus(
                "dbConnect",
                f"Establishing connection to TANGO DB {self.dbHost}",
            )
            self.db = Database()
            self.server_list = self.db.get_server_list()
        else:
            self.printStatus("dbConnect", "Unable to detect TANGO DB. Exiting")
            exit(0)

    def printServerList(self):
        if not self.server_list:
            self.printStatus("printServerList", "Server list is empty.")
        else:
            self.printStatus(
                "printServerList", f"Server list for {self.dbHost}:"
            )
            for s in self.server_list:
                print(f"   SERVER: {s}")
                #         instance_list = self.db.get_device_class_list(s)
                instance_list = [
                    dev
                    for dev in self.db.get_device_class_list(s)
                    if "/" in dev and not dev.startswith("dserver")
                ]
                for i in instance_list:
                    print(f"       - {i}")

    def extract(self):
        server_name_list = self.db.get_server_name_list().value_string
        for server_name in server_name_list:
            print(f"Server name: {server_name}")
        # print(server_name_list)
        if not self.server_list:
            self.printStatus("printServerList", "Server list is empty.")
        else:
            self.printStatus(
                "printServerList", f"Server list for {self.dbHost}:"
            )
            # for s in self.server_list:
            # print( f'   SERVER: {s}' )

    #                instance_list = self.db.get_device_class_list( s )
    # instance_list = [dev for dev in self.db.get_device_class_list(s) if '/'
    # in dev and not dev.startswith('dserver')]
    # for i in instance_list:
    # print( f'       - {i}' )

    def deviceName(self, family):
        """
        Returns the composed instance name for a device
        The device name is the unique tango identifier for a database instance
        of a device server.
        The format is device/name/family

        For the purposes of dbpopulate, device and name come frmo the
        input json.
        Family is provided by the calling method.
        """
        return f'{self.json["device"]}/{self.json["name"]}/{family}'

    def addDevice(self, device):
        """
        Adds the device instance(s) specified by the JSON 'devices' element
        """
        className = device["class"]

        alias = device["alias"]

        if device.get("id", None) is not None:
            name = self.deviceName(f'{alias}-{device["id"]}')
        else:
            name = self.deviceName(alias)
        device_info = DbDevInfo()
        device_info.name = name
        device_info._class = className
        device_info.server = (
            f'{self.json["server"]}/{self.json["instance"]}'
        )
        try:
            self.printStatus(
                "addDevice",
                f"  Installing device {name} under {className}",
            )
            self.db.add_device(device_info)
            sleep(self.sleep_time)
        except Exception as e:
            self.printStatus(
                "addDevice",
                f" *** Unable to create device {name}\n{e}",
            )
        if "devprop" in device.keys():
            try:
                for property in device["devprop"]:
                    self.printStatus(
                        "addDevice",
                        f"    Adding device property {property}:"
                        f'{device["devprop"][property]}',
                    )
                    self.db.put_device_property(
                        name, {property: device["devprop"][property]}
                    )
                    sleep(self.sleep_time)
            except Exception as e:
                self.printStatus(
                    "addDevice",
                    f" *** Unable to set device properties for "
                    f"{name}\n{e}",
                )

    def removeDevice(self, device):
        """
        Deletes the device specified by name from the DB
        """
        className = device["class"]


        alias = device["alias"]
        
        if device.get("id", None) is not None:
            name = self.deviceName(f'{alias}-{device["id"]}')
        else:
            name = self.deviceName(alias)
        if self.checkForDevice(className, name):
            self.printStatus("removeDevice", f" Removing device {name}")
            self.db.delete_device(name)
            sleep(self.sleep_time)
        else:
            self.printStatus(
                "removeDevice", f" Device {name} not found in DB"
            )

    def checkForDevice(self, className, device):
        """
        Checks the DB for an instance of device with the supplied name,
        registered as a member of the specified TANGO device class
        """
        dbList = self.db.get_device_name("*", className)
        return True if (device in dbList) else False

    def process(self, mode="add"):
        """
        Process a JSON configuration input file. This file should contain
        information regarding the TANGO device classes and instances that
        are to be created. This includes definintion of any attribute and/or
        device properties.
        """
        self.printStatus("process", f"Called in {mode.upper()} mode.")

        for device in self.json["deviceList"]:
            self.printStatus("process", f'Processing {device["class"]}')

            if mode == "add":
                self.addDevice(device)

            if mode == "remove":
                self.removeDevice(device)
