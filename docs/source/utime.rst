:mod:`utime` -- Time functions
==============================

.. module:: utime
   :synopsis: Time functions adapted for SR OS

.. admonition:: Differences to CPython
   :class: attention

   This module implements a subset of the corresponding CPython 3.5 module, as
   described below. For more information, refer to the original CPython
   documentation: `time (version 3.5) <https://docs.python.org/3.5/library/time.html>`_.

This module is used when executing on SR OS only.  On a remote machine, the
native Python `time <https://docs.python.org/3/library/time.html>`_ module is
used.

The :mod:`utime` module provides functions for getting the current time and date,
measuring time intervals, and for delays.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

Functions
---------

.. function:: gmtime(secs)

   Convert a time, expressed in seconds, since the `epoch`_ to a
   :class:`struct_time`.
   If *secs* is not provided or :const:`None`, the current time is returned 
   by :func:`.time`.  Fractions of a second are ignored.  

   :param secs: Seconds since `epoch`_. Default :const:`None`
   :type secs: int, optional
   :return: Structured time object in UTC where the *dst* flag is 0.
   :rtype: .struct_time

.. Reviewed by PLM 20210916
.. Reviewed by TechComms 20211013

.. function:: localtime(secs)

   Operates like :func:`gmtime` but converts to the local time.  The local time 
   is defined by the timezone configured on SR OS in the ``/configure system 
   time zone`` context.

   :param secs: Seconds since `epoch`_.  Default :const:`None`
   :type secs: int, optional
   :return: Structured time object in local time.  The *dst* flag is set
            to 1 when DST applies to the given time.
   :rtype: .struct_time
   
.. Reviewed by PLM 20210916
.. Reviewed by TechComms 20211013

.. function:: mktime(t)

   This is the inverse function of :func:`localtime`.  
   The earliest date for which it can generate a time on SR OS is the `epoch`_.

   :param t: Time in *local* time, not UTC.  The *dst* flag is required; use ``-1``
             as the *dst* flag value if it is unknown.
   :type t: .struct_time, tuple(tm_year, tm_mon, tm_mday, tm_hour, tm_min, 
            tm_sec, tm_wday, tm_yday, tm_isdst)
   :return: Floating point number compatible with :func:`.time`.  If the input 
            value cannot be represented as a valid time, either :exc:`OverflowError`
            or :exc:`ValueError` is raised (depending on whether the 
            invalid value is caught by Python or the underlying C libraries).
   :rtype: float
   :raises OverflowError: Result of an arithmetic operation is too large to be represented.
   :raises ValueError: Argument has the right type but an inappropriate value, and the 
                       situation is not described by a more precise exception.

.. Reviewed by PLM 20210916
.. Reviewed by TechComms 20211013

.. function:: sleep(secs)
              sleep_ms(millisecs)
              sleep_us(microsecs)

   Suspend execution for the given period of time.  The suspension time may be longer 
   than requested by an arbitrary amount because of the scheduling of other activities
   in the system.

   :param secs: Time, in seconds.
   :type secs: int, float
   :param millisecs: Time, in milliseconds.
   :type millisecs: int, float
   :param microsecs: Time, in microseconds.
   :type microsecs: int, float

.. Reviewed by PLM 20210916
.. Reviewed by TechComms 20211013

.. function:: strftime(format, t)

   Convert a tuple or :class:`struct_time` representing a time as returned by
   :func:`gmtime` or :func:`localtime` to a string as specified by the *format*
   argument.  If *t* is not provided, the current time as returned by
   :func:`localtime` is used.

   :param format: Output format template.  Accepted directives for the template
                  can be found in the table below :ref:`strftime-format-directives-table`.
   :type format: str
   :param t: Time
   :type t: :class:`struct_time`, tuple, optional
   :returns: Formatted string
   :rtype: str
   :raises ValueError: Any field in *t* is outside of the allowed range.

   .. note::
     0 is a valid input for any position in the time tuple. If the value is
     invalid, the value is changed to a correct one.

   The following directives can be embedded in the *format* string. They are shown
   without the optional field width and precision specification, and are replaced
   by the indicated characters in the :func:`strftime` result.

   .. _strftime-format-directives-table:

   .. table:: Format directives

       +-----------+------------------------------------------------+--------+
       | Directive | Meaning                                        | Notes  |
       +===========+================================================+========+
       | ``%a``    | Abbreviated weekday name in English.           | [#f1]_ |
       |           |                                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%A``    | Weekday name in English.                       |        |
       +-----------+------------------------------------------------+--------+
       | ``%b``    | Abbreviated month name in English.             |        |
       |           |                                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%B``    | Full month name in English.                    |        |
       +-----------+------------------------------------------------+--------+
       | ``%c``    | Date and time representation.                  |        |
       +-----------+------------------------------------------------+--------+
       | ``%d``    | Day of the month as a decimal number           |        |
       |           | [Range: 01-31].                                |        |
       |           |                                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%H``    | Hour (24-hour clock) as a decimal number       |        |
       |           | [Range: 00-23].                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%I``    | Hour (12-hour clock) as a decimal number       |        |
       |           | [Range: 01-12].                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%j``    | Day of the year as a decimal number            |        |
       |           | [Range: 001-366].                              |        |
       +-----------+------------------------------------------------+--------+
       | ``%m``    | Month as a decimal number [Range: 01-12].      |        |
       |           |                                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%M``    | Minute as a decimal number [Range: 00-59].     |        |
       |           |                                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%p``    | AM or PM.                                      |        |
       |           |                                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%S``    | Second as a decimal number [Range: 00-59].     |        |
       |           |                                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%U``    | Week number of the year (Sunday as the first   |        |
       |           | day of the week) as a decimal number           |        |
       |           | [Range: 00-53].                                |        |
       |           | All days in a new year preceding the first     |        |
       |           | Sunday are considered to be in week 0.         |        |
       |           |                                                |        |
       |           |                                                |        |
       |           |                                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%w``    | Weekday as a decimal number [Range: 0-6].      |        |
       |           | 0 is considered to mean Sunday.                |        |
       +-----------+------------------------------------------------+--------+
       | ``%W``    | Week number of the year (Monday as the first   |        |
       |           | day of the week) as a decimal number           |        |
       |           | [Range: 00-53].                                |        |
       |           | All days in a new year preceding the first     |        |
       |           | Monday are considered to be in week 0.         |        |
       |           |                                                |        |
       |           |                                                |        |
       |           |                                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%x``    | Locale's appropriate date representation.      |        |
       |           |                                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%X``    | Locale's appropriate time representation.      |        |
       |           |                                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%y``    | Year without century as a decimal number       |        |
       |           | [Range: 00-99].                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%Y``    | Year with century as a decimal number.         |        |
       |           |                                                |        |
       +-----------+------------------------------------------------+--------+
       | ``%%``    | A literal ``'%'`` character.                   |        |
       +-----------+------------------------------------------------+--------+

Notes:

.. [#f1] Output uses English words and is all uppercase characters.

   Example to format a date and time into :rfc:`2822` Internet email standard:

   .. code-block:: python
      :name: strftime-example
      :caption: :func:`strftime` example

      >>> from time import gmtime, strftime
      >>> strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
      'THU, 28 JUN 2001 14:17:15 +0000'

.. Reviewed by PLM 20210917
.. Reviewed by TechComms 20211013

.. class:: struct_time

   The type of the time value sequence returned by :func:`gmtime` and
   :func:`localtime`. It is an object with a named tuple interface.
   Values can be accessed by index or by attribute name.

   When a tuple with an incorrect length is passed to a function expecting a
   :class:`struct_time`, or has elements of the wrong type, a
   :exc:`TypeError` is raised.
   The following values are present:

   .. table:: :class:`struct_time` object values

       +-------+-------------------+---------------------------------+
       | Index | Attribute         | Values                          |
       +=======+===================+=================================+
       | 0     | :attr:`tm_year`   | Example: 1993                   |
       +-------+-------------------+---------------------------------+
       | 1     | :attr:`tm_mon`    | [Range: 1-12] [#f2]_            |
       +-------+-------------------+---------------------------------+
       | 2     | :attr:`tm_mday`   | [Range: 1-31]                   |
       +-------+-------------------+---------------------------------+
       | 3     | :attr:`tm_hour`   | [Range: 0-23]                   |
       +-------+-------------------+---------------------------------+
       | 4     | :attr:`tm_min`    | [Range: 0-59]                   |
       +-------+-------------------+---------------------------------+
       | 5     | :attr:`tm_sec`    | [Range: 0-59]                   |
       +-------+-------------------+---------------------------------+
       | 6     | :attr:`tm_wday`   | [Range: 0-6]. Monday is 0       |
       +-------+-------------------+---------------------------------+
       | 7     | :attr:`tm_yday`   | [Range: 1-366]                  |
       +-------+-------------------+---------------------------------+
       | 8     | :attr:`tm_isdst`  | 0, 1 or -1 [#f3]_               |
       +-------+-------------------+---------------------------------+
       | N/A   | :attr:`tm_zone`   | Abbreviation of timezone name   |
       +-------+-------------------+---------------------------------+
       | N/A   | :attr:`tm_gmtoff` | Offset east of UTC in seconds   |
       +-------+-------------------+---------------------------------+

Notes:

.. [#f2] Note that unlike the C structure, the month value is a
   range of 1-12, not 0-11.
.. [#f3] In calls to :func:`mktime`, :attr:`tm_isdst` may be set to 1 when daylight
   savings time is in effect, and 0 when it is not.  A value of -1 indicates that
   this is not known, and results in the correct state being filled in.

.. Reviewed by PLM 20210917
.. Reviewed by TechComms 20211013

.. function:: ticks_ms()

    Return an increasing millisecond counter with an arbitrary reference point, that
    wraps around after some value.

    The wraparound value is not explicitly exposed, but for discussion, is referred
    to as *TICKS_MAX*. Period of the values is
    *TICKS_PERIOD = TICKS_MAX + 1*. *TICKS_PERIOD* is guaranteed to be a power of
    two, but otherwise may differ.

    The same period value is used
    for all of :func:`ticks_ms`, :func:`ticks_us`, :func:`ticks_cpu`
    functions (for simplicity). Therefore, these functions return a value
    in the range [*0* .. *TICKS_MAX*], inclusive, total *TICKS_PERIOD* values.

    Values returned by these functions should be treated as opaque.
    The only operations available are :func:`ticks_diff` and :func:`ticks_add`.

    :return: Increasing millisecond counter with an arbitrary reference point.
    :rtype: int

    .. note::

       Note that only non-negative values are used.

    .. note::

        Standard mathematical operations (e.g. +, -), or relational
        operators (e.g. <, <=, >, >=) cannot be performed directly on these values.
        Invalid results also occur if results from mathematical operations are passed
        as arguments to :func:`ticks_diff` or :func:`ticks_add`.

.. Reviewed by PLM 20210917
.. Reviewed by TechComms 20211013

.. function:: ticks_us()

   Similar to :func:`ticks_ms` , but in microseconds.

   :return: Increasing microseconds counter with an arbitrary reference point.
   :rtype: int

.. Reviewed by PLM 20210917
.. Reviewed by TechComms 20211013

.. function:: ticks_cpu()

   Similar to :func:`ticks_ms` and `ticks_us`, but with the highest
   possible resolution in the system.

   :return: Increasing counter with an arbitrary reference point.
   :rtype: int

.. Reviewed by PLM 20210917
.. Reviewed by TechComms 20211013

.. function:: ticks_add(ticks, delta)

   Offset the value of *ticks* by a given (positive or negative) *delta*.

   Given a *ticks* value, this function calculates the *ticks* value *delta*
   ticks before or after it, using the modular-arithmetic definition of tick values
   (see :func:`ticks_ms`).

   :func:`ticks_add` is useful for calculating deadlines for events/tasks.

   :param ticks: *ticks* value as a direct result of a call to :func:`ticks_ms`,
                 :func:`ticks_us` or :func:`ticks_cpu` or from a previous call to
                 :func:`ticks_add`.
   :type ticks: int
   :param delta: Positive or negative integer number or numeric expression.
   :type delta: int, expr
   :return: Calculated value of ticks.
   :rtype: int

   .. note::

      Use :func:`ticks_diff` function to work with deadlines.

   Example:

   .. code-block:: python
      :name: ticks-add-example
      :caption: :func:`ticks_add` example

        # Find out what ticks value 100ms ago
        print(ticks_add(time.ticks_ms(), -100))

        # Calculate deadline for operation and test for it
        deadline = ticks_add(time.ticks_ms(), 200)
        while ticks_diff(deadline, time.ticks_ms()) > 0:
            do_a_little_of_something()

        # Find out TICKS_MAX used by this port
        print(ticks_add(0, -1))

.. Reviewed by PLM 20210917
.. Reviewed by TechComms 20211013

.. function:: ticks_diff(ticks1, ticks2)

   Measure *ticks* difference between values returned from :func:`ticks_ms`,
   :func:`ticks_us`, or :func:`ticks_cpu` functions, as a signed value which
   may wrap around.  The function has the same meaning as ``ticks1 - ticks2``.

   Values returned by :func:`ticks_ms`, :func:`ticks_us` or :func:`ticks_cpu`
   may wrap around. Directly using a subtraction operation
   produces an incorrect result. Use the :func:`ticks_diff` function
   provided.

   The function implements modular (or more specifically, ring)
   arithmetic to produce the correct result, even for wraparound values (as
   long as there is not too much of a difference between them).

   If the result is negative, it means that
   *ticks1* occurred earlier in time than *ticks2*. Otherwise, it means that
   *ticks1* occurred after *ticks2*. This holds **only** if *ticks1* and *ticks2*
   are apart from each other for no more than *TICKS_PERIOD/2-1* ticks. If that does
   not hold, an incorrect result is returned. That is, if two tick values are
   apart for *TICKS_PERIOD/2-1* ticks, that value is returned by the function.
   However, if *TICKS_PERIOD/2* of real-time ticks has passed between them, the
   function returns *-TICKS_PERIOD/2* instead. That is, the result value wraps
   to the negative range of possible values.

   :return: Signed value in the range [*-TICKS_PERIOD/2* .. *TICKS_PERIOD/2-1*], which
            is a typical range definition for a two's-completment signed binary integer.
   :rtype: int (signed)

   .. note::

      Do not pass :func:`time` values to :func:`ticks_diff`.  Use standard mathematical
      operations instead.

.. Reviewed by PLM 20210917
.. Reviewed by TechComms 20211013

.. function:: time()

   Return the time in seconds since the `epoch`_.

   The number returned by :func:`.time` may be converted to a more common
   time format (i.e. year, month, day, hour, etc...) in UTC by passing it to
   :func:`gmtime` function, or in local time by passing it to the
   :func:`localtime` function. In both cases, a
   :class:`struct_time` object is returned, from which the components
   of the calendar date may be accessed as attributes.

   :return: Time in seconds since the `epoch`_.
   :rtype: float

.. Reviewed by PLM 20210917
.. Reviewed by TechComms 20211013

.. function:: tzset()

   Reset the time conversion rules used by the library routines.
   When invoked, the current time configuration is inspected and the variables
   :const:`tzname` , :const:`timezone` (non-DST seconds West of UTC),
   :const:`altzone` (DST seconds west of UTC) and :const:`daylight` are set.
   :const:`daylight` is set to 0 if the timezone does not have daylight
   saving time rules, or to nonzero if there is a time (past, present or
   future) when daylight saving time applies.

.. Reviewed by PLM 20210917
.. Reviewed by TechComms 20211013


Timezone constants
------------------

.. data:: altzone

   The offset of the local DST timezone, in seconds, west of UTC (if one is defined).
   The offset is negative if the local DST timezone is east of UTC (such as Western Europe,
   including the UK).  Only use this if :const:`daylight` is nonzero.
   See the `note on timezone constants`_.

.. Reviewed by PLM 20210917
.. Reviewed by TechComms 20211013

.. data:: daylight

   Nonzero if a DST timezone is defined.  See the `note on timezone constants`_.

.. Reviewed by PLM 20210917
.. Reviewed by TechComms 20211013

.. data:: timezone

   The offset of the local (non-DST) timezone, in seconds, west of UTC
   (negative in most of Western Europe, positive in the USA, zero in the UK).
   See the `note on timezone constants`_.

.. Reviewed by PLM 20210917
.. Reviewed by TechComms 20211013

.. data:: tzname

   A tuple of two strings:

   - Name of the local non-DST timezone
   - Name of the local DST timezone

   If no DST timezone is defined, the second string should not be used.
   See the `note on timezone constants`_.

.. note::
   :name: note on timezone constants

   For the above timezone constants (:data:`altzone`, :data:`daylight`, :data:`timezone`,
   and :data:`tzname`), the value is determined by the timezone configuration in effect
   at module load time or the last time :func:`tzset` is called, and may be incorrect for
   times in the past. Nokia recommends using the :attr:`tm_gmtoff` and :attr:`tm_zone`
   results from :func:`localtime` to obtain timezone information.

.. note::
   :name: epoch

   The `epoch`_ on Nokia SR OS is January 1, 1970, 00:00:00 (UTC).  Leap
   seconds are not counted towards the time in seconds since the `epoch`_.
   This is commonly referred to as `UNIX time <https://en.wikipedia.org/wiki/Unix_time>`_.


