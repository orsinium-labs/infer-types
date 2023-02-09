from __future__ import annotations

import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, TextIO

from ._format import format_code
from ._inferno import Inferno


try:
    import ipdb as pdb
except ImportError:
    import pdb  # type: ignore[no-redef]


@dataclass(frozen=True)
class Config:
    format: bool
    skip_tests: bool
    skip_migrations: bool
    exit_on_failure: bool
    dry: bool
    stream: TextIO


def add_annotations(root: Path, config: Config) -> None:
    inferno = Inferno()
    for path in root.iterdir():
        if path.is_dir():
            if config.skip_migrations and path.name == 'migrations':
                continue
            add_annotations(path, config)
            continue
        if path.suffix != '.py':
            continue
        if config.skip_tests and path.name.startswith('test_'):
            continue
        new_source = inferno.transform(path, safe=not config.exit_on_failure)
        if config.format:
            new_source = format_code(new_source)
        if not config.dry:
            path.write_text(new_source)
        print(path, file=config.stream)


def main(argv: list[str], stream: TextIO) -> int:
    parser = ArgumentParser()
    parser.add_argument(
        'dir', type=Path, default=Path(),
        help='path to directory with the source code to analyze'
    )
    parser.add_argument(
        '--format', action='store_true',
        help='run available code formatters on the modified files',
    )
    parser.add_argument(
        '--skip-tests', action='store_true',
        help='skip test files (starting with `test_`)',
    )
    parser.add_argument(
        '--skip-migrations', action='store_true',
        help='skip Django migration files',
    )
    parser.add_argument(
        '--exit-on-failure', action='store_true',
        help='do not suppress exceptions during inference',
    )
    parser.add_argument(
        '--pdb', action='store_true',
        help='start debugger on failure',
    )
    parser.add_argument(
        '--dry', action='store_true',
        help='do not modify any files',
    )
    args = parser.parse_args(argv)
    config = Config(
        format=args.format,
        skip_tests=args.skip_tests,
        skip_migrations=args.skip_migrations,
        exit_on_failure=args.exit_on_failure or args.pdb,
        dry=args.dry,
        stream=stream,
    )
    try:
        add_annotations(args.dir, config)
    except Exception:  # pragma: no cover
        pdb.post_mortem()
    return 0


def entrypoint() -> NoReturn:
    sys.exit(main(sys.argv[1:], sys.stdout))
