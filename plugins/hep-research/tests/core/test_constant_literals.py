"""Th9: no hard-coded common masses (or hbar c) in the code of skills/, core/ and profiles/. Values come from
core/constants. The scan reads numeric literals in the code (the AST), so docstrings, comments and usage examples are
not scanned, and neither are test folders (tests state their own SYNTHETIC inputs). A literal that matches a reference value to 1e-4 and has at least four significant digits fails
unless tests/core/constant_literal_allowlist.json lists it with a reason (a pinned edition that a published
benchmark depends on). Standard library only."""
import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST = Path(__file__).with_name("constant_literal_allowlist.json")
SCANNED = ("skills", "core", "profiles")

# Reference values (rounded; only used for matching). GeV, MeV, kg and g forms of the common masses, and hbar c.
_GEV = {"electron": 0.000510998950, "muon": 0.1056583755, "charged pion": 0.13957039, "neutral pion": 0.1349768,
        "charged kaon": 0.493677, "proton": 0.93827208943, "neutron": 0.93956542194, "deuteron": 1.875612945,
        "triton": 2.808921136, "helion": 2.808391611, "alpha particle": 3.727379412, "atomic mass unit": 0.93149410372}
_KG = {"electron": 9.1093837139e-31, "proton": 1.67262192595e-27, "neutron": 1.67492750056e-27,
       "atomic mass unit": 1.66053906892e-27}
REFERENCE = {}
for _name, _v in _GEV.items():
    REFERENCE[f"{_name} mass (GeV)"] = _v
    REFERENCE[f"{_name} mass (MeV)"] = _v * 1e3
for _name, _v in _KG.items():
    REFERENCE[f"{_name} mass (kg)"] = _v
    REFERENCE[f"{_name} mass (g)"] = _v * 1e3
REFERENCE.update({"hbar c (MeV fm)": 197.3269804, "hbar c (GeV fm)": 0.1973269804,
                  "(hbar c)^2 (GeV^2 mb)": 0.3893793721})


def significant_digits(text):
    mantissa = text.lower().replace("_", "").lstrip("+-").split("e")[0]
    digits = mantissa.replace(".", "").lstrip("0")
    return len(digits if "." in mantissa else digits.rstrip("0"))


def scan(path):
    """(line, literal text, matched reference) for each numeric literal in the code of one file."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float) and node.value:
            seg = ast.get_source_segment(source, node) or lines[node.lineno - 1]
            if significant_digits(seg) < 4:
                continue
            for ref_name, ref in REFERENCE.items():
                if abs(abs(float(node.value)) / ref - 1.0) < 1e-4:
                    hits.append((node.lineno, seg, ref_name))
    return hits


class ConstantLiteralScan(unittest.TestCase):
    def test_no_unlisted_mass_literals(self):
        allow = json.loads(ALLOWLIST.read_text(encoding="utf-8"))["entries"]
        allowed = {(e["file"], e["literal"]) for e in allow}
        found, used = [], set()
        for top in SCANNED:
            for path in sorted((ROOT / top).rglob("*.py")):
                rel = path.relative_to(ROOT).as_posix()
                if "/tests/" in f"/{rel}":
                    continue
                for line, seg, ref in scan(path):
                    if (rel, seg) in allowed:
                        used.add((rel, seg))
                    else:
                        found.append(f"{rel}:{line}: {seg} looks like the {ref}; take it from core/constants")
        self.assertEqual(found, [], "\n".join(found))
        self.assertEqual(sorted(allowed - used), [], "allowlist entries that no longer match a literal")

    def test_allowlist_entries_give_a_reason(self):
        for e in json.loads(ALLOWLIST.read_text(encoding="utf-8"))["entries"]:
            with self.subTest(entry=e):
                self.assertTrue(e.get("reason"))
                if e["file"].startswith(("core/", "skills/")):  # only while a sci-fix: commit that switches it is pending
                    self.assertTrue(e.get("sci_fix_pending"), "core and skills take values from core/constants")

    def test_scan_catches_the_gram_form_and_ignores_docstrings(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.py"
            p.write_text('"""Run with --mass 0.93827208943."""\nM_H_G = 1.67262192369e-24\nN = 4\n', encoding="utf-8")
            hits = scan(p)
        self.assertEqual([(h[0], h[2]) for h in hits], [(2, "proton mass (g)")])


if __name__ == "__main__":
    unittest.main()
