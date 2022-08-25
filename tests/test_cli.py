from io import StringIO
from pathlib import Path
from textwrap import dedent
from infer_types import main

SOURCE = """
    def f(x):
        return len(x)
"""


def test_main(tmp_path: Path):
    # prepare files and dirs
    source_path = tmp_path / 'source'
    source_path.mkdir()
    (source_path / 'example.py').write_text(dedent(SOURCE))
    stubs_path = tmp_path / 'types'

    # call the CLI
    flags = ['--pyi-dir', str(stubs_path), str(source_path)]
    stream = StringIO()
    code = main(flags, stream)
    assert code == 0

    # check stdout
    stream.seek(0)
    stdout = stream.read()
    assert 'example.py' in stdout

    # check generated stub
    stub_path = stubs_path / 'example.pyi'
    assert stub_path.exists()
    stub = stub_path.read_text()
    assert 'def f(x) -> int:' in stub
