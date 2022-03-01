# Copyright 2021 Nokia

import copy
import locale
import sys

from enum import Enum, IntFlag, IntEnum, auto
from typing import Any, Dict, List, Optional, Tuple

from lxml import etree

from .errors import *
from .identifier import Identifier, NoModule
from .yang_type import Enumeration, YangType, YangTypeBase
from .yang_type import YangType

class AModel:
    class StatementType(Enum):
        leaf_         = 0
        list_         = 1
        container_    = 2
        leaf_list_    = 3
        choice_       = 4
        case_         = 5
        augment_      = 6
        uses_         = 7
        typedef_      = 8
        module_       = 9
        submodule_    = 10
        grouping_     = 11
        import_       = 12
        identity_     = 13
        action_       = 14
        anydata_      = 15
        anyxml_       = 16
        notification_ = 17
        rpc_          = 18
        input_        = 19
        output_       = 20
        deviation_    = 21
        deviate_      = 22

    __slots__ = ()

    def recursive_walk(self, cb):
        cont = cb(self)
        if cont == False:
            return
        for i in self.children:
            i.recursive_walk(cb)

    def __str__(self):
        return f"""Model("{str(self.name)}")"""

    def __repr__(self):
       return f"""Model("{str(self.name)}")"""

    def __deepcopy__(self, memo):
        raise make_exception(pysros_err_use_deepcopy)

    def debug_print(self, prefix="", last = False):
        class Colors:
            RED    = '\033[1;31;48m'
            GREEN  = '\033[1;32;48m'
            DGREEN = '\033[2;32;48m'
            BLUE   = '\033[1;34;48m'
            CYAN   = '\033[1;36;48m'
            PURPLE = '\033[1;35;48m'
            YELLOW = '\033[1;33;48m'
            RESET  = '\033[1;37;0m'

        utf_supported = locale.getlocale()[1] == "UTF-8"
        class AsciiArt:
            CHILD =         "+-- " if not utf_supported else "\u251c\u2500\u2500 "
            LAST_CHILD =    "+-- " if not utf_supported else "\u2514\u2500\u2500 "
            VERTICAL_LINE = "   |" if not utf_supported else "   \u2502"

        data_def_stm = self.data_def_stm.name[:-1]

        if sys.stdout.isatty():
            colorize = lambda data, color : color + str(data) + Colors.RESET
        else:
            colorize = lambda data, color : str(data)

        if not prefix:
            field_prefix = ""
        elif last:
            field_prefix = AsciiArt.LAST_CHILD
        else:
            field_prefix = AsciiArt.CHILD
        if data_def_stm == "container":
            t = colorize(data_def_stm, Colors.YELLOW)
        elif data_def_stm == "list":
            t = colorize(data_def_stm, Colors.GREEN)
        else:
            t = colorize(data_def_stm, Colors.CYAN)
        t_sufix = []
        if data_def_stm in ("leaf", "typedef", ):
            t_sufix.append(colorize(self.yang_type, Colors.BLUE))
        elif data_def_stm == "identity":
            bases = [str(b) for b in self.identity_bases]
            if bases:
                t_sufix.append(colorize(f"base=[{','.join(bases)}]", Colors.BLUE))
        elif data_def_stm == "list":
            t_sufix.append(colorize(",".join(self.local_keys), Colors.DGREEN))
            if self.user_ordered:
                t_sufix.append(colorize("user ordered", Colors.PURPLE))
        elif data_def_stm == "container":
            if self.presence_container:
                t_sufix.append(colorize("presence", Colors.PURPLE))
        elif data_def_stm == "typedef":
            t_sufix.append(colorize(f"->{self.yang_type}", Colors.YELLOW))
        elif data_def_stm == "augment":
            t_sufix.append(colorize(self.target_path, Colors.PURPLE))

        print(f"""{prefix[:-1]}{field_prefix}{self.debug_flags()} {self.name} [{" ".join((t,*t_sufix))}]""")

        remain = self.children_size - 1
        for i in self.children:
            new_prefix = prefix + ("    " if not remain else AsciiArt.VERTICAL_LINE)
            if not prefix:
                new_prefix = new_prefix[3:]
            i.debug_print(new_prefix, not remain)
            remain -= 1

    def debug_flags(self) -> str:
        """Return text flags:
            rw  for configuration data
            ro  for non-configuration data
            -x  for rpcs and actions
            -n  for notifications
            mp   for schema mount points

        .. Reviewed by TechComms 20210713
        """
        data_def_stm = self.data_def_stm.name[:-1]
        if data_def_stm in ("leaf", "list", "leaf_list", "container", "choice", "case"):
            return {
                True:  'rw',
                False: 'ro',
                None:  '??'
            }[self.config]
        if data_def_stm in ("rpc", "action"):
            return "-x"
        if data_def_stm == "notification":
            return "-n"
        return "mp"

    def test_print(self, prefix="", _last = False):
        data_def_stm = self.data_def_stm.name[:-1]
        if not prefix:
            field_prefix = ""
        else:
            field_prefix = "+-- "
        t_sufix = [data_def_stm]
        if data_def_stm in ("leaf", "typedef"):
            t_sufix.append(str(self.yang_type))
        elif data_def_stm == "list":
            t_sufix.append(",".join(self.local_keys))
            if self.user_ordered:
                t_sufix.append("user ordered")
        elif data_def_stm == "container":
            if self.presence_container:
                t_sufix.append("presence")
        elif data_def_stm == "typedef":
            t_sufix.append(f"->{self.yang_type}")
        elif data_def_stm == "augment":
            t_sufix.append(self.target_path)

        res = f"""{prefix[:-1]}{field_prefix}{self.name} [{" ".join(t_sufix)}]\n"""

        remain = self.children_size - 1
        for i in sorted(self.children, key=lambda o: (str(o.name.prefix), o.name.name)):
            new_prefix = prefix + ("    " if not remain else "   |")
            if not prefix:
                new_prefix = new_prefix[3:]
            res += i.test_print(new_prefix, not remain)
            remain -= 1
        return res

class BuildingModel(AModel):
    __slots__ = (
        "name",
        "children",
        "yang_type",
        "presence_container",
        "user_ordered",
        "local_keys",
        "data_def_stm",
        "target_path",
        "identity_bases",
        "_parent",
        "config",
        "blueprint",
    )

    def __init__(self, name: Identifier, data_def_stm: AModel.StatementType, parent):
        self.name = Identifier.builtin(name) if type(name) == str else name
        self.children: List[Model] = []
        self.yang_type: Optional[YangType] = None
        self.presence_container = False
        self.user_ordered = False
        self.local_keys: List[str] = []
        self.data_def_stm = data_def_stm
        self.target_path = None
        self.parent = parent
        self.identity_bases = None if data_def_stm != AModel.StatementType.identity_ else []
        self.config: bool = True
        self.blueprint = []

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, new_parent):
        self._parent = new_parent
        if new_parent:
            new_parent.children.append(self)

    @property
    def has_children(self):
        return bool(self.children)

    @property
    def children_size(self):
        return len(self.children)

    @property
    def prefix(self):
        return self.name.prefix

    @prefix.setter
    def prefix(self, v):
        self.name._prefix = v

    def sanity_parent_child_test(self):
        for i in self.children:
            assert self is i.parent
            i.sanity_parent_child_test()

    def delete_from_parent(self, *, quiet=True):
        idx = self.parent.children.index(self)
        if idx < 0:
            if quiet:
                return
            else:
                raise make_exception(pysros_err_cannot_remove_node, node=self.name)
        del self.parent.children[idx]
        self.parent = None

    def deepcopy(self, parent):
        cls = self.__class__
        result = cls.__new__(cls)
        for i in self.__slots__:
            if i in ("_parent", "children"):
                continue
            setattr(result, i, copy.deepcopy(getattr(self, i)))
        result.parent = parent
        result.children = []
        for child in self.children:
            child.deepcopy(result)
        return result

class StorageModel(AModel):
    __slots__ = (
        "_storage",
        "_index",
    )

    class DataBitmask(IntFlag):
        data_def_stm        = 0xff
        presence_container  = 1 << 8
        user_ordered        = 1 << 9
        config              = 1 << 10

    class DataMembers(IntEnum):
        name            = 0
        children        = 1
        yang_type       = 2
        local_keys      = 3
        target_path     = 4
        identity_bases  = 5
        parent          = 6
        bitmask         = 7

class Model(StorageModel):
    """Class to represent a single YANG entry and hold additional information, such as type, configuration state, children, and data definition statement.

    .. Reviewed by TechComms 20210713
    """
    __slots__ = ("_data", "children", "parent", "name", "_bitmask", "data_def_stm",)

    def __init__(self, storage, index, parent):
        assert storage
        assert isinstance(storage, list)
        assert 0 <= index < len(storage)
        self._storage = storage
        self._index = index
        self._data = self._storage[self._index]
        self.parent = parent

    def __getattr__(self, name):
        getter = {
            "name": Model._name_getter,
            "children": Model._children_getter,
            "_bitmask": Model._bitmask_getter,
            "data_def_stm": Model._data_def_stm_detter,
        }.get(name)
        if not getter:
            raise AttributeError(name)
        res = getter(self)
        setattr(self, name, res)
        return res

    def _name_getter(self):
        name = self._data[Model.DataMembers.name]
        if name[0] is None:
            return Identifier.builtin(name[1])
        return Identifier(*name)

    def _children_getter(self):
        return [Model(self._storage, index, self) for index in self._data[Model.DataMembers.children]]

    def _bitmask_getter(self):
        return self._data[Model.DataMembers.bitmask]

    def _data_def_stm_detter(self):
        return Model.StatementType(int(self._bitmask & Model.DataBitmask.data_def_stm))

    @property
    def prefix(self):
        return self._data[Model.DataMembers.name][0]

    @property
    def has_children(self):
        return bool(self.children_data)

    @property
    def children_size(self):
        return len(self.children_data)

    @property
    def children_data(self):
        return self._data[Model.DataMembers.children]

    @property
    def yang_type(self):
        return self._data[Model.DataMembers.yang_type]

    @property
    def presence_container(self):
        return bool(self._bitmask & Model.DataBitmask.presence_container)

    @property
    def user_ordered(self):
        return bool(self._bitmask & Model.DataBitmask.user_ordered)

    @property
    def local_keys(self):
        return self._data[Model.DataMembers.local_keys]

    @property
    def target_path(self):
        return self._data[Model.DataMembers.target_path]

    @property
    def identity_bases(self):
        return self._data[Model.DataMembers.identity_bases]

    @property
    def config(self):
        return bool(self._bitmask & Model.DataBitmask.config)

    def sanity_parent_child_test(self):
        for i in self.children:
            assert self._data is i.parent._data
            i.sanity_parent_child_test()

    def __str__(self):
        return f"""Model("{str(self.name)}")"""

    def __repr__(self):
        return f"""Model("{str(self.name)}")"""

    def __deepcopy__(self, memo):
        raise make_exception(pysros_err_use_deepcopy)

    def __eq__(self, other):
        return self._data is other._data

class StorageConstructionModel(StorageModel):
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        storage, data = new_Model_data(*args, **kwargs)
        self._storage = storage
        self._index = len(storage)
        self._storage.append(data)
        self.parent = self.parent

    @classmethod
    def new_from_data(cls, storage, index):
        assert storage
        assert isinstance(storage, list)
        assert 0 <= index < len(storage)
        res = cls.__new__(cls)
        res._storage = storage
        res._index = index
        return res

    @property
    def name(self):
        name = self._data[self.DataMembers.name]
        if name[0] is None:
            return Identifier.builtin(name[1])
        return Identifier(*name)

    @property
    def prefix(self):
        return self._data[self.DataMembers.name][0]

    @prefix.setter
    def prefix(self, value):
        self._data[self.DataMembers.name][0] = value

    @property
    def children(self):
        return (self.new_from_data(self._storage, index) for index in self._data[self.DataMembers.children])

    @property
    def has_children(self):
        return bool(self.children_data)

    @property
    def children_size(self):
        return len(self.children_data)

    @property
    def children_data(self):
        return self._data[self.DataMembers.children]

    @children_data.setter
    def children_data(self, data):
        self._data[self.DataMembers.children] = data

    @property
    def yang_type(self):
        return self._data[self.DataMembers.yang_type]

    @yang_type.setter
    def yang_type(self, value):
        self._data[self.DataMembers.yang_type] = value

    @property
    def presence_container(self):
        return bool(self._bitmask & self.DataBitmask.presence_container)

    @presence_container.setter
    def presence_container(self, value):
        if value:
            self._bitmask |= int(self.DataBitmask.presence_container)
        else:
            self._bitmask &= int(~self.DataBitmask.presence_container)

    @property
    def user_ordered(self):
        return bool(self._bitmask & self.DataBitmask.user_ordered)

    @user_ordered.setter
    def user_ordered(self, value):
        if value:
            self._bitmask |= int(self.DataBitmask.user_ordered)
        else:
            self._bitmask &= int(~self.DataBitmask.user_ordered)

    @property
    def local_keys(self):
        return self._data[self.DataMembers.local_keys]

    @local_keys.setter
    def local_keys(self, value):
        self._data[self.DataMembers.local_keys] = value

    @property
    def data_def_stm(self):
        return self.StatementType(int(self._bitmask & self.DataBitmask.data_def_stm))

    @property
    def target_path(self):
        return self._data[self.DataMembers.target_path]

    @target_path.setter
    def target_path(self, value):
        self._data[self.DataMembers.target_path] = value

    @property
    def identity_bases(self):
        return self._data[self.DataMembers.identity_bases]

    @identity_bases.setter
    def identity_bases(self, value):
        self._data[self.DataMembers.identity_bases] = value

    @property
    def parent(self):
        parent = self._data[self.DataMembers.parent]
        if parent is None:
            return parent
        return self.new_from_data(self._storage, parent)

    @parent.setter
    def parent(self, new_parent):
        self._data[self.DataMembers.parent] = new_parent if new_parent is None else new_parent._index
        if new_parent:
            assert new_parent._storage is self._storage
            new_parent.children_data.append(self._index)

    @property
    def config(self):
        return bool(self._bitmask & self.DataBitmask.config)

    @config.setter
    def config(self, value):
        if value:
            self._bitmask |= int(self.DataBitmask.config)
        else:
            self._bitmask &= int(~self.DataBitmask.config)

    @property
    def _bitmask(self):
        return self._data[self.DataMembers.bitmask]

    @_bitmask.setter
    def _bitmask(self, value):
        self._data[self.DataMembers.bitmask] = value

    @property
    def _data(self):
        return self._storage[self._index]

    def sanity_parent_child_test(self):
        for i in self.children:
            assert self._data is i.parent._data
            i.sanity_parent_child_test()

    def __str__(self):
        return f"""Model("{str(self.name)}")"""

    def __repr__(self):
        return f"""Model("{str(self.name)}")"""

    def deepcopy(self, parent):
        cls = self.__class__
        result = cls.__new__(cls)
        result._storage = parent._storage
        result._index = len(result._storage)
        result._storage.append(copy.deepcopy(self._data))
        result.children_data = []
        result.parent = parent
        for child in self.children:
            child.deepcopy(result)
        return result

    def __deepcopy__(self, memo):
        raise make_exception(pysros_err_use_deepcopy)

    def __eq__(self, other):
        return self._data is other._data

def new_Model_data(name: Identifier, data_def_stm: Model.StatementType, parent):
    return (parent._storage if parent is not None else []), [
        [None, name] if type(name) == str else [name.prefix, name.name],        # 0 = name
        [],                                                                     # 1 = children
        None,                                                                   # 2 = yang_type
        [],                                                                     # 3 = local_keys
        None,                                                                   # 4 = target_path
        None if data_def_stm != Model.StatementType.identity_ else [],          # 5 = identity_bases
        parent if parent is None else parent._index,                            # 6 = parent
        data_def_stm.value | Model.DataBitmask.config,                          # 7 = bitmask
    ]
