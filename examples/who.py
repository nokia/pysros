#!/usr/bin/env python3

### who.py
#   Copyright 2024 Nokia
###

# pylint: disable=import-error, import-outside-toplevel, line-too-long, too-many-branches, too-many-locals, too-many-statements

"""
Tested on: SR OS 23.10.R2

Show who is logged on.

Execution on SR OS
    usage: pyexec bin/who.py
    usage: pyexec bin/who.py am i
Execution on remote machine
    usage: python who.py username@host
    usage: python who.py username@host am i
Execution on remote machine if who.py is executable
    usage: ./who.py username@host
    usage: ./who.py username@host am i

Add the following alias so that the Python application can be run as
a native MD-CLI command.

/configure python { python-script "who" admin-state enable }
/configure python { python-script "who" urls ["cf3:bin/who.py"] }
/configure python { python-script "who" version python3 }
/configure system { management-interface cli md-cli environment command-alias alias "who" }
/configure system { management-interface cli md-cli environment command-alias alias "who" admin-state enable }
/configure system { management-interface cli md-cli environment command-alias alias "who" description "Show who is logged on" }
/configure system { management-interface cli md-cli environment command-alias alias "who" python-script "who" }
/configure system { management-interface cli md-cli environment command-alias alias "who" mount-point global }
"""

# Import sys for parsing arguments and returning specific exit codes
import sys

# Import the connect and sros methods from the management pySROS submodule
from pysros.management import connect, sros


def usage():
    """Print the usage"""

    print("Usage:", sys.argv[0], "username@host [am i]")


def get_remote_connection(my_username, my_host, my_password):
    """Function definition to obtain a Connection object to a remote SR OS device
    and access model-driven information"""

    # Import the exceptions so they can be caught on error
    # fmt: off
    from pysros.exceptions import ModelProcessingError
    # fmt: on

    # The try statement and except statements allow an operation
    # attempt with specific error conditions handled gracefully
    try:
        remote_connection_object = connect(
            username=my_username, host=my_host, password=my_password
        )
        return remote_connection_object

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

    return remote_connection_object


def get_connection_with_argv():
    """Parse arguments and get a connection"""

    # The "am i" is optional, so we need a default value
    parsed_arg = 0

    # Use the sros() function to determine if the application is executed
    # locally on an SR OS device, or remotely so that the same application
    # can be developed to run locally or remotely.

    # The application is running locally
    if sros():
        # Like who(1), we don't really care what the arguments are
        # 'am i' or 'mom likes' are usual
        if len(sys.argv) > 2:
            parsed_arg = 1

        # Get a local Connection object
        connection_object = connect()  # pylint: disable=missing-kwoa

    # The application is running remotely
    else:
        # Import getpass to read the password
        import getpass

        # Parse the arguments for an optional argument
        if len(sys.argv) < 2:
            usage()
            sys.exit(2)

        # Like who(1), we don't really care what the arguments are,
        # 'am i' or 'mom likes' are usual
        if len(sys.argv) > 2:
            parsed_arg = 1

        # Split the username and host arguments, the host can be an IP
        # address or a hostname
        username_host = sys.argv[1].split("@")
        if len(username_host) != 2:
            usage()
            sys.exit(2)

        # Get the password
        password = getpass.getpass()

        # Get a remote Connection object
        connection_object = get_remote_connection(
            my_username=username_host[0],
            my_host=username_host[1],
            my_password=password,
        )

    return connection_object, parsed_arg


def who_output(connection_object, arg):
    """Main function for the who command"""

    # Get the users state
    users = connection_object.running.get("/nokia-state:state/users/session")

    # Step through the sessions
    for session_id in sorted(users):
        if "login-time" in users[session_id]:
            # Check for arg that means to show the current session
            if (
                arg == 1
                and str(users[session_id]["current-active-session"]) == "False"
            ):
                continue

            # Print session info in who(1) format
            # GNU who displays "%-8s" for user, use same format
            print(
                "{0:8.8} {1}/{2}\t{3}".format(
                    str(users[session_id]["user"]),
                    str(users[session_id]["connection-type"]),
                    str(session_id),
                    str(users[session_id]["login-time"]),
                ),
                end="",
            )

            if "connection-ip" in users[session_id]:
                print(
                    " ("
                    + str(users[session_id]["router-instance"])
                    + "/"
                    + str(users[session_id]["connection-ip"])
                    + ")"
                )
            else:
                print()


if __name__ == "__main__":
    my_connection_object, my_arg = get_connection_with_argv()
    who_output(connection_object=my_connection_object, arg=my_arg)
