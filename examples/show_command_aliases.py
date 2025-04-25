#!/usr/bin/env python3

### show_command_aliases.py
#   Copyright 2021-2025 Nokia
###

# pylint: disable=import-error, import-outside-toplevel, line-too-long, too-many-branches, too-many-locals, too-many-statements

"""
Tested on: SR OS 24.3.R1

Show command aliaseses.

Execution on SR OS
    usage: pyexec bin/show_command_aliases.py
Execution on remote machine
    usage: python show_command_aliases.py username@host
Execution on remote machine if show_command_aliases.py is executable
     usage: ./show_command_aliaess.py username@host

This application shows the configured command aliases.

Add the following alias so that the Python application can be run as a
native MD-CLI command.

/configure python { python-script "show-command-aliases" admin-state enable }
/configure python { python-script "show-command-aliases" urls ["cf3:bin/show_command_aliases.py"] }
/configure python { python-script "show-command-aliases" version python3 }
/configure system { management-interface cli md-cli environment command-alias alias "command-aliases" }
/configure system { management-interface cli md-cli environment command-alias alias "command-aliases" admin-state enable }
/configure system { management-interface cli md-cli environment command-alias alias "command-aliases" description "Show command aliases" }
/configure system { management-interface cli md-cli environment command-alias alias "command-aliases" python-script "show-command-aliases" }
/configure system { management-interface cli md-cli environment command-alias alias "command-aliases" mount-point "/show" }
"""

# Import sys for parsing arguments and returning specific exit codes
import sys

# Import the connect and sros methods from the management pySROS submodule
from pysros.management import connect, sros


def usage():
    """Print the usage"""

    if sros():
        print("")
        # Remove the first hyphen that is added in the python-script "show-command-aliases" name
        print("", sys.argv[0].replace("w-c", "w c"))
    else:
        print("Usage:", sys.argv[0], "username@host")


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


def show_command_aliases_output(connection_object):
    """Main function for the show_command_aliases command"""

    bright_blue = "\033[1;34m"
    bright_cyan = "\033[1;36m"
    bright_green = "\033[1;32m"
    bright_red = "\033[1;31m"
    bright_yellow = "\033[1;33m"
    reset_color = "\033[0m"

    # Get environment configuration data
    try:
        alias_config = connection_object.running.get(
            "/nokia-conf:configure/system/management-interface/cli/md-cli/environment/command-alias"
        )
    except LookupError as lookup_error:
        print("Failed to get enviroment configuration.")
        print("Error:", lookup_error, end="")
        print(".")
        sys.exit(102)

    # Get python configuration and state data.  It doesn't matter it there is
    # none since it's only referenced if a Python alias is configured in
    # alias_config.
    python_config = connection_object.running.get(
        "/nokia-conf:configure/python"
    )
    python_state = connection_object.running.get("/nokia-state:state/python")

    # Make sure that aliases are actually configured
    if "alias" not in alias_config:
        print(
            "Failed to get alias configuration.  Are any aliases configured?"
        )
        sys.exit(103)

    # Print the header
    print("")
    print("=" * 80)

    # Print the aliases
    is_first_item = True
    num_admin_up_aliases = 0
    num_admin_down_aliases = 0
    num_oper_down_aliases = 0
    for alias_name in sorted(alias_config["alias"]):
        # Only print the separator after the first item
        if is_first_item:
            is_first_item = False
        else:
            print("-" * 80)

        # Print the alias name and admin-state depending on its color
        if (
            "admin-state" in alias_config["alias"][alias_name]
            and str(alias_config["alias"][alias_name]["admin-state"])
            == "enable"
        ):
            print(
                "Alias name    : "
                + bright_blue
                + alias_name
                + reset_color
                + " ("
                + bright_green
                + "enabled"
                + reset_color,
                end="",
            )
            num_admin_up_aliases += 1
        else:
            print(
                "Alias name    : "
                + bright_blue
                + alias_name
                + reset_color
                + " ("
                + bright_yellow
                + "disabled"
                + reset_color,
                end="",
            )
            num_admin_down_aliases += 1

        # Print the cli-command or python-script depending on which one is configured
        if "cli-command" in alias_config["alias"][alias_name]:
            print(")")
        elif "python-script" in alias_config["alias"][alias_name]:
            if (
                str(
                    python_state["python-script"][
                        str(alias_config["alias"][alias_name]["python-script"])
                    ]["oper-state"]
                )
                == "up"
            ):
                print("/" + bright_green + "up" + reset_color + ")")
            else:
                print(
                    "/"
                    + bright_red
                    + str(
                        python_state["python-script"][
                            str(
                                alias_config["alias"][alias_name][
                                    "python-script"
                                ]
                            )
                        ]["oper-state"]
                        + reset_color
                        + ")"
                    )
                )
                num_oper_down_aliases += 1

        # Print the description if it exists
        if "description" in alias_config["alias"][alias_name]:
            print(
                "Description   : "
                + str(alias_config["alias"][alias_name]["description"])
            )

        # Print the cli-command or python-script depending on which one is configured
        if "cli-command" in alias_config["alias"][alias_name]:
            print(
                "CLI command   : "
                + str(alias_config["alias"][alias_name]["cli-command"])
            )
        elif "python-script" in alias_config["alias"][alias_name]:
            # Clean up and split URLs
            urls = str(
                python_config["python-script"][
                    str(alias_config["alias"][alias_name]["python-script"])
                ]["urls"]
            )
            urls = urls.replace("[", "")
            urls = urls.replace("]", "")
            urls = urls.replace("'", "")
            urls = urls.replace(",", "\n              :")
            print("Python script : " + urls)

        # Print the command availability as the mount point and alias name together
        is_first_mount_point = True
        for mount_point in sorted(
            alias_config["alias"][alias_name]["mount-point"]
        ):
            if is_first_mount_point:
                is_first_mount_point = False
                if mount_point == "global":
                    print(
                        "Availability  : "
                        + bright_cyan
                        + alias_name
                        + reset_color
                        + " (global)"
                    )
                else:
                    print(
                        "Availability  : "
                        + bright_cyan
                        + mount_point.replace("/", "")
                        + " "
                        + alias_name
                        + reset_color
                    )
            else:
                if mount_point == "global":
                    print(
                        "              : "
                        + bright_cyan
                        + alias_name
                        + reset_color
                        + " (global)"
                    )
                else:
                    print(
                        "              : "
                        + bright_cyan
                        + mount_point.replace("/", "")
                        + " "
                        + alias_name
                        + reset_color
                    )

    # Print the total aliases
    print("-" * 80)
    print(
        "Total aliases : "
        + bright_blue
        + str(num_admin_up_aliases + num_admin_down_aliases)
        + reset_color
        + " ("
        + bright_green
        + str(num_admin_up_aliases)
        + reset_color
        + " enabled, "
        + bright_yellow
        + str(num_admin_down_aliases)
        + reset_color
        + " disabled, "
        + bright_red
        + str(num_oper_down_aliases)
        + reset_color
        + " down)"
    )

    # Print the closing deliminator
    print("=" * 80)


def get_connection_with_argv():
    """Parse arguments and get a connection"""

    # Use the sros() function to determine if the application is executed
    # locally on an SR OS device, or remotely so that the same application
    # can be developed to run locally or remotely.

    # The application is running locally
    if sros():
        # Parse the arguments for an optional language parameter
        if len(sys.argv) > 1:
            usage()
            sys.exit(2)

        # Get a local Connection object
        connection_object = connect()  # pylint: disable=missing-kwoa

    # The application is running remotely
    else:
        # Import getpass to read the password
        import getpass

        # Parse the arguments for connection and optional language parameters
        if len(sys.argv) != 2:
            usage()
            sys.exit(2)

        # Split the username and host arguments, the host can be an IP
        # address or a hostname
        username_host = sys.argv[1].split("@")

        # Get the password
        password = getpass.getpass(
            prompt="Password (press Enter to use SSH key): "
        )

        # Get a remote Connection object
        connection_object = get_remote_connection(
            my_username=username_host[0],
            my_host=username_host[1],
            my_password=password,
        )

    return connection_object


if __name__ == "__main__":
    my_connection_object = get_connection_with_argv()
    show_command_aliases_output(connection_object=my_connection_object)
