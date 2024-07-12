### user_input_example.py
#   Copyright 2024 Nokia
###

"""
Tested on: SR OS 24.7.R1

Simple example to show different user input options and
interaction with the SR OS pager.

This example program is designed to be run locally on
an SR OS device.
"""

import getpass
import sys

from pysros.management import sros


def print_lines_of_data():
    for line in range(0, 100):
        print("This is line %s" % line)


def input_without_prompt():
    """This function uses the print statement to write
    a prompt to the screen and then requests an input
    using the input function call which has no parameters.  It prints what you entered in
    response.
    """
    print("Please enter your name: ", end="")
    name = input()
    print("You entered %s" % name)


def input_with_prompt(prompt="Enter your favourite fruit: "):
    """This function uses the parameter to the input function
    to display a prompt to the user requesting the input.  The
    prompt can be set when calling this function but it has a
    default prompt if you do not set it yourself.  It
    prints what you entered in response.

    Args:
        prompt (str, optional): Prompt to display to the user. Defaults to "Enter your favourite fruit: ".
    """
    my_input = input(prompt)
    print("You entered %s" % my_input)


def trigger_pager_then_input_with_prompt(prompt):
    """This function prints enough text to the screen to
    trigger the SR OS pager and subsequently requests input.

    Args:
        prompt (str, optional): User prompt for input
    """
    print_lines_of_data()
    input_with_prompt(prompt)


def readline_without_prompt():
    """This example function requests user input using the
    readline function.  The readline function includes
    any trailing newline character that the input function
    strips off."""
    print("Enter your favourite animal: ")
    animal = sys.stdin.readline()
    print("You entered %s" % animal)


def getpass_with_prompt(prompt):
    """This function uses getpass to obtain user input
    that is not returned to the screen as you type it.
    For demonstration purposes it then prints the input
    to the screen.

    Args:
        prompt (str, optional): User defined prompt
    """
    password = getpass.getpass(prompt=prompt)
    print("You entered %s." % password)
    print("Note that it was not displayed as you typed.")


def main():
    """To show options for reading in user input."""
    input_without_prompt()
    input_with_prompt("Enter your age: ")
    trigger_pager_then_input_with_prompt("Input after the pager now: ")
    readline_without_prompt()
    getpass_with_prompt("Enter your password which we will print later: ")


if __name__ == "__main__":
    if sros:
        main()
