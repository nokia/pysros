
The :mod:`pysros.esm` module provides functionality obtain data from the
specific event that triggered the execution of a Python application from
the SR OS subscriber management system.

.. Reviewed by PLM 20240828

.. note:: This module is available when executing on SR OS only. On a remote
          machine, subscriber management functionality is not supported.

.. Reviewed by PLM 20240828

.. py:function:: pysros.esm.get_event

   The subscriber management event that triggered the execution of the Python application.

   :return: The Event object or None.
   :rtype: :py:class:`pysros.esm.Event` or ``None``

   .. Reviewed by PLM 20240828

.. class:: pysros.esm.Event

   The ESM :py:class:`pysros.esm.Event` Class for the event that triggered the execution of the
   Python application.

   .. py:attribute:: eventparameters

      The additional parameters specific to the event that caused the
      Python application to execute.

      :type: :py:class:`pysros.ehs.EventParams`

      .. Reviewed by PLM 20240828

.. class:: pysros.esm.EventParams

   The additional parameters of the specific :py:class:`pysros.esm.Event`.
   This class is *read-only*.  Specific additional parameters may be
   accessed using standard Python subscript syntax.

   .. Reviewed by PLM 20240828

   .. py:method:: keys

      Obtain the additional parameters names.

      :return: Additional parameters names for the Event.
      :rtype: tuple(str)

      .. Reviewed by PLM 20240828

   .. describe:: params[key]

      Return the value of the parameter *key*. If the parameter does not exist,
      a :exc:`KeyError` is raised.

      .. Reviewed by PLM 20240828



