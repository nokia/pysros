# Copyright 2021 Nokia

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
from .model_walker import FilteredDataModelWalker
from .request_data import RequestData
from .wrappers import Empty, Container, Leaf, LeafList

__all__ = ("connect", "sros", "Connection", "Datastore", "Empty", "SrosMgmtError", "InvalidPathError", "ModelProcessingError", "InternalError", "SrosConfigConflictError", "ActionTerminatedIncompleteError",)
__doc__ = """This module contains basic primitives for managing an SR OS node.
It contains functions to obtain and manipulate configuration and state data.

.. reviewed by PLM 20210624
.. reviewed by TechComms 20210713
"""


def connect(*, host, port=830, username, password=None, yang_directory=None,
            rebuild=False, transport="netconf", timeout=300):
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
                     will be used.
    :type password: str, optional
    :param yang_directory: Path (absolute or relative to the local machine) to the YANG modules
                           for the specific node. If this argument is used, YANG modules are not
                           downloaded from the SR OS node.
    :type yang_directory: str, optional
    :param rebuild: Trigger the rebuild of an already cached YANG schema.
    :type rebuild: bool, optional
    :param timeout: Timeout of the transport protocol in seconds. Default 300.
    :type timeout: int, optional
    :return: Connection object for specific SR OS node.
    :rtype: .Connection
    :raises RuntimeError: Error occurred during creation of connection
    :raises ModelProcessingError: Error occurred during compilation of the YANG modules


    .. note ::

       When executing a Python application using the pySROS libraries on a remote workstation,
       the initial connection is slower to complete than subsequent connections as the schema
       is generated from the YANG models and cached.


    .. code-block:: python
       :caption: Example 1 - Connection using YANG models automatically obtained from the SR OS node
       :name: pysros-management-connect-example-usage-1

       from pysros.management import connect
       from pysros.exceptions import ModelProcessingError
       import sys

       def get_connection():
           try:
               connection_object = connect(host="192.168.74.51",
                                           username="admin",
                                           password="admin")
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
               connection_object = connect(host="192.168.74.51",
                                           username="admin",
                                           password="admin",
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


    .. reviewed by PLM 20211201
    .. reviewed by TechComms 20211202
    """
    if transport != "netconf":
        raise make_exception(pysros_err_invalid_transport)
    return Connection(host=host, port=port, username=username, password=password,
                      device_params={'name': 'sros'}, manager_params={'timeout': timeout},
                      nc_params={'capabilities':['urn:nokia.com:nc:pysros:pc']},
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
        self.root = self._get_root(self._models)

    def _get_root(self, modules):
        hasher = hashlib.sha256()
        yangs = sorted(modules, key = lambda m: m.name)
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
                    return pickle.load(f)

        # attempt to pickle. If load fails, we need to create a new tree
        model_builder = ModelBuilder(self._yang_getter)
        for mod in yangs:
            model_builder.register_yang(mod.name)
        model_builder.process_all_yangs()

        cache_dir.mkdir(mode=0o755, exist_ok=True, parents = True)
        # write to temp file instead of locking file
        # make hard link to correct name before close + unlink
        with tempfile.NamedTemporaryFile("wb", dir = cache_dir, prefix = "temp_", delete=False) as f:
            try:
                pickle.dump(model_builder.root, f)
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
        for candidate in pathlib.Path(self.yang_directory).rglob(f"{yang_name}*.yang"):
            if candidate.parts and re.fullmatch(f"{yang_name}(?:[@]\\d{{4}}[-]\\d{{2}}[-]\\d{{2}})?.yang", str(candidate.parts[-1])):
                return candidate
        raise make_exception(pysros_err_can_not_find_yang, yang_name=yang_name)

    def _get_module_set_id(self):
        caps = list(self._nc.server_capabilities)
        yang_cap = list(filter(lambda x: x.startswith("urn:ietf:params:netconf:capability:yang-library:"), self._nc.server_capabilities))
        if len(yang_cap) == 0:
            raise make_exception(pysros_err_server_dos_not_have_yang_lib)
        if yang_cap[0].find("yang-library:1.0") != -1:
            match = re.search("module-set-id=([^&]*)", yang_cap[0])
        elif yang_cap[0].find("yang-library:1.1") != -1:
            match = re.search("content-id=([^&]*)", yang_cap[0])
        else:
            raise make_exception(pysros_err_server_dos_not_have_required_yang_lib)
        if match is None:
            raise make_exception(pysros_err_cannot_find_module_set_id_or_content_id)
        return match.group(1)

    def _get_yang_models(self):
        subtree = to_ele("""
            <modules-state xmlns="urn:ietf:params:xml:ns:yang:ietf-yang-library">
                <module-set-id/>
                <module/>
            </modules-state>""")
        with self._process_connected():
            yangs_resp = self._nc.get(filter=("subtree", subtree))
        module_set_id = yangs_resp.xpath(
            "/ncbase:rpc-reply/ncbase:data/library:modules-state/library:module-set-id",
            self._common_namespaces
        )[0].text

        if module_set_id != self._get_module_set_id():
            raise make_exception(pysros_err_invalid_module_set_id_or_content_id)

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
           connection_object = connect(host='192.168.1.1', username='admin', password='admin')
           print(connection_object.cli('show version'))

        .. Reviewed by PLM 20211201
        .. Reviewed by TechComms 20211202
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

    def _get(self, path, *, defaults=False, custom_walker=None, config_only=False):
        model_walker = custom_walker if custom_walker else FilteredDataModelWalker.user_path_parse(self.connection.root, path)

        if config_only and model_walker.is_state:
            raise make_exception(pysros_err_no_data_found)

        rd = RequestData(self.connection.root, self.connection._ns_map)
        current = rd.process_path(model_walker)
        config = rd.to_xml()

        if self.target == "running":
            if config_only:
                response = self._operation_get_config(config, defaults, path)
            else:
                response = self._operation_get(config, defaults, path)
        else:
            if model_walker.current.config == False:
                raise make_exception(pysros_err_can_get_state_from_running_only)
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
            if model_walker.has_explicit_presence():
                raise e from None
            if model_walker.get_dds() == Model.StatementType.list_:
                res = OrderedDict() if model_walker.current.user_ordered else {}
            else:
                res = Container._with_module({}, model_walker.get_name().prefix)

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
        return current.to_model(config_only=config_only)

    def _set(self, path, value, action):
        if self.target == 'running':
            raise make_exception(pysros_err_cannot_modify_config)
        model_walker = FilteredDataModelWalker.user_path_parse(self.connection.root, path)
        if model_walker.current.config == False:
            raise make_exception(pysros_err_cannot_modify_state)
        config = new_ele("config")
        rd = RequestData(self.connection.root, self.connection._ns_map)
        if action == Datastore._SetAction.delete:
            rd.process_path(path).delete()
            operation="none"
        else:
            rd.process_path(path).set(value)
            operation="merge"
        config.extend(rd.to_xml())
        if self.debug:
            print("SET request")
            print(f"path: '{path}', value: '{value}'")
            print(etree.dump(config))
        self.nc.edit_config(target=self.target, default_operation=operation, config=config)

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
        if exist_reason == Datastore._ExistReason.delete and model_walker.is_local_key:
            raise make_exception(pysros_err_invalid_operation_on_key)
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

    def _commit(self):
        try:
            self.nc.commit()
        except nc_RPCError as e:
            if e.message and e.message.find("MGMT_CORE #2703:") > -1:
                self.nc.discard_changes()
                self.nc.commit()
                raise make_exception(pysros_err_commit_conflicts_detected) from None
            raise e from None

    def get(self, path, *, defaults=False, config_only=False):
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
        :return: A pySROS data structure.  This may be a simple value or a more
                 complicated structure depending on the path requested.
        :param config_only: Obtain configuration data only.  Items marked as
                            ``config false`` in YANG are not returned.
        :type config_only: bool
        :rtype: :class:`pysros.wrappers.Leaf`, :class:`pysros.wrappers.LeafList`,
                :class:`pysros.wrappers.Container`
        :raises RuntimeError: Error if the connection was lost.
        :raises InvalidPathError: Error if the path is malformed.
        :raises SrosMgmtError: Error for broader SR OS issues including
                               (non-exhaustive list): passing invalid objects, and
                               setting to an unsupported branch.
        :raises TypeError: Error if fields or keys are incorrect.
        :raises InternalError: Error if the schema is corrupted.

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


        .. Reviewed by PLM 20211201
        .. Reviewed by TechComms 20211202
        """
        with self.connection._process_connected():
            return self._get(path, defaults=defaults, config_only=config_only)

    def set(self, path, value):
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
                  'address': Leaf('5.5.5.1')})}), 'admin-state': Leaf('enable')})
           connection_object.candidate.set(path, data)

        .. Reviewed by PLM 20211201
        .. Reviewed by TechComms 20211202
        """
        with self.connection._process_connected():
            self._set(path, value, Datastore._SetAction.set)
            self._commit()

    def delete(self, path):
        """Delete a specific path from an SR OS node.

        :param path: Path to the node in the datastore.  See the path parameter definition in
                     :py:meth:`pysros.management.Datastore.get` for details.
        :type path: str
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
            if not self._exists(path, Datastore._ExistReason.delete):
                raise make_exception(pysros_err_data_missing)
            self._delete(path)
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
