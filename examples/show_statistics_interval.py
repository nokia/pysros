#!/usr/bin/env python3

### show_statistics_interval.py
#   Copyright 2021 Nokia
###

"""Example to show statistics for a given port in a given interval"""

import sys
import time
from pysros.management import connect, sros
from pysros.pprint import Table  # pylint: disable=no-name-in-module

# Import the exceptions so they can be caught on error.
from pysros.exceptions import ModelProcessingError

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


def get_input_args():
    """Obtain and process input arguments"""

    # expected ip-address as input -> defines next-hop
    if len(sys.argv) > 3:
        interval = int(sys.argv[1])
        count = int(sys.argv[2])
        port_name = sys.argv[3]
    else:
        print(
            "This script expects three arguments:\n"
            "    <interval> - <int>\n"
            "    <count> - <int>\n"
            "    <port-id> - <slot/mda/port>"
        )
        sys.exit(2)

    return interval, count, port_name


def print_table(
    rows, port_name, curr_time, prev_time, i, count
):  # pylint: disable=too-many-arguments
    """Setup and print the SR OS style table"""

    # compute total width of table
    cols = [
        (30, "Stat name"),
        (15, "Prev value"),
        (15, "Curr value"),
        (15, "Delta"),
    ]
    width = sum([col[0] for col in cols])
    if sros():
        if width > 79:
            print("The table width is too large to display on SR OS")
            sys.exit(105)

    # init and print table
    table = Table(
        "Port {} Statistics in ({}s) {}/{}".format(
            port_name, round(curr_time - prev_time, 2), i + 1, count
        ),
        cols,
        width=width,
    )
    table.print(rows)


def main():
    """Main function to take an interval, number of iterations and a SR OS port and
    display a regularly updating table of statistics."""

    # pylint: disable=too-many-locals

    # get input args
    interval, count, port_name = get_input_args()

    # connect to the router
    connection_object = get_connection(credentials)

    # we are going to use this timestamp
    prev_time = time.time()

    # make an initial get
    port_stats_path = (
        "/nokia-state:state/port[port-id='{}']/statistics".format(port_name)
    )
    init_port_state = connection_object.running.get(port_stats_path)

    # save init stats
    # if cannot parse, continue
    prev_port_stats = {}
    for item in init_port_state:
        if isinstance(init_port_state[item].data, int):
            prev_port_stats[item] = init_port_state[item].data

    # begin the cycle
    # not using while True, could be dangerous
    for i in range(count):
        # wait interval
        time.sleep(interval)
        # get current stats, count delta and update
        curr_time = time.time()
        curr_port_state = connection_object.running.get(port_stats_path)
        delta_port_stats = []
        for (
            item
        ) in prev_port_stats:  # pylint: disable=consider-using-dict-items
            prev_value = prev_port_stats[item]
            curr_value = curr_port_state[item].data
            delta = curr_value - prev_value
            delta_port_stats.append([item, prev_value, curr_value, delta])

        # clear screen
        print("\033c")
        # show delta stats
        print_table(
            delta_port_stats, port_name, curr_time, prev_time, i, count
        )
        prev_time = curr_time

    # disconnect from router
    connection_object.disconnect()


if __name__ == "__main__":
    main()
