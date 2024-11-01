from .model_path import ModelPath
from .identifier import Identifier
from .singleton import _Singleton
from .model_walker import ModelWalker

import re
import functools
import contextlib
from typing import Optional, List, Iterable, Tuple, Dict, Union

class LevelUp(metaclass=_Singleton):
    def __str__(self):
        return f"{self.__class__.__name__}()"

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other


class _Path:
    def __init__(self):
        self._path: List[Identifier] = []
        self._keys: List[Dict[Identifier, Union[str, _Path]]] = []
        self.default_module = None

    def append(self, i: Identifier):
        self._path.append(i)
        self._keys.append({})

    def append_level_up(self):
        self.append(LevelUp())

    def move_walker(self, w: ModelWalker, default_module=None):
        for name, keys in zip(self._path, self._keys):
            if name is LevelUp():
                w.go_to_parent()
            elif name.is_lazy_bound():
                w.go_to_child(Identifier(default_module or w.current.prefix, name.name))
            else:
                w.go_to_child(name)
            if not w.is_root:
                w.local_keys.update(keys)

    @property
    def top_keys(self):
        return self._keys[-1]


class AbsolutePath(_Path):
    def move_walker(self, w: ModelWalker, *args, **kwargs):
        while not w.is_root:
            w.go_to_parent()
        super().move_walker(w, *args, **kwargs)


class RelativePath(_Path):
    pass

"""
leafref:
===================================================================
   leafref-specification =
                         ;; these stmts can appear in any order
                         path-stmt
                         [require-instance-stmt]

   path-stmt           = path-keyword sep path-arg-str stmtend

   path-arg-str        = < a string that matches the rule >
                         < path-arg >
===================================================================

augment:
===================================================================
   augment-arg-str     = < a string that matches the rule >
                         < augment-arg >

   augment-arg         = absolute-schema-nodeid
===================================================================

deviation:
===================================================================
   deviation-arg-str   = < a string that matches the rule >
                         < deviation-arg >

   deviation-arg       = absolute-schema-nodeid
===================================================================

uses:
===================================================================
   refine-arg-str      = < a string that matches the rule >
                         < refine-arg >

   refine-arg          = descendant-schema-nodeid

   uses-augment-arg-str = < a string that matches the rule >
                          < uses-augment-arg >

   uses-augment-arg    = descendant-schema-nodeid
===================================================================

json-instance-path:
===================================================================
   An "instance-identifier" value is encoded as a string that is
   analogical to the lexical representation in XML encoding; see
   Section 9.13.2 in [RFC7950].  However, the encoding of namespaces in
   instance-identifier values follows the rules stated in Section 4,
   namely:

   o  The leftmost (top-level) data node name is always in the
      namespace-qualified form.

   o  Any subsequent data node name is in the namespace-qualified form
      if the node is defined in a module other than its parent node, and
      the simple form is used otherwise.  This rule also holds for node
      names appearing in predicates.
===================================================================
"""

"""
path-arg:
  leafref

absolute-schema-nodeid:
  augment
  deviation

descendant-schema-nodeid:
  uses-refine
  uses-augment

json-instance-path:
  pysros
"""

"""
   path-arg            = absolute-path / relative-path

   absolute-path       = 1*("/" (node-identifier *path-predicate))

   relative-path       = 1*("../") descendant-path

   descendant-path     = node-identifier
                         [*path-predicate absolute-path]

   path-predicate      = "[" *WSP path-equality-expr *WSP "]"

   path-equality-expr  = node-identifier *WSP "=" *WSP path-key-expr

   path-key-expr       = current-function-invocation *WSP "/" *WSP
                         rel-path-keyexpr

   rel-path-keyexpr    = 1*(".." *WSP "/" *WSP)
                         *(node-identifier *WSP "/" *WSP)
                         node-identifier

   node-identifier     = [prefix ":"] identifier

   current-function-invocation = current-keyword *WSP "(" *WSP ")"

   current-keyword          = %s"current"

absolute-path:
    /a
    /a/b
    /prefix:a
    /a/b[key=current()/../c]
    /a/b[key=current()/../c][key2=current()/../c][key3=current()/../c]
    /a/b[prefix:key=current()/../c]
    /a/b[  prefix:key  =  current  (  )  /  ..  /  c]
    #not in grammar, but probably still correct
    /  a  /  b

relative-path:
    ../a
    ../a/b
    ../../../a/b
    ../prefix:a
    ../a/b[key=current()/../c]
    ../a/b[key=current()/../c][key2=current()/../c][key3=current()/../c]
    ../a/b[prefix:key=current()/../c]
    ..  /  a  /  b  [  prefix:key  =  current  (  )  /  ..  /  c]

"""

"""
   ;; Schema Node Identifiers

   schema-nodeid       = absolute-schema-nodeid /
                         descendant-schema-nodeid

   absolute-schema-nodeid = 1*("/" node-identifier)

   descendant-schema-nodeid =
                         node-identifier
                         [absolute-schema-nodeid]

   node-identifier     = [prefix ":"] identifier

absolute-schema-nodeid:
    /a
    /a/b/c
    /prefix:a

descendant-schema-nodeid:
    a
    a/b/c
    prefix:a
"""

"""
   ;; Instance Identifiers

   instance-identifier = 1*("/" (node-identifier
                                 [1*key-predicate /
                                  leaf-list-predicate /
                                  pos]))

   key-predicate       = "[" *WSP key-predicate-expr *WSP "]"

   key-predicate-expr  = node-identifier *WSP "=" *WSP quoted-string

   leaf-list-predicate = "[" *WSP leaf-list-predicate-expr *WSP "]"

   leaf-list-predicate-expr = "." *WSP "=" *WSP quoted-string

   pos                 = "[" *WSP positive-integer-value *WSP "]"

   quoted-string       = (DQUOTE string DQUOTE) / (SQUOTE string SQUOTE)

   node-identifier     = [prefix ":"] identifier

Instance Identifiers:
    /ex:system/ex:services/ex:ssh
    /ex:system/ex:services/ex:ssh/ex:port
    /ex:system/ex:user[ex:name='fred']
    /ex:system/ex:user[ex:name='fred']/ex:type
    /ex:system/ex:server[ex:ip='192.0.2.1'][ex:port='80']
    /ex:system/ex:service[ex:name='foo'][ex:enabled='']
    /ex:system/ex:services/ex:ssh/ex:cipher[.='blowfish-cbc']
    /ex:stats/ex:port[3]
    /   ex:stats   /   ex:port   [   3   ]

Json instance identifier:
    /mod:system/services/ssh
    /mod:system/user[name='fred']
    /mod:system/services/mod2:ssh

Pysros instance identifier:
    /system/services/ssh
    /system/user[name='fred']
    /system/services/ssh
"""

SLASH_RE = r'\s*(?P<SLASH>[/])\s*'
BRACKET_OPEN_RE = r'\s*(?P<BRACKET_OPEN>\[)\s*'
BRACKET_CLOSE_RE = r'\s*(?P<BRACKET_CLOSE>\])\s*'
EQ_RE = r'\s*(?P<EQ>=)\s*'
_NAME_RE = r"""[a-zA-Z_][a-zA-Z0-9_.-]*"""
NAME_RE = fr"""(?P<NAME>{_NAME_RE})"""
IDENTIFIER_RE = fr"""(?P<IDENTIFIER>{_NAME_RE}:{_NAME_RE})"""
CURRENT_NODE_RE = r"(?P<CURRENT_NODE>[.])"
PARENT_NODE_RE = r"(?P<PARENT_NODE>[.][.])"
QUOTED_STR_RE = r"""(?P<QUOTED_STR>(?:["](?:[^\\"]|[\\][\\nt"])*["])|(?:['](?:[^'])*[']))"""
CURRENT_FNC_RE = r"\s*(?P<CURRENT_FNC>current\s*[(]\s*[)])\s*"


class Tokenizer:
    def __init__(self, s: str):
        self.s = s
        self.pos = 0
        self.current_match = None

    def consume(self, regex: Iterable[str]):
        if self.finished:
            return False
        r = re.compile(fr"(?:{'|'.join(regex)})")
        self.current_match = r.match(self.s, self.pos)
        if self.current_match is None:
            return False
        self.pos = self.current_match.end()
        return True

    def match(self, regex: Iterable[str]):
        if self.finished:
            return False
        r = re.compile(fr"(?:{'|'.join(regex)})")
        match = r.match(self.s, self.pos)
        if match is None:
            return False
        return True

    @property
    def kind(self):
        return self.current_match.lastgroup

    @property
    def token(self):
        return self.current_match.group(self.current_match.lastindex)

    @property
    def finished(self):
        return self.pos >= len(self.s)


_ = (SLASH_RE, BRACKET_OPEN_RE, BRACKET_CLOSE_RE, EQ_RE, CURRENT_FNC_RE, PARENT_NODE_RE, CURRENT_NODE_RE, IDENTIFIER_RE, NAME_RE, QUOTED_STR_RE, )

"""
    absolute_path
        path_segment+

    relative_path
        (PARENT_NODE / SLASH) * / ( node_segment / absolute_path ? ) ?

    node
        (NAME|IDENTIFIER)
    path_segment
        SLASH / node_segment
    node_segment
        node / [ key_segment* ]
        node /* for schema node id */
    key_segment
        BRACKET_OPEN / node / EQ / path_key_val / BRACKET_CLOSE
    path_key_val
        CURRENT_FNC / SLASH /relative_path
        QUOTED_STR /* for json instance path */

"""


class Parser:
    def __init__(self, s: str, *, key_allowed, absolute_path_allowed, relative_path_allowed, prefix_resolver=None, key_expect_path=None):
        assert key_expect_path is not None or not key_allowed
        self.tokenizer = Tokenizer(s)
        self.key_allowed = key_allowed
        self.absolute_path_allowed = absolute_path_allowed
        self.relative_path_allowed = relative_path_allowed
        self.key_expect_path = key_expect_path
        if prefix_resolver is not None:
            self.prefix_identifier_resolver = prefix_resolver
        else:
            self.prefix_identifier_resolver = lambda x: x

    def parse(self):
        if self.peek_slash():
            self.path = AbsolutePath()
            assert self.absolute_path_allowed
        else:
            self.path = RelativePath()
            assert self.relative_path_allowed
            while self.try_levelup():
                if not self.tokenizer.finished:
                    self.slash()
                    assert not self.tokenizer.finished
                self.path.append_level_up()

            if not self.tokenizer.finished:
                component = self.identifier_with_keys()
                self.path.append(component[0])
                for name, val in component[1]:
                    self.path.top_keys[name] = val

        while not self.tokenizer.finished:
            component = self.path_component()
            self.path.append(component[0])
            for name, val in component[1]:
                self.path.top_keys[name] = val

    def try_levelup(self):
        return self.tokenizer.consume((PARENT_NODE_RE, ))

    def peek_slash(self):
        return self.tokenizer.match((SLASH_RE, ))

    def try_slash(self):
        return self.tokenizer.consume((SLASH_RE, ))

    def peek_bracket_open(self):
        return self.tokenizer.match((BRACKET_OPEN_RE, ))

    def slash(self):
        assert self.tokenizer.consume((SLASH_RE, ))
        assert self.tokenizer.kind == "SLASH"

    def path_component(self) -> Tuple[Identifier, List[Tuple[Identifier, str]]]:
        self.slash()
        return self.identifier_with_keys()

    def key_segment(self) -> Tuple[Identifier, str]:
        assert self.tokenizer.consume((BRACKET_OPEN_RE, ))
        name = self.identifier()
        assert self.tokenizer.consume((EQ_RE, ))
        if self.key_expect_path:
            val = self.leaflist_pathj_key()
        else:
            val = self.quoted_str()
        assert self.tokenizer.consume((BRACKET_CLOSE_RE, ))
        return (name, val, )

    def leaflist_pathj_key(self):
        res = RelativePath()
        self.current_fnc()

        while self.try_slash():
            if self.try_levelup():
                res.append_level_up()
            else:
                res.append(self.identifier())

    def identifier_with_keys(self) -> Tuple[Identifier, List[Tuple[Identifier, str]]]:
        identifier = self.identifier()
        keys = []
        if self.key_allowed:
            while self.peek_bracket_open():
                keys.append(self.key_segment())
        return (identifier, keys, )

    def identifier(self) -> Identifier:
        assert self.tokenizer.consume((IDENTIFIER_RE, NAME_RE, ))
        name = self.tokenizer.token
        if self.tokenizer.kind == "IDENTIFIER":
            prefix, name = name.split(":")
            return Identifier(self.prefix_identifier_resolver(prefix), name)
        return Identifier.lazy_bound(name)

    def quoted_str(self):
        assert self.tokenizer.consume((QUOTED_STR_RE, ))
        return self.tokenizer.token[1:-1]

    def current_fnc(self):
        assert self.tokenizer.consume((CURRENT_FNC_RE, ))
        assert self.tokenizer.kind == "CURRENT_FNC"


def parse(w: ModelWalker, *args, **kwargs):
    get_path(*args, **kwargs).move_walker(w)


@functools.wraps(Parser)
def get_path(*args, default_module=None, **kwargs):
    parser = Parser(*args, **kwargs)
    parser.parse()
    res = parser.path
    if default_module:
        res.default_module = default_module
    return res
