from __future__ import annotations
import ast
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator, Iterable


@dataclass
class FSig:
    name: str
    return_type: Type

    @property
    def stub(self) -> str:
        return f'def {self.name}() -> {self.return_type.rep}: ...'


class Ass(Enum):
    """Assumptions about the types that might be not true but usually are true.
    """
    # cannot infer type of one or more of the return statements,
    # assume all return statements to have the same type
    ALL_RETURNS_SAME = 'all-returns-same'


@dataclass
class Type:
    rep: str
    ass: set[Ass] = field(default_factory=set)

    def merge(self, other: Type) -> Type:
        if not self.rep or not other.rep:
            rep = self.rep or other.rep
        elif other.rep in self.rep:
            rep = self.rep
        else:
            rep = f'{self.rep} | {other.rep}'
        return Type(
            rep=rep,
            ass=self.ass | other.ass,
        )


class Inferno:
    def generate_stub(self, path: Path) -> str:
        source = path.read_text()
        root = ast.parse(source, mode='exec')
        result = []
        for fsig in self.infer_all(root):
            result.append(fsig.stub)
        return '\n\n'.join(result) + '\n'

    def infer_all(self, root: ast.Module) -> Iterator[FSig]:
        for node in root.body:
            if isinstance(node, ast.FunctionDef):
                sig = self.infer_sig(node)
                if sig is not None:
                    yield sig

    def infer_sig(self, node: ast.FunctionDef) -> FSig | None:
        if node.returns is not None:
            return None
        return_type = self.get_return_type(node.body)
        if not return_type.rep:
            return None
        return FSig(node.name, return_type=return_type)

    def get_return_type(self, nodes: Iterable[ast.AST]) -> Type:
        result = Type('')
        for node in nodes:
            if isinstance(node, ast.Return):
                # bare return
                if node.value is None:
                    result = result.merge(Type('None'))
                    continue
                node_type = self.get_node_type(node.value)
                if node_type is None:
                    result.ass.add(Ass.ALL_RETURNS_SAME)
                else:
                    result = result.merge(node_type)
                continue
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                continue
            branch_nodes = ast.iter_child_nodes(node)
            branch_type = self.get_return_type(branch_nodes)
            result = result.merge(branch_type)
        return result

    def get_node_type(self, node: ast.expr) -> Type | None:
        if isinstance(node, ast.Constant):
            return Type(type(node.value).__name__)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return Type('bool')
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            if isinstance(node.ops[0], (ast.Is, ast.In)):
                return Type('bool')
        return None
