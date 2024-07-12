#!/usr/bin/env python3

### make_connection_extended_with_argv.py
#   Copyright 2021-2024 Nokia
###

# pylint: disable=import-error, import-outside-toplevel, line-too-long, too-many-branches, too-many-locals, too-many-statements

"""
Tested on: SR OS 22.2.R1

Example to show how to make a connection and handle exceptions with an
optional argument.

Execution on SR OS
    usage: pyexec make_connection_extended_with_argv.py [<parameter>]
Execution on remote machine
    usage: python make_connection_extended_with_argv.py username@host [<parameter>]
Execution on remote machine if show_system_summary.py is executable
    usage: ./make_connection_extended_with_argv.py username@host [<parameter>]
"""

# Import sys for parsing arguments and returning specific exit codes
import sys

# Import the connect and sros methods from the management pySROS submodule
from pysros.management import connect, sros


def usage():
    """Print the usage"""
    if sros():
        print("Usage:", sys.argv[0], "[<parameter>]")
    else:
        print("Usage:", sys.argv[0], "username@host [<parameter>]")


def get_remote_connection(my_username, my_host, my_password):
    """Function definition to obtain a Connection object to a remote SR OS device
    and access model-driven information"""

    # Import the exceptions so they can be caught on error
    # fmt: off
    from pysros.exceptions import ModelProcessingError

    # fmt: on
    # The try statement and except statements allow an operation
    # attempt with specific error conditions handled gracefully
    try:
        remote_connection_object = connect(
            username=my_username, host=my_host, password=my_password
        )
        return remote_connection_object

    # This first exception is described in the pysros.management.connect
    # method and references errors that occur during the creation of the
    # Connection object.  If the provided exception is raised during
    # the execution of the connect method, the information provided in
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
    # method, the information provided in that exception is loaded into
    # the model_proc_error variable for use.
    except ModelProcessingError as model_proc_error:
        print("Failed to compile YANG modules.")
        print("Error:", model_proc_error, end="")
        print(".")
        sys.exit(101)

    return remote_connection_object


def get_connection_with_argv():
    """Parse arguments and get a connection"""

    # The parameter in this example is optional, so we need a default value
    parameter = ""

    # Use the sros() function to determine if the application is executed
    # locally on an SR OS device, or remotely so that the same application
    # can be developed to run locally or remotely.

    # The application is running locally
    if sros():
        # Parse the arguments for an optional argument parameter
        if len(sys.argv) > 2:
            usage()
            sys.exit(2)

        # Set the argument value
        if len(sys.argv) == 2:
            # This quick example doesn't check if the parameter contains a valid value
            parameter = sys.argv[1]

        # Get a local Connection object
        connection_object = connect()  # pylint: disable=missing-kwoa

    # The application is running remotely
    else:
        # Import getpass to read the password
        import getpass

        # Parse the arguments for username, host and optional argument parameters
        if len(sys.argv) > 3 or len(sys.argv) < 2:
            usage()
            sys.exit(2)

        # Set the argument value
        if len(sys.argv) == 3:
            # This quick example doesn't check if the parameter contains a valid value
            parameter = sys.argv[2]

        # Split the username and host arguments, the host can be an IP
        # address or a hostname
        username_host = sys.argv[1].split("@")
        if len(username_host) != 2:
            usage()
            sys.exit(2)

        # Get the password
        password = getpass.getpass(
            prompt="Password (press Enter to use SSH key): "
        )

        # Get a remote Connection object
        connection_object = get_remote_connection(
            my_username=username_host[0],
            my_host=username_host[1],
            my_password=password,
        )

    if parameter:
        print(
            'Connection established successfully with optional argument value "'
            + parameter
            + '"!'
        )
    else:
        print(
            "Connection established successfully with no optional argument value!"
        )
    return connection_object


if __name__ == "__main__":
    my_connection_object = get_connection_with_argv()
