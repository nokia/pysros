#!/usr/bin/env python3

### showRouteTableCommunities.py
#   Copyright 2021 Nokia
#   Example to show all bgp routes for a given community expression
###
	
import re
import sys
from pysros.management import connect
from pysros.pprint import Table
# Import the exceptions so they can be caught on error.
from pysros.exceptions import *

credentials = {
    "host": "192.168.168.70",
    "username": "admin",
    "password": "admin",
    "port": 830,
}
	
def get_connection(credentials):
    try:
        c = connect(
            host=credentials["host"],
            username=credentials["username"],
            password=credentials["password"],
            port=credentials["port"],
        )
    except Exception as e:
        print("Failed to connect:", e)
        sys.exit(-1)

    return c

def get_input_args():
    # expected regular expression as input - defines community name
    if len(sys.argv) > 1:
        reg_expr = sys.argv[1]
    else:
        print("This script expects one argument:\n<regular-expression> - <string enclosed in quotes>\n")
        sys.exit(-1)
			
    return reg_expr
		
def compile_reg_expr(reg_expr):
    try:
        compiled_regex = re.compile(sys.argv[1])
    except Exception as e:
        print(
            "An error has occured while compiling the regex: {}".format(e)
        )
        sys.exit(-1)

    return compiled_regex

def print_table(rows):
    # compute total width of table
    cols = [
        (10, "Community"),
        (15, "Address-type"),
        (15, "Route"),
        (10, "Neighbor"),
        (7, "Owner"),
        (20, "Rout-ins"),
    ]
    width = sum([col[0] for col in cols])

    # init and print table
    table = Table("Route-table for bgp communities", cols, width=width)
    table.print(rows)


def main():

    # get input argument
    reg_expr = get_input_args()

    # compile the input regular expression -> which is in sys.argv[1]
    community_regex = compile_reg_expr(reg_expr)        

    # connect to the router
    c = get_connection(credentials)

    # get the bgp portion of the state tree
    bgp_info = c.running.get(
        "/nokia-state:state/router[router-name='Base']/bgp/rib"
    )
    # prepare a list for the routes info
    routes_info = []

    # first, iterate the address types: ipv4-unicast .. etc.
    # skip attr-sets - it is not an address-type, but stores the community-values
    for addr_type in bgp_info:
        if addr_type == "attr-sets":
            continue
        bgp_addr_type = bgp_info[addr_type]["local-rib"]
        # now iterate the routes
        for route in bgp_addr_type["routes"]:
            # store the attribute info
            attr_value = bgp_addr_type["routes"][route]["attr-id"].data
            # iterate the attribute sets
            for attr in bgp_info["attr-sets"]["attr-set"][("rib-in", attr_value)]:
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
    c.disconnect()
    
    return 0

if __name__ == "__main__":
    main()


