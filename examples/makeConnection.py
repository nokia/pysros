#!/usr/bin/env python3

### makeConnection.py
#   Copyright 2021 Nokia
#   Example to show how to make a connection and handle exceptions
###

# Import the connect method from the management pySROS sub-module
from pysros.management import connect
# Import the exceptions so they can be caught on error.
from pysros.exceptions import *
# Import sys for returning specific exit codes
import sys

# This function attempts to make a connection to an SR OS device
def get_connection(host=None, credentials=None):

    # The try statement coupled with the except statements allow an operation(s) to be
    # attempted and specific error conditions handled gracefully
    try:
        c = connect(host=host,
                    username=credentials['username'],
                    password=credentials['password'])

    # This first exception is described in the pysros.management.connect method
    # and references errors that occur during the creation of the Connection object.
    # If the provided exception is raised during the execution of the connect method
    # the information provided in that exception is loaded into the e1 variable for use
    except RuntimeError as e1:
        print("Failed to connect during the creation of the Connection object.  Error:", e1)
        sys.exit(-1)

    # This second exception is described in the pysros.management.connect method
    # and references errors that occur whilst compiling the YANG modules that have been
    # obtained into a model-driven schema.
    # If the provided exception is raised during the execution of the connect method the
    # information provided in that exception is loaded into the e2 variable for use.
    except ModelProcessingError as e2:
        print("Failed to create model-driven schema.  Error:", e2)
        sys.exit(-2)

    # This last exception is a general exception provided in Python
    # If any other unhandled specific exception is thrown the information provided in
    # that exception is loaded into the e3 variable for use
    except Exception as e3:
        print("Failed to connect.  Error:", e3)
        sys.exit(-3)

    # Confirm to the user that the connection establishment completed successfully
    print("Connection established successfully")

    # Return the Connection object that we created
    return c

# Example general/main function
def main():

    # Define some user credentials to pass to the get_connect function
    credentials = {
        "username": "admin",
        "password": "admin"
    }

    # Call the get_connection function providing a hostname/IP and the credentials
    # Returns a Connection object for use in obtaining data from the SR OS device
    # or configuring that device
    c = get_connection(host='192.168.168.70', credentials=credentials)

if __name__ == "__main__":
    main()
