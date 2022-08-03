:mod:`uos.path` -- Filesystem functions
=======================================

.. module:: uos.path
   :synopsis: Filesystem operations on paths.

This module contains miscellaneous functions on filesystem paths.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

Functions
---------

.. function:: isfile(path)

   Check if a ``path`` to a file is an existing regular file.

   :param path: Full path to the file.
   :type path: str
   :returns: ``True`` if the ``path`` is an :func:`existing <exists>` regular file.
   :rtype: bool

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

.. function:: isdir(path)

   Check if a ``path`` to a directory is an existing directory.

   :param path: Full path to the directory.
   :type path: str
   :returns: ``True`` if the ``path`` is an :func:`existing <exists>` directory.
   :rtype: bool

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

.. function:: exists(path)

   Check if a ``path`` is an existing file or directory.

   :param path: Full path to the file or directory.
   :type path: str
   :returns: ``True`` if the ``path`` references an existing file or directory.
   :rtype: bool

   .. note::

      This function may return ``False`` if permission is not granted to execute
      :func:`os.stat` on the requested file, even if the ``path`` exists.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

