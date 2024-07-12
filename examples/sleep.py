#!/usr/bin/env python3

### sleep.py
#   Copyright 2024 Nokia
###

# pylint: disable=import-error, import-outside-toplevel, line-too-long, too-many-branches, too-many-locals, too-many-statements

"""
Tested on: SR OS 24.3.R1

Delay for a specified amount of time.

Execution on SR OS
    usage: pyexec bin/sleep.py (<number> | <decimal-number>)

Add the following alias so that the Python application can be run as a
native MD-CLI command.

/configure python python-script "sleep" admin-state enable
/configure python python-script "sleep" urls ["cf3:bin/sleep.py"]
/configure python python-script "sleep" version python3

/configure system management-interface cli md-cli environment command-alias alias "sleep" admin-state enable
/configure system management-interface cli md-cli environment command-alias alias "sleep" description "Delay for a specified amount of time"
/configure system management-interface cli md-cli environment command-alias alias "sleep" python-script "sleep"
/configure system management-interface cli md-cli environment command-alias alias "sleep" mount-point global
"""

# Import sys for parsing arguments and returning specific exit codes
import sys

# Import the time module for the sleep function
import time


def usage():
    """Print the usage"""

    print("")
    print("Usage:", sys.argv[0], "(<number> | <decimal-number>)")
    print(" <number>         - <0..100>")
    print(" <decimal-number> - <0.00..100.99>")


def sleep():
    """Parse decimal number and then sleep"""

    # Check the number of arguments is 2
    if len(sys.argv) != 2:
        usage()
        sys.exit(2)

    # Check to see if the argument is a float.
    # This also checks if the argument is an int.
    try:
        float(sys.argv[1])
        if float(sys.argv[1]) < 0.00 or float(sys.argv[1]) > 100.99:
            usage()
            sys.exit(2)
    except ValueError:
        usage()
        sys.exit(2)

    time.sleep(float(sys.argv[1]))


if __name__ == "__main__":
    sleep()
