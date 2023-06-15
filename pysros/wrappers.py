# Copyright 2021-2023 Nokia

import operator

from abc import ABC, abstractmethod

from .errors import *
from .singleton import _Empty
from .yang_type import YangUnion, DECIMAL_LEAF_TYPE

__all__ = ("Action", "Container", "Leaf", "LeafList")

__doc__ = """This module contains wrappers describing the YANG 
structure and metadata obtained from SR OS.

.. Reviewed by PLM 20211201
.. Reviewed by TechComms 20211202
"""

class Schema:
    """YANG schema metadata information associated with elements in the data structure.

    .. note:: :py:class:`pysros.wrappers.Schema` metadata is read-only.

    .. property:: module

       YANG module name from which this node originates.

       :rtype: str

    .. property:: namespace

       YANG module namespace from which this node originates.  This is in URN or URL format.

       :rtype: str

    .. property:: yang_type

       YANG data type.  This type is the derived base YANG type, for example, if a YANG node uses
       a ``typedef``, and that ``typedef`` is a ``uint8``, yang_type returns ``uint8``.

       :rtype: str, :py:class:`SchemaType`

    .. property:: units

       The units defined in the YANG module.

       :rtype: str

    .. property:: default

       The default value as defined in the YANG module.

       :rtype: str, int

    .. property:: mandatory

       Identifies whether the item is required (mandatory) in the YANG module.

       :rtype: bool


    .. Reviewed by PLM 20221005
    .. Reviewed by TechComms 20221005
    """
    __slots__ = ("_model")
    _attributes = (
        "module",
        "namespace",
        "yang_type",
        "units",
        "default",
        "mandatory",
    )

    def __init__(self, model):
        self._model = model

    def __dir__(self):
        retval = super(self.__class__, self).__dir__()
        for attr in self._attributes:
            if hasattr(self, attr):
                retval.append(attr)
        return retval

    def __getattr__(self, attr):
        if attr == "module":
            return self._model.prefix
        if attr == "namespace":
            return self._model.namespace
        if attr == "yang_type":
            if self._model.yang_type is not None:
                return SchemaType(self._model.yang_type)
        if attr == "units":
            if self._model.units is not None:
                return self._model.units
        if attr == "default":
            if self._model.default is not None:
                return self._model.default
        if attr == "mandatory":
            if self._model.data_def_stm in (
                self._model.StatementType.leaf_,
                self._model.StatementType.leaf_list_,
                self._model.StatementType.choice_,
                self._model.StatementType.anydata_,
                self._model.StatementType.anyxml_,
            ):
                return True if self._model.mandatory else False
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{attr}'")

    def __eq__(self, other):
        attrs_eq = lambda self, other, attr: getattr(self, attr, None) == getattr(other, attr, None)
        return (
            self.__class__ is other.__class__
            and all(attrs_eq(self, other, attr) for attr in self._attributes)
        )

class SchemaType:
    """Type information for YANG node. Resolves to a YANG base type.

    .. property:: range

       The range defined in YANG.

       :rtype: str

    .. container::

       .. property:: union_members

          Base YANG types that form part of the YANG union.

          :rtype: tuple

    .. Reviewed by PLM 20221005
    .. Reviewed by TechComms 20221005
    """
    __slots__ = ("_yang_type")
    _attributes = (
        "range",
        "union_members",
    )

    def __init__(self, yt):
        self._yang_type = yt

    def __dir__(self):
        retval = super(self.__class__, self).__dir__()
        for attr in self._attributes:
            if hasattr(self, attr):
                retval.append(attr)
        return retval

    def __getattr__(self, attr):
        if attr == "range":
            if self._yang_type.json_name() in DECIMAL_LEAF_TYPE:
                return self._yang_type.yang_range
        if attr == "union_members":
            if isinstance(self._yang_type, YangUnion):
                return tuple(SchemaType(yt) for yt in self._yang_type)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{attr}'")

    def __str__(self):
        return self._yang_type.json_name()

    def __repr__(self):
        return self._yang_type.json_name()

    def __eq__(self, other):
        attrs_eq = lambda self, other, attr: getattr(self, attr, None) == getattr(other, attr, None)
        return (
            self.__class__ is other.__class__
            and self._yang_type.json_name() == other._yang_type.json_name()
            and all(attrs_eq(self, other, attr) for attr in self._attributes)
        )

class Wrapper:
    """Common functionality to support wrappers that describe the YANG structure from
    the SR OS schema.

    .. warning::
       Instance of this class SHOULD NOT be created by user of pysros library.

    .. Reviewed by PLM 20220923
    .. Reviewed by TechComms 20210712
    """

    __slots__ = ('_data', '_model')

    def __init__(self, value):
        self._data  = value
        self._model = None

    def __getattr__(self, attr):
        if attr == "_data":
            raise AttributeError()
        return getattr(self._data, attr)

    def __setattr__(self, attr, value):
        if attr == '_data' and not hasattr(self, '_data'):
            self._check_data_type(value)
            object.__setattr__(self, attr, value)
            return
        elif attr == '_model' and getattr(self, '_model', None) is None:
            object.__setattr__(self, attr, value)
            return
        raise AttributeError(f"'{self.__class__.__name__}' object attribute '{attr}' is read-only")

    def __delattr__(self, attr):
        raise make_exception(pysros_err_attr_cannot_be_deleted, obj=self.__class__.__name__, attribute=attr)

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._data == other._data

    @property
    def data(self):
        return self._data

    __module__ = 'pysros.wrappers'

    def __dir__(self):
        result = ['__module__', 'schema', 'data', '__getattr__', '__slots__']
        old_dir = object.__dir__(self)
        for item in dir(self.data):
            if not item.startswith('_') or item in old_dir:
                result.append(item)
        return result

    @property
    def schema(self):
        return Schema(self._model) if self._model else None

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


    @classmethod
    def _with_model(cls, data, model):
        obj = cls(data)
        obj._model = model
        return obj

def forward_methods(C, *methods):
    def make_forward(method):
        op = getattr(operator, method, None)
        if op is not None:
            # solves most methods like __add__, __and__, , but not special cases
            def forwad(self, *args):
                return op(self.data, *args)
            return forwad
        if method.startswith('__r'):
            n_method = "__" + method[3:]
            if hasattr(operator, n_method): # reverse operator __radd__, __rsub__, __rxor, etc.
                def forward(self, arg):
                    return getattr(operator, n_method)(arg, self.data)
                return forward

        # some methods (eg. __len__) are not defined in operator
        def forward(self, *args):
            return getattr(self.data, method)(*args)
        return forward
    for method in methods:
        setattr(C, method, make_forward(method))

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

    @classmethod
    def _check_data_type(cls, value):
        if not isinstance(value, dict):
            raise make_exception(pysros_err_unsupported_type_for_wrapper, wrapper_name=cls.__name__)

forward_methods(Container, '__contains__', '__delitem__', '__getitem__', '__iter__', '__len__', '__reversed__', '__setitem__')

class Action(Container):
    """YANG Action data structure node wrapper.

    A YANG action in the pySROS data structure behaves in the same way as a pySROS :py:class:`Container`, but
    it is returned by the :py:meth:`pysros.management.Connection.convert` method.

    :ivar data: dictionary containing the fields data
    """
    pass


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

    @classmethod
    def _check_data_type(cls, values):
        if not isinstance(values, list):
            raise make_exception(pysros_err_unsupported_type_for_wrapper, wrapper_name=cls.__name__)
        for value in values:
            Leaf._check_data_type(value)

forward_methods(LeafList, '__add__', '__contains__', '__delitem__', '__getitem__', '__iadd__', '__imul__', '__iter__', '__len__', '__mul__', '__reversed__', '__rmul__', '__setitem__')

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
            raise make_exception(pysros_err_unsupported_type_for_wrapper, wrapper_name = 'Leaf')

    def __bool__(self):
        return bool(self.data)

forward_methods(Leaf,
    '__lt__',
    '__le__',
    '__ge__',
    '__gt__',
    '__abs__',
    '__add__',
    '__and__',
    '__ceil__',
    '__contains__',
    '__divmod__',
    '__float__',
    '__floor__',
    '__floordiv__',
    '__getitem__',
    '__getnewargs__',
    '__index__',
    '__int__',
    '__invert__',
    '__iter__',
    '__len__',
    '__lshift__',
    '__mod__',
    '__mul__',
    '__neg__',
    '__or__',
    '__pos__',
    '__pow__',
    '__radd__',
    '__rand__',
    '__rdivmod__',
    '__rfloordiv__',
    '__rlshift__',
    '__rmod__',
    '__rmul__',
    '__ror__',
    '__round__',
    '__rpow__',
    '__rrshift__',
    '__rshift__',
    '__rsub__',
    '__rtruediv__',
    '__rxor__',
    '__sub__',
    '__truediv__',
    '__trunc__',
    '__xor__',
)
del forward_methods