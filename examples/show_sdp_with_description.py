#!/usr/bin/env python3

### show_sdp_with_description.py
#   Copyright 2021 Nokia
###

"""Example to show all SDPs with description"""

# Import the required libraries for the application.
import sys
from pysros.management import connect
from pysros.pprint import Table  # pylint: disable=no-name-in-module

# Import the exceptions so they can be caught on error.
from pysros.exceptions import ModelProcessingError

# Global credentials dictionary for the purposes of this example.  Global variables
# discouraged in operational applications.
credentials = {
    "host": "192.168.1.1",
    "username": "myusername",
    "password": "mypassword",
    "port": 830,
}


def get_connection(creds):
    """Function definition to obtain a Connection object to a specific SR OS device
    and access the model-driven information."""
    try:
        connection_object = connect(
            host=creds["host"],
            username=creds["username"],
            password=creds["password"],
            port=creds["port"],
        )
        return connection_object
    except RuntimeError as error1:
        print(
            "Failed to connect during the creation of the Connection object.  Error:",
            error1,
        )
        sys.exit(101)
    except ModelProcessingError as error2:
        print("Failed to create model-driven schema.  Error:", error2)
        sys.exit(102)
    except Exception as error3:  # pylint: disable=broad-except
        print("Failed to connect:", error3)
        sys.exit(103)


# Fuction definition to output a SR OS style table to the screen
def print_table(rows):
    """Setup and print the SR OS style table"""

    # Define the columns that will be used in the table.  Each list item
    # is a tuple of (column width, heading).
    cols = [
        (10, "ID"),
        (20, "Description"),
        (10, "Adm"),
        (10, "Opr"),
        (15, "Far End"),
    ]

    # Initalize the Table object with the heading and columns.
    table = Table(
        "Service Destination Points with Descriptions", cols, showCount="SDP"
    )

    # Print the output passing the data for the rows as an argument to the function.
    table.print(rows)


# The main function definition
def main():
    """Main function to display all SDPs on an SR OS device"""

    # Connect to the router.
    connection_object = get_connection(credentials)

    # Initialize the 'sdp_info' list that will be used to store the
    # data obtained that we wish to use in the output.
    sdp_info = []

    # Obtain the SDP configuration information from the SR OS device.  Ensure all
    # default values are returned in addition to specifically set values.
    sdp_conf = connection_object.running.get(
        "/nokia-conf:configure/service/sdp", defaults=True
    )

    # Obtain the SDP state information from the SR OS device.  Ensure all
    # default values are returned in addition to specifically set values.
    sdp_state = connection_object.running.get(
        "/nokia-state:state/service/sdp", defaults=True
    )

    # Identify the SDP ID numbers and store this value as the variable 'id' and perform
    # the following operations for every SDP.
    for ident in sdp_conf.keys():
        # Initalize the description variable as it is referenced later
        description = None

        # If the description of the SDP has been configured place the obtained
        # description into the 'description' variable.
        if "description" in sdp_conf[ident].keys():
            description = sdp_conf[ident]["description"].data

        # Store the administrative state of the SDP from the obtained
        # configuration data.
        admin_state = sdp_conf[ident]["admin-state"].data

        # Store the far-end IP address of the SDP from the obtained
        # configuration data.
        far_end = sdp_conf[ident]["far-end"]["ip-address"].data

        # Store the operational state of the SDP from the obtained
        # state data.
        oper_state = sdp_state[ident]["sdp-oper-state"].data

        # Add the collected data to the 'sdp_info' list that will be used as
        # the rows in the tabulated output.
        sdp_info.append([ident, description, admin_state, oper_state, far_end])

    # Print the table using the defined print_table function.
    print_table(sdp_info)

    # Disconnect from the model-driven interfaces of the SR OS node.
    connection_object.disconnect()

    # Returning 0 should be considered the same as completing the function with a
    # thumbs up!
    return 0


if __name__ == "__main__":
    main()
