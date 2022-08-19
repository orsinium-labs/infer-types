from pathlib import Path
import sys
import subprocess

SOURCE = """
def f(x):
    return len(x)
"""


def test_main(tmp_path: Path):
    spath = tmp_path / 'source'
    spath.mkdir()
    (spath / 'example.py').write_text(SOURCE)
    tpath = tmp_path / 'types'
    flags = ['--pyi-dir', str(tpath), str(spath)]
    res = subprocess.run([sys.executable, '-m', 'infer_types', *flags])
    assert res.returncode == 0
    out_path = tpath / 'example.pyi'
    assert out_path.exists()
