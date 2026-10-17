"""detector_atlas.py (D13): validate, render, query and audit the sourced detector atlas.

Oracles: the shipped atlas validates; --release fails on stale-date notes; a claim without a complete atlas block is
refused; every rendered number maps back to its claim; a query pages at most 20 rows and 16 KiB, labels a user atlas
user-supplied and puts it before the plugin atlas, answers unknown when nothing matches (with the profile link for an
experiment that has its own profile); the audit lists numbers without a claim id and, in strict mode, fails on them
(the comparison tables have none). The tool names no experiment (check_layering). Synthetic inputs are SYNTHETIC."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "detector_atlas.py"
N_CLAIMS = len(json.loads((PLUGIN / "profiles" / "reference" / "detector-atlas" / "evidence" / "claims.json").read_text(encoding="utf-8")))
ATLAS = PLUGIN / "profiles" / "reference" / "detector-atlas"
TABLES = PLUGIN / "skills" / "hep-detector" / "references" / "detector-comparison-tables.md"


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout), p.stderr


def user_atlas(tmp: Path, mutate=None) -> Path:
    d = tmp / "my-atlas"
    shutil.copytree(ATLAS, d)
    claims = json.loads((d / "evidence" / "claims.json").read_text(encoding="utf-8"))
    claims = [dict(c, atlas=dict(c["atlas"], value="SYNTHETIC " + c["atlas"]["value"])) for c in claims[:3]]
    if mutate:
        mutate(claims)
    (d / "evidence" / "claims.json").write_text(json.dumps(claims), encoding="utf-8")
    return d


class Validate(unittest.TestCase):
    def test_shipped_atlas_validates(self):
        code, out, err = run("validate", "--today", "2026-10-17")
        self.assertEqual(code, 0, err)
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["claims"], N_CLAIMS)

    def test_release_fails_on_stale_notes(self):
        code, out, _ = run("validate", "--release", "--today", "2030-01-01")
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "failed")
        self.assertTrue(any(n["code"].startswith("stale.") for n in out["release_blockers"]))

    def test_incomplete_atlas_block_refused(self):
        with tempfile.TemporaryDirectory() as d:
            def drop_kind(claims):
                del claims[0]["atlas"]["kind"]
                claims[1]["atlas"]["kind"] = "measured-somewhere"
            ua = user_atlas(Path(d), drop_kind)
            code, out, _ = run("validate", "--atlas", ua, "--today", "2026-10-17")
        self.assertEqual(code, 1)
        text = json.dumps(out["atlas_errors"])
        self.assertIn("kind", text)
        self.assertIn("measured-somewhere", text)


class Render(unittest.TestCase):
    def test_every_number_maps_to_its_claim(self):
        code, out, _ = run("render")
        self.assertEqual(code, 0)
        claims = {c["id"]: c for c in json.loads((ATLAS / "evidence" / "claims.json").read_text(encoding="utf-8"))}
        rows = [line for line in out["markdown"].splitlines() if line.startswith("| ") and "detector-atlas:C" in line]
        self.assertEqual(len(rows), len(claims))
        for line in rows:
            cid = re.search(r"detector-atlas:C\d+", line).group(0)
            self.assertIn(claims[cid]["atlas"]["value"].replace("|", "/"), line)
        numeric = [line for line in out["markdown"].splitlines() if line.startswith("| ") and re.search(r"\d", line)
                   and "---" not in line and "Quantity" not in line]
        self.assertTrue(all("detector-atlas:C" in line for line in numeric))

    def test_one_experiment(self):
        code, out, _ = run("render", "--experiment", "CMS")
        self.assertEqual(code, 0)
        self.assertEqual(out["rows"], 9)


class Query(unittest.TestCase):
    def test_filter_and_fields(self):
        code, out, _ = run("query", "--experiment", "cms", "--subsystem", "magnet")
        self.assertEqual(code, 0)
        self.assertEqual(len(out["rows"]), 1)
        row = out["rows"][0]
        for key in ("claim_id", "value", "unit", "kind", "valid_for", "source", "read_level", "origin", "status_label"):
            self.assertIn(key, row)
        self.assertEqual(row["origin"], "plugin atlas")

    def test_paging(self):
        code, out, _ = run("query")
        self.assertEqual(code, 0)
        self.assertEqual((len(out["rows"]), out["total"], out["next_page"]), (20, N_CLAIMS, 1))
        self.assertLessEqual(len(json.dumps(out).encode()), 16384)
        last_page = (N_CLAIMS - 1) // 20
        code, last, _ = run("query", "--page", str(last_page))
        self.assertEqual((len(last["rows"]), last["next_page"]), (N_CLAIMS - 20 * last_page, None))

    def test_unknown_and_profile_link(self):
        code, out, _ = run("query", "--experiment", "no such experiment")
        self.assertEqual((code, out["answer"]), (0, "unknown"))
        code, out, _ = run("query", "--experiment", "AMS-02")
        self.assertEqual(out["answer"], "unknown")
        self.assertEqual(out["see_profile"], "experiment:ams-02")

    def test_user_atlas_first_and_labelled(self):
        with tempfile.TemporaryDirectory() as d:
            ua = user_atlas(Path(d))
            code, out, _ = run("query", "--user-atlas", ua, "--experiment", "ATLAS", "--subsystem", "magnet")
        self.assertEqual(code, 0)
        self.assertEqual([r["origin"] for r in out["rows"]], ["user atlas", "plugin atlas"])
        self.assertEqual(out["rows"][0]["status_label"], "user-supplied")
        self.assertTrue(out["rows"][0]["value"].startswith("SYNTHETIC"))


class Audit(unittest.TestCase):
    def test_comparison_tables_have_no_unsourced_number(self):
        code, out, _ = run("audit", TABLES, "--strict")
        self.assertEqual(code, 0, out)
        self.assertEqual(out["unsourced"], [])

    def test_unsourced_numbers_listed_and_strict_fails(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "notes.md"
            f.write_text("SYNTHETIC: the field is 3.8 T.\nThe solenoid gives 2 T (detector-atlas:C001).\n", encoding="utf-8")
            code, out, _ = run("audit", f)
            self.assertEqual(code, 0)
            self.assertEqual([u["text"] for u in out["unsourced"]], ["3.8 T"])
            code, out, _ = run("audit", f, "--strict")
            self.assertEqual(code, 1)


class Contract(unittest.TestCase):
    def test_bad_input_and_status(self):
        code, out, _ = run("query", "--atlas", "/nonexistent/atlas")
        self.assertEqual((code, out["status"]), (2, "rejected"))
        code, out, _ = run("validate", "--today", "2026-10-17")
        self.assertEqual(out["status_label"], "unvalidated")
        self.assertIn("status", out["defaults_used"])


if __name__ == "__main__":
    unittest.main()
