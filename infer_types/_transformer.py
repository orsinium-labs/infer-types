from __future__ import annotations

import tokenize
from dataclasses import dataclass, field
from functools import cached_property

import astroid


class Transformation:

    def pick_position(self, tr: Transformer) -> tuple[int, int]:
        raise NotImplementedError

    def as_str(self) -> str:
        raise NotImplementedError

    @property
    def position(self) -> tuple[int, int]:
        """Approximated position of the change, used to order transformations.
        """
        raise NotImplementedError


@dataclass(frozen=True)
class InsertImport(Transformation):
    """Insert import statement required for the function annotations.

    Currently, inserts it right after the function. Let isort fix it.
    """
    node: astroid.FunctionDef | astroid.ClassDef
    text: str

    def pick_position(self, tr: Transformer) -> tuple[int, int]:
        return (self.node.lineno, self.node.col_offset)

    def as_str(self) -> str:
        return f'{self.text}\n'

    @property
    def position(self) -> tuple[int, int]:
        return (self.node.lineno, self.node.col_offset)


@dataclass(frozen=True)
class InsertReturnType(Transformation):
    """Insert the return type annotation into the function at the given line.
    """
    node: astroid.FunctionDef
    text: str

    def pick_position(self, tr: Transformer) -> tuple[int, int]:
        assert tr.colons, 'no colons found'
        node = self.node.doc_node or self.node.body[0]
        for line, col in reversed(tr.colons):
            if line < node.lineno:
                return (line, col)
        msg = f'cannot find colon matching the function {self.node.name}'
        raise LookupError(msg)

    def as_str(self) -> str:
        return f' -> {self.text}'

    @property
    def position(self) -> tuple[int, int]:
        return (self.node.lineno, self.node.col_offset + 1)


@dataclass(frozen=True)
class Transformer:
    """Insert snippets of text into the source code.
    """
    source: str
    _transforms: list[Transformation] = field(default_factory=list)

    def add(self, transform: Transformation) -> None:
        """Add new transformation to pending.
        """
        self._transforms.append(transform)

    def apply(self) -> str:
        """Apply all pending transformations and return the transformed source code.
        """
        self._transforms.sort(key=lambda t: t.position, reverse=True)
        lines = self.source.splitlines(keepends=True)
        for transform in self._transforms:
            lineno, col = transform.pick_position(self)
            lineno -= 1
            line = lines[lineno]
            lines[lineno] = line[:col] + transform.as_str() + line[col:]
        return ''.join(lines)

    @cached_property
    def colons(self) -> tuple[tuple[int, int], ...]:
        """Positions of all colons.
        """
        result = []
        for token in self._tokens:
            if token.type == tokenize.OP and token.string == ':':
                result.append(token.start)
        return tuple(result)

    @cached_property
    def _tokens(self) -> tuple[tokenize.TokenInfo, ...]:
        lines = self.source.encode('utf8').splitlines(keepends=True)
        return tuple(tokenize.tokenize(iter(lines).__next__))
