#!/usr/bin/env python3

### show_route_table_communities.py
#   Copyright 2021 Nokia
###

"""Example to show all bgp routes for a given community expression"""

import re
import sys

# Import the exceptions so they can be caught on error.
from pysros.exceptions import ModelProcessingError
from pysros.management import connect
from pysros.pprint import Table  # pylint: disable=no-name-in-module

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
    """Obtain and process input arguments."""

    reg_expr = ""
    # expected regular expression as input - defines community name
    if len(sys.argv) == 2:
        reg_expr = sys.argv[1]
    else:
        print(
            "This script expects one argument:\n"
            "  <regular-expression> where <regular-expression> is a string enclosed in quotes\n"
        )
        sys.exit(-1)

    return reg_expr


def compile_reg_expr(reg_expr):
    """Attempt to compile the regular expression passed in as a command-line argument"""
    try:
        compiled_regex = re.compile(reg_expr)
    except Exception as error:  # pylint: disable=broad-except
        print(
            "An error has occured while compiling the regex: {}".format(error)
        )
        sys.exit(-1)

    return compiled_regex


def print_table(rows):
    """Setup and print the SR OS style table."""

    # compute total width of table
    cols = [
        (10, "Community"),
        (15, "Address-type"),
        (15, "Route"),
        (10, "Neighbor"),
        (7, "Owner"),
        (20, "Rout-ins"),
    ]
    # pylint: disable=consider-using-generator
    width = sum([col[0] for col in cols])

    # init and print table
    table = Table("Route-table for bgp communities", cols, width=width)
    table.print(rows)


def main():
    """Main procedure to obtain a BGP community regular expression and print
    the prefixes in the route-table with matching communities."""

    # get input argument
    reg_expr = get_input_args()

    # compile the input regular expression -> which is in sys.argv[1]
    community_regex = compile_reg_expr(reg_expr)

    # connect to the router
    connection_object = get_connection(credentials)

    # get the bgp portion of the state tree
    bgp_info = connection_object.running.get(
        "/nokia-state:state/router[router-name='Base']/bgp/rib"
    )
    # prepare a list for the routes info
    routes_info = []

    # first, iterate the address types: ipv4-unicast .. etc.
    # skip attr-sets - it is not an address-type, but stores the community-values
    # pylint: disable=too-many-nested-blocks
    for addr_type in bgp_info:
        if addr_type == "attr-sets":
            continue
        bgp_addr_type = bgp_info[addr_type]["local-rib"]
        # now iterate the routes
        for route in bgp_addr_type["routes"]:
            # store the attribute info
            attr_value = bgp_addr_type["routes"][route]["attr-id"].data
            # iterate the attribute sets
            for attr in bgp_info["attr-sets"]["attr-set"][
                ("rib-in", attr_value)
            ]:
                if attr == "communities":
                    for comm in bgp_info["attr-sets"]["attr-set"][
                        ("rib-in", attr_value)
                    ][attr]["community"]:
                        comm_value = bgp_info["attr-sets"]["attr-set"][
                            ("rib-in", attr_value)
                        ][attr]["community"][comm]["community-value"].data
                        # if the regex matches the value, store the info you need
                        # address_type, route, neighbor, owner, router_instance, community-name
                        if community_regex.match(comm_value):
                            routes_info.append(
                                [
                                    comm_value,
                                    addr_type,
                                    route[0],
                                    route[1],
                                    route[2],
                                    route[3],
                                ]
                            )

    # print data into table
    print_table(routes_info)

    # disconnect from router
    connection_object.disconnect()

    return 0


if __name__ == "__main__":
    main()
