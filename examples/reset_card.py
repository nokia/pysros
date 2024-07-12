### reset_card.py
#   Copyright 2024 Nokia
###

"""
Tested on: SR OS 24.7.R1

Simple example to explain how to use user-input to
reset a card in a system.

This example program is designed to be run locally on
an SR OS device.
"""

from pysros.management import connect, sros


def main():
    """Main procedure to reset a specific card with a yes/no prompt.

    Raises:
        SystemExit: User canceled transaction
    """
    slot = input("Reset card in which slot? ")
    print("About to reset the card in slot %s" % slot)
    are_you_sure = input("Are you sure? ")
    if are_you_sure.lower() == "y":
        print("Resetting card in slot %s" % slot)
        c = connect()
        c.action(
            "/nokia-oper-reset:reset/card[slot-number=%s]/reinitialize" % slot
        )
        c.disconnect()
    else:
        print("Did not reset card in slot %s.  Canceled by user." % slot)
        raise SystemExit()


if __name__ == "__main__":
    if sros:
        main()
