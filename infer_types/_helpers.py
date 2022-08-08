from __future__ import annotations
import astroid
from ._types import Type


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
