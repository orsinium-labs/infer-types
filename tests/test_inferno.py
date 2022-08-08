from pathlib import Path
from textwrap import dedent

import pytest
from infer_types._inferno import Inferno


def get_stubs(tmp_path: Path, source: str) -> str:
    inferno = Inferno(warn=print)
    path = tmp_path / 'example.py'
    path.write_text(source)
    result = inferno.generate_stub(path).strip()
    return '\n'.join(line for line in result.splitlines() if line)


@pytest.mark.parametrize('expr, type', [
    # literals
    ('1', 'int'),
    ('1.2', 'float'),
    ('"hi"', 'str'),
    ('f"hi"', 'str'),
    ('b"hi"', 'bytes'),
    ('""', 'str'),
    ('None', 'None'),
    ('', 'None'),
    ('True', 'bool'),

    # operations with known type
    ('not x', 'bool'),
    ('x is str', 'bool'),

    # operations with assumptions
    ('x in (1, 2, 3)', 'bool'),
    ('x < 10', 'bool'),
    ('~13', 'int'),
    ('+13', 'int'),

    # methos of builtins
    ('"".join(x)', 'str'),

    # builtin functions
    ('len(x)', 'int'),
    ('list(x)', 'list'),
])
def test_inferno_expr(tmp_path, expr, type):
    source = dedent(f"""
        def f():
            return {expr}
    """)
    result = get_stubs(tmp_path, source)
    assert result == f'def f() -> {type}: ...'


@pytest.mark.parametrize('expr', [
    'min(x)',
    'x',
    '+x',
    'x + y',
    'str.wat',
    '"hi".wat',
    'None.hi',
    'None.hi()',
    '"hi".wat()',
    'wat.wat',
])
def test_cannot_infer_expr(tmp_path, expr):
    source = dedent(f"""
        def f():
            return {expr}
    """)
    result = get_stubs(tmp_path, source)
    assert result == ''


@pytest.mark.parametrize('setup, expr, type', [
    ('import math', 'math.sin(x)', 'float'),
    ('from math import sin', 'sin(x)', 'float'),
    ('my_list = list', 'my_list(x)', 'list'),
])
def test_astroid_inference(tmp_path, setup, expr, type):
    source = dedent(f"""
        {setup}

        def f():
            return {expr}
    """)
    result = get_stubs(tmp_path, source)
    assert result == f'def f() -> {type}: ...'


@pytest.mark.parametrize('expr', [
    '',
    'x',
    'x, y',
    'x, *, y',
    '*, a',
    '*args',
    '**kwargs',
    '*args, **kwargs',
    'x=None, y=12',
    'x: int | None',
    'x: int | None = 13',
])
def test_preserve_args(tmp_path, expr):
    source = dedent(f"""
        def f({expr}):
            return 1
    """)
    result = get_stubs(tmp_path, source)
    assert result == f'def f({expr}) -> int: ...'


def test_infer_class_methods(tmp_path):
    given = dedent("""
        class C:
            def m(self, x):
                return 13
    """)
    expected = dedent("""
        class C:
            def m(self, x) -> int: ...
    """)
    actual = get_stubs(tmp_path, given)
    lactual = [line for line in actual.splitlines() if line]
    lexpected = [line for line in expected.splitlines() if line]
    assert lactual == lexpected


@pytest.mark.parametrize('g_imp, g_expr, e_imp, e_type', [
    (
        'import datetime', 'datetime.date(1,2,3)',
        'from datetime import date', 'date',
    ),
    (
        'from datetime import date', 'date(1,2,3)',
        'from datetime import date', 'date',
    ),
    (
        'import ast', 'ast.walk(x)',
        'from typing import Iterator', 'Iterator',
    ),
])
def test_import_types(tmp_path, g_imp, g_expr, e_imp, e_type):
    source = dedent(f"""
        {g_imp}

        def f():
            return {g_expr}
    """)
    result = get_stubs(tmp_path, source)
    assert result == f'{e_imp}\ndef f() -> {e_type}: ...'
