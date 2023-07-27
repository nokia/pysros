# Copyright 2021-2023 Nokia

import copy
import locale
import sys

from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

from lxml import etree

from .errors import *
from .identifier import Identifier, NoModule
from .identifier import Identifier, NoModule
from .yang_type import Enumeration, YangType, YangTypeBase
from .yang_type import YangType

class Model:
    """Class to represent a single YANG entry and hold additional information, such as type, configuration state, children, and data definition statement.

    .. Reviewed by TechComms 20210713
    """
    class StatementType(Enum):
        leaf_         = auto()
        list_         = auto()
        container_    = auto()
        leaf_list_    = auto()
        choice_       = auto()
        case_         = auto()
        augment_      = auto()
        uses_         = auto()
        typedef_      = auto()
        module_       = auto()
        submodule_    = auto()
        grouping_     = auto()
        import_       = auto()
        identity_     = auto()
        action_       = auto()
        anydata_      = auto()
        anyxml_       = auto()
        notification_ = auto()
        rpc_          = auto()
        input_        = auto()
        output_       = auto()
        deviation_    = auto()
        deviate_      = auto()

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
        "parent",
        "filename",
        "lineno",
        "config",
        "blueprint",
    )

    def __init__(self, name: Identifier, data_def_stm: StatementType, parent, filename: str, lineno: int = -1):
        self.name = Identifier.builtin(name) if type(name) == str else name
        self.children: List[Model] = []
        self.yang_type: Optional[YangType] = None
        self.presence_container = False
        self.user_ordered = False
        self.local_keys: List[str] = []
        self.data_def_stm = data_def_stm
        self.target_path = None
        if parent:
            parent.children.append(self)
        self.parent = parent
        self.filename = filename
        self.lineno = lineno
        assert isinstance(lineno, int)
        self.identity_bases = None if data_def_stm != Model.StatementType.identity_ else []
        self.config: Optional[bool] = None
        self.blueprint = []

    def pos(self):
        if self.lineno is None:
            return f"{self.filename}"
        return f"{self.filename}:{self.lineno}"

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

        print(f"""{prefix[:-1]}{field_prefix}{self.debug_flags()} {self.name} [{" ".join((t,*t_sufix))}] ({self.pos()})""")

        remain = len(self.children) - 1
        for i in self.children:
            new_prefix = prefix + ("    " if not remain else AsciiArt.VERTICAL_LINE)
            if not prefix:
                new_prefix = new_prefix[3:]
            i.debug_print(new_prefix, not remain)
            remain -= 1

    def  debug_flags(self) -> str:
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

        remain = len(self.children) - 1
        for i in sorted(self.children, key=lambda o: (str(o.name.prefix), o.name.name)):
            new_prefix = prefix + ("    " if not remain else "   |")
            if not prefix:
                new_prefix = new_prefix[3:]
            res += i.test_print(new_prefix, not remain)
            remain -= 1
        return res

    def recursive_walk(self, cb):
        cont = cb(self)
        if cont == False:
            return
        for i in self.children:
            i.recursive_walk(cb)

    def sanity_parent_child_test(self):
        for i in self.children:
            assert self is i.parent
            i.sanity_parent_child_test()

    def __str__(self):
        return f"""Model("{str(self.name)}")"""

    def __repr__(self):
        return f"""Model("{str(self.name)}")"""

    def deepcopy(self, parent):
        cls = self.__class__
        result = cls.__new__(cls)
        for i in self.__slots__:
            if i in ("parent", "children"):
                continue
            setattr(result, i, copy.deepcopy(getattr(self, i)))
        result.parent = parent
        result.children = [i.deepcopy(result) for i in self.children]
        return result

    def __deepcopy__(self, memo):
        raise make_exception(pysros_err_use_deepcopy)

    def __getstate__(self):
        return {i: getattr(self, i) for i in self.__slots__}

    def __setstate__(self, state:dict):
        for k, v in state.items():
            setattr(self, k, v)
