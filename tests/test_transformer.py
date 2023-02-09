from textwrap import dedent

import astroid

from infer_types._transformer import InsertReturnType, Transformer


def add_ret_ann(given: str, annotation: str) -> str:
    tr = Transformer(dedent(given))
    tree = astroid.parse(given)
    patch = InsertReturnType(tree.body[0], annotation)
    tr.add(patch)
    return tr.apply()


def test_simple() -> None:
    given = """
        def f():
            pass
    """
    expected = """
        def f() -> int:
            pass
    """
    actual = add_ret_ann(given, 'int')
    assert actual == dedent(expected)


def test_with_args() -> None:
    given = """
        def f(a: int, b):
            pass
    """
    expected = """
        def f(a: int, b) -> int:
            pass
    """
    actual = add_ret_ann(given, 'int')
    assert actual == dedent(expected)


def test_multiline() -> None:
    given = """
        def f(
            a: int,
            b: float,
        ):
            pass
    """
    expected = """
        def f(
            a: int,
            b: float,
        ) -> str:
            pass
    """
    actual = add_ret_ann(given, 'str')
    assert actual == dedent(expected)


def test_empty_body() -> None:
    given = """
        def f(a, b: str):
            '''hello'''
    """
    expected = """
        def f(a, b: str) -> int:
            '''hello'''
    """
    actual = add_ret_ann(given, 'int')
    assert actual == dedent(expected)
