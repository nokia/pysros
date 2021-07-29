.. sectionauthor:: jcumming

.. _pysros-examples:

********
Examples
********

This section provides examples and background information to assist developers to maximize their use of the
pySROS libraries.

.. note::

   There are multiple ways in Python to achieve the requirements of an application.  These examples
   should not be considered as the correct or recommended way.  These examples should be used as an
   example of one way to achieve a result.



pySROS data structures
######################

Having made a connection to an SR OS device it is important to understand the data structures returned by the
:py:meth:`pysros.management.Datastore.get` function and those that can be sent to a router using
:py:meth:`pysros.management.Datastore.set`.

As described in the :ref:`pysros-data-model` section, data obtained from and sent to an SR OS device are described
in a format referred to as a pySROS data structure.

This section provides some example outputs of the data structures for the respective YANG constructs.

.. _pysros-examples-leaf-structure:

YANG leaf structure
*******************

A YANG leaf is wrapped in the :py:class:`pysros.wrappers.Leaf` class.  The following example obtains a YANG leaf from
SR OS using the :py:meth:`pysros.management.Datastore.get` method.

.. code-block:: python3
   :name: yang-leaf-py3-struct-ex1
   :caption: Obtaining the YANG leaf data structure
   :emphasize-lines: 5

   >>> from pysros.management import connect
   >>> c = connect()
   >>> pysros_ds = c.running.get("/nokia-conf:configure/system/name")
   >>> pysros_ds
   Leaf('sros')

To obtain just the data (excluding the wrapper), call ``.data`` on the obtained object.

.. code-block:: python3
   :name: yang-leaf-py3-struct-data-ex1
   :caption: Obtaining the data from a YANG leaf data structure
   :emphasize-lines: 2

   >>> pysros_ds.data
   'sros'

.. _pysros-examples-container-structure:

YANG container structure
************************

A YANG container is wrapped in the :py:class:`pysros.wrappers.Container` class.  The following example obtains a
YANG container from SR OS using the :py:meth:`pysros.management.Datastore.get` method.

.. code-block:: python3
   :name: yang-container-py3-struct-data-ex1
   :caption: Obtaining the data from a YANG container data structure
   :emphasize-lines: 5

   >>> from pysros.management import connect
   >>> c = connect()
   >>> data = c.running.get('/nokia-state:state/router[router-name="Base"]/sfm-overload')
   >>> data
   Container({'state': Leaf('normal'), 'start': Leaf('2021-06-21T19:35:17.3Z'), 'time': Leaf(0)})

.. note:: State information is obtained by targeting the *running* datastore

.. _pysros-examples-leaflist-structure:

YANG leaf-list structure
************************

A YANG leaf-list is wrapped in the :py:class:`pysros.wrappers.LeafList` class.  The following example obtains a
YANG container from SR OS using the :py:meth:`pysros.management.Datastore.get` method.

.. code-block:: python3
   :name: yang-leaflist-py3-struct-data-ex1
   :caption: Obtaining the data from a YANG leaf-list data structure
   :emphasize-lines: 5

   >>> from pysros.management import connect
   >>> c = connect()
   >>> data = c.running.get('/nokia-conf:configure/router[router-name="Base"]/bgp/neighbor[ip-address="5.5.5.2"]/import/policy')
   >>> data
   LeafList(['demo', 'example-policy-statement'])

.. note:: The order of the entries in a leaf-list is important.  Lists in Python are order aware.

.. _pysros-examples-list-structure:

YANG list structure
*******************

A YANG list is represented as a Python dict, as noted in the :ref:`pysros-data-model` section.

YANG lists define three elements:

- a list name
- a list key
- a set of key-values

The YANG module :ref:`example-yang` shown below, demonstrates this:

.. literalinclude:: ../../examples/example.yang
   :caption: example.yang
   :name: example-yang
   :language: yang

As you can see in the YANG module, the YANG list's key (``listkey``) is a child element of the list (``listname``)
itself.  Without knowledge of the structure of the specific YANG list, a developer would need to have an external
reference to be able to identify the key of the list in order to iterate through it or to reference specific items in it.
For this reason, the pySROS libraries translate YANG lists into Python dictionaries keyed on the values of the list
key (``listkey``) as opposed to Python lists.

The element ``/nokia-conf:configure/log/log-id`` is a YANG list in the ``nokia-conf`` YANG module.  The YANG list name
is ``log-id`` and the YANG list's key is ``name``.

.. note::

   The YANG list's key can be identified using context-sensitive help within SR OS, from the YANG module or by
   obtaining the ``pwc json-instance-path`` of an element in the YANG list, for example
   ``/nokia-conf:configure/log/log-id[name="10"]``.

Consider the following router configuration:

.. code-block:: none
   :name: sros-example-log-config
   :caption: SR OS example log configuration

   /configure log log-id "10" { }
   /configure log log-id "10" { description "Log ten" }
   /configure log log-id "11" { }
   /configure log log-id "11" { description "Log eleven" }

If this list is obtained using :py:meth:`pysros.Datastore.get` for the list ``log-id``, the resultant data structure
is a Python dictionary, keyed on the values of the ``log-id`` list's key, ``name``:

.. code-block:: python
   :name: yang-list-py3-struct-data-ex1
   :caption: Obtaining the data from a YANG list data structure
   :emphasize-lines: 5-6

   >>> from pysros.management import connect
   >>> c = connect()
   >>> data = c.running.get('/nokia-conf:configure/log/log-id')
   >>> data
   {'10': Container({'description': Leaf('Log ten'), 'name': Leaf('10')}),
    '11': Container({'description': Leaf('Log eleven'), 'name': Leaf('11')})}


Configuring YANG lists
----------------------
YANG lists may be configured using the pySROS libraries in many ways.

Assuming the target configuration of the ``log-id`` list on SR OS is as shown above in the :ref:`sros-example-log-config`.

This is a YANG list named ``log-id``, with one key name (``name``) and two key-values, ``10`` and ``11``.

Method 1
^^^^^^^^

Configure the list with a payload that is a Python dictionary keyed on the YANG list key-value:

.. code-block:: python
   :name: yang-list-py3-set-ex1
   :caption: Configure YANG list using Python dict payload without key name
   :emphasize-lines: 2-3

   >>> c = connect()
   >>> path = '/nokia-conf:configure/log/log-id'
   >>> payload = {'10': {'description': 'Log ten'}, '11': {'description': 'Log eleven'}}
   >>> c.candidate.set(path, payload)


Method 2
^^^^^^^^

Configure the specific items in the list with a payload that is a Python dictionary containing just the contents
of that list item *without* the key name and key-value information (The list's key name and key-value are supplied
in the ``path``).

.. code-block:: python
   :name: yang-list-py3-set-ex2
   :caption: Configure each YANG list entry in turn providing the key and key-value in the path
   :emphasize-lines: 2, 4-5

   >>> c = connect()
   >>> list_entries = [("10", "Log ten"), ("11", "Log eleven")]
   >>> for item in list_entries:
   >>>     payload = {'description': item[1]}
   >>>     path = '/nokia-conf:configure/log/log-id[name=' + item[0] + ']'
   >>>     c.candidate.set(path, payload)


Method 3
^^^^^^^^

Configure the specific items in the list with a payload that is a Python dictionary containing just the contents
of that list item *with* the key name and key-value information provided (The list's key name and key-value are
also supplied in the ``path``).  In this case, the contents of the payload dictionary for key name and key-value
**must** match the data provided in the ``path``.

.. code-block:: python
   :name: yang-list-py3-set-ex3
   :caption: Configure each YANG list entry in turn providing the key and key-value in the path *and* payload
   :emphasize-lines: 2, 4-5

   >>> c = connect()
   >>> list_entries = [("10", "Log ten"), ("11", "Log eleven")]
   >>> for item in list_entries:
   >>>     payload = {'name': item[0], 'description': item[1]}
   >>>     path = '/nokia-conf:configure/log/log-id[name=' + item[0] + ']'
   >>>     c.candidate.set(path, payload)

These examples are available in a single Python file :download:`here <../../examples/setList.py>`



.. _pysros-examples-user-ordered-list-structure:

YANG user-ordered list structure
********************************
A user-ordered list is very similar to a :ref:`pysros-examples-list-structure`.

Python dictionaries are not order aware.  This is not of concern for most configuration items in the SR OS
model-driven interfaces as SR OS ensures the required order is identified and achieved automatically,
however, some specific lists in SR OS are order dependent.  One such example is policies.

User-ordered lists are therefore represented as ordered dictionaries in Python.

.. code-block:: python
   :name: yang-user-ordered-list-py3-struct-data-ex1
   :caption: Obtaining the data from a user-ordered YANG list data structure
   :emphasize-lines: 5-6

   >>> from pysros.management import connect
   >>> c = connect()
   >>> data = c.running.get('/nokia-conf:configure/policy-options/policy-statement[name="example-policy-statement"]/named-entry')
   >>> data
   OrderedDict({'one': Container({'entry-name': Leaf('one'), 'action': Container({'action-type': Leaf('accept')})}),
                'three': Container({'entry-name': Leaf('three'), 'action': Container({'action-type': Leaf('accept')})})})


.. _pysros-examples-connecting-to-md-interfaces:

Connecting to the SR OS model-driven interface
##############################################

Connecting when executing on a remote workstation
*************************************************

To access the model-driven interface of SR OS when executing a Python application from a remote workstation, use
the :py:meth:`pysros.management.connect` method.  Examples are show in the method documentation.

Connecting when executing on SR OS
**********************************

To access the model-driven interface of SR OS when executing a Python application on SR OS, use the
:py:meth:`pysros.management.connect` method.  The arguments to this method are ignored when executing on SR OS and
therefore the following two examples perform the same operation:

.. code-block:: python
   :name: connect-on-box-example-1
   :caption: Connecting to the model-driven interfaces when executing on SR OS - example 1
   :emphasize-lines: 2

   from pysros.management import connect
   c = connect()


.. code-block:: python
   :name: connect-on-box-example-2
   :caption: Connecting to the model-driven interfaces when executing on SR OS - example 2
   :emphasize-lines: 2-4

   from pysros.management import connect
   c = connect(host="192.168.74.51",
               username="admin",
               password="admin")

.. note:: The above examples show the minimum Python code required to connect to the SR OS model-driven interfaces of
          a device.
          See the :ref:`pysros-examples-handling-exceptions` section to ensure potential error scenarios in the
          connection process are handled cleanly in your application and the :py:meth:`pysros.management.connect`
          documentation for more detailed examples.


.. _pysros-examples-handling-exceptions:

Handling exceptions
###################

Python provides the ability to handle error situations through the use of *exceptions*.  The pySROS libraries
provide a number of exceptions that are detailed within the :py:mod:`pysros` module documentation.

The following is an example of how to use these exceptions in order to handle specific error scenarios:

.. literalinclude:: ../../examples/makeConnection.py
   :caption: makeConnection.py
   :name: make-connection-example
   :language: python
   :emphasize-lines: 16-21, 23-29, 31-38, 40-45

Obtaining data and formatted output
###################################

This section provides some examples of obtaining data from SR OS and printing that data in
various formats.

Show SDP state and descriptions
*******************************

This examples creates a new show command that displays a list of the SDPs and their ID, description,
administrative state, operational state, and far-end IP address.

This example demonstrates how to obtain data from various locations in the configure and state tree structure of
SR OS, how to manipulate and correlate this data, and how to use the :py:class:`pysros.pprint.Table` class to
create SR OS style table output.

.. literalinclude:: ../../examples/showSdpWithDescription.py
   :caption: showSdpWithDescription.py
   :name: show-sdp-with-description-example
   :language: python
   :emphasize-lines: 10-11, 41-58, 66-110

The example output for this application is shown here:

.. code-block:: none

   ===============================================================================
   Service Destination Points with Descriptions
   ===============================================================================
   ID         Description          Adm        Opr        Far End
   -------------------------------------------------------------------------------
   44         None                 enable     down       5.5.5.2
   -------------------------------------------------------------------------------
   No. of SDP: 1
   ===============================================================================



Multi-device hardware inventory
*******************************

This example is created to be executed on a remote workstation.  It connects to the devices that are
supplied on input and obtains the hardware inventory from the chassis and line cards displaying the
output in JSON that can be used with external systems.

.. literalinclude:: ../../examples/getInventoryRemotely.py
   :caption: getInventoryRemotely.py
   :name: get-inventory-remotely-example
   :language: python
   :emphasize-lines: 1

