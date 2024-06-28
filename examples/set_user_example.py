#!/usr/bin/env python3


### set_user_example.py
#   Copyright 2021-2024 Nokia
###

"""Example to show how to set data"""

import random
import string

# Import the required libraries
import sys

# Import the exceptions so they can be caught on error.
from pysros.exceptions import ModelProcessingError
from pysros.management import connect

# Global credentials dictionary for the purposes of this example.  Global variables
# discouraged in operational applications.
creds = {"username": "myusername", "password": "mypassword"}


def check_user(*, connection, user_details):
    """Confirm that the user configuration has been applied"""
    try:
        running_config_user = connection.running.get(
            # pylint: disable=line-too-long
            '/nokia-conf:configure/system/security/user-params/local-user/user[user-name="{}"]'.format(
                user_details["user-name"]
            )
        )
        if running_config_user["user-name"].data == user_details["user-name"]:
            print("User:", user_details["user-name"], "Validated: True")
    except Exception as error:  # pylint: disable=broad-except
        print(
            "User:",
            user_details["user-name"],
            "Validated: False Error:",
            error,
        )


def add_user(*, connection, users):
    """Generate the configuration for each user, configure it and then read back the
    configuration to confirm it is correctly applied."""
    letter_box = string.ascii_letters + string.digits
    user_access_template = {"netconf": True, "console": True, "grpc": True}
    user_console_template = {"member": ["administrative"]}
    print("Creating...")
    for user in users:
        passwd = "".join(random.choice(letter_box) for i in range(15))
        template = {
            "user-name": user,
            "access": user_access_template,
            "password": passwd,
            "console": user_console_template,
        }
        try:
            connection.candidate.set(
                "/nokia-conf:configure/system/security/user-params/local-user/user",
                template,
            )
            print("User:", user, "Password:", passwd)
            check_user(connection=connection, user_details=template)
        except Exception as error:  # pylint: disable=broad-except
            print("Failed to create", user, "Error:", error)
            continue


def get_connection(host=None, credentials=None):
    """Function definition to obtain a Connection object to a specific SR OS device
    and access the model-driven information."""

    # The try statement and except statements allow an operation
    # attempt with specific error conditions handled gracefully
    try:
        connection_object = connect(
            host=host,
            username=credentials["username"],
            password=credentials["password"],
        )

        # Confirm to the user that the connection establishment completed successfully
        print("Connection established successfully")

        # Return the Connection object that we created
        return connection_object

    # This first exception is described in the pysros.management.connect method
    # and references errors that occur during the creation of the Connection object.
    # If the provided exception is raised during the execution of the connect method
    # the information provided in that exception is loaded into the e1 variable for use
    except RuntimeError as error1:
        print(
            "Failed to connect during the creation of the Connection object.  Error:",
            error1,
        )
        sys.exit(101)

    # This second exception is described in the pysros.management.connect method
    # and references errors that occur whilst compiling the YANG modules that have been
    # obtained into a model-driven schema.
    # If the provided exception is raised during the execution of the connect method, the
    # information provided in that exception is loaded into the e2 variable for use.
    except ModelProcessingError as error2:
        print("Failed to create model-driven schema.  Error:", error2)
        sys.exit(102)

    # This last exception is a general exception provided in Python
    # If any other unhandled specific exception is thrown the information provided in
    # that exception is loaded into the e3 variable for use
    except Exception as error3:  # pylint: disable=broad-except
        print("Failed to connect.  Error:", error3)
        sys.exit(103)


def main():
    """Provide a list of hosts to add the users too and this main function connects
    to each device in turn and adds the user."""
    inventory_hosts = ["192.168.168.70"]
    users = ["rod", "jane", "freddy"]
    for host in inventory_hosts:
        try:
            connection_object = get_connection(host, creds)
            add_user(connection=connection_object, users=users)
        except Exception:  # pylint: disable=broad-except
            continue


if __name__ == "__main__":
    main()
