#!/usr/bin/env python3

### showServiceSapsWithServiceType.py
#   Copyright 2021 Nokia
#   Example to show all SAPs with service-type
###
	
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
    
def print_table(rows):
    # compute total width of table
    cols = [
        (20, "Sap"),
        (20, "SvcId"),
        (10, "SvcType"),
        (10, "Adm"),
        (10, "Oper"),
    ]
    width = sum([col[0] for col in cols])
		
    # init and print table
    table = Table(
            "Service Access Points with service-type", cols, showCount="SAPs", width=width)		
    table.print(rows)

def main():

    # connect to the router
    c = get_connection(credentials)

    # store our data in sap_data
    sap_data = []

    # iterate through the services
    service_conf = c.running.get("/nokia-conf:configure/service")
    for service in service_conf:
        for name in service_conf[service]:
            # we need the service which has sap(s)
            if "sap" in service_conf[service][name].keys():
                # construct path
                path = "/service/{}[service-name='{}']".format(service, name)
                # store service-type
                service_type = service
                # store admin-state
                admin_state = None
                # if default, we have to do a new get
                if "admin-state" not in service_conf[service][name].keys():
                    admin_state = c.running.get(
                        "/nokia-conf:configure{}/admin-state".format(path),
                        defaults=True,
                    ).data
                else:
                    admin_state = service_conf[service][name]["admin-state"].data

                # get data from the state tree
                service_state = c.running.get("/nokia-state:state{}".format(path))
                # store service-id
                service_id = service_state["oper-service-id"].data
                # store oper-state
                oper_state = service_state["oper-state"].data
                for sap in service_state["sap"]:
                    sap_data.append(
                        [sap, service_id, service_type, admin_state, oper_state]
                    )

    # print the table
    print_table(sap_data)

    # disconnect from router
    c.disconnect()

    return 0

if __name__ == "__main__":
    main()
		

# example with memory debug only off-box
