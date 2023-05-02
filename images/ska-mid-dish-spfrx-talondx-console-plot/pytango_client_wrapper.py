import sys
from typing import Any

from tango import DeviceProxy


class PyTangoClientWrapper:
    def __init__(self):
        self.dp = None
        self.timeout_ms = 3000  # Default Tango timeout

    def create_tango_client(self, dev_name: str):
        """
        Creates a device proxy to the specified device.

        :param dev_name: Device FQDN to connect to
        """
        try:
            self.dp = DeviceProxy(dev_name)
            print("Device State : {}".format(self.dp.state()))
            print("Device Status: {}".format(self.dp.status()))
            print("dev_name = {}".format(dev_name))

        except Exception as e:
            print("Error on DeviceProxy: {}".format(str(e)))
            self.clear_all()
            sys.exit(str(e))

    def clear_all(self):
        """
        Reset all class variables to the default setting.
        """
        self.timeout_ms = 3000
        if self.dp is not None:
            self.dp = None

    def set_timeout_millis(self, timeout_ms: int):
        """
        Set the timeout of the DeviceProxy connection.

        :param timeout_ms: Timeout in milliseconds
        """
        try:
            self.timeout_ms = timeout_ms
            self.dp.set_timeout_millis(timeout_ms)
        except Exception as e:
            print(str(e))

    def write_attribute(self, attr_name: str, value: Any):
        """
        Write to an attribute.

        :param attr_name: Attribute to write to
        :param value: Value to write
        """
        try:
            self.dp.write_attribute(attr_name, value)
        except Exception as e:
            print(str(e))

    def read_attribute(self, attr_name: str) -> Any:
        """
        Read from an attribute.

        :param attr_name: Attribute to read from
        :returns: Attribute value or None if an exception occurred
        """
        try:
            attr_read = self.dp.read_attribute(attr_name)
            return attr_read.value
        except Exception as e:
            print(str(e))
            return None

    def command_read_write(self, command_name: str, *args) -> Any:
        """
        Send a command.

        :param command_name: Name of the command
        :param args: Input arguments
        :returns: Command result or None is an exception occurred
        """
        try:
            return self.dp.command_inout(command_name, *args)
        except Exception as e:
            print(str(e))
            return None
