#!/usr/bin/env python3

### show_log_event_summary.py
#   Copyright 2021 Nokia
###

# pylint: disable=line-too-long

"""
Tested on: SR OS 23.10.R2

Obtain a summary of the log event history on the node.

Execution on SR OS
    usage: pyexec bin/show_log_event_summary.py
Execution on remote machine
    usage: python show_log_event_summary username@host
Execution on remote machine if show_log_event_summary.py is executable
     usage: ./show_log_event_summary.py username@host

Add the following alias so that the Python application can be run as a
native MD-CLI command.

/configure python { python-script "show-log-event-summary" admin-state enable }
/configure python { python-script "show-log-event-summary" urls ["cf3:bin/show_log_event_summary.py"] }
/configure python { python-script "show-log-event-summary" version python3 }
/configure system { management-interface cli md-cli environment command-alias alias "event-summary" }
/configure system { management-interface cli md-cli environment command-alias alias "event-summary" admin-state enable }
/configure system { management-interface cli md-cli environment command-alias alias "event-summary" description "Show log event summary" }
/configure system { management-interface cli md-cli environment command-alias alias "event-summary" python-script "show-log-event-summary" }
/configure system { management-interface cli md-cli environment command-alias alias "event-summary" mount-point "/show log" }

"""

from pysros.management import connect, sros
from pysros.pprint import Table
from pysros.exceptions import InvalidPathError, SrosMgmtError, InternalError


def get_connection():
    """Function definition to obtain a Connection object to a specific SR OS device
    and access model-driven information"""

    # Use the sros() function to determine if the application is executed
    # locally on an SR OS device, or remotely so that the same application
    # can be developed to run locally or remotely.  If the application is
    # executed locally, call connect() and return the Connection object.
    # If the application is executed remotely, the username and host is
    # required as arguments, and a prompt for the password is displayed
    # before calling connect().  Connection error handling is also checked.

    # If the application is executed locally
    if sros():
        connection_object = connect()  # pylint: disable=missing-kwoa

    # Else if the application is executed remotely
    else:
        # Import sys for returning specific exit codes
        import sys  # pylint: disable=import-outside-toplevel

        # Import getpass to read the password
        import getpass  # pylint: disable=import-outside-toplevel

        # Import the exceptions so they can be caught on error
        # fmt: off
        from pysros.exceptions import ModelProcessingError  # pylint: disable=import-error disable=import-outside-toplevel
        # fmt: on

        # Make sure we have the right number of arguments, the host can
        # be an IP address or a hostname
        if len(sys.argv) != 2:
            print("Usage:", sys.argv[0], "username@host")
            sys.exit(2)

        # Split the username and host arguments
        username_host = sys.argv[1].split("@")
        if len(username_host) != 2:
            print("Usage:", sys.argv[0], "username@host")
            sys.exit(2)

        # Get the password
        password = getpass.getpass()

        # The try statement and except statements allow an
        # operation attempt with specific error conditions handled
        # gracefully
        try:
            connection_object = connect(
                username=username_host[0],
                host=username_host[1],
                password=password,
            )
            return connection_object

        # This first exception is described in the pysros.management.connect
        # method and references errors that occur during the creation of the
        # Connection object.  If the provided exception is raised during
        # the execution of the connect method, the information provided in
        # that exception is loaded into the runtime_error variable for use.
        except RuntimeError as runtime_error:
            print(
                "Failed to connect during the creation of the Connection object."
            )
            print("Error:", runtime_error, end="")
            print(".")
            sys.exit(100)

        # This second exception is described in the pysros.management.connect
        # method and references errors that occur whilst compiling the YANG
        # modules that have been obtained into a model-driven schema.  If the
        # provided exception is raised during the execution of the connect
        # method, the information provided in that exception is loaded into
        # the model_proc_error variable for use.
        except ModelProcessingError as model_proc_error:
            print("Failed to compile YANG modules.")
            print("Error:", model_proc_error, end="")
            print(".")
            sys.exit(101)

    return connection_object


def getter(connection, path):
    """Obtain modeled data from a device."""
    import sys  # pylint: disable=import-outside-toplevel

    try:
        output = connection.running.get(path)
    except RuntimeError as runtime_error:
        print("Failed to obtain the data from the device:", runtime_error)
        sys.exit(200)
    except InvalidPathError as invalid_path_error:
        print("Failed to obtain the data from the device:", invalid_path_error)
        sys.exit(201)
    except SrosMgmtError as sros_management_error:
        print(
            "Failed to obtain the data from the device:", sros_management_error
        )
        sys.exit(202)
    except TypeError as type_error:
        print("Failed to obtain the data from the device:", type_error)
        sys.exit(203)
    except InternalError as internal_error:
        print("Failed to obtain the data from the device:", internal_error)
        sys.exit(204)
    except Exception as generic_exception:  # pylint: disable=broad-except
        print("Failed to obtain the data from the device:", generic_exception)
        sys.exit(205)
    return output


def main():
    """Main function."""
    connection = get_connection()
    logs = getter(connection, "/nokia-state:state/log/log-events")
    connection.disconnect()
    events = []
    for group in logs.keys():
        for event in logs[group].keys():
            if logs[group][event]["statistics"]["count"].data != 0:
                eventid = logs[group][event]["event-id"].data
                event = logs[group][event]["event"].data
                count = logs[group][event]["statistics"]["count"].data
                events.append((eventid, count, event))
    output_table(sort(events))


def output_table(events):
    """Define and output the SR OS styled table."""
    cols = [(15, "eventId"), (20, "Occurrences"), (44, "EventName")]
    table = Table("Event Summary", columns=cols, showCount="event categories")
    table.print(events)


def sort(events):
    """Sort a list of events by the number of occurrences."""
    return sorted(events, key=lambda x: x[1], reverse=True)


if __name__ == "__main__":
    main()
