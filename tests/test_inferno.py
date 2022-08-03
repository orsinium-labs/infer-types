from pathlib import Path
from textwrap import dedent

import pytest
from infer_types._inferno import Inferno


def get_stubs(tmp_path: Path, source: str) -> str:
    inferno = Inferno()
    path = tmp_path / 'example.py'
    path.write_text(source)
    return inferno.generate_stub(path)


@pytest.mark.parametrize('expr, type', [
    # literals
    ('1', 'int'),
    ('1.2', 'float'),
    ('"hi"', 'str'),
    ('f"hi"', 'str'),
    ('b"hi"', 'bytes'),
    ('""', 'str'),
    ('None', 'None'),
    ('', 'None'),
    ('True', 'bool'),

    # operations with known type
    ('not x', 'bool'),
    ('x is str', 'bool'),

    # operations with assumptions
    ('x in (1, 2, 3)', 'bool'),
    ('x < 10', 'bool'),
    ('~13', 'int'),
    ('+13', 'int'),

    # methos of builtins
    ('"".join(x)', 'str'),
])
def test_inferno_expr(tmp_path, expr, type):
    source = dedent(f"""
        def f():
            return {expr}
    """)
    result = get_stubs(tmp_path, source)
    assert result.strip() == f'def f() -> {type}: ...'
