"""Files that run under interpreters older than the plugin's 3.13 floor stay parseable by them, checked on any runner.

- core/partition/runner.py is copied to batch workers, which run Python 3.9;
- skills/hep-computing/scripts/find_python.py is started as `python3 find_python.py`, and `python3` may be old (macOS
  ships 3.9): it must run there to find a qualifying interpreter. Its PROBE string runs inside every candidate, so it
  keeps to syntax every Python 3 parses (checked at 3.7, the lowest version `ast` can parse as);
- core/interpreter_guard.py runs first in every skill script, on whatever `python3` started it, to stop or switch an
  old interpreter (tests/core/test_interpreter_guard.py);
- tools/run_all_checks.py and tools/check_ams_optional.py must parse on an old Python far enough to print their
  "Python 3.13 or newer is required" message (tests/tools/test_run_all_checks.py).

`ast.parse(feature_version=...)` rejects most newer grammar (match, except*, type aliases, generics, walrus before 3.8,
positional-only parameters before 3.8) but not the Python 3.12 f-string grammar (PEP 701) or a starred subscript
(3.11), so those two are checked here as well; `datetime.UTC` (3.11) is the one runtime name checked, since the runner
has avoided it before. A real old interpreter, when present, byte-compiles the files as the final word.
"""
from __future__ import annotations

import ast
import io
import shutil
import subprocess
import tokenize
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = {  # path -> oldest Python that must parse it
    "core/partition/runner.py": (3, 9),
    "core/interpreter_guard.py": (3, 9),
    "skills/hep-computing/scripts/find_python.py": (3, 9),
    "tools/run_all_checks.py": (3, 9),
    "tools/check_ams_optional.py": (3, 9),
}
PROBE_VERSION = (3, 7)


def _quote(token_text: str) -> str:
    body = token_text.lstrip("rRbBuUfF")
    return body[:3] if body[:3] in ('"""', "'''") else body[:1]


def _fstring_problems(source: str) -> list[str]:
    """f-strings that only Python 3.12+ parses (PEP 701): a nested string reusing an enclosing f-string's quote, a
    backslash or a comment inside a replacement field."""
    found, stack = [], []  # stack: quotes of the f-strings we are inside
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        where = f"line {tok.start[0]}"
        if tok.type == tokenize.FSTRING_START:
            q = _quote(tok.string)
            if any(q == outer or (len(outer) == 1 and q[0] == outer) for outer in stack):
                found.append(f"{where}: nested f-string reuses the enclosing quote")
            stack.append(q)
        elif tok.type == tokenize.FSTRING_END:
            stack.pop()
        elif stack and tok.type == tokenize.STRING:
            q = _quote(tok.string)
            if any(q == outer or (len(outer) == 1 and q[0] == outer) for outer in stack):
                found.append(f"{where}: string inside an f-string reuses its quote")
            if "\\" in tok.string:
                found.append(f"{where}: backslash inside an f-string replacement field")
        elif stack and tok.type == tokenize.COMMENT:
            found.append(f"{where}: comment inside an f-string")
    return found


def incompatibilities(source: str, version: tuple[int, int]) -> list[str]:
    """Reasons `source` would not parse (or would fail at import) on Python `version`; empty when it is compatible."""
    try:
        tree = ast.parse(source, feature_version=version)
    except SyntaxError as exc:
        return [f"line {exc.lineno}: {exc.msg} (Python {version[0]}.{version[1]} grammar)"]
    found = _fstring_problems(source) if version < (3, 12) else []
    for node in ast.walk(tree):
        if version < (3, 11) and isinstance(node, ast.Subscript) and (
                isinstance(node.slice, ast.Starred)
                or isinstance(node.slice, ast.Tuple) and any(isinstance(e, ast.Starred) for e in node.slice.elts)):
            found.append(f"line {node.lineno}: starred subscript (Python 3.11)")
        if version < (3, 11) and (
                isinstance(node, ast.ImportFrom) and node.module == "datetime"
                and any(a.name == "UTC" for a in node.names)
                or isinstance(node, ast.Attribute) and node.attr == "UTC"
                and isinstance(node.value, ast.Name) and node.value.id == "datetime"):
            found.append(f"line {node.lineno}: datetime.UTC (Python 3.11; use timezone.utc)")
    return found


def probe_source() -> str:
    tree = ast.parse((ROOT / "skills/hep-computing/scripts/find_python.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and [t.id for t in node.targets if isinstance(t, ast.Name)] == ["PROBE"]:
            return ast.literal_eval(node.value)
    raise AssertionError("find_python.py defines no PROBE string")


def old_interpreter() -> str | None:
    for name in ("python3.9", "/usr/bin/python3"):
        exe = shutil.which(name)
        if exe:
            try:
                out = subprocess.run([exe, "-c", "import sys; print(sys.version_info[1])"], capture_output=True,
                                     text=True, timeout=30).stdout.strip()
            except (OSError, subprocess.TimeoutExpired):
                continue
            if out.isdigit() and int(out) <= 9:
                return exe
    return None


class OldPythonCompatibilityTests(unittest.TestCase):
    def test_files_parse_on_their_oldest_python(self):
        for rel, version in FILES.items():
            with self.subTest(file=rel):
                self.assertEqual(incompatibilities((ROOT / rel).read_text(encoding="utf-8"), version), [])

    def test_probe_parses_on_every_python_3(self):
        self.assertEqual(incompatibilities(probe_source(), PROBE_VERSION), [])

    def test_the_check_catches_newer_constructs(self):
        """Each construct below parses on 3.13 and not on 3.9: the check must name it."""
        newer = {
            "match": "match x:\n    case 1:\n        pass\n",
            "except*": "try:\n    pass\nexcept* ValueError:\n    pass\n",
            "type alias": "type X = int\n",
            "generic function": "def f[T](x: T):\n    return x\n",
            "PEP 701 quote reuse": "x = f\"{'a' + \"b\"}\"\n",
            "PEP 701 nested f-string": "x = f\"{f\"{1}\"}\"\n",
            "PEP 701 backslash": "x = f\"{'\\n'.join(y)}\"\n",
            "starred subscript": "a[*b]\n",
            "datetime.UTC": "import datetime\nnow = datetime.datetime.now(datetime.UTC)\n",
            "from datetime import UTC": "from datetime import UTC\n",
        }
        for name, src in newer.items():
            with self.subTest(construct=name):
                ast.parse(src)  # valid on the runner's Python
                self.assertNotEqual(incompatibilities(src, (3, 9)), [], name)
        for ok in ("x = f\"{'a'}\"\n", "x = f'''{\"a\"}'''\n", "from datetime import timezone\nt = timezone.utc\n",
                   "a[b, c]\n"):
            with self.subTest(ok=ok):
                self.assertEqual(incompatibilities(ok, (3, 9)), [])

    @unittest.skipUnless(old_interpreter(), "no Python 3.9 or older on this machine")
    def test_a_real_old_python_compiles_them(self):
        exe = old_interpreter()
        code = "import sys; [compile(open(p, encoding='utf-8').read(), p, 'exec') for p in sys.argv[1:]]"
        p = subprocess.run([exe, "-c", code, *(str(ROOT / rel) for rel in FILES)], capture_output=True, text=True,
                           timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr[-800:])
        p = subprocess.run([exe, "-c", "import sys; compile(sys.stdin.read(), 'PROBE', 'exec')"], input=probe_source(),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr[-800:])


if __name__ == "__main__":
    unittest.main()
