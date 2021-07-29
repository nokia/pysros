#!/usr/bin/env python3

### showStatisticsInterval.py
#   Copyright 2021 Nokia
#   Example to show statistics for a given port in a given interval
###
	
import sys
import time
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
    # expected ip-address as input -> defines next-hop
    if len(sys.argv) > 3:
        interval = int(sys.argv[1])
        count = int(sys.argv[2])
        port_name = sys.argv[3]
    else:
        print(
            "This script expects three arguments:\n<interval> - <int>\n<count> - <int>\n<port-id> - <slot/mda/port>"
        )
        sys.exit(-1)
			
    return interval, count, port_name
    
def print_table(rows, port_name, curr_time, prev_time, i, count):
    # compute total width of table
    cols = [
        (30, "Stat name"),
        (15, "Prev value"),
        (15, "Curr value"),
        (15, "Delta"),
    ]
    width = sum([col[0] for col in cols])
		
    # init and print table
    table = Table(
            "Port {} Statistics in ({}s) {}/{}".format(
                port_name, round(curr_time - prev_time, 2), i + 1, count
            ),
            cols,
        )		
    table.print(rows)
		
def main():

    # get input args
    interval, count, port_name = get_input_args()
    
    # connect to the router
    c = get_connection(credentials)

    # we are going to use this timestamp
    prev_time = time.time()

    # make an initial get
    port_stats_path = "/nokia-state:state/port[port-id='{}']/statistics".format(
        port_name
    )
    init_port_state = c.running.get(port_stats_path)

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
        curr_port_state = c.running.get(port_stats_path)
        delta_port_stats = []
        for item in prev_port_stats:
            prev_value = prev_port_stats[item]
            curr_value = curr_port_state[item].data
            delta = curr_value - prev_value
            delta_port_stats.append([item, prev_value, curr_value, delta])

        # clear screen
        print("\033c")
        # show delta stats            
        print_table(delta_port_stats, port_name, curr_time, prev_time, i, count)
        prev_time = curr_time

    # disconnect from router
    c.disconnect()

    return 0

if __name__ == "__main__":
    main()


