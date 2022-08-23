from __future__ import annotations
from collections import deque

from typing import Callable, Iterable, Iterator

import astroid
from astypes import Type, get_type, Ass


Extractor = Callable[[Iterable[astroid.NodeNG]], Type]
extractors: list[Extractor] = []


def register(extractor: Extractor) -> Extractor:
    extractors.append(extractor)
    return extractor


def get_return_type(nodes: Iterable[astroid.NodeNG]) -> Type | None:
    """
    Recursively walk the given body, find all return stmts,
    and infer their type. The result is a union of these types.
    """
    for extractor in extractors:
        ret_type = extractor(nodes)
        if not ret_type.unknown:
            return ret_type
    return None


def walk(nodes: Iterable[astroid.NodeNG]) -> Iterator[astroid.NodeNG]:
    stack = deque(nodes)
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
def _extract_astypes(nodes: Iterable[astroid.NodeNG]) -> Type:
    result = Type.new('')
    for node in walk(nodes):
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
def _extract_no_return(nodes: Iterable[astroid.NodeNG]) -> Type:
    for node in walk(nodes):
        if isinstance(node, (astroid.Yield, astroid.YieldFrom)):
            return Type.new('')
        if isinstance(node, astroid.Return) and node.value is not None:
            return Type.new('')
    return Type.new('None')


@register
def _extract_yield(nodes: Iterable[astroid.NodeNG]) -> Type:
    for node in walk(nodes):
        if isinstance(node, (astroid.Yield, astroid.YieldFrom)):
            return Type.new('Iterator', module='typing')
    return Type.new('')
