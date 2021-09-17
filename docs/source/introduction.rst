.. _overview:

********
Overview
********

Introduction
############

The pySROS libraries provide a model-driven management interface for
Python developers to integrate with supported Nokia routers
running the Service Router Operating System (SR OS).

The libraries provide an Application Programming Interface (API) for developers
to create applications that can interact with Nokia SR OS devices, whether those
applications are executed from a development machine, a remote server, or directly on the router.

When a developer uses only libraries and constructs supported on SR OS, a
single application may be executed from a development machine or ported
directly to an SR OS node where the application is executed without modification.

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902



License
#######

The license is located :download:`here <../../LICENSE.md>`.

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Pre-requisites
##############

To use the pySROS libraries, the following pre-requisites must be met:

- one or more SR OS nodes

  - Running in model-driven management interface configuration mode
  - Running SR OS 21.7.R1 or greater (to execute applications on the SR OS device)
  - With NETCONF enabled and accessible by an authorized user (to execute applications
    remotely)

- a Python 3 interpreter of version 3.6 or newer when using the pySROS libraries to
  execute applications remotely

All the required software is included and installed automatically on the SR OS node, including
the Python 3 interpreter and all supported Python libraries.

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


YANG modeling
#############

It is assumed that the developer has a working knowledge of model-driven
management in a networking environment and of YANG models and their constituent
parts.

The `Nokia YANG models are available for each release of SR OS on GitHub <https://github.com/nokia/7x50_YangModels>`_.

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


.. _modeled-paths:

Modeled paths
**************

At the root of the pySROS libraries is Nokia's model-driven management concepts
built into SR OS.

Communication between applications developed using the pySROS libraries and
Nokia SR OS routers is achieved using model-driven paths referencing elements
within the Service Router Operating System.

The pySROS libraries accept modeled paths in the JSON instance path format,
a path format based on
`RFC 6020 <https://datatracker.ietf.org/doc/html/rfc6020#section-9.13>`_ and
`RFC 7951 <https://datatracker.ietf.org/doc/html/rfc7951#section-6.11>`_.
This path format describes the YANG models to which it is referencing, including
all YANG lists, YANG list keys, and their key values (although in some instances,
these may be omitted).

The JSON instance path can be obtained directly from an SR OS router running
software from release 21.7.R1 by entering the ``pwc json-instance-path`` from
the location in the MD-CLI the developer wishes to reference.

See the following for examples:

- :ref:`pwc-json-instance-path-sros-services-config-example`
- :ref:`pwc-json-instance-path-sros-bgp-state-example`
- :ref:`pwc-json-instance-path-sros-openconfig-example`



.. code-block:: text
   :caption: SR OS ``pwc json-instance-path`` output from services configuration
   :name: pwc-json-instance-path-sros-services-config-example

   A:admin@sros# pwc json-instance-path
   Present Working Context:
   /nokia-conf:configure/service/vprn[service-name="vpn1"]/static-routes/route[ip-prefix="1.1.1.1/32"][route-type="unicast"]/blackhole

.. code-block:: text
   :caption: SR OS ``pwc json-instance-path`` output from BGP state
   :name: pwc-json-instance-path-sros-bgp-state-example

   [/state router "Base" bgp neighbor "1.1.1.1"]
   A:admin@sros# pwc json-instance-path
   Present Working Context:
   /nokia-state:state/router[router-name="Base"]/bgp/neighbor[ip-address="1.1.1.1"]

.. code-block:: text
   :caption: SR OS ``pwc json-instance-path`` output from OpenConfig interfaces
   :name: pwc-json-instance-path-sros-openconfig-example

   A:admin@sros# pwc json-instance-path
   Present Working Context:
   /openconfig-interfaces:interfaces/interface[name="1/1/c2/1"]/subinterfaces/subinterface[index=0]/openconfig-if-ip:ipv4/addresses


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902



Schema aware
************

The pySROS libraries are YANG schema aware.  Each element has knowledge
of its path, model, and data type in the YANG model.

The YANG schema is automatically obtained by the pySROS libraries by performing one
of the following upon connection (using :py:meth:`pysros.management.connect`).

   * Download the YANG models from the targeted nodes using
     `YANG library as described in RFC 8525 <https://tools.ietf.org/html/rfc8525>`_ and `get-schema as defined
     in RFC 6022 <https://tools.ietf.org/html/rfc6022>`_ (default).  For this to work the YANG models must
     be available from the SR OS device and the schema-path set correctly (for more information, see the
     SR OS System Management Guide).
   * Compile a YANG model or set of YANG models located on a file system and referenced by the developer.

.. note ::

   When executing a Python application using the pySROS libraries on a remote workstation, the initial
   connection to a node is slower than subsequent connections as the schema is generated
   from the YANG models and cached.


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


pySROS schema cache
*******************

The pySROS libraries use a model-driven schema which is generated from YANG models.  This schema is stored on
your local machine [#f1]_.  The location is dependent on your operating system:

.. list-table::
   :widths: 20 50
   :header-rows: 1
   :name: Location of pySROS schema cache

   * - Operating System
     - pySROS schema cache location
   * - UNIX
     - ``$HOME/.pysros``
   * - macOS
     - ``$HOME/.pysros``
   * - Windows 10
     - ``/Users/<username>/.pysros``


.. [#f1] Not applicable when executing a Python application using the pySROS libraries on SR OS

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Network communication
#####################

When executing applications remotely, the pySROS
libraries use NETCONF for communication between the remote node and the SR OS node.  To facilitate this, the SR OS node must be
configured to allow NETCONF access from the location that the application is run.

For more information about configuring SR OS to use NETCONF, see the SR OS System
Management Guide.

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Installation
############

Multiple installation methods are available:

* `PyPI`_
* `Nokia support portal`_
* `GitHub`_

.. note:: Nokia recommends using Python virtual environments where appropriate.

PyPI
****
The preferred method of installation of the pySROS libraries is to install
directly from the Python Package Index (PyPI) using the ``pip`` tool.

The pySROS project is `located on PyPI.org <https://pypi.org/project/pysros>`_

The libraries can be downloaded and installed by using the following:

.. code-block:: bash

   pip install pysros

To upgrade to the latest version of the pySROS libraries, use the following:

.. code-block:: bash

   pip install --upgrade pysros


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902



Nokia support portal
********************
The pySROS libraries are available for `download from the portal <https://customer.nokia.com/support>`_ for registered
customers.

The obtained file can be unzipped and subsequently installed using:

.. code-block:: python3

   python3 setup.py install


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


GitHub
******
The pySROS libraries are available for
`download from GitHub <https://github.com/nokia/pysros>`_.

The obtained file can be installed using the ``git`` tool:

.. code-block:: python3

   git clone https://github.com/nokia/pysros
   python3 setup.py install


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


.. _pysros-data-model:

The pySROS data model
#####################

The pySROS libraries provide YANG model-aware Python 3 data structures to the
developer that can be manipulated and traversed with Python in the same way
as any other Python structure.

YANG-modeled data structures are converted into Python 3 data structures as
follows:

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


.. _yang_to_python_structures:

Data structure conversions
**************************

.. tabularcolumns:: |1|1|

.. list-table::
   :widths: 20 50
   :header-rows: 1
   :name: yang-py-structures

   * - YANG structure
     - Python 3 structure
   * - List
     - Dict keyed on the YANG list's key value
   * - User-ordered List
     - OrderedDict keyed on the YANG list's key value
   * - Leaf-List
     - List
   * - Leaf
     - Value (Type derived as shown in :ref:`yang_to_python_types`)
   * - Container
     - Dict


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


.. _yang_to_python_types:

Type conversions
****************

.. list-table::
   :widths: 20 50
   :header-rows: 1

   * - Base YANG type
     - Python 3 type
   * - binary
     - string
   * - bits
     - string
   * - boolean
     - boolean
   * - decimal64
     - string
   * - empty
     - :py:class:`pysros.management.Empty` [#f2]_
   * - enumeration
     - string
   * - identityref
     - string
   * - int8
     - integer
   * - int16
     - integer
   * - int32
     - integer
   * - int64
     - integer
   * - leafref
     - N/A [#f3]_
   * - string
     - string
   * - uint8
     - integer
   * - uint16
     - integer
   * - uint32
     - integer
   * - uint64
     - integer
   * - union
     - string [#f4]_

.. [#f2] This specific type is provided by the pySROS libraries
.. [#f3] A leaf-ref takes the YANG native type of the leaf it is referencing.  This type is then
         converted to Python according to this table.
.. [#f4] A union YANG type may be a union of a variety of different YANG types (for example, a union
         of a string and a Boolean).  As it is not possible to identify the intention at the time of
         obtaining the data, automatic type selection is not performed.  Every union is treated as a
         string, allowing the developer to cast the element into a specified type.


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Wrappers
********
To assist with data manipulation, data structures obtained from SR OS are wrapped with
class identifiers depending on their YANG element structure.  This additional information can assist
developers when writing Python code to analyze, manipulate, and output modeled data.

YANG containers are wrapped in the :py:class:`pysros.wrappers.Container` class.

YANG leaf-lists are wrapped in the :py:class:`pysros.wrappers.LeafList` class.

YANG leafs are wrapped in the :py:class:`pysros.wrappers.Leaf` class.  Use the ``data`` variable to
obtain the value of the leaf without the wrapper, as in the following example: :ref:`leaf-dot-data-example`.

Example:

.. code-block:: python
   :caption: Obtaining the value of an object wrapped in the :py:class:`pysros.wrappers.Leaf` class
   :name: leaf-dot-data-example
   :emphasize-lines: 3-4

   >>> from pysros.wrappers import Leaf
   >>> obj = Leaf('example')
   >>> print(obj.data)
   example


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


YANG schema metadata
********************
Additional metadata information from the model-driven schema is available to developers for each element
in a data structure obtained from SR OS using the pySROS libraries.  This metadata can be queried on demand
by calling the ``schema`` method against the element.

Metadata currently available includes:

.. list-table:: Supported schema metadata
   :widths: 20 50
   :header-rows: 1

   * - Metadata variable
     - Description
   * - module
     - The YANG module name [#f5]_

.. [#f5] The YANG module name is the root module for the element.  The pySROS libraries take into
         consideration YANG imports, includes, deviations, and augmentations to provide this result.

Example:

.. code-block:: python
   :caption: Obtaining metadata of an object
   :name: leaf-dot-schema-dot-module-example
   :emphasize-lines: 3-4

   >>> name
   Leaf('sros')
   >>> name.schema.module
   'nokia-conf'

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Getting Started
###############

Making a connection
*******************

To connect to a device running SR OS, a :py:class:`pysros.management.Connection` object must be
created.  The :py:meth:`pysros.management.connect` method creates this object.

The pySROS libraries are designed to provide a level of portability for applications, allowing
developers to create applications within a preferred development environment and to execute them
locally or transfer them to SR OS for execution.

The :py:meth:`pysros.management.connect` method provides arguments
that allow the developer to specify parameters such as the authentication credentials
and TCP port.  These attributes are ignored when an application is executed from an
SR OS node.

Example:

.. code-block:: python
   :caption: Making a connection using :py:meth:`pysros.management.connect`
   :name: connect-example

   from pysros.management import connect
   from pysros.exceptions import *
   import sys

   def get_connection():
       try:
           c = connect(host="192.168.74.51",
                       username="admin",
                       password="admin")
       except RuntimeError as e1:
           print("Failed to connect.  Error:", e1)
           sys.exit(-1)
       except ModelProcessingError as e2:
           print("Failed to create model-driven schema.  Error:", e2)
           sys.exit(-2)
       return c

   if __name__ == "__main__":
       c = get_connection()


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Obtaining data
**************

Use the :py:meth:`pysros.management.Datastore.get` method to obtain model-driven data from an SR OS device.  
This method takes a single JSON instance path (see the :ref:`modeled-paths` section) and returns a data structure.

The :py:meth:`pysros.management.Datastore.get` method can be performed against the ``running`` or the ``candidate`` datastore
when *configuration* data is required.  When *state* data is required, it can only be performed against the
``running`` datastore.

.. note::

   When combined configuration and state schemas are in use, such as OpenConfig, the :py:meth:`pysros.management.Datastore.get`
   method obtains both configuration and state information unless the ``config_only=True`` flag is provided.

Example:

.. code-block:: python
   :caption: Get example using :py:meth:`pysros.management.Datastore.get`
   :name: get-example

   >>> from pysros.management import connect
   >>> c = connect()
   >>> c.running.get('/nokia-conf:configure/router[router-name="Base"]/bgp')
   Container({'group': {'mesh': Container({'group-name': Leaf('mesh'), 'admin-state': Leaf('enable'),
              'peer-as': Leaf(65535)})}, 'neighbor': {'5.5.5.2': Container({'group': Leaf('mesh'),
              'import': Container({'policy': LeafList(['demo', 'example-policy-statement'])}),
              'ip-address': Leaf('5.5.5.2'), 'family': Container({'ipv6': Leaf(True),
              'vpn-ipv4': Leaf(True), 'ipv4': Leaf(True), 'vpn-ipv6': Leaf(True)}),
              'add-paths': Container({'ipv4': Container({'receive': Leaf(True), 'send': Leaf('multipaths')})}),
              'admin-state': Leaf('enable')})}, 'admin-state': Leaf('enable')})


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Configuring SR OS routers
*************************

Configuration of SR OS devices is achieved using an atomic :py:meth:`pysros.management.Datastore.set` method.  This method takes
two inputs: the first is a JSON instance path (see the :ref:`modeled-paths` section) and the second is the payload in
the pySROS data structure format.

The :py:meth:`pysros.management.Datastore.set` method can be performed against the ``candidate`` datastore only and *state*
data cannot be set.

For example, if the developer wishes to enable the gRPC interface and gNMI on a device, the configuration elements for
these settings are located in the ``/nokia-conf:configure/system/grpc`` path.

The configuration settings in the MD-CLI are:

.. code-block:: none

   /configure system grpc admin-state enable
   /configure system grpc allow-unsecure-connection
   /configure system grpc gnmi { }
   /configure system grpc gnmi { admin-state enable }

The pySROS data structure format for this configuration is as shown:

.. code-block:: python3

   Container({'allow-unsecure-connection': Leaf(Empty),
              'admin-state': Leaf('enable'),
              'gnmi': Container({'admin-state': Leaf('enable')})})

To configure the SR OS device, use the :py:meth:`pysros.management.Datastore.set` method as follows:

.. code-block:: python
   :caption: Configuration example using :py:meth:`pysros.management.Datastore.set`
   :name: set-example

   from pysros.management import connect, Empty
   from pysros.wrappers import Leaf, Container
   c = connect()
   path = '/nokia-conf:configure/system/grpc'
   payload = Container({'allow-unsecure-connection': Leaf(Empty),
                        'admin-state': Leaf('enable'),
                        'gnmi': Container({'admin-state': Leaf('enable')})})
   c.candidate.set(path, payload)

The :py:meth:`pysros.management.Datastore.set` method creates a private candidate configuration on the SR OS device,
makes the required configuration changes, validates the changes, performs an update of the baseline configuration
datastore, and commits the changes before releasing the private candidate.  The operation is atomic, that is,
all configuration changes must be made successfully or the configuration remains unchanged.

Objects obtained using :py:meth:`pysros.management.Datastore.get` may be returned directly to
:py:meth:`pysros.management.Datastore.set` if no *state* information is included.

.. code-block:: python
   :caption: Example using :py:meth:`pysros.management.Datastore.set` with an object obtained from :py:meth:`pysros.management.Datastore.get`
   :name: get-set-example

   from pysros.management import connect, Empty
   from pysros.wrappers import Leaf, Container
   c = connect()
   path = '/nokia-conf:configure/system/grpc'
   payload = c.running.get(path)
   c.candidate.set(path, payload)


The :py:meth:`pysros.management.Datastore.set` method also accepts payloads that do not include the pySROS wrapper information.
This enables the developer to simply structure their own data.

.. code-block:: python
   :caption: Configuration example using :py:meth:`pysros.management.Datastore.set` and developer structured data
   :name: set-dev-structured-data-example

   from pysros.management import connect, Empty
   from pysros.wrappers import Leaf, Container
   c = connect()
   path = '/nokia-conf:configure/system/grpc'
   payload = {'allow-unsecure-connection': Empty, 'admin-state': 'enable', 'gnmi': {'admin-state': 'enable'}}
   c.candidate.set(path, payload)


.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Next steps
##########

The :ref:`pysros-examples` section for more details and examples.

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902


Feedback, Support and Assistance
################################

All feedback, issues, errors, improvements, and suggestions may be submitted
via the
`Nokia support portal <https://customer.nokia.com/support>`_ or through your
Nokia representative.

.. Reviewed by PLM 20210902
.. Reviewed by TechComms 20210902
