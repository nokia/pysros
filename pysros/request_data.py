# Copyright 2021 Nokia

import copy
import pprint
import json

from abc import ABC, abstractmethod
from collections import OrderedDict
from contextlib import ExitStack
from enum import Enum, auto
from lxml import etree
from ncclient.xml_ import to_ele
from typing import Union

from .errors import *
from .identifier import NoModule, Identifier
from .model import Model
from .model_walker import FilteredDataModelWalker, ModelWalker
from .singleton import _Singleton, Empty
from .wrappers import Wrapper, Action, Container, Leaf, LeafList
from .yang_type import IdentityRef

COMMON_NAMESPACES = {
    "ncbase": "urn:ietf:params:xml:ns:netconf:base:1.0",
    "monitoring": "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring",
    "library": "urn:ietf:params:xml:ns:yang:ietf-yang-library",
    "nokiaoper": "urn:nokia.com:sros:ns:yang:sr:oper-global",
    "yang_1_0" : "urn:ietf:params:xml:ns:yang:1",
    "attrs"    : "urn:nokia.com:sros:ns:yang:sr:attributes",
}

MO_STATEMENT_TYPES = (Model.StatementType.container_, Model.StatementType.list_, Model.StatementType.action_)
FIELD_STATEMENT_TYPES = (Model.StatementType.leaf_, Model.StatementType.leaf_list_)

_get_tag_name = lambda x: etree.QName(x).localname
_text_in_tag_tail = lambda x: x.tail and x.tail.strip()
_text_in_tag_text = lambda x: x.text and x.text.strip()
_create_root_ele = lambda : etree.Element("dummy-root", nsmap={"nokia-attr": COMMON_NAMESPACES["attrs"]})

def _raise_invalid_text_exception(tag, check_parent_tag=True):
    tag_to_check = tag.getparent() if check_parent_tag else tag
    if tag_to_check.tag == "dummy-root":
        raise make_exception(pysros_err_invalid_xml_root)
    else:
        raise make_exception(pysros_err_invalid_xml_element, element=_get_tag_name(tag_to_check))

def _leaf_to_xml(value, root, walker, ns_map, replace_field=False):
    if walker.get_dds() == Model.StatementType.leaf_:
        value = (value, )
    for i in value:
        txt, add_ns = walker.get_type().to_string(i)
        subelement(root, walker.current.name, ns_map, txt, {f"""{{{COMMON_NAMESPACES["ncbase"]}}}operation""":"replace"} if replace_field else {}, add_ns)
        replace_field=False

class RequestData:
    """Basic API for holding and handling data.

    .. Reviewed by TechComms 20210712
    """

    class _Action(Enum):
        basic   = auto()
        convert = auto()

    def __init__(self, root:Model, ns_map:dict, action:_Action=_Action.basic, walker=FilteredDataModelWalker):
        self._root = root
        self._data = _ListStorage(root, self)
        self._ns_map = ns_map
        self._action = action
        self._Walker = walker
        self._extra_namespaces = {}

    def process_path(self, path:Union[str, FilteredDataModelWalker], *, strict=False):
        """Create all entries in given path and return setter for last section of the path.

        .. Reviewed by TechComms 20210712
        """
        walker = path if isinstance(path, ModelWalker) else self._Walker.user_path_parse(self._root, path, accept_root=(self._action == self._Action.convert))
        current = _ASetter.create_setter(self._data, self)
        for elem, keys in zip(walker.path, walker.keys):
            if not isinstance(current, _MoDataSetter):
                raise make_exception(pysros_err_missing_keys, element=current._walker.get_name())
            if elem.data_def_stm not in FIELD_STATEMENT_TYPES:
                if strict and not current.child_mos.is_created(elem.name.name):
                    raise make_exception(pysros_err_no_data_found)
                current = current.child_mos.get_or_create(elem.name.name)
                if keys:
                    if strict and not current.entry_exists_nocheck(keys):
                        raise make_exception(pysros_err_no_data_found)
                    current = current.entry_nocheck(keys)
            elif current.keys.can_contains(elem.name.name):
                current = current.keys.get(elem.name.name)
            else:
                if not current.fields.contains(elem.name.name):
                    if strict:
                        raise make_exception(pysros_err_no_data_found)
                    else:
                        current.fields.set_getValue(elem.name.name)
                current = current.fields.get(elem.name.name)

        return current

    def set_as_xml(self, value):
        """Populate storage from xml value.

        .. Reviewed by TechComms 20210712
        """
        d = value.xpath("/ncbase:rpc-reply/ncbase:data", namespaces={"ncbase": "urn:ietf:params:xml:ns:netconf:base:1.0"})
        if len(d) != 1:
            raise make_exception(pysros_err_wrong_netconf_response)
        d = d[0]

        root = _ASetter.create_setter(self._data, self)
        root.set_as_xml(d)

    def set_action_as_xml(self, path, value):
        data = value.xpath("/ncbase:rpc-reply", namespaces={"ncbase": "urn:ietf:params:xml:ns:netconf:base:1.0"})
        if len(data) != 1:
            raise make_exception(pysros_err_wrong_netconf_response)
        data = data[0]

        self.process_path(path).set_as_xml(data)

    def to_xml(self):
        """Return storage as xml.

        .. Reviewed by TechComms 20210712
        """
        root = etree.Element(etree.QName('urn:ietf:params:xml:ns:netconf:base:1.0', 'root'))
        self._data._to_xml(self._ns_map, root)
        return list(root[0])

    def xml_tag_has_correct_ns(self, tag, walker):
        """Check if xml namespace is correct.
        """
        if self._action == RequestData._Action.convert and etree.QName(tag).namespace:
            prefix = walker.get_child(_get_tag_name(tag)).current.prefix
            if prefix not in self._ns_map or self._ns_map[prefix] != etree.QName(tag).namespace:
                return False
        return True

    def debug_to_model(self):
        """Print storage as model.

        .. Reviewed by TechComms 20210712
        """
        model = self._data.to_model()
        pprint.pprint(model)

    def debug_dump(self):
        """Dump rquest data in raw form.

        .. Reviewed by TechComms 20210712
        """
        self._data.debug_dump()

    def _unwrap(self, value):
        return value.data if isinstance(value, Wrapper) else value

    def _add_xml_namespace(self, identity):
        assert self._ns_map[identity.module] == identity.namespace
        self._extra_namespaces[identity.module] = identity.namespace


class _AStorage(ABC):
    """Abstract representation of data storage.

    .. Reviewed by TechComms 20210712
    """
    def __init__(self, rd:RequestData):
        self.rd = rd

    def to_xml(self, ns_map, root):
        """Return data in xml format.

        .. Reviewed by TechComms 20210712
        """
        return self._to_xml(ns_map, root)

    @abstractmethod
    def _to_xml(self, ns_map, root):
        """Implementation of returning data in xml format.

        """
        pass

    @abstractmethod
    def to_model(self, *, key_filter={}):
        """Return data as user model.

        .. Reviewed by TechComms 20210712
        """
        pass

    @property
    def _walker(self):
        return self.rd._Walker(self._model)

    def _resolve_xml_name(self, model, ns_map):
        if model.name.prefix in ns_map:
            return etree.QName(ns_map[model.name.prefix], model.name.name)
        elif model.name.prefix is NoModule():
            return model.name.name
        else:
            raise make_exception(pysros_err_prefix_does_not_have_ns, prefix=model.name.prefix, name=model.name.name)

def subelement(parent, tag, nsmap, text=None, attrib=None, add_ns=None):
    """Wrapper around etree.Subelement, that raises SrosMgmtError instead of ValueError."""
    local_nsmap = {}
    if add_ns:
        local_nsmap[add_ns] = nsmap[add_ns]
    try:
        if tag.is_builtin():
            result = etree.SubElement(parent, tag.name, attrib, nsmap=local_nsmap)
        else:
            module = tag.prefix
            uri = nsmap[module]
            local_nsmap[module] = uri
            result = etree.SubElement(
                parent,
                etree.QName(uri, tag.name),
                attrib,
                nsmap=local_nsmap
            )

        if text is not None:
            result.text = text
        return result
    except ValueError as err:
        raise SrosMgmtError(err.args) from None

class _MoStorage(_AStorage):
    """Data storage for containers and list entries (list+local keys).

    .. Reviewed by TechComms 20210712
    """

    def __init__(self, model:Model, local_keys, rd:RequestData):
        super().__init__(rd)
        self._model = model
        self._local_keys = copy.deepcopy(local_keys)
        self._child = {}
        self._operation = ""
        self._replace_field = "" # Could be field storage

    def _to_xml(self, ns_map, root):
        root_attr = None if not self._operation else {f"""{{{COMMON_NAMESPACES["ncbase"]}}}operation""": self._operation}
        root = subelement(root, self._model.name, ns_map, None, root_attr)
        for k, v in self._local_keys.items():
            if v is FieldValuePlaceholder():
                pass
            elif v is GetValuePlaceholder():
                self._leaf_placeholder_to_xml(v, root, self._walker.get_child(k), ns_map)
            else:
               txt, add_ns = self._walker.get_child(k).get_type().to_string(v)
               subelement(root, self._walker.get_child(k).current.name, ns_map, txt, {}, add_ns)

        for k, v in self._child.items():
            if isinstance(v, (_MoStorage, _ListStorage)):
                v._to_xml(ns_map, root)
            else:
                if v is Delete():
                    subelement(root, self._walker.get_child(k).current.name, ns_map, None, {f"""{{{COMMON_NAMESPACES["ncbase"]}}}operation""": "remove"})
                elif v is FieldValuePlaceholder():
                    pass
                elif v is GetValuePlaceholder():
                    self._leaf_placeholder_to_xml(v, root, self._walker.get_child(k), ns_map)
                elif self._replace_field and self._replace_field == k:
                    _leaf_to_xml(v, root, self._walker.get_child(k), ns_map, replace_field=True)
                else:
                    _leaf_to_xml(v, root, self._walker.get_child(k), ns_map)

    def to_xml(self, ns_map, root):
        root_attr = None if not self._operation else {f"""{{{COMMON_NAMESPACES["ncbase"]}}}operation""": self._operation}

        for k, v in self._child.items():
            if isinstance(v, (_MoStorage, _ListStorage)):
                v._to_xml(ns_map, root)
            else:
                if v is Delete():
                    subelement(root, self._walker.get_child(k).current.name, ns_map, None, {f"""{{{COMMON_NAMESPACES["ncbase"]}}}operation""": "remove"})
                elif v is FieldValuePlaceholder():
                    pass
                elif v is GetValuePlaceholder():
                    self._leaf_placeholder_to_xml(v, root, self._walker.get_child(k), ns_map)
                elif self._replace_field and self._replace_field == k:
                    _leaf_to_xml(v, root, self._walker.get_child(k), ns_map, replace_field=True)
                else:
                    _leaf_to_xml(v, root, self._walker.get_child(k), ns_map)

    def _leaf_placeholder_to_xml(self, value, root, walker, ns_map):
        subelement(root, walker.current.name, ns_map)

    def to_model(self, *, key_filter={}):
        data = {}
        is_selection_filter = {} in key_filter.values()
        for k, v in self._local_keys.items():
            if is_selection_filter and k not in key_filter:
                continue
            data[k] = self._leaf_to_model(k, v)
        for k, v in self._child.items():
            key_proxy = DictionaryKeysProxy(self.rd._unwrap(key_filter))
            if is_selection_filter and self._walker.get_child(k).current.name not in key_proxy:
                continue
            if not isinstance(v, (_MoStorage, _ListStorage)):
                data[k] = self._leaf_to_model(k, v)
            else:
                data[k] = v.to_model(key_filter=(key_filter.get(k, {})))
                if not data[k] and not self._walker.get_child(k).has_explicit_presence():
                    del data[k]
        if self._walker.is_root:
            return data
        if self._model.data_def_stm == Model.StatementType.action_:
            return Action._with_model(data, self._model)
        return Container._with_model(data, self._model)

    def _leaf_to_model(self, name, value):
        assert self.rd._action == RequestData._Action.convert or value is not GetValuePlaceholder()
        assert value is not FieldValuePlaceholder()
        model = self._walker.get_child(name).current
        if self._walker.get_child_dds(name) == Model.StatementType.leaf_:
            return Leaf._with_model(value, model)
        return LeafList._with_model(value, model)

    def keys_equal(self, keys):
        """Compare if keys are equal. Keys are expected as dict(name->value).

        .. Reviewed by TechComms 20210712
        """
        return self._local_keys == keys

    def get_keys_flat(self):
        keys = tuple(self._local_keys[key] for key in self._model.local_keys)
        if len(keys) == 1: keys = keys[0]
        return keys

    def debug_dump(self, indent=0):
        line = " "*indent
        if self._operation:
            line += self._operation + " "
        line += self._walker.get_name().name
        if self._local_keys:
            line += " ["
            line += ", ".join(f"{k}={v}" for k, v in self._local_keys.items())
            line += "]"
        line += " {"
        print(line)
        for k, v in self._child.items():
            if isinstance(v, _AStorage):
                v.debug_dump(indent+1)
            else:
                print(f"{' '*(indent+1)}{k} = {v}")
        print((" "*indent)+"}")


class _ListStorage(_AStorage):
    """Storage for all entries for a specific list.

    .. Reviewed by TechComms 20210712
    """
    def __init__(self, model:Model, rd:RequestData):
        if model.data_def_stm in (Model.StatementType.container_, Model.StatementType.action_):
            self.__class__ = _MoStorage
            self.__class__.__init__(self, model, {}, rd)
        else:
            super().__init__(rd)
            self._model = model
            self._entries = {}
            self._operation = ""

    def _to_xml(self, ns_map, root):
        if self._entries:
            for entry in self._entries.values():
                entry._to_xml(ns_map, root)
        else:
            subelement(root, self._model.name, ns_map)

    def to_xml(self, ns_map, root):
        if self._entries:
            for entry in self._entries.values():
                entry._to_xml(ns_map, root)

    def to_model(self, *, key_filter={}):
        d = OrderedDict() if self._model.user_ordered else {}
        for e in self._entries.values():
            d[e.get_keys_flat()] = e.to_model(key_filter=key_filter)

        return d

    def get_entry(self, keys):
        """Get entry by keys. Keys are expected as dict(name->value).

        .. Reviewed by TechComms 20210712
        """
        res = self._entries.get(tuple(sorted(keys.items())), None)
        if res is None:
            raise make_exception(pysros_err_entry_does_not_exists)
        return res

    def get_or_create_entry(self, keys):
        """Get entry by keys. Create the entry if it does not exist. Keys are expected as dict(name->value).

        .. Reviewed by TechComms 20210712
        """
        try:
            return self.get_entry(keys)
        except KeyError:
            return self.add_entry(keys)

    def has_entry(self, keys):
        """Determine if entry with specific keys exists. Keys are expected as dict(name->value).

        .. Reviewed by TechComms 20210712
        """
        try:
            self.get_entry(keys)
            return True
        except KeyError:
            return False

    def add_entry(self, keys):
        """Add new entry with specific keys. Entry cannot already exist. Keys are expected as dict(name->value).

        .. Reviewed by TechComms 20210712
        """
        assert not self.has_entry(keys)
        res = _MoStorage(self._model, keys, self.rd)
        self._entries[tuple(sorted(keys.items()))] = res
        return res

    def debug_dump(self, indent=0):
        for i in self._entries.values():
            i.debug_dump(indent+1)

class DictionaryKeysProxy():
    """Proxy for dictionary keys which unwraps keys and compares by performing Identifier.__eq__"""
    def __init__(self, data):
        if not isinstance(data, dict):
            raise make_exception(pysros_err_invalid_value, data=data)
        self.data = data

    def __getitem__(self, key:Identifier):
        #need to call Identifier.__eq__
        for k in self.data.keys():
            if key == k:
                return self._unwrap(self.data[k])
        raise KeyError(key)

    def __contains__(self, val:Identifier):
        #need to call Identifier.__eq__
        for ele in self.data:
            if val == ele:
                return True
        return False

    def __str__(self):
        return str(self.data)

    def _unwrap(self, val):
        return val.data if isinstance(val, Wrapper) else val

class RdJsonEncoder(json.JSONEncoder):
    def add_ns(self, o, d, walker:ModelWalker):
        if o is self.root:
            return {walker.get_child(k).get_name().model_string: v for k, v in d.items()}
        return {walker.get_child(k).get_name().model_string if walker.get_name().prefix != walker.get_child(k).get_name().prefix else k: v for k, v in d.items()}

    def default(self, o):
        is_root = o is self.root
        if isinstance(o, _MoStorage):
            res = {}
            if not is_root:
                res.update(self.add_ns(o, o._local_keys, o._walker))
            elif is_root and self.force_key:
                res[o._walker.get_child(self.force_key).get_name().model_string] = o._local_keys[self.force_key]
            res.update(self.add_ns(o, o._child, o._walker))
            stringify = lambda x, dds: [str(v) for v in x] if dds == Model.StatementType.leaf_list_ else str(x)
            cvt = lambda k, v: stringify(v, o._walker.get_child_dds(k)) if o._walker.get_child_dds(k) in FIELD_STATEMENT_TYPES and o._walker.get_child_type(k).json_name() in ("int64", "uint64") else v
            res = {k: cvt(k, v) for k, v in res.items()}
            return res
        elif isinstance(o, _ListStorage):
            res = list(o._entries.values())
            return {o._walker.get_name().model_string: res} if is_root else res
        elif isinstance(o, (str, list, dict, bool)):
            return o
        elif o is Empty:
            return [None]
        else:
            return str(o)

class _ASetter(ABC):
    """Data setter representation for storage classes.

    .. Reviewed by TechComms 20210712
    """
    def __init__(self, storage:"_AStorage", rd:RequestData):
        self._storage = storage
        self.rd = rd

    @property
    def _walker(self):
        return self.rd._Walker(self._storage._model)

    @staticmethod
    def create_setter(storage:"_AStorage", rd:RequestData):
        if isinstance(storage, _MoStorage):
            return _MoDataSetter(storage, rd)
        else:
            return _ListSetter(storage, rd)

    @abstractmethod
    def set(self, value):
        """Set data in model format.

        .. Reviewed by TechComms 20210712
        """
        pass

    @abstractmethod
    def set_as_xml(self, value):
        """Set data in xml format.

        .. Reviewed by TechComms 20210712
        """
        pass

    def checkJsonDuplicates(x):
        if len(x) != len({i[0] for i in x}):
            raise make_exception(pysros_err_multiple_occurences_of_node)
        return dict(x)

    def set_as_json(self, value):
        """Set data in json format."""
        try:
            val = json.loads(value, object_pairs_hook=_ASetter.checkJsonDuplicates)
        except json.JSONDecodeError as e:
            raise JsonDecodeError(*e.args) from None

        if not isinstance(val, dict):
            raise make_exception(pysros_err_wrong_json_root)

        self._set_as_json(val, is_root = True)

    @abstractmethod
    def _set_as_json(self, value, is_root = False):
        """Implementation of setter for JSON."""
        pass

    def to_json(self, pprint = True):
        """Return data in json format."""
        members = {
            "root": self._storage,
            "root_setter": self,
            "force_key": getattr(self, "_key_name", None),
        }
        encoder = type("RdJsonEncoderSpecialization", (RdJsonEncoder, ), members)
        indent = 4 if pprint else None
        return json.dumps(self._storage, cls=encoder, indent=indent)

    @abstractmethod
    def delete(self):
        """Set data operation to delete"""
        pass

    @abstractmethod
    def replace(self):
        """Set data operation to replace"""
        pass

    def entry_get_keys(self):
        """Set list keys as a placeholders"""
        raise make_exception(pysros_err_target_should_be_list)


    def to_model(self, *, key_filter={}):
        """Return data in model format.

        .. Reviewed by TechComms 20210712
        """
        return self._storage.to_model(key_filter=key_filter)

    def to_xml(self):
        """Return data in xml format."""
        root = _create_root_ele()
        self._storage.to_xml(self.rd._ns_map, root)
        return root


    def set_filter(self, value):
        """Populate request data with filter syntax"""
        raise make_exception(pysros_err_filter_not_supported_on_leaves)

    def is_compare_supported_endpoint(self):
        return False

    def is_action(self):
        return self._walker.get_dds() == Model.StatementType.action_

    def entry_xml(self, value):
        """For XML there is no tag for the list itself, only for entries.
        Therefore, the list setter can be avoided, however, you must create
        an entry setter and it simplifies the code if you always create
        an entry regardless of the child type.  It is effective only for
        the list setter."""
        return self

    def _as_storage_type(self, val, *, child_name=None):
        walker = self._walker.get_child(child_name) if child_name else self._walker
        if walker.get_dds() == Model.StatementType.leaf_list_:
            return [walker.get_type().as_storage_type(v, self.rd._action == RequestData._Action.convert, self.rd._add_xml_namespace) for v in val]
        else:
            return walker.get_type().as_storage_type(val, self.rd._action == RequestData._Action.convert, self.rd._add_xml_namespace)

    def _handle_entry_keys_namespaces(self, entry):
        """Strip namespace prefixes from entry key names.
        Also raise an error if there are two identical entry keys, one with the namespace prefix and other one without it.
        """
        local_keys = [Identifier(self._walker.get_name().prefix, k) for k in self._walker.get_local_key_names()]
        for k in local_keys:
            if k.model_string in entry:
                if k.name in entry:
                    raise make_exception(pysros_err_malformed_keys, full_path=self._walker, value=entry[k.model_string])
                entry[k.name] = entry.pop(k.model_string)

class _LeafSetter(_ASetter):
    """Interface for managing leafs. Because leafs do not have dedicated storage, the
       class has its own implementation of to_model method.

    .. Reviewed by TechComms 20210713
    """
    def __init__(self, storage:"_ListStorage", leaf_name:str, rd:RequestData):
        super().__init__(storage, rd)
        self._leaf_name = leaf_name

    def set(self, value):
        value = self.rd._unwrap(value)
        if not self._walker.check_field_value(value):
            raise make_exception(pysros_err_incorrect_leaf_value, leaf_name=self._leaf_name)
        else:
            val = self._as_storage_type(value)
            self._set_nocheck(val)

    def _set_nocheck(self, value):
        self._storage._child[self._leaf_name] = value

    def set_getValue(self):
        self._storage._child[self._leaf_name] = GetValuePlaceholder()

    def set_as_xml(self, value):
        if not len(value):
            raise make_exception(pysros_err_malformed_xml)
        for v in value:
            self.set_or_append_as_xml(v)

    def _set_as_json(self, value, is_root = False):
        if not isinstance(value, dict):
            raise make_exception(pysros_err_invalid_json_structure)
        value = {k:v for k, v in value.items() if not k.startswith("@")}
        if len(value) != 1:
            raise make_exception(pysros_err_invalid_json_structure)

        val = next(iter(value.items()))
        if self._walker.get_name() != val[0]:
            raise make_exception(pysros_err_invalid_json_structure)
        val = val[1]
        if self._walker.get_type().json_name() in ("int64", "uint64"):
            if self._walker.get_dds() != Model.StatementType.leaf_list_:
                val = [self.rd._unwrap(val)]
            else:
                val = self.rd._unwrap(val)
            if not isinstance(val, list) or not all(isinstance(v, str) for v in val):
                raise make_exception(pysros_err_incorrect_leaf_value, leaf_name=self._walker.get_name().name)
            try:
                value = [int(self.rd._unwrap(v)) for v in val]
            except:
                raise make_exception(pysros_err_incorrect_leaf_value, leaf_name=self._walker.get_name().name) from None
        self.set(self._walker.as_model_type(val))

    def set_or_append_as_xml(self, value_element):
        if _text_in_tag_tail(value_element) or (self._walker.get_dds() == Model.StatementType.leaf_list_ and _text_in_tag_text(value_element.getparent())):
            _raise_invalid_text_exception(value_element)
        value = self._walker.as_model_type(value_element.text or "")

        if isinstance(self._walker.get_type(), IdentityRef):
            is_leaf_list = isinstance(value, list)
            assert not is_leaf_list or len(value) == 1
            identity = self._walker.get_type()._find_identity(value[0] if is_leaf_list else value)
            if not identity:
                raise make_exception(pysros_err_incorrect_leaf_value, leaf_name = self._walker.current.name.name)
            value_ns = value_element.nsmap.get(identity.module, None)
            if value_ns is not None and value_ns!=identity.namespace:
                raise make_exception(pysros_err_incorrect_leaf_value, leaf_name = self._walker.current.name.name)

        if self._walker.get_dds() == Model.StatementType.leaf_list_ and isinstance(self._storage._child.get(self._leaf_name), list):
            value = self._storage._child[self._leaf_name] + value
        self.set(value)

    def to_model(self, *, key_filter={}):
        return self._storage._leaf_to_model(self._leaf_name, self._storage._child[self._leaf_name])

    def to_xml(self):
        root = _create_root_ele()
        _leaf_to_xml(self._storage._child[self._leaf_name], root, self._walker, self.rd._ns_map)
        return root

    def delete(self):
        if self._walker.get_dds() == Model.StatementType.leaf_list_:
            raise make_exception(pysros_err_invalid_operation_on_leaflist)
        self._storage._child[self._leaf_name] = Delete()

    def replace(self):
        self._storage._replace_field = self._leaf_name

    @property
    def _walker(self):
        return super()._walker.get_child(self._leaf_name)

class _KeySetter(_ASetter):
    """Interface for keys. Most of this class are stub methods to provide
       setter interface to keys."""
    def __init__(self, storage:"_ListStorage", key_name:str, rd:RequestData):
        super().__init__(storage, rd)
        self._key_name = key_name

    def set(self, value):
        value = self.rd._unwrap(value)
        if not self._walker.check_field_value(value):
            raise make_exception(pysros_err_incorrect_leaf_value, leaf_name=self._key_name)
        elif self._as_storage_type(value) != self._storage._local_keys[self._key_name]:
            raise make_exception(pysros_err_key_val_mismatch, key_name=self._key_name)

    def set_getValue(self):
        pass

    def set_placeholder(self):
        pass

    def to_model(self, *, key_filter={}):
        return self._storage._leaf_to_model(self._key_name, self._storage._local_keys[self._key_name])

    def to_xml(self):
        root = _create_root_ele()
        _leaf_to_xml(self._storage._local_keys[self._key_name], root, self._walker, self.rd._ns_map)
        return root

    def delete(self):
        raise make_exception(pysros_err_invalid_operation_on_key)

    def replace(self):
        raise make_exception(pysros_err_invalid_operation_on_key)

    def set_as_xml(self, value):
        if _text_in_tag_tail(value):
            _raise_invalid_text_exception(value_element)
        if not len(value):
            raise make_exception(pysros_err_malformed_xml)
        for v in value:
            if _text_in_tag_tail(v):
                _raise_invalid_text_exception(v)
            self.set(self._walker.as_model_type(v.text or ""))

    def _set_as_json(self, value, is_root = False):
        if not isinstance(value, dict):
            raise make_exception(pysros_err_invalid_json_structure)
        value = {k:v for k, v in value.items() if not k.startswith("@")}
        if  len(value) != 1:
            raise make_exception(pysros_err_invalid_json_structure)

        val = next(iter(value.items()))
        if self._walker.get_name() != val[0]:
            raise make_exception(pysros_err_invalid_json_structure)
        if self._walker.get_type().json_name() in ("int64", "uint64"):
            if not isinstance(val[1], str):
                raise make_exception(pysros_err_incorrect_leaf_value, leaf_name=self._walker.get_name().name)
            try:
                value = int(val[1])
            except:
                raise make_exception(pysros_err_incorrect_leaf_value, leaf_name=self._walker.get_name().name) from None
        self.set(self._walker.as_model_type(val[1]))

    @property
    def _walker(self):
        return super()._walker.get_child(self._key_name)

class _ListSetter(_ASetter):
    """Interface for managing instances of specific list.

    .. Reviewed by TechComms 20210712
    """

    def set(self, value):
        """Set a value in a list.

        Keys may be in format {(key1, key2) : Container({}), (key1, key2) : Container({})}
        or directly in entry {key1: value1, key2: value2, field1 : value}.

        .. Reviewed by PLM 20211018
        """
        is_wrapped = isinstance(value, Container)
        value = self.rd._unwrap(value)
        value = copy.copy(value)
        unwrapper = DictionaryKeysProxy(value)
        if value and not is_wrapped and self._walker.dict_keys(value):
            for k, v in value.items():
                self._handle_entry_keys_namespaces(v)
                self.entry(self._tuple_to_dict(k)).set(v)
        elif self._walker.entry_keys(unwrapper):
            self._handle_entry_keys_namespaces(value)
            self.entry(value).set(value)
        else:
            raise make_exception(pysros_err_malformed_keys, full_path=self._walker, value=value)

    def set_filter(self, value):
        value = copy.copy(value)
        self._handle_entry_keys_namespaces(value)
        for k in self._walker.get_local_key_names():
            if k not in value:
                value[k] = FieldValuePlaceholder()
        self.entry_nocheck(value).set_filter(value)

    def _tuple_to_dict(self, t):
        return {k:v for k, v in zip(self._walker.get_local_key_names(), (t if isinstance(t, tuple) else (t, )))}

    def _extract_keys(self, entry):
        return {k:self._as_storage_type(v, child_name=k) for k, v in entry.items() if k in self._walker.get_local_key_names()}

    def _convert_keys_to_model(self, entry):
        try:
            def unwrap(v):
                return v.data if isinstance(v, Wrapper) else v
            val =  {k: (GetValuePlaceholder() if unwrap(v) in (GetValuePlaceholder(), {}) else self._walker.as_child_model_type(k, unwrap(v))) for k, v in entry.items() if v is not FieldValuePlaceholder()}
            return val
        except:
            raise make_exception(pysros_err_invalid_key_in_path) from None

    def _check_and_unwrap_keys(self, entry, *, json=False):
        for k in self._walker.get_local_key_names():
            if k not in entry:
                raise make_exception(pysros_err_malformed_keys, full_path=self._walker, value=k)
            entry[k] = self.rd._unwrap(entry[k])
            if not self._walker.check_child_field_value(k, entry[k], json=json):
                raise make_exception(pysros_err_incorrect_leaf_value, leaf_name=k)
            entry[k] = self._walker.get_child_type(k).as_storage_type(entry[k], self.rd._action == RequestData._Action.convert, self.rd._add_xml_namespace)

    def entry(self, value, *, json=False):
        """Receive entry with specified keys in value. Keys are expected as dict(name->value). Additional
        fields may be present (no verification for extra fields).

        .. Reviewed by TechComms 20210712
        """
        if json:
            value = copy.copy(value)
        self._handle_entry_keys_namespaces(value)
        self._check_and_unwrap_keys(value, json=json)
        return _MoDataSetter(self._storage.get_or_create_entry(self._extract_keys(value)), self.rd)

    def add_entry(self, value, *, json=False):
        if json:
            value = copy.copy(value)
        self._handle_entry_keys_namespaces(value)
        self._check_and_unwrap_keys(value, json=json)
        keys = self._extract_keys(value)
        if self._storage.has_entry(keys):
            raise make_exception(pysros_err_multiple_occurences_of_entry)
        return _MoDataSetter(self._storage.get_or_create_entry(keys), self.rd)

    def entry_nocheck(self, value):
        """Receive entry with specified keys in value without checking for the correct type. Keys are expected
        as dict(name->value). Additional fields may be present (no verification for extra fields).

        .. Reviewed by PLM 20211018
        """
        return _MoDataSetter(self._storage.get_or_create_entry(self._convert_keys_to_model(self._extract_keys(value))), self.rd)

    def entry_exists_nocheck(self, value):
        """Receive entry with specified keys in value without checking for the correct type. Keys are expected
        as dict(name->value). Additional fields may be present (no verification for extra fields)
        Returns true if entry exists, otherwise false.
        """
        return self._storage.has_entry(self._convert_keys_to_model(self._extract_keys(value)))

    def entry_xml(self, value):
        keys = {}
        for e in value:
            if _get_tag_name(e) in self._walker.get_local_key_names():
                if _text_in_tag_tail(e):
                    _raise_invalid_text_exception(e)
                keys[_get_tag_name(e)] = e.text or ""
        if set(keys.keys()) != set(self._walker.get_local_key_names()):
            raise make_exception(pysros_err_malformed_keys, full_path=self._walker, value=keys)
        if self.entry_exists_nocheck(keys):
            raise make_exception(pysros_err_multiple_occurences_of_entry)
        return self.entry_nocheck(keys)

    def set_as_xml(self, value):
        for v in value:
            self.entry_xml(v).set_as_xml(v)

    def _set_as_json(self, value, is_root = False):
        if is_root:
            if not isinstance(value, dict):
                raise make_exception(pysros_err_invalid_json_structure)
            value = {k:v for k, v in value.items() if not k.startswith("@")}
            if len(value) != 1:
                raise make_exception(pysros_err_invalid_json_structure)
            value = next(iter(value.items()))
            if self._walker.get_name() != value[0] or not isinstance(value[1], list):
                raise make_exception(pysros_err_invalid_json_structure)
            value = value[1]
        else:
            if not isinstance(value, list) or not all(isinstance(i, dict) for i in value):
                raise make_exception(pysros_err_convert_invalid_value_for_type, name=self._walker.get_name().name)
        for v in value:
            self.add_entry(v, json=True)._set_as_json(v)

    def delete(self):
        raise make_exception(pysros_err_invalid_path_operation_missing_keys)

    def replace(self):
        for k, v in self._storage._entries.items():
            v._operation = "replace"

    def entry_get_keys(self):
        keys = {key:GetValuePlaceholder() for key in self._walker.get_local_key_names()}
        setter = _MoDataSetter(self._storage.get_or_create_entry(keys), self.rd)
        setter.set({})
        return setter

class _MoDataSetter(_ASetter):
    """Interface managing specific list entry or container.

    .. Reviewed by TechComms 20210712
    """
    class _AChild:
        def __init__(self, setter:"_MoDataSetter"):
            self._setter = setter

        @property
        def _walker(self):
            return self._setter.rd._Walker(self._setter._storage._model)

    class _Keys(_AChild):
        """Interface for retrieving and setting keys.

        .. Reviewed by TechComms 20210712
        """
        def set(self, name, value):
            name = Identifier.from_model_string(name).name
            self.get(name).set(value)

        def set_as_json(self, name, value):
            name = Identifier.from_model_string(name).name
            self.get(name)._set_as_json({name: value})

        def set_getValue(self, name):
            self.get(name).set_getValue()

        def set_placeholder(self, name):
            self.get(name).set_placeholder()

        def get(self, name):
            if not self.can_contains(name):
                raise make_exception(pysros_err_unknown_child, child_name=name, path=self._walker._get_path())
            return _KeySetter(self._setter._storage, name, self._setter.rd)

        def contains(self, name):
            return self.can_contains(name)

        def can_contains(self, name):
            return self._walker.has_local_key_named(name)

    class _Fields(_AChild):
        """Interface for retrieving and setting fields.

        .. Reviewed by TechComms 20210712
        """

        def set(self, name, value):
            name = Identifier.from_model_string(name).name
            self.get(name).set(value)

        def set_as_json(self, name, value):
            name = Identifier.from_model_string(name).name
            self.get(name)._set_as_json({name: value})

        def set_getValue(self, name):
            self.get(name).set_getValue()

        def get(self, name):
            if not self.can_contains(name):
                raise make_exception(pysros_err_unknown_child, child_name=name, path=self._walker._get_path())
            return _LeafSetter(self._setter._storage, name, self._setter.rd)

        def get_nonexisting(self, name):
            if not self.can_contains(name):
                raise make_exception(pysros_err_unknown_child, child_name=name, path=self._walker._get_path())
            if self.contains(name) and self._walker.get_child_dds(name) != Model.StatementType.leaf_list_:
                raise make_exception(pysros_err_multiple_occurences_of_node)
            return _LeafSetter(self._setter._storage, name, self._setter.rd)

        def contains(self, name):
            return name in self._setter._storage._child

        def can_contains(self, name):
            return self._walker.has_field_named(name)


    class _ChildMos(_AChild):
        """Interface for retrieving and setting children.

        .. Reviewed by TechComms 20210712
        """
        def set(self, name, value):
            self.get_or_create(Identifier.from_model_string(name).name).set(value)

        def set_as_json(self, name, value):
            self.get_or_create(Identifier.from_model_string(name).name)._set_as_json(value)

        def get_or_create(self, name):
            if self._walker.get_child_dds(name) in MO_STATEMENT_TYPES:
                if not self.is_created(name):
                    self._setter._storage._child[name] = _ListStorage(self._setter._walker.get_child(name).current, self._setter.rd)
                return _ASetter.create_setter(self._setter._storage._child[name], self._setter.rd)
            else:
                raise KeyError(name)

        def get(self, name):
            if self._walker.get_child_dds(name) in MO_STATEMENT_TYPES:
                if self.is_created(name):
                    if not self._walker.get_child_dds(name) == Model.StatementType.list_:
                        raise make_exception(pysros_err_multiple_occurences_of_node)
                else:
                    self._setter._storage._child[name] = _ListStorage(self._setter._walker.get_child(name).current, self._setter.rd)
                return _ASetter.create_setter(self._setter._storage._child[name], self._setter.rd)
            else:
                raise KeyError(name)

        def is_created(self, name):
            return self._walker.get_child_dds(name) in MO_STATEMENT_TYPES and name in self._setter._storage._child


    @property
    def keys(self):
        return self._Keys(self)

    @property
    def fields(self):
        return self._Fields(self)

    @property
    def child_mos(self):
        return self._ChildMos(self)

    def set(self, value):
        value = self.rd._unwrap(value)
        if not isinstance(value, dict):
            raise make_exception(pysros_err_invalid_value, data=value)
        children_to_set = set()
        walker = self._walker
        for k, v in value.items():
            if k in walker.get_local_key_names():
                self.keys.set(k, v)
            elif walker.get_child_dds(k) in FIELD_STATEMENT_TYPES:
                self.fields.set(k, v)
            elif walker.get_child_dds(k) in MO_STATEMENT_TYPES:
                self.child_mos.set(k, v)
            else:
                raise make_exception(pysros_err_unknown_dds, dds=walker.get_child_dds(k))
            name = Identifier.from_model_string(k).name
            if name in children_to_set:
                raise make_exception(pysros_err_duplicate_found, duplicate=name)
            children_to_set.add(name)

    def set_filter(self, value):
        value = self.rd._unwrap(value)
        if not isinstance(value, dict):
            raise make_exception(pysros_err_invalid_value, data=value)
        self._handle_entry_keys_namespaces(value)
        children_to_set = set()
        for k, v in value.items():
            v = self.rd._unwrap(v)
            if k in self._walker.get_local_key_names():
                if v == {} or v is GetValuePlaceholder():
                    self.keys.set_getValue(k)
                elif v is FieldValuePlaceholder():
                    self.keys.set_placeholder(k)
                else:
                    self.keys.set(k, v)
            elif self._walker.get_child_dds(k) in FIELD_STATEMENT_TYPES:
                if v == {}:
                    self.fields.set_getValue(k)
                else:
                    self.fields.set(k, v)
            elif self._walker.get_child_dds(k) in MO_STATEMENT_TYPES:
                self.child_mos.get_or_create(k).set_filter(v)
            else:
                raise make_exception(pysros_err_unknown_dds, dds=self._walker.get_child_dds(k))
            name = Identifier.from_model_string(k).name
            if name in children_to_set:
                raise make_exception(pysros_err_duplicate_found, duplicate=name)
            children_to_set.add(name)

    def set_as_xml(self, value):
        walker = self._walker
        if self.rd._action != RequestData._Action.convert:
            walker.return_blocked_regions = True
        if _text_in_tag_text(value):
            _raise_invalid_text_exception(value, check_parent_tag=False)
        if _text_in_tag_tail(value):
            _raise_invalid_text_exception(value)
        for e in value:
            if not walker.has_child(_get_tag_name(e)) or not self.rd.xml_tag_has_correct_ns(e, walker):
                raise make_exception(pysros_err_unknown_child, child_name=_get_tag_name(e), path=walker._get_path())
            if walker.is_region_blocked_in_child(_get_tag_name(e)):
                continue
            else:
                if walker.get_child_dds(_get_tag_name(e)) in FIELD_STATEMENT_TYPES:
                    if _get_tag_name(e) not in walker.get_local_key_names():
                        self.fields.get_nonexisting(_get_tag_name(e)).set_or_append_as_xml(e)
                    elif self.rd._action == RequestData._Action.convert:
                        xml = to_ele(f"<{_get_tag_name(value)}>{etree.tostring(e, encoding='unicode')}</{_get_tag_name(value)}>")
                        _KeySetter(self._storage, _get_tag_name(e), self.rd).set_as_xml(xml)
                elif walker.get_child_dds(_get_tag_name(e)) in MO_STATEMENT_TYPES:
                    self.child_mos.get(_get_tag_name(e)).entry_xml(e).set_as_xml(e)

    def _set_as_json(self, value, is_root = False):
        if not isinstance(value, dict):
            raise make_exception(pysros_err_invalid_json_structure)

        children_to_set = set()
        for k, v in value.items():
            if k.startswith("@"):
                continue
            self._walker.get_child(k) #module name check?
            k = Identifier.from_model_string(k).name
            if k in self._walker.get_local_key_names():
                self.keys.set_as_json(k, v)
            elif self._walker.get_child_dds(k) in FIELD_STATEMENT_TYPES:
                self.fields.set_as_json(k, v)
            elif self._walker.get_child_dds(k) in MO_STATEMENT_TYPES:
                self.child_mos.set_as_json(k, v)
            else:
                raise make_exception(pysros_err_unknown_dds, dds=self._walker.get_child_dds(k))
            name = Identifier.from_model_string(k).name
            if name in children_to_set:
                raise make_exception(pysros_err_duplicate_found, duplicate=name)
            children_to_set.add(name)

    def delete(self):
        self._storage._operation = "delete"

    def replace(self):
        self._storage._operation = "replace"

    def is_compare_supported_endpoint(self):
        return True

class GetValuePlaceholder(metaclass=_Singleton):
    pass

class FieldValuePlaceholder(metaclass=_Singleton):
    pass

class Delete(metaclass=_Singleton):
    pass
