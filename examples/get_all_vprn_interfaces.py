#!/usr/bin/env python3

### get_all_vprn_interfaces.py
#   Copyright 2023 Nokia
###

"""Example to get all VPRN interfaces with in/out packets in one CLI command"""

from pysros.management import connect, sros
from pysros.pprint import Table  # pylint: disable=no-name-in-module


def print_table(rows, cols):
    """Setup and print the SR OS style table"""
    # compute total width of table
    all_cols = [(15, "VPRN")] + cols

    # init and print table
    table = Table("All Interfaces on all VPRNs", all_cols, width=100)
    table.print(rows)


def keys_exists(obj, *keys):
    """Confirm whether all the required keys exist"""
    for key in keys:
        if key in obj:
            obj = obj[key]
        else:
            return False
    return True


def main():
    """Main function to obtain all routers and VPRNs and output them in a table"""

    # connect to router
    if sros():
        connection_object = connect()  # pylint: disable=missing-kwoa
    else:
        raise SystemExit("Example for on-box use only")

    state = connection_object.running.get("/nokia-state:state/service/vprn")
    # cols we want to fetch
    cols = [
        (15, "Interface Name"),
        (15, "IPv4 Address"),
        (15, "Oper Status"),
        (15, "Port:VLAN"),
        (10, "In-Pkts"),
        (10, "Out-Pkts"),
    ]
    rows = []
    # iterate all vprns
    for vrtr_name in state:
        # row = [vrtr_name]
        vrtr_state = state[vrtr_name]
        if "interface" in vrtr_state.keys():
            # iterate all interfaces in vprn
            for if_name in vrtr_state["interface"]:
                row = [vrtr_name]
                row.append(if_name)
                if_state = vrtr_state["interface"][if_name]
                if keys_exists(if_state, "ipv4", "primary", "oper-address"):
                    oper_address = if_state["ipv4"]["primary"][
                        "oper-address"
                    ].data
                    row.append(oper_address)
                if_operstate = if_state["oper-state"].data
                row.append(if_operstate)
                if "sap" in if_state.keys():
                    for sap_name in if_state["sap"]:
                        row.append(sap_name)
                else:
                    row.append("loopback")
                if keys_exists(if_state, "ipv4", "statistics"):
                    if_in_pkts = if_state["ipv4"]["statistics"][
                        "in-packets"
                    ].data
                    if_out_pkts = if_state["ipv4"]["statistics"][
                        "out-packets"
                    ].data
                    row.append(if_in_pkts)
                    row.append(if_out_pkts)
                rows.append(row)

    print_table(rows, cols)

    # disconnect from router
    connection_object.disconnect()


if __name__ == "__main__":
    main()
