# Copyright 2021 Nokia

from typing import Dict, Iterable

from .identifier import Identifier

class ModelPath:
    """Representation of path as a sequence of identifiers.

    .. Reviewed by TechComms 20210712
    """
    def __init__(self, parts: Iterable[Identifier]):
        self._path = tuple(parts)

    def is_valid(self, *, only_absolute_path: bool):
        if not self._path:
            return False

        for p in self._path:
            if p.is_valid():
                continue
            if only_absolute_path or p.name != "..":
                return False
        return True

    def repr_path(self):
        return self._path.__repr__()

    def __hash__(self):
        return hash(self._path)

    def __eq__(self, other):
        return isinstance(other, ModelPath) and self._path == other._path
