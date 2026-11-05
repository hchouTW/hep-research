"""params (Section 6.5): named values and expressions of safe arithmetic, evaluated with exact decimals.

An expression holds numeric literals, identifiers [a-z_][a-z0-9_]*, + - * / and parentheses, and nothing else: it is parsed
here, never handed to eval. A params table may refer to itself in any order; a cycle or an unknown name is an error.
"""
from __future__ import annotations

import re
from decimal import Decimal, DivisionByZero, InvalidOperation

from core.geometry.numbers import CONTEXT, GeometryError, add, divide, exact, multiply, subtract

_TOKEN = re.compile(r"\s*(?:(?P<number>(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)(?![a-zA-Z0-9_.])"
                    r"|(?P<name>[a-z_][a-z0-9_]*)|(?P<op>[-+*/()]))", re.ASCII)


def tokens(text: str) -> list[tuple[str, str]]:
    found, position, end = [], 0, len(text.rstrip())
    while position < end:
        match = _TOKEN.match(text, position)
        if match is None:
            raise GeometryError("params-syntax", f"{text[:80]!r}: cannot read from position {position}")
        kind = match.lastgroup or ""
        found.append((kind, match.group(kind)))
        position = match.end()
    return found


class _Parser:
    def __init__(self, text: str, lookup):
        self.text, self.items, self.at, self.lookup = text, tokens(text), 0, lookup

    def peek(self):
        return self.items[self.at] if self.at < len(self.items) else (None, None)

    def take(self):
        item = self.peek()
        self.at += 1
        return item

    def expression(self) -> Decimal:
        value = self.term()
        while self.peek() in (("op", "+"), ("op", "-")):
            value = (add if self.take()[1] == "+" else subtract)(value, self.term())
        return value

    def term(self) -> Decimal:
        value = self.factor()
        while self.peek() in (("op", "*"), ("op", "/")):
            value = (multiply if self.take()[1] == "*" else divide)(value, self.factor())
        return value

    def factor(self) -> Decimal:
        kind, text = self.take()
        if (kind, text) == ("op", "-"):
            return CONTEXT.minus(self.factor())
        if (kind, text) == ("op", "+"):
            return self.factor()
        if (kind, text) == ("op", "("):
            value = self.expression()
            if self.take() != ("op", ")"):
                raise GeometryError("params-syntax", f"{self.text[:80]!r}: a parenthesis is not closed")
            return value
        if kind == "number":
            return CONTEXT.plus(exact(text))
        if kind == "name":
            return self.lookup(text)
        raise GeometryError("params-syntax", f"{self.text[:80]!r}: an expression is incomplete")


def evaluate(text, lookup) -> Decimal:
    """The value of a numeric literal or expression; lookup(name) gives the value of an identifier."""
    if not isinstance(text, str):
        raise GeometryError("params-syntax", f"{text!r} is not a string")
    parser = _Parser(text, lookup)
    try:
        value = parser.expression()
    except DivisionByZero:
        raise GeometryError("params-division", f"{text[:80]!r} divides by zero") from None
    except InvalidOperation:
        raise GeometryError("params-range", f"{text[:80]!r} has no value") from None
    if parser.peek() != (None, None):
        raise GeometryError("params-syntax", f"{text[:80]!r}: unexpected {parser.peek()[1]!r}")
    return value


def resolve(table: dict) -> dict[str, Decimal]:
    """Every entry of a params table as an exact value."""
    values: dict[str, Decimal] = {}
    active: list[str] = []

    def lookup(name: str) -> Decimal:
        if name in values:
            return values[name]
        if name in active:
            raise GeometryError("params-cycle", " -> ".join([*active[active.index(name):], name]))
        if name not in table:
            raise GeometryError("params-unknown", f"{name!r} is not in params")
        active.append(name)
        values[name] = evaluate(table[name], lookup)
        active.pop()
        return values[name]

    for name in table:
        if re.fullmatch(r"[a-z_][a-z0-9_]*", name, re.ASCII) is None:
            raise GeometryError("params-name", f"{name!r} is not an identifier")
        lookup(name)
    return values


def names_in(text: str) -> list[str]:
    """The identifiers of an expression, in order: the derivation of a value inherits their sources."""
    return [value for kind, value in tokens(text) if kind == "name"]
