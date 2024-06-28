#!/usr/bin/env python3

### make_connection.py
#   Copyright 2021-2024 Nokia
###

"""Example to show how to make a connection and handle exceptions"""

# Import sys for returning specific exit codes
import sys

# Import the exceptions that are referenced so they can be caught on error.
from pysros.exceptions import ModelProcessingError

# Import the connect method from the management pySROS sub-module
from pysros.management import connect


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


def main():
    """Example general/main function"""

    # Define some user credentials to pass to the get_connect function
    credentials = {"username": "myusername", "password": "mypassword"}

    # Call the get_connection function providing a hostname/IP and the credentials
    # Returns a Connection object for use in obtaining data from the SR OS device
    # or configuring that device
    connection_object = get_connection(  # pylint: disable=unused-variable
        host="192.168.1.1", credentials=credentials
    )
    assert connection_object


if __name__ == "__main__":
    main()
