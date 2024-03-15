#!/usr/bin/env python3

### get_all_router_and_vprn.py
#   Copyright 2021 Nokia
###

"""Example to get all routers and VPRNs"""


import sys
from pysros.management import connect
from pysros.exceptions import ModelProcessingError
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


def print_table(rows, cols):
    """Setup and print the SR OS style table"""
    # compute total width of table
    all_cols = [(30, "Name"), (20, "Type")] + cols
    width = sum(  # pylint: disable=consider-using-generator
        [col[0] for col in all_cols]
    )

    # init and print table
    table = Table("Router List", all_cols, width=width)
    table.print(rows)


def main():
    """Main function to obtain all routers and VPRNs and output them in a table"""

    # connect to router
    connection_object = get_connection(credentials)

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
        rtr_type = rtr_path.rsplit("/", maxsplit=1)[-1]

        # get router config
        cfg = connection_object.running.get(rtr_path, defaults=True)

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
    connection_object.disconnect()

    return 0


if __name__ == "__main__":
    main()
