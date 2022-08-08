from __future__ import annotations
import ast
import astroid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator
import typeshed_client

from ._types import Type, FSig, Ass


SUPPORTED_DECORATORS = frozenset({
    'staticmethod',
    'classmethod',
    'property',
    'cached_property',
})


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
    if '.' not in qname:
        return Type(qname)
    mod_name, _, obj_name = qname.rpartition('.')
    imp = f'from {mod_name} import {obj_name}'
    return Type(obj_name, imp={imp})


def is_camel(name: str) -> bool:
    if not name:
        return False
    if not name[0].isupper():
        return False
    if not any(c.islower() for c in name):
        return False
    return True


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
                node_type = self._get_node_type(node.value)
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

    def _get_node_type(self, node: astroid.NodeNG) -> Type | None:
        """Try to detect type of the given AST node.
        """
        # explicit literals
        if isinstance(node, astroid.Const):
            if node.value is None:
                return Type('None')
            return Type(type(node.value).__name__)
        if isinstance(node, astroid.JoinedStr):
            return Type('str')

        # unary operation
        if isinstance(node, astroid.UnaryOp):
            if node.op == 'not':
                return Type('bool')
            result = self._get_node_type(node.operand)
            if result is not None:
                result.ass.add(Ass.NO_UNARY_OVERLOAD)
                return result

        # binary operation
        if isinstance(node, astroid.Compare) and len(node.ops) == 1:
            if node.ops[0][0] == 'is':
                return Type('bool')
            return Type('bool', ass={Ass.NO_COMP_OVERLOAD})

        # call of a function or method
        if isinstance(node, astroid.Call):
            if isinstance(node.func, astroid.Attribute):
                result = self._get_attr_call_type(node.func)
                if result is not None:
                    return result
            if isinstance(node.func, astroid.Name):
                _, symbol_defs = node.func.lookup(node.func.name)
                mod_name = 'builtins'
                if symbol_defs:
                    symbol_def = symbol_defs[0]
                    if isinstance(symbol_def, astroid.ImportFrom):
                        mod_name = symbol_def.modname
                result = self._get_ret_type_of_fun(mod_name, node.func.name)
                if result is not None:
                    return result
                if is_camel(node.func.name):
                    return Type(node.func.name, ass={Ass.CAMEL_CASE_IS_TYPE})

        # astroid inference for class instantination
        for def_node in infer(node):
            if not isinstance(def_node, astroid.Instance):
                continue
            return qname_to_type(def_node.pytype())
        # astroid inference for a function call
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
        """For the given module and function name, get return type of the function.
        """
        module = typeshed_client.get_stub_names(mod_name)
        if module is None:
            self.warn(f'no typeshed stubs for module {mod_name}')
            return None
        fun_def = module.get(fun_name)
        if fun_def is None:
            self.warn('no typeshed stubs for module')
            return None
        if not isinstance(fun_def.ast, ast.FunctionDef):
            self.warn('resolved call target is not a function')
            return None
        ret_node = fun_def.ast.returns
        return self._conv_node_to_type(mod_name, ret_node)

    def _get_attr_call_type(self, node: astroid.Attribute) -> Type | None:
        result = self._get_node_type(node.expr)
        if result is None:
            self.warn('cannot get type of the left side of attribute')
            return None
        module = typeshed_client.get_stub_names('builtins')
        assert module is not None
        try:
            method_def = module[result.rep].child_nodes[node.attrname]
        except KeyError:
            self.warn('not a built-in function')
            return None
        if not isinstance(method_def.ast, ast.FunctionDef):
            self.warn('resolved call target of attr is not a function')
            return None
        ret_node = method_def.ast.returns
        return self._conv_node_to_type('builtins', ret_node)

    def _conv_node_to_type(
        self, mod_name: str, node: ast.AST | None,
    ) -> Type | None:
        import builtins
        import typing

        if node is None:
            self.warn('no return type annotation for called function def')
            return None

        # fore generics, keep it generic
        if isinstance(node, ast.Subscript):
            return self._conv_node_to_type(mod_name, node.value)

        # for regular name, check if it is a typing primitive or a built-in
        if isinstance(node, ast.Name):
            name = node.id
            if hasattr(builtins, name):
                return Type(name, ass={Ass.NO_SHADOWING})
            if name in typing.__all__:
                return Type(name, imp={f'from typing import {name}'})
            self.warn(f'cannot resolve {name} into a known type')
            return None

        self.warn('cannot resolve return AST node into a known type')
        return None
