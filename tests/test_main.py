import subprocess
import sys
from pathlib import Path
from textwrap import dedent


SOURCE = """
    def f(x):
        return len(x)
"""

EXPECTED = """
    def f(x) -> int:
        return len(x)
"""


def test_main(tmp_path: Path):
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    source_file = source_dir / 'example.py'
    source_file.write_text(dedent(SOURCE))
    res = subprocess.run([sys.executable, '-m', 'infer_types', str(source_dir)])
    assert res.returncode == 0
    assert source_file.read_text() == dedent(EXPECTED)
