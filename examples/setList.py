#!/usr/bin/env python3

### setList.py
#   Copyright 2021 Nokia
#   Simple example to explain the various YANG list configuration options
###

# Import the required libraries
from pysros.management import connect
# Import the exceptions so they can be caught on error.
from pysros.exceptions import *
import sys

# YANG list configuration - method 1 example
def setListMethod1(c):
    # path is the json-instance-path to the YANG list
    path = '/nokia-conf:configure/log/log-id'
    # payload is a dict including the list key-values as the Python dict keys
    payload = {'10': {'description': 'Log ten'}, '11': {'description': 'Log eleven'}}
    print("YANG list configuration - Method 1")
    print("  {: <15}: {: <}".format(*['Path', path]))
    print("  {: <15}: {: <}".format(*['Payload', str(payload)]))
    print("  {: <15}: {: <}".format(*['API call', 'c.candidate.set(path, payload)']))
    print("  c.candidate.set(path, payload)")
    # Configure the SR OS device
    c.candidate.set(path, payload)

# YANG list configuration - method 2 example
# Method 2 requires multiple set API calls
def setListMethod2(c):
    # Provide the list entry data that will be iterated through
    list_entries = [("10", "Log ten"), ("11", "Log eleven")]
    print("\nYANG list configuration - Method 2")
    for item in list_entries:
        # payload is the fields to be set within the list item.  The key name and key-value are not provided.
        payload = {'description': item[1]}
        # path is the json-instance-path to the YANG lists specific item including list name,
        # list key name and the list key-value.
        path = '/nokia-conf:configure/log/log-id[name=' + item[0] + ']'
        print("  {: <15}: {: <}".format(*['Path', path]))
        print("  {: <15}: {: <}".format(*['Payload', str(payload)]))
        print("  {: <15}: {: <}".format(*['API call', 'c.candidate.set(path, payload)']))
        # Configure the SR OS device
        c.candidate.set(path, payload)

# YANG list configuration - method 3 example
# Method 3 requires multiple set API calls
def setListMethod3(c):
    # Provide the list entry data that will be iterated through
    list_entries = [("10", "Log ten"), ("11", "Log eleven")]
    print("\nYANG list configuration - Method 3")
    for item in list_entries:
        # payload is the fields to be set within the list item.  The key name and key-value are provided
        # even though they are also to be referenced in the path.
        payload = {'name': item[0], 'description': item[1]}
        # path is the json-instance-path to the YANG lists specific item including list name,
        # list key name and the list key-value.
        path = '/nokia-conf:configure/log/log-id[name=' + item[0] + ']'
        print("  {: <15}: {: <}".format(*['Path', path]))
        print("  {: <15}: {: <}".format(*['Payload', str(payload)]))
        print("  {: <15}: {: <}".format(*['API call', 'c.candidate.set(path, payload)']))
        # Configure the SR OS device
        c.candidate.set(path, payload)

# Define the main function
def main():
    # Establish the connection to SR OS and handle any errors
    try:
        c = connect(host='192.168.168.70', username='admin', password='admin')
    except Exception as e:
        print("Failed to connect.  Error:", e)
        sys.exit(-1)

    # Call the various configuration methods in turn
    setListMethod1(c)
    setListMethod2(c)
    setListMethod3(c)

# Run from here
main()
