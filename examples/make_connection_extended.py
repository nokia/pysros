#!/usr/bin/env python3

### make_connection_extended.py
#   Copyright 2021 Nokia
###

# pylint: disable=import-error, import-outside-toplevel, line-too-long, too-many-branches, too-many-locals, too-many-statements

"""
Tested on: SR OS 22.2.R1

Example to show how to make a connection and handle exceptions.

Execution on SR OS
    usage: pyexec make_connection_extended.py
Execution on remote machine
    usage: python make_connection_extended.py username@host
Execution on remote machine if make_connection_extended.py is executable
    usage: ./make_connection_extended.py username@host
"""

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
        import sys

        # Import getpass to read the password
        import getpass

        # Import the exceptions so they can be caught on error
        # fmt: off
        from pysros.exceptions import ModelProcessingError
        # fmt: on

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
                username=username_host[0], host=username_host[1], password=password
            )
            return connection_object

        # This first exception is described in the pysros.management.connect
        # method and references errors that occur during the creation of the
        # Connection object.  If the provided exception is raised during
        # the execution of the connect method the information provided in
        # that exception is loaded into the runtime_error variable for use.
        except RuntimeError as runtime_error:
            print("Failed to connect during the creation of the Connection object.")
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


if __name__ == "__main__":
    my_connection_object = get_connection()
    print("Connection established successfully!")
