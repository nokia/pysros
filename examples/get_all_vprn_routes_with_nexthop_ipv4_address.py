#!/usr/bin/env python3

### get_all_vprn_routes_with_nexthop_ipv4_address.py
#   Copyright 2021 Nokia
###

"""Example to get all VPRN routes with a given next-hop IP address"""

import sys
import ipaddress
from pysros.management import connect
from pysros.exceptions import ModelProcessingError
from pysros.pprint import Table  # pylint: disable=no-name-in-module

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
    """Obtain and evaluate input arguments"""
    if len(sys.argv) > 1:
        try:
            searched_ip_address = ipaddress.IPv4Address(sys.argv[1])
        except Exception as error:  # pylint: disable=broad-except
            print("Argument is not valid ipv4 address: ", error)
            sys.exit(-1)
    else:
        print(
            # pylint: disable=line-too-long
            "This script expects one argument:\n<ipv4-address> - <[0-255].[0-255].[0-255].[0-255]>\n"
        )
        sys.exit(-1)

    return searched_ip_address


def print_table(route_list, searched_ip_address):
    """Setup and print the SR OS style table"""
    # compute total width of table
    cols = [(30, "Route"), (20, "Vprn"), (20, "Traffic Type"), (20, "Ipv Type")]
    width = sum([col[0] for col in cols])

    # init and print table
    table = Table(
        "Route List (nexthop: {})".format(searched_ip_address), cols, width=width
    )
    table.print(route_list)


def keys_exists(obj, *keys):
    """Confirm whether all the required keys exist"""
    for key in keys:
        if key in obj:
            obj = obj[key]
        else:
            return False
    return True


def main():
    """Main procedure to get all VPRN routes with a given next-hop IP address"""
    # pylint: disable=too-many-locals,too-many-nested-blocks,too-many-branches

    # get input argument
    searched_ip_address = get_input_args()

    # connect to router and get state for all vprn
    connection_object = get_connection(credentials)
    state = connection_object.running.get("/nokia-state:state/service/vprn")

    if_list = []
    # iterate all vprns
    for vrtr_name in state:
        vrtr_state = state[vrtr_name]
        if "interface" in vrtr_state.keys():
            # iterate all interfaces in vprn
            for if_name in vrtr_state["interface"]:
                if_state = vrtr_state["interface"][if_name]
                if keys_exists(if_state, "ipv4", "primary", "oper-address"):
                    oper_address = if_state["ipv4"]["primary"]["oper-address"].data
                    ip_address = ipaddress.IPv4Address(oper_address)
                    if_list.append((if_state["if-index"], if_name, ip_address))

    # filter interface index list where ipv4 address is searched address
    if_index_list = [ifs[0].data for ifs in if_list if searched_ip_address == ifs[2]]

    route_list = []
    # iterate all vprns
    for vrtr_name in state:
        vrtr_state = state[vrtr_name]

        # iterate all cast and ipv types
        for traffic_type in ["multicast", "unicast"]:
            for ipv_type in ["ipv4", "ipv6"]:
                # check if route exists or continue
                if keys_exists(
                    vrtr_state, "route-table", traffic_type, ipv_type, "route"
                ):
                    routes_state = vrtr_state["route-table"][traffic_type][ipv_type][
                        "route"
                    ]
                    # iterate all routes
                    for route_name in routes_state:
                        if "nexthop" in routes_state[route_name]:
                            # iterate all nexthop
                            for nexthop_id in routes_state[route_name]["nexthop"]:
                                if keys_exists(
                                    routes_state[route_name]["nexthop"][nexthop_id],
                                    "if-index",
                                ):
                                    nexthop_if_index = routes_state[route_name][
                                        "nexthop"
                                    ][nexthop_id]["if-index"].data
                                    nexthop_if_index = int(nexthop_if_index)
                                    # add route if nexthop interface in interface index list
                                    if nexthop_if_index in if_index_list:
                                        route_list.append(
                                            (
                                                route_name,
                                                vrtr_name,
                                                traffic_type,
                                                ipv_type,
                                            )
                                        )

        # iterate all static routes if they exist
        if keys_exists(vrtr_state, "static-routes"):
            for route in vrtr_state["static-routes"]["route"]:
                # if a route with a next-hop exists
                if keys_exists(vrtr_state["static-routes"]["route"][route], "next-hop"):
                    # identify whether the address portion of the CIDR address is IPv4 or IPv6
                    version = ipaddress.ip_address(route[0].split("/")[0]).version
                    if version == 4:
                        route_list.append((route[0], vrtr_name, route[1], "ipv4"))
                    elif version == 6:
                        route_list.append((route[0], vrtr_name, route[1], "ipv6"))
                    else:
                        print("Unknown whether ipv4 or ipv6")
                        sys.exit(-1)

    # print data into table
    print_table(route_list, searched_ip_address)

    # disconnect from router
    connection_object.disconnect()

    return 0


if __name__ == "__main__":
    main()
