
The :mod:`pysros.ehs` module provides functionality obtain data from the
specific event that triggered the execution of a Python application from
the event handling system (EHS).

.. Reviewed by PLM 20220118
.. Reviewed by TechComms 20220124

.. note:: This module is available when executing on SR OS only. On a remote
          machine, the event handling system (EHS) and its functionality
          are not supported.

.. Reviewed by PLM 20220117
.. Reviewed by TechComms 20220124

.. py:function:: pysros.ehs.get_event

   The EHS event that triggered the execution of the Python application.

   :return: The Event object or None.
   :rtype: :py:class:`pysros.ehs.Event` or ``None``

   .. Reviewed by PLM 20220118
   .. Reviewed by TechComms 20220124

.. class:: pysros.ehs.Event

   The EHS :py:class:`pysros.ehs.Event` Class for the event that triggered the execution of the
   Python application.

   .. py:attribute:: name

      The name of the event.

      :type: str

      .. Reviewed by PLM 20220930
      .. Reviewed by TechComms 20221005

   .. py:attribute:: appid

      The name of the application that generated the event.

      :type: str

      .. Reviewed by PLM 20220118
      .. Reviewed by TechComms 20220124

   .. py:attribute:: eventid

      The event ID number of the application.

      :type: int

      .. Reviewed by PLM 20220118
      .. Reviewed by TechComms 20220124

   .. py:attribute:: severity

      The severity level of the event.

      :type: str

      .. Reviewed by PLM 20220118
      .. Reviewed by TechComms 20220124

   .. py:attribute:: sequence

      The sequence number of the event in the syslog collector.

      :type: int
      :raises ValueError: for negative values.

      .. Reviewed by PLM 20220930
      .. Reviewed by TechComms 20221005

   .. py:attribute:: subject

      The subject or affected object of the event.

      :type: str

      .. Reviewed by PLM 20220118
      .. Reviewed by TechComms 20220124

   .. py:attribute:: router_name

      The name of the SR OS router-instance (For example, ``Base``) in which this
      event was triggered.

      :type: str

      .. Reviewed by PLM 20220930
      .. Reviewed by TechComms 20221005

   .. py:attribute:: gentime

      The time, in ISO 8601 format, that the event was generated.

      :type: str

     .. Reviewed by PLM 20220118
     .. Reviewed by TechComms 20220124

   .. py:attribute:: timestamp

      The timestamp, in seconds, that the event was generated.

      :type: float

      .. Reviewed by PLM 20220118
      .. Reviewed by TechComms 20220124

   .. py:attribute:: text

      The event specific body, formatted as a string.  By default, this
      is generated from the :py:attr:`eventparameters`.

      :type: str

   .. py:attribute:: eventparameters

      The additional parameters specific to the event that caused the
      Python application to execute.

      :type: :py:class:`pysros.ehs.EventParams`

      .. Reviewed by PLM 20220930
      .. Reviewed by TechComms 20221005

   .. py:method:: format_msg

      Return a string representation of the SR OS formatted log message.

      :return: SR OS formatted log message.
      :rtype: str

      .. Reviewed by PLM 20220118
      .. Reviewed by TechComms 20220124

.. class:: EventParams

   The additional parameters of the specific :py:class:`pysros.ehs.Event`.
   This class is *read-only*.  Specific additional parameters may be
   accessed using standard Python subscript syntax.

   .. Reviewed by PLM 20220118
   .. Reviewed by TechComms 20220124

   .. py:method:: keys

      Obtain the additional parameters names.

      :return: Additional parameters names for the Event.
      :rtype: tuple(str)

      .. Reviewed by PLM 20220118
      .. Reviewed by TechComms 20220124

   .. describe:: params[key]

      Return the value of the parameter *key*. If the parameter does not exist,
      a :exc:`KeyError` is raised.

      .. Reviewed by PLM 20220930
      .. Reviewed by TechComms 20221005

