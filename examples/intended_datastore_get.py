#!/usr/bin/env python3

### intended_datastore_get.py
#   Copyright 2021-2025 Nokia
###

"""
Tested on: SR OS 24.7.R1

Demonstrate the usage of the get method against the intended datastore to
show expanded configuration (such as applied configuration groups).

Execution on SR OS
    usage: pyexec bin/intended_datastore_get.py
Execution on remote machine
    usage: python intended_datastore_get.py
Execution on remote machine if intended_datastore_get.py is executable
    usage: ./intended_datastore_get.py

In order to use the intended datastore from a remote machine, NMDA must be
enabled on the SR OS node using the following MD-CLI command:

/configure system management-interface yang-modules nmda nmda-support true
"""

# Import the connect method from the pySROS libraries
from pysros.management import connect, sros


def setup_example_config(connection_object):
    """Deploys an example configuration-group template and an example
    interface that uses the template.

    Args:
        connection_object (pysros.management.Connection): pySROS Connection object
    """
    config_group = {
        "router": {
            "Base": {
                "router-name": "Base",
                "interface": {
                    "<example-.*>": {
                        "interface-name": "<example-.*>",
                        "ip-mtu": 4444,
                    }
                },
            }
        }
    }
    interface = {
        "description": "Example interface",
        "apply-groups": ["test"],
    }
    connection_object.candidate.set(
        '/configure/groups/group[name="test"]', config_group, method="replace"
    )
    connection_object.candidate.set(
        '/configure/router[router-name="Base"]/interface[interface-name="example-pysros"]',
        interface,
        method="replace",
    )


def cleanup_example_config(connection_object):
    """Remove the example configuration deployed at the start of the programs
    execution.

    Args:
        connection_object (pysros.management.Connection): pySROS Connection object
    """
    connection_object.candidate.delete(
        '/configure/router[router-name="Base"]/interface[interface-name="example-pysros"]'
    )
    connection_object.candidate.delete('/configure/groups/group[name="test"]')


def get_connection():
    """Obtain a Connection object from the node

    Raises:
        SystemExit: Exits the application with the error information

    Returns:
        pysros.management.Connection: pySROS Connection object
    """
    try:
        if sros():
            connection_object = connect()
        else:
            import getpass

            password = getpass.getpass(prompt="Enter password: ")
            connection_object = connect(
                host="hostname",
                username="admin",
                password=password,
                hostkey_verify=False,
            )
    except RuntimeError as runtime_error:
        raise SystemExit(runtime_error) from runtime_error
    return connection_object


def main():
    """Main procedure"""
    connection_object = get_connection()
    setup_example_config(connection_object)
    print(
        "Running:",
        connection_object.running.get(
            '/nokia-conf:configure/router[router-name="Base"]/interface[interface-name="example-pysros"]'
        ),
    )
    print(
        "Intended:",
        connection_object.intended.get(
            '/nokia-conf:configure/router[router-name="Base"]/interface[interface-name="example-pysros"]'
        ),
    )
    cleanup_example_config(connection_object)


if __name__ == "__main__":
    main()
