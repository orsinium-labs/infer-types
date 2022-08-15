from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator

import astroid

from ._handlers import handlers
from ._types import Ass, FSig, Type


SUPPORTED_DECORATORS = frozenset({
    'staticmethod',
    'classmethod',
    'property',
    'cached_property',
})


def void(msg: str) -> None:
    return None


@dataclass
class Inferno:
    warn: Callable[[str], None] = void

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
                yield from sig.imp
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
                    if mod_name:
                        imports.add(f'from {mod_name} import {dec_name}')
                        sigs.append(f'    @{dec_name}')
                imports.update(sig.imp)
                sigs.append(f'    {sig.stub}')
        yield from imports
        if sigs:
            yield f'class {node.name}:'
            yield from sigs

    def infer_sig(self, node: astroid.FunctionDef) -> FSig | None:
        if node.returns is not None:
            return None
        return_type = self._get_return_type(node.body)
        if not return_type.rep:
            return None
        return FSig(
            name=node.name,
            args=node.args.as_string(),
            return_type=return_type,
        )

    def _get_return_type(self, nodes: Iterable[astroid.NodeNG]) -> Type:
        """
        Recursively walk the given body, find all return stmts,
        and infer their type. The result is a union of these types.
        """
        result = Type('')
        for node in nodes:
            if isinstance(node, astroid.Return):
                # bare return
                if node.value is None:
                    result = result.merge(Type('None'))
                    continue
                node_type = handlers.node_to_type(node.value)
                if node_type is None:
                    result.ass.add(Ass.ALL_RETURNS_SAME)
                else:
                    result = result.merge(node_type)
                continue
            if isinstance(node, (astroid.FunctionDef, astroid.ClassDef)):
                continue
            branch_nodes = node.get_children()
            branch_type = self._get_return_type(branch_nodes)
            result = result.merge(branch_type)
        return result
