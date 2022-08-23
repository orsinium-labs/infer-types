from pathlib import Path
from textwrap import dedent

import pytest
from infer_types._inferno import Inferno


def get_stubs(tmp_path: Path, source: str) -> str:
    inferno = Inferno()
    path = tmp_path / 'example.py'
    path.write_text(source)
    result = inferno.generate_stub(path).strip()
    return '\n'.join(line for line in result.splitlines() if line)


def test_inferno_expr(tmp_path):
    source = dedent("""
        def f(x):
            return len(x)
    """)
    result = get_stubs(tmp_path, source)
    assert result == 'def f(x) -> int: ...'


def test_infer_bare_return(tmp_path):
    source = dedent("""
        def f(x):
            if x == y:
                return
            return 13
    """)
    result = get_stubs(tmp_path, source)
    assert result == 'def f(x) -> int | None: ...'


def test_skip_subfuncs(tmp_path):
    source = dedent("""
        def f(x):
            def f2():
                return 'hello'
            return 13
    """)
    result = get_stubs(tmp_path, source)
    assert result == 'def f(x) -> int: ...'


def test_cannot_infer_expr(tmp_path):
    source = dedent("""
        def f(x):
            return min(x)
    """)
    result = get_stubs(tmp_path, source)
    assert result == ''


def test_skip_annotated(tmp_path):
    source = dedent("""
        def f() -> int:
            return "hi"
    """)
    result = get_stubs(tmp_path, source)
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
def test_preserve_args(tmp_path, expr):
    source = dedent(f"""
        def f({expr}):
            return 1
    """)
    result = get_stubs(tmp_path, source)
    assert result == f'def f({expr}) -> int: ...'


def test_infer_class_methods(tmp_path):
    given = dedent("""
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
    actual = get_stubs(tmp_path, given)
    lactual = [line for line in actual.splitlines() if line]
    lexpected = [line for line in expected.splitlines() if line]
    assert lactual == lexpected


def test_preserve_property_decorator(tmp_path):
    given = dedent("""
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
    actual = get_stubs(tmp_path, given)
    lactual = [line for line in actual.splitlines() if line]
    lexpected = [line for line in expected.splitlines() if line]
    assert lactual == lexpected


def test_preserve_cached_property_decorator(tmp_path):
    given = dedent("""
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
    actual = get_stubs(tmp_path, given)
    lactual = [line for line in actual.splitlines() if line]
    lexpected = [line for line in expected.splitlines() if line]
    assert lactual == lexpected


def test_cannot_infer_class_methods(tmp_path):
    given = dedent("""
        class C:
            def m(self, x):
                return x
    """)
    assert get_stubs(tmp_path, given) == ""


def test_can_infer_only_one(tmp_path):
    given = dedent("""
        def f(x):
            if x == y:
                return x
            else:
                return 13
    """)
    expected = dedent("def f(x) -> int: ...")
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


def test_detect_bare_return(tmp_path):
    source = dedent("""
        def f(x):
            if x:
                return
            do_something()
    """)
    result = get_stubs(tmp_path, source)
    assert result == 'def f(x) -> None: ...'


def test_detect_no_return(tmp_path):
    source = dedent("""
        def f():
            do_something()
    """)
    result = get_stubs(tmp_path, source)
    assert result == 'def f() -> None: ...'


def test_detect_yield(tmp_path):
    source = dedent("""
        def f():
            yield x
    """)
    result = get_stubs(tmp_path, source)
    assert result == 'from typing import Iterator\ndef f() -> Iterator: ...'
