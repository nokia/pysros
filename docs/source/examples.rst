.. _pysros-examples:

********
Examples
********

This section provides examples and background information to assist developers to maximize their use of the
pySROS libraries.

.. note::

   There are multiple ways in Python to achieve the requirements of an application.  Examples shown
   are suggestions only; actual usage may differ depending on supported functionality and user configuration.

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


pySROS data structures
######################

Having made a connection to an SR OS device it is important to understand the data structures returned by the
:py:meth:`pysros.management.Datastore.get` function and those that can be sent to a router using
:py:meth:`pysros.management.Datastore.set`.

As described in the :ref:`pysros-data-model` section, data obtained from and sent to an SR OS device are described
in a format referred to as a pySROS data structure.

This section provides some example outputs of the data structures for the respective YANG constructs.

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902

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

To obtain the data only (excluding the wrapper), call ``.data`` on the obtained object.

.. code-block:: python3
   :name: yang-leaf-py3-struct-data-ex1
   :caption: Obtaining the data from a YANG leaf data structure
   :emphasize-lines: 2

   >>> pysros_ds.data
   'sros'

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902

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

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902

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

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


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

The key of the YANG list (``listkey``) is a child element of the list (``listname``)
itself.  Without knowledge of the structure of the specific YANG list, a developer would need to have an external
reference to be able to identify the key of the list to iterate through it or to reference specific items.
For this reason, the pySROS libraries translate YANG lists into Python dictionaries keyed on the values of the list
key (``listkey``) as opposed to Python lists.

The element ``/nokia-conf:configure/log/log-id`` is a YANG list in the ``nokia-conf`` YANG module.  The YANG list name
is ``log-id`` and the YANG list's key is ``name``.

.. note::

   The key of a YANG list can be identified using context-sensitive help within SR OS, from the YANG module or by
   obtaining the ``pwc json-instance-path`` of an element in the YANG list, for example,
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

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Configuring YANG lists
----------------------
YANG lists may be configured using the pySROS libraries in many ways.

Assume the target configuration of the ``log-id`` list on SR OS is in the :ref:`sros-example-log-config` as shown in the preceding example.

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

Configure the specific items in the list with a payload that is a Python dictionary containing the contents
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

Configure the specific items in the list with a payload that is a Python dictionary containing the contents
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

These examples are available in a single Python file :download:`here <../../examples/set_list.py>`


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


.. _pysros-examples-user-ordered-list-structure:

YANG user-ordered list structure
********************************
A user-ordered list is similar to a :ref:`pysros-examples-list-structure`.

Python dictionaries are not order aware.  This is not important for most configuration items in the SR OS
model-driven interfaces as SR OS ensures the required order is identified and achieved automatically.
However, some specific lists in SR OS are order dependent, such as policies.

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


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902

.. _pysros-examples-connecting-to-md-interfaces:

Connecting to the SR OS model-driven interface
##############################################

Connecting when executing on a remote workstation
*************************************************

To access the model-driven interface of SR OS when executing a Python application from a remote workstation, use
the :py:meth:`pysros.management.connect` method.  Examples are shown in the method documentation.

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

.. note:: The preceding examples show the minimum Python code required to connect to the SR OS model-driven interfaces of
          a device.
          See the :ref:`pysros-examples-handling-exceptions` section to ensure potential error scenarios in the
          connection process are handled cleanly in your application and see the :py:meth:`pysros.management.connect`
          documentation for more detailed examples.

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


.. _pysros-examples-handling-exceptions:

Handling exceptions
###################

Python provides the ability to handle error situations through the use of *exceptions*.  The pySROS libraries
provide a number of exceptions that are detailed within the :py:mod:`pysros` module documentation.

The following is an example of how to use these exceptions to handle specific error scenarios:

.. literalinclude:: ../../examples/make_connection.py
   :caption: make_connection.py
   :name: make-connection-example
   :language: python
   :emphasize-lines: 16-17, 26-64

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Obtaining data and formatted output
###################################

This section provides some examples of obtaining data from SR OS and printing that data in
various formats.

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Show SDP state and descriptions
*******************************

This examples creates a new show command that displays a list of the SDPs and their ID, description,
administrative state, operational state, and far-end IP address.

This example demonstrates how to obtain data from various locations in the configure and state tree structure of
SR OS, how to manipulate and correlate this data, and how to use the :py:class:`pysros.pprint.Table` class to
create SR OS style table output.

.. literalinclude:: ../../examples/show_sdp_with_description.py
   :caption: show_sdp_with_description.py
   :name: show-sdp-with-description-example
   :language: python
   :emphasize-lines: 12, 52-70, 84-94

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


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Efficient YANG list key handling
********************************

There are occasions where a set of specific entries in a YANG list are required.
In these situations, use one of the following to obtain the key values for the list.

- Obtain the list from the node which is stored as a Python *dict* and then use ``.keys()`` on the
  dict to obtain the key values.
- Use the :py:func:`pysros.management.Datastore.get_list_keys` function to obtain the list of the key values without
  obtaining the full data structure of the YANG list.

Using the :py:func:`pysros.management. Datastore.get_list_keys` function is significantly
faster and uses less memory.

The following example compares and contrasts the different methods.

.. literalinclude:: ../../examples/get_list_keys_usage.py
   :caption: get_list_keys_usage.py
   :name: get-list-keys-usage-example
   :language: python

The example output for this application is shown here:

.. code-block:: none

   get without defaults
    Output: dict_keys(['Base']) Time: 0.1393
   get with defaults
    Output: dict_keys(['Base', 'management', 'vpls-management']) Time: 0.7754
   get_list_keys without defaults
    Output: ['Base'] Time: 0.0859
   get_list_keys with defaults
    Output: ['Base', 'management', 'vpls-management'] Time: 0.1171

.. Reviewed by PLM 20220114
.. Reviewed by TechComms 20220124


Multi-device hardware inventory
*******************************

This example is created to be executed on a remote workstation.  It connects to the devices that are
supplied on input and obtains the hardware inventory from the chassis and line cards that can be used
with external systems, with the output in JSON format.

.. literalinclude:: ../../examples/get_inventory_remotely.py
   :caption: get_inventory_remotely.py
   :name: get-inventory-remotely-example
   :language: python

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Local language output
*********************

This example demonstrates the ability to display unicode (UTF-8) characters on SR OS.  This allows
for the addition of local language personalization for developers.

.. literalinclude:: ../../examples/local_language_output.py
   :caption: local_language_output.py
   :name: local-language-output-example
   :language: python


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Filesystem access
#################

Filesystem access is provided to the local SR OS filesystem using the standard Python 3 methods.
Specific adaptations have been provided for some libraries.  See :py:mod:`uio`, :py:mod:`uos`
and :py:mod:`uos.path` for more information.

.. note::

   Filesystem access is provided using the SR OS profile of the executing user and respects
   any permissions or restrictions therein.

.. important::

   Python applications triggered from EHS and CRON have system access to the filesystem.

The ability to read and write to the filesystem provides many possibilities to the developer, including
the ability to maintain a persistent state between executions.  This enables a developer
to choose to evaluate something based on the last time the application was run, in addition to the
instantaneous data available.

.. literalinclude:: ../../examples/filesystem_example.py
   :caption: filesystem_example.py
   :name: filesystem-example
   :language: python
   :emphasize-lines: 18-60

The example output of this application is shown below.

.. code-block:: none

   [/]
   A:admin@sros# pyexec filesystem_example.py
   This command has been run 20 times
   Number of received octets for BGP peer 5.5.5.2 (last run/this run): 205754 / 209022
   The difference between the last run and this run is: 3268

   [/]
   A:admin@sros# pyexec filesystem_example.py
   This command has been run 21 times
   Number of received octets for BGP peer 5.5.5.2 (last run/this run): 209022 / 209022
   The difference between the last run and this run is: 0

   [/]
   A:admin@sros# pyexec filesystem_example.py
   This command has been run 22 times
   Number of received octets for BGP peer 5.5.5.2 (last run/this run): 209022 / 209041
   The difference between the last run and this run is: 19

.. Reviewed by PLM 20220630
.. Reviewed by TechComms 20220706



Further examples
################

Additional example are located in the examples directory of the source repository available on
`GitHub <https://github.com/nokia/pysros>`_.

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902

