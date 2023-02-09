from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import astroid
from ._fsig import FSig
from ._extractors import get_return_type
from ._transformer import Transformer, InsertReturnType


@dataclass
class Inferno:
    def transform(self, path: Path) -> str:
        source = path.read_text()
        tr = Transformer(source)
        root = astroid.parse(source, path=str(path))
        for node in root.body:
            for transform in self._get_transforms_for_node(node):
                tr.add(transform)
        return tr.apply()

    def _get_transforms_for_node(
        self, node: astroid.NodeNG,
    ) -> Iterator[InsertReturnType]:
        # infer return type for function
        if isinstance(node, astroid.FunctionDef):
            sig = self._infer_sig(node)
            if sig is not None:
                # yield from sig.imports
                yield InsertReturnType(node, sig.annotation)
            return

        # infer return type for all methods of a class
        if isinstance(node, astroid.ClassDef):
            for subnode in node.body:
                if not isinstance(subnode, astroid.FunctionDef):
                    continue
                sig = self._infer_sig(subnode)
                if sig is None:
                    continue
                # dec_qname: str
                # for dec_qname in subnode.decoratornames():
                #     mod_name, _, dec_name = dec_qname.rpartition('.')
                #     if mod_name != 'builtins':
                #         imports.add(f'from {mod_name} import {dec_name}')
                #     if mod_name:
                #         sigs.append(f'    @{dec_name}')
                # imports.update(sig.imports)
                yield InsertReturnType(subnode, sig.annotation)

    def _infer_sig(self, node: astroid.FunctionDef) -> FSig | None:
        if node.returns is not None:
            return None
        return_type = get_return_type(node)
        if return_type is None:
            return None
        return FSig(
            name=node.name,
            args=node.args.as_string(),
            return_type=return_type,
        )
