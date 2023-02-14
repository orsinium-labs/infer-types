from __future__ import annotations

import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, TextIO

from ._extractors import extractors
from ._format import format_code
from ._inferno import Inferno


try:
    import ipdb as pdb
except ImportError:
    import pdb  # type: ignore[no-redef]


TEST_NAMES = frozenset({'tests.py', 'conftest.py'})


@dataclass(frozen=True)
class Config:
    format: bool            # run code formatters
    skip_tests: bool        # skip `test_*` files
    skip_migrations: bool   # skip `migrations/`
    exit_on_failure: bool   # propagate exceptions
    imports: bool           # allow annotations requiring imports
    methods: bool           # allow annotating methods
    functions: bool         # allow annotating functions
    assumptions: bool       # allow astypes to make assumptions
    dry: bool               # do not write changes in files
    only: frozenset[str]    # run only the these extractors
    stream: TextIO          # stdout


def add_annotations(root: Path, config: Config) -> None:
    inferno = Inferno(
        safe=not config.exit_on_failure,
        imports=config.imports,
        methods=config.methods,
        functions=config.functions,
        assumptions=config.assumptions,
        only=config.only,
    )
    for path in root.iterdir():
        if path.is_dir():
            if config.skip_migrations and path.name == 'migrations':
                continue
            add_annotations(path, config)
            continue
        if path.suffix != '.py':
            continue
        if config.skip_tests:
            if path.name.startswith('test_'):
                continue
            if path.name in TEST_NAMES:
                continue
            if 'tests' in path.parts:
                continue
        new_source = inferno.transform(path)
        if config.format:
            new_source = format_code(new_source)
        if not config.dry:
            path.write_text(new_source)
        print(path, file=config.stream)


def main(argv: list[str], stream: TextIO) -> int:
    parser = ArgumentParser()
    parser.add_argument(
        'dir', type=Path, default=Path(),
        help='path to the directory with the source code to analyze',
    )
    parser.add_argument(
        '--only', nargs='*', choices=sorted(name for name, _ in extractors),
        help='list of extractors to run (all by default)',
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
        '--no-imports', action='store_true',
        help='do not write annotations requiring imports',
    )
    parser.add_argument(
        '--no-methods', action='store_true',
        help='do not annotate methods',
    )
    parser.add_argument(
        '--no-functions', action='store_true',
        help='do not annotate functions',
    )
    parser.add_argument(
        '--no-assumptions', action='store_true',
        help='do not make any assumptions, avoid false-positives',
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
        assumptions=not args.no_assumptions,
        dry=args.dry,
        exit_on_failure=args.exit_on_failure or args.pdb,
        format=args.format,
        functions=not args.no_functions,
        imports=not args.no_imports,
        methods=not args.no_methods,
        only=args.only,
        skip_migrations=args.skip_migrations,
        skip_tests=args.skip_tests,
        stream=stream,
    )
    try:
        add_annotations(args.dir, config)
    except Exception:  # pragma: no cover
        pdb.post_mortem()
    return 0


def entrypoint() -> NoReturn:
    sys.exit(main(sys.argv[1:], sys.stdout))
