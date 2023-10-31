# Copyright 2021-2023 Nokia

import contextlib
import copy
import json
from enum import Enum, auto
from typing import List, Optional, Union

from .errors import *
from .errors import InvalidPathError, SrosMgmtError, make_exception
from .identifier import Identifier
from .model import Model
from .wrappers import Container, Leaf, LeafList
from .yang_type import *


class Token:
    def __init__(self):
        self.kind: Optional["ModelWalker._TokenKind"] = None
        self.value = ''


class ModelWalker:
    """API representation for walking model tree.

    .. Reviewed by TechComms 20210712
    """
    _expected_dds = (
        Model.StatementType.container_, Model.StatementType.list_,
        Model.StatementType.leaf_, Model.StatementType.leaf_list_,
        Model.StatementType.augment_, Model.StatementType.notification_,
        Model.StatementType.rpc_, Model.StatementType.input_,
        Model.StatementType.output_, Model.StatementType.choice_,
        Model.StatementType.case_, Model.StatementType.action_
    )
    _recursive_visited_dds = (
        Model.StatementType.module_, Model.StatementType.submodule_,
        Model.StatementType.uses_, Model.StatementType.grouping_,
        Model.StatementType.augment_
    )

    def __init__(self, model: Model):
        self.path: List[Model] = []
        self.keys = []
        while model.parent is not None:
            if model.data_def_stm in self._expected_dds:
                self.path.insert(0, model)
                self.keys.insert(0, dict())
            model = model.parent
        self.model = model

    @property
    def current(self):
        return self.path[-1] if len(self.path) > 0 else self.model

    @property
    def local_keys(self):
        return self.keys[-1]

    @property
    def is_root(self):
        return not self.path

    @property
    def is_state(self):
        return not self.current.config

    def go_to_parent(self):
        if not self.path:
            raise make_exception(pysros_err_cannot_call_go_to_parent)

        self.path.pop()
        self.keys.pop()

    def go_to_child(self, child_name: Union[str, Identifier]):
        child = self._get_child(child_name)
        self.path.append(child)
        self.keys.append(dict())
        return child

    def go_to(self, path: ModelPath, module: Optional[str] = None):
        for p in path._path:
            if not p.is_lazy_bound():
                try:
                    self.go_to_child(p)
                except SrosMgmtError as e:
                    raise InvalidPathError(*e.args) from None
                continue

            if p.name == '..':
                self.go_to_parent()
                continue

            prefix = self.path[-1].name.prefix if self.path else module
            assert prefix

            try:
                self.go_to_child(
                    Identifier(prefix, p.name))
            except SrosMgmtError as e:
                raise InvalidPathError(*e.args) from None

    def check_child_field_value(self, name: Union[str, Identifier], value, *, json=False):
        with self.visit_child(name):
            return self.check_field_value(value, json=json)

    def check_field_value(self, value, *, json=False):
        if self.get_dds() == Model.StatementType.leaf_list_:
            if not isinstance(value, list):
                raise make_exception(pysros_err_leaflist_should_be_list, type_name=value.__class__.__name__)
            return all(self.get_type().check_field_value(i, json) for i in value)
        elif self.get_dds() == Model.StatementType.leaf_:
            return self.get_type().check_field_value(value, json)
        else:
            assert False, "Checking field value for non-field walker"

    def get_parent(self):
        res = self.__class__(self.model)
        if self.path:
            res.path = self.path[:-1]
            res.keys = self.keys[:-1]
        return res

    def get_child(self, child_name: Union[str, Identifier]):
        res = self.copy()
        res.path.append(self._get_child(child_name))
        res.keys.append(dict())
        return res

    def copy(self):
        res = self.__class__(self.model)
        res.path = self.path[:]
        res.keys = copy.deepcopy(self.keys)
        return res

    def go_to_last_with_presence(self):
        while self.path and not self.has_explicit_presence():
            self.go_to_parent()

    def has_explicit_presence(self):
        types_with_presence = (
            Model.StatementType.leaf_, Model.StatementType.leaf_list_
        )
        return (
            self.get_dds() in types_with_presence
            or self.get_dds() == Model.StatementType.list_ and not self.has_missing_keys()
            or self.get_dds() == Model.StatementType.container_ and self.current.presence_container)

    def has_missing_keys(self):
        return (
            self.get_dds() == Model.StatementType.list_ and
            len(self.keys[-1]) != len(self.current.local_keys)
        )

    def dict_keys(self, value):
        for i in value.keys():
            if not isinstance(i, tuple):
                i = (i,)
            if (len(self.get_local_key_names()) != len(i)):
                return False
            if not all(self.check_child_field_value(key_name, key_val) for key_name, key_val in zip(self.get_local_key_names(), i)):
                return False
        return all(isinstance(v, (dict, Container)) for v in value.values())

    def entry_keys(self, value):
        def correct_key(entry, key):
            if key in entry and self.check_child_field_value(key, entry[key]):
                return True
            return False

        local_keys = [Identifier(self.get_name().prefix, k) for k in self.get_local_key_names()]
        return all(correct_key(value, k) for k in local_keys)

    def as_model_type(self, s):
        assert self.get_dds() in (Model.StatementType.leaf_, Model.StatementType.leaf_list_)
        if isinstance(s, list):
            res = [self.get_type().to_value(p) for p in s]
        else:
            res = [self.get_type().to_value(s)]

        if self.get_dds() == Model.StatementType.leaf_:
            res = res[0]
        return res

    def dump_json(self):
        def _dump_json(self, parent_data):
            if self.get_dds() in self._expected_dds:
                data = {"name": self.get_name().name,
                        "dds":  self.get_dds().name}
                if self.get_dds() != Model.StatementType.leaf_:
                    data["children"] = []
                if self.get_dds() == Model.StatementType.leaf_:
                    data["type"] = self.get_type().json_name()
                parent_data["children"].append(data)
                parent_data = data

            children = list(self.current.children)
            while children:
                child = children.pop()
                if child.data_def_stm in (Model.StatementType.module_, Model.StatementType.submodule_):
                    children.extend(child.children)
                    continue
                if child.data_def_stm in (Model.StatementType.container_, Model.StatementType.list_, Model.StatementType.leaf_, Model.StatementType.leaf_list_, Model.StatementType.choice_, Model.StatementType.case_, ):
                    with self.visit_child(child.name.name):
                        _dump_json(self, parent_data)
        root_data = {"children": []}
        _dump_json(self, root_data)
        return json.dumps(root_data, indent=4)

    def as_child_model_type(self, child, s):
        with self.visit_child(child):
            return self.as_model_type(s)

    @contextlib.contextmanager
    def visit_child(self, child: Union[str, Identifier]):
        self.go_to_child(child)
        try:
            yield
        finally:
            self.go_to_parent()

    def get_child_type(self, child_name: Union[str, Identifier]):
        return self._get_child(child_name).yang_type

    def get_child_dds(self, child_name: Union[str, Identifier]):
        return self._get_child(child_name).data_def_stm

    def get_child_name(self, child_name: Union[str, Identifier]):
        return self._get_child(child_name).name

    def get_type(self):
        return self.current.yang_type

    def get_dds(self):
        return self.current.data_def_stm

    def get_name(self):
        return self.current.name

    def get_local_key_names(self):
        return self.current.local_keys

    def has_local_keys_specified(self):
        return len(self.get_local_key_names()) == len(self.local_keys)

    def has_local_key_named(self, name):
        return name in self.get_local_key_names()

    def has_field_named(self, name):
        return (
            self.has_child(name) and
            self.get_child_dds(name) in (
                Model.StatementType.leaf_, Model.StatementType.leaf_list_
            )
        )

    @property
    def is_leaflist(self):
        return self.get_dds() == Model.StatementType.leaf_list_

    @property
    def is_local_key(self):
        return self.get_name().name in self.get_parent().get_local_key_names()

    def has_child(self, child_name: Union[str, Identifier] = None):
        if child_name:
            try:
                self._get_child(child_name)
            except:
                return False
            else:
                return True
        else:
            return self.current.has_children

    def validate_get_filter(self, filter: Union[dict, Container]):
        if filter == Container({}):
            filter = {}
        if self.get_dds() in (Model.StatementType.list_, Model.StatementType.container_):
            if isinstance(filter, Container):
                filter = filter.data
            if not isinstance(filter, dict):
                raise make_exception(pysros_err_filter_should_be_dict)
            unwrap = lambda v: v.data if isinstance(v, Leaf) else v
            if any(unwrap(v) == '' for v in filter.values()):
                raise make_exception(pysros_err_filter_empty_string)
            for k, v in filter.items():
                with self.visit_child(k):
                    self.validate_get_filter(v)
        elif self.get_dds() in (Model.StatementType.leaf_, Model.StatementType.leaf_list_):
            if isinstance(filter, Leaf) and self.get_dds() == Model.StatementType.leaf_:
                filter = filter.data
            if isinstance(filter, LeafList) and self.get_dds() == Model.StatementType.leaf_list_:
                filter = filter.data
            if isinstance(filter, dict):
                if filter:
                    raise make_exception(pysros_err_filter_wrong_leaf_value, leaf_name=self.get_name().name)
            elif isinstance(filter, str):
                pass
            elif not self.check_field_value(filter):
                raise make_exception(
                    pysros_err_incorrect_leaf_value,
                    leaf_name=self.get_name().name
                )

    class _TokenKind(Enum):
        string = auto()
        symbol = auto()

    @classmethod
    def _tokenize(cls, string):
        for i in cls._tokenize_(string):
            yield i

    @classmethod
    def _tokenize_(cls, string):
        res = []
        iterator = iter(string)
        while True:
            try:
                i = next(iterator)
            except StopIteration:
                if res:
                    yield (cls._TokenKind.string, "".join(res))
                return
            if i in "[]=/":
                if res:
                    yield (cls._TokenKind.string, "".join(res))
                    res = []
                yield (cls._TokenKind.symbol, i)
                continue
            if res:
                res.append(i)
                continue
            if i == '"':
                while True:
                    try:
                        i = next(iterator)
                        if i == '"':
                            break
                        res.append(i)
                    except StopIteration:
                        raise make_exception(pysros_err_unended_quoted_string)
                yield (cls._TokenKind.string, "".join(res))
                res = []
                continue

            if i == "'":
                while True:
                    try:
                        i = next(iterator)
                        if i == "'":
                            break
                        res.append(i)
                    except StopIteration:
                        raise make_exception(pysros_err_unended_quoted_string)
                yield (cls._TokenKind.string, "".join(res))
                res = []
                continue
            res.append(i)

    @classmethod
    def user_path_parse(cls, *args, accept_root=False, **kwargs):
        res = cls.path_parse(*args, **kwargs)
        assert isinstance(res, ModelWalker)
        if not accept_root and res.is_root:
            raise make_exception(pysros_err_root_path)
        for elem in res.path:
            if elem.is_region_blocked:
                raise make_exception(
                    pysros_err_unknown_element, element=elem.name.name
                )
        return res

    @classmethod
    def path_parse(cls, model_root, path_string):
        if not isinstance(path_string, str):
            raise make_exception(pysros_err_path_should_be_string)

        if path_string == "/":
            return cls(model_root)

        if not path_string.startswith('/'):
            if not path_string:
                raise make_exception(pysros_err_empty_path)
            raise make_exception(pysros_err_not_found_slash_before_name)
        if path_string.endswith('/'):
            raise make_exception(pysros_err_invalid_identifier)

        iterator = iter(cls._tokenize(path_string))

        def next_token(*accepts, err,  **kwarg):
            """Verify a next token from path and return tuple(kind, token) if no errors.
                Otherwise, raise make_exception(err, **kwarg).

:param accepts: Contains a list of the following:
    - one of '/', '[', ']' or '=' - Function accepts specified symbol.
    - 'string' - Function accepts a string, not a symbol.
    - None - Function accepts end of string.

            .. Reviewed by TechComms 20210713
            """
            n = next(iterator, None)

            if n is None:
                if None in accepts:
                    return None, None
            elif n[0] == cls._TokenKind.symbol:
                if n[1] in accepts:
                    return n
            elif 'string' in accepts:
                return n
            raise make_exception(err, **kwarg)

        res = cls(model_root)
        missing_keys = set()
        elem = 'root'

        while True:
            _, i = next_token('/', '[', None, err=pysros_err_not_found_slash_before_name)
            if i == None:
                if (
                    missing_keys
                    and len(missing_keys) != len(res.current.local_keys)
                ):
                    raise make_exception(pysros_err_missing_keys, element=elem)
                break
            if i == "/":
                if missing_keys:
                    raise make_exception(pysros_err_missing_keys, element=elem)
                _, elem = next_token('string', None, err=pysros_err_invalid_identifier)
                try:
                    res.go_to_child(elem)
                    missing_keys.update(res.current.local_keys)
                except Exception:
                    raise make_exception(
                        pysros_err_unknown_element,
                        element=elem) from None
                continue
            if i == "[":
                _, key_name = next_token(
                    'string', err=pysros_err_invalid_identifier
                )
                next_token('=', err=pysros_err_expected_equal_operator)
                _, value = next_token(
                    'string', err=pysros_err_invalid_identifier
                )
                next_token(']', err=pysros_err_expected_end_bracket)
                if key_name not in missing_keys:
                    try:
                        res._get_child(key_name)
                    except Exception:
                        raise make_exception(
                            pysros_err_unknown_key, key_name=key_name
                        )
                    raise make_exception(
                        pysros_err_cannot_specify_non_key_leaf
                    )
                missing_keys.remove(key_name)
                res.local_keys[key_name] = value
        return res

    @classmethod
    def tokenize_path(cls, path: str, absolute_schema_id: bool):
        # absolute schema id has form: absolute-schema-nodeid = 1*("/" node-identifier)
        # leaf-ref form allows also predicates and a ".." inside paths
        if not path.startswith(('/', '../')):
            raise make_exception(pysros_err_invalid_yang_path, path=path)

        _end = None, ''
        t = Token()

        iterator = iter(cls._tokenize_(path))

        def next_token(t):
            t.kind, t.value = next(iterator, _end)
        next_token(t)
        if t.value == '/':
            # skip '/' in absolute path
            next_token(t)

        while True:
            if t.kind != cls._TokenKind.string:
                raise make_exception(pysros_err_invalid_yang_path, path=path)
            yield t.value
            next_token(t)

            while t.value == '[' and not absolute_schema_id:
                while t.value not in ('', ']'):
                    next_token(t)
                    if t.kind is None:
                        return
                next_token(t)

            if t.value == '/':
                next_token(t)
                continue

            if t.kind is None:
                return

            raise make_exception(pysros_err_invalid_yang_path, path=path)

    def __str__(self):
        return "/" + "/".join(str(name.name) + "".join(f"[{key}={value}]" for key, value in keys.items()) for name, keys in zip(self.path, self.keys))

    def _get_child(self, child_name: Union[str, Identifier]):
        children = list(self.current.children)
        while children:
            child = children.pop()
            if child.name == child_name and child.data_def_stm in self._expected_dds and self._is_allowed(child):
                return child
            if child.data_def_stm in self._recursive_visited_dds:
                children.extend(child.children)
        raise make_exception(
            pysros_err_unknown_child,
            child_name=child_name,
            path=self._get_path()
        )

    def recursive_walk(self, *, enter_fnc=None, leave_fnc=None):
        children = list(self.current.children)
        while children:
            child = children.pop()
            if child.data_def_stm in self._expected_dds and self._is_allowed(child):
                self.path.append(child)
                self.keys.append(dict())
                enter_fnc and enter_fnc(self)
                self.recursive_walk(enter_fnc=enter_fnc, leave_fnc=leave_fnc)
                leave_fnc and leave_fnc(self)
                self.path.pop()
                self.keys.pop()
            if child.data_def_stm in self._recursive_visited_dds:
                children.extend(child.children)

    def _get_path(self):
        return " ".join(str(model.name) for model in self.path)

    def _is_allowed(self, model):
        return True

    def is_region_blocked_in_child(self, child_name: Union[str, Identifier]):
        return self._get_child(child_name).is_region_blocked


class DataModelWalker(ModelWalker):
    _expected_dds = (
        Model.StatementType.container_, Model.StatementType.list_,
        Model.StatementType.leaf_, Model.StatementType.leaf_list_,
        Model.StatementType.action_, Model.StatementType.input_,
        Model.StatementType.output_
    )
    _recursive_visited_dds = (
        Model.StatementType.module_, Model.StatementType.submodule_,
        Model.StatementType.uses_, Model.StatementType.augment_,
        Model.StatementType.choice_, Model.StatementType.case_
    )


class FilteredDataModelWalker(DataModelWalker):
    _expected_dds = (
        Model.StatementType.container_, Model.StatementType.list_,
        Model.StatementType.leaf_, Model.StatementType.leaf_list_
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_only = False
        self.return_blocked_regions = False

    def _is_allowed(self, model):
        if self.config_only and not model.config:
            return False
        if not self.return_blocked_regions and model.is_region_blocked:
            return False
        return any(i in model.name.prefix for i in ("nokia", "openconfig"))


class ActionInputFilteredDataModelWalker(FilteredDataModelWalker):
    _expected_dds = (
        Model.StatementType.container_, Model.StatementType.list_,
        Model.StatementType.leaf_, Model.StatementType.leaf_list_,
        Model.StatementType.action_
    )
    _recursive_visited_dds = (
        Model.StatementType.module_, Model.StatementType.submodule_,
        Model.StatementType.uses_, Model.StatementType.augment_,
        Model.StatementType.choice_, Model.StatementType.case_,
        Model.StatementType.input_
    )


class ActionOutputFilteredDataModelWalker(FilteredDataModelWalker):
    _expected_dds = (
        Model.StatementType.container_, Model.StatementType.list_,
        Model.StatementType.leaf_, Model.StatementType.leaf_list_,
        Model.StatementType.action_
    )
    _recursive_visited_dds = (
        Model.StatementType.module_, Model.StatementType.submodule_,
        Model.StatementType.uses_, Model.StatementType.augment_,
        Model.StatementType.choice_, Model.StatementType.case_,
        Model.StatementType.output_
    )
