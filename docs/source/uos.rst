:mod:`uos` -- Filesystem functions
==================================

.. module:: uos
   :synopsis: Filesystem functions.

This module contains miscellaneous operating system functions.

.. warning::

   All filesystem operations accept absolute paths only and will raise a
   :exc:`ValueError` when passed an invalid path.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706


Functions
---------

.. function:: listdir(path)

   Obtain a list of names or the entries in the provided directory.

   If the ``path`` is provided in type ``bytes``, the filenames returned are
   also of type ``bytes``; otherwise they are of type ``str``.

   .. note::

      The list is in an arbitrary order and does not include special entries such
      as ``.`` and ``..``, even if they are present in the directory.  If a file is
      removed from or added to the directory during this function call, its
      appearance or otherwise is undetermined.

   :param path: Full path to the directory.
   :type path: str or bytes
   :returns: List containing the names of the entries in the directory.
   :rtype: str or bytes

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

.. function:: mkdir(path, mode=None)

   Create a directory.

   :param path: Full path to the new directory.
   :type path: str
   :param mode: *This parameter is ignored and is only present to ensure compatibility.*
   :type mode: optional
   :raises FileExistsError: Directory already exists.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

.. function:: remove(path)

   Remove (delete) a file.

   :param path: Full path to the file.
   :type path: str
   :raises IsADirectoryError: The provided ``path`` is a directory rather than a file.
                              Use :py:func:`rmdir` to remove directories.
   :raises FileNotFoundError: File does not exist.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706

.. function:: rmdir(path)

   Remove (delete) a directory.

   :param path: Full path to the directory.
   :type path: str
   :raises FileNotFoundError: The directory does not exist.
   :raises OSError: Directory is not empty.

.. Reviewed by PLM 20220628
.. Reviewed by TechComms 20220706