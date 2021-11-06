#!/usr/bin/env python3

### show_system_summary.py
#   Copyright 2021 Nokia
###

# pylint: disable=line-too-long
"""
Tested on: SR OS 21.10.R1

Show port counters.

Execution on SR OS
    usage: pyexec show_port_counters.py [<keyword>]
Execution on remote machine
    usage: python show_port_counters.py username@host [<keyword>]
Execution on remote machine if show_port_counters.py is executable
     usage: ./show_port_counters.py username@host [<keyword>]

This application to display system information demonstrates how to parse
different arguments depending on if the application is running locally or
remotely.  It also demonstrates how to print table headers in a different
language.  The state element names and text values are displayed in English,
since this how they appear in the state datastore.

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

# pylint: disable=too-many-locals

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
    "spacer": {
        "chinese": "\u3000",
        "english": " ",
        "french": " ",
        "japanese": "\u3000",
        "russian": " ",
        "slovak": " ",
        "spanish": " ",
    },
    "Port Statistics for": {
        "chinese": "端口统计信息",
        "english": "Port Statistics for",
        "french": "Statistiques pour le Port",
        "japanese": "ポート統計情報",
        "russian": "Статистика порта",
        "slovak": "Štatistiky Porto pre",
        "spanish": "Estadísticas del Puerto",
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
    "description": {
        "chinese": "描述",
        "english": "Description",
        "french": "Description",
        "japanese": "説明",
        "russian": "Описание",
        "slovak": "Popis",
        "spanish": "Descripción",
    },
    "oper-state": {
        "chinese": "状态",
        "english": "Operational state",
        "french": "Etat opérationnel",
        "japanese": "状態",
        "russian": "Операционный статус",
        "slovak": "Stav portu",
        "spanish": "Estado operacional",
    },
    "counter-discontinuity-time": {
        "chinese": "计数中断时间",
        "english": "Counter discontinuity time",
        "french": "Compteur de temps d’interruption",
        "japanese": "カウンター中断時間",
        "russian": "Счетчик прерывности",
        "slovak": "Celkové trvanie výpadkov počítadla",
        "spanish": "Tiempo desde última discontinuidad en contadores",
    },
    "last-cleared-time": {
        "chinese": "上次清空时间",
        "english": "Last cleared time",
        "french": "Dernière heure de remise à zéro",
        "japanese": "前回クリア時間",
        "russian": "Время-послед.-сброса",
        "slovak": "Čas posledného vyčistenia",
        "spanish": "Hora del último borrado",
    },
    "in-discards": {
        "chinese": "ｉｎ－丢包",
        "english": "In discards",
        "french": "Supprimés en entrée",
        "japanese": "ｉｎ－廃棄",
        "russian": "Вх. отклоненных",
        "slovak": "Zahodenia na vstupe",
        "spanish": "Descartes en entrada",
    },
    "in-errors": {
        "chinese": "ｉｎ－错误",
        "english": "In errors",
        "french": "Erreurs en entrée",
        "japanese": "ｉｎ－エラー",
        "russian": "Вх. ошибок",
        "slovak": "Chyby na vstupe",
        "spanish": "Errores en entrada",
    },
    "in-octets": {
        "chinese": "ｉｎ－转发字节",
        "english": "In octets",
        "french": "Octets entrant",
        "japanese": "ｉｎ－オクテット",
        "russian": "Вх. октетов",
        "slovak": "Oktety na vstupe",
        "spanish": "Octetos en entrada",
    },
    "in-packets": {
        "chinese": "ｉｎ－转发数据包",
        "english": "In packets",
        "french": "Paquets entrant",
        "japanese": "ｉｎ－パケット",
        "russian": "Вх. пакетов",
        "slovak": "Pakety na vstupe",
        "spanish": "Paquetes en entrada",
    },
    "in-unknown-protocol-discards": {
        "chinese": "ｉｎ－未知协议丢包",
        "english": "In unknown protocol discards",
        "french": "Protocole inconnu supprimé en entrée",
        "japanese": "ｉｎ－不明プロトコル廃棄",
        "russian": "Вх. отклоненных неизвестный протокол",
        "slovak": "Zahodené neznáme protokoly na vstupe",
        "spanish": "Descartes por protocol desconocido en entrada",
    },
    "in-broadcast-packets": {
        "chinese": "ｉｎ－广播转发数据包",
        "english": "In broadcast packets",
        "french": "Paquets broadcast entrant",
        "japanese": "ｉｎ－ブロードキャストパケット",
        "russian": "Вх. широковещательных пакетов",
        "slovak": "Broadcast pakety na vstupe",
        "spanish": "Paquetes broadcast en entrada",
    },
    "in-multicast-packets": {
        "chinese": "ｉｎ－组播转发数据包",
        "english": "In multicast packets",
        "french": "Paquets multicast entrant",
        "japanese": "ｉｎ－マルチキャストパケット",
        "russian": "Вх. мультикаст пакетов",
        "slovak": "Multicast pakety na vstupe",
        "spanish": "Paquetes multicast en entrada",
    },
    "in-unicast-packets": {
        "chinese": "ｉｎ－单播转发数据包",
        "english": "In unicast packets",
        "french": "Paquets unicast entrant",
        "japanese": "ｉｎ－ユニキャストパケット",
        "russian": "Вх. юникаст пакетов",
        "slovak": "Unicast pakety na vstupe",
        "spanish": "Paquetes unicast en entrada",
    },
    "out-discards": {
        "chinese": "ｏｕｔ－丢包",
        "english": "Out discards",
        "french": "Supprimés en sortie",
        "japanese": "ｏｕｔ－廃棄",
        "russian": "Исх. отклоненных",
        "slovak": "Zahodenia na výstupe",
        "spanish": "Descartes en salida",
    },
    "out-errors": {
        "chinese": "ｏｕｔ－错误",
        "english": "Out errors",
        "french": "Erreurs en sortie",
        "japanese": "ｏｕｔ－エラー",
        "russian": "Исх. ошибок",
        "slovak": "Chyby na výstupe",
        "spanish": "Errores en salida",
    },
    "out-octets": {
        "chinese": "ｏｕｔ－转发字节",
        "english": "Out octets",
        "french": "Octets sortant",
        "japanese": "ｏｕｔ－オクテット",
        "russian": "Исх. октетов",
        "slovak": "Oktety na výstupe",
        "spanish": "Octetos en salida",
    },
    "out-packets": {
        "chinese": "ｏｕｔ－转发数据包",
        "english": "Out packets",
        "french": "Paquets sortant",
        "japanese": "ｏｕｔ－パケット",
        "russian": "Исх. пакетов",
        "slovak": "Pakety na výstupe",
        "spanish": "Paquetes en salida",
    },
    "out-broadcast-packets": {
        "chinese": "ｏｕｔ－广播转发数据包",
        "english": "Out broadcast packets",
        "french": "Paquets broadcast sortant",
        "japanese": "ｏｕｔ－ブロードキャストパケット",
        "russian": "Исх. широковещательных пакетов",
        "slovak": "Broadcast pakety na výstupe",
        "spanish": "Paquetes broadcast en salida",
    },
    "out-multicast-packets": {
        "chinese": "ｏｕｔ－组播转发数据包",
        "english": "Out multicast packets",
        "french": "Paquets multicast sortant",
        "japanese": "ｏｕｔ－マルチキャストパケッ",
        "russian": "Исх. мультикаст пакетов",
        "slovak": "Multicast pakety na výstupe",
        "spanish": "Paquetes multicast en salida",
    },
    "out-unicast-packets": {
        "chinese": "ｏｕｔ－单播转发数据包",
        "english": "Out unicast packets",
        "french": "Paquets unicast sortant",
        "japanese": "ｏｕｔ－ユニキャストパケット",
        "russian": "Исх. юникаст пакетов",
        "slovak": "Unicast pakety na výstupe",
        "spanish": "Paquetes unicast en salida",
    },
}


def usage():
    """Print the usage"""

    if sros():
        # Remove hyphens that are added in the python-script "show-port-counters" name
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
        # Only display the separator after the first item
        if is_first_item:
            is_first_item = False
        else:
            print("-" * 80)

        # Print row header
        print_row_with_spacing(
            local_str["spacer"][language], width, local_str["Port"][language], str(port)
        )
        print("-" * 80)

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

        # Print in counters if the port is not down
        # The operational state can be: unknown, up, down, diagnosing, failed
        if str(port_stats[port]["oper-state"]) != "down":

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
    show_port_counters_output(
        connection_object=my_connection_object, language=my_language
    )
