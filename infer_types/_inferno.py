from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

import astroid
from astypes import Type
from ._fsig import FSig
from ._extractors import extractors


@dataclass
class Inferno:
    def generate_stub(self, path: Path) -> str:
        source = path.read_text()
        root = astroid.parse(source, path=str(path))

        result: list[str] = []
        for node in root.body:
            result.extend(self._get_stubs_for_node(node))
        return '\n'.join(result) + '\n'

    def _get_stubs_for_node(self, node: astroid.NodeNG) -> Iterator[str]:
        # infer return type for function
        if isinstance(node, astroid.FunctionDef):
            sig = self.infer_sig(node)
            if sig is not None:
                yield from sig.imports
                yield sig.stub
            return

        # infer return type for all methods of a class
        imports: set[str] = set()
        sigs: list[str] = []
        if isinstance(node, astroid.ClassDef):
            for subnode in node.body:
                if not isinstance(subnode, astroid.FunctionDef):
                    continue
                sig = self.infer_sig(subnode)
                if sig is None:
                    continue
                dec_qname: str
                for dec_qname in subnode.decoratornames():
                    mod_name, _, dec_name = dec_qname.rpartition('.')
                    if mod_name != 'builtins':
                        imports.add(f'from {mod_name} import {dec_name}')
                    if mod_name:
                        sigs.append(f'    @{dec_name}')
                imports.update(sig.imports)
                sigs.append(f'    {sig.stub}')
        yield from imports
        if sigs:
            yield f'class {node.name}:'
            yield from sigs

    def infer_sig(self, node: astroid.FunctionDef) -> FSig | None:
        if node.returns is not None:
            return None
        return_type = self._get_return_type(node.body)
        if return_type is None:
            return None
        return FSig(
            name=node.name,
            args=node.args.as_string(),
            return_type=return_type,
        )

    def _get_return_type(self, nodes: Iterable[astroid.NodeNG]) -> Type | None:
        """
        Recursively walk the given body, find all return stmts,
        and infer their type. The result is a union of these types.
        """
        for extractor in extractors:
            ret_type = extractor(nodes)
            if not ret_type.unknown:
                return ret_type
        return None
