#!/usr/bin/env python3
"""Read a strict YAML subset into plain Python data (the form `json.loads` returns).

Purpose: let a specification for `audit_analysis_spec.py` be written as YAML
without an external dependency. It supports exactly what a specification needs and
rejects everything else with a line number, so a document is never silently
misread.

Supported: block mappings and block sequences (spaces only), `key:` followed by a
sequence at the same indent, `- key: value` list items, scalars (null `null`/`~`/empty,
`true`/`false`, integers, floats that contain a point or exponent, single- and
double-quoted strings, plain strings), `#` comments, `|` and `>` block scalars with
an optional `-` chomp, one-line flow sequences `[a, b]` and flow mappings `{k: v}`,
and one leading `---`.
Not supported (error): anchors, aliases, tags, directives, multiple documents,
multi-line plain/quoted/flow scalars, complex `?` keys, merge keys, tab indentation,
duplicate keys, `+`/indent-digit block scalar headers, a plain scalar containing
`: ` (quote it). Deliberate differences from full YAML: `yes`/`no`/`on`/`off` are
strings (YAML 1.2 style), dates such as 2011-05-19 stay strings (no date type, as in
JSON), `.inf`/`.nan` and hex or octal integers stay strings, and every key is a string.

Usage (from the skill directory):
  python3 scripts/yaml_subset.py FILE.yaml        # print the parsed document as JSON
Importable: `yaml_subset.loads(text)` raises `YamlSubsetError` (a ValueError).
Exit codes: 0 parsed; 2 file unreadable or not in the supported subset.
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


class YamlSubsetError(ValueError):
    """The text is not in the supported YAML subset; the message carries the line number."""


_INT = re.compile(r"[-+]?\d+\Z")
_FLOAT = re.compile(r"[-+]?(\d+\.\d*|\.\d+|\d+)([eE][-+]?\d+)?\Z")
_UNSUPPORTED_START = "&*!%@`"
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\", "/": "/", "0": "\0"}


def _err(lineno: int, msg: str) -> YamlSubsetError:
    return YamlSubsetError(f"line {lineno}: {msg}")


def _plain(s: str):
    if s in ("", "~", "null", "Null", "NULL"):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if _INT.match(s):
        return int(s)
    if _FLOAT.match(s) and any(c in s for c in ".eE"):
        return float(s)
    return s


def _strip_comment(s: str) -> str:
    """Cut a trailing ` # comment` that is outside quotes."""
    quote = None
    i = 0
    while i < len(s):
        c = s[i]
        if quote == '"':
            if c == "\\":
                i += 1
            elif c == '"':
                quote = None
        elif quote == "'":
            if c == "'":
                if s[i + 1:i + 2] == "'":
                    i += 1
                else:
                    quote = None
        elif c in "\"'" and (i == 0 or s[i - 1] in " \t[{,:-"):
            quote = c
        elif c == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i].rstrip()
        i += 1
    return s.rstrip()


def _read_quoted(s: str, i: int, lineno: int) -> tuple[str, int]:
    """Parse a quoted string starting at s[i]; return (value, index after the closing quote)."""
    q = s[i]
    out = []
    i += 1
    while i < len(s):
        c = s[i]
        if q == "'":
            if c == "'":
                if s[i + 1:i + 2] == "'":
                    out.append("'")
                    i += 2
                    continue
                return "".join(out), i + 1
            out.append(c)
        else:
            if c == "\\":
                i += 1
                e = s[i:i + 1]
                if e == "u":
                    hexa = s[i + 1:i + 5]
                    if not re.fullmatch(r"[0-9a-fA-F]{4}", hexa):
                        raise _err(lineno, "bad \\u escape")
                    out.append(chr(int(hexa, 16)))
                    i += 4
                elif e in _ESCAPES:
                    out.append(_ESCAPES[e])
                else:
                    raise _err(lineno, f"unsupported escape \\{e}")
            elif c == '"':
                return "".join(out), i + 1
            else:
                out.append(c)
        i += 1
    raise _err(lineno, "unterminated quoted string (multi-line quoted scalars are not supported)")


class _Flow:
    """One-line flow collections: [a, b] and {k: v}, nested."""

    def __init__(self, s: str, lineno: int):
        self.s, self.i, self.ln = s, 0, lineno

    def _ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t":
            self.i += 1

    def parse(self):
        v = self.value()
        self._ws()
        if self.i != len(self.s):
            raise _err(self.ln, f"unexpected text after flow collection: {self.s[self.i:]!r}")
        return v

    def value(self, in_map_key: bool = False):
        self._ws()
        if self.i >= len(self.s):
            raise _err(self.ln, "unterminated flow collection (multi-line flow is not supported)")
        c = self.s[self.i]
        if c == "[":
            return self.seq()
        if c == "{":
            return self.map()
        if c in "\"'":
            v, self.i = _read_quoted(self.s, self.i, self.ln)
            return v
        if c in _UNSUPPORTED_START or c in "|>?":
            raise _err(self.ln, f"unsupported YAML feature starting with {c!r}")
        j = self.i
        stops = ",]}" + (":" if in_map_key else "")
        while j < len(self.s) and self.s[j] not in stops:
            if self.s[j] == ":" and self.s[j + 1:j + 2] in (" ", ""):
                raise _err(self.ln, "a plain scalar may not contain ': ' (quote it)")
            j += 1
        raw = self.s[self.i:j].strip()
        self.i = j
        return raw if in_map_key else _plain(raw)

    def seq(self):
        self.i += 1
        out = []
        self._ws()
        if self.s[self.i:self.i + 1] == "]":
            self.i += 1
            return out
        while True:
            out.append(self.value())
            self._ws()
            c = self.s[self.i:self.i + 1]
            self.i += 1
            if c == "]":
                return out
            if c == "":
                raise _err(self.ln, "unterminated flow collection (multi-line flow is not supported)")
            if c != ",":
                raise _err(self.ln, "expected ',' or ']' in flow sequence")
            self._ws()
            if self.s[self.i:self.i + 1] == "]":  # trailing comma
                self.i += 1
                return out

    def map(self):
        self.i += 1
        out = {}
        self._ws()
        if self.s[self.i:self.i + 1] == "}":
            self.i += 1
            return out
        while True:
            key = self.value(in_map_key=True)
            if not isinstance(key, str):
                key = str(key)
            self._ws()
            if self.s[self.i:self.i + 1] != ":":
                raise _err(self.ln, "expected ':' after key in flow mapping")
            self.i += 1
            if key in out:
                raise _err(self.ln, f"duplicate key {key!r}")
            out[key] = self.value()
            self._ws()
            c = self.s[self.i:self.i + 1]
            self.i += 1
            if c == "}":
                return out
            if c == "":
                raise _err(self.ln, "unterminated flow collection (multi-line flow is not supported)")
            if c != ",":
                raise _err(self.ln, "expected ',' or '}' in flow mapping")
            self._ws()
            if self.s[self.i:self.i + 1] == "}":
                self.i += 1
                return out


def _inline(text: str, lineno: int):
    """A value written on one line (after a key or a dash)."""
    s = _strip_comment(text).strip()
    if s[:1] in ("[", "{"):
        return _Flow(s, lineno).parse()
    if s[:1] in "\"'":
        v, end = _read_quoted(s, 0, lineno)
        if s[end:].strip():
            raise _err(lineno, f"unexpected text after quoted string: {s[end:]!r}")
        return v
    if s[:1] and (s[0] in _UNSUPPORTED_START or s[0] == "?"):
        raise _err(lineno, f"unsupported YAML feature (anchor, alias, tag, directive or complex key) at {s[:12]!r}")
    if ": " in s or s.endswith(":"):
        raise _err(lineno, "a plain scalar may not contain ': ' (quote it, or fix the indentation)")
    return _plain(s)


def _split_key(content: str, lineno: int):
    """Return (key, rest) when `content` is `key: rest` / `key:`; else None."""
    if content[:1] in ("[", "{"):
        return None
    if content[:1] in "\"'":
        key, end = _read_quoted(content, 0, lineno)
        after = content[end:]
        if after.startswith(":") and (len(after) == 1 or after[1] in " \t"):
            return key, after[1:].strip()
        return None
    m = re.search(r":(?:\s|\Z)", content)
    if not m:
        return None
    key = content[:m.start()].strip()
    if not key:
        raise _err(lineno, "empty key")
    if key[0] in _UNSUPPORTED_START or key[0] == "?":
        raise _err(lineno, f"unsupported YAML feature at key {key[:12]!r}")
    if key == "<<":
        raise _err(lineno, "merge keys are not supported")
    return key, content[m.end():].strip()


class _Parser:
    def __init__(self, text: str):
        if text.startswith("﻿"):
            text = text[1:]
        self.lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        self.pos = 0

    @staticmethod
    def _indent(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    def _skip(self):
        while self.pos < len(self.lines):
            s = self.lines[self.pos].strip()
            if s and not s.startswith("#"):
                return
            self.pos += 1

    def _peek(self):
        """(indent, content, lineno) of the next meaningful line, or None at the end."""
        self._skip()
        if self.pos >= len(self.lines):
            return None
        line = self.lines[self.pos]
        ln = self.pos + 1
        lead = line[:len(line) - len(line.lstrip(" \t"))]
        if "\t" in lead:
            raise _err(ln, "tab in indentation (use spaces)")
        content = line.strip()
        if line.startswith(("---", "...")) and (len(line) == 3 or line[3] in " \t"):
            raise _err(ln, "document markers inside the file (multiple documents) are not supported")
        return self._indent(line), content, ln

    def document(self):
        self._skip()
        if self.pos < len(self.lines) and self.lines[self.pos].strip() == "---":
            self.pos += 1
        for ln, raw in enumerate(self.lines[self.pos:], self.pos + 1):
            if raw.startswith("%"):
                raise _err(ln, "directives are not supported")
        nxt = self._peek()
        if nxt is None:
            return None
        value = self._node(nxt[0])
        extra = self._peek()
        if extra is not None:
            raise _err(extra[2], "unexpected content (inconsistent indentation or a second top-level value)")
        return value

    def _node(self, min_indent: int):
        nxt = self._peek()
        if nxt is None or nxt[0] < min_indent:
            return None
        ind, content, ln = nxt
        if content == "-" or content.startswith("- "):
            return self._seq(ind)
        if _split_key(_strip_comment(content), ln) is not None:
            return self._map(ind)
        self.pos += 1
        return _inline(content, ln)

    def _block_scalar(self, header: str, parent_indent: int, lineno: int) -> str:
        if header not in ("|", ">", "|-", ">-"):
            raise _err(lineno, f"unsupported block scalar header {header!r} (only |, >, |-, >-)")
        folded, strip = header[0] == ">", header.endswith("-")
        body: list[str] = []
        content_indent = None
        while self.pos < len(self.lines):
            raw = self.lines[self.pos]
            if not raw.strip():
                body.append("")
                self.pos += 1
                continue
            ind = self._indent(raw)
            if "\t" in raw[:len(raw) - len(raw.lstrip(" \t"))]:
                raise _err(self.pos + 1, "tab in indentation (use spaces)")
            if ind <= parent_indent:
                break
            if content_indent is None:
                content_indent = ind
            if ind < content_indent:
                raise _err(self.pos + 1, "block scalar line indented less than its first line")
            body.append(raw[content_indent:])
            self.pos += 1
        while body and body[-1] == "":
            body.pop()
        if not body:
            return ""
        if folded:
            text, prev, blanks = "", None, 0
            for b in body:
                if b == "":
                    blanks += 1
                    continue
                kind = "more" if b.startswith(" ") else "text"
                if text == "":
                    text = b
                elif blanks:
                    text += "\n" * blanks + b
                elif kind == "text" and prev == "text":
                    text += " " + b
                else:
                    text += "\n" + b
                prev, blanks = kind, 0
        else:
            text = "\n".join(body)
        return text if strip else text + "\n"

    def _value_after_key_or_dash(self, rest: str, parent_indent: int, lineno: int, same_indent_seq: bool):
        """The value following `key:` or `-` on the same line (rest) or on the lines below."""
        rest_nc = _strip_comment(rest).strip()
        if rest_nc == "":
            nxt = self._peek()
            if nxt is None:
                return None
            ind, content, _ = nxt
            if ind > parent_indent:
                return self._node(parent_indent + 1)
            if same_indent_seq and ind == parent_indent and (content == "-" or content.startswith("- ")):
                return self._seq(parent_indent)
            return None
        if rest_nc[0] in "|>":
            return self._block_scalar(rest_nc, parent_indent, lineno)
        return _inline(rest_nc, lineno)

    def _map(self, ind: int):
        out = {}
        while True:
            nxt = self._peek()
            if nxt is None or nxt[0] < ind:
                return out
            cur, content, ln = nxt
            if cur > ind:
                raise _err(ln, "unexpected indentation (multi-line plain scalars are not supported)")
            if content == "-" or content.startswith("- "):
                return out
            kv = _split_key(content, ln)
            if kv is None:
                raise _err(ln, f"expected 'key: value', got {content[:40]!r}")
            key, rest = kv
            if key in out:
                raise _err(ln, f"duplicate key {key!r}")
            self.pos += 1
            out[key] = self._value_after_key_or_dash(rest, ind, ln, same_indent_seq=True)

    def _seq(self, ind: int):
        out = []
        while True:
            nxt = self._peek()
            if nxt is None or nxt[0] < ind:
                return out
            cur, content, ln = nxt
            if cur > ind:
                raise _err(ln, "unexpected indentation in a sequence")
            if not (content == "-" or content.startswith("- ")):
                return out
            rest = content[1:]
            lead = len(rest) - len(rest.lstrip(" "))
            item_indent = ind + 1 + lead
            rest_s = rest.strip()
            rest_nc = _strip_comment(rest_s)
            if rest_nc and rest_nc[0] not in "|>" and (
                    rest_nc == "-" or rest_nc.startswith("- ") or _split_key(rest_nc, ln) is not None):
                # nested sequence or mapping starting on the dash line: re-indent this line and parse it as a block
                self.lines[self.pos] = " " * item_indent + rest.lstrip(" ")
                out.append(self._node(item_indent))
                continue
            self.pos += 1
            out.append(self._value_after_key_or_dash(rest, ind, ln, same_indent_seq=False))


def loads(text: str):
    """Parse `text` (the supported YAML subset) into dicts, lists, str, int, float, bool and None."""
    return _Parser(text).document()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("file", type=Path, help="YAML file in the supported subset")
    args = parser.parse_args(argv)
    try:
        data = loads(args.file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"verdict": "unreadable", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
