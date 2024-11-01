#!/usr/bin/env python3

### convert_example.py
#   Copyright 2022-2024 Nokia
###

"""Example to demonstrate the convert function to manipulate data formats.

Tested on: SR OS 22.10.R1
"""

# Import sys library
import sys

# Import the exceptions that are referenced so they can be caught on error.
from pysros.exceptions import ModelProcessingError

# Import the connect method from the management pySROS sub-module
from pysros.management import connect


class Data:  # pylint: disable=too-few-public-methods
    """Create an object containing the input data in the required format
    and the path used in the convert method.

    :parameter input_format: The type of data to generate, either:
                             ``pysros``, ``xml`` or ``json``.
    :type input_format: str
    :returns: Object with ``path`` and ``payload`` parameters in the desire format.
    :rtype: :py:class:`Data`
    :raises Exception: Raises a general Exception if the ``input_format`` is invalid.
    """

    def __init__(self, input_format):
        self.path = "/nokia-conf:configure/system/management-interface"
        if input_format == "pysros":
            self.payload = self._gen_pysros()
        elif input_format == "xml":
            self.payload = self._gen_xml()
        elif input_format == "json":
            self.payload = self._gen_json()
        else:
            raise ValueError("Valid data formats are pysros, xml or json")

    def _gen_pysros(self):
        """Private method to generate simple pySROS formatted example data
        without namespaces.
        """
        return {
            "snmp": {"admin-state": "disable"},
            "netconf": {"admin-state": "enable", "auto-config-save": True},
            "yang-modules": {
                "nmda": {"nmda-support": True},
                "openconfig-modules": True,
            },
            "cli": {"md-cli": {"auto-config-save": True}},
            "configuration-mode": "model-driven",
        }

    def _gen_xml(self):
        """Private method to generate simple XML formatted example data
        without namespaces.
        """
        example_data = """
<cli>
    <md-cli>
        <auto-config-save>true</auto-config-save>
    </md-cli>
</cli>
<netconf>
    <admin-state>enable</admin-state>
    <auto-config-save>true</auto-config-save>
</netconf>
<yang-modules>
    <openconfig-modules>true</openconfig-modules>
    <nmda>
        <nmda-support>true</nmda-support>
    </nmda>
</yang-modules>
<snmp>
    <admin-state>disable</admin-state>
</snmp>
        """
        return example_data

    def _gen_json(self):
        """Private method to generate simple JSON IETF formatted example data
        without namespaces.
        """
        example_data = """
{
    "configuration-mode": "model-driven",
    "cli": {
        "md-cli": {
            "auto-config-save": true
        }
    },
    "netconf": {
        "admin-state": "enable",
        "auto-config-save": true
    },
    "yang-modules": {
        "openconfig-modules": true,
        "nmda": {
            "nmda-support": true
        }
    },
    "snmp": {
        "admin-state": "disable"
    }
}
        """
        return example_data

    def __str__(self):
        """Allow the object to be printed directly."""
        return "Path: " + self.path + "\n" + "Payload: " + self.payload


def get_connection(host=None, credentials=None, port=830):
    """Function definition to obtain a Connection object to a specific SR OS device
    and access the model-driven information.

    :parameter host: The hostname or IP address of the SR OS node.
    :type host: str
    :paramater credentials: The username and password to connect
                            to the SR OS node.
    :type credentials: dict
    :parameter port: The TCP port for the connection to the SR OS node.
    :type port: int
    :returns: Connection object for the SR OS node.
    :rtype: :py:class:`pysros.management.Connection`
    """

    # The try statement and except statements allow an operation
    # attempt with specific error conditions handled gracefully
    try:
        print("-" * 79)
        print("Obtaining connection to", host)
        connection_object = connect(
            host=host,
            username=credentials["username"],
            password=credentials["password"],
            port=port,
            hostkey_verify=False,
        )

        # Confirm to the user that the connection establishment completed successfully
        print("Connection established successfully")

        # Return the created Connection object
        return connection_object

    # This first exception is described in the pysros.management.connect method
    # and references errors that occur during the creation of the Connection object.
    # If the provided exception is raised during the execution of the connect method,
    # the information provided in that exception is loaded into the error1 variable for use
    except RuntimeError as error1:
        print(
            "Failed to connect during the creation of the Connection object.  Error:",
            error1,
        )
        sys.exit(101)

    # This second exception is described in the pysros.management.connect method
    # and references errors that occur when compiling the YANG modules that have been
    # obtained into a model-driven schema.
    # If the provided exception is raised during the execution of the connect method, the
    # information provided in that exception is loaded into the error2 variable for use.
    except ModelProcessingError as error2:
        print("Failed to create model-driven schema.  Error:", error2)
        sys.exit(102)

    # This last exception is a general exception provided in Python
    # If any other unhandled specific exception occurs, the information provided in
    # that exception is loaded into the error3 variable for use
    except Exception as error3:  # pylint: disable=broad-except
        print("Failed to connect.  Error:", error3)
        sys.exit(103)


def converting(input_format, output_format, data, connection_object):
    """Perform the conversion from a given format to another format.

    :parameter input_format: The type of data used on input, either:
                             ``pysros``, ``xml`` or ``json``.
    :type input_format: str
    :parameter output_format: The type of data used on output, either:
                              ``pysros``, ``xml`` or ``json``.
    :type input_format: str
    :parameter data: The example data object.
    :type data: :py:class:`Data`
    :parameter connection_object: The connection object for a specific node.
    :type connection_object: :py:class:`pysros.management.Connection`
    """
    print("-" * 79)
    print("Converting", input_format, "to", output_format, "\n")
    print("The path used as the YANG-modeled root for the data is:")
    print(data.path, "\n")
    print("The payload is:")
    print(data.payload, "\n")
    print("The converted result is:")
    print(
        connection_object.convert(
            path=data.path,
            payload=data.payload,
            source_format=input_format,
            destination_format=output_format,
            pretty_print=True,
        )
    )


def main():
    """The main procedure.  The execution starts here."""
    connection_object = get_connection(
        "192.168.1.1", {"username": "admin", "password": "admin"}
    )
    data = Data("pysros")
    converting("pysros", "pysros", data, connection_object)
    data = Data("pysros")
    converting("pysros", "xml", data, connection_object)
    data = Data("pysros")
    converting("pysros", "json", data, connection_object)
    data = Data("xml")
    converting("xml", "xml", data, connection_object)
    data = Data("xml")
    converting("xml", "pysros", data, connection_object)
    data = Data("xml")
    converting("xml", "json", data, connection_object)
    data = Data("json")
    converting("json", "json", data, connection_object)
    data = Data("json")
    converting("json", "pysros", data, connection_object)
    data = Data("json")
    converting("json", "xml", data, connection_object)


if __name__ == "__main__":
    main()
