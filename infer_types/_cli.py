from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import NoReturn, TextIO

from ._format import format_code
from ._inferno import Inferno


def generate_stubs(in_dir: Path, out_dir: Path, stream: TextIO) -> None:
    inferno = Inferno()
    for in_path in in_dir.iterdir():
        if in_path.is_dir():
            generate_stubs(in_path, out_dir / in_path.name, stream)
            continue
        if in_path.suffix != '.py':
            continue
        stub_source = inferno.generate_stub(in_path)
        if not stub_source.strip():
            continue
        stub_source = format_code(stub_source)
        out_dir.mkdir(exist_ok=True, parents=True)
        out_path = out_dir / f'{in_path.stem}.pyi'
        out_path.write_text(stub_source)
        print(out_path, file=stream)


def main(argv: list[str], stream: TextIO) -> int:
    parser = ArgumentParser()
    parser.add_argument(
        'dir', type=Path, default=Path(),
        help='path to directory with the source code to analyze'
    )
    parser.add_argument(
        '--pyi-dir', type=Path, default=Path('types'),
        help='path to directory to output generated stub files',
    )
    args = parser.parse_args(argv)
    generate_stubs(args.dir, args.pyi_dir, stream)
    return 0


def entrypoint() -> NoReturn:
    sys.exit(main(sys.argv[1:], sys.stdout))
