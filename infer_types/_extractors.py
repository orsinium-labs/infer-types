from __future__ import annotations

import ast
import builtins
from collections import deque
from types import MappingProxyType
from typing import Callable, Iterator

import astroid
import typeshed_client
from astypes import Ass, Type, get_type
from astypes._helpers import conv_node_to_type


Extractor = Callable[[astroid.FunctionDef], Type]
extractors: list[tuple[str, Extractor]] = []

UNKNOWN_TYPE = Type.new('')

KNOWN_NAMES = MappingProxyType({
    'dumps': 'str',
    'exists': 'bool',
    'contains': 'bool',
    'count': 'int',
    'size': 'int',
})
REMOVE_PREFIXES = ('as_', 'to_', 'get_')
BOOL_PREFIXES = ('is_', 'has_', 'should_', 'can_', 'will_', 'supports_')


def register(name: str) -> Callable[[Extractor], Extractor]:
    def callback(extractor: Extractor) -> Extractor:
        extractors.append((name, extractor))
        return extractor
    return callback


def get_return_type(
    func_node: astroid.FunctionDef,
    names: frozenset[str],
) -> Type | None:
    """
    Recursively walk the given body, find all return stmts,
    and infer their type. The result is a union of these types.
    """
    for name, extractor in extractors:
        if names and name not in names:
            continue
        ret_type = extractor(func_node)
        if not ret_type.unknown:
            return ret_type
    return None


def walk(func_node: astroid.FunctionDef) -> Iterator[astroid.NodeNG]:
    stack: deque[astroid.NodeNG] = deque(func_node.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (astroid.FunctionDef, astroid.ClassDef)):
            continue
        doc_node = getattr(node, 'doc_node', None)
        if doc_node is not None and doc_node is not node:
            stack.append(doc_node)
        stack.extend(node.get_children())
        yield node


@register(name='astypes')
def _extract_astypes(func_node: astroid.FunctionDef) -> Type:
    result = UNKNOWN_TYPE
    for node in walk(func_node):
        if not isinstance(node, astroid.Return):
            continue
        # bare return
        if node.value is None:
            result = result.merge(Type.new('None'))
            continue
        node_type = get_type(node.value)
        if node_type is None:
            result = result.add_ass(Ass.ALL_RETURNS_SAME)
        else:
            result = result.merge(node_type)
    if result.unknown:
        return UNKNOWN_TYPE
    return result


@register(name='inherit')
def _extract_inherit_method(func_node: astroid.FunctionDef) -> Type:
    for node in func_node.node_ancestors():
        if isinstance(node, astroid.ClassDef):
            cls_node = node
            break
    else:
        return UNKNOWN_TYPE
    for parent in cls_node.getattr(func_node.name):
        if isinstance(parent, astroid.BoundMethod):
            parent = parent._proxied
        if not isinstance(parent, astroid.FunctionDef):
            continue
        qname: str = parent.qname()
        mod_name, cls_name, func_name = qname.rsplit('.', maxsplit=2)
        assert func_name == func_node.name

        # extract type from the return type annotation
        return_type = conv_node_to_type(mod_name, parent.returns)
        if return_type is not None:
            return return_type

        # extract type from typeshed
        module = typeshed_client.get_stub_names(mod_name)
        if module is None:
            continue
        child_nodes = module[cls_name].child_nodes
        assert child_nodes is not None
        try:
            method_def = child_nodes[func_name]
        except KeyError:
            continue
        if not isinstance(method_def.ast, ast.FunctionDef):
            continue
        type_node = method_def.ast.returns
        return_type = conv_node_to_type(mod_name, type_node)
        if return_type is not None:
            return return_type
    return UNKNOWN_TYPE


@register(name='yield')
def _extract_yield(func_node: astroid.FunctionDef) -> Type:
    for node in walk(func_node):
        if isinstance(node, (astroid.Yield, astroid.YieldFrom)):
            return Type.new('Iterator', module='typing')
    return UNKNOWN_TYPE


@register(name='none')
def _extract_no_return(func_node: astroid.FunctionDef) -> Type:
    # ignore empty methods, they can be there for base class signatures
    if isinstance(func_node.parent, astroid.ClassDef):
        if not func_node.body:
            return UNKNOWN_TYPE
        if len(func_node.body) == 1:
            node = func_node.body[0]

            if isinstance(node, (astroid.Raise, astroid.Pass)):
                return UNKNOWN_TYPE
            if isinstance(node, astroid.Expr):
                node = node.value
                if isinstance(node, astroid.Const) and node.value == ...:
                    return UNKNOWN_TYPE

    for node in walk(func_node):
        if isinstance(node, (astroid.Yield, astroid.YieldFrom)):
            return UNKNOWN_TYPE
        if isinstance(node, astroid.Return) and node.value is not None:
            return UNKNOWN_TYPE
    return Type.new('None')


@register(name='name')
def _extract_from_name(func_node: astroid.FunctionDef) -> Type:
    """Try to guess the return type based on the function name.
    """
    name: str = func_node.name
    name = name.lstrip('_')
    # TODO(@orsinium): use str.removeprefix when migrating to 3.9
    for prefix in REMOVE_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
    if name.startswith(BOOL_PREFIXES):
        return Type.new('bool')
    if name.endswith('_at'):
        return Type.new('datetime', module='datetime')
    if hasattr(builtins, name):
        return Type.new(name)
    return Type.new(KNOWN_NAMES.get(name, ''))
