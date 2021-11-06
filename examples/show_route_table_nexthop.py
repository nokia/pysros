#!/usr/bin/env python3

### show_route_table_communities.py
#   Copyright 2021 Nokia
###

"""Example to show all bgp routes for a given next-hop"""

import sys
import ipaddress
from pysros.management import connect
from pysros.pprint import Table  # pylint: disable=no-name-in-module

# Import the exceptions so they can be caught on error.
from pysros.exceptions import ModelProcessingError

credentials = {
    "host": "192.168.168.70",
    "username": "admin",
    "password": "admin",
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
    """Obtain the input arguments and process them"""

    # expected ip-address as input -> defines next-hop
    if len(sys.argv) == 2:
        try:
            next_hop = str(ipaddress.IPv4Address(sys.argv[1]))
        except Exception as error:  # pylint: disable=broad-except
            print("Argument is not valid IPv4 address: ", error)
            sys.exit(-1)
    else:
        print(
            "This script expects one argument:\n"
            "  <ipv4-address> - <[0-255].[0-255].[0-255].[0-255]>\n"
        )
        sys.exit(-1)

    return next_hop


def print_table(rows, next_hop):
    """Setup and output the SR OS style table"""
    cols = [
        (15, "Address-type"),
        (20, "Route"),
        (10, "Neighbor"),
        (7, "Owner"),
        (20, "Rout-ins"),
    ]

    # init and print table
    table = Table("Route-table for bgp routes with next-hop: {}".format(next_hop), cols)
    table.print(rows)


def main():
    """Main procedure to obtain all routes in the routing table
    with the specified next-hop address"""

    # get input argument
    target_next_hop = get_input_args()

    # connect to the router
    connection_object = get_connection(credentials)

    # get the bgp portion of the state tree
    bgp_info = connection_object.running.get(
        "/nokia-state:state/router[router-name='Base']/bgp/rib"
    )

    # prepare a list for the routes info
    routes_info = []

    # first, iterate the address types: ipv4-unicast .. etc.
    # skip attr-sets - it is not an address-type, but stores the next-hop address
    for addr_type in bgp_info:
        if addr_type == "attr-sets":
            continue
        bgp_addr_type = bgp_info[addr_type]["local-rib"]
        # now iterate the routes
        for route in bgp_addr_type["routes"]:
            # store the route attribute info
            attr_value = bgp_addr_type["routes"][route]["attr-id"].data
            # iterate the attribute sets
            next_hop_value = bgp_info["attr-sets"]["attr-set"][("rib-in", attr_value)][
                "next-hop"
            ].data
            if next_hop_value == target_next_hop:
                # store the info, address_type, route, neighbor, owner, router_instance
                routes_info.append([addr_type, route[0], route[1], route[2], route[3]])

    # print data into table
    print_table(routes_info, target_next_hop)

    # disconnect from router
    connection_object.disconnect()

    return 0


if __name__ == "__main__":
    main()
