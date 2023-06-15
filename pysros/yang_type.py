# Copyright 2021-2023 Nokia

import base64

from abc import ABC, abstractmethod
from collections import OrderedDict
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Set, Type, Tuple, Union

from lxml.etree import SubElement

from .errors import *
from .identifier import Identifier, NoModule
from .model_path import ModelPath
from .singleton import Empty


INTEGRAL_LEAF_TYPE      = ("int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64")
DECIMAL_LEAF_TYPE       = INTEGRAL_LEAF_TYPE + ("decimal64",)
YANG_PRIMITIVE_TYPES    = INTEGRAL_LEAF_TYPE + ("binary", "boolean", "decimal64", "empty", "string", "instance-identifier")

INTEGRAL_TYPES_MIN = {
    'uint8':    "0",
    'uint16':   "0",
    'uint32':   "0",
    'uint64':   "0",
    'int8':     str(-(2**7)),
    'int16':    str(-(2**15)),
    'int32':    str(-(2**31)),
    'int64':    str(-(2**63)+1),
}

INTEGRAL_TYPES_MAX = {
    'int8':     str((2**7)-1),
    'uint8':    str((2**8)-1),
    'int16':    str((2**15)-1),
    'uint16':   str((2**16)-1),
    'int32':    str((2**31)-1),
    'uint32':   str((2**32)-1),
    'int64':    str((2**63)-1),
    'uint64':   str((2**64)-1),
}

assert set(INTEGRAL_LEAF_TYPE) == set(INTEGRAL_TYPES_MIN.keys()) == set(INTEGRAL_TYPES_MAX.keys())

IP_TYPES = {
    Identifier('ietf-inet-types',       'ip-address'),
    Identifier('ietf-inet-types',       'ip-address-no-zone'),
    Identifier('ietf-inet-types',       'ip-prefix'),
    Identifier('nokia-types-sros',      'ip-address'),
    Identifier('nokia-types-sros',      'ip-address-with-zone'),
    Identifier('nokia-types-sros',      'ip-prefix'),
    Identifier('nokia-types-sros',      'ip-prefix-with-host-bits'),
    Identifier('nokia-types-sros',      'ip-multicast-address'),
    Identifier('nokia-types-sros',      'ip-multicast-prefix'),
    Identifier('nokia-types-sros',      'ip-unicast-address'),
    Identifier('nokia-types-sros',      'ip-unicast-address-with-zone'),
    Identifier('nokia-types-sros',      'ip-unicast-without-local-address'),
    Identifier('nokia-types-sros',      'ip-unicast-or-linklocal-without-site-or-unique-local-address'),
    Identifier('nokia-types-sros',      'ip-unicast-prefix'),
    Identifier('openconfig-inet-types', 'ip-address'),
    Identifier('openconfig-inet-types', 'ip-prefix'),
}

class YangTypeBase(ABC):
    """Abstract interface for all leaf types.

    .. Reviewed by TechComms 20210713
    """
    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def __repr__(self):
        pass

    @abstractmethod
    def __hash__(self):
        pass

    @abstractmethod
    def __eq__(self, other):
        if other is None:
            return False
        assert isinstance(other, YangTypeBase)
        return self.__class__ is other.__class__

    @property
    def name(self):
        return self.__str__()

    def to_string(self, val: Any) -> str:
        """Translate value to xml text without any checking."""
        # User input is also checked by check_field_value, paths are not
        if isinstance(val, bool) and isinstance(self, PrimitiveType):
            if self.identifier.name == 'boolean':
                return str(val).lower()
            assert self.identifier.name in INTEGRAL_LEAF_TYPE
            return str(int(val))
        if isinstance(val, (int, str)):
            return str(val)
        if val is Empty:
            return ''
        if isinstance(val, bytes):
            return base64.b64encode(val).decode('utf8')
        raise make_exception(pysros_err_unexpected_value_of_type, val_type=type(val), type=str(self))

    def to_value(self, val: str) -> Any:
        """Transform string to native Python type.
            If the value does not fit the expected type, a TypeError exception is raised. This exception is tested
            in union."""
        raise make_exception(pysros_err_invalid_value_for_type, type=self, value=val)

    @abstractmethod
    def check_field_value(self, value: Any, json=False) -> bool:
        """Check whether value is acceptable for a specific yang_type."""
        return False

    def json_name(self) -> str:
        return self.__class__.__name__.lower()

    def as_storage_type(self, obj, is_convert):
        return obj


def _is_valid_decimal64(value: str) -> bool:
    return isinstance(value, str)

def _is_valid_base64(value: Any) -> bool:
    return isinstance(value, (bytes, str))

class PrimitiveType(YangTypeBase):
    """Primitive built-in types representation, such as int8, str, and binary. All types are in YANG_PRIMITIVE_TYPES.

    .. Reviewed by TechComms 20210713
    """
    def __init__(self, name: str, yang_range: Optional[str] = None, fraction_digits: Optional[int] = None, length: Optional[str] = None):
        assert name in YANG_PRIMITIVE_TYPES
        self.identifier         = Identifier.builtin(name)
        self.yang_range         = yang_range
        self.fraction_digits    = fraction_digits
        self.length             = length

    def __str__(self):
        return str(self.identifier)

    def __repr__(self):
        if self.yang_range:
            repr_str = f"(name={self.identifier.name!r}, yang_range={self.yang_range!r})"
        else:
            repr_str = f"({self.identifier.name!r})"
        return self.__class__.__name__ + repr_str

    def __eq__(self, other):
        if not YangTypeBase.__eq__(self, other):
            return False
        return all((
            self.identifier         == other.identifier,
            self.yang_range         == other.yang_range,
            self.fraction_digits    == other.fraction_digits,
        ))

    def __hash__(self):
        return hash((
            self.identifier,
            self.yang_range,
            self.fraction_digits,
        ))

    def to_value(self, val: str) -> Any:
        t = self.identifier.name
        if t in INTEGRAL_LEAF_TYPE:
            return int(val)
        if t == "boolean":
            if isinstance(val, str) and val.lower() in ("true", "false"):
                return val.lower() == "true"
            elif isinstance(val, bool): #TODO is this really good place for this?
                return val
        if t == "empty":
            return Empty
        if t in ("string", "binary"):
            return val
        if t == "decimal64":
            return val
        return super().to_value(val)

    _check_field_value = {
        "string":   lambda val: type(val) == str,
        "empty":    lambda val:  val is Empty,
        "boolean":  lambda val:  isinstance(val, bool),
        "decimal64": _is_valid_decimal64,
        "binary": _is_valid_base64
    }

    def check_field_value(self, value: Any, json=False) -> bool:
        name = self.identifier.name
        cmp = self._check_field_value.get(name, None)
        if cmp is not None:
            return cmp(value)

        if json and name in ("int64", "uint64"):
            return isinstance(name, str)
        elif name in INTEGRAL_LEAF_TYPE:
            return isinstance(value, int) and not isinstance(value, bool)
        return False

    def json_name(self) -> str:
        return self.identifier.name

    def as_storage_type(self, obj, is_convert):
        if self.identifier.name == "boolean" and type(obj) == int:
            return bool(obj)
        elif self.identifier.name in INTEGRAL_LEAF_TYPE and (type(obj) == bool or self.identifier.name in ("int64", "uint64")):
            return int(obj)
        return super().as_storage_type(obj, is_convert)

class UnresolvedIdentifier(YangTypeBase):
    """Identifier that has not been resolved yet."""
    def __init__(self, identifier: Identifier, yang_range: Optional[str] = None, fraction_digits: Optional[int] = None, length: Optional[str] = None):
        self.identifier         = identifier
        self.yang_range         = yang_range
        self.fraction_digits    = fraction_digits
        self.length             = length
        assert not self.identifier.is_builtin()

    def __str__(self):
        return str(self.identifier)

    def __repr__(self):
        if self.yang_range:
            repr_str = f"(identifier={self.identifier!r}, yang_range={self.yang_range!r})"
        else:
            repr_str = f"({self.identifier!r})"
        return self.__class__.__name__ + repr_str

    def __eq__(self, other):
        if not YangTypeBase.__eq__(self, other):
            return False
        return all((
            self.identifier         == other.identifier,
            self.yang_range         == other.yang_range,
            self.fraction_digits    == other.fraction_digits,
        ))

    def __hash__(self):
        return hash((
            self.identifier,
            self.yang_range,
            self.fraction_digits,
        ))

    def to_string(self, _val: Any) -> str:
        raise make_exception(pysros_err_unresolved_type, type=self)

    def to_value(self, _val: str) -> Any:
        raise make_exception(pysros_err_unresolved_type, type=self)

    def check_field_value(self, value: Any, json=False) -> bool:
        return False

class YangUnion(YangTypeBase):
    def __init__(self, types: List["YangType"] = []):
        super().__init__()

        self._types: List["YangType"] = types.copy() if isinstance(types, list) else list(types)
        self.deduplicate()

    def __iter__(self):
        return self._types.__iter__()

    def __getitem__(self, *args):
        return self._types.__getitem__(*args)

    def append(self, t: "YangType"):
        self._types.append(t)

    def __str__(self):
        return f"union[{','.join(map(str, self._types))}]"

    def __repr__(self):
        return f"{self.__class__.__name__}(({', '.join(map(repr, self._types))}))"

    def __hash__(self):
        return hash(tuple(self._types))

    def __eq__(self, other):
        return (
            YangTypeBase.__eq__(self, other)
            and self._types == other._types
        )

    def __len__(self):
        return len(self._types)

    def to_string(self, val: Any) -> str:
        if isinstance(val, str):
            return val
        if isinstance(val, bool):
            return "true" if val else "false"
        return super().to_string(val)

    def to_value(self, val: Any) -> Any:
        return val

    def check_field_value(self, value: Any, json=False) -> bool:
        if isinstance(value, str):
            return True
        return any(t.check_field_value(value, json) for t in self._types)

    def json_name(self) -> str:
        return "union"

    def deduplicate(self):
        types = list(OrderedDict.fromkeys(self._types))
        if len(types) != len(self._types):
            self._types = types

class Enumeration(OrderedDict, YangTypeBase):
    def __str__(self):
        return f"enumeration[{'|'.join(map(str, self.keys()))}]"

    def __hash__(self):
        return hash(tuple(self))

    def add_enum(self, name: str):
        val = 1+max(self.values()) if self else 0
        self[name] = val

    def set_last_enum_value(self, val: int):
        assert self
        last_used_key = next(reversed(self))
        self[last_used_key] = val

    def to_value(self, val: str) -> Any:
        return str(val)

    def check_field_value(self, value: Any, json=False) -> bool:
        return isinstance(value, str)


class Bits(set, YangTypeBase):
    def __str__(self):
        return f"bits[{' '.join(sorted(self))}]"

    def __repr__(self):
        return f"Bits(({', '.join(map(repr, sorted(self)))}))"

    def __hash__(self):
        return hash(frozenset(self))

    def __eq__(self, other):
        return YangTypeBase.__eq__(self, other) and frozenset(self) == frozenset(other)

    def is_valid_value(self, val: Any) -> bool:
        return isinstance(val, str)

    def to_value(self, val: str) -> Any:
        if self.is_valid_value(val):
            return val
        return super().to_value(val)

    def check_field_value(self, value: Any, json=False) -> bool:
        return self.is_valid_value(value)

class LeafRef(YangTypeBase):
    def __init__(self, path = None):
        if path is None or isinstance(path, ModelPath):
            self._path: Optional[ModelPath] = path
            return
        assert isinstance(path, tuple) and all(isinstance(p, Identifier) for p in path)
        self._path = ModelPath(path)


    def set_path(self, path: ModelPath):
        assert isinstance(path, ModelPath)
        self._path = path

    def __eq__(self, other):
        return YangTypeBase.__eq__(self, other) and self._path == other._path

    def __ne__(self, other):
        return not(self == other)

    def __str__(self):
        return f"leafref({self._path!s})"

    def __repr__(self):
        return f"LeafRef({self._path.repr_path()})"

    def __hash__(self):
        return hash((self.__class__.__name__, self._path))

    def to_string(self, _val: Any) -> str:
        raise make_exception(pysros_err_unresolved_leafref, type=str(self))

    def to_value(self, _val: str) -> Any:
        raise make_exception(pysros_err_unresolved_leafref, type=str(self))

    def check_field_value(self, value: Any, json=False) -> bool:
        return False

    @property
    def path(self):
        return self._path

class IdentityRef(YangTypeBase):
    def __init__(self, bases = (), values: Optional[Set[Identifier]] = None):
        self.bases:  List[Identifier] = list(bases)
        self.values: Set[Identifier] = values or set()

    def add_base(self, base: Identifier):
        assert isinstance(base, Identifier)
        self.bases.append(base)

    def set_values(self, derived: Mapping[Identifier, Set[Identifier]]):
        assert not self.values
        self.values = set()
        for b in self.bases:
            if b not in derived:
                continue
            self.values |= derived[b]

    def __eq__(self, other):
        return (
            YangTypeBase.__eq__(self, other)
            and self.bases == other.bases
            and self.values == other.values
        )

    def __str__(self):
        return f"identityref[{', '.join(b.__str__() for b in self.bases)}]"

    def __repr__(self):
        return f"IdentityRef({self.bases!r}, set(({', '.join(sorted(map(repr, self.values)))})))"

    def __hash__(self):
        return hash((self.__class__.__name__, *self.bases, frozenset(self.values)))

    def to_value(self, _val: str) -> Any:
        return _val

    def as_storage_type(self, obj, is_convert):
        return obj

    def check_field_value(self, value: Any, json=False) -> bool:
        return isinstance(value, str)


YangType = Union[
    PrimitiveType,
    UnresolvedIdentifier,
    Enumeration,
    Bits,
    YangUnion,
    LeafRef,
    IdentityRef]


_KNOWN_TYPES = {
        "leafref":     LeafRef,
        "bits":        Bits,
        "enumeration": Enumeration,
        "union":       YangUnion,
        "identityref": IdentityRef,
    }

def should_be_buildin(name):
    return name in _KNOWN_TYPES or name in YANG_PRIMITIVE_TYPES

def type_from_name(identifier: Identifier):
    if identifier.is_builtin():
        t = _KNOWN_TYPES.get(identifier.name)
        if t is not None:
            return t()
        return PrimitiveType(identifier.name)
    return UnresolvedIdentifier(identifier)
