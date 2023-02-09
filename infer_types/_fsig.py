from __future__ import annotations

from dataclasses import dataclass

from astypes import Type


@dataclass
class FSig:
    name: str
    args: str
    return_type: Type

    @property
    def imports(self) -> frozenset[str]:
        return self.return_type.imports

    @property
    def annotation(self) -> str:
        return self.return_type.annotation
