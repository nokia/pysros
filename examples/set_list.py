#!/usr/bin/env python3

### set_list.py
#   Copyright 2021-2024 Nokia
###

"""Simple example to explain the various YANG list configuration options"""

# Import the required libraries
import sys
from pysros.management import connect

# Import the exceptions so they can be caught on error.
from pysros.exceptions import ModelProcessingError


def get_connection(host=None, credentials=None):
    """Function definition to obtain a Connection object to a specific SR OS device
    and access the model-driven information."""

    # The try statement and except statements allow an operation
    # attempt with specific error conditions handled gracefully
    try:
        connection_object = connect(
            host=host,
            username=credentials["username"],
            password=credentials["password"],
        )

        # Confirm to the user that the connection establishment completed successfully
        print("Connection established successfully")

        # Return the Connection object that we created
        return connection_object

    # This first exception is described in the pysros.management.connect method
    # and references errors that occur during the creation of the Connection object.
    # If the provided exception is raised during the execution of the connect method
    # the information provided in that exception is loaded into the e1 variable for use
    except RuntimeError as error1:
        print(
            "Failed to connect during the creation of the Connection object.  Error:",
            error1,
        )
        sys.exit(101)

    # This second exception is described in the pysros.management.connect method
    # and references errors that occur whilst compiling the YANG modules that have been
    # obtained into a model-driven schema.
    # If the provided exception is raised during the execution of the connect method, the
    # information provided in that exception is loaded into the e2 variable for use.
    except ModelProcessingError as error2:
        print("Failed to create model-driven schema.  Error:", error2)
        sys.exit(102)

    # This last exception is a general exception provided in Python
    # If any other unhandled specific exception is thrown the information provided in
    # that exception is loaded into the e3 variable for use
    except Exception as error3:  # pylint: disable=broad-except
        print("Failed to connect.  Error:", error3)
        sys.exit(103)


def set_list_method_1(connection_object):
    """YANG list configuration - method 1 example"""
    # path is the json-instance-path to the YANG list
    path = "/nokia-conf:configure/log/log-id"
    # payload is a dict including the list key-values as the Python dict keys
    payload = {
        "10": {"description": "Log ten"},
        "11": {"description": "Log eleven"},
    }
    print("YANG list configuration - Method 1")
    print("  {: <15}: {: <}".format(*["Path", path]))
    print("  {: <15}: {: <}".format(*["Payload", str(payload)]))
    print(
        "  {: <15}: {: <}".format(
            *["API call", "c.candidate.set(path, payload)"]
        )
    )
    print("  c.candidate.set(path, payload)")
    # Configure the SR OS device
    connection_object.candidate.set(path, payload)


def set_list_method_2(connection_object):
    """YANG list configuration - method 2 example.
    Method 2 requires multiple set API calls."""
    # Provide the list entry data that will be iterated through
    list_entries = [("10", "Log ten"), ("11", "Log eleven")]
    print("\nYANG list configuration - Method 2")
    for item in list_entries:
        # payload is the fields to be set within the list item.
        # The key name and key-value are not provided.
        payload = {"description": item[1]}
        # path is the json-instance-path to the YANG lists specific item including list name,
        # list key name and the list key-value.
        path = "/nokia-conf:configure/log/log-id[name=" + item[0] + "]"
        print("  {: <15}: {: <}".format(*["Path", path]))
        print("  {: <15}: {: <}".format(*["Payload", str(payload)]))
        print(
            "  {: <15}: {: <}".format(
                *["API call", "c.candidate.set(path, payload)"]
            )
        )
        # Configure the SR OS device
        connection_object.candidate.set(path, payload)


def set_list_method_3(connection_object):
    """YANG list configuration - method 3 example.
    Method 3 requires multiple set API calls."""
    # Provide the list entry data that will be iterated through
    list_entries = [("10", "Log ten"), ("11", "Log eleven")]
    print("\nYANG list configuration - Method 3")
    for item in list_entries:
        # payload is the fields to be set within the list item.
        # The key name and key-value are provided even though they are
        # also to be referenced in the path.
        payload = {"name": item[0], "description": item[1]}
        # path is the json-instance-path to the YANG lists specific item
        # including list name, list key name and the list key-value.
        path = "/nokia-conf:configure/log/log-id[name=" + item[0] + "]"
        print("  {: <15}: {: <}".format(*["Path", path]))
        print("  {: <15}: {: <}".format(*["Payload", str(payload)]))
        print(
            "  {: <15}: {: <}".format(
                *["API call", "c.candidate.set(path, payload)"]
            )
        )
        # Configure the SR OS device
        connection_object.candidate.set(path, payload)


def main():
    """Main function to demonstrate various options to configure YANG lists"""
    connection_object = get_connection(
        host="192.168.1.1",
        credentials={"username": "myusername", "password": "mypassword"},
    )

    # Call the various configuration methods in turn
    set_list_method_1(connection_object)
    set_list_method_2(connection_object)
    set_list_method_3(connection_object)


# Run from here
if __name__ == "__main__":
    main()
