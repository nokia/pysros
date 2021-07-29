#!/usr/bin/env python3

### setUserExample.py
#   Copyright 2021 Nokia
#   Example to show how to set data
###

# Import the required libraries
import sys, string, random
from pysros.management import connect
# Import the exceptions so they can be caught on error.
from pysros.exceptions import *


# Global credentials dictionary for the purposes of this example.  Global variables
# discouraged in operational applications.
credentials = {
    "username": "admin",
    "password": "admin"
}

def check_user(*, connection, user_details):
    try:
        running_config_user = connection.running.get(
            '/nokia-conf:configure/system/security/user-params/local-user/user[user-name="{}"]'.format(
                user_details['user-name']))
        if running_config_user['user-name'].data == user_details['user-name']:
            print("User:", user_details['user-name'], "Validated: True")
    except Exception as e:
        print("User:", user_details['user-name'], "Validated: False Error:", e)

def add_user(*, connection, users):
    letter_box = string.ascii_letters + string.digits
    user_access_template = {
            "netconf": True,
            "console": True,
            "grpc": True
    }
    user_console_template = {
            "member": ["administrative"]
    }
    print("Creating...")
    for user in users:
        passwd = ''.join(random.choice(letter_box) for i in range(15))
        template = {'user-name': user,
                    'access': user_access_template,
                    'password': passwd,
                    'console': user_console_template}
        try:
            connection.candidate.set('/nokia-conf:configure/system/security/user-params/local-user/user', template)
            print("User:", user, "Password:", passwd)
            check_user(connection=connection, user_details=template)
        except Exception as e:
            print("Failed to create", user, "Error:", e)
            continue

# Function definition to obtain a Connection object to a specific SR OS device
# and access the model-driven information.
def get_connection(host):
    # Attempt to make the connection and handle any error scenarios.
    try:
        c = connect(
            host=host,
            username=credentials["username"],
            password=credentials["password"],
            port=830
        )
        # Return the Connection object.
        return c
    except Exception as e:
        print("Failed to connect to", host, "Error:", e)
        sys.exit(-1)


def main():
    inventory_hosts = ['192.168.168.70']
    users = ['rod', 'jane', 'freddy']
    for host in inventory_hosts:
        try:
            c = get_connection(host)
            add_user(connection=c, users=users)
        except Exception:
            continue



if __name__ == "__main__":
    main()
