# Copyright 2021 Nokia

import re

from .errors import *
from .wrappers import _Singleton

class LazyBindModule(metaclass=_Singleton):
    def __str__(self):
        return f"{self.__class__.__name__}()"

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

class NoModule(metaclass=_Singleton):
    def __str__(self):
        return f"{self.__class__.__name__}()"

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

class Identifier:
    """Class to hold prefix-name pair for single YANG entry"""
    __slots__ = "_name", "_prefix"

    def __init__(self, module, name: str):
        assert ':' not in name
        if isinstance(module, str):
            assert':' not in module
        self._name = name
        self._prefix = module

    @staticmethod
    def lazy_bound(name: str):
        return Identifier(LazyBindModule(), name)

    @staticmethod
    def builtin(name: str):
        return Identifier(NoModule(), name)

    def is_builtin(self):
        return self._prefix is NoModule()


    def is_lazy_bound(self):
        return self._prefix is LazyBindModule()

    @staticmethod
    def from_yang_string(s:str, default_module, prefix_module_mapping:dict):
        if ":" not in s:
            return Identifier(default_module, s)
        if s.count(":") != 1:
            raise make_exception(pysros_err_can_have_one_semicolon)
        prefix, name = s.split(":")
        if prefix not in prefix_module_mapping:
            raise make_exception(pysros_err_unknown_prefix_for_name, prefix=prefix, name=name)
        return Identifier(prefix_module_mapping[prefix], name)

    @staticmethod
    def from_model_string(s:str):
        if ":" not in s:
            return Identifier.lazy_bound(s)
        if s.count(":") != 1:
            raise make_exception(pysros_err_can_have_one_semicolon)
        return Identifier(*s.split(":"))

    def __hash__(self):
        return hash((self.prefix, self.name))

    def __str__(self):
        return  f"""{(str(self.prefix)+":") if self.prefix != NoModule() else ""}{self.name}"""

    def __repr__(self):
        if self.prefix is NoModule():
            return f"""Identifier.builtin({self.name!r})"""
        if self.prefix is LazyBindModule():
            return f"""Identifier.lazy_bound({self.name!r})"""
        return f"""Identifier({self.prefix!r}, {self.name!r})"""

    def __eq__(self, other):
        if type(other) is Identifier:
            return self._name == other._name and self._prefix == other._prefix
        elif type(other) == str:
            if ":" in other:
                return self == Identifier.from_model_string(other)
            return self.name == other
        return False

    def __ne__(self, other):
        return not(self == other)

    _IDENTIFIER_RE = re.compile(r'[a-zA-Z_][a-zA-Z0-9_\-.]*')
    def is_valid(self) -> bool:
        def valid_identifier(x):
            return bool(Identifier._IDENTIFIER_RE.fullmatch(x))
        return (valid_identifier(self._name) and
                (self._prefix is LazyBindModule()
                or self._prefix is NoModule()
                or valid_identifier(self._prefix)))

    @property
    def prefix(self):
        return self._prefix

    @property
    def name(self):
        return self._name

    @property
    def model_string(self):
        return f"{self.prefix+':' if self.prefix else ''}{self.name}"

