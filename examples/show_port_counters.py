#!/usr/bin/env python3

### show_port_counters.py
#   Copyright 2021 Nokia
###

# pylint: disable=import-error, import-outside-toplevel, line-too-long, too-many-branches, too-many-locals, too-many-statements

"""
Tested on: SR OS 22.2.R1

Show port counters.

Execution on SR OS
    usage: pyexec show_port_counters.py [<keyword>]
Execution on remote machine
    usage: python show_port_counters.py username@host [<keyword>]
Execution on remote machine if show_port_counters.py is executable
     usage: ./show_port_counters.py username@host [<keyword>]

This application to display system information demonstrates how to parse
different arguments depending on if the application is running locally or
remotely.  It also demonstrates how to print table headers and element names
in a different language.

Add the following alias so that the Python application can be run as a
native MD-CLI command.

/configure python { python-script "show-port-counters" admin-state enable }
/configure python { python-script "show-port-counters" urls ["cf3:show_port_counters.py"]
/configure python { python-script "show-port-counters" version python3 }
/configure system { management-interface cli md-cli environment command-alias alias "counters" }
/configure system { management-interface cli md-cli environment command-alias alias "counters" admin-state enable }
/configure system { management-interface cli md-cli environment command-alias alias "counters" description "Show port counters" }
/configure system { management-interface cli md-cli environment command-alias alias "counters" python-script "show-port-counters" }
/configure system { management-interface cli md-cli environment command-alias alias "counters" mount-point "/show port" }
"""

# Import sys for parsing arguments and returning specific exit codes
import sys

# Import datetime to get and display the date and time
import datetime

# Import the connect and sros methods from the management pySROS submodule
from pysros.management import connect, sros

# Define local language strings
local_str = {
    "supported languages": {
        "chinese": "??????",
        "english": "English",
        "french": "Fran??ais",
        "japanese": "?????????",
        "russian": "??????????????",
        "slovak": "Slovensk??",
        "spanish": "Espa??ol",
        "turkish": "T??rk??e",
    },
    "spacer": {
        "chinese": "\u3000",
        "english": " ",
        "french": " ",
        "japanese": "\u3000",
        "russian": " ",
        "slovak": " ",
        "spanish": " ",
        "turkish": " ",
    },
    "Port Statistics for": {
        "chinese": "??????????????????",
        "english": "Port Statistics for",
        "french": "Statistiques pour le Port",
        "japanese": "?????????????????????",
        "russian": "???????????????????? ??????????",
        "slovak": "??tatistiky Porto pre",
        "spanish": "Estad??sticas del Puerto",
        "turkish": "Port ??statistikleri ??zeti",
    },
    "Port": {
        "chinese": "??????",
        "english": "Port",
        "french": "Port",
        "japanese": "?????????",
        "russian": "????????",
        "slovak": "Port",
        "spanish": "Puerto",
        "turkish": "Port",
    },
    "description": {
        "chinese": "??????",
        "english": "Description",
        "french": "Description",
        "japanese": "??????",
        "russian": "????????????????",
        "slovak": "Popis",
        "spanish": "Descripci??n",
        "turkish": "Betimleme",
    },
    "oper-state": {
        "chinese": "??????",
        "english": "Operational state",
        "french": "Etat op??rationnel",
        "japanese": "??????",
        "russian": "???????????????????????? ????????????",
        "slovak": "Stav portu",
        "spanish": "Estado operacional",
        "turkish": "Operasyonel durum",
    },
    "counter-discontinuity-time": {
        "chinese": "??????????????????",
        "english": "Counter discontinuity time",
        "french": "Compteur de temps d???interruption",
        "japanese": "???????????????????????????",
        "russian": "?????????????? ??????????????????????",
        "slovak": "Celkov?? trvanie v??padkov po????tadla",
        "spanish": "Tiempo desde ??ltima discontinuidad en contadores",
        "turkish": "Saya?? s??reksizlik zaman??",
    },
    "last-cleared-time": {
        "chinese": "??????????????????",
        "english": "Last cleared time",
        "french": "Derni??re heure de remise ?? z??ro",
        "japanese": "?????????????????????",
        "russian": "??????????-????????????.-????????????",
        "slovak": "??as posledn??ho vy??istenia",
        "spanish": "Hora del ??ltimo borrado",
        "turkish": "Son temizlenme zaman??",
    },
    "in-discards": {
        "chinese": "???????????????",
        "english": "In discards",
        "french": "Supprim??s en entr??e",
        "japanese": "???????????????",
        "russian": "????. ??????????????????????",
        "slovak": "Zahodenia na vstupe",
        "spanish": "Descartes en entrada",
        "turkish": "Giren at??lm????lar",
    },
    "in-errors": {
        "chinese": "???????????????",
        "english": "In errors",
        "french": "Erreurs en entr??e",
        "japanese": "??????????????????",
        "russian": "????. ????????????",
        "slovak": "Chyby na vstupe",
        "spanish": "Errores en entrada",
        "turkish": "Giren hatal??lar ",
    },
    "in-octets": {
        "chinese": "?????????????????????",
        "english": "In octets",
        "french": "Octets entrant",
        "japanese": "????????????????????????",
        "russian": "????. ??????????????",
        "slovak": "Oktety na vstupe",
        "spanish": "Octetos en entrada",
        "turkish": "Giren oktetler",
    },
    "in-packets": {
        "chinese": "????????????????????????",
        "english": "In packets",
        "french": "Paquets entrant",
        "japanese": "?????????????????????",
        "russian": "????. ??????????????",
        "slovak": "Pakety na vstupe",
        "spanish": "Paquetes en entrada",
        "turkish": "Giren paketler",
    },
    "in-unknown-protocol-discards": {
        "chinese": "???????????????????????????",
        "english": "In unknown protocol discards",
        "french": "Protocole inconnu supprim?? en entr??e",
        "japanese": "????????????????????????????????????",
        "russian": "????. ?????????????????????? ?????????????????????? ????????????????",
        "slovak": "Zahoden?? nezn??me protokoly na vstupe",
        "spanish": "Descartes por protocol desconocido en entrada",
        "turkish": "Giren bilinmeyen protokoll?? at??lm????lar",
    },
    "in-broadcast-packets": {
        "chinese": "??????????????????????????????",
        "english": "In broadcast packets",
        "french": "Paquets broadcast entrant",
        "japanese": "?????????????????????????????????????????????",
        "russian": "????. ?????????????????????????????????? ??????????????",
        "slovak": "Broadcast pakety na vstupe",
        "spanish": "Paquetes broadcast en entrada",
        "turkish": "Giren broadcast paketler",
    },
    "in-multicast-packets": {
        "chinese": "??????????????????????????????",
        "english": "In multicast packets",
        "french": "Paquets multicast entrant",
        "japanese": "??????????????????????????????????????????",
        "russian": "????. ???????????????????? ??????????????",
        "slovak": "Multicast pakety na vstupe",
        "spanish": "Paquetes multicast en entrada",
        "turkish": "Giren multicast paketler",
    },
    "in-unicast-packets": {
        "chinese": "??????????????????????????????",
        "english": "In unicast packets",
        "french": "Paquets unicast entrant",
        "japanese": "???????????????????????????????????????",
        "russian": "????. ?????????????? ??????????????",
        "slovak": "Unicast pakety na vstupe",
        "spanish": "Paquetes unicast en entrada",
        "turkish": "Giren unicast paketler",
    },
    "out-discards": {
        "chinese": "??????????????????",
        "english": "Out discards",
        "french": "Supprim??s en sortie",
        "japanese": "??????????????????",
        "russian": "??????. ??????????????????????",
        "slovak": "Zahodenia na v??stupe",
        "spanish": "Descartes en salida",
        "turkish": "????kan at??lm????lar",
    },
    "out-errors": {
        "chinese": "??????????????????",
        "english": "Out errors",
        "french": "Erreurs en sortie",
        "japanese": "?????????????????????",
        "russian": "??????. ????????????",
        "slovak": "Chyby na v??stupe",
        "spanish": "Errores en salida",
        "turkish": "????kan hatal??lar",
    },
    "out-octets": {
        "chinese": "????????????????????????",
        "english": "Out octets",
        "french": "Octets sortant",
        "japanese": "???????????????????????????",
        "russian": "??????. ??????????????",
        "slovak": "Oktety na v??stupe",
        "spanish": "Octetos en salida",
        "turkish": "????kan oktetler",
    },
    "out-packets": {
        "chinese": "???????????????????????????",
        "english": "Out packets",
        "french": "Paquets sortant",
        "japanese": "????????????????????????",
        "russian": "??????. ??????????????",
        "slovak": "Pakety na v??stupe",
        "spanish": "Paquetes en salida",
        "turkish": "????kan paketler",
    },
    "out-broadcast-packets": {
        "chinese": "?????????????????????????????????",
        "english": "Out broadcast packets",
        "french": "Paquets broadcast sortant",
        "japanese": "????????????????????????????????????????????????",
        "russian": "??????. ?????????????????????????????????? ??????????????",
        "slovak": "Broadcast pakety na v??stupe",
        "spanish": "Paquetes broadcast en salida",
        "turkish": "????kan broadcast paketler",
    },
    "out-multicast-packets": {
        "chinese": "?????????????????????????????????",
        "english": "Out multicast packets",
        "french": "Paquets multicast sortant",
        "japanese": "??????????????????????????????????????????",
        "russian": "??????. ???????????????????? ??????????????",
        "slovak": "Multicast pakety na v??stupe",
        "spanish": "Paquetes multicast en salida",
        "turkish": "????kan multicast paketler",
    },
    "out-unicast-packets": {
        "chinese": "?????????????????????????????????",
        "english": "Out unicast packets",
        "french": "Paquets unicast sortant",
        "japanese": "??????????????????????????????????????????",
        "russian": "??????. ?????????????? ??????????????",
        "slovak": "Unicast pakety na v??stupe",
        "spanish": "Paquetes unicast en salida",
        "turkish": "????kan unicast paketler",
    },
}


def usage():
    """Print the usage"""

    if sros():
        print("")
        # Remove hyphens that are added in the python-script "show-port-counters" name
        print("", sys.argv[0].replace("-", " "), "[<keyword>]")
    else:
        print("Usage:", sys.argv[0], "username@host [<keyword>]")
    print(
        " <keyword>  - (chinese|english|french|japanese|russian|slovak|spanish|turkish)"
    )
    print(" Default    - english")


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
        print("Failed to connect during the creation of the Connection object.")
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


def set_column_width(language):
    """Count the maximum column width based on the longest element name in the input data"""
    column_width = 0

    # Walk though local strings dict
    for k in local_str.items():
        # Check length of each string, and keep track of the longest one
        if len(k[1][language]) > column_width:
            column_width = len(k[1][language])
    return column_width


def print_row_with_spacing(spacer, column, name, value):
    """Print a row of output with the correct ASCII or UTF-8 spacing character"""

    if value == 0:
        return

    print(name, end="")

    # Print spaces
    num_spaces = column - len(name)
    while num_spaces > 0:
        print(spacer, end="")
        num_spaces -= 1

    print(" : " + str(value))


def show_port_counters_output(connection_object, language):
    """Main function for the show_port_counters command"""

    bright_green = "\u001b[32;1m"
    bright_red = "\u001b[31;1m"
    bright_yellow = "\u001b[33;1m"
    reset_color = "\u001b[0m"

    # Define local language oper-state strings and colors
    oper_state_str = {
        "diagnosing": {
            "chinese": bright_yellow + "diagnosing" + reset_color,
            "english": bright_yellow + "diagnosing" + reset_color,
            "french": bright_yellow + "diagnosing" + reset_color,
            "japanese": bright_yellow + "diagnosing" + reset_color,
            "russian": bright_yellow + "??????????????????????" + reset_color,
            "slovak": bright_yellow + "vyhodnocovan??" + reset_color,
            "spanish": bright_yellow + "en diagn??stico" + reset_color,
            "turkish": bright_yellow + "tan??lan??yor" + reset_color,
        },
        "down": {
            "chinese": bright_red + "down" + reset_color,
            "english": bright_red + "down" + reset_color,
            "french": bright_red + "down" + reset_color,
            "japanese": bright_red + "down" + reset_color,
            "russian": bright_red + "????????." + reset_color,
            "slovak": bright_red + "mimo prev??dzky" + reset_color,
            "spanish": bright_red + "down" + reset_color,
            "turkish": bright_red + "d??????k" + reset_color,
        },
        "failed": {
            "chinese": bright_red + "failed" + reset_color,
            "english": bright_red + "failed" + reset_color,
            "french": bright_red + "failed" + reset_color,
            "japanese": bright_red + "failed" + reset_color,
            "russian": bright_red + "????????????" + reset_color,
            "slovak": bright_red + "zlyhan??" + reset_color,
            "spanish": bright_red + "fallo" + reset_color,
            "turkish": bright_red + "ar??zal??" + reset_color,
        },
        "unknown": {
            "chinese": bright_red + "unknown" + reset_color,
            "english": bright_red + "unknown" + reset_color,
            "french": bright_red + "unknown" + reset_color,
            "japanese": bright_red + "unknown" + reset_color,
            "russian": bright_red + "????????????????????" + reset_color,
            "slovak": bright_red + "nezn??my" + reset_color,
            "spanish": bright_red + "desconocido" + reset_color,
            "turkish": bright_red + "bilinmeyen" + reset_color,
        },
        "up": {
            "chinese": bright_green + "up" + reset_color,
            "english": bright_green + "up" + reset_color,
            "french": bright_green + "up" + reset_color,
            "japanese": bright_green + "up" + reset_color,
            "russian": bright_green + "??????." + reset_color,
            "slovak": bright_green + "v prev??dzke" + reset_color,
            "spanish": bright_green + "up" + reset_color,
            "turkish": bright_green + "ayakta" + reset_color,
        },
    }

    # Get configuration and state data
    port_config = connection_object.running.get("/nokia-conf:configure/port")
    port_stats = connection_object.running.get("/nokia-state:state/port")
    oper_name = connection_object.running.get("/nokia-state:state/system/oper-name")

    # Get the current date and time
    now = datetime.datetime.now()

    # Print the port statistics
    print("")
    print("=" * 80)
    print(
        local_str["Port Statistics for"][language],
        oper_name,
        now.strftime("%Y-%m-%d %H:%M:%S"),
        now.astimezone().tzinfo,
    )
    print("=" * 80)

    width = set_column_width(language)
    is_first_item = True
    for port in sorted(port_stats):
        # Only print the separator after the first item
        if is_first_item:
            is_first_item = False
        else:
            print("-" * 80)

        # Print row header
        print_row_with_spacing(
            local_str["spacer"][language], width, local_str["Port"][language], str(port)
        )

        # Print oper-state values
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["oper-state"][language],
            oper_state_str[str(port_stats[port]["oper-state"])][language],
        )

        # Print description
        if port in port_config and "description" in port_config[port]:
            print_row_with_spacing(
                local_str["spacer"][language],
                width,
                local_str["description"][language],
                str(port_config[port]["description"].data),
            )

            # counter-discontinuity-time is a conditional state leaf, check existence
            if "counter-discontinuity-time" in port_stats[port]["statistics"]:
                print_row_with_spacing(
                    local_str["spacer"][language],
                    width,
                    local_str["counter-discontinuity-time"][language],
                    str(
                        port_stats[port]["statistics"][
                            "counter-discontinuity-time"
                        ].data
                    ),
                )

            # last-cleared-time is a conditional state leaf, check existence
            if "last-cleared-time" in port_stats[port]["statistics"]:
                print_row_with_spacing(
                    local_str["spacer"][language],
                    width,
                    local_str["last-cleared-time"][language],
                    str(port_stats[port]["statistics"]["last-cleared-time"].data),
                )

            # Print input statistics
            print_row_with_spacing(
                local_str["spacer"][language],
                width,
                local_str["in-discards"][language],
                port_stats[port]["statistics"]["in-discards"].data,
            )
            print_row_with_spacing(
                local_str["spacer"][language],
                width,
                local_str["in-errors"][language],
                port_stats[port]["statistics"]["in-errors"].data,
            )
            print_row_with_spacing(
                local_str["spacer"][language],
                width,
                local_str["in-octets"][language],
                port_stats[port]["statistics"]["in-octets"].data,
            )
            print_row_with_spacing(
                local_str["spacer"][language],
                width,
                local_str["in-packets"][language],
                port_stats[port]["statistics"]["in-packets"].data,
            )
            print_row_with_spacing(
                local_str["spacer"][language],
                width,
                local_str["in-unknown-protocol-discards"][language],
                port_stats[port]["statistics"]["in-unknown-protocol-discards"].data,
            )
            print_row_with_spacing(
                local_str["spacer"][language],
                width,
                local_str["in-broadcast-packets"][language],
                port_stats[port]["statistics"]["in-broadcast-packets"].data,
            )
            print_row_with_spacing(
                local_str["spacer"][language],
                width,
                local_str["counter-discontinuity-time"][language],
                str(port_stats[port]["statistics"]["counter-discontinuity-time"].data),
            )

        # last-cleared-time is a conditional state leaf, check existence
        if "last-cleared-time" in port_stats[port]["statistics"]:
            print_row_with_spacing(
                local_str["spacer"][language],
                width,
                local_str["last-cleared-time"][language],
                str(port_stats[port]["statistics"]["last-cleared-time"].data),
            )

        # Print input statistics
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["in-discards"][language],
            port_stats[port]["statistics"]["in-discards"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["in-errors"][language],
            port_stats[port]["statistics"]["in-errors"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["in-octets"][language],
            port_stats[port]["statistics"]["in-octets"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["in-packets"][language],
            port_stats[port]["statistics"]["in-packets"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["in-unknown-protocol-discards"][language],
            port_stats[port]["statistics"]["in-unknown-protocol-discards"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["in-broadcast-packets"][language],
            port_stats[port]["statistics"]["in-broadcast-packets"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["in-multicast-packets"][language],
            port_stats[port]["statistics"]["in-multicast-packets"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["in-unicast-packets"][language],
            port_stats[port]["statistics"]["in-unicast-packets"].data,
        )

        # Print output statistics
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["out-discards"][language],
            port_stats[port]["statistics"]["out-discards"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["out-errors"][language],
            port_stats[port]["statistics"]["out-errors"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["out-octets"][language],
            port_stats[port]["statistics"]["out-octets"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["out-packets"][language],
            port_stats[port]["statistics"]["out-packets"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["out-broadcast-packets"][language],
            port_stats[port]["statistics"]["out-broadcast-packets"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["out-multicast-packets"][language],
            port_stats[port]["statistics"]["out-multicast-packets"].data,
        )
        print_row_with_spacing(
            local_str["spacer"][language],
            width,
            local_str["out-unicast-packets"][language],
            port_stats[port]["statistics"]["out-unicast-packets"].data,
        )

    # Print the closing delimator
    print("=" * 80)


def get_connection_with_argv():
    """Parse arguments and get a connection"""

    # The language is optional, so we need a default value
    parsed_language = "english"

    # Use the sros() function to determine if the application is executed
    # locally on an SR OS device, or remotely so that the same application
    # can be developed to run locally or remotely.

    # The application is running locally
    if sros():
        # Parse the arguments for an optional language parameter
        if len(sys.argv) > 2:
            usage()
            sys.exit(2)

        # Get the language
        if len(sys.argv) == 2:
            if sys.argv[1] in local_str["supported languages"]:
                parsed_language = sys.argv[1]
            else:
                usage()
                sys.exit(2)

        # Get a local Connection object
        connection_object = connect()  # pylint: disable=missing-kwoa

    # The application is running remotely
    else:
        # Import getpass to read the password
        import getpass

        # Parse the arguments for connection and optional language parameters
        if len(sys.argv) > 3 or len(sys.argv) < 2:
            usage()
            sys.exit(2)

        # Get the language
        if len(sys.argv) == 3:
            if sys.argv[2] in local_str["supported languages"]:
                parsed_language = sys.argv[2]
            else:
                usage()
                sys.exit(2)

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
            my_username=username_host[0], my_host=username_host[1], my_password=password
        )

    return connection_object, parsed_language


if __name__ == "__main__":

    my_connection_object, my_language = get_connection_with_argv()
    show_port_counters_output(
        connection_object=my_connection_object, language=my_language
    )
