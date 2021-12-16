:mod:`ehs` -- Functions specific to the event handling system (EHS)
===================================================================

.. module:: ehs
   :synopsis: Functions specific for the SR OS event handling system (EHS)

This module is used when executing on SR OS only.  On a remote machine, the
event handling system (EHS) and its functionality are not supported.

The :mod:`ehs` module provides functions for obtaining the data from the
specific event that triggered the execution of a Python application from
the event handling system (EHS).

.. Reviewed by PLM 20211201
.. Reviewed by TechComms 20211202

Classes
-------

.. class:: get_event

   The EHS event that triggered the execution of the Python application.

      .. function:: appid

         The name of the application that generated the event.

         :return: Application name.
         :rtype: str

         .. Reviewed by PLM 20211201
         .. Reviewed by TechComms 20211202

      .. function:: eventid

         The event ID number of the application.

         :return: Event ID.
         :rtype: int

         .. Reviewed by PLM 20211201
         .. Reviewed by TechComms 20211202

      .. function:: severity

         The severity level of the event.

         :return: Severity of the event.
         :rtype: str

         .. Reviewed by PLM 20211201
         .. Reviewed by TechComms 20211202

      .. function:: subject

         The subject or affected object of the event.

         :return: Subject or affected object.
         :rtype: str

         .. Reviewed by PLM 20211201
         .. Reviewed by TechComms 20211202

      .. function:: gentime

         The formatted time the event was generated in UTC.

         :return: The timestamp in ISO 8601 format that the event was generated.
         :rtype: str

         .. Reviewed by PLM 20211201
         .. Reviewed by TechComms 21211202

      .. function:: timestamp

         The formatted time the event was generated.

         :return: The timestamp in seconds.
         :rtype: float

         .. Reviewed by PLM 20211201
         .. Reviewed by TechComms 21211202

      .. function:: eventparameters

         The additional parameters specific to the event that caused the
         Python application to execute.

         :return: Additional attributes of the specific event.
         :rtype: dict

         .. Reviewed by PLM 20211201
         .. Reviewed by TechComms 21211202
