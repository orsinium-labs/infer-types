from __future__ import annotations
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
import tokenize


@dataclass(frozen=True)
class InsertReturnType:
    """Insert the return type annotation into the function at the given line.
    """
    line: int
    text: str

    def pick_position(self, tr: Transformer) -> tuple[int, int]:
        assert tr.colons, 'no colons found'
        for line, col in tr.colons:
            if line >= self.line:
                return (line, col)
        msg = f'cannot find colon matching the function at {self.line}'
        raise LookupError(msg)

    def as_str(self) -> str:
        return f' -> {self.text}'


@dataclass(frozen=True)
class Transformer:
    """Insert snippets of text into the source code.
    """
    path: Path
    _transforms: list[InsertReturnType] = field(default_factory=list)

    def add(self, transform: InsertReturnType) -> None:
        """Add new transformation to pending.
        """
        self._transforms.append(transform)

    def apply(self) -> None:
        """Apply all pending transformations in place.
        """
        old_text = self.path.read_text(encoding='utf8')
        new_text = self._transform(old_text)
        self.path.write_text(new_text, encoding='utf8')

    def _transform(self, text: str) -> str:
        self._transforms.sort(key=lambda t: t.line, reverse=True)
        lines = text.splitlines(keepends=True)
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
        with self.path.open('rb') as stream:
            return tuple(tokenize.tokenize(stream.__next__))
