from __future__ import annotations

import ast
from collections import deque
from typing import Callable, Iterator

import astroid
import typeshed_client
from astypes import Ass, Type, get_type
from astypes._helpers import conv_node_to_type


Extractor = Callable[[astroid.FunctionDef], Type]
extractors: list[Extractor] = []


def register(extractor: Extractor) -> Extractor:
    extractors.append(extractor)
    return extractor


def get_return_type(func_node: astroid.FunctionDef) -> Type | None:
    """
    Recursively walk the given body, find all return stmts,
    and infer their type. The result is a union of these types.
    """
    for extractor in extractors:
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


@register
def _extract_astypes(func_node: astroid.FunctionDef) -> Type:
    result = Type.new('')
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
        return Type.new('')
    return result


@register
def _extract_inherit_method(func_node: astroid.FunctionDef) -> Type:
    for node in func_node.node_ancestors():
        if isinstance(node, astroid.ClassDef):
            cls_node = node
            break
    else:
        return Type.new('')
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
    return Type.new('')


@register
def _extract_yield(func_node: astroid.FunctionDef) -> Type:
    for node in walk(func_node):
        if isinstance(node, (astroid.Yield, astroid.YieldFrom)):
            return Type.new('Iterator', module='typing')
    return Type.new('')


@register
def _extract_no_return(func_node: astroid.FunctionDef) -> Type:
    for node in walk(func_node):
        if isinstance(node, astroid.Return) and node.value is not None:
            return Type.new('')
    return Type.new('None')
