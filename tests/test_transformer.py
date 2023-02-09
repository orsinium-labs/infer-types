from textwrap import dedent
from infer_types._transformer import Transformer, InsertReturnType
from pathlib import Path


def transform(
    tmp_path: Path,
    given: str,
    *patches: InsertReturnType,
) -> str:
    file_path = tmp_path / 'example.py'
    file_path.write_text(dedent(given))
    tr = Transformer(path=file_path)
    for patch in patches:
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
    actual = transform(tmp_path, given, InsertReturnType(1, 'int'))
    assert actual == dedent(expected)
