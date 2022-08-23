from __future__ import annotations

from dataclasses import dataclass
from astypes import Type


@dataclass
class FSig:
    name: str
    args: str
    return_type: Type

    @property
    def imports(self) -> set[str]:
        return self.return_type.imports

    @property
    def stub(self) -> str:
        rtype = self.return_type.annotation
        return f'def {self.name}({self.args}) -> {rtype}: ...'
