# Copyright 2021-2023 Nokia

import base64
import contextlib
import datetime
import hashlib
import os.path
import pathlib
import pickle
import re
import tempfile
import types

from collections import OrderedDict
from enum import Enum, auto
from typing import NamedTuple, Tuple

from lxml import etree
from ncclient import manager
from ncclient.operations.rpc import RPCError as nc_RPCError
from ncclient.transport.errors import TransportError as nc_TransportError
from ncclient.xml_ import new_ele, to_ele

from .errors import *
from .model import Model
from .model_builder import ModelBuilder
from .model_walker import FilteredDataModelWalker, ActionInputFilteredDataModelWalker, ActionOutputFilteredDataModelWalker
from .request_data import RequestData
from .singleton import Empty
from .wrappers import Container, Leaf, LeafList

__all__ = ("connect", "sros", "Connection", "Datastore", "Empty", "SrosMgmtError", "InvalidPathError", "ModelProcessingError", "InternalError", "SrosConfigConflictError", "ActionTerminatedIncompleteError", "JsonDecodeError", "XmlDecodeError", )
__doc__ = """This module contains basic primitives for managing an SR OS node.
It contains functions to obtain and manipulate configuration and state data.

.. reviewed by PLM 20210624
.. reviewed by TechComms 20210713
"""


def connect(*, host, port=830, username, password=None, yang_directory=None,
            rebuild=False, transport="netconf", timeout=300, hostkey_verify=True):
    """Create a :class:`.Connection` object.  This function is the main entry point for
    model-driven management of configuration and state for a specific SR OS node using
    the pySROS library.

    .. note::
       All parameters to connect are ignored when executed on an SR OS node.

    :param host: Hostname, Fully Qualified Domain Name (FQDN) or IP address of the SR OS node.
    :type host: str
    :param port: TCP port on the SR OS node to connect to. Default 830.
    :type port: int, optional
    :param username: User name.
    :type username: str
    :param password: User password.  If the password is not provided the systems SSH key
                     is used.
    :type password: str, optional
    :param yang_directory: Path (absolute or relative to the local machine) to the YANG modules
                           for the specific node. If this argument is used, YANG modules are not
                           downloaded from the SR OS node.
    :type yang_directory: str, optional
    :param rebuild: Trigger the rebuild of an already cached YANG schema.
    :type rebuild: bool, optional
    :param timeout: Timeout of the transport protocol, in seconds. Default 300.
    :type timeout: int, optional
    :param hostkey_verify: Enables hostkey verification using the SSH known_hosts file. Default True.
    :type hostkey_verify: bool, optional
    :return: Connection object for specific SR OS node.
    :rtype: :py:class:`Connection`
    :raises RuntimeError: Error occurred during creation of connection
    :raises ModelProcessingError: Error occurred during compilation of the YANG modules


    .. note ::

       When executing a Python application using the pySROS libraries on a remote workstation,
       the initial connection is slower to complete than subsequent connections as the schema
       is generated from the YANG models and cached.

    .. warning::

       ``hostkey_verify`` should be set to ``True`` in a live network environment.

    .. code-block:: python
       :caption: Example 1 - Connection using YANG models automatically obtained from the SR OS node
       :name: pysros-management-connect-example-usage-1

       from pysros.management import connect
       from pysros.exceptions import ModelProcessingError
       import sys

       def get_connection():
           try:
               connection_object = connect(host="192.168.1.1",
                                           username="myusername",
                                           password="mypassword")
           except RuntimeError as runtime_error:
               print("Failed to connect.  Error:", runtime_error)
               sys.exit(-1)
           except ModelProcessingError as model_proc_error:
               print("Failed to create model-driven schema.  Error:", model_proc_error)
               sys.exit(-2)
           return connection_object

       if __name__ == "__main__":
           connection_object = get_connection()


    .. code-block:: python
       :caption: Example 2 - Connection using YANG models obtained from a local directory
       :name: pysros-management-connect-example-usage-2

       from pysros.management import connect
       from pysros.exceptions import ModelProcessingError
       import sys

       def get_connection():
           try:
               connection_object = connect(host="192.168.1.1",
                                           username="myusername",
                                           password="mypassword",
                                           yang_directory="./YANG")
           except RuntimeError as runtime_error:
               print("Failed to connect.  Error:", runtime_error)
               sys.exit(-1)
           except ModelProcessingError as model_proc_error:
               print("Failed to create model-driven schema.  Error:", model_proc_error)
               sys.exit(-2)
           return connection_object

       if __name__ == "__main__":
           connection_object = get_connection()


    .. reviewed by PLM 20220621
    .. reviewed by TechComms 20220624
    """
    if transport != "netconf":
        raise make_exception(pysros_err_invalid_transport)
    return Connection(host=host, port=port, username=username, password=password,
                      device_params={'name': 'sros'}, manager_params={'timeout': timeout},
                      nc_params={'capabilities':['urn:nokia.com:nc:pysros:pc']}, hostkey_verify=hostkey_verify,
                      yang_directory=yang_directory, rebuild=rebuild)

def sros():
    """Determine whether the execution environment is an SR OS node

    :return: True if the application is executed on an SR OS node, False otherwise.
    :rtype: bool

    .. code-block:: python
       :caption: Example
       :name: pysros-management-sros-example-usage

       from pysros.management import sros

       def main():
           if sros():
               print("I'm running on a SR OS device")
           else:
               print("I'm not running on a SR OS device")

       if __name__ == "__main__":
           main()


    .. reviewed by PLM 20210625
    .. reviewed by TechComms 20210713
    """
    return False

class Connection:
    """An object representing a connection to an SR OS device.
    This object is transport agnostic and manages the connection whether the application
    is run on the SR OS node or remotely.

    .. warning::
        You **should not** create this class directly. Please use :func:`~pysros.management.connect`
        instead.

    The underlying transport is NETCONF when executed on a machine that is not running SR OS.

    :ivar running: running datastore
    :vartype running: .Datastore
    :ivar candidate: candidate datastore
    :vartype candidate: .Datastore

    .. Reviewed by PLM 20211201
    .. Reviewed by TechComms 20211202
    """
    _common_namespaces = {
        "ncbase": "urn:ietf:params:xml:ns:netconf:base:1.0",
        "monitoring": "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring",
        "library": "urn:ietf:params:xml:ns:yang:ietf-yang-library",
        "nokiaoper": "urn:nokia.com:sros:ns:yang:sr:oper-global",
        "yang_1_0" : "urn:ietf:params:xml:ns:yang:1",
        "attrs"    : "urn:nokia.com:sros:ns:yang:sr:attributes",
    }

    def __init__(self, *args, yang_directory, rebuild, **kwargs):
        try:
            self._nc        = manager.connect_ssh(*args, **kwargs)
        except Exception as e:
            raise make_exception(pysros_err_could_not_create_conn, reason=e) from None

        self.running    = Datastore(self, 'running')
        self.candidate  = Datastore(self, 'candidate')

        self.yang_directory = yang_directory
        self.rebuild = rebuild
        self._models    = self._get_yang_models()
        self._ns_map    = types.MappingProxyType({model.name: model.namespace for model in self._models})
        self._mod_revs  = {model.name: model.revision for model in self._models}
        self.root = self._get_root(self._models)
        self.debug      = False

    def _get_root(self, modules):
        hasher = hashlib.sha256()
        yangs = sorted(modules, key = lambda m: m.name)
        hasher.update(b"Schema ver 4\n")
        for m in yangs:
            hasher.update(f"mod:{m.name};rev:{m.revision};".encode())
            for sm in sorted(m.submodules, key = lambda sm: sm.name):
                hasher.update(f" smod:{sm.name};srev:{sm.revision};".encode())
        cache_dir = pathlib.Path.home() / '.pysros' / 'cache'
        cache_name_txt = f"model_{base64.b32encode(hasher.digest()).decode('utf-8')}.ver"
        cache_name = cache_dir / cache_name_txt

        if not self.rebuild:
            with contextlib.suppress(FileNotFoundError):
                with cache_name.open("rb") as f:
                    return Model(pickle.load(f), 0, None)

        # attempt to pickle. If load fails, we need to create a new tree
        model_builder = ModelBuilder(self._yang_getter, self._ns_map)
        for mod in yangs:
            model_builder.register_yang(mod.name)
        model_builder.process_all_yangs()

        cache_dir.mkdir(mode=0o755, exist_ok=True, parents = True)
        # write to temp file instead of locking file
        # make hard link to correct name before close + unlink
        with tempfile.NamedTemporaryFile("wb", dir = cache_dir, prefix = "temp_", delete=False) as f:
            try:
                pickle.dump(model_builder.root._storage, f)
            except:
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(f.name)
                raise
        os.replace(f.name, cache_name)

        return model_builder.root

    def _yang_getter(self, yang_name, *, debug=False):
        if self.yang_directory:
            if debug:
                print(f"open local file {yang_name}")
            with open(self._find_module(yang_name), "r", encoding="utf8") as f:
                return f.read()

        # download using netconf protocol
        if debug:
            start = datetime.datetime.now()
            print(f"GET SCHEMA {yang_name}")

        response = self._nc.get_schema(yang_name)
        data = response.xpath("/ncbase:rpc-reply/monitoring:data", self._common_namespaces)[0].text
        if debug:
            print(f" * {len(data)/1024:.1f} kB downloaded in {(datetime.datetime.now()-start).total_seconds():.3f} sec")

        return data

    def _find_module(self, yang_name):
        if os.path.isfile(f"""{self.yang_directory}/nokia-combined/{yang_name}.yang"""):
            return f"""{self.yang_directory}/nokia-combined/{yang_name}.yang"""
        if yang_name in self._ns_map: #module
            for candidate in pathlib.Path(self.yang_directory).rglob(f"{yang_name}*.yang"):
                if candidate.parts and re.fullmatch(f"{yang_name}[@]{self._mod_revs[yang_name]}.yang", str(candidate.parts[-1])):
                    return candidate
        for candidate in pathlib.Path(self.yang_directory).rglob(f"{yang_name}*.yang"):
            if candidate.parts and re.fullmatch(f"{yang_name}.yang", str(candidate.parts[-1])):
                return candidate
        raise make_exception(pysros_err_can_not_find_yang, yang_name=yang_name)

    def _get_yang_models(self):
        subtree = to_ele("""
            <modules-state xmlns="urn:ietf:params:xml:ns:yang:ietf-yang-library">
                <module-set-id/>
                <module/>
            </modules-state>""")
        with self._process_connected():
            yangs_resp = self._nc.get(filter=("subtree", subtree))

        result = []
        modules = yangs_resp.xpath(
            "/ncbase:rpc-reply/ncbase:data/library:modules-state/library:module",
            self._common_namespaces
        )

        get_text = lambda e, path: e.findtext(path, namespaces=self._common_namespaces)
        for m in modules:
            submodules = []
            for sm in m.xpath("./library:submodule", namespaces=self._common_namespaces):
                submodules.append(YangSubmodule(
                    name      = get_text(sm, "./library:name"),
                    revision  = get_text(sm, "./library:revision"),
                ))
            submodules.sort(key = lambda sm: sm.name)
            result.append(YangModule(
                name       = get_text(m, "./library:name"),
                namespace  = get_text(m, "./library:namespace"),
                revision   = get_text(m, "./library:revision"),
                submodules = tuple(submodules)
            ))
        return tuple(result)

    def _action(self, path, value):
        rd = RequestData(self.root, self._ns_map, walker=ActionInputFilteredDataModelWalker)
        current = rd.process_path(path)
        if not current.is_action():
            raise make_exception(pysros_err_unsupported_action_path)
        if current._walker.current.name.name == "md-compare" and "path" in value and "subtree-path" in value["path"]:
            raise make_exception(pysros_err_action_subtree_not_supported)
        current.set(value)

        xml_action = etree.Element(f"""{{{self._common_namespaces["yang_1_0"]}}}action""")
        xml_action.extend(rd.to_xml())

        if self.debug:
            print("ACTION request")
            print(etree.dump(xml_action))

        response = self._nc.rpc(xml_action)

        if self.debug:
            print("ACTION response")
            print(response)

        del rd
        rd = RequestData(self.root, self._ns_map, walker=ActionOutputFilteredDataModelWalker)
        rd.set_action_as_xml(path, response)
        current = rd.process_path(path, strict=True)
        return current.to_model()

    def _convert(self, path, payload, src_fmt, dst_fmt, pretty_print, action_io):
        def convert_walker(action_io):
            if action_io == "input":
                return ActionInputFilteredDataModelWalker
            elif action_io == "output":
                return ActionOutputFilteredDataModelWalker
            raise make_exception(pysros_err_unsupported_action_io)

        if not all(fmt in ("xml", "json", "pysros") for fmt in (src_fmt, dst_fmt)):
            raise make_exception(pysros_err_unsupported_convert_method)
        rd = RequestData(self.root, self._ns_map, action=RequestData._Action.convert, walker=convert_walker(action_io))
        current = rd.process_path(path)

        if src_fmt == "pysros":
            current.set(payload)
        elif src_fmt == "xml":
            if not isinstance(payload, str):
                raise make_exception(pysros_err_convert_wrong_payload_type)
            try:
                data = to_ele(f"<dummy-root>{payload}</dummy-root>")
            except Exception as e:
                raise XmlDecodeError(*e.args)
            current.set_as_xml(data)
        elif src_fmt == "json":
            if not isinstance(payload, str):
                raise make_exception(pysros_err_convert_wrong_payload_type)
            current.set_as_json(payload)
        else:
            raise NotImplementedError()

        if dst_fmt == "pysros":
            return current.to_model()
        elif dst_fmt == "xml":
            root = current.to_xml()
            xml_output=""
            for subtree in root:
                if pretty_print:
                    etree.indent(subtree, space="    ")
                    if xml_output:  xml_output += "\n"
                xml_output += etree.tostring(subtree).decode("utf-8")
            return xml_output
        elif dst_fmt == "json":
            return current.to_json(pretty_print)
        else:
            raise NotImplementedError()

    @contextlib.contextmanager
    def _process_connected(self):
        try:
            if  not self._nc.connected:
                # test wether connection is not disconected before start of the body
                raise make_exception(pysros_err_not_connected)
            yield
        except nc_TransportError as e:
            raise make_exception(pysros_err_not_connected) from None
        except nc_RPCError as e:
            raise SrosMgmtError(e.message.strip() or str(e).strip()) from None

    def disconnect(self):
        """Disconnect the current transport session. After disconnect,
        the model-driven interfaces for the SR OS devices are not available.

        .. code-block:: python
           :caption: Example
           :name: pysros-management-connection-disconnect-example-usage

           from pysros.management import connect
           connection_object = connect()
           connection_object.disconnect()

        .. Reviewed by PLM 20211201
        .. Reviewed by TechComms 20211202
        """
        with self._process_connected():
            self._nc.close_session()

    def cli(self, command):
        """Run a single MD-CLI command. A single line of input is allowed.
        This may include MD-CLI output redirection (such as ``no-more``).
        Some restrictions apply to the commands that may be provided.

        :param command: MD-CLI command
        :type command: str
        :returns: Output as returned from the MD-CLI.  The returned data is an
                  unstructured string. An empty string is returned if the command
                  does not have any output (for example, a ``clear`` command).
        :rtype: str
        :raises RuntimeError: Error if the connection was lost.
        :raises SrosMgmtError: Error when command was not successful.
        :raises ActionTerminatedIncompleteError: Error when command terminated
                                                 with ``terminated-incomplete`` status.

        .. code-block:: python
           :caption: Example
           :name: pysros-cli

           from pysros.management import connect
           connection_object = connect(host='192.168.1.1', username='myusername', password='mypassword')
           print(connection_object.cli('show version'))

        .. Reviewed by PLM 20220901
        """
        with self._process_connected():
            output = self._nc.md_cli_raw_command(command)
        status = output.xpath("/ncbase:rpc-reply/nokiaoper:status", self._common_namespaces)
        if status and status[0].text == "terminated-incomplete":
            errors = output.xpath("/ncbase:rpc-reply/nokiaoper:error-message", self._common_namespaces)
            errors = [e.text.strip() for e in errors]
            args = errors or ["MINOR: MGMT_AGENT #2007: Operation failed"]
            raise ActionTerminatedIncompleteError(*args)
        output = output.xpath("/ncbase:rpc-reply/nokiaoper:results/nokiaoper:md-cli-output-block", self._common_namespaces)
        return output[0].text if output else ""

    def action(self, path, value={}):
        """Perform a YANG modeled action on SR OS by providing the *json-instance-path* to the
        action statement in the chosen operations YANG model, and the pySROS data structure to
        match the YANG modeled input for that action.
        This method provides structured data input and output for available operations.

        :param path: *json-instance-path* to the YANG action.
        :type path: str
        :param value: pySROS data structure providing the input data for the chosen action.
        :type value: pySROS data structure
        :returns: YANG modeled, structured data representing the output of the modeled action (operation)
        :rtype: pySROS data structure

        .. code-block:: python
           :caption: Example calling the **ping** YANG modeled action (operation)
           :name: pysros-action-example

           >>> from pysros.management import connect
           >>> from pysros.pprint import printTree
           >>> connection_object = connect(host='192.168.1.1',
           ... username='myusername', password='mypassword')
           >>> path = '/nokia-oper-global:global-operations/ping'
           >>> input_data = {'destination': '172.16.100.101'}
           >>> output = connection_object.action(path, input_data)
           >>> output
           Container({'operation-id': Leaf(12), 'start-time': Leaf('2022-09-08T22:21:32.6Z'), 'results': Container({'test-parameters': Container({'destination': Leaf('172.16.100.101'), 'count': Leaf(5), 'output-format': Leaf('detail'), 'do-not-fragment': Leaf(False), 'fc': Leaf('nc'), 'interval': Leaf('1'), 'pattern': Leaf('sequential'), 'router-instance': Leaf('Base'), 'size': Leaf(56), 'timeout': Leaf(5), 'tos': Leaf(0), 'ttl': Leaf(64)}), 'probe': {1: Container({'probe-index': Leaf(1), 'status': Leaf('response-received'), 'round-trip-time': Leaf(2152), 'response-packet': Container({'size': Leaf(64), 'source-address': Leaf('172.16.100.101'), 'icmp-sequence-number': Leaf(1), 'ttl': Leaf(64)})}), 2: Container({'probe-index': Leaf(2), 'status': Leaf('response-received'), 'round-trip-time': Leaf(2097), 'response-packet': Container({'size': Leaf(64), 'source-address': Leaf('172.16.100.101'), 'icmp-sequence-number': Leaf(2), 'ttl': Leaf(64)})}), 3: Container({'probe-index': Leaf(3), 'status': Leaf('response-received'), 'round-trip-time': Leaf(2223), 'response-packet': Container({'size': Leaf(64), 'source-address': Leaf('172.16.100.101'), 'icmp-sequence-number': Leaf(3), 'ttl': Leaf(64)})}), 4: Container({'probe-index': Leaf(4), 'status': Leaf('response-received'), 'round-trip-time': Leaf(2164), 'response-packet': Container({'size': Leaf(64), 'source-address': Leaf('172.16.100.101'), 'icmp-sequence-number': Leaf(4), 'ttl': Leaf(64)})}), 5: Container({'probe-index': Leaf(5), 'status': Leaf('response-received'), 'round-trip-time': Leaf(1690), 'response-packet': Container({'size': Leaf(64), 'source-address': Leaf('172.16.100.101'), 'icmp-sequence-number': Leaf(5), 'ttl': Leaf(64)})})}, 'summary': Container({'statistics': Container({'packets': Container({'sent': Leaf(5), 'received': Leaf(5), 'loss': Leaf('0.0')}), 'round-trip-time': Container({'minimum': Leaf(1690), 'average': Leaf(2065), 'maximum': Leaf(2223), 'standard-deviation': Leaf(191)})})})}), 'status': Leaf('completed'), 'end-time': Leaf('2022-09-08T22:21:36.9Z')})
           >>> printTree(output)
           +-- operation-id: 13
           +-- start-time: 2022-09-08T22:23:21.2Z
           +-- results:
           |   +-- test-parameters:
           |   |   +-- destination: 172.16.100.101
           |   |   +-- count: 5
           |   |   +-- output-format: detail
           |   |   +-- do-not-fragment: False
           |   |   +-- fc: nc
           |   |   +-- interval: 1
           |   |   +-- pattern: sequential
           |   |   +-- router-instance: Base
           |   |   +-- size: 56
           |   |   +-- timeout: 5
           |   |   +-- tos: 0
           |   |   `-- ttl: 64
           |   +-- probe:
           |   |   +-- 1:
           |   |   |   +-- probe-index: 1
           |   |   |   +-- status: response-received
           |   |   |   +-- round-trip-time: 2159
           |   |   |   `-- response-packet:
           |   |   |       +-- size: 64
           |   |   |       +-- source-address: 172.16.100.101
           |   |   |       +-- icmp-sequence-number: 1
           |   |   |       `-- ttl: 64
           |   |   +-- 2:
           |   |   |   +-- probe-index: 2
           |   |   |   +-- status: response-received
           |   |   |   +-- round-trip-time: 2118
           |   |   |   `-- response-packet:
           |   |   |       +-- size: 64
           |   |   |       +-- source-address: 172.16.100.101
           |   |   |       +-- icmp-sequence-number: 2
           |   |   |       `-- ttl: 64
           |   |   +-- 3:
           |   |   |   +-- probe-index: 3
           |   |   |   +-- status: response-received
           |   |   |   +-- round-trip-time: 2098
           |   |   |   `-- response-packet:
           |   |   |       +-- size: 64
           |   |   |       +-- source-address: 172.16.100.101
           |   |   |       +-- icmp-sequence-number: 3
           |   |   |       `-- ttl: 64
           |   |   +-- 4:
           |   |   |   +-- probe-index: 4
           |   |   |   +-- status: response-received
           |   |   |   +-- round-trip-time: 2084
           |   |   |   `-- response-packet:
           |   |   |       +-- size: 64
           |   |   |       +-- source-address: 172.16.100.101
           |   |   |       +-- icmp-sequence-number: 4
           |   |   |       `-- ttl: 64
           |   |   `-- 5:
           |   |       +-- probe-index: 5
           |   |       +-- status: response-received
           |   |       +-- round-trip-time: 1735
           |   |       `-- response-packet:
           |   |           +-- size: 64
           |   |           +-- source-address: 172.16.100.101
           |   |           +-- icmp-sequence-number: 5
           |   |           `-- ttl: 64
           |   `-- summary:
           |       `-- statistics:
           |           +-- packets:
           |           |   +-- sent: 5
           |           |   +-- received: 5
           |           |   `-- loss: 0.0
           |           `-- round-trip-time:
           |               +-- minimum: 1735
           |               +-- average: 2038
           |               +-- maximum: 2159
           |               `-- standard-deviation: 153
           +-- status: completed
           `-- end-time: 2022-09-08T22:23:25.4Z

        .. Reviewed by PLM 20220908

        """
        with self._process_connected():
            return self._action(path, value)

    def convert(self, path, payload, *, source_format, destination_format, pretty_print=False, action_io="output"):
        """Returns converted version of the input data (payload) in the destination format.

        The input data must be valid according to the YANG schema for the :py:class:`Connection`
        object that :py:meth:`convert` is being called against.

        :param path: *json-instance-path* to the location in the YANG schema that the
                     payload uses as its YANG modeled root.
        :type path: str
        :param payload: Input data for conversion.  The payload must be valid data according
                        to the YANG schema associated with the :py:class:`Connection` object and
                        should be in the format as defined in the ``source_format`` argument.
                        For ``pySROS``, the payload must be a pySROS data structure.  For
                        ``xml`` or ``json``, the payload must be a *string* containing valid XML
                        or JSON IETF data.
        :type payload: pySROS data structure, str
        :param source_format: Format of the input data.  Valid options are ``xml``, ``json``, or ``pysros``.
        :type source_format: str
        :param destination_format: Format of the output data. Valid options are ``xml``, ``json``, or ``pysros``.
        :type destination_format: str
        :param pretty_print: Format the output for human consumption.
        :type pretty_print: bool, optional
        :param action_io: When converting the input/output of a YANG modeled operation (action), it is possible
                          for there to be conflicting fields in the input and output sections of the YANG.  This
                          parameter selects whether to consider the payload against the ``input`` or ``output``
                          section of the YANG. Default: ``output``.
        :type action_io: str, optional
        :returns: Data structure of the same format as ``destination_format``.
        :rtype: pySROS data structure, str

        An example of the :py:meth:`convert` function can be found in
        the :ref:`Converting Data Formats` section.

        .. note:: Any metadata associated with a YANG node is currently not converted.  Metadata
                  includes SR OS configuration comments as well as more general metadata such as
                  insert or delete operations defined in XML attributes.  If metadata is provided
                  in the payload in XML or JSON format, it is stripped from the
                  resulting output. Attention should be given to converting the output
                  of the ``compare summary netconf-rpc`` MD-CLI command.

        .. Reviewed by PLM 20221123
        .. Reviewed by TechComms 20221124
        """
        return self._convert(path, payload, source_format, destination_format, pretty_print, action_io)


class Datastore:
    """Datastore object that can be used to perform multiple operations on a specified datastore.

    .. Reviewed by PLM 20210614
    .. Reviewed by TechComms 20210705
    """
    class _SetAction(Enum):
        set    = auto()
        delete = auto()

    class _ExistReason(Enum):
        exist  = auto()
        delete = auto()

    def __init__(self, connection, target):
        if target != 'running' and target != 'candidate':
            raise make_exception(pysros_invalid_target)
        self.connection  = connection
        self.nc          = connection._nc
        self.target      = target
        self.transaction = None
        self.debug       = False

    def _get_defaults(self, defaults):
        return "report-all" if defaults else None

    def _check_empty_string(self, model_walker):
        for k in model_walker.keys:
            if '' in k.values():
                raise make_exception(pysros_err_filter_empty_string)


    def _prepare_root_ele(self, subtree, path):
        root = etree.Element("filter")
        root.extend(subtree)
        if self.debug:
            print("GET request for path ", path)
            print(etree.dump(root))
        return root

    def _operation_get(self, subtree, defaults, path):
        if subtree:
            root = self._prepare_root_ele(subtree, path)
            return self.nc.get(filter=root, with_defaults=self._get_defaults(defaults))
        else:
            return self.nc.get(with_defaults=self._get_defaults(defaults))

    def _operation_get_config(self, subtree, defaults, path):
        if subtree:
            root = self._prepare_root_ele(subtree, path)
            return self.nc.get_config(source=self.target, filter=root, with_defaults=self._get_defaults(defaults))
        else:
            return self.nc.get_config(source=self.target, with_defaults=self._get_defaults(defaults))

    def _get(self, path, *, defaults=False, custom_walker=None, config_only=False, filter=None):
        model_walker = custom_walker if custom_walker else FilteredDataModelWalker.user_path_parse(self.connection.root, path)

        if config_only and model_walker.is_state:
            raise make_exception(pysros_err_no_data_found)

        self._check_empty_string(model_walker)

        rd = RequestData(self.connection.root, self.connection._ns_map)
        current = rd.process_path(model_walker)
        if filter is not None:
            model_walker.validate_get_filter(filter)
            current.set_filter(filter)
        config = rd.to_xml()

        if self.target == "running":
            if config_only:
                response = self._operation_get_config(config, defaults, path)
                model_walker.config_only = True
            else:
                response = self._operation_get(config, defaults, path)
        else:
            if model_walker.current.config == False:
                raise make_exception(pysros_err_can_get_state_from_running_only)
            model_walker.config_only = True
            response = self._operation_get_config(config, defaults, path)

        if self.debug:
            print("GET response")
            print(response)
        del rd, current

        rd = RequestData(self.connection.root, self.connection._ns_map)
        rd.set_as_xml(response)
        try:
            current = rd.process_path(model_walker, strict=True)
        except LookupError as e:
            #two possible scenarions - entry does not exists or is empty
            #if has presence and LookupError is raised, it does not exists
            if model_walker.has_explicit_presence() and not filter:
                raise e from None
            if model_walker.get_dds() == Model.StatementType.list_:
                res = OrderedDict() if model_walker.current.user_ordered else {}
            else:
                res = Container._with_model({}, model_walker.current)

            model_walker_copy = model_walker.copy()
            #doing exists to check whether really exists or not
            model_walker_copy.go_to_last_with_presence()
            if model_walker_copy.is_root:
                return res
            else:
                try:
                    self._get(path, custom_walker=model_walker_copy)
                except LookupError:
                    raise e from None
                return res
        return current.to_model(key_filter=(filter or {}))

    def _set(self, path, value, action, method="merge"):
        if self.target == 'running':
            raise make_exception(pysros_err_cannot_modify_config)
        if method != 'merge' and method != 'replace':
            raise make_exception(pysros_err_unsupported_set_method)
        model_walker = FilteredDataModelWalker.user_path_parse(self.connection.root, path)
        if model_walker.current.config == False:
            raise make_exception(pysros_err_cannot_modify_state)
        config = new_ele("config")
        rd = RequestData(self.connection.root, self.connection._ns_map)
        if action == Datastore._SetAction.delete:
            default_operation="none"
            rd.process_path(path).delete()
        else:
            default_operation="merge"
            current = rd.process_path(path)
            current.set(value)
            if method == "replace":
                current.replace()
        config.extend(rd.to_xml())
        if self.debug:
            print("SET request")
            print(f"path: '{path}', value: '{value}'")
            print(etree.dump(config))
        self.nc.edit_config(target=self.target, default_operation=default_operation, config=config)

    def _delete(self, path):
        self._set(path, None, Datastore._SetAction.delete)

    def _exists(self, path, exist_reason):
        model_walker = FilteredDataModelWalker.user_path_parse(self.connection.root, path)
        # if exists is called as a check before deletion, check for path to avoid
        # incorrect errors such as pysros_err_can_check_state_from_running_only
        # as we want to handle state delete related errors first
        if model_walker.current.config == False:
            if exist_reason == Datastore._ExistReason.delete:
                raise make_exception(pysros_err_cannot_delete_from_state)
            elif self.target == "candidate":
                raise make_exception(pysros_err_can_check_state_from_running_only)
        if exist_reason == Datastore._ExistReason.delete:
            if model_walker.is_local_key:
                raise make_exception(pysros_err_invalid_operation_on_key)
            if model_walker.is_leaflist:
                raise make_exception(pysros_err_invalid_operation_on_leaflist)
        if model_walker.has_missing_keys():
            raise make_exception(pysros_err_invalid_path_operation_missing_keys)
        model_walker.go_to_last_with_presence()
        if model_walker.is_root:
            return True
        else:
            try:
                self._get(path, custom_walker=model_walker)
            except LookupError:
                return False
            return True

    def _get_list_keys(self, path, defaults):
        model_walker = FilteredDataModelWalker.user_path_parse(self.connection.root, path)
        self._check_empty_string(model_walker)

        rd = RequestData(self.connection.root, self.connection._ns_map)
        current = rd.process_path(model_walker)

        #get possible errors related to the getting candidate from state before
        #errors related to the incorrect path while calling entry_get_keys
        if self.target == "candidate" and model_walker.current.config == False:
            raise make_exception(pysros_err_can_get_state_from_running_only)

        current.entry_get_keys()
        config = rd.to_xml()

        if self.target == "running":
            response = self._operation_get(config, defaults, path)
        else:
            response = self._operation_get_config(config, defaults, path)

        if self.debug:
            print("GET response")
            print(response)
        del rd, current

        rd = RequestData(self.connection.root, self.connection._ns_map)
        rd.set_as_xml(response)
        try:
            current = rd.process_path(model_walker, strict=True)
        except LookupError as e:
            #two possible scenarios - list has no entries or path does not exist
            #doing exists to check whether really exists or not
            model_walker_copy = model_walker.copy()
            model_walker_copy.go_to_last_with_presence()
            if model_walker_copy.is_root:
                return []
            else:
                try:
                    self._get(path, custom_walker=model_walker_copy)
                except LookupError:
                    raise e from None
                return []

        return [*current.to_model()]

    def _compare(self, output_format, user_path):
        if self.target == 'running':
            raise make_exception(pysros_err_unsupported_compare_datastore)
        if output_format not in ("md-cli", "xml"):
            raise make_exception(pysros_err_unsupported_compare_method)

        path = user_path if user_path != "/" else ""

        if path:
            model_walker = FilteredDataModelWalker.user_path_parse(self.connection.root, path)
            if model_walker.current.config == False:
                raise make_exception(pysros_err_unsupported_compare_endpoint)
            rd = RequestData(self.connection.root, self.connection._ns_map)
            current = rd.process_path(model_walker)
            if not current.is_compare_supported_endpoint():
                raise make_exception(pysros_err_unsupported_compare_endpoint)
            path = rd.to_xml()

        op_ns = self.connection._common_namespaces["nokiaoper"]
        xml_action = etree.Element(f"""{{{self.connection._common_namespaces["yang_1_0"]}}}action""")
        xml_gl_op = etree.SubElement(xml_action, f"{{{op_ns}}}global-operations")
        xml_md_cmp = etree.SubElement(xml_gl_op, f"{{{op_ns}}}md-compare")
        if path:
            xml_path = etree.SubElement(xml_md_cmp, f"{{{op_ns}}}path")
            xml_sbtr_path = etree.SubElement(xml_path, f"{{{op_ns}}}subtree-path")
            xml_sbtr_path.extend(path)
        xml_fmt = etree.Element(f"{{{op_ns}}}format")
        xml_fmt.text=output_format if output_format == "xml" else "md-cli"
        xml_md_cmp.append(xml_fmt)
        xml_src = etree.SubElement(xml_md_cmp, f"{{{op_ns}}}source")
        xml_src.append(etree.Element(self.target))
        xml_dst = etree.SubElement(xml_md_cmp, f"{{{op_ns}}}destination")
        xml_dst.append(etree.Element(f"{{{op_ns}}}baseline"))

        if self.debug:
            print("COMPARE request")
            print(etree.dump(xml_action))

        reply = self.nc.rpc(xml_action)

        if self.debug:
            print("COMPARE reply")
            print(reply)

        if output_format == "md-cli":
            return reply.xpath("/ncbase:rpc-reply/nokiaoper:results/nokiaoper:md-compare-output/text()")[0].strip()

        xml_output=""
        for subtree in reply.xpath("/ncbase:rpc-reply/nokiaoper:results/nokiaoper:md-compare-output/*"):
            subtree.getparent().remove(subtree)
            etree.cleanup_namespaces(subtree, keep_ns_prefixes=["nc", "nokia-attr", "yang"])
            xml_output+=etree.tostring(subtree).decode("utf-8")

        if xml_output:
            xml_trees = etree.fromstring(f"<root>{xml_output}</root>", parser=etree.XMLParser(remove_blank_text=True))
            for xml_tree in xml_trees:
                etree.indent(xml_tree, space="    ")
            return "\n".join(etree.tostring(xml_tree, pretty_print=True).decode("utf-8").strip() for xml_tree in xml_trees)
        return ""

    def _commit(self):
        try:
            self.nc.commit()
        except nc_RPCError as e:
            if e.message and e.message.find("MGMT_CORE #2703:") > -1:
                self.nc.discard_changes()
                self.nc.commit()
                raise make_exception(pysros_err_commit_conflicts_detected) from None
            raise e from None

    def get(self, path, *, defaults=False, config_only=False, filter=None):
        """Obtain a pySROS data structure containing the contents of the supplied path.  See the
        :ref:`pysros-data-model`
        section for more information about the pySROS data structure.

        :param path: Path to the requested node in the datastore. The path
                     is an instance-identifier based on
                     `RFC 6020 <https://datatracker.ietf.org/doc/html/rfc6020#section-9.13>`_
                     and `RFC 7951 <https://datatracker.ietf.org/doc/html/rfc7951#section-6.11>`_.
                     The path can be obtained from an SR OS device using the
                     ``pwc json-instance-path`` MD-CLI command.
                     The path may point to a YANG Container, List, Leaf, Leaf-List or a
                     specific List entry.
        :type path: str
        :param defaults: Obtain default values in addition to specifically set values.
        :type defaults: bool
        :param config_only: Obtain configuration data only.  Items marked as
                            ``config false`` in YANG are not returned.
        :type config_only: bool
        :param filter: A filter defining one or more of the following:  *Content node matches* that select items
                       whose values are equal to the provided filter or *Selection node matches* that define which
                       fields to return.  See :ref:`pysros-management-datastore-get-example-content-node-filters`,
                       :ref:`pysros-management-datastore-get-example-selection-node-filters` and
                       :ref:`pysros-management-datastore-get-example-mixed-filters` for examples.
        :type filter: dict
        :return: A pySROS data structure.  This may be a simple value or a more
         complicated structure depending on the path requested.
        :rtype: :class:`pysros.wrappers.Leaf`, :class:`pysros.wrappers.LeafList`,
                :class:`pysros.wrappers.Container`
        :raises RuntimeError: Error if the connection was lost.
        :raises InvalidPathError: Error if the path is malformed.
        :raises SrosMgmtError: Error for broader SR OS issues including
                               (non-exhaustive list): passing invalid objects, and
                               setting to an unsupported branch.
        :raises TypeError: Error if fields or keys are incorrect.
        :raises InternalError: Error if the schema is corrupted.

        .. note::

           Any whitespace at the beginning or end of a content match filter is stripped.

        .. code-block:: python
           :caption: Example
           :name: pysros-management-datastore-get-example-usage

            from pysros.management import connect
            import sys

            connection_object = connect()
            try:
                oper_name = connection_object.running.get("/nokia-state:state/system/oper-name")
            except RuntimeError as runtime_error:
                print("Runtime Error:", runtime_error)
                sys.exit(100)
            except InvalidPathError as invalid_path_error:
                print("Invalid Path Error:", invalid_path_error)
                sys.exit(101)
            except SrosMgmtError as sros_mgmt_error:
                print("SR OS Management Error:", sros_mgmt_error)
                sys.exit(102)
            except TypeError as type_error:
                print("Type Error:", type_error)
                sys.exit(103)
            except InternalError as internal_error:
                print("Internal Error:", internal_error)
                sys.exit(104)

        .. code-block:: python
           :caption: Example using content node matching filters
           :name: pysros-management-datastore-get-example-content-node-filters
           :emphasize-lines: 5-7

           from pysros.management import connect

           connection_object = connect()

           connection_object.running.get(
               "/nokia-conf:configure/service/vprn", filter={"service-name": "VPRN_42"}
           )

        .. code-block:: python
           :caption: Example using selection node filters
           :name: pysros-management-datastore-get-example-selection-node-filters
           :emphasize-lines: 5-8

           from pysros.management import connect

           connection_object = connect()

           connection_object.running.get(
               "/nokia-conf:configure/service/vprn",
               filter={"admin-state": {}, "interface": {"interface-name": {}}},
           )

        .. code-block:: python
           :caption: Example using content node match filters and selection node filters together
           :name: pysros-management-datastore-get-example-mixed-filters
           :emphasize-lines: 5-8

           from pysros.management import connect

           connection_object = connect()

           connection_object.running.get(
               "/nokia-conf:configure/service/vprn",
               filter={'service-name': 'VPRN_42', 'admin-state': {}, 'interface': {'interface-name': {}}},
           )

        .. Reviewed by PLM 20220621
        .. Reviewed by TechComms 20220624

        """
        with self.connection._process_connected():
            return self._get(path, defaults=defaults, config_only=config_only, filter=filter)

    def set(self, path, value, commit=True, method="merge"):
        """Set a pySROS data structure to the supplied path. See the
        :ref:`pysros-data-model` section for more information about the pySROS data structure.

        :param path: Path to the target node in the datastore.  See the path parameter definition in
                     :py:meth:`pysros.management.Datastore.get` for details.
        :type path: str

        :param value: Value to set the node to. When ``path`` points to a Leaf, the
                      value should be a `str` (optionally wrapped in a
                      :class:`pysros.wrappers.Leaf`). When ``path`` points to a Leaf-List,
                      the value should be a `list` of `str` (optionally wrapped in
                      a :class:`pysros.wrappers.LeafList`). When ``path`` points to a
                      Container or list item, the value should be a `dict` (optionally
                      wrapped in a :class:`pysros.wrappers.Container`).
                      Valid nested data structures are supported.

        :param commit: Specify whether update and commit should be executed after set.  Default True.
        :type commit: bool

        :param method: Specify whether set operation should be ``merge`` or ``replace``.  Default ``merge``.
        :type method: str

        :raises RuntimeError: Error if the connection is lost.
        :raises InvalidPathError: Error if the path is malformed.
        :raises SrosMgmtError: Error for broader SR OS issues, including (non-exhaustive list):
                passing invalid objects, and setting to an unsupported branch.
        :raises TypeError: Error if fields or keys are incorrect.
        :raises InternalError: Error if the schema is corrupted.
        :raises SrosConfigConflictError: Error if configuration commit failed due to conflicts.

        .. code-block:: python
           :caption: Example 1 - Configuring a leaf
           :name: pysros-management-datastore-set-example-usage-1

           from pysros.management import connect

           connection_object = connect()
           payload = "my-router-name"
           connection_object.candidate.set("/nokia-conf:configure/system/name", payload)

        .. code-block:: python
           :caption: Example 2 - Configuring a more complex structure
           :name: pysros-management-datastore-set-example-usage-2

           from pysros.management import connect
           from pysros.wrappers import *

           connection_object = connect()
           path = '/nokia-conf:configure/router[router-name="Base"]/interface[interface-name="demo1"]'
           data = Container({'interface-name': Leaf('demo1'), 'port': Leaf('1/1/c1/1:0'),
                  'ipv4': Container({'primary': Container({'prefix-length': Leaf(24),
                  'address': Leaf('192.168.100.1')})}), 'admin-state': Leaf('enable')})
           connection_object.candidate.set(path, data)

        .. Reviewed by PLM 20220901
        """
        with self.connection._process_connected():
            self._set(path, value, Datastore._SetAction.set, method)
            if commit:
                self._commit()

    def delete(self, path, commit=True):
        """Delete a specific path from an SR OS node.

        :param path: Path to the node in the datastore.  See the path parameter definition in
                     :py:meth:`pysros.management.Datastore.get` for details.
        :type path: str
        :param commit: Specify whether commit should be executed after delete.  Default True.
        :type commit: bool

        :raises RuntimeError: Error if the connection is lost.
        :raises InvalidPathError: Error if the path is malformed.
        :raises SrosMgmtError: Error for broader SR OS issues, including (non-exhaustive list):
                passing invalid objects, and setting to an unsupported branch.
        :raises TypeError: Error if fields or keys are incorrect.
        :raises InternalError: Error if the schema is corrupted.
        :raises SrosConfigConflictError: Error if configuration commit failed due to conflicts.

        .. code-block:: python
           :caption: Example
           :name: pysros-management-datastore-delete-example

           from pysros.management import connect
           connection_object = connect()
           connection_object.candidate.delete('/nokia-conf:configure/log/log-id[name="33"]')

        .. Reviewed by PLM 20211201
        .. Reviewed by TechComms 20211202
        """
        with self.connection._process_connected():
            if self.target == 'running':
                raise make_exception(pysros_err_cannot_modify_config)
            if not self._exists(path, Datastore._ExistReason.delete):
                raise make_exception(pysros_err_data_missing)
            self._delete(path)
            if commit:
                self._commit()

    def exists(self, path):
        """Check if a specific node exists.

        :param path: Path to the node in the datastore. See the path parameter definition in
                     :py:meth:`pysros.management.Datastore.get` for details.
        :type path: str
        :rtype: bool
        :raises RuntimeError: Error if the connection is lost.
        :raises InvalidPathError: Error if the path is malformed.
        :raises SrosMgmtError: Error for broader SR OS issues, including (non-exhaustive list):
                passing invalid objects, and setting to an unsupported branch.
        :raises TypeError: Error if fields or keys are incorrect.
        :raises InternalError: Error if the schema is corrupted.

        .. code-block:: python
           :caption: Example
           :name: pysros-management-datastore-exists-example

           from pysros.management import connect
           connection_object = connect()
           if connection_object.running.exists('/nokia-conf:configure/log/log-id[name="33"]') == True:
               print("The log with the ID of 33 is present on the SR OS router")
           else:
               print("This log ID is not present on the SR OS router")

        .. Reviewed by PLM 20211201
        .. Reviewed by TechComms 20211202
        """
        with self.connection._process_connected():
            return self._exists(path, Datastore._ExistReason.exist)

    def get_list_keys(self, path, defaults=False):
        """Returns list of key values.

        :param path: Path to the node in the datastore. See the path parameter definition in
                     :py:meth:`pysros.management.Datastore.get` for details.
        :type path: str
        :param defaults: Obtain default values in addition to specifically set values.
        :type defaults: bool
        :rtype: list
        :raises RuntimeError: Error if the connection was lost.
        :raises InvalidPathError: Error if the path is malformed.
        :raises SrosMgmtError: Error for broader SR OS issues, including (non-exhaustive list):
                passing invalid objects, and setting to an unsupported branch.
        :raises TypeError: Error if fields or keys are incorrect.
        :raises InternalError: Error if the schema is corrupted.
        :raises LookupError: Error if path does not exist.

        .. Reviewed by PLM 20220114

        """
        with self.connection._process_connected():
            return self._get_list_keys(path, defaults)

    def lock(self):
        """Lock the configuration datastore.  Transitions a candidate configuration into an exclusive
        candidate configuration.

        :raises SrosMgmtError: Error if a lock cannot be obtained.

        .. note::
           The :py:meth:`lock` method may only be called against the ``candidate`` configuration datastore.

        .. note::
           Only one lock may be obtained per SR OS system.  Attempting to obtain another lock raises
           an exception.

        .. Reviewed by PLM 20220621
        .. Reviewed by TechComms 20220624
        """
        with self.connection._process_connected():
            if self.target == "running":
                raise make_exception(pysros_err_cannot_lock_and_unlock_running)
            self.nc.lock(target=self.target)

    def unlock(self):
        """Unlock the configuration datastore.  Transitions an exclusive candidate configuration to a candidate
        configuration.  Any changes present in the candidate configuration are retained.

        :raises SrosMgmtError: Error if no lock is held.

        .. note::
           The :py:meth:`unlock` method may only be called against the ``candidate`` configuration datastore.

        .. Reviewed by PLM 20220621
        .. Reviewed by TechComms 20220624
        """
        with self.connection._process_connected():
            if self.target == "running":
                raise make_exception(pysros_err_cannot_lock_and_unlock_running)
            self.nc.unlock(target=self.target)

    def commit(self):
        """Commit the candidate configuration.

        :raises SrosMgmtError: Error if committing the configuration is not possible.

        .. note::
           The :py:meth:`commit` method may only be called against the ``candidate`` configuration datastore.

        .. Reviewed by PLM 20220623
        .. Reviewed by TechComms 20220624
        """
        with self.connection._process_connected():
            if self.target == 'running':
                raise make_exception(pysros_err_cannot_modify_config)
            self._commit()

    def discard(self):
        """Discard the current candidate configuration.

        :raises SrosMgmtError: Error if discarding the candidate configuration is not possible.

        .. note::
           The :py:meth:`discard` method may only be called against the ``candidate`` configuration datastore.

        .. Reviewed by PLM 20220623
        .. Reviewed by TechComms 20220624
        """
        with self.connection._process_connected():
            if self.target == 'running':
                raise make_exception(pysros_err_cannot_modify_config)
            self.nc.discard_changes()


    def compare(self, path="", *, output_format):
        """Perform a comparison of the uncommitted candidate configuration with the baseline
        configuration.
        The output can be provided in XML or in MD-CLI format and provided in a format
        where, if applied to the node, the resulting configuration would be the same as if the
        candidate configuration is committed.

        :param output_format: Specify output format of compare command. Supported formats are
                              ``xml`` and ``md-cli``.  The ``md-cli`` output format displays similar output
                              to that of the **compare summary** command on the MD-CLI.  The ``xml``
                              output format displays similar output to that of the **compare summary netconf-rpc**
                              MD-CLI command.
        :type output_format: str
        :param path: Specify json-instance-path to the location in the schema that the compare runs from.
                     This is the root of the comparison.
        :type path: str
        :returns: The formatted differences between the configurations.
        :rtype: str

        .. note::
           The :py:meth:`compare` method may only be called against the ``candidate`` configuration datastore.

        .. code-block:: python
           :caption: Example - Compare in XML format
           :name: pysros-management-datastore-compare-example-usage-1
           :emphasize-lines: 5,14

           from pysros.management import connect

           connection_object = connect()
           path = '/nokia-conf:configure/policy-options/policy-statement[name="DEMO"]'
           output_format = 'xml'

           print("Current config in", path)
           print(connection_object.candidate.get(path))

           print("Deleting config in", path)
           connection_object.candidate.delete(path, commit=False)

           print("Comparing the candidate configuration to the baseline configuration in {} format".format(output_format))
           print(connection_object.candidate.compare(output_format=output_format))

        .. Reviewed by PLM 20220901
        .. Reviewed by PLM 20221005

        """
        with self.connection._process_connected():
            return self._compare(output_format, path)

    def __getitem__(self, path):
        return self.get(path)

    def __setitem__(self, path, value):
        self.set(path, value)

    def __delitem__(self, path):
        self.delete(path)

class YangSubmodule(NamedTuple):
    name: str
    revision: str

class YangModule(NamedTuple):
    name: str
    namespace: str
    revision: str
    submodules: Tuple[YangSubmodule]
