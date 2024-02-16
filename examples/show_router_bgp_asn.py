#!/usr/bin/env python3

### show_router_bgp_asn.py
#   Copyright 2021 Nokia
###

# pylint: disable=import-error, import-outside-toplevel, line-too-long, too-many-branches, too-many-locals, too-many-statements

"""
Tested on: SR OS 23.10.R2

Show all BGP peers for an ASN.

Execution on SR OS
    usage: pyexec bin/show_router_bgp_asn.py <number>
Execution on remote machine
    usage: python show_router_bgp_asn.py username@host <number>
Execution on remote machine if show_router_bgp_asn.py is executable
    usage: ./show_router_bgp_asn.py username@host <number>

Add the following alias so that the Python application can be run as a
native MD-CLI command.

/configure python { python-script "show-router-bgp-asn" admin-state enable }
/configure python { python-script "show-router-bgp-asn" urls ["cf3:bin/show_router_bgp_asn.py"] }
/configure python { python-script "show-router-bgp-asn" version python3 }

/configure system { management-interface cli md-cli environment command-alias alias "asn" }
/configure system { management-interface cli md-cli environment command-alias alias "asn" admin-state enable }
/configure system { management-interface cli md-cli environment command-alias alias "asn" description "Show all BGP peers for an ASN" }
/configure system { management-interface cli md-cli environment command-alias alias "asn" python-script "show-router-bgp-asn" }
/configure system { management-interface cli md-cli environment command-alias alias "asn" mount-point "/show router bgp" }
"""

# Import sys for parsing arguments and returning specific exit codes
import sys

# Import datetime to get and display the date and time
import datetime

# Import the connect and sros methods from the management pySROS submodule
from pysros.management import connect, sros


def usage():
    """Print the usage"""

    if sros():
        print("")
        # Remove hyphens that are added in the python-script "show-router-bgp-asn" name
        print("", sys.argv[0].replace("-", " "), "[<keyword>]")
    else:
        print("Usage:", sys.argv[0], "username@host [<number>]")
    print(" <number>  - <1..4294967295>")


def get_remote_connection(my_username, my_host, my_password):
    """Function definition to obtain a Connection object to a remote SR OS device
    and access model-driven information"""

    # Import the exceptions so they can be caught on error
    # fmt: off
    from pysros.exceptions import ModelProcessingError
    # fmt: on

    # The try statement coupled with the except statements allow an
    # operation(s) to be attempted and specific error conditions handled
    # gracefully
    try:
        remote_connection_object = connect(
            username=my_username, host=my_host, password=my_password
        )
        return remote_connection_object

    # This first exception is described in the pysros.management.connect
    # method and references errors that occur during the creation of the
    # Connection object.  If the provided exception is raised during
    # the execution of the connect method the information provided in
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
    # method the information provided in that exception is loaded into
    # the model_proc_error variable for use.
    except ModelProcessingError as model_proc_error:
        print("Failed to compile YANG modules.")
        print("Error:", model_proc_error, end="")
        print(".")
        sys.exit(101)

    return remote_connection_object


def show_router_bgp_asn_output(connection_object, asn):
    """Main function for the show_router_bgp_asn command"""

    bright_cyan = "\u001b[36;1m"
    bright_green = "\u001b[32;1m"
    bright_red = "\u001b[31;1m"
    bright_yellow = "\u001b[33;1m"
    reset_color = "\u001b[0m"
    bgp_stats = None

    oper_name = connection_object.running.get(
        "/nokia-state:state/system/oper-name"
    )

    # Get BGP configuration data
    try:
        bgp_config = connection_object.running.get(
            '/nokia-conf:configure/router[router-name="Base"]/bgp/neighbor'
        )
    except LookupError as lookup_error:
        print(
            "Failed to get BGP neighbor configuration.  Are any neighbors configured?"
        )
        print("Error:", lookup_error, end="")
        print(".")
        sys.exit(102)

    # Make sure we have all of the configuration and state that we need
    for neighbor in bgp_config:
        # The peer-as can be configured under the neighbor or group
        # Check to see if the peer-as exists in the neighbor first
        if "peer-as" not in bgp_config[neighbor]:
            # If not, try to get the peer-as from the neighbor's group
            try:
                bgp_config[neighbor][
                    "peer-as"
                ] = connection_object.running.get(
                    "/nokia-conf:configure/router[router-name=Base]/bgp/group[group-name=%s]/peer-as"
                    % bgp_config[neighbor]["group"]
                )
            except LookupError as lookup_error:
                print(
                    "Failed to get the BGP peer AS configuration for neighbor "
                    + str(neighbor)
                    + ".  Does the neighbor or group have a 'peer-as' configured?"
                )
                print("Error:", lookup_error, end="")
                print(".")
                sys.exit(103)

        # Get state if the ASN is all
        if asn == 0 and bgp_stats is None:
            bgp_stats = connection_object.running.get(
                '/nokia-state:state/router[router-name="Base"]/bgp/neighbor'
            )
        # Get state if the ASN is configured, only need to do this the first
        # time the ASN is found
        elif (
            int(asn) == bgp_config[neighbor]["peer-as"].data
            and bgp_stats is None
        ):
            bgp_stats = connection_object.running.get(
                '/nokia-state:state/router[router-name="Base"]/bgp/neighbor'
            )

    # Get the current date and time
    now = datetime.datetime.now()

    # Print the header
    print("")
    print("=" * 80)
    if asn == 0:
        print(
            "BGP Peers for",
            oper_name,
            now.strftime("%Y-%m-%d %H:%M:%S"),
            now.astimezone().tzinfo,
        )
    else:
        print(
            "BGP Peers for AS",
            asn,
            oper_name,
            now.strftime("%Y-%m-%d %H:%M:%S"),
            now.astimezone().tzinfo,
        )
    print("=" * 80)
    # Longest possible IP address is 45 characters
    print("{0:<45} {1}".format("Neighbor", "Last Up/Down Time (Transitions)"))
    print("Description")
    print("Group")
    print(
        "{0:<13} {1:<13}/{2:<17}".format("ASN", "Messages Rcvd", "In Queue"),
        end="",
    )
    print(
        " State|"
        + bright_cyan
        + "Rcv"
        + reset_color
        + "/"
        + bright_green
        + "Act"
        + reset_color
        + "/Sent (Addr Family)"
    )
    print("{0:<13} {1:<13}/{2:<13}".format("", "Messages Sent", "Out Queue"))
    print("-" * 80)

    # Print each neighbor's info
    num_up_neighbors = 0
    num_down_neighbors = 0
    num_disabled_neighbors = 0
    for neighbor in sorted(bgp_config):
        if asn == 0 or int(asn) == bgp_config[neighbor]["peer-as"].data:
            # Print line 1
            print(
                "{0:<45} {1} ({2})".format(
                    neighbor,
                    bgp_stats[neighbor]["statistics"]["last-established-time"],
                    bgp_stats[neighbor]["statistics"][
                        "established-transitions"
                    ],
                )
            )

            # Print line 2
            if "description" in bgp_config[neighbor]:
                print(bgp_config[neighbor]["description"])
            else:
                print("(no description configured)")

            # Print line 3
            print(bgp_config[neighbor]["group"])

            # Print line 4
            print(
                "{0:<13} {1:>13}/{2:<17} ".format(
                    str(bgp_config[neighbor]["peer-as"]),
                    str(
                        bgp_stats[neighbor]["statistics"]["received"][
                            "messages"
                        ]
                    ),
                    str(
                        bgp_stats[neighbor]["statistics"]["received"]["queues"]
                    ),
                ),
                end="",
            )
            if (
                str(bgp_stats[neighbor]["statistics"]["session-state"])
                == "Established"
            ):
                num_up_neighbors += 1
                if (
                    str(bgp_stats[neighbor]["statistics"]["negotiated-family"])
                    == "['IPv4']"
                ):
                    print(
                        bright_cyan
                        + str(
                            bgp_stats[neighbor]["statistics"]["family-prefix"][
                                "ipv4"
                            ]["received"]
                        )
                        + reset_color
                        + "/"
                        + bright_green
                        + str(
                            bgp_stats[neighbor]["statistics"]["family-prefix"][
                                "ipv4"
                            ]["received"]
                        )
                        + reset_color
                        + "/"
                        + str(
                            bgp_stats[neighbor]["statistics"]["family-prefix"][
                                "ipv4"
                            ]["sent"]
                        )
                        + " (IPv4)"
                    )
                elif (
                    str(bgp_stats[neighbor]["statistics"]["negotiated-family"])
                    == "['IPv6']"
                ):
                    print(
                        bright_cyan
                        + str(
                            bgp_stats[neighbor]["statistics"]["family-prefix"][
                                "ipv6"
                            ]["received"]
                        )
                        + reset_color
                        + "/"
                        + bright_green
                        + str(
                            bgp_stats[neighbor]["statistics"]["family-prefix"][
                                "ipv6"
                            ]["received"]
                        )
                        + reset_color
                        + "/"
                        + str(
                            bgp_stats[neighbor]["statistics"]["family-prefix"][
                                "ipv6"
                            ]["sent"]
                        )
                        + " (IPv6)"
                    )
                else:
                    print(
                        bright_green
                        + +bgp_stats[neighbor]["statistics"]["session-state"]
                        + reset_color
                    )
            elif (
                str(bgp_stats[neighbor]["statistics"]["session-state"])
                == "disabled"
            ):
                num_disabled_neighbors += 1
                print(
                    bright_red
                    + "Disabled"
                    + " ("
                    + str(bgp_stats[neighbor]["statistics"]["last-event"])
                    + ")"
                    + reset_color
                )
            elif (
                str(bgp_stats[neighbor]["statistics"]["session-state"])
                == "Idle (shutdown)"
            ):
                num_down_neighbors += 1
                print(
                    bright_yellow
                    + str(bgp_stats[neighbor]["statistics"]["session-state"])
                    + reset_color
                )
            else:
                num_down_neighbors += 1
                print(
                    bright_yellow
                    + str(bgp_stats[neighbor]["statistics"]["session-state"])
                    + " ("
                    + str(bgp_stats[neighbor]["statistics"]["last-event"])
                    + ")"
                    + reset_color
                )

            # Print line 5
            print(
                "{0:<13} {1:>13}/{2:<13}".format(
                    "",
                    str(bgp_stats[neighbor]["statistics"]["sent"]["messages"]),
                    str(bgp_stats[neighbor]["statistics"]["sent"]["queues"]),
                )
            )

    # Print the total neighbors
    print("-" * 80)
    print(
        "Total neighbors : "
        + bright_cyan
        + str(num_up_neighbors + num_down_neighbors + num_disabled_neighbors)
        + reset_color
        + " ("
        + bright_green
        + str(num_up_neighbors)
        + reset_color
        + " up, "
        + bright_yellow
        + str(num_down_neighbors)
        + reset_color
        + " down, "
        + bright_red
        + str(num_disabled_neighbors)
        + reset_color
        + " disabled)"
    )

    # Print the closing deliminator
    print("=" * 80)


def get_connection_with_argv():
    """Parse arguments and get a connection"""

    # The asn is optional, so we need a default value
    parsed_asn = 0

    # Use the sros() function to determine if the application is executed
    # locally on an SR OS device, or remotely so that the same application
    # can be developed to run locally or remotely.

    # The application is running locally
    if sros():
        # Parse the arguments for an optional ASN parameter
        if len(sys.argv) > 2:
            usage()
            sys.exit(2)

        # Get the ASN
        if len(sys.argv) == 2:
            # Check ASN type and range
            if sys.argv[1].isdigit():
                if int(sys.argv[1]) < 1 or int(sys.argv[1]) > 4294967295:
                    usage()
                    sys.exit(2)
            else:
                usage()
                sys.exit(2)
            parsed_asn = sys.argv[1]

        # Get a local Connection object
        connection_object = connect()  # pylint: disable=missing-kwoa

    # The application is running remotely
    else:
        # Import getpass to read the password
        import getpass

        # Parse the arguments for connection and optional ASN parameter
        if len(sys.argv) > 3 or len(sys.argv) < 2:
            usage()
            sys.exit(2)

        if len(sys.argv) == 3:
            # Check ASN type and range
            if sys.argv[2].isdigit():
                if int(sys.argv[2]) < 1 or int(sys.argv[2]) > 4294967295:
                    usage()
                    sys.exit(2)
            else:
                usage()
                sys.exit(2)
            parsed_asn = sys.argv[2]

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

    return connection_object, parsed_asn


if __name__ == "__main__":
    my_connection_object, my_asn = get_connection_with_argv()
    show_router_bgp_asn_output(
        connection_object=my_connection_object, asn=my_asn
    )
