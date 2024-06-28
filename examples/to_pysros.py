#!/usr/bin/env python3

### to_pysros.py
#   Copyright 2023-2024 Nokia
###

"""
Tested on: SR OS 22.10.R3

Convert the output of info full-context json on a router into pySROS format
for cut-and-paste use in pySROS Python3 code.

Execution on SR OS
    Navigate to the location in the tree that you would like the data (configuration/state)
    usage: info full-context json | pyexec to_pysros.py
    This assumes this application is placed on the SR OS router in cf3:
Execution on remote machine
    Not supported.
"""

import builtins
import json

# Required imports
import sys

from pysros.exceptions import ModelProcessingError
from pysros.management import connect


def get_connection():
    """Function definition to obtain a Connection object on a local SR OS device"""

    # The try statement and except statements allow an operation
    # attempt with specific error conditions handled gracefully
    try:
        connection_object = connect(host=None, username=None)

    # This first exception is described in the pysros.management.connect
    # method and references errors that occur during the creation of the
    # Connection object.  If the provided exception is raised during
    # the execution of the connect method, the information provided in
    # that exception is loaded into the runtime_error variable for use.
    except builtins.RuntimeError as runtime_error:
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

    return connection_object


def main():
    """Main function reads from STDIN (redirected info full-context json SR OS command) and
    uses the pySROS convert method to return the pySROS data structure for the data.
    """
    # Read in from STDIN
    data = ""
    for line in sys.stdin:
        data = data + line

    # Ensure the data converts to valid JSON
    json_input = json.loads(data)

    # Obtain the pySROS connection object to the node
    connection_object = get_connection()

    # Output to the screen the pySROS data structure using the pySROS convert method
    print(
        connection_object.convert(
            "/",
            json.dumps(json_input),
            source_format="json",
            destination_format="pysros",
        )
    )


if __name__ == "__main__":
    main()
