#!/usr/bin/env python3

### show_system_summary.py
#   Copyright 2021 Nokia
###

# pylint: disable=line-too-long
"""
Tested on: SR OS 21.10.R1

Show system summary information.

Execution on SR OS
    usage: pyexec show_system_summary.py [<keyword>]
Execution on remote machine
    usage: python show_system_summary.py username@host [<keyword>]
Execution on remote machine if show_system_summary.py is executable
    usage: ./show_system_summary.py username@host [<keyword>]

This application to display system information demonstrates how to parse
different arguments depending on if the application is running locally or
remotely.  It also demonstrates how to print table headers in a different
language.  The state element names and text values are displayed in English,
since this how they appear in the state datastore.

Add the following alias so that the Python application can be run as a
native MD-CLI command.

/configure python { python-script "show-system-summary" admin-state enable }
/configure python { python-script "show-system-summary" urls ["cf3:show_system_summary.py"]
/configure python { python-script "show-system-summary" version python3 }
/configure system { management-interface cli md-cli environment command-alias alias "summary" }
/configure system { management-interface cli md-cli environment command-alias alias "summary" admin-state enable }
/configure system { management-interface cli md-cli environment command-alias alias "summary" description "Show system summary information" }
/configure system { management-interface cli md-cli environment command-alias alias "summary" python-script "show-system-summary" }
/configure system { management-interface cli md-cli environment command-alias alias "summary" mount-point "/show system" }
"""

# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# pylint: disable=too-many-branches

# Import sys for parsing arguments and returning specific exit codes
import sys

# Import datetime to get and display the date and time
import datetime

# Import the connect and sros methods from the management pySROS submodule
from pysros.management import connect  # pylint: disable=import-error
from pysros.management import sros  # pylint: disable=import-error


# Define local language strings
local_str = {
    "supported languages": {
        "chinese": "中文",
        "english": "English",
        "french": "Français",
        "japanese": "日本語",
        "russian": "Русский",
        "slovak": "Slovenský",
        "spanish": "Español",
    },
    "System Summary for": {
        "chinese": "系统概要",
        "english": "System Summary for",
        "french": "Résumé Système pour",
        "japanese": "システムサマリー",
        "russian": "Сводка по системе",
        "slovak": "Sumár Systému pre",
        "spanish": "Resumen del Sistema",
    },
    "Active Alarms": {
        "chinese": "活动告警",
        "english": "Active Alarms",
        "french": "Alarmes Actives",
        "japanese": "アクティブアラーム",
        "russian": "Активных аварий",
        "slovak": "Aktívne Alarmy",
        "spanish": "Alarmas Activas",
    },
    "FP Error Statistics": {
        "chinese": "ＦＰ错误统计",
        "english": "FP Error Statistics",
        "french": "Statistiques des Erreurs FP",
        "japanese": "ＦＰエラー統計",
        "russian": "Статистика ошибок FP",
        "slovak": "Štatistiky Chýb FP",
        "spanish": "Estadísticas de Errores FP",
    },
    "Card": {
        "chinese": "板卡",
        "english": "Card",
        "french": "Carte",
        "japanese": "カード",
        "russian": "Карта",
        "slovak": "Karta",
        "spanish": "Tarjeta",
    },
    "FP": {
        "chinese": "ＦＰ芯片",
        "english": "FP",
        "french": "FP",
        "japanese": "ＦＰチップ",
        "russian": "FP",
        "slovak": "FP",
        "spanish": "FP",
    },
    "Port Statistics": {
        "chinese": "端口统计芯片",
        "english": "Port Statistics",
        "french": "Statistiques du Port",
        "japanese": "ポート統計情報",
        "russian": "Статистика порта",
        "slovak": "Štatistiky Portov",
        "spanish": "Estadísticas de Puerto",
    },
    "Port": {
        "chinese": "端口",
        "english": "Port",
        "french": "Port",
        "japanese": "ポート",
        "russian": "Порт",
        "slovak": "Port",
        "spanish": "Puerto",
    },
}


def usage():
    """Print the usage"""

    if sros():
        # Remove hyphens that are added in the python-script "show-system-summary" name
        for i in sys.argv[0]:
            if i in "-":
                sys.argv[0] = sys.argv[0].replace(i, " ")
        print("")
        print("", sys.argv[0], "[<keyword>]")
    else:
        print("Usage:", sys.argv[0], "username@host [<keyword>]")
    print(" <keyword>  - (chinese|english|french|japanese|russian|slovak|spanish)")
    print(" Default    - english")


def get_remote_connection(my_username, my_host, my_password):
    """Function definition to obtain a Connection object to a remote SR OS device
    and access model-driven information"""

    # Import the exceptions so they can be caught on error
    # fmt: off
    from pysros.exceptions import ModelProcessingError  # pylint: disable=import-error disable=import-outside-toplevel
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


def print_rows(input_data, column):
    """Print table rows in the specified format"""

    for k in sorted(input_data):
        # Elements with no data are not displayed
        if input_data[k].data:
            # If the input data is a dict like from
            # /nokia-state:state/system/alarms/active then recurse
            if isinstance(input_data[k].data, dict):
                print_rows(input_data[k].data, column)
            else:
                print(
                    "{0:<{width}} : {1}".format(
                        k, str(input_data[k].data), width=column
                    )
                )


def set_column_width(input_data):
    """Count the maximum column width based on the longest element name in the input data"""

    column_width = 0
    for k in sorted(input_data):
        # If the input data is a dict like from
        # /nokia-state:state/system/alarms/active then recurse
        if isinstance(input_data[k].data, dict):
            column_width = set_column_width(input_data[k].data)
        else:
            if len(k) > column_width:
                column_width = len(k)
    return column_width


def print_row_mixed_spacing(language, column, name, value):
    """Print a row of output with the correct spacing"""

    print(name, end="")

    # Calculate spaces
    if language in ("chinese", "japanese"):
        # UTF-8 full-width characters, multiply length by 2
        num_spaces = column - 2 * len(name)
    else:
        # ASCII or UTF-8 half-width characters
        num_spaces = column - len(name)

    while num_spaces > 0:
        print(" ", end="")
        num_spaces -= 1

    print(" : " + str(value))


def show_system_summary_output(connection_object, language):
    """Main function for the show_system_summary command"""

    bright_red = "\u001b[31;1m"
    green = "\u001b[32m"
    reset = "\u001b[0m"
    yellow = "\u001b[33m"

    # Define local language oper-state strings and colors
    oper_state_str = {
        "diagnosing": {
            "chinese": yellow + "diagnosing" + reset,
            "english": yellow + "diagnosing" + reset,
            "french": yellow + "diagnosing" + reset,
            "japanese": yellow + "diagnosing" + reset,
            "russian": yellow + "Диагностика" + reset,
            "slovak": yellow + "vyhodnocovaný" + reset,
            "spanish": yellow + "en diagnóstico" + reset,
        },
        "down": {
            "chinese": bright_red + "down" + reset,
            "english": bright_red + "down" + reset,
            "french": bright_red + "down" + reset,
            "japanese": bright_red + "down" + reset,
            "russian": bright_red + "Выкл." + reset,
            "slovak": bright_red + "mimo prevádzky" + reset,
            "spanish": bright_red + "down" + reset,
        },
        "failed": {
            "chinese": bright_red + "failed" + reset,
            "english": bright_red + "failed" + reset,
            "french": bright_red + "failed" + reset,
            "japanese": bright_red + "failed" + reset,
            "russian": bright_red + "Ошибка" + reset,
            "slovak": bright_red + "zlyhaný" + reset,
            "spanish": bright_red + "fallo" + reset,
        },
        "unknown": {
            "chinese": bright_red + "unknown" + reset,
            "english": bright_red + "unknown" + reset,
            "french": bright_red + "unknown" + reset,
            "japanese": bright_red + "unknown" + reset,
            "russian": bright_red + "неизвестно" + reset,
            "slovak": bright_red + "neznámy" + reset,
            "spanish": bright_red + "desconocido" + reset,
        },
        "up": {
            "chinese": green + "up" + reset,
            "english": green + "up" + reset,
            "french": green + "up" + reset,
            "japanese": green + "up" + reset,
            "russian": green + "Вкл." + reset,
            "slovak": green + "v prevádzke" + reset,
            "spanish": green + "up" + reset,
        },
    }

    # Get configuration and state data
    port_config = connection_object.running.get("/nokia-conf:configure/port")
    active_alarms = connection_object.running.get(
        "/nokia-state:state/system/alarms/active"
    )
    card_stats = connection_object.running.get("/nokia-state:state/card")
    port_stats = connection_object.running.get("/nokia-state:state/port")
    oper_name = connection_object.running.get("/nokia-state:state/system/oper-name")

    # Get the current date and time
    now = datetime.datetime.now()

    # Print the system summary header
    print("")
    print("=" * 80)
    print(
        local_str["System Summary for"][language],
        oper_name,
        now.strftime("%Y-%m-%d %H:%M:%S"),
        now.astimezone().tzinfo,
    )

    # Print the active alarms
    print("=" * 80)
    print(local_str["Active Alarms"][language])
    print("=" * 80)
    is_first_item = True
    width = 0
    for active_alarm in sorted(active_alarms):
        # Only set the width once
        if width == 0:
            width = set_column_width(active_alarms[active_alarm])
        # Only display the separator after the first item
        if is_first_item:
            is_first_item = False
        else:
            print("-" * 80)
        print_rows(active_alarms[active_alarm], width)

    # Print the FP statistics
    print("=" * 80)
    print(local_str["FP Error Statistics"][language])
    print("=" * 80)
    is_first_item = True
    width = 0
    for card in sorted(card_stats):
        # Check to see if a card is equipped, if there is then print the statistics
        if (str(card_stats[card]["equipped-type"]) != "unassigned") and (
            str(card_stats[card]["equipped-type"]) != "unknown"
        ):
            for fp_number in sorted(card_stats[card]["fp"]):
                # Only set the width once
                if width == 0:
                    width = set_column_width(
                        card_stats[card]["fp"][fp_number]["statistics"]
                    )
                # Only display the separator after the first item
                if is_first_item:
                    is_first_item = False
                else:
                    print("-" * 80)
                print_row_mixed_spacing(
                    language, width, local_str["Card"][language], card
                )
                print_row_mixed_spacing(
                    language, width, local_str["FP"][language], fp_number
                )
                print("-" * 80)
                print_rows(card_stats[card]["fp"][fp_number]["statistics"], width)

    # Print the port statistics
    print("=" * 80)
    print(local_str["Port Statistics"][language])
    print("=" * 80)
    is_first_item = True
    width = 0
    for port in sorted(port_stats):
        # Only set the width once
        if width == 0:
            width = set_column_width(port_stats[port]["statistics"])
        # Only display the separator after the first item
        if is_first_item:
            is_first_item = False
        else:
            print("-" * 80)
        print_row_mixed_spacing(language, width, local_str["Port"][language], port)
        print("-" * 80)

        # Print oper-state values
        print(
            "{0:<{column}} : {1}".format(
                "oper-state",
                oper_state_str[str(port_stats[port]["oper-state"])][language],
                column=width,
            )
        )

        # Print description
        if port in port_config and "description" in port_config[port]:
            print(
                "{0:<{column}} : {1}".format(
                    "description", str(port_config[port]["description"]), column=width
                )
            )

        # Print statistics for each port
        print_rows(port_stats[port]["statistics"], width)

    # Print the closing deliminator
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
        connection_object = connect()

    # The application is running remotely
    else:
        # Import getpass to read the password
        import getpass  # pylint: disable=import-outside-toplevel

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
    show_system_summary_output(
        connection_object=my_connection_object, language=my_language
    )