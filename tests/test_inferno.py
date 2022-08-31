from pathlib import Path
from textwrap import dedent
from typing import Callable

import pytest
from infer_types._inferno import Inferno


@pytest.fixture
def get_stubs(tmp_path: Path) -> Callable:
    def callback(source: str) -> str:
        inferno = Inferno()
        path = tmp_path / 'example.py'
        source = dedent(source)
        path.write_text(source)
        result = inferno.generate_stub(path).strip()
        return '\n'.join(line for line in result.splitlines() if line)
    return callback


def test_inferno_expr(get_stubs):
    result = get_stubs("""
        def f(x):
            return len(x)
    """)
    assert result == 'def f(x) -> int: ...'


def test_infer_bare_return(get_stubs):
    result = get_stubs("""
        def f(x):
            if x == y:
                return
            return 13
    """)
    assert result == 'def f(x) -> int | None: ...'


def test_skip_subfuncs(get_stubs):
    result = get_stubs("""
        def f(x):
            def f2():
                return 'hello'
            return 13
    """)
    assert result == 'def f(x) -> int: ...'


def test_simplify_union_same_type(get_stubs):
    result = get_stubs("""
        def f(x):
            if x == y:
                return 12
            return 13
    """)
    assert result == 'def f(x) -> int: ...'


def test_cannot_infer_expr(get_stubs):
    result = get_stubs("""
        def f(x):
            return min(x)
    """)
    assert result == ''


def test_skip_annotated(get_stubs):
    result = get_stubs("""
        def f() -> int:
            return "hi"
    """)
    assert result == ''


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
def test_preserve_args(get_stubs, expr):
    result = get_stubs(f"""
        def f({expr}):
            return 1
    """)
    assert result == f'def f({expr}) -> int: ...'


def test_infer_class_methods(get_stubs):
    actual = get_stubs("""
        SOMETHING = 13
        class C:
            some_attr: str = 14
            def m(self, x):
                return 13
    """)
    expected = dedent("""
        class C:
            def m(self, x) -> int: ...
    """)
    lactual = [line for line in actual.splitlines() if line]
    lexpected = [line for line in expected.splitlines() if line]
    assert lactual == lexpected


def test_preserve_property_decorator(get_stubs):
    actual = get_stubs("""
        class C:
            @property
            @garbage
            def m(self, x):
                return 13
    """)
    expected = dedent("""
        class C:
            @property
            def m(self, x) -> int: ...
    """)
    lactual = [line for line in actual.splitlines() if line]
    lexpected = [line for line in expected.splitlines() if line]
    assert lactual == lexpected


def test_preserve_cached_property_decorator(get_stubs):
    actual = get_stubs("""
        from functools import cached_property
        class C:
            @cached_property
            def m(self, x):
                return 13
    """)
    expected = dedent("""
        from functools import cached_property
        class C:
            @cached_property
            def m(self, x) -> int: ...
    """)
    lactual = [line for line in actual.splitlines() if line]
    lexpected = [line for line in expected.splitlines() if line]
    assert lactual == lexpected


def test_cannot_infer_class_methods(get_stubs):
    actual = get_stubs("""
        class C:
            def m(self, x):
                return x
    """)
    assert actual == ""


def test_can_infer_only_one(get_stubs):
    actual = get_stubs("""
        def f(x):
            if x == y:
                return x
            else:
                return 13
    """)
    expected = dedent("def f(x) -> int: ...")
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
def test_import_types(get_stubs, g_imp, g_expr, e_imp, e_type):
    result = get_stubs(f"""
        {g_imp}

        def f():
            return {g_expr}
    """)
    assert result == f'{e_imp}\ndef f() -> {e_type}: ...'


def test_detect_bare_return(get_stubs):
    result = get_stubs("""
        def f(x):
            if x:
                return
            do_something()
    """)
    assert result == 'def f(x) -> None: ...'


def test_detect_no_return(get_stubs):
    result = get_stubs("""
        def f():
            do_something()
    """)
    assert result == 'def f() -> None: ...'


def test_detect_yield(get_stubs):
    result = get_stubs("""
        def f():
            yield x
    """)
    assert result == 'from typing import Iterator\ndef f() -> Iterator: ...'


def test_detect_magic_method(get_stubs):
    result = get_stubs("""
        class A:
            def __str__(self):
                return x
    """)
    expected = dedent("""
        class A:
            def __str__(self) -> str: ...
    """)
    assert result.strip() == expected.strip()


def test_inherit(get_stubs):
    result = get_stubs("""
        class A:
            def f(self) -> str:
                return x

        class B(A):
            def f(self):
                return y
    """)
    expected = dedent("""
        class B:
            def f(self) -> str: ...
    """)
    assert result.strip() == expected.strip()
