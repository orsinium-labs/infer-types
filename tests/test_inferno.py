from pathlib import Path
from textwrap import dedent
from typing import Callable

import pytest

from infer_types._inferno import Inferno


@pytest.fixture
def transform(tmp_path: Path) -> Callable:
    def callback(source: str) -> str:
        inferno = Inferno()
        path = tmp_path / 'example.py'
        source = dedent(source)
        path.write_text(source)
        return inferno.transform(path)
    return callback


@pytest.mark.parametrize('fused', [
    # basic inference
    """
    def f(x):
        return len(x)
    ---
    def f(x) -> int:
        return len(x)
    """,
    # bare return has type None
    """
    def f(x):
        if x == y:
            return
        return 13
    ---
    def f(x) -> int | None:
        if x == y:
            return
        return 13
    """,
    # nested functions must be ignored
    """
    def f(x):
        def f2():
            return 'hello'
        return 13
    ---
    def f(x) -> int:
        def f2():
            return 'hello'
        return 13
    """,
    # multiple returns with the same type
    """
    def f(x):
        if x == y:
            return 12
        return 13
    ---
    def f(x) -> int:
        if x == y:
            return 12
        return 13
    """,
    # cannot infer, do not modify
    """
    def f(x):
        return min(x)
    ---
    def f(x):
        return min(x)
    """,
    # skip already annotated
    """
    def f() -> int:
        return "hi"
    ---
    def f() -> int:
        return "hi"
    """,
    # infer class methods
    """
    SOMETHING = 13
    class C:
        some_attr: str = 14
        def m(self, x):
            return 13
    ---
    SOMETHING = 13
    class C:
        some_attr: str = 14
        def m(self, x) -> int:
            return 13
    """,
    # cannot infer some class methods
    """
    class C:
        def m(self, x):
            return x
    ---
    class C:
        def m(self, x):
            return x
    """,
    # can infer only one return statement, roll with it
    """
    def f(x):
        if x == y:
            return x
        else:
            return 13
    ---
    def f(x) -> int:
        if x == y:
            return x
        else:
            return 13
    """,
    # bare return
    """
    def f(x):
        if x:
            return
        do_something()
    ---
    def f(x) -> None:
        if x:
            return
        do_something()
    """,
    # no return
    """
    def f(x):
        do_something()
    ---
    def f(x) -> None:
        do_something()
    """,
    # magic method
    """
    class A:
        def __str__(self):
            return x
    ---
    class A:
        def __str__(self) -> str:
            return x
    """,
    # yield
    """
    def f():
        yield x
    ---
    from typing import Iterator
    def f() -> Iterator:
        yield x
    """,
    # inherit types
    """
    class A:
        def f(self) -> str:
            return x

    class B(A):
        def f(self):
            return y
    ---
    class A:
        def f(self) -> str:
            return x

    class B(A):
        def f(self) -> str:
            return y
    """,
    # preserve decorators
    """
    from functools import cached_property

    class C:
        @cached_property
        def m(self, x):
            return 13
    ---
    from functools import cached_property

    class C:
        @cached_property
        def m(self, x) -> int:
            return 13
    """,
    # preserve multiple decorators
    """
    class C:
        @property
        @garbage
        def m(self, x):
            return 13
    ---
    class C:
        @property
        @garbage
        def m(self, x) -> int:
            return 13
    """,
    # insert imports for methods
    """
    class C:
        def m(self, x):
            yield 12
    ---
    from typing import Iterator
    class C:
        def m(self, x) -> Iterator:
            yield 12
    """,
    # don't infer no return for empty base class methods
    """
    class A:
        def m(self, x):
            raise NotImplementedError
    ---
    class A:
        def m(self, x):
            raise NotImplementedError
    """,
    """
    class A:
        def m(self, x):
            "some docstring"
    ---
    class A:
        def m(self, x):
            "some docstring"
    """,
    """
    class A:
        def m(self, x):
            pass
    ---
    class A:
        def m(self, x):
            pass
    """,
    """
    class A:
        def m(self, x):
            ...
    ---
    class A:
        def m(self, x):
            ...
    """,
    # infer no return for methods
    """
    class A:
        def m(self, x):
            pass
            1 + 2
    ---
    class A:
        def m(self, x) -> None:
            pass
            1 + 2
    """,
    """
    class A:
        def m(self, x):
            13
    ---
    class A:
        def m(self, x) -> None:
            13
    """,
])
def test_inferno(transform, fused: str) -> None:
    given, expected = fused.split('---')
    assert transform(given) == dedent(expected)


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
def test_preserve_args(transform, expr):
    given = f"""
        def f({expr}):
            return 1
    """
    expected = f"""
        def f({expr}) -> int:
            return 1
    """
    assert transform(given) == dedent(expected)


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
def test_import_types(transform, g_imp, g_expr, e_imp, e_type):
    given = f"""
        {g_imp}

        def f():
            return {g_expr}
    """
    expected = f"""
        {g_imp}

        {e_imp}
        def f() -> {e_type}:
            return {g_expr}
    """
    assert transform(given) == dedent(expected)


@pytest.mark.parametrize('f_name, e_type', [
    ('is_user', 'bool'),
    ('has_access', 'bool'),
    ('exists', 'bool'),
    ('contains', 'bool'),
    ('size', 'int'),
    ('get_size', 'int'),
    ('as_dict', 'dict'),
    ('to_dict', 'dict'),
    ('dumps', 'str'),
    ('should_fail', 'bool'),
    ('can_fail', 'bool'),
    ('will_fail', 'bool'),
    ('supports_pickups', 'bool'),
    ('created_at', 'datetime'),
    ('updated_at', 'datetime'),
])
def test_infer_type_from_function_name(transform, f_name, e_type):
    given = f"""
        def {f_name}(x):
            return x
    """
    expected = dedent(f"""
        def {f_name}(x) -> {e_type}:
            return x
    """)
    actual = transform(given)
    if e_type == 'datetime':
        expected = expected.replace('def', 'from datetime import datetime\ndef')
    assert actual == expected
