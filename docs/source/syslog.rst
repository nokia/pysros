The :mod:`pysros.syslog` module provides functionality for obtaining and
manipulating a syslog event.

.. note:: This module is available when executing on SR OS only. On a remote
          machine, the syslog function is not supported.

.. important::

   The :py:mod:`pysros.syslog` module is designed to be used 
   with the SR OS syslog functionality at high processing rates.
   It cannot be used with the :py:mod:`pysros.management`
   module, SR OS filesystem access, or the EHS, CRON, or pyexec execution
   pathways.

Two methods are available to modify the syslog message being sent:

* The :py:func:`pysros.syslog.get_event` function retrieves the syslog event
  that is in the queue to be sent out and allows for its attributes to be
  modified.  When the Python application terminates successfully, the newly
  modified attributes are reformatted using the default syslog format.
* The :py:meth:`pysros.syslog.Event.override_payload` method allows for an
  entirely new payload to be crafted based on the data from the original
  event but choosing a customer format and which data to include.

.. note:: The maximum length of a syslog message on SR OS is 1023 bytes.  When
          modifying the payload to become larger than this maximum value, one of
          the following occurs:

          * When using :py:meth:`pysros.syslog.Event.override_payload`, an
            exception is raised.  The length can be checked prior to
            executing the :py:meth:`pysros.syslog.Event.override_payload`
            method.
          * When modifying the event parameters, the resulting payload is 
            truncated as the resulting length cannot be known in advance.
            When this occurs, the last character is marked with an
            asterisk (*).

.. Reviewed by PLM 20220929
.. Reviewed by TechComms 20221005

.. function:: pysros.syslog.get_event

   Obtain the syslog event queued to be sent out.

   :return: The event object or None.
   :rtype: :class:`pysros.syslog.Event` or ``None``

   .. Reviewed by PLM 20220929
   .. Reviewed by TechComms 20221005

.. function:: generate_pri(facility, severity)

   Converts the event severity into a syslog severity and
   combines it with the facility to generate the syslog PRI value
   (See `RFC 5424 <https://www.rfc-editor.org/rfc/rfc5424.html#section-6>`_
   for details) that can be used when formatting a new syslog payload.

   :param facility: Syslog facility value.
   :type facility: int
   :param severity: Event severity name.
   :type severity: str
   :returns: Syslog PRI value.
   :rtype: str
   :raises ValueError: for invalid facilities, see :attr:`pysros.syslog.Event.facility`
   :raises ValueError: for invalid severities, see :attr:`pysros.syslog.Event.severity`

   .. Reviewed by PLM 20220929
   .. Reviewed by PLM 20221005

.. function:: severity_to_name(severity)

   Converts an event severity name into a syslog severity name.

   :param severity: Event severity name.
   :type severity: str
   :returns: Syslog severity name.
   :rtype: str
   :raises ValueError: for invalid severities, see :attr:`pysros.syslog.Event.severity`

   .. Reviewed by PLM 20220929
   .. Reviewed by TechComms 20221005

.. function:: get_system_name

   Retrieves the system name.  This function is provided directly as part
   of the :py:mod:`pysros.syslog` module to provide enhanced
   performance for the syslog execution pathway.

   :returns: SR OS system name.
   :rtype: str


.. class:: pysros.syslog.Event

   The syslog :py:class:`Event` class provides access to the header-fields of the messages,
   the individual fields of the event and the syslog-specific attributes.

   .. note::

      The header-fields can be modified unless stated otherwise.

   Any changes are reflected in the actual syslog-packet being sent out.

   If a change of message format is required, for example, the ordering or the value of the
   field needs to change, :py:meth:`override_payload` should be used to override the complete
   message. In this case, the actual message first needs to be formatted using the
   :py:func:`format_msg` function before it is passed to the
   :py:meth:`override_payload` function.

   .. Reviewed by PLM 20220929
   .. Reviewed by PLM 20221005

   .. attribute:: name

      The name of the event.

      :type: str

      .. Reviewed by PLM 20220929
      .. Reviewed by TechComms 20221004

   .. attribute:: appid

      The name of the application that generated the event.

      :type: str

      .. Reviewed by PLM 20220826
      .. Reviewed by TechComms 20221005

   .. attribute:: eventid

      The event ID number of the application.

      :type: int
      :raises ValueError: for negative values.

      .. Reviewed by PLM 20220929
      .. Reviewed by TechComms 20221005

   .. attribute:: severity

      The severity level of the event.  Valid values are:

      * none
      * cleared
      * indeterminate
      * critical
      * major
      * minor
      * warning

      :type: str

      .. Reviewed by PLM 20220929
      .. Reviewed by TechComms 20221005

   .. attribute:: sequence

      The sequence number of the event in the syslog collector.

      :type: int
      :raises ValueError: for negative values.

      .. Reviewed by PLM 20220929
      .. Reviewed by TechComms 20221005

   .. attribute:: subject

      The subject or affected object of the event.

      :type: str

      .. Reviewed by PLM 20220826
      .. Reviewed by TechComms 20221005

   .. attribute:: router_name

      The name of the SR OS router-instance (For example, ``Base``) in which this
      event was triggered.

      :type: str

      .. Reviewed by PLM 20220929
      .. Reviewed by TechComms 20221005

   .. attribute:: gentime

      The time, in ISO 8601 format, that the event was generated.

      .. note::

         Changes to :attr:`timestamp` are reflected in this attribute.

      :type: str, *read-only*

      .. Reviewed by PLM 20220826
      .. Reviewed by TechComms 20221005

   .. attribute:: timestamp

      The time, in seconds, that the event was generated.

      :type: float

      .. Reviewed by PLM 20220826
      .. Reviewed by TechComms 20221005

   .. attribute:: hostname

      The hostname field of the syslog message.  This can be an IP address,
      fully-qualified domain name (FQDN), or hostname.

      :type: str

      .. Reviewed by PLM 20220929
      .. Reviewed by TechComms 20221005

   .. attribute:: log_prefix

      The log-prefix inserted into the event message.

      :type: str

      .. Reviewed by PLM 20220929
      .. Reviewed by TechComms 20221005

   .. attribute:: facility

      The syslog facility code. A list of named values is provided in
      :class:`pysros.syslog.Facility`.

      :type: int
      :raises ValueError: for values outside of the valid range [0..31]

      .. Reviewed by PLM 20220929
      .. Reviewed by TechComms 20221005

   .. attribute:: text

      The event specific body formatted as a string.  By default, this
      is generated from the :py:attr:`eventparameters`.

      This attribute can be modified to provide new event text.

      This message may include values from the :py:attr:`eventparameters` function.

      :type: str

   .. attribute:: eventparameters

      The additional parameters specific to the event that caused the
      Python application to execute.

      .. note::

         The parameters returned cannot be modified to alter the generated
         event text.  Instead, a new event text should be generated from the
         values and assigned to the :attr:`text` attribute.

      :returns: Event specific parameters.  The parameters in this class are *read-only*.
      :rtype: :py:class:`pysros.syslog.EventParams`

      .. Reviewed by PLM 20220929
      .. Reviewed by TechComms 20221005

   .. method:: format_msg

      Return a string representation of the SR OS formatted log message.

      :return: SR OS formatted log message.
      :rtype: str

   .. method:: format_syslog_msg

      Return a string representation of the SR OS formatted log message as it
      appears in the syslog packet.
      When any of the writable attributes on this event have been modified,
      the output of this function contains these changes.

      :return: SR OS formatted syslog message.
      :rtype: str

   .. method:: override_payload(payload)

      Provide a custom syslog message as it appears in the packet. This includes
      header information (facility, timestamp, etc.) and body data (the actual message).

      Attributes from this event can be used to construct a completely new message format.
      Any prior changes to the values of these attributes are used.

      :parameter payload: New syslog payload.
      :type payload: str

      :raises ValueError: when payload is larger than the maximum of 1023 bytes.

   .. method:: drop

      Drop the syslog message from the send queue.

.. class:: pysros.syslog.EventParams

   The additional parameters of the specific :py:class:`pysros.syslog.Event`. This class is
   *read-only*.  Specific additional parameters may be accessed using standard Python subscript
   syntax.

   .. Reviewed by PLM 20220929
   .. Reviewed by TechComms 20221005

   .. method:: keys

      Obtain the additional parameter names.

      :return: Additional parameter names for the event.
      :rtype: tuple(str)

      .. Reviewed by PLM 20220929
      .. Reviewed by TechComms 20221005

   .. describe:: params[key]
      
      Return the value of the parameter *key*. If the parameter does not exist,
      a :exc:`KeyError` is raised.  *key* is of type `str`.

      .. Reviewed by PLM 20220929
      .. Reviewed by TechComms 20221005

   .. describe:: iter(params)

      Return an iterator for the key value pairs of parameters.

      Where an iterator is expected, this object can be passed and the iterator
      is used implicitly.  This can be used to collect all
      :py:attr:`pysros.syslog.Event.eventparameters` into a standard Python *dict*.

      .. code-block:: python3
         :caption: Example use of the iterator for type conversion

         >>> list(event.eventparameters)
         [('key1', 'value1'), ('key2', 'value2'), ('key3', 'value3')]
         >>> params = dict(event.eventparameters)
         >>> type(params)
         <class 'dict'>
         >>> params
         {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'}

      .. Reviewed by PLM 20220929
      .. Reviewed by TechComms 20221005

.. class:: pysros.syslog.Facility

   Class similar to an Enum that defines constants that can be used as values for the
   :py:attr:`pysros.syslog.Event.facility` attribute.

   .. Reviewed by PLM 20220826
   .. Reviewed by TechComms 20221005

   .. note::

      No instances of this class can be instantiated.

   .. attribute:: KERNEL
      :value: 0

   .. attribute:: USER
      :value: 1

   .. attribute:: MAIL
      :value: 2

   .. attribute:: SYSTEMD
      :value: 3

   .. attribute:: AUTH
      :value: 4

   .. attribute:: SYSLOGD
      :value: 5

   .. attribute:: PRINTER
      :value: 6

   .. attribute:: NETNEWS
      :value: 7

   .. attribute:: UUCP
      :value: 8

   .. attribute:: CRON
      :value: 9

   .. attribute:: AUTHPRIV
      :value: 10

   .. attribute:: FTP
      :value: 11

   .. attribute:: NTP
      :value: 12

   .. attribute:: LOGAUDIT
      :value: 13

   .. attribute:: LOGALERT
      :value: 14

   .. attribute:: CRON2
      :value: 15

   .. attribute:: LOCAL0
      :value: 16

   .. attribute:: LOCAL1
      :value: 17

   .. attribute:: LOCAL2
      :value: 18

   .. attribute:: LOCAL3
      :value: 19

   .. attribute:: LOCAL4
      :value: 20

   .. attribute:: LOCAL5
      :value: 21

   .. attribute:: LOCAL6
      :value: 22

   .. attribute:: LOCAL7
      :value: 23

