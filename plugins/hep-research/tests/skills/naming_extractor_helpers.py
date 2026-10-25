"""Shared fixtures of the extract_names.py tests: load one skill's extractor, run its CLI on a temporary project and
read the inventory back, validated against contracts/schemas/naming_inventory.json."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts.schema import validate  # noqa: E402


def load(skill: str):
    spec = importlib.util.spec_from_file_location(f"extract_names_{skill.replace('-', '_')}",
                                                  ROOT / f"skills/{skill}/scripts/extract_names.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ProjectCase(unittest.TestCase):
    """A temporary project folder (self.root) with write(rel, text) and extract(surface) -> (exit, inventory)."""
    SKILL = ""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "naming").mkdir()
        self.mod = load(self.SKILL)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel: str, text) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text if isinstance(text, str) else json.dumps(text, indent=1), encoding="utf-8")
        return p

    def extract(self, surface: str, *extra: str):
        out = self.root / "naming" / f"{surface}.json"
        with redirect_stdout(io.StringIO()) as buf:
            code = self.mod.main(["--surface", surface, "--out", str(out), "--root", str(self.root), *extra])
        status = json.loads(buf.getvalue())
        if code == 2:
            return code, status
        inv = json.loads(out.read_text())
        rep = validate(inv, "naming_inventory.json")
        self.assertTrue(rep.ok, [f.message for f in rep.errors][:3])
        return code, inv

    def names(self, inv, kind=None) -> list[str]:
        return [e["name"] for e in inv["entities"] if kind is None or e["entity_kind"] == kind]

    def entity(self, inv, name, kind=None) -> dict:
        return next(e for e in inv["entities"] if e["name"] == name and (kind is None or e["entity_kind"] == kind))
