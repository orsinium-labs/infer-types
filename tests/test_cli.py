from io import StringIO
from pathlib import Path
from textwrap import dedent
from infer_types import main

GIVEN = """
    def f(x):
        return len(x)
"""

EXPECTED = """
    def f(x) -> int:
        return len(x)
"""


def test_main(tmp_path: Path):
    # prepare files and dirs
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    source_file = source_dir / 'example.py'
    source_file.write_text(dedent(GIVEN))

    # call the CLI
    stream = StringIO()
    code = main([str(source_dir)], stream)
    assert code == 0

    # check stdout
    stream.seek(0)
    stdout = stream.read()
    assert 'example.py' in stdout

    # check modifications
    assert source_file.read_text() == dedent(EXPECTED)
