from __future__ import annotations
import ast
import astroid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Iterator
import typeshed_client


def infer(node: astroid.NodeNG) -> list:
    try:
        return list(node.infer())
    except astroid.InferenceError:
        return []


def qname_to_type(qname: str) -> Type:
    if qname.startswith('builtins.'):
        qname = qname.split('.')[-1]
    if qname == 'NoneType':
        qname = 'None'
    return Type(qname)


def is_camel(name: str) -> bool:
    if not name:
        return False
    if not name[0].isupper():
        return False
    if not any(c.islower() for c in name):
        return False
    return True


@dataclass
class FSig:
    name: str
    args: str
    return_type: Type

    @property
    def stub(self) -> str:
        return f'def {self.name}({self.args}) -> {self.return_type.rep}: ...'


class Ass(Enum):
    """Assumptions about the types that might be not true but usually are true.
    """
    # cannot infer type of one or more of the return statements,
    # assume all return statements to have the same type
    ALL_RETURNS_SAME = 'all-returns-same'
    # assume that comparison operations aren't overloaded
    NO_COMP_OVERLOAD = 'no-comp-overload'
    # assume that unary operators aren't overloaded
    NO_UNARY_OVERLOAD = 'no-unary-overload'
    # assume that all CamelCase names are types
    CAMEL_CASE_IS_TYPE = 'camel-case-is-type'
    # assume that built-in types and functions aren't shadowed
    NO_SHADOWING = 'camel-case-is-type'


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
        root = astroid.parse(source, path=str(path))

        result: list[str] = []
        for node in root.body:
            result.extend(self._get_stubs_for_node(node))
        return '\n\n'.join(result) + '\n'

    def _get_stubs_for_node(self, node: astroid.NodeNG) -> Iterator[str]:
        if isinstance(node, astroid.FunctionDef):
            sig = self.infer_sig(node)
            if sig is not None:
                yield sig.stub
            return

        if isinstance(node, astroid.ClassDef):
            printed_class = False
            for subnode in node.body:
                if isinstance(subnode, astroid.FunctionDef):
                    sig = self.infer_sig(subnode)
                    if sig is not None:
                        if not printed_class:
                            printed_class = True
                            yield f'class {node.name}:'
                        yield f'    {sig.stub}'

    def infer_sig(self, node: astroid.FunctionDef) -> FSig | None:
        if node.returns is not None:
            return None
        return_type = self.get_return_type(node.body)
        if not return_type.rep:
            return None
        return FSig(
            name=node.name,
            args=node.args.as_string(),
            return_type=return_type,
        )

    def get_return_type(self, nodes: Iterable[astroid.NodeNG]) -> Type:
        result = Type('')
        for node in nodes:
            if isinstance(node, astroid.Return):
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
            if isinstance(node, (astroid.FunctionDef, astroid.ClassDef)):
                continue
            branch_nodes = node.get_children()
            branch_type = self.get_return_type(branch_nodes)
            result = result.merge(branch_type)
        return result

    def get_node_type(self, node: astroid.NodeNG) -> Type | None:
        if isinstance(node, astroid.Const):
            if node.value is None:
                return Type('None')
            return Type(type(node.value).__name__)

        if isinstance(node, astroid.JoinedStr):
            return Type('str')

        if isinstance(node, astroid.UnaryOp):
            if node.op == 'not':
                return Type('bool')
            result = self.get_node_type(node.operand)
            if result is not None:
                result.ass.add(Ass.NO_UNARY_OVERLOAD)
                return result

        if isinstance(node, astroid.Compare) and len(node.ops) == 1:
            if node.ops[0][0] == 'is':
                return Type('bool')
            return Type('bool', ass={Ass.NO_COMP_OVERLOAD})

        if isinstance(node, astroid.Call):
            if isinstance(node.func, astroid.Attribute):
                result = self._get_attr_call_type(node.func)
                if result is not None:
                    return result
            if isinstance(node.func, astroid.Name):
                result = self._get_ret_type_of_fun('builtins', node.func.name)
                if result is not None:
                    result.ass = {Ass.NO_SHADOWING}
                    return result
                if is_camel(node.func.name):
                    return Type(node.func.name, ass={Ass.CAMEL_CASE_IS_TYPE})

        for def_node in infer(node):
            if not isinstance(def_node, astroid.Instance):
                continue
            return qname_to_type(def_node.pytype())
        if isinstance(node, astroid.Call):
            for def_node in infer(node.func):
                if not isinstance(def_node, astroid.FunctionDef):
                    continue
                mod_name, _, fun_name = def_node.qname().rpartition('.')
                return self._get_ret_type_of_fun(mod_name, fun_name)

        return None

    def _get_ret_type_of_fun(
        self,
        mod_name: str,
        fun_name: str,
    ) -> Type | None:
        module = typeshed_client.get_stub_names(mod_name)
        fun_def = module.get(fun_name)
        if fun_def is None:
            return None
        if not isinstance(fun_def.ast, ast.FunctionDef):
            return None
        ret_node = fun_def.ast.returns
        if isinstance(ret_node, ast.Name):
            return Type(ret_node.id)
        return None

    def _get_attr_call_type(self, node: astroid.Attribute) -> Type | None:
        result = self.get_node_type(node.expr)
        if result is None:
            return None
        module = typeshed_client.get_stub_names('builtins')
        try:
            method_def = module[result.rep].child_nodes[node.attrname]
        except KeyError:
            return None
        if not isinstance(method_def.ast, ast.FunctionDef):
            return None
        ret_node = method_def.ast.returns
        if isinstance(ret_node, ast.Name):
            return Type(ret_node.id)
        return None
