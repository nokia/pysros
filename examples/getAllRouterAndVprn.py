#!/usr/bin/env python3

### getAllRouterAndVprn.py
#   Copyright 2021 Nokia
#   Example to get all routers and VPRNs
###

import sys
from pysros.management import connect
from pysros.exceptions import *
from pysros.pprint import Table

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

def print_table(rows, cols):
    # compute total width of table
    all_cols = [(30, "Name"), (20, "Type")] + cols
    width = sum([col[0] for col in all_cols])

    # init and print table
    table = Table("Router List", all_cols, width=width)
    table.print(rows)

def main():

    # connect to router
    c = get_connection(credentials)

    # list of router paths
    router_path_list = [
        "/nokia-conf:configure/router",
        "/nokia-conf:configure/service/vprn",
    ]

    # cols we want to fetch
    cols = [(20, "admin-state"), (30, "description")]
    rows = []
    # iterate router_path_list
    for rtr_path in router_path_list:
        # vprn or grt
        rtr_type = rtr_path.split("/")[-1]

        # get router config
        cfg = c.running.get(rtr_path, defaults=True)

        # iterate routers in rtr_path
        for rtr_name in cfg:
            row = [rtr_name, rtr_type]
            for col in cols:
                # get field name, add if non empty
                field = col[1]
                if field in cfg[rtr_name]:
                    row.append(cfg[rtr_name][field])
                else:
                    row.append("None")
            rows.append(row)

    # print data into table
    print_table(rows, cols)

    # disconnect from router
    c.disconnect()

    return 0

if __name__ == "__main__":
    main()


