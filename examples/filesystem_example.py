#!/usr/bin/env python3

### filesystem_example.py
#   Copyright 2022 Nokia
###

"""Example to demonstrate local filesystem access on an SR OS device.

Tested on: SR OS 22.7.R1
"""

# pylint: disable=broad-except, eval-used, unspecified-encoding

import sys
from pysros.management import connect, sros


def update_file(filename=None, operation="get", counter=None, stat_value=None):
    """Read and write from the file on the SR OS filesystem.

    :param filename: Full path to the filename to read/write to/from.
    :type filename: str
    :param operation: Define whether the action is to ``get`` (read) from the
                      file or ``set`` (write) to the file.
    :type operation: str
    :param counter: Counter variable for number of times the file has been
                    written to.
    :type counter: int
    :param stat_value: Value of the statistic being recorded to the file.
    :type stat_value: int
    :returns: Returns the counter and statistic
    :rtype: tuple

    """
    if operation == "get":
        try:
            with open(filename, "r") as file_object:
                # Read the tuple in from the file, if it does not exist, set it to (0, stat_value)
                # where stat_value where stat_value exists (the program will exit earlier if the
                # statistic cannot be obtained.
                return_tuple = eval(file_object.read() or (0, stat_value))
            return return_tuple
        except OSError:
            # If the file cannot be read (for example, because it does not exist) then return
            # the default counter 0 and the current statistic value
            return (0, stat_value)
        except Exception as error:
            print("Failed:", error)
            sys.exit(6)
    elif operation == "set":
        try:
            with open(filename, "w") as file_object:
                # Write to the file the current counter and stat_value as a tuple
                file_object.write(str((counter, stat_value)))
            return 0
        except Exception as error:
            print("Failed:", error)
            sys.exit(7)
    else:
        sys.exit(3)


def get_stat_value(connection_object):
    """Obtain the statistics from the node.  The statistic gathered in
    this example is the number of received octets from a specific BGP peer
    at the neighbor IP address of 192.168.10.2.  You can replace this path with
    a path of your choosing.

    :param connection_object: Connection object referencing the router connection.
    :type connection_object: :py:class:`pysros.Connection`
    :returns: pySROS dataset containing the requested statistics
    :rtype: dict
    """
    return connection_object.running.get(
        # pylint: disable=line-too-long
        '/nokia-state:state/router[router-name="Base"]/bgp/neighbor[ip-address="192.168.10.2"]/statistics/received/octets'
    )


def main():
    """This is the main function, the example code begins here."""

    # Obtain a connection to the router.  The example uses connect() without
    # credentials as this example is designed to operate on the SR OS device.
    try:
        connection_object = connect()  # pylint: disable=missing-kwoa
    except Exception as error:
        print("Failed to obtain a connection:", error)
        sys.exit(5)

    # Attempt to obtain the statistical data from the node.
    try:
        stat_value = get_stat_value(connection_object).data
    except Exception as error:
        print("Failed to obtain statistics\n", error)
        sys.exit(2)

    # Provide the full path to the file the will be read from and written to.
    filename = "cf3:\\counter.txt"

    # Obtain the data the file
    mytuple = update_file(filename=filename, stat_value=stat_value)

    # Output to the screen the details of this run and the difference between this
    # run the and last.
    print("This command has been run", mytuple[0] + 1, "times")
    print(
        "Number of received octets for BGP peer 192.168.10.2 (last run/this run):",
        mytuple[1],
        "/",
        stat_value,
    )
    print(
        "The difference between the last run and this run is:",
        stat_value - mytuple[1],
    )

    # Increase the counter and update the file with the new data.
    counter = mytuple[0] + 1
    update_file(
        filename=filename,
        operation="set",
        counter=counter,
        stat_value=stat_value,
    )


if __name__ == "__main__":
    # Check that the application is being run on an SR OS device, if not then
    # exit.
    if sros():
        main()
    else:
        print("This example is designed to operate on an SR OS node.")
        sys.exit(10)
