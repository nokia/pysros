# Copyright 2021-2023 Nokia

import copy
from collections import defaultdict
from itertools import chain
from typing import DefaultDict, Dict, Optional, Set, Union

from .errors import *
from .errors import InvalidPathError, make_exception
from .identifier import Identifier, LazyBindModule
from .model import AModel, BuildingModel, Model, StorageConstructionModel
from .model_path import ModelPath
from .model_walker import DataModelWalker, ModelWalker
from .request_data import COMMON_NAMESPACES
from .tokenizer import yang_parser
from .yang_type import (DECIMAL_LEAF_TYPE, INTEGRAL_TYPES_MAX,
                        INTEGRAL_TYPES_MIN, Bits, Enumeration,
                        IdentityRef, LeafRef, PrimitiveType,
                        UnresolvedIdentifier, YangType, YangTypeBase,
                        YangUnion, should_be_buildin, type_from_name)


class YangHandler:
    """Handler for yang processing."""
    TAGS_WITH_MODEL = (
        "container", "list", "leaf", "typedef", "module", "submodule", "uses",
        "leaf-list", "import", "identity", "notification", "rpc",
        "input", "output", "choice", "case", "deviate", "action"
    )
    TAGS_FORCE_MODULE = (
        "grouping", "identity", "typedef", "uses", "augment",
        "deviation", "type", "base"
    )
    TAGS_ARG_IS_IDENTIFIER = ("base", "type", )
    TAGS_ARG_IS_YANG_PATH_NOT_ABSOLUTE_SCHEMA_ID = ("path", )
    assert not ({
        "config", "default", "fraction-digits", "length", "mandatory",
        "max-elements", "min-elements", "must", "range", "status", "type",
        "unique", "units",
    } & set(TAGS_WITH_MODEL)), "Substmt of deviate can not have model"
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
        # "error-app-tag",
        # error-message",
        # extension",
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
        "md:annotation",
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
        # "when",
        "yang-version",
        "yin-element",
    )

    def __init__(self, builder: "ModelBuilder", root: BuildingModel):
        self.builder = builder
        self.root = root
        self.path = [root]
        self.full_path = []
        self.grouping_depth = 0
        self.in_type = 0
        self.derived_identities: Dict[Identifier, Set[Identifier]] = {}
        self.include_stack = [{}]
        self.module = None
        self.prefix = None
        self.ignore_depth = 0

    def enter(self, name, arg):
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
            new = BuildingModel(new_id, BuildingModel.StatementType.typedef_, None)
            self.path.append(new)
        elif name in self.TAGS_WITH_MODEL:
            new_id = self.get_identifier(arg, name in self.TAGS_FORCE_MODULE)
            new = BuildingModel(new_id, BuildingModel.StatementType[name.replace("-", "_") + "_"], self.model)
            self.path.append(new)
        elif name in ("augment", "deviation"):
            new_id = self.get_identifier(name, name in self.TAGS_FORCE_MODULE)
            new = BuildingModel(new_id, BuildingModel.StatementType[name + "_"], None)
            new.target_path = self.yang_path_to_model_path(arg)
            (self.builder.augments if name == "augment" else self.builder.deviations).append(new)
            self.path.append(new)
        elif name == "grouping":
            new_id = self.get_identifier(arg, name in self.TAGS_FORCE_MODULE)
            new = BuildingModel(new_id, BuildingModel.StatementType[name.replace("-", "_") + "_"], None)
            self.path.append(new)
            assert new_id not in self.builder.groupings
            self.builder.groupings[new_id] = new
        elif name == "md:annotation":
            new_id = self.get_identifier(arg, name in self.TAGS_FORCE_MODULE)
            new = BuildingModel(new_id, BuildingModel.StatementType.annotate_, None)
            self.path.append(new)
            self.builder.metadata.append(new)
        else:
            if name in self.TAGS_ARG_IS_IDENTIFIER:
                if name == "type" and should_be_buildin(arg):
                    arg = Identifier.builtin(arg)
                else:
                    arg = self.get_identifier(arg, name in self.TAGS_FORCE_MODULE)
            elif name in self.TAGS_ARG_IS_YANG_PATH_NOT_ABSOLUTE_SCHEMA_ID:
                arg = self.yang_path_to_model_path(arg, absolute_schema_id=False)
            self.model.blueprint.append((True, (name, arg)))

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
            self.builder.types_to_resolve[self.model.name] = TypeDefModel(self.model)
        elif name in ("action", "rpc"):
            for child in self.model.children:
                if child.data_def_stm == BuildingModel.StatementType.input_:
                    break
            else:
                self.enter("input", None)
                self.leave("input")
            for child in self.model.children:
                if child.data_def_stm == BuildingModel.StatementType.output_:
                    break
            else:
                self.enter("output", None)
                self.leave("output")

        popped = self.full_path.pop()
        assert popped == name
        if name in (*self.TAGS_WITH_MODEL, "grouping", "augment", "deviation", "md:annotation"):
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
        name, arg = instruction
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
        assert self.model.data_def_stm == BuildingModel.StatementType.identity_

    def handle_base(self, ident):
        if self.in_type:
            assert isinstance(self.last_yang_type, IdentityRef)
            self.last_yang_type.add_base(ident)
        elif self.model.data_def_stm == BuildingModel.StatementType.identity_:
            self.model.identity_bases.append(ident)

    def handle_path(self, arg: str):
        if self.in_type:
            assert isinstance(self.last_yang_type, LeafRef)
            self.last_yang_type.set_path(arg)

    def handle_type(self, identifier: str):
        if not isinstance(self.model.yang_type, YangUnion):
            assert self.model.yang_type is None
            self.model.yang_type = type_from_name(identifier)
        elif (identifier != Identifier.builtin('union')):
            self.model.yang_type.append(type_from_name(identifier))

    def handle_units(self, arg: str):
        assert self.model.units is None
        self.model.units = arg

    def handle_namespace(self, arg: str):
        assert self.model.namespace is None
        self.model.namespace = arg

    def handle_default(self, arg: str):
        assert self.model.default is None
        self.model.default = arg

    def handle_mandatory(self, arg: str):
        assert self.model.mandatory is None
        self.model.mandatory = arg

    def handle_range(self, arg: str):
        assert isinstance(self.last_yang_type, (PrimitiveType, UnresolvedIdentifier))
        assert self.last_yang_type.yang_range is None
        self.last_yang_type.yang_range = arg

    def handle_fraction_DASH_digits(self, arg: str):
        assert isinstance(self.last_yang_type, (PrimitiveType, UnresolvedIdentifier))
        assert self.last_yang_type.fraction_digits is None
        self.last_yang_type.fraction_digits = int(arg)

    def handle_length(self, arg: str):
        assert isinstance(self.last_yang_type, (PrimitiveType, UnresolvedIdentifier))
        assert self.last_yang_type.length is None
        self.last_yang_type.length = arg

    def handle_status(self, arg: str):
        self.model.status = arg

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
    def __init__(self, yang_getter=_dummy_getter, ns_map={}):
        self.root = BuildingModel(
            "root",
            BuildingModel.StatementType["container_"],
            None
        )
        self.metadata = []
        self.types_to_resolve = dict()
        self.groupings = dict()
        self.resolved_types = dict()
        self.all_yangs = set()
        self.parsed_yangs = set()
        self.files_to_parse = []
        self.augments = []
        self.deviations = []
        self.registered_modules = {}
        self._ns_map = ns_map
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
        yang_parser(f, YangHandler(self, self.root))

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
        self.resolve_type_ranges()
        self.resolve_identities()
        self.resolve_leafrefs()
        self.resolve_config()
        self.resolve_namespaces()
        self.delete_blueprints()
        self.resolve_metadata_exceptions()
        self.convert_model()

    def walk_models(self, cb):
        self.root.recursive_walk(cb)
        for a in self.metadata:
            a.recursive_walk(cb)

    def perform_parse(self, yang_name, yang_handler=None):
        if yang_name in self.parsed_yangs:
            return
        self.parsed_yangs.add(yang_name)

        yang_parser(
            self.get_module_content(yang_name),
            yang_handler or YangHandler(self, self.root)
        )

    def add_child_to_uses(self, m: BuildingModel):
        if m.data_def_stm == BuildingModel.StatementType.uses_:
            assert not m.has_children
            i = m
            while True:
                if i.data_def_stm == BuildingModel.StatementType.module_:
                    module = i.name.name
                    break
                elif i.data_def_stm == BuildingModel.StatementType.augment_:
                    module = i.name.prefix
                    break
                i = i.parent

            def resolve_unresolved(m: BuildingModel):
                if m.name.prefix is LazyBindModule():
                    m.prefix = module

            for i in self.groupings[m.name].children:
                i.deepcopy(m)
            m.recursive_walk(resolve_unresolved)
            return False

    def set_correct_types(self, m: BuildingModel):
        if isinstance(m.yang_type, (UnresolvedIdentifier, YangUnion)):
            tdm = resolve_typedefs_deep(TypeDefModel(m), self.resolved_types)
            m.yang_type = tdm.yang_type
            m.default = tdm.default
            m.units = tdm.units

    def resolve_typedefs(self):
        for key, value in self.types_to_resolve.items():
            assert key not in self.resolved_types
            self.resolved_types[key] = resolve_typedefs_deep(value, self.types_to_resolve)
        self.walk_models(self.set_correct_types)

    def set_correct_range(self, yt: YangTypeBase):
        assert yt.json_name() != "decimal64" or yt.fraction_digits
        if isinstance(yt, YangUnion):
            for t in yt:
                self.set_correct_range(t)

        if not yt or not yt.json_name() in (*DECIMAL_LEAF_TYPE, "string", "binary"):
            return
        if yt.json_name() in ("string", "binary") and not yt.length:
            return

        full_range = False if (yt.yang_range or yt.json_name() in ("string", "binary")) else True
        work_range = yt.length if yt.json_name() in ("string", "binary") else yt.yang_range

        if full_range:
            work_range = "min..max"
        if yt.json_name() == "decimal64":
            min_val = str(-2**63 + 1)
            max_val = str(2**63 - 1)
            min_val = min_val[:-yt.fraction_digits] + '.' + min_val[-yt.fraction_digits:]
            max_val = max_val[:-yt.fraction_digits] + '.' + max_val[-yt.fraction_digits:]
        elif yt.json_name() in ("string", "binary"):
            min_val = str(0)
            max_val = str(2**64 - 1)
        else:
            min_val = INTEGRAL_TYPES_MIN[yt.json_name()]
            max_val = INTEGRAL_TYPES_MAX[yt.json_name()]

        work_range = work_range.replace("min", min_val)
        work_range = work_range.replace("max", max_val)

        if full_range:
            yt.yang_range = work_range
            return

        # merge adjacent subranges, such as "0|1..100" to "0..100" or "0..10|11..20" to "0..20"
        def process_subrange(subrange: str):
            nonlocal yt
            map_f = float if yt.json_name() == "decimal64" else int
            i_subrange = list(map(map_f, subrange.split("..")))
            assert len(i_subrange) in (1, 2)
            return i_subrange if len(i_subrange) == 2 else 2 * i_subrange

        subranges = work_range.split("|")
        res_subranges = [process_subrange(subranges[0])]
        for subrange in subranges[1:]:
            i_subrange = process_subrange(subrange)
            if res_subranges[-1][1] == i_subrange[0] - 1:
                res_subranges[-1][1] = i_subrange[1]
            else:
                res_subranges.append(i_subrange)

        res_subranges = [subr if subr[0] != subr[1] else [subr[0]] for subr in res_subranges]
        work_range = "|".join(
            "..".join(map(str, subr)) for subr in res_subranges
        )
        if yt.json_name() in ("string", "binary"):
            yt.length = work_range
        else:
            yt.yang_range = work_range

    def resolve_type_ranges(self):
        def setter(m: BuildingModel):
            if isinstance(m.yang_type, YangTypeBase):
                self.set_correct_range(m.yang_type)
        self.walk_models(setter)

    def resolve_identities(self):
        # first step creates dict, where we find for each identity
        # its all identities, that are directly derived from it.
        directly_derived: DefaultDict[Identifier, Set[Identifier]] = defaultdict(set)

        def find_derived(m: BuildingModel):
            if m.data_def_stm != BuildingModel.StatementType.identity_:
                return
            for b in m.identity_bases:
                if m.status != 'obsolete':
                    directly_derived[b].add(m.name)

        self.walk_models(find_derived)
        # second step adds all direct and indirect derived identities together

        def add_derived_recursive(result_set, id):
            got = directly_derived.get(id, set())
            toUpdate = got - result_set
            result_set.update(got)
            for c in toUpdate:
                add_derived_recursive(result_set, c)

        derived: Dict[Identifier, Set(Identifier)] = {}
        for id in directly_derived.keys():
            derived[id] = set()
            add_derived_recursive(derived[id], id)

        # last step iterates through all identityrefs and set possible values
        def identityref_set_value(m: BuildingModel):
            if m.yang_type is None:
                return
            if type(m.yang_type) is IdentityRef:
                m.yang_type.set_values(derived, self._ns_map)
            elif type(m.yang_type) is YangUnion:
                for st in m.yang_type:
                    if type(st) is IdentityRef:
                        st.set_values(derived, self._ns_map)

        self.walk_models(identityref_set_value)

    def resolve_leafrefs(self):
        def replace_leafrefs(m: BuildingModel):
            if not isinstance(m.yang_type, LeafRef):
                return

            w = DataModelWalker(m)
            assert m.data_def_stm in (
                BuildingModel.StatementType.leaf_,
                BuildingModel.StatementType.leaf_list_
            )

            while isinstance(w.current.yang_type, LeafRef):
                path = w.current.yang_type.path
                module_name = w.current.name.prefix
                if path._path and path._path[0].name != '..':
                    # absolute path - go to root
                    while not w.is_root:
                        w.go_to_parent()
                w.go_to(path, module_name)
            m.yang_type = w.current.yang_type
        self.walk_models(replace_leafrefs)

    def resolve_groupings(self):
        def inner(m: BuildingModel):
            if m.data_def_stm == BuildingModel.StatementType.uses_:
                if m.has_children:
                    return False
                for child in self.groupings[m.name].children:
                    child.deepcopy(m)
        for grouping in self.groupings.values():
            grouping.recursive_walk(inner)
        self.root.recursive_walk(self.add_child_to_uses)
        for augment in self.augments:
            augment.recursive_walk(self.add_child_to_uses)

    def process_augment(self, m: BuildingModel):
        if m.data_def_stm == BuildingModel.StatementType.augment_:
            w = ModelWalker.path_parse(self.root, m.target_path)
            for i in m.children:
                i.deepcopy(w.current)

    def resolve_augments(self):
        current = self.augments
        while current:
            remaining = []
            for augment in current:
                w = ModelWalker(self.root)
                try:
                    w.go_to(augment.target_path)
                    node = w.current
                except InvalidPathError:
                    remaining.append(augment)
                    continue
                for i in augment.children:
                    i.deepcopy(node)
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
                    w.current.delete_from_parent(quiet=False)

    def resolve_namespaces(self):
        def ns_set(m: BuildingModel):
            if m.namespace or m.name.prefix not in self._ns_map.keys():
                return
            m.namespace = self._ns_map[m.name.prefix]
        for root_child in chain(self.root.children, self.metadata):
            root_child.recursive_walk(ns_set)

    def build_blueprints(self):
        handler = YangHandler(self, self.root)
        handler.construct()
        for a in self.metadata:
            handler.construct(a)

    def delete_blueprints(self):
        def deleter(m: BuildingModel):
            del m.blueprint
        self.walk_models(deleter)

    def resolve_config(self):
        def false_setter(m: BuildingModel):
            m.config = False

        def resolver(m: BuildingModel):
            if not m.config:
                m.recursive_walk(false_setter)
                return False

        self.walk_models(resolver)

    def resolve_metadata_exceptions(self):
        new = BuildingModel(Identifier("ietf-netconf", "operation"), BuildingModel.StatementType.annotate_, None)
        new.namespace = COMMON_NAMESPACES["ncbase"]
        type = Enumeration()
        type.add_enums("merge", "replace", "create", "delete", "remove")
        new.yang_type = type
        self.metadata.append(new)

    def convert_model(self):
        new_root = StorageConstructionModel("root", BuildingModel.StatementType["container_"], None)
        w = DataModelWalker(self.root)

        stack = [new_root]

        def enter_fnc(w: DataModelWalker):
            nonlocal stack
            new = StorageConstructionModel(w.get_name(), w.get_dds(), stack[-1])
            if isinstance(w.current.yang_type, YangUnion):
                w.current.yang_type.deduplicate()
            new.yang_type = w.current.yang_type
            new.units = w.current.units
            new.namespace = w.current.namespace
            new.default = w.current.default
            new.mandatory = w.current.mandatory
            new.status = w.current.status
            new.presence_container = w.current.presence_container
            new.user_ordered = w.current.user_ordered
            new.local_keys = w.current.local_keys
            new.target_path = w.current.target_path
            new.identity_bases = w.current.identity_bases
            new.config = w.current.config
            stack.append(new)

        def leave_fnc(w: DataModelWalker):
            nonlocal stack
            stack.pop()

        w.recursive_walk(enter_fnc=enter_fnc, leave_fnc=leave_fnc)
        self.root = Model(new_root._storage, new_root._index, None)


class TypeDefModel:
    __slots__ = ("yang_type", "default", "units")

    def __init__(self, arg: Union[YangType, Model, BuildingModel], default: Optional[str] = None, units: Optional[str] = None) -> None:
        assert isinstance(arg, (YangTypeBase, AModel))
        if isinstance(arg, AModel):
            self.yang_type = arg.yang_type
            self.default = arg.default
            self.units = arg.units
        else:
            self.yang_type = arg
            self.default = default
            self.units = units

    def __eq__(self, other):
        if not isinstance(other, self.__class__) or self.__slots__ != other.__slots__:
            return False
        return all(getattr(self, name) == getattr(other, name) for name in self.__slots__)


def merge_typedef_ranges(parent_range: str, child_range: str):
    """
    Vertically merge typedef integer ranges across typedef parent and child
    - keep child's integer range values (non-'min' or 'max')
    - replace child's 'min'/'max' strings with integer min or max values if present in parent
    - return child's ranges as-is if parent has no range defined or child has no 'max' or 'min'
    examples:
        - parent typedef range "1..200", child type range "min..100", result "1..100"
        - parent typedef range "1..200", child type range "100..max", result "100..200"
        - parent typedef range is None, child type range "100..max", result "100..max"
        - parent typedef range is '1..200', child type range "50..150", result "50..150"
    """
    if not parent_range:
        return child_range

    min_val = parent_range.split("|")[0].split("..")[0]
    child_range = child_range.replace("min", min_val)
    max_val = parent_range.split("|")[-1].split("..")[-1]
    child_range = child_range.replace("max", max_val)

    return child_range


def resolve_typedefs_shallow(t: TypeDefModel, typedefs: Dict[Identifier, TypeDefModel]):
    assert isinstance(t.yang_type, YangTypeBase)
    yang_type, default, units = t.yang_type, t.default, t.units
    while (type(yang_type) is UnresolvedIdentifier and
            yang_type.identifier in typedefs):
        r_model = typedefs[yang_type.identifier]
        u_range = yang_type.yang_range
        frac_d = yang_type.fraction_digits
        length = yang_type.length
        if any((u_range, frac_d, length)):
            yang_type = copy.copy(r_model.yang_type)
            if u_range:
                yang_type.yang_range = merge_typedef_ranges(yang_type.yang_range, u_range)
            if frac_d:
                yang_type.fraction_digits = frac_d
            if length:
                yang_type.length = length
        else:
            yang_type = r_model.yang_type
        default = default or r_model.default
        units = units or r_model.units

    assert not isinstance(yang_type, UnresolvedIdentifier), f"Cannot resolve type {yang_type}"
    assert isinstance(yang_type, YangTypeBase)
    return TypeDefModel(
        copy.copy(yang_type),
        default,
        units,
    )


def resolve_typedefs_deep(m: TypeDefModel, typedefs: Dict[Identifier, TypeDefModel]):
    m = resolve_typedefs_shallow(m, typedefs)
    if not isinstance(m.yang_type, YangUnion):
        return m

    u_yang_type, u_default, u_units = YangUnion(), None, None
    for sub in m.yang_type:
        tdm = resolve_typedefs_deep(TypeDefModel(sub), typedefs)
        if type(tdm.yang_type) == YangUnion:
            for t in tdm.yang_type:
                u_yang_type.append(t)
        else:
            u_yang_type.append(tdm.yang_type)
        u_default = tdm.default
        u_units = tdm.units
    m.yang_type = u_yang_type
    m.default = m.default or u_default
    m.units = m.units or u_units
    return m
