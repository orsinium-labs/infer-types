from __future__ import annotations

from dataclasses import dataclass, field
from logging import getLogger
from pathlib import Path
from typing import Iterator

import astroid

from ._extractors import get_return_type
from ._fsig import FSig
from ._transformer import (
    InsertImport, InsertReturnType, Transformation, Transformer,
)


logger = getLogger(__name__)


@dataclass(frozen=True)
class Inferno:
    safe: bool = False
    imports: bool = True
    methods: bool = True
    functions: bool = True
    assumptions: bool = True
    only: frozenset[str] = field(default_factory=frozenset)

    def transform(self, path: Path) -> str:
        source = path.read_text()
        tr = Transformer(source)
        root = astroid.parse(source, path=str(path))
        for node in root.body:
            try:
                transforms = list(self._get_transforms_for_node(node))
            except Exception:
                if not self.safe:
                    raise
                logger.exception(f'failed inference for {path}:{node.lineno}')
                continue
            for transform in transforms:
                tr.add(transform)
        return tr.apply()

    def _get_transforms_for_node(self, node: astroid.NodeNG) -> Iterator[Transformation]:
        # infer return type for function
        if self.functions and isinstance(node, astroid.FunctionDef):
            sig = self._infer_sig(node)
            if sig is not None:
                if not self.imports and sig.imports:
                    return
                for import_stmt in sig.imports:
                    yield InsertImport(node, import_stmt)
                yield InsertReturnType(node, sig.annotation)
            return

        # infer return type for all methods of a class
        if self.methods and isinstance(node, astroid.ClassDef):
            for subnode in node.body:
                if not isinstance(subnode, astroid.FunctionDef):
                    continue
                sig = self._infer_sig(subnode)
                if sig is None:
                    continue
                if not self.imports and sig.imports:
                    continue
                for import_stmt in sig.imports:
                    yield InsertImport(node, import_stmt)
                yield InsertReturnType(subnode, sig.annotation)

    def _infer_sig(self, node: astroid.FunctionDef) -> FSig | None:
        if node.returns is not None:
            return None
        return_type = get_return_type(node, names=self.only)
        if return_type is None:
            return None
        if not self.assumptions and return_type.assumptions:
            return None
        return FSig(
            name=node.name,
            args=node.args.as_string(),
            return_type=return_type,
        )
