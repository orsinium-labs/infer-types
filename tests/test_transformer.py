from textwrap import dedent
from infer_types._transformer import Transformer, InsertReturnType
from pathlib import Path
import astroid


def add_ret_ann(
    tmp_path: Path,
    given: str,
    annotation: str,
) -> str:
    file_path = tmp_path / 'example.py'
    file_path.write_text(dedent(given))
    tr = Transformer(path=file_path)
    tree = astroid.parse(given)
    patch = InsertReturnType(tree.body[0], annotation)
    tr.add(patch)
    tr.apply()
    return file_path.read_text()


def test_simple(tmp_path: Path) -> None:
    given = """
        def f():
            pass
    """
    expected = """
        def f() -> int:
            pass
    """
    actual = add_ret_ann(tmp_path, given, 'int')
    assert actual == dedent(expected)


def test_with_args(tmp_path: Path) -> None:
    given = """
        def f(a: int, b):
            pass
    """
    expected = """
        def f(a: int, b) -> int:
            pass
    """
    actual = add_ret_ann(tmp_path, given, 'int')
    assert actual == dedent(expected)


def test_multiline(tmp_path: Path) -> None:
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
    actual = add_ret_ann(tmp_path, given, 'str')
    assert actual == dedent(expected)


def test_empty_body(tmp_path: Path) -> None:
    given = """
        def f(a, b: str):
            '''hello'''
    """
    expected = """
        def f(a, b: str) -> int:
            '''hello'''
    """
    actual = add_ret_ann(tmp_path, given, 'int')
    assert actual == dedent(expected)
