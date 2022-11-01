#!/usr/bin/env python3

### get_inventory_remotely.py
#   Copyright 2021 Nokia
###

"""Example to show obtaining a hardware inventory of multiple devices"""

# Import the required libraries
import sys
import ipaddress
import json
from pysros.management import connect, sros
from pysros.exceptions import ModelProcessingError


# Global credentials dictionary for the purposes of this example.  Global variables
# discouraged in operational applications.
credentials = {"username": "myusername", "password": "mypassword"}


def get_connection(creds, host):
    """Function definition to obtain a Connection object to a specific SR OS device
    and access the model-driven information."""
    try:
        connection_object = connect(
            host=host,
            username=creds["username"],
            password=creds["password"],
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
        sys.exit(103)
    except Exception as error3:  # pylint: disable=broad-except
        print("Failed to connect:", error3)
        sys.exit(103)


def get_input_args():
    """Function definition to check that input arguments exist and that they are in
    the correct format for processing."""

    # Initialize the 'args' list that will be used to store the validate arguments
    # for use later in the application
    args = []

    # Confirm that arguments have been provided
    if len(sys.argv) > 1:
        try:
            # For every argument provided, confirm that the argument is a valid IP address
            for arg in sys.argv[1:]:
                args.append(ipaddress.ip_address(arg))
            # Return the list of valid arguments (IP addresses)
            return args

        # If the provided arguments are not valid IP addresses provide this feedback and exit
        # the application.
        except Exception as error:  # pylint: disable=broad-except
            print("Argument is not valid IP address: ", error)
            sys.exit(-1)
    # If no arguments have been provided then print the usage information to the screen and
    # exit the application
    else:
        print("This application expects a whitespace separated list of IP addresses\n")
        print("Usage:", sys.argv[0], "<IP address> [IP address] ...\n")
        sys.exit(-1)
    return -1


def get_hardware_data(struct):
    """Function definition to iterate through a provided data-structure looking for a
    hardware-data container and then create a dictionary of the contents."""

    # Initialize the empty dictionary in case there is no hardware-data container in
    # the provided data-structure.
    build_hash = {}

    # Identify the hardware-data container in the data-structure and create the dictionary.
    for k in struct["hardware-data"]:
        build_hash[k] = struct["hardware-data"][k].data

    # Return the dictionary of hardware-data inventory items.
    return build_hash


def get_chassis_inventory(connection_object):
    """Function definition to obtain chassis state information from SR OS and obtain the
    required data in order to build the inventory."""

    # Obtain the data from the SR OS device.  The data in this example is only obtained
    # from the first chassis per host.
    chassis_state = connection_object.running.get(
        '/nokia-state:state/chassis[chassis-class="router"][chassis-number="1"]'
    )

    # Define some constants that describe the chassis itself
    hwtype = "chassis"
    number = 1

    # Obtain the dictionary of the hardware-data elements and their values from the
    # chassis_state data-structure.
    build_hash = get_hardware_data(chassis_state)

    # Initialize the results dictionary with the chassis information using the above constants
    # and the obtained hardware-data.
    hash_data = {hwtype: {number: build_hash}}

    # For every element in the original chassis_state data-structure iterate through the
    # child elements (depth 1) and select the fans and power-supplies.
    for item in chassis_state.keys():
        if item in ["fan", "power-supply"]:
            item_num_hash = {}

            # For every fan and power-supply obtain the hardware-data information and add
            # it to the return dictionary.
            for item_num in chassis_state[item]:
                item_num_hash[item_num] = get_hardware_data(
                    chassis_state[item][item_num]
                )
            hash_data[item] = item_num_hash

    # Return the dictionary containing all chassis, fan and power-supply hardware inventory data.
    return hash_data


def get_card_inventory(connection_object):
    """Function definition to obtain card state information from SR OS and obtain the
    required data in order to build the inventory."""

    # Obtain the state data about line cards from the SR OS device.
    card_state = connection_object.running.get("/nokia-state:state/card")

    # Initialize the dictionary because no line cards may exist.
    hash_data = {}

    # For every line card installed obtain the hardware-data for the inventory.
    for item_number in card_state.keys():
        hash_data[item_number] = get_hardware_data(card_state[item_number])

    # Return a dictionary of cards with the obtained data.
    return {"card": hash_data}


def main():
    """The 'main' function definition.  Check that the application is not being executed on SR OS
    and then obtain the provided arguments and iterate through the hosts to obtain and build
    a hardware inventory which is outputted in JSON format."""

    # Check that the application is not being executed on SR OS.
    # If it is, provide a warning and exit.
    if sros():
        print(
            "This application cannot be run on the SR OS node.  Please run it on an external device"
        )
        sys.exit(200)
    else:
        # Obtain the host IP addresses provided as input arguments.
        hosts = get_input_args()
        # Initialize the inventory dictionary to cover the case where no hardware data is returned.
        chassis_inv = {}

        # For every host connect to the model-driven interface and obtain the inventory/
        for host in hosts:
            # Obtain a Connection object for the host.
            connection_object = get_connection(credentials, str(host))
            # Obtain the inventory of chassis, fan and power-supply data.
            per_host_inv = get_chassis_inventory(connection_object)
            # Obtain the inventory of line card data.
            per_host_inv.update(get_card_inventory(connection_object))
            # Link the completed inventory with the specific host in the output dictionary.
            chassis_inv[str(host)] = per_host_inv
            # Close the connection to the model-driven interface of the host.
            connection_object.disconnect()

        # Output the obtained inventory in indented JSON format.
        print(json.dumps(chassis_inv, indent=4))


if __name__ == "__main__":
    main()
