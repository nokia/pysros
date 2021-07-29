# Copyright 2021 Nokia

import copy
import xml.parsers.expat

from collections import defaultdict
from typing import Dict, DefaultDict, List, Set

from .errors import *
from .identifier import Identifier, NoModule, LazyBindModule
from .model import Model
from .model_path import ModelPath
from .model_walker import ModelWalker, DataModelWalker
from .tokenizer import yang_parser
from .yang_type import IdentityRef, LeafRef, UnresolvedIdentifier, YangUnion, Enumeration, Bits, resolve_typedefs_deep, should_be_buildin, type_from_name

class YangHandler:
    """Handler for yang processing."""
    TAGS_WITH_MODEL = ("container", "list", "leaf", "typedef", "module", "submodule", "uses", "leaf-list", "import", "identity", "notification", "rpc", "input", "output", "choice", "case", "deviate")
    TAGS_FORCE_MODULE = ("grouping", "identity", "typedef", "uses", "augment", "deviation", "type", "base")
    TAGS_ARG_IS_IDENTIFIER = ("base", "type", )
    TAGS_ARG_IS_YANG_PATH_NOT_ABSOLUTE_SCHEMA_ID = ("path", )
    assert not ({"config", "default", "mandatory", "max-elements", "min-elements", "must", "type", "unique", "units", } & set(TAGS_WITH_MODEL)), "Substmt of deviate can not have model"
    TAGS_SHOULD_BE_PROCESSED = (
        "action",
        "anydata",
        "anyxml",
        "argument",
        "augment",
        "base",
        "belongs-to",
        "bit",
        "case",
        "choice",
        "config",
        "contact",
        "container",
        "default",
        "description",
        "deviate",
        "deviation",
        "enum",
#        "error-app-tag",
#        "error-message",
#        "extension",
        "feature",
        "fraction-digits",
        "grouping",
        "identity",
        "if-feature",
        "import",
        "include",
        "input",
        "key",
        "leaf",
        "leaf-list",
        "length",
        "list",
        "mandatory",
        "max-elements",
        "min-elements",
        "modifier",
        "module",
        "must",
        "namespace",
        "notification",
        "ordered-by",
        "organization",
        "output",
        "path",
        "pattern",
        "position",
        "prefix",
        "presence",
        "range",
        "reference",
        "refine",
        "require-instance",
        "revision",
        "revision-date",
        "rpc",
        "status",
        "submodule",
        "type",
        "typedef",
        "unique",
        "units",
        "uses",
        "value",
#        "when",
        "yang-version",
        "yin-element",
    )

    def __init__(self, builder: "ModelBuilder", root: Model):
        self.builder = builder
        self.root = root
        self.path = [root]
        self.full_path = []
        self.grouping_depth = 0
        self.in_type = 0
        self.derived_identities: Dict[Identifier, Set(Identifier)] = {}
        self.include_stack = [{}]
        self.module = None
        self.prefix = None
        self.ignore_depth = 0

    def enter(self, name, arg, filename, lineno):
        if self.ignore_depth or name not in self.TAGS_SHOULD_BE_PROCESSED:
            self.ignore_depth += 1
            return
        self.full_path.append(name)

        if name in ("input", "output"):
            arg = name
        if name == "case" and not arg:
            arg = "unnamed"
        if name == 'typedef':
            new_id = self.get_identifier(arg, name in self.TAGS_FORCE_MODULE)
            assert not new_id.is_lazy_bound()
            new = Model(new_id, Model.StatementType.typedef_, None, filename, lineno)
            self.path.append(new)
        elif name in self.TAGS_WITH_MODEL:
            new_id = self.get_identifier(arg, name in self.TAGS_FORCE_MODULE)
            new = Model(new_id, Model.StatementType[name.replace("-", "_") + "_"], self.model, filename, lineno)
            self.path.append(new)
        elif name in ("augment", "deviation"):
            new_id = self.get_identifier(name, name in self.TAGS_FORCE_MODULE)
            new = Model(new_id, Model.StatementType[name + "_"], None, filename, lineno)
            new.target_path = self.yang_path_to_model_path(arg)
            (self.builder.augments if name == "augment" else self.builder.deviations).append(new)
            self.path.append(new)
        elif name == "grouping":
            new_id = self.get_identifier(arg, name in self.TAGS_FORCE_MODULE)
            new = Model(new_id, Model.StatementType[name.replace("-", "_") + "_"], None, filename, lineno)
            self.path.append(new)
            assert new_id not in self.builder.groupings
            self.builder.groupings[new_id] = new
        else:
            if name in self.TAGS_ARG_IS_IDENTIFIER:
                if name == "type" and should_be_buildin(arg):
                    arg = Identifier.builtin(arg)
                else:
                    arg = self.get_identifier(arg, name in self.TAGS_FORCE_MODULE)
            elif name in self.TAGS_ARG_IS_YANG_PATH_NOT_ABSOLUTE_SCHEMA_ID:
                arg = self.yang_path_to_model_path(arg, absolute_schema_id = False)
            self.model.blueprint.append((True, (name, arg, filename, lineno)))

        handle_name = f'handle_early_{name.replace("-", "_DASH_")}'
        if hasattr(self, handle_name):
            handler = getattr(self, handle_name)
            handler(arg)

    def leave(self, name):
        if self.ignore_depth:
            self.ignore_depth -= 1
            return
        if name == "grouping":
            self.grouping_depth -= 1
        elif name == "typedef":
            self.construct(self.model)
            self.builder.types_to_resolve[self.model.name] = self.model.yang_type
        elif name in ("action", "rpc"):
            for child in self.model.children:
                if child.data_def_stm == Model.StatementType.input_:
                    break
            else:
                self.enter("input", None, self.model.filename, self.model.lineno)
                self.leave("input")
            for child in self.model.children:
                if child.data_def_stm == Model.StatementType.output_:
                    break
            else:
                self.enter("output", None, self.model.filename, self.model.lineno)
                self.leave("output")

        popped = self.full_path.pop()
        assert popped == name
        if name in (*self.TAGS_WITH_MODEL, "grouping", "augment", "deviation"):
            self.path.pop()
        else:
            self.model.blueprint.append((False, name))

    def construct(self, model=None):
        model = model or self.root
        self.path.append(model)
        self.full_path.append(model.data_def_stm.name.replace("_", "-")[:-1])
        for instruction in model.blueprint:
            if instruction[0]:
                self.full_path.append(instruction[1][0])
                if self.full_path[-1] == "type":
                    self.in_type += 1
                self.construct_enter(instruction[1])
            else:
                if self.full_path.pop() == "type":
                    self.in_type -= 1
        for child in self.model.children:
            self.construct(child)
        self.path.pop()
        self.full_path.pop()

    def construct_enter(self, instruction):
        name, arg, filename, lineno = instruction
        handle_name = f'handle_{name.replace("-", "_DASH_")}'
        if hasattr(self, handle_name):
            handler = getattr(self, handle_name)
            handler(arg)

    def get_identifier(self, s, force_module=False):
        if self.module is not None:
            module = LazyBindModule() if (self.grouping_depth and not force_module) else self.module
            return Identifier.from_yang_string(s, module, self.prefixModuleMapping)
        return Identifier.builtin(s)

    @staticmethod
    def model_path_from_string(path: str, default_module: str, prefixModuleMapping: Dict[str, str], *,  absolute_schema_id):
        assert isinstance(path, str)
        if not path.startswith(('/', '../')):
            raise make_exception(pysros_err_cannot_pars_path, path=path)

        tokens = ModelWalker.tokenize_path(path, absolute_schema_id)
        result = ModelPath(Identifier.from_yang_string(
            p, default_module, prefixModuleMapping) for p in tokens)
        if not result.is_valid(only_absolute_path=absolute_schema_id):
            raise make_exception(pysros_err_invalid_yang_path, path=path)
        return result

    def yang_path_to_model_path(self, path, absolute_schema_id=True):
        default_module = self.module if absolute_schema_id else LazyBindModule()
        return self.model_path_from_string(path, default_module, self.prefixModuleMapping, absolute_schema_id=absolute_schema_id)

    @property
    def model(self):
        return self.path[-1]

    @property
    def model_type(self):
        return self.model.data_def_stm

    @property
    def prefixModuleMapping(self):
        return self.include_stack[-1]

    @property
    def last_yang_type(self):
        return self.model.yang_type[-1] if isinstance(self.model.yang_type, YangUnion) else self.model.yang_type

    def handle_identity(self, identifier):
        assert self.model.data_def_stm == Model.StatementType.identity_

    def handle_base(self, ident):
        if self.in_type:
            assert isinstance(self.last_yang_type, IdentityRef)
            self.last_yang_type.add_base(ident)
        elif self.model.data_def_stm == Model.StatementType.identity_:
            self.model.identity_bases.append(ident)

    def handle_path(self, arg: str):
        if self.in_type:
            assert isinstance(self.last_yang_type, LeafRef)
            self.last_yang_type.set_path(arg)

    def handle_type(self, identifier: str):
        if isinstance(self.model.yang_type, YangUnion):
            self.model.yang_type.append(type_from_name(identifier))
        else:
            assert self.model.yang_type is None
            self.model.yang_type = type_from_name(identifier)

    def handle_enum(self, value: str):
        if self.in_type:
            assert isinstance(self.last_yang_type, Enumeration), f"expected Enumeration, got {self.last_yang_type}"
            self.last_yang_type.add_enum(value)

    def handle_bit(self, value: str):
        if self.in_type:
            assert isinstance(self.last_yang_type, Bits)
            self.last_yang_type.add(value)

    def handle_value(self, value: str):
        if self.in_type:
            assert isinstance(self.last_yang_type, Enumeration)
            self.last_yang_type.set_last_enum_value(int(value))

    def handle_presence(self, _arg):
        self.model.presence_container = True

    def handle_ordered_DASH_by(self, arg):
        if arg == "user":
            self.model.user_ordered = True

    def handle_early_import(self, arg):
        self.builder.register_yang(arg)

    def handle_early_include(self, arg):
        self.include_stack.append({})
        self.builder.perform_parse(arg, self)
        self.include_stack.pop()

    def handle_key(self, arg):
        self.model.local_keys.extend(arg.split())

    def handle_early_module(self, arg):
        self.module = arg

    def handle_early_grouping(self, _arg):
        self.grouping_depth += 1

    def handle_early_prefix(self, arg):
        if self.full_path[-2] == "module":
            self.prefix = arg
        if self.full_path[-2] in ("import", "module"):
            assert arg not in self.prefixModuleMapping
            self.prefixModuleMapping[arg] = self.model.name.name

    def handle_config(self, arg: str):
        if arg not in ('false', 'true'):
            raise make_exception(pysros_err_invalid_config)
        self.model.config = (arg == 'true')

def _dummy_getter(filename):
    assert False, "Missing getter"

class ModelBuilder:
    """API for walking model tree."""
    def __init__(self, yang_getter=_dummy_getter):
        self.root = Model("root", Model.StatementType["container_"], None, 'root', -1)
        self.types_to_resolve = dict()
        self.groupings = dict()
        self.resolved_types = dict()
        self.all_yangs = set()
        self.parsed_yangs = set()
        self.files_to_parse = []
        self.augments = []
        self.deviations = []
        self.registered_modules = {}
        self.yang_getter = yang_getter

    def get_module_content(self, yang_name):
        if yang_name in self.registered_modules:
            return self.registered_modules[yang_name]
        return self.yang_getter(yang_name)

    def register_yangs(self, yang_names):
        for name in yang_names:
            self.register_yang(name)

    def register_yang(self, yang_name):
        assert isinstance(yang_name, str)
        if yang_name not in self.all_yangs:
            self.all_yangs.add(yang_name)
            self.files_to_parse.append(yang_name)

    def DEBUG_parse_File(self, module_name, f):
        if module_name not in self.all_yangs:
            self.all_yangs.add(module_name)
            self.parsed_yangs.add(module_name)
        yang_parser(f, YangHandler(self, self.root), module_name)

    def DEBUG_register_module(self, module_name, f):
        assert module_name not in self.registered_modules
        self.registered_modules[module_name] = f

    def process_all_yangs(self):
        while self.files_to_parse:
            self.perform_parse(self.files_to_parse.pop())
        self.resolve()

    def resolve(self):
        self.resolve_groupings()
        self.resolve_augments()
        self.resolve_deviations()
        self.build_blueprints()
        self.resolve_typedefs()
        self.resolve_identities()
        self.resolve_leafrefs()
        self.resolve_config()

    def perform_parse(self, yang_name, yang_handler=None):
        if yang_name in self.parsed_yangs:
            return
        self.parsed_yangs.add(yang_name)

        yang_parser(self.get_module_content(yang_name), yang_handler or YangHandler(self, self.root), yang_name)


    def add_child_to_uses(self, m: Model):
        if m.data_def_stm == Model.StatementType.uses_:
            assert not m.children
            i = m
            while True:
                if i.data_def_stm == Model.StatementType.module_:
                    module = i.name.name
                    break
                elif i.data_def_stm == Model.StatementType.augment_:
                    module = i.name.prefix
                    break
                i = i.parent

            def resolve_unresolved(m:Model):
                if m.name.prefix is LazyBindModule():
                    m.name._prefix = module

            m.children = [i.deepcopy(m) for i in self.groupings[m.name].children]
            m.recursive_walk(resolve_unresolved)
            return False

    def set_correct_types(self, m:Model):
        if m.yang_type is None:
            return

        if isinstance(m.yang_type, UnresolvedIdentifier):
            m.yang_type = copy.deepcopy(resolve_typedefs_deep(m.yang_type, self.resolved_types))

        if isinstance(m.yang_type, YangUnion):
            m.yang_type = copy.deepcopy(resolve_typedefs_deep(m.yang_type, self.resolved_types))

    def resolve_typedefs(self):
        for name, value in self.types_to_resolve.items():
            assert not name in self.resolved_types
            self.resolved_types[name] = resolve_typedefs_deep(value, self.types_to_resolve)
        self.root.recursive_walk(self.set_correct_types)

    def resolve_identities(self):
        # first step creates dict, where we find for each identity
        # its all identities, that are directly derived from it.
        directly_derived: DefaultDict[Identifier, List[Identifier]] = defaultdict(list)
        def find_derived(m:Model):
            if m.data_def_stm != Model.StatementType.identity_:
                return
            for b in m.identity_bases:
                directly_derived[b].append(m.name)

        self.root.recursive_walk(find_derived)
        # second step adds all direct and indirect derived identities together
        def add_derived_recursive(result_set, id):
            if id in result_set:
                return
            result_set.update(directly_derived.get(id, []))
            for c in directly_derived.get(id, []):
                add_derived_recursive(result_set, c)

        derived: Dict[Identifier, Set(Identifier)] = {}
        for id in directly_derived.keys():
            derived[id] = set()
            add_derived_recursive(derived[id], id)

        # last step iterates through all identityrefs and set possible values
        def identityref_set_value(m:Model):
            if m.yang_type is None:
                return
            if type(m.yang_type) is IdentityRef:
                m.yang_type.set_values(derived)
            elif type(m.yang_type) is YangUnion:
                for st in m.yang_type:
                    if type(st) is IdentityRef:
                        st.set_values(derived)

        self.root.recursive_walk(identityref_set_value)

    def resolve_leafrefs(self):
        def replace_leafrefs(m: Model):
            if not isinstance(m.yang_type, LeafRef):
                return

            w = DataModelWalker(m)
            assert m.data_def_stm in (Model.StatementType.leaf_, Model.StatementType.leaf_list_)

            while isinstance(w.current.yang_type, LeafRef):
                path = w.current.yang_type.path
                module_name = w.current.name.prefix
                if path._path and path._path[0].name != '..':
                    # absolute path - go to root
                    while not w.is_root:
                        w.go_to_parent()
                w.go_to(path, module_name)
            m.yang_type = w.current.yang_type
        self.root.recursive_walk(replace_leafrefs)

    def resolve_groupings(self):
        def inner(m:Model):
            if m.data_def_stm == Model.StatementType.uses_:
                assert not m.children
                m.children = self.groupings[m.name].children
                return False
        for grouping in self.groupings.values():
            grouping.recursive_walk(inner)
        self.root.recursive_walk(self.add_child_to_uses)
        for augment in self.augments:
            augment.recursive_walk(self.add_child_to_uses)

    def process_augment(self, m:Model):
        if m.data_def_stm == Model.StatementType.augment_:
            w = ModelWalker.path_parse(self.root, m.target_path)
            w.current.children.extend(i.deepcopy(w.current) for i in m.children)

    def resolve_augments(self):
        current = self.augments
        while current:
            remaining = []
            for augment in current:
                w = ModelWalker(self.root)
                try:
                    w.go_to(augment.target_path)
                    node = w.current
                except InvalidPathError as e:
                    remaining.append(augment)
                    continue
                node.children.extend(i.deepcopy(node) for i in augment.children)
            if len(remaining) >= len(current):
                raise make_exception(pysros_err_unresolved_augment)
            current = remaining

    def filter_blueprint(self, function, blueprint):
        filtering_depth = 0
        for instruction in blueprint:
            if filtering_depth:
                filtering_depth += 1 if instruction[0] else -1
                continue
            if instruction[0]:
                if function(instruction[1]):
                    yield instruction
                else:
                    filtering_depth = 1
            else:
                yield instruction

    def resolve_deviations(self):
        for deviation in self.deviations:
            w = ModelWalker(self.root)
            w.go_to(deviation.target_path)
            for deviate in deviation.children:
                if deviate.name.name == "add":
                    w.current.blueprint.extend(deviate.blueprint)
                if deviate.name.name == "delete":
                    for instruction in deviate.blueprint:
                        if instruction[0]:
                            w.current.blueprint = list(self.filter_blueprint(lambda b: b[0:1] != instruction[1][0:1], w.current.blueprint))
                if deviate.name.name == "replace":
                    depth = 0
                    for instruction in deviate.blueprint:
                        if not depth:
                            w.current.blueprint = list(self.filter_blueprint(lambda b: b[0] != instruction[1][0], w.current.blueprint))
                        depth += 1 if instruction[0] else -1
                    w.current.blueprint = list(w.current.blueprint) + deviate.blueprint
                if deviate.name.name == "not-supported":
                    idx = w.current.parent.children.index(w.current)
                    if idx < 0:
                        raise make_exception(pysros_err_cannot_remove_node, node=w.current.name)
                    del w.current.parent.children[idx]
                    w.current.parent = None

    def build_blueprints(self):
        handler = YangHandler(self, self.root)
        handler.construct()

    def resolve_config(self):
        def set_config(m: Model, value: bool):
            if m.config is None:
                m.config = value
            elif  m.config is True and value is False:
                # RFC 7950: If a node has "config" set to "false", no node underneath it can have
                # "config" set to "true".
                raise make_exception(pysros_err_invalid_config)

            for c in m.children:
                set_config(c, m.config)
        set_config(self.root, True)
