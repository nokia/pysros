# Copyright 2021 Nokia

import operator

from abc import ABC, abstractmethod

from .errors import *

__all__ = ("Container", "Leaf", "LeafList")

__doc__ = """This module contains wrappers describing the YANG structure and metadata obtained from SR OS.

.. Reviewed by PLM 20210630
"""

class Schema:
    """Metadata about the YANG schema associated with elements in the data structure.

    .. note:: :py:class:`pysros.wrappers.Schema` metadata is read-only.

    :ivar module: YANG module name from which this node originates

    .. Reviewed by PLM 20210630
    .. Reviewed by TechComms 20210712
    """
    __slots__ = ("_module",)

    def __init__(self, module):
        self._module = module

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._module == other._module

    @property
    def module(self):
        """YANG module name from which this node originates.

        .. TODO: Consider removing this property from the documentation as its mentioned as an ivar above - PLM

        .. Reviewed by PLM 20210630
        .. Reviewed by TechComms 20210712
        """
        return self._module

class Wrapper(ABC):
    """Common functionality to support wrappers that describe the YANG structure from
    the SR OS schema.

    .. warning::
       Instance of this class SHOULD NOT be created by user of pysros library.

    .. Reviewed by TechComms 20210712   
    """

    __slots__ = ('_data', '_module')

    def __init__(self, value):
        self.data    = value
        self._module = None

    def __getattr__(self, attr):
        return getattr(self._data, attr)

    def __setattr__(self, attr, value):
        if attr == "data" or attr == "schema" or attr in Wrapper.__slots__:
            object.__setattr__(self, attr, value)
        else:
            setattr(self._data, attr, value)

    def __delattr__(self, attr):
        raise make_exception(pysros_err_attr_cannot_be_deleted, obj=self.__class__.__name__, attribute=attr)

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._data == other._data

    def __bool__(self):
        return bool(self._data)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._check_data_type(value)
        self._data = value

    @property
    def schema(self):
        return Schema(self._module) if self._module else None

    @schema.setter
    def schema(self, _):
        raise make_exception(pysros_err_attr_is_read_only, obj=self.__class__.__name__, attribute = 'schema')

    @staticmethod
    @abstractmethod
    def _check_data_type(value):
        pass

    def __str__(self):
        return str(self._data)

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    # helper used in followed loop and deleted
    def _unwrap_first(op):
        return lambda w1, w2: op(w1._data, w2)

    for op in ('__add__', '__sub__', '__mul__', '__truediv__', '__floordiv__'
                , '__mod__', '__pow__', '__lshift__', '__rshift__'
                , '__and__', '__xor__', '__or__'):
        locals()[op] = _unwrap_first(getattr(operator, op))

    # helper used in followed loop and deleted
    def _runwrap_first(op):
        return lambda w1, w2: op(w2, w1._data)

    for rop in ('__radd__', '__rsub__', '__rmul__', '__rtruediv__', '__rfloordiv__'
                , '__rmod__', '__rpow__', '__rlshift__', '__rrshift__'
                , '__rand__', '__rxor__', '__ror__'):
        assert rop.startswith('__r')
        op = '__' + rop[3:]
        locals()[rop] = _runwrap_first(getattr(operator, op))


    # helper used in followed loop and deleted
    def _unwrap_both(op):
        def fn(self, other):
            if self.__class__ is not other.__class__:
                return NotImplemented
            return op(self._data, other._data)
        return fn

    for op in ('__lt__', '__le__', '__gt__', '__ge__'):
        locals()[op] = _unwrap_both(getattr(operator, op))

    del _unwrap_first
    del _runwrap_first
    del _unwrap_both
    del op
    del rop

    @classmethod
    def _with_module(cls, data, module):
        if module and not isinstance(module, str):
            raise make_exception(pysros_err_arg_must_be_string)
        obj = cls(data)
        obj._module = module
        return obj

class Container(Wrapper):
    """YANG container data structure node wrapper.

    A YANG container in the pySROS data structure behaves in the same way as a Python dict,
    where the value of a field can be obtained using the field name.

    :ivar data: dictionary containing the fields data

    .. Reviewed by PLM 20210630
    .. Reviewed by TechComms 20210712
    """
    __slots__ = ()
    def __init__(self, value = None):
        super().__init__(value if value is not None else {})

    @staticmethod
    def _check_data_type(value):
        if not isinstance(value, dict):
            raise make_exception(pysros_err_type_must_be, expected="dict", actual=value.__class__.__name__)

class LeafList(Wrapper):
    """YANG leaf-list data structure node wrapper.

    A YANG leaf-list in the pySROS data structure behaves in the same way as a Python list, where the separate
    values can be obtained using an index.

    :ivar data: list containing the values

    .. Reviewed by PLM 20210630
    .. Reviewed by TechComms 20210712
    """
    __slots__ = ()

    def __init__(self, value = None):
        super().__init__(value if value is not None else [])

    @staticmethod
    def _check_data_type(values):
        if not isinstance(values, list):
            raise make_exception(pysros_err_type_must_be, expected="list", actual=values.__class__.__name__)
        for value in values:
            Leaf._check_data_type(value)

class Leaf(Wrapper):
    """YANG leaf data structure node wrapper.

    Depending on the base (root) YANG type of the node, this object wraps a str, int, or bool.

    :ivar data: python object corresponding to the value

    .. Reviewed by PLM 20210630
    .. Reviewed by TechComms 20210713
    """
    __slots__ = ()

    @staticmethod
    def _check_data_type(data):
        if not isinstance(data, (str, int, bool, _Empty)):
            raise make_exception(pysros_err_unsupported_type_for_leaf)


class _Singleton(type):
    _instances = {}
    def __new__(cls, *args, **kwargs):
        res = super(_Singleton, cls).__new__(cls, *args, **kwargs)
        res.__copy__     = lambda self: self
        res.__deepcopy__ = lambda self, memo: self
        res.__reduce__   = lambda self: (self.__class__, ())
        return res

    def __call__(cls, *args, **kwargs):
        assert args == () and kwargs == {}
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class _Empty(metaclass=_Singleton):
    """Representation of whether empty leaf is present.
    
    .. Reviewed by TechComms 20210712
    """
    def __str__(self):
        return "Empty"

    def __repr__(self):
        return "Empty"

Empty = _Empty()
Empty.__doc__="""Define the YANG Empty type."""
