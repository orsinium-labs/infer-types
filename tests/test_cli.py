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


def test_recursive_file_lookup(tmp_path: Path):
    # prepare files and dirs
    source_dir1 = tmp_path / 'source'
    source_dir1.mkdir()
    source_dir2 = source_dir1 / 'subdir'
    source_dir2.mkdir()
    source_file1 = source_dir1 / 'example1.py'
    source_file2 = source_dir2 / 'example2.py'
    source_file1.write_text(dedent(GIVEN))
    source_file2.write_text(dedent(GIVEN))

    # call the CLI
    stream = StringIO()
    code = main([str(tmp_path)], stream)
    assert code == 0

    # check modifications
    assert source_file1.read_text() == dedent(EXPECTED)
    assert source_file2.read_text() == dedent(EXPECTED)


def test_skip_migrations(tmp_path: Path):
    # prepare files and dirs
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    migrations_dir = source_dir / 'migrations'
    migrations_dir.mkdir()
    source_file = source_dir / 'example1.py'
    migration_file = migrations_dir / 'example2.py'
    source_file.write_text(dedent(GIVEN))
    migration_file.write_text(dedent(GIVEN))

    # call the CLI
    stream = StringIO()
    code = main([str(tmp_path), '--skip-migrations'], stream)
    assert code == 0

    # check modifications
    assert source_file.read_text() == dedent(EXPECTED)
    assert migration_file.read_text() == dedent(GIVEN)


def test_skip_tests(tmp_path: Path):
    # prepare files and dirs
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    source_file = source_dir / 'example.py'
    test_file = source_dir / 'test_example.py'
    source_file.write_text(dedent(GIVEN))
    test_file.write_text(dedent(GIVEN))

    # call the CLI
    stream = StringIO()
    code = main([str(tmp_path), '--skip-tests'], stream)
    assert code == 0

    # check modifications
    assert source_file.read_text() == dedent(EXPECTED)
    assert test_file.read_text() == dedent(GIVEN)


def test_skip_non_python(tmp_path: Path):
    # prepare files and dirs
    source_dir = tmp_path / 'source'
    source_dir.mkdir()
    source_file = source_dir / 'example.py'
    ruby_file = source_dir / 'example.rb'
    source_file.write_text(dedent(GIVEN))
    ruby_file.write_text(dedent(GIVEN))

    # call the CLI
    stream = StringIO()
    code = main([str(tmp_path)], stream)
    assert code == 0

    # check modifications
    assert source_file.read_text() == dedent(EXPECTED)
    assert ruby_file.read_text() == dedent(GIVEN)


def test_format_doesnt_explode(tmp_path: Path):
    # prepare files and dirs
    source_file = tmp_path / 'example.py'
    source_file.write_text(dedent(GIVEN))
    # call the CLI
    stream = StringIO()
    code = main([str(tmp_path), '--format'], stream)
    assert code == 0


def test_no_imports(tmp_path: Path):
    given = """
        def f1():
            return 1

        def f2():
            yield 1

        class A:
            def f1(self):
                return 1

            def f2(self):
                yield 1
    """
    expected = """
        def f1() -> int:
            return 1

        def f2():
            yield 1

        class A:
            def f1(self) -> int:
                return 1

            def f2(self):
                yield 1
    """

    # prepare files and dirs
    source_file = tmp_path / 'example.py'
    source_file.write_text(dedent(given))
    # call the CLI
    stream = StringIO()
    code = main([str(tmp_path), '--no-imports'], stream)
    assert code == 0
    assert source_file.read_text() == dedent(expected)


def test_no_methods(tmp_path: Path):
    given = """
        def f1():
            return 1

        def f2(x):
            yield x

        class A:
            def f1(self):
                return 1

            def f2(self):
                yield 1
    """
    expected = """
        def f1() -> int:
            return 1

        from typing import Iterator
        def f2(x) -> Iterator:
            yield x

        class A:
            def f1(self):
                return 1

            def f2(self):
                yield 1
    """

    # prepare files and dirs
    source_file = tmp_path / 'example.py'
    source_file.write_text(dedent(given))
    # call the CLI
    stream = StringIO()
    code = main([str(tmp_path), '--no-methods'], stream)
    assert code == 0
    assert source_file.read_text() == dedent(expected)


def test_no_functions(tmp_path: Path):
    given = """
        def f1():
            return 1

        def f2(x):
            yield x

        class A:
            def f1(self):
                return 1

            def f2(self, x):
                yield x
    """
    expected = """
        def f1():
            return 1

        def f2(x):
            yield x

        from typing import Iterator
        class A:
            def f1(self) -> int:
                return 1

            def f2(self, x) -> Iterator:
                yield x
    """

    # prepare files and dirs
    source_file = tmp_path / 'example.py'
    source_file.write_text(dedent(given))
    # call the CLI
    stream = StringIO()
    code = main([str(tmp_path), '--no-functions'], stream)
    assert code == 0
    assert source_file.read_text() == dedent(expected)


def test_no_assumptions(tmp_path: Path):
    given = """
        def f1():
            return 1

        def f2(x):
            if x:
                return x
            return 1
    """
    expected = """
        def f1() -> int:
            return 1

        def f2(x):
            if x:
                return x
            return 1
    """

    # prepare files and dirs
    source_file = tmp_path / 'example.py'
    source_file.write_text(dedent(given))
    # call the CLI
    stream = StringIO()
    code = main([str(tmp_path), '--no-assumptions'], stream)
    assert code == 0
    assert source_file.read_text() == dedent(expected)


def test_only(tmp_path: Path):
    given = """
        def f1():
            return 1

        def is_used(x):
            return x
    """
    expected = """
        def f1():
            return 1

        def is_used(x) -> bool:
            return x
    """

    # prepare files and dirs
    source_file = tmp_path / 'example.py'
    source_file.write_text(dedent(given))
    # call the CLI
    stream = StringIO()
    code = main([str(tmp_path), '--only', 'name'], stream)
    assert code == 0
    assert source_file.read_text() == dedent(expected)
