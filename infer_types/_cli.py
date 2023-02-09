from __future__ import annotations
from dataclasses import dataclass

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import NoReturn, TextIO

from ._format import format_code
from ._inferno import Inferno


@dataclass(frozen=True)
class Config:
    format: bool
    stream: TextIO


def generate_stubs(root: Path, config: Config) -> None:
    inferno = Inferno()
    for path in root.iterdir():
        if path.is_dir():
            generate_stubs(path, config)
            continue
        if path.suffix != '.py':
            continue
        new_source = inferno.transform(path)
        if config.format:
            new_source = format_code(new_source)
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
    args = parser.parse_args(argv)
    config = Config(format=args.format, stream=stream)
    generate_stubs(args.dir, config)
    return 0


def entrypoint() -> NoReturn:
    sys.exit(main(sys.argv[1:], sys.stdout))
