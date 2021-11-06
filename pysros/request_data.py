# Copyright 2021 Nokia

import copy
import pprint

from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Union
from contextlib import ExitStack

from lxml import etree

from .errors import *
from .identifier import NoModule, Identifier
from .model import Model
from .model_walker import FilteredDataModelWalker, ModelWalker
from .wrappers import *
from .wrappers import _Singleton, Wrapper

_get_tag = lambda x: etree.QName(x).localname

class RequestData:
    """Basic API for holding and handling data.

    .. Reviewed by TechComms 20210712
    """
    def __init__(self, root:Model, ns_map:dict):
        self._root = root
        self._data = _ListStorage(root)
        self._ns_map = ns_map

    def process_path(self, path:Union[str, FilteredDataModelWalker], *, strict=False):
        """Create all entries in given path and return setter for last section of the path.

        .. Reviewed by TechComms 20210712
        """
        walker = path if isinstance(path, ModelWalker) else FilteredDataModelWalker.path_parse(self._root, path)
        current = _ASetter.create_setter(self._data)
        for elem, keys in zip(walker.path, walker.keys):
            if not isinstance(current, _MoDataSetter):
                raise make_exception(pysros_err_missing_keys, element=current._walker.get_name())
            if elem.data_def_stm not in (Model.StatementType.leaf_, Model.StatementType.leaf_list_):
                if strict and not current.child_mos.is_created(elem.name.name):
                    raise make_exception(pysros_err_no_data_found)
                current = current.child_mos.get_or_create(elem.name.name)
                if keys:
                    current = current.entry_nocheck(keys)
            elif current.keys.can_contains(elem.name.name):
                current = current.keys.get(elem.name.name)
            else:
                if not current.fields.contains(elem.name.name):
                    if strict:
                        raise make_exception(pysros_err_no_data_found)
                    else:
                        current.fields.set_placeholder(elem.name.name)
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

        root = _ASetter.create_setter(self._data)
        root.set_as_xml(d)

    def to_xml(self):
        """Return storage as xml.

        .. Reviewed by TechComms 20210712
        """
        root = etree.Element("root")
        self._data.to_xml(self._ns_map, root)
        return list(root[0])

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


class _AStorage(ABC):
    """Abstract representation of data storage.

    .. Reviewed by TechComms 20210712
    """

    @abstractmethod
    def to_xml(self, ns_map, root):
        """Return data in xml format.

        .. Reviewed by TechComms 20210712
        """
        pass

    @abstractmethod
    def to_model(self, *, config_only=False):
        """Return data as user model.

        .. Reviewed by TechComms 20210712
        """
        pass

    @property
    def _walker(self):
        return FilteredDataModelWalker(self._model)

    def _resolve_xml_name(self, model, ns_map):
        if model.name.prefix in ns_map:
            return etree.QName(ns_map[model.name.prefix], model.name.name)
        elif model.name.prefix is NoModule():
            return model.name.name
        else:
            raise make_exception(pysros_err_prefix_does_not_have_ns, prefix=model.name.prefix, name=model.name.name)

class _MoStorage(_AStorage):
    """Data storage for containers and list entries(list+local keys).

    .. Reviewed by TechComms 20210712
    """

    def __init__(self, model:Model, local_keys):
        self._model = model
        self._local_keys = copy.deepcopy(local_keys)
        self._child = {}
        self._delete = False

    def to_xml(self, ns_map, root):
        try:
            root = etree.SubElement(root, self._resolve_xml_name(self._model, ns_map))
            for k, v in self._local_keys.items():
                etree.SubElement(root, self._resolve_xml_name(self._walker.get_child(k).current, ns_map)).text = self._walker.get_child(k).get_type().to_string(v)
            if self._delete:
                root.attrib["operation"] = "remove"
            for k, v in self._child.items():
                if isinstance(v, (_MoStorage, _ListStorage)):
                    v.to_xml(ns_map, root)
                else:
                    if v is Delete():
                        etree.SubElement(root, self._resolve_xml_name(self._walker.get_child(k).current, ns_map)).attrib["operation"] = "remove"
                    elif v is FieldValuePlaceholder():
                        self._leaf_placeholder_to_xml(v, root, self._walker.get_child(k), ns_map)
                    else:
                        self._leaf_to_xml(v, root, self._walker.get_child(k), ns_map)
        except ValueError as err:
            if not err.args[0].startswith("All strings must be XML compatible"):
                raise
            raise SrosMgmtError(err.args)

    def _leaf_to_xml(self, value, root, walker, ns_map):
        if walker.get_dds() == Model.StatementType.leaf_:
            value = (value, )
        for i in value:
            etree.SubElement(root, self._resolve_xml_name(walker.current, ns_map)).text = walker.get_type().to_string(i)

    def _leaf_placeholder_to_xml(self, value, root, walker, ns_map):
        etree.SubElement(root, self._resolve_xml_name(walker.current, ns_map))

    def to_model(self, *, config_only=False):
        if config_only and self._walker.is_state:
            raise make_exception(pysros_err_no_data_found)
        data = {}
        for k, v in self._child.items():
            if config_only and self._walker.get_child(k).is_state:
                continue
            if not isinstance(v, (_MoStorage, _ListStorage)):
                data[k] = self._leaf_to_model(k, v)
            else:
                data[k] = v.to_model(config_only=config_only)
                if not data[k] and not self._walker.get_child(k).has_explicit_presence():
                    del data[k]
        for k, v in self._local_keys.items():
            data[k] = self._leaf_to_model(k, v)
        return Container._with_module(data, self._model.name.prefix)

    def _leaf_to_model(self, name, value):
        assert value is not FieldValuePlaceholder()
        module = self._walker.get_child_name(name).prefix
        if self._walker.get_child_dds(name) == Model.StatementType.leaf_:
            return Leaf._with_module(value, module)
        return LeafList._with_module(value, module)

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
        if self._delete:
            line += "delete "
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
    def __init__(self, model:Model):
        if model.data_def_stm == Model.StatementType.container_:
            self.__class__ = _MoStorage
            self.__class__.__init__(self, model, {})
        else:
            self._model = model
            self._entries = {}
            self._delete = False

    def to_xml(self, ns_map, root):
        if self._entries:
            for entry in self._entries.values():
                entry.to_xml(ns_map, root)
        else:
            elem = etree.SubElement(root, self._resolve_xml_name(self._model, ns_map))

    def to_model(self, *, config_only=False):
        if config_only and self._walker.is_state:
            raise make_exception(pysros_err_no_data_found)
        d = OrderedDict() if self._model.user_ordered else {}
        for e in self._entries.values():
            d[e.get_keys_flat()] = e.to_model(config_only=config_only)

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
        res = _MoStorage(self._model, keys)
        self._entries[tuple(sorted(keys.items()))] = res
        return res

    def debug_dump(self, indent=0):
        for i in self._entries.values():
            i.debug_dump(indent+1)

class EntryKeysDictProxy():
    """Proxy for dict keys which unwraps keys and compares by performing Identifier.__eq__"""
    def __init__(self, data):
        if not isinstance(data, dict):
            raise make_exception(pysros_err_invalid_value, data=data)
        self.data = data

    def __getitem__(self, key):
        #need to call Identifier.__eq__
        for k in self.data.keys():
            if key == k:
                return self._unwrap(self.data[k])
        raise KeyError(key)

    def __contains__(self, val):
        #need to call Identifier.__eq__
        for ele in self.data:
            if val == ele:
                return True
        return False

    def __str__(self):
        return str(self.data)

    def _unwrap(self, val):
        return val.data if isinstance(val, Wrapper) else val


class _ASetter(ABC):
    """Data setter representation for storage classes.

    .. Reviewed by TechComms 20210712
    """
    def __init__(self, storage:"_ListStorage"):
        self._storage = storage

    @property
    def _walker(self) -> FilteredDataModelWalker:
        return FilteredDataModelWalker(self._storage._model)

    @staticmethod
    def create_setter(storage:"_ListStorage"):
        if isinstance(storage, _MoStorage):
            return _MoDataSetter(storage)
        else:
            return _ListSetter(storage)

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

    def to_model(self, *, config_only=False):
        """Return data in model format.

        .. Reviewed by TechComms 20210712
        """
        return self._storage.to_model(config_only=config_only)

    def delete(self):
        self._storage._delete = True

    def _unwrap(self, value):
        return value.data if isinstance(value, Wrapper) else value


    def _as_storage_type(self, val, *, child_name=None):
        walker = self._walker.get_child(child_name) if child_name else self._walker
        if walker.get_dds() == Model.StatementType.leaf_list_:
            return [walker.get_type().as_storage_type(v) for v in val]
        else:
            return walker.get_type().as_storage_type(val)

class _LeafSetter(_ASetter):
    """Interface for managing leafs. Because leafs do not have dedicated storage, the
       class has its own implementation of to_model method.

    .. Reviewed by TechComms 20210713
    """
    def __init__(self, storage:"_ListStorage", leaf_name:str):
        super().__init__(storage)
        self._leaf_name = leaf_name

    def set(self, value):
        value = self._unwrap(value)
        if not self._walker.check_field_value(value):
            raise make_exception(pysros_err_incorrect_leaf_value, value=value, leaf_name=self._leaf_name)
        else:
            self._set_nocheck(self._as_storage_type(value))

    def _set_nocheck(self, value):
        self._storage._child[self._leaf_name] = value

    def set_placeholder(self):
        self._storage._child[self._leaf_name] = FieldValuePlaceholder()

    def set_as_xml(self, value):
        value = value.text or ""
        self.set(self._walker.as_model_type(value))

    def set_or_append_as_xml(self, value):
        value = self._walker.as_model_type(value.text or "")
        if self._walker.get_dds() == Model.StatementType.leaf_list_ and self._leaf_name in self._storage._child:
            value = self._storage._child[self._leaf_name] + value
        self.set(value)

    def to_model(self, *, config_only=False):
        if config_only and self._walker.is_state:
            raise make_exception(pysros_err_no_data_found)
        return self._storage._leaf_to_model(self._leaf_name, self._storage._child[self._leaf_name])

    def delete(self):
        self._storage._child[self._leaf_name] = Delete()

    @property
    def _walker(self):
        return super()._walker.get_child(self._leaf_name)

class _KeySetter(_ASetter):
    """Interface for keys. Most of this class are stub methods to provide
       setter interface to keys."""
    def __init__(self, storage:"_ListStorage", key_name:str):
        super().__init__(storage)
        self._key_name = key_name

    def set(self, value):
        value = self._unwrap(value)
        if not self._walker.check_field_value(value):
            raise make_exception(pysros_err_incorrect_leaf_value, value=value, leaf_name=self._key_name)
        elif self._as_storage_type(value) != self._storage._local_keys[self._key_name]:
            raise make_exception(pysros_err_key_val_mismatch, key_name=self._key_name)

    def set_placeholder(self):
        pass

    def to_model(self, *, config_only=False):
        if config_only and self._walker.is_state:
            raise make_exception(pysros_err_no_data_found)
        return self._storage._leaf_to_model(self._key_name, self._storage._local_keys[self._key_name])

    def delete(self):
        raise make_exception(pysros_err_invalid_operation_on_key)

    def set_as_xml(self, value):
        value = value.text or ""
        self.set(self._walker.as_model_type(value))

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
        value = self._unwrap(value)
        value = copy.copy(value)
        unwrapper = EntryKeysDictProxy(value)
        if not is_wrapped and self._walker.dict_keys(value):
            for k, v in value.items():
                self.handle_entry_keys_namespaces(v)
                self.entry(self._tuple_to_dict(k)).set(v)
        elif self._walker.entry_keys(unwrapper):
            self.handle_entry_keys_namespaces(value)
            self.entry(value).set(value)
        else:
            raise make_exception(pysros_err_malformed_keys, full_path=self._walker, value=value)

    def _tuple_to_dict(self, t):
        return {k:v for k, v in zip(self._walker.get_local_key_names(), (t if isinstance(t, tuple) else (t, )))}

    def _extract_keys(self, entry):
        return {k:self._as_storage_type(v, child_name=k) for k, v in entry.items() if k in self._walker.get_local_key_names()}

    def _convert_keys_to_model(self, entry):
        try:
            return {k:self._walker.as_child_model_type(k, v) for k, v in entry.items()}
        except:
            raise make_exception(pysros_err_invalid_key_in_path) from None

    def handle_entry_keys_namespaces(self, entry):
        local_keys = [Identifier(self._walker.get_name().prefix, k) for k in self._walker.get_local_key_names()]
        for k in local_keys:
            if k.model_string in entry:
                entry[k.name] = entry.pop(k.model_string)

    def _check_and_unwrap_keys(self, entry):
        for k in self._walker.get_local_key_names():
            if k not in entry:
                raise make_exception(pysros_err_malformed_keys, full_path=self._walker, value=value)
            entry[k] = self._unwrap(entry[k])
            if not self._walker.check_child_field_value(k, entry[k]):
                raise make_exception(pysros_err_incorrect_leaf_value, value=entry[k], leaf_name=k)
            entry[k] = self._walker.get_child_type(k).as_storage_type(entry[k])

    def entry(self, value):
        """Receive entry with specified keys in value. Keys are expected as dict(name->value). Additional
        fields may be present (no verification for extra fields).

        .. Reviewed by TechComms 20210712
        """
        self.handle_entry_keys_namespaces(value)
        self._check_and_unwrap_keys(value)
        return _MoDataSetter(self._storage.get_or_create_entry(self._extract_keys(value)))

    def entry_nocheck(self, value):
        """Receive entry with specified keys in value without checking for the correct type. Keys are expected
        as dict(name->value). Additional fields may be present (no verification for extra fields).

        .. Reviewed by PLM 20211018
        """
        return _MoDataSetter(self._storage.get_or_create_entry(self._convert_keys_to_model(self._extract_keys(value))))

    def entry_xml(self, value):
        keys = {}
        for e in value:
            if _get_tag(e) in self._walker.get_local_key_names():
                keys[_get_tag(e)] = e.text
        if set(keys.keys()) != set(self._walker.get_local_key_names()):
            raise make_exception(pysros_err_schema_box_keys_mismatch, schema_keys=self._walker.get_local_key_names(), box_keys=list(keys.keys()))
        return self.entry_nocheck(keys)

    def set_as_xml(self, value):
        self.entry_xml(value).set_as_xml(value)

    def delete(self):
        raise make_exception(pysros_err_invalid_path_operation_missing_keys)

class _MoDataSetter(_ASetter):
    """Interface managing specific list entry or container.

    .. Reviewed by TechComms 20210712
    """
    class _AChild:
        def __init__(self, setter:"_MoDataSetter"):
            self._setter = setter

        @property
        def _walker(self) -> FilteredDataModelWalker:
            return FilteredDataModelWalker(self._setter._storage._model)

    class _Keys(_AChild):
        """Interface for retrieving and setting keys.

        .. Reviewed by TechComms 20210712
        """
        def set(self, name, value):
            name = Identifier.from_model_string(name).name
            self.get(name).set(value)

        def set_placeholder(self, name):
            self.get(name).set_placeholder()

        def get(self, name):
            if not self.can_contains(name):
                raise make_exception(pysros_err_unknown_child, child_name=name, path=self._walker._get_path())
            return _KeySetter(self._setter._storage, name)

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

        def set_placeholder(self, name):
            self.get(name).set_placeholder()

        def get(self, name):
            if not self.can_contains(name):
                raise make_exception(pysros_err_unknown_child, child_name=name, path=self._walker._get_path())
            return _LeafSetter(self._setter._storage, name)

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

        def get_or_create(self, name):
            if self._walker.get_child_dds(name) in (Model.StatementType.container_, Model.StatementType.list_):
                if not self.is_created(name):
                    self._setter._storage._child[name] = _ListStorage(self._setter._walker.get_child(name).current)
                return _ASetter.create_setter(self._setter._storage._child[name])
            else:
                raise KeyError(name)

        def is_created(self, name):
            return self._walker.get_child_dds(name) in (Model.StatementType.container_, Model.StatementType.list_) and name in self._setter._storage._child


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
        value = self._unwrap(value)
        if not isinstance(value, dict):
            raise make_exception(pysros_err_invalid_value, data=value)
        children_to_set = set()
        for k, v in value.items():
            if k in self._walker.get_local_key_names():
                self.keys.set(k, v)
            elif self._walker.get_child_dds(k) in (Model.StatementType.leaf_, Model.StatementType.leaf_list_):
                self.fields.set(k, v)
            elif self._walker.get_child_dds(k) in (Model.StatementType.container_, Model.StatementType.list_):
                self.child_mos.set(k, v)
            else:
                raise make_exception(pysros_err_unknown_dds, dds=self._walker.get_child_dds(k))
            name = Identifier.from_model_string(k).name
            if name in children_to_set:
                raise make_exception(pysros_err_duplicate_found, duplicate=name)
            children_to_set.add(name)

    def set_as_xml(self, value):
        for e in value:
            if not self._walker.has_child(_get_tag(e)):
                raise make_exception(pysros_err_unknown_child, child_name=_get_tag(e), path=self._walker._get_path())
            else:
                if self._walker.get_child_dds(_get_tag(e)) in (Model.StatementType.leaf_, Model.StatementType.leaf_list_) and _get_tag(e) not in self._walker.get_local_key_names():
                    self.fields.get(_get_tag(e)).set_or_append_as_xml(e)
                elif self._walker.get_child_dds(_get_tag(e)) in (Model.StatementType.list_, Model.StatementType.container_):
                    self.child_mos.get_or_create(_get_tag(e)).set_as_xml(e)


class FieldValuePlaceholder(metaclass=_Singleton):
    pass

class Delete(metaclass=_Singleton):
    pass
