from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class FSig:
    name: str
    args: str
    return_type: Type

    @property
    def imp(self) -> set[str]:
        return self.return_type.imp

    @property
    def stub(self) -> str:
        return f'def {self.name}({self.args}) -> {self.return_type.rep}: ...'


class Ass(Enum):
    """Assumptions about the types that might be not true but usually are true.
    """
    # cannot infer type of one or more of the return statements,
    # assume all return statements to have the same type
    ALL_RETURNS_SAME = 'all-returns-same'
    # assume that comparison operations aren't overloaded
    NO_COMP_OVERLOAD = 'no-comp-overload'
    # assume that unary operators aren't overloaded
    NO_UNARY_OVERLOAD = 'no-unary-overload'
    # assume that all CamelCase names are types
    CAMEL_CASE_IS_TYPE = 'camel-case-is-type'
    # assume that built-in types and functions aren't shadowed
    NO_SHADOWING = 'camel-case-is-type'


@dataclass
class Type:
    rep: str
    ass: set[Ass] = field(default_factory=set)
    imp: set[str] = field(default_factory=set)

    def merge(self, other: Type) -> Type:
        if not self.rep or not other.rep:
            rep = self.rep or other.rep
        elif other.rep in self.rep:
            rep = self.rep
        else:
            rep = f'{self.rep} | {other.rep}'
        return Type(
            rep=rep,
            ass=self.ass | other.ass,
            imp=self.imp | other.imp,
        )
