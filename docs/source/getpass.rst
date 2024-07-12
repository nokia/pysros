:mod:`getpass` --- Portable password input
==========================================

.. module:: getpass
   :synopsis: Portable reading of passwords

.. admonition:: Differences to Python
   :class: attention

   This module implements a subset of the upstream Python module.
   For more information, refer to the original documentation: 
   `getpass <https://docs.python.org/3.9/library/getpass.html>`_.

This module is used when executing on SR OS only.  On a remote machine, the
native Python `getpass <https://docs.python.org/3.9/library/getpass.html>`_ 
module is used.

The :mod:`getpass` module provides functions for user inputs of passwords
without returning the characters to the screen.

.. Reviewed by PLM 20240523
.. Reviewed by TechComms 20240529

Functions
---------

.. function:: getpass(prompt='Password: ')

   Prompt the user for a password without echoing.  The user is prompted using
   the string *prompt*, which defaults to ``'Password: '``.

   :param prompt: Optional string prompt to provide the user guidance.
   :type prompt: str, optional
   :return: The inputted value
   :rtype: str

.. Reviewed by PLM 20240612
.. Reviewed by TechComms 20240612