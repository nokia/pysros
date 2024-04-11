# Copyright 2021-2024 Nokia

import operator
import collections

from abc import abstractmethod
from io import StringIO
from functools import total_ordering

from .errors import *
from .errors import make_exception
from .singleton import _Empty
from .yang_type import DECIMAL_LEAF_TYPE, INTEGRAL_LEAF_TYPE, YangUnion

__all__ = (
    "Action", "Container", "Leaf", "LeafList", "Annotation", "Annotations"
)

__doc__ = """This module contains wrappers describing the YANG
structure and metadata obtained from SR OS.

.. Reviewed by PLM 20211201
.. Reviewed by TechComms 20211202
"""


class Schema:
    """YANG schema supporting information associated with elements in the data structure.

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
        if attr == "yang_type" and self._model.yang_type:
            return SchemaType(self._model.yang_type)
        if attr == "units" and self._model.units:
            return self._model.units
        if attr == "default" and self._model.default:
            assert isinstance(self._model.default, str)
            if self._model.yang_type.json_name() == "boolean":
                if self._model.default == "true":
                    return True
                if self._model.default == "false":
                    return False
            if self._model.yang_type.json_name() in INTEGRAL_LEAF_TYPE:
                try:
                    return int(self._model.default)
                except ValueError:
                    pass
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
        raise make_exception(
            pysros_err_attr_object_has_no_attribute,
            obj=self.__class__.__name__,
            attribute=attr
        )

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
        raise make_exception(
            pysros_err_attr_object_has_no_attribute,
            obj=self.__class__.__name__,
            attribute=attr
        )

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

    __slots__ = ('_data', '_model', '_annotations')

    def __init__(self, value, annotations=None):
        self._data = value
        self._model = None
        self._annotations = annotations

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
        elif attr == '_annotations' or attr == 'annotations':
            object.__setattr__(self, '_annotations', value)
            return
        raise make_exception(
            pysros_err_attr_is_read_only,
            obj=self.__class__.__name__,
            attribute=attr
        )

    def __delattr__(self, attr):
        raise make_exception(
            pysros_err_attr_cannot_be_deleted,
            obj=self.__class__.__name__,
            attribute=attr
        )

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return False
        if self._data != other._data:
            return False
        lhs, rhs = getattr(self, 'annotations', None), getattr(other, 'annotations', None)

        if lhs == rhs:
            return True
        is_empty = lambda ann: bool(not ann or (isinstance(ann, list) and not any(ann)))
        lhs_empty, rhs_empty = is_empty(lhs), is_empty(rhs)
        return lhs_empty and rhs_empty

    @property
    def annotations(self):
        if self._annotations is None:
            self._annotations = Annotations()
        return self._annotations

    @property
    def data(self):
        return self._data

    __module__ = 'pysros.wrappers'

    def __dir__(self):
        result = ['__module__', 'annotations', 'schema', 'data', '__getattr__', '__slots__']
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
        raise make_exception(
            pysros_err_attr_is_read_only,
            obj=self.__class__.__name__,
            attribute='schema'
        )

    @staticmethod
    @abstractmethod
    def _check_data_type(value):
        pass

    def __str__(self):
        return str(self._data)

    def __repr__(self):
        s = StringIO()
        s.write(self.__class__.__name__)
        s.write('(')
        s.write(repr(self._data))
        anns = self._annotations
        if anns is not None:
            if (isinstance(anns, Annotations) and anns) or (isinstance(anns, list) and any(anns)):
                s.write(', annotations = ')
                s.write(repr(self._annotations))
        s.write(')')
        return s.getvalue()

    @classmethod
    def _with_model(cls, data, model, *, annotations=None):
        obj = cls(data)
        obj._model = model
        obj._annotations = annotations
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
            if hasattr(operator, n_method):  # reverse operator __radd__, __rsub__, __rxor, etc.
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

    def __init__(self, value=None, *,  annotations=None):
        super().__init__(value if value is not None else {}, annotations)

    @classmethod
    def _check_data_type(cls, value):
        if not isinstance(value, dict):
            raise make_exception(
                pysros_err_unsupported_type_for_wrapper,
                wrapper_name=cls.__name__
            )


forward_methods(
    Container,
    '__contains__',
    '__delitem__',
    '__getitem__',
    '__iter__',
    '__len__',
    '__reversed__',
    '__setitem__',
    '__or__',
    '__ror__',
)


class Action(Container):
    """YANG Action data structure node wrapper.

    Action in the pySROS data structure behaves as Container, but
    it it returned by convert action.

    :ivar data: dictionary containing the fields data
    """

    pass


class LeafList(Wrapper):
    """
    YANG leaf-list data structure node wrapper.

    A YANG leaf-list in the pySROS data structure behaves in the same way as a Python list, where the separate
    values can be obtained using an index.

    :ivar data: list containing the values

    .. Reviewed by PLM 20210630
    .. Reviewed by TechComms 20210712
    """

    __slots__ = ()

    def __init__(self, value=None, *, annotations=None):
        super().__init__(value if value is not None else [], annotations)

    @classmethod
    def _check_data_type(cls, values):
        if not isinstance(values, list):
            raise make_exception(
                pysros_err_unsupported_type_for_wrapper,
                wrapper_name=cls.__name__
            )
        for value in values:
            Leaf._check_data_type(value)

    @property
    def annotations(self):
        """
        List of YANG annotations (metadata) applied to the LeafList.

        Applying YANG annotations to a :py:class:`LeafList` uses the same constructs
        detailed in the :py:class:`Annotations` section.  When applied to LeafLists the
        :py:attr:`.annotations` property is a Python list.  Each entry in the LeafList
        has an entry in the :py:attr:`.annotations` list.

        Each entry in the LeafList may have zero or more annotations.  This list of
        annotations per entry is represented as an instance of the
        :py:class:`Annotations` class.  Each instance of :py:class:`Annotations`
        has zero or more instances of the :py:class:`Annotation`.

        This concept is better illustrated through examples.

        .. note:: The example below will not validate against the Nokia YANG models but
                  is provided to detail the implementation and usage of YANG annotations
                  attached to :py:class:`LeafList` classes.


        Consider the following LeafList:

        .. code-block:: python
           :name: annotations-leaflist-initiallist

           >>> my_leaflist
           LeafList(['one', 'two', 'three'])

        The list of annotations attached to this :py:class:`LeafList` is stored in the ``annotations``
        attribute:

        .. code-block:: python
           :name: annotations-leaflist-initiallist-annotations

           >>> my_leaflist.annotations
           []

        This is an empty list as there are no annotations defined against any entry in the :py:class:`LeafList`.
        Annotations will now be added to the first entry and the last entry of the list.  The first entry will
        have two annotations and the last one:

        .. code-block:: python
           :caption: Example showing annotations in :py:class:`LeafList` objects
           :name: annotations-leaflist-set-annotations

           >>> my_leaflist.annotations = [
           ...     Annotations([
           ...         Annotation(key='key1', data='value1'),
           ...         Annotation(key='key2', data='value2')
           ...     ]),
           ...     Annotations([]),
           ...     Annotations([
           ...         Annotation(key='key3', data='value3')
           ...     ])
           ... ]
           >>> my_leaflist.annotations
           [
               Annotations([
                   Annotation(key='key1', data='value1'),
                   Annotation(key='key2', data='value2')]),
               Annotations([]),
               Annotations([
                   Annotation(key='key3', data='value3')
               ])
           ]

        .. Reviewed by PLM 20231003

        """
        if self._annotations is None:
            self._annotations = [Annotations() for _ in self._data]
        return self._annotations


forward_methods(
    LeafList,
    '__add__', '__contains__', '__delitem__', '__getitem__', '__iadd__',
    '__imul__', '__iter__', '__len__', '__mul__', '__reversed__', '__rmul__',
    '__setitem__'
)


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
        if not isinstance(data, (str, int, bool, _Empty)) and data is not None:
            raise make_exception(
                pysros_err_unsupported_type_for_wrapper,
                wrapper_name='Leaf'
            )

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
                '__xor__',)
del forward_methods

_sentinel = object()

class _AnnotationAttr:
    """Internal class for handling attributes of Annotation."""
    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = '_' + name

    def __set__(self, obj, value):
        if self.private_name != '_data':
            setattr(obj, '_model', None)
        if self.private_name == '_key' and not isinstance(value, str):
            raise make_exception(pysros_err_annotation_type_key)
        setattr(obj, self.private_name, value)

    def __get__(self, obj, objtype=None):
        value = getattr(obj, self.private_name)
        if value is None:
            raise make_exception(
                pysros_err_attr_object_has_no_attribute,
                obj=obj.__class__.__name__,
                attribute=self.public_name)
        return value

    def __delete__(self, obj):
        if getattr(obj, self.private_name) is None or self.private_name == '_key':
            raise make_exception(
                pysros_err_attr_object_has_no_attribute,
                obj=obj.__class__.__name__,
                attribute=self.public_name
            )
        setattr(obj, self.private_name, None)

@total_ordering
class Annotation:
    """
    Wrapper for an individual annotation (YANG metadata) associated with an elements
    in the data structure.  An element in the data structure may have more than one
    :py:class:`Annotation`.  The :py:class:`Annotations` class is used to define this.

    Allows operator to provide an arbitrary key/value pair to any element in the pySROS
    data structure.  The data in the :py:class:`Annotation` must exist in the nodes YANG
    schema for the :py:meth:`pysros.management.Datastore.set` and
    :py:meth:`pysros.management.Connection.convert` methods to function.

    :ivar key: The name of the YANG annotation statement.  This may be in simple form
               or in namespace qualified form, for example: ``comment`` or ``nokia-attr:comment``.

    :ivar data: The value of the annotation.

    :ivar module: The YANG module name in which the YANG annotation exists.

    :ivar namespace: The YANG module namespace in which the YANG annotation exists.

    .. Reviewed by PLM 20231003

    """

    __slots__ = ('_key', '_data', '_module', '_namespace', '_model')
    key = _AnnotationAttr()
    """The name of the YANG annotation statement.  This may be in simple form
    or in namespace qualified form, for example: `comment` or `nokia-attr:comment`.
    
    .. Reviewed by PLM 20231003
    """
    data = _AnnotationAttr()
    """The value of the annotation.
    
    .. Reviewed by PLM 20231003
    """
    module = _AnnotationAttr()
    """The YANG module name in which the YANG annotation exists.
    
    .. Reviewed by PLM 20231003
    """
    namespace = _AnnotationAttr()
    """The YANG module namespace in which the YANG annotation exists.
    
    .. Reviewed by PLM 20231003
    """

    def __init__(self, key, data=None, *, module=None, namespace=None):
        if not isinstance(key, str):
            raise make_exception(pysros_err_annotation_type_key)

        if ':' in key:
            nmodule, key = key.split(':', 1)
            if module is not None and module != nmodule:
                raise make_exception(pysros_err_annotation_invalid_module)
            module = nmodule

        self._key = key
        self._data = data
        self._module = module
        self._namespace = namespace
        self._model = None

    @classmethod
    def _with_model(cls, *arg, model, **kwarg):
        res = cls(*arg, **kwarg)
        res._model = model
        return res

    @property
    def schema(self):
        """YANG schema supporting information associated with elements in the data structure (Read only).

        .. Reviewed by PLM 20231003

        """
        return self._model and Schema(self._model)

    def __repr__(self):
        comma = False
        stream = StringIO()
        stream.write(self.__class__.__name__)
        stream.write('(')
        for attr in self.__slots__:
            if attr.startswith('_'):
                attr = attr[1:]
            a = getattr(self, attr, _sentinel)
            if a != _sentinel:
                if comma:
                    stream.write(', ')
                comma = True
                stream.write(f'{attr}={getattr(self, attr)!r}')
        stream.write(')')
        return stream.getvalue()

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return (
            self._key == other._key
            and self._data == other._data
            and self._module == other._module
            and self._namespace == other._namespace
        )

    def __lt__(self, other):
        def is_less(a,b):
            return False if (b is None) else (a is None or a < b)

        if self.__class__ is not other.__class__:
            return NotImplemented

        if self._key != other._key: return is_less(self._key, other._key)
        if self._module != other._module: return is_less(self._module, other._module)
        if self._namespace != other._namespace: return is_less(self._namespace, other._namespace)
        return is_less(self._data, other._data)


class Annotations(collections.UserList):
    """Annotations class provides wrapper for instances of the Annotation class that must be supplied
    in the same way as Python *list*.

    The annotations (there may be more than one) on a particular YANG node are defined in the ``annotations``
    parameter attached to a :py:class:`Leaf`, :py:class:`Container` or :py:class:`LeafList`.
    The ``annotations`` parameter is a class of type :py:class:`.Annotations` (with
    an 's').  This is a list of :py:class:`.Annotation` (without an 's') class instances.

    An :py:class:`.Annotation` in pySROS is treated in a similar way as any
    other YANG structure such as a :py:class:`.Leaf`.  A :py:class:`.Annotation`
    class wrapper encodes the structures required to define and use a YANG modeled annotation.  Unlike other
    wrappers, because a YANG modeled annotation can be in a different YANG namespace from the node it is
    attached to, additional information is needed.

    The :py:meth:`pysros.management.Connection.convert` method and the :py:meth:`pysros.management.Datastore.set`
    method support the :py:class:`.Annotation` class.  This means that, as with other data in
    pySROS, annotations can be entered without providing the details of the YANG module and these methods
    derive the correct YANG model information using the YANG schema learned from the specific router.

    .. note::

       Applying annotations to :py:class:`LeafList` objects requires special consideration.  Please refer to
       the :py:attr:`.LeafList.annotations` section for more information.

    The following example obtains a :py:class:`.Leaf` from the device, in this instance the system name, and
    adds a configuration comment to it which it then sets back to the router using the
    :py:meth:`pysros.management.Datastore.set` method.  The example assumes that a
    :py:class:`pysros.management.Connection` object called ``connection_object`` has already been created:

    .. code-block:: python
       :caption: Set a configuration comment on the system name obtained from the device
       :name: annotations-set-comment-on-sysname

       >>> from pysros.wrappers import Annotations, Annotation
       >>> path = '/nokia-conf:configure/system/name'
       >>> system_name = connection_object.running.get(path)
       >>> system_name
       Leaf('sros')
       >>> system_name.annotations = [Annotation('comment', 'This is my comment')]
       >>> connection_object.candidate.set(path, system_name)

    The following example obtains a :py:class:`.Leaf` from the device and adds a configuration comment to it in
    the native Python data structure.  It then uses the :py:meth:`pysros.management.Connection.convert` method
    to query the known YANG schema for the given router and add the YANG model information to the
    :py:class:`.Annotation`.  The example assumes that a :py:class:`pysros.management.Connection` object called
    ``connection_object`` has already been created:

    .. code-block:: python
       :caption: Use convert to identify and complete YANG specific attributes in the object
       :name: annotations-convert-comment-on-sysname
       :emphasize-lines: 6-10,15,20,25-26

       >>> from pysros.wrappers import Annotations, Annotation
       >>> path = '/nokia-conf:configure/system/name'
       >>> system_name = connection_object.running.get(path)
       >>> system_name
       Leaf('sros')
       >>> system_name.annotations
       Annotations([])
       >>> system_name.annotations.append(Annotation('comment', 'This is my configuration comment'))
       >>> system_name.annotations
       Annotations([Annotation(key='comment', data='This is my configuration comment')])
       >>> connection_object.convert(path,
       ...                           system_name,
       ...                           source_format='pysros',
       ...                           destination_format='xml')
       '<nokia-conf:name xmlns:nokia-conf="urn:nokia.com:sros:ns:yang:sr:conf" xmlns:nokia-attr="urn:nokia.com:sros:ns:yang:sr:attributes" nokia-attr:comment="This is my configuration comment">sros</nokia-conf:name>'
       >>> connection_object.convert(path,
       ...                           system_name,
       ...                           source_format='pysros',
       ...                           destination_format='json')
       '{"@nokia-conf:name": {"nokia-attributes:comment": "This is my configuration comment"}, "nokia-conf:name": "sros"}'
       >>> augmented_system_name = connection_object.convert(path,
       ...                                                   system_name,
       ...                                                   source_format='pysros',
       ...                                                   destination_format='pysros')
       >>> augmented_system_name.annotations
       Annotations([Annotation(key='comment', data='This is my configuration comment', module='nokia-attributes', namespace='urn:nokia.com:sros:ns:yang:sr:attributes')])

    This next example takes a valid NETCONF RPC encoded in XML that inserts a new item into a user-ordered YANG
    list.  The well-known ``operation`` annotation.  Using the :py:class:`.Annotations` and
    :py:class:`.Annotation` classes, this RPC can be converted into native the native Python (pySROS)
    data structure, manipulated if required, and sent to the router.  The example assumes that a
    :py:class:`pysros.management.Connection` object called ``connection_object`` has already been created.

    The initial configuration of the user-ordered list is as follows:

    .. code-block:: text
       :caption: Initial state of the user-ordered list
       :name: annotations-user-ordered-list-before

       (gl)[/configure policy-options policy-statement "example"]
       A:admin@sros# info
           entry-type named
           named-entry "one" {
               action {
                   action-type accept
               }
           }
           named-entry "three" {
               action {
                   action-type accept
               }
           }
           default-action {
               action-type reject
           }


    .. code-block:: python
       :caption: Convert NETCONF operations using system defined annotations
       :name: annotations-system-defined
       :emphasize-lines: 8,19

        >>> from pysros.wrappers import Annotation, Annotations
        >>> from pysros.management import connect
        >>> my_xml = \"\"\"
        ... <configure xmlns="urn:nokia.com:sros:ns:yang:sr:conf" xmlns:yang="urn:ietf:params:xml:ns:yang:1" xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0">
        ...     <policy-options>
        ...         <policy-statement>
        ...             <name>example</name>
        ...             <named-entry nc:operation="merge" yang:insert="after" yang:key="[entry-name='one']">
        ...                 <entry-name>two</entry-name>
        ...                 <action>
        ...                     <action-type>accept</action-type>
        ...                 </action>
        ...             </named-entry>
        ...         </policy-statement>
        ...     </policy-options>
        ... </configure>
        ... \"\"\"
        >>> my_rpc = connection_object.convert('/', my_xml, source_format='xml', destination_format='pysros')
        {'configure': Container({'policy-options': Container({'policy-statement': {'example': Container({'name': Leaf('example'), 'named-entry': OrderedDict([('two', Container({'entry-name': Leaf('two'), 'action': Container({'action-type': Leaf('accept')})}, annotations = Annotations([Annotation(key='operation', data='merge', module='ietf-netconf', namespace='urn:ietf:params:xml:ns:netconf:base:1.0'), Annotation(key='insert', data='after', module='yang', namespace='urn:ietf:params:xml:ns:yang:1'), Annotation(key='key', data="[entry-name='one']", module='yang', namespace='urn:ietf:params:xml:ns:yang:1')])))])})}})})}
        >>> connection_object.candidate.set('/nokia-conf:configure', my_rpc['configure'])


    .. code-block:: text
       :caption: Resulting state of the user-ordered list
       :name: annotations-user-ordered-list-after
       :emphasize-lines: 9-13

       (gl)[/configure policy-options policy-statement "example"]
       A:admin@sros# info
           entry-type named
           named-entry "one" {
               action {
                   action-type accept
               }
           }
           named-entry "two" {
               action {
                   action-type accept
               }
           }
           named-entry "three" {
               action {
                   action-type accept
               }
           }
           default-action {
               action-type reject
           }

    The :py:class:`.Annotations` class behaves in a similar way to a native Python list and many of the
    functions that operate on a Python list will also function on the :py:class:`.Annotations` class.
    Examples include :py:func:`index` (which returns the numerical location in the list of the requested
    item), :py:func:`remove` (which deletes a specific item from a list) and :py:func:`append` (which
    adds an item to the end of a list).

    .. note:: When using :py:func:`index` and :py:func:`remove` the exact matching :py:class:`.Annotation`
              must be provided including all associated parameters.

    A number of additional helper methods are provided for searching through :py:class:`.Annotations` and
    selecting specific :py:class:`.Annotation` entries.  These are described below:

    .. Reviewed by PLM 20231001

    """

    def __eq__(self, other):
        if self.__class__ is not other.__class__:
            return NotImplemented
        return self.data == other.data

    def index_annotation(self, key, data=None, *, module=None, namespace=None):
        """Return the index to searched :py:attr:`.Annotation.key`.  An exception
        is raised if the :py:class:`.Annotation` is not found.

        :param key: Name of the :py:class:`Annotation`.  This should match the
                    :py:attr:`.Annotation.key` in order to yield a successful match.
                    If more than one :py:class:`Annotation` exists with the same
                    :py:attr:`.Annotation.key` other parameters must be provided.
        :type key: str

        :param data: The value (:py:attr:`.Annotation.data`) of the
                     :py:class:`Annotation`.
        :type data: str, optional

        :param module: The YANG module name that :py:class:`Annotation` exists in.
        :type module: str, optional

        :param namespace: The YANG module namespace that the :py:class:`Annotation`
                          exists in.
        :type namespace: str, optional

        :raises ValueError: A matching :py:class:`Annotation` is not found.

        .. note:: The example below will not validate against the Nokia YANG models but
                  is provided to detail the implementation and usage of the :py:class:`Annotations`
                  class.

        .. code-block:: python
           :caption: :py:meth:`.Annotations.index_annotation` example
           :name: annotations-index-annotation
           :emphasize-lines: 3-4

           >>> myleaf.annotations
           Annotations([Annotation(key='key1', data='data1'), Annotation(key='key2', data='data2'), Annotation(key='key3', data='data3')])
           >>> myleaf.annotations.index_annotation('key2')
           1

        .. code-block:: python
           :caption: :py:meth:`.Annotations.index_annotation` example handling a failed match
           :name: annotations-index-annotation-failed-match
           :emphasize-lines: 3-8

           >>> myleaf.annotations
           Annotations([Annotation(key='key1', data='data1'), Annotation(key='key2', data='data2'), Annotation(key='key3', data='data3')])
           >>> try:
           ...   myleaf.annotations.index_annotation('foo')
           ... except ValueError as error:
           ...   print("Failed to find Annotation:", error)
           ...
           Failed to find Annotation: Annotation not found

        .. Reviewed by PLM 20231003

        """

        def match(required, given):
            return (required is None) or (required == given)

        if not isinstance(key, str):
            raise make_exception(pysros_err_annotation_type_key)

        if ':' in key and module == None:
            module, key = key.split(':', 1)

        idx = None
        for i, d in enumerate(self.data):
            if (not match(key, d._key)
                    or not match(data, d._data)
                    or not match(module, d._module)
                    or not match(namespace, d._namespace)):
                continue

            if idx is not  None:
                raise make_exception(pysros_err_annotation_too_many_instances)

            idx = i

        if idx is None:
            raise  make_exception(pysros_err_annotation_not_found)
        return idx

    def get(self, annotation):
        """Return the :py:class:`.Annotation` (without an ‘s’) from the :py:class:`.Annotations`
        (with an ‘s’) class (list) that matches the provided :py:class:`.Annotation`.

        The match must be identical, that is, all parameters inside the :py:class:`.Annotation`
        class *must match exactly*.

        :param annotation: Annotation object to match in the :py:class:`.Annotations` list.
        :type annotation: :py:class:`.Annotation`

        :raises ValueError: Error if the requested :py:class:`.Annotation` is not found.

        .. note:: The example below does not validate against the Nokia YANG models but
          is provided to detail the implementation and usage of the :py:class:`Annotations`
          class.

        .. code-block:: python
           :caption: :py:meth:`.Annotations.get` example
           :name: annotations-get
           :emphasize-lines: 3-4

           >>> myleaf.annotations
           Annotations([Annotation(key='key1', data='data1'), Annotation(key='key2', data='data2'), Annotation(key='key3', data='data3')])
           >>> myleaf.annotations.get(Annotation(key='key3', data='data3'))
           Annotation(key='key3', data='data3')

        .. code-block:: python
           :caption: :py:meth:`.Annotations.get` example handling a failed match
           :name: annotations-get-failed-match
           :emphasize-lines: 3-8

           >>> myleaf.annotations
           Annotations([Annotation(key='key1', data='data1'), Annotation(key='key2', data='data2'), Annotation(key='key3', data='data3')])
           >>> try:
           ...   myleaf.annotations.get('key1')
           ... except ValueError as error:
           ...   print("Failed to find Annotation:", error)
           ...
           Failed to find Annotation: 'key1' is not in list

        .. Reviewed by PLM 20231003
        .. Reviewed by TechComms 20231009

        """
        idx = self.data.index(annotation)
        return self.data[idx]

    def get_annotation(self, key, data=None, *, module=None, namespace=None):
        """
        Return the :py:class:`.Annotation` (without an ‘s’) from the :py:class:`.Annotations`
        (with an ‘s’) class (list) that matches the provided :py:attr:`.Annotation.key`.
        An exception is raised if the :py:class:`Annotation` is not found.

        :param key: Name of the :py:class:`Annotation`.  This should match the
                    :py:attr:`.Annotation.key` in order to yield a successful match.
                    If more than one :py:class:`Annotation` exists with the same
                    :py:attr:`.Annotation.key` other parameters must be provided.
        :type key: str

        :param data: The value (:py:attr:`.Annotation.data`) of the
                     :py:class:`Annotation`.
        :type data: str, optional

        :param module: The YANG module name that :py:class:`Annotation` exists in.
        :type module: str, optional

        :param namespace: The YANG module namespace that the :py:class:`Annotation`
                          exists in.
        :type namespace: str, optional

        :raises ValueError: A matching :py:class:`Annotation` is not found.

        .. note:: The example below does not validate against the Nokia YANG models but
                  is provided to detail the implementation and usage of the :py:class:`Annotations`
                  class.

        .. code-block:: python
           :caption: :py:meth:`.Annotations.get_annotation` example
           :name: annotations-get-annotation
           :emphasize-lines: 3-4

           >>> myleaf.annotations
           Annotations([Annotation(key='key1', data='data1'), Annotation(key='key2', data='data2'), Annotation(key='key3', data='data3')])
           >>> myleaf.annotations.get_annotation('key2')
           Annotation(key='key2', data='data2')

        .. Reviewed by PLM 20231003
        .. Reviewed by TechComms 20231009

        """
        idx = self.index_annotation(key, data, module=module, namespace=namespace)
        return self.data[idx]


    def remove_annotation(self, key, data=None, *, module=None, namespace=None):
        """Remove the :py:class:`.Annotation` object for the searched
        :py:attr:`.Annotation.key` from the :py:class:`.Annotations` class (list).
        An exception is raised if the :py:class:`.Annotation` is not found.

        :param key: Name of the :py:class:`Annotation`.  This should match the
                    :py:attr:`.Annotation.key` in order to yield a successful match.
                    If more than one :py:class:`Annotation` exists with the same
                    :py:attr:`.Annotation.key` other parameters must be provided.
        :type key: str

        :param data: The value (:py:attr:`.Annotation.data`) of the
                     :py:class:`Annotation`.
        :type data: str, optional

        :param module: The YANG module name that :py:class:`Annotation` exists in.
        :type module: str, optional

        :param namespace: The YANG module namespace that the :py:class:`Annotation`
                          exists in.
        :type namespace: str, optional

        :raises ValueError: A matching :py:class:`Annotation` is not found.

        .. note:: The example below does not validate against the Nokia YANG models but
                  is provided to detail the implementation and usage of the :py:class:`Annotations`
                  class.

        .. code-block:: python
           :caption: :py:meth:`.Annotations.remove_annotation` example
           :name: annotations-remove-annotation
           :emphasize-lines: 3-4

           >>> myleaf.annotations
           Annotations([Annotation(key='key1', data='data1'), Annotation(key='key2', data='data2'), Annotation(key='key3', data='data3')])
           >>> myleaf.annotations.remove_annotation('key2')
           >>> myleaf.annotations
           Annotations([Annotation(key='key1', data='data1'), Annotation(key='key3', data='data3')])

        .. Reviewed by PLM 20231003
        .. Reviewed by TechComms 20231009

        """
        idx = self.index_annotation(key, data, module=module, namespace=namespace)
        del self.data[idx]

    def __repr__(self):
        return f"Annotations({self.data!r})"

