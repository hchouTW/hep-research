"""Geant4 program A1.17 (design-f4-label-passthrough, robust-fix): evaluate_design.py f4 --label-spec passes the run
records, reference records and variation table on to check_geant4_study.py label --upgrade, and reports its outcome
faithfully: a refused upgrade is incomplete with label's reasons, a validated-in-scope study without
results.<figure of merit> is incomplete (results-missing), label's exit 1, 2, 3 map to failed, rejected, incomplete.

The design project is the SYNTHETIC spectrometer of tests/contracts/design_fixtures.py (as F4Path in
test_design_m2.py); the study is J14's MPV study (examples/geant4-thin-silicon, offline replay), which reports no
results (B2 adds them)."""
import json
import shutil
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "tests" / "contracts"))
from design_fixtures import NS  # noqa: E402
from tests.contracts.test_geant4_upgrade import j14_output, tearDownModule  # noqa: E402,F401
from tests.skills.hep_detector.test_design_m2 import Base, ev  # noqa: E402

J14 = PLUGIN / "examples" / "geant4-thin-silicon"
STUDY = "studies/j14-mpv.computational-run.json"
RUNS = ["nominal", "control", "cut-0.1", "cut-0.03", "em-option0", "em-option3", "pai", "ftfp-bert-emz"]


class F4LabelPassthrough(Base):
    def setUp(self):
        super().setUp()
        self.j14 = self.root / "j14"
        self.j14.mkdir()
        for name in ("study-mpv.json", "literature-input.json", "specs", "refdata", "recorded"):
            src = J14 / name
            (shutil.copytree if src.is_dir() else shutil.copyfile)(src, self.j14 / name)
        shutil.copytree(j14_output(), self.j14 / "output")
        self.ok("geometry", "--candidate", f"{NS}:cand-B", "--figure-of-merit", "momentum-resolution-core",
                "--denominator", "rigidity_GV=1000", "--denominator", "species=proton", "--id", "g1")

    def f4(self, *extra):
        o = self.j14 / "output"
        return ev(self.b, "f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study", STUDY,
                  "--id", "SIM-G4", "--label-spec", self.j14 / "study-mpv.json",
                  "--label-benchmarks", o / "benchmarks-mpv.json", "--label-convergence", o / "convergence-mpv.json",
                  "--label-project-root", self.j14, *extra)

    def runs(self):
        return [a for r in RUNS for a in ("--label-run-record",
                                          self.j14 / "output" / "artifacts" / "runs" / f"mpv-{r}.computational-run.json")]

    def test_a_run_records_reach_label(self):
        code, out = self.f4(*self.runs(), "--label-variations", self.j14 / "output" / "variations-mpv.json")
        record = json.loads((self.b.art / STUDY).read_text(encoding="utf-8"))
        self.assertEqual(record["status"], ["validated-in-scope"], out)
        self.assertEqual(len(record["extension"]["evidence_records"]), len(RUNS))

    def test_b_a_refused_upgrade_is_incomplete_with_the_reasons(self):
        """Without run records label refuses the upgrade (and still writes an unvalidated record, exit 0): f4 is
        incomplete with label's reasons, not a usage error about missing results."""
        code, out = self.f4()
        self.assertEqual((code, out["status"]), (3, "incomplete"), out)
        self.assertEqual(out["reason"], "upgrade-refused")
        self.assertTrue(any("no run record" in r for r in out["refused"]), out)
        record = json.loads((self.b.art / STUDY).read_text(encoding="utf-8"))
        self.assertEqual(record["status"], ["unvalidated"])

    def test_c_an_upgrade_without_results_is_incomplete(self):
        code, out = self.f4(*self.runs(), "--label-variations", self.j14 / "output" / "variations-mpv.json")
        self.assertEqual((code, out["status"], out["reason"]), (3, "incomplete", "results-missing"), out)
        self.assertFalse((self.b.art / "evaluations" / "SIM-G4.json").exists())

    def test_label_exit_codes_map(self):
        """Unusable label input (a missing benchmarks file): label exits 2, f4 is rejected (exit 2)."""
        code, out = ev(self.b, "f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study", STUDY,
                       "--id", "SIM-G4", "--label-spec", self.j14 / "study-mpv.json",
                       "--label-benchmarks", self.j14 / "missing.json",
                       "--label-convergence", self.j14 / "output" / "convergence-mpv.json",
                       "--label-project-root", self.j14)
        self.assertEqual((code, out["status"]), (2, "rejected"), out)


if __name__ == "__main__":
    unittest.main()
