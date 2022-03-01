#!/usr/bin/env python3

### get_list_keys_usage.py
#   Copyright 2022 Nokia
###

"""
Tested on: SR OS 22.2.R1

This example demonstrates the use of the get_list_keys function introduced in
release 22.2.1 of pySROS.
"""

# Import the time module to provide performance timers
import time

# Import the connect and sros methods from the management pySROS submodule
from pysros.management import connect, sros


def get_connection():
    """Function definition to obtain a Connection object to a specific SR OS device
    and access model-driven information"""

    # Use the sros() function to determine if the application is executed
    # locally on an SR OS device, or remotely so that the same application
    # can be developed to run locally or remotely.  If the application is
    # executed locally, call connect() and return the Connection object.
    # If the application is executed remotely, the username and host is
    # required as arguments, and a prompt for the password is displayed
    # before calling connect().  Connection error handling is also checked.

    # If the application is executed locally
    if sros():
        connection_object = connect()  # pylint: disable=missing-kwoa

    # Else if the application is executed remotely
    else:
        # Import sys for returning specific exit codes
        import sys  # pylint: disable=import-outside-toplevel

        # Import getpass to read the password
        import getpass  # pylint: disable=import-outside-toplevel

        # Import the exceptions so they can be caught on error
        # pylint: disable=import-outside-toplevel
        from pysros.exceptions import (
            ModelProcessingError,
        )

        # Make sure we have the right number of arguments, the host can
        # be an IP address or a hostname
        if len(sys.argv) != 2:
            print("Usage:", sys.argv[0], "username@host")
            sys.exit(2)

        # Split the username and host arguments
        username_host = sys.argv[1].split("@")
        if len(username_host) != 2:
            print("Usage:", sys.argv[0], "username@host")
            sys.exit(2)

        # Get the password
        password = getpass.getpass()

        # The try statement coupled with the except statements allow an
        # operation(s) to be attempted and specific error conditions handled
        # gracefully
        try:
            connection_object = connect(
                username=username_host[0],
                host=username_host[1],
                password=password,
            )
            return connection_object

        # This first exception is described in the pysros.management.connect
        # method and references errors that occur during the creation of the
        # Connection object.  If the provided exception is raised during
        # the execution of the connect method the information provided in
        # that exception is loaded into the runtime_error variable for use.
        except RuntimeError as runtime_error:
            print(
                "Failed to connect during the creation of the Connection object."
            )
            print("Error:", runtime_error, end="")
            print(".")
            sys.exit(100)

        # This second exception is described in the pysros.management.connect
        # method and references errors that occur whilst compiling the YANG
        # modules that have been obtained into a model-driven schema.  If the
        # provided exception is raised during the execution of the connect
        # method the information provided in that exception is loaded into
        # the model_proc_error variable for use.
        except ModelProcessingError as model_proc_error:
            print("Failed to compile YANG modules.")
            print("Error:", model_proc_error, end="")
            print(".")
            sys.exit(101)

    return connection_object


def get_list_keys_example_without_defaults(connection_object, path):
    """Function to obtain the keys of a YANG list (excluding default entries) using the
    get_list_keys function.
    """
    return connection_object.running.get_list_keys(path)


def get_list_keys_example_with_defaults(connection_object, path):
    """Function to obtain the keys of a YANG list (including default entries) using the
    get_list_keys function.
    """
    return connection_object.running.get_list_keys(path, defaults=True)


def get_list_then_extract_keys_example_without_defaults(
    connection_object, path
):
    """Function to obtain the keys of a YANG list (excluding default entries) using the
    get function and then calling keys() against the resulting data structure.
    """
    return connection_object.running.get(path).keys()


def get_list_then_extract_keys_example_with_defaults(connection_object, path):
    """Function to obtain the keys of a YANG list (including default entries) using the
    get function and then calling keys() against the resulting data structure.
    """
    return connection_object.running.get(path, defaults=True).keys()


def compare_and_contrast():
    """Compare and contrast the different methods to obtain a list of key values
    from a YANG list.
    """
    # Obtain the Connection object for the device
    connection_object = get_connection()
    # The example path used in the example.  This is the path to a YANG list.
    path = "/nokia-conf:configure/router"

    # Use get to obtain the list then select the keys from the resulting dict without defaults
    starttime = time.perf_counter()
    output = get_list_then_extract_keys_example_without_defaults(
        connection_object, path
    )
    duration = round(time.perf_counter() - starttime, 4)
    print("get without defaults\n", "Output:", output, "Time:", duration)

    # Use get to obtain the list then select the keys from the resulting dict with defaults
    starttime = time.perf_counter()
    output = get_list_then_extract_keys_example_with_defaults(
        connection_object, path
    )
    duration = round(time.perf_counter() - starttime, 4)
    print("get with defaults\n", "Output:", output, "Time:", duration)

    # Use get_list_keys to obtain the list keys without defaults
    starttime = time.perf_counter()
    output = get_list_keys_example_without_defaults(connection_object, path)
    duration = round(time.perf_counter() - starttime, 4)
    print(
        "get_list_keys without defaults\n",
        "Output:",
        output,
        "Time:",
        duration,
    )

    # Use get_list_keys to obtain the list keys without defaults
    starttime = time.perf_counter()
    output = get_list_keys_example_with_defaults(connection_object, path)
    duration = round(time.perf_counter() - starttime, 4)
    print(
        "get_list_keys with defaults\n", "Output:", output, "Time:", duration
    )
    connection_object.disconnect()


if __name__ == "__main__":
    compare_and_contrast()
