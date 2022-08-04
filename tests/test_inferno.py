from pathlib import Path
from textwrap import dedent

import pytest
from infer_types._inferno import Inferno


def get_stubs(tmp_path: Path, source: str) -> str:
    inferno = Inferno()
    path = tmp_path / 'example.py'
    path.write_text(source)
    return inferno.generate_stub(path)


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
    assert result.strip() == f'def f() -> {type}: ...'


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
    assert result.strip() == ''


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
    assert result.strip() == f'def f() -> {type}: ...'


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
    assert result.strip() == f'def f({expr}) -> int: ...'
