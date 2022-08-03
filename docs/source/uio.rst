:mod:`uio` -- Input/Output stream functions
===========================================

.. module:: uio
   :synopsis: input/output streams

This module contains functions and types to work with file objects
and other objects similar to files.

.. admonition:: Differences to CPython
   :class: attention

   This module implements a simplified conceptual hierarchy of stream base
   classes when compared to the CPython implementation.

   CPython defines a number of base stream classes which serve as the
   foundation for the behaviour of the main classes.  The SR OS implementation
   does not define these abstract base classes.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

Returned object types
---------------------

The :py:func:`open` function can be used to open a file. Based on the arguments used
when this function is called, either a :py:class:`TextIO` or a :py:class:`FileIO` object
is returned.  In both cases, the object has the same set of
functions defined, but may have different behaviors depending on the
type of object.

All functions are documented based on the :py:class:`TextIO` class, however,
they also apply to the :py:class:`FileIO` class.
Any differences are documented explicitly.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

Functions
---------

.. function:: open(name, mode='r', buffering=-1, newline=None)

   Open a file. The builtin ``open()`` function is aliased to this function.

   Open a file and return a corresponding file object.

   :param name: Absolute name and path to the file that is opened.
   :type name: bytes or str

   :param mode: Mode in which the file is opened.  Supported file modes are shown in the
                :ref:`filemodes` section.  Default ``r`` which is a synonym of ``rt`` (open for
                reading text).
   :type mode: str, optional

   :param buffering: Set the buffering policy.  ``0`` disables buffering (only allowed in binary
                      mode).  An integer > ``0`` indicates the size, in bytes, of a fixed-size chunk buffer.
                      When no ``buffering`` argument is given, the file is buffered in chunks.
   :type buffering: int, optional

   :param newline: Control the behavior of universal newlines mode.  Only applies to
                   :py:class:`TextIO` mode.  Accepted options: ``None``, empty string, ``\n``,
                   ``\r``, and ``\r\n``.  See the :ref:`newlines` section for more information.
   :type newline: None or str, optional


   :returns: File object.  The type of file object returned by the :py:func:`open` function
             depends on the mode.  When :py:func:`open` is used to open a file in a text
             mode (``w``, ``r``, ``wt``, ``rt``, etc.), it returns an instance of
             :py:class:`uio.TextIO`.  When used to open a file in a binary mode an instance
             of :py:class:`uio.FileIO` is returned, regardless of buffering mode.
   :rtype: :py:class:`TextIO` or :py:class:`FileIO`

   :raises OSError: File cannot be opened.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

.. _filemodes:

Supported file modes
********************

The supported file modes for SR OS are:

   ========= ===============================================================
   Character Meaning
   ========= ===============================================================
   ``r``     Open for reading (Default)
   ``w``     Open for writing, truncating the file first
   ``a``     Open for writing, appending to the end of file if it exists
   ``b``     Binary mode
   ``t``     Text mode (Default)
   ``+``     Open for updating (reading and writing)
   ========= ===============================================================

.. note::

   The default mode is ``r`` which is a synonym of ``rt`` (open for reading text).
   Other common values are ``w`` for writing (truncating the file if it
   already exists) and ``a`` for appending.

.. note::

   Modes ``w+`` and ``w+b`` open and truncate the file.  Modes ``r+``
   and ``r+b`` open the file with no truncation.

Python distinguishes between binary and text I/O.

Files opened in binary mode (including ``b`` in the ``mode`` argument of the
:py:func:`open` function) return data as :py:class:`bytes` objects without any decoding.

Files opened in text mode (which is the default, or when ``t`` is explicitly included in
the ``mode`` argument of the :py:func:`open` function) are returned as :class:`str`, the
bytes having been first decoded as UTF-8.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

.. _newlines:

Newline behavior
****************

The behavior of newlines in the :py:func:`open` function depends on the input provided to the
``newline`` argument.

When reading input from the stream:

* If the ``newline`` argument is set to ``None``, universal newlines mode is enabled.
  Lines in the input can end in ``\n``, ``\r`` or ``\r\n``.  These are translated into
  ``\n`` before being returned to the caller.
* If the ``newline`` argument is set to an empty string, universal newlines mode is enabled,
  however, line endings are returned to the caller without translation.
* If the ``newline`` argument has any other legal values, input lines are only terminated
  by the given string and the line ending is returned to the caller without translation.

When writing output to the stream:

* If the ``newline`` argument is ``None``, any ``\n`` characters written are translated
  to the system default line separator, :data:`os.linesep`.
* If the ``newline`` argument is an empty string or ``\n``, no translation takes place.
* If the ``newline`` argument is any other legal value, any ``\n`` characters written
  are translated to the given string.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706


Classes
-------

.. note::

   Where a method definition has a ``/`` as the last argument, the method takes only
   positional arguments.  See `PEP 570 <https://peps.python.org/pep-0570>`_ for more details.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

.. class:: TextIO

   Text mode object obtained by using the :py:func:`open` function, for example ``open(name, "rt")``.

   .. warning::

      This class cannot be instantiated directly.  Use the :py:func:`open` function.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: read(size=-1, /)

      Read at most ``size`` characters from stream. If ``size`` is a negative number or omitted,
      read until the end of the file (EOF).

      :param size: Maximum number of characters to read from the stream.  Default ``-1``.
      :type size: int, optional
      :raises OSError: File is not readable.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: readinto(b, size=None, /)

      Read bytes into a pre-allocated, writable, bytes-like object ``b``.

      :param b: Pre-allocated, writable bytes-like object.
      :type b: bytes
      :param size: The maximum size of bytes to read from the stream.  Default ``None``.
      :type size: int, optional

      :returns: Number of bytes read.
      :rtype: int

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: write(text, /)

      Write the provided text to the stream.

      :param text: String to be written to the file.
      :type text: str

      :returns: Number of characters written.
      :rtype: int
      :raises OSError: File is not writable.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: seek(offset, whence=0, /)

      Change the stream position to the given byte ``offset`` relative to the position
      indicated by ``whence``.

      :param offset: Byte offset from ``whence``.
      :type offset: int
      :param whence: Starting position.  Accepted values:

                        * ``0`` -- Seek from the start of the stream.  ``offset`` must either
                          be a number returned by :py:meth:`tell`, or ``0``. Any other
                          offset value produces undefined behaviour.
                        * ``1`` -- Seek to the current position.  ``offset`` must be ``0``, which
                          is a no-operation.  All other values of ``offset`` are unsupported.
                        * ``2`` -- Seek to the end of the stream.  ``offset`` must be ``0``.
                          All other values of ``offset`` are unsupported.

                     Default ``0``.
      :type whence: int, optional
      :returns: New absolute position.
      :rtype: int
      :raises OSError: File does not support random access.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: tell()

      Obtain the current streams position.

      :returns: Current stream position.
      :rtype: int
      :raises OSError: File does not support random access.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: flush()

      Flush the write buffers, if applicable.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: close()

      Flush and close the IO object.

      This method has no effect if the file is already closed.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: writelines(lines, /)

      Write a list of lines to stream.

      Line separators are not added. It is normal for each of the lines provided
      to have a line separator at the end.

      :param lines: List of lines to be written.
      :type lines: list

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: readline(size=-1, /)

      Read until a newline is found or until the end of the file is reached.  Return a
      string containing a single line.

      :param size: Maximum number of characters to be read.
      :type size: int, optional
      :returns: A single string containing the required line.  If the stream is already at
                the end of the file (EOF), an empty string is returned.
      :rtype: str

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: readlines(hint=-1, /)

      Return a list of lines from the stream.

      :param hint: No more lines are read if the accumulated total size (in bytes or characters) of
                   all the lines exceeds the value specified in ``hint``.  This can be
                   used to control the number of lines read.
      :type hint: int, optional
      :returns: List of lines
      :rtype: list

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706


   .. method:: readable()

      Return whether object is opened for reading.

      :returns: Whether the file is readable.  ``True`` indicates that the file can be 
               read, ``False`` indicates that it cannot.
      :rtype: bool

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: writable()

      Return whether object is opened for writing.

      :returns: Whether the file is writable.  ``True`` indicates that the file can be written to,
                ``False`` indicates that.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: seekable()

      Return whether the object supports random access.  This method may perform a test :py:meth:`seek`.

      :returns: Whether the file supports random access (is seekable).  ``True`` if random access
                is supported.  ``False`` if not.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. method:: truncate(size=None, /)

      Truncate file to size bytes.

      .. note::

         The file pointer is left unchanged.

      :param size: Size to truncate the file to.  Defaults to ``None`` which is interpreted as the
                   current seek position as reported by :py:meth:`tell`.
      :type size: int, optional
      :returns: The new size of the file.

      :raises OSError: File does not support random access.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

   .. attribute:: buffered
      :type: bool

   .. attribute:: closed
      :type: bool

   .. attribute:: mode
      :type: str

   .. attribute:: name
      :type: str

   .. attribute:: newlines
      :type: str or None

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

.. class:: FileIO

   File mode object obtained by using the :py:func:`open` function, for example ``open(name, "rb")``.

   .. warning::

      This class cannot be instantiated directly. Use the :py:func:`open` function.

   .. important::

      The same methods as defined on :py:class:`TextIO` are supported on :py:class:`FileIO`.
      Any differences are documented below.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

   .. method:: seek(offset, whence=0, /)

      Change the stream position to the given byte ``offset`` relative to the position
      indicated by ``whence``.

      :param offset: Byte offset from ``whence``.
      :type offset: int
      :param whence: Starting position.  Accepted values:

                        * ``0`` -- Seek from the start of the stream.  ``offset`` should be ``0``
                          or a positive integer.
                        * ``1`` -- Seek to the current position.  ``offset`` may be a negative
                          integer.
                        * ``2`` -- Seek to the end of the stream.  ``offset`` is usually a negative
                          integer.

                     Default ``0``.
      :type whence: int, optional
      :returns: New absolute position.
      :rtype: int
      :raises OSError: The file does not support random access.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706

.. class:: StringIO([string])

   In-memory file-like object for input/output use for text-mode I/O, similar to a normal file
   opened with ``t`` file mode (See :ref:`filemodes` for more information).

   :param string: Initial contents of the file-like object.
   :type string: str

   :raises OSError: File-like object cannot be created.

   .. important::

      The same methods as defined on :py:class:`TextIO` are supported on :py:class:`StringIO`.
      Any differences or additions are documented below.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

   .. method:: getvalue()

      Obtain the current contents of the underlying buffer that holds data.

      :returns: Contents of the underlying buffer.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706


.. class:: BytesIO([string])

   In-memory file-like object for input/output use for binary-mode I/O, similar to a normal file
   opened with the ``b`` file mode (See :ref:`filemodes` for more information).

   :param string: Initial contents of the file-like object.
   :type string: bytes

   :raises OSError: File-like object cannot be created.

   .. important::

      The same methods as defined on :py:class:`TextIO` are supported on :py:class:`BytesIO`.
      Any differences or additions are documented below.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

   .. method:: getvalue()

      Obtain the current contents of the underlying buffer that holds data.

      :returns: Contents of the underlying buffer.

   .. Reviewed by PLM 20220628
   .. Reviewed by TechComms 20220706


.. class:: StringIO(alloc_size)
   :noindex:

   Create an empty :py:class:`StringIO` object, pre-allocated to consume ``alloc_size`` bytes.
   With this method, writing the specific amount of bytes does not lead to reallocation
   of the buffer and therefore does not result in out-of-memory or memory-fragmentation issues.

   .. warning::

      This constructor is a specific MicroPython extension and is recommended for use only
      in special cases and in system-level libraries.  It is not recommended for use in
      end-user applications.

   :param alloc_size: Amount of memory to pre-allocate (consume).
   :type alloc_size: bytes

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706


.. class:: BytesIO(alloc_size)
   :noindex:

   Create an empty :py:class:`BytesIO` object, pre-allocated to consume ``alloc_size`` bytes.
   With this method, writing the specific amount of bytes does not lead to reallocation
   of the buffer and therefore does not result in out-of-memory or memory-fragmentation issues.

   .. warning::

      This constructor is a specific MicroPython extension and is recommended for use only
      in special cases and in system-level libraries.  It is not recommended for use in
      end-user applications.

   :param alloc_size: Amount of memory to pre-allocate (consume).
   :type alloc_size: bytes

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706