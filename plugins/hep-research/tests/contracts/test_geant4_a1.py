"""Geant4 program stage A1 (contracts CV-A1, sci-fix): evidence tests of the study-record rules.

Each test goes through the command line of contracts/validate.py (--strict) with copies of the J14 study record
(examples/geant4-thin-silicon, offline replay through test_geant4_upgrade.j14_output), so that it reaches the code of
the parent commit as well: a test fails there by assertion when the parent accepts what CV-A1 refuses.
Expected outcomes are transcribed from the program spec, docs/dev/geant4-architecture/geant4-program.en.md (A1.1
benchmark table, A1.2 scope rules, A1.3 configuration rules), never from the code's output."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from tests.contracts.test_geant4_upgrade import j14_output, tearDownModule  # noqa: E402,F401

VALIDATE = PLUGIN / "contracts" / "validate.py"
RECORD = "artifacts/mpv.study-validated.computational-run.json"
# program spec A1.1, table "benchmark | Class": the class is also the value the record's grade must have
SPEC_CLASS = {"stopping-power": "reference", "range": "reference", "thin-layer-mpv": "reference",
              "thin-layer-width": "sanity", "multiple-scattering": "sanity", "em-shower-shape": "sanity",
              "shower-containment": "sanity", "longitudinal-profile": "setup-matched", "published-data": "interface"}
GRADES = ("reference", "setup-matched", "sanity", "interface", "gold")


def strict_exit(doc: dict) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "record.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        p = subprocess.run([sys.executable, "-B", str(VALIDATE), str(path), "--strict"], capture_output=True,
                           text=True, timeout=120)
    return p.returncode


def j14_record() -> dict:
    return json.loads((j14_output() / RECORD).read_text(encoding="utf-8"))


class BenchmarkGradeTable(unittest.TestCase):
    """geant4-grade-table (D2): a benchmark's grade comes from the contracts table, not from the record."""

    def test_every_benchmark_and_declared_grade(self):
        """Exhaustive over the benchmarks of the A1.1 table x 5 declared grades, plus an unknown benchmark: an extra
        benchmark result is added next to J14's passing thin-layer-mpv; the record stays valid only when the declared
        grade is the table's class. longitudinal-profile, whose class changes, is the domain of
        SetupMatchedClass."""
        base = j14_record()
        self.assertEqual(strict_exit(base), 0, "the J14 validated study record must pass --strict")
        extra = copy.deepcopy(next(b for b in base["extension"]["study"]["benchmarks"]
                                   if b["benchmark"] == "thin-layer-width"))
        table = [(n, c) for n, c in SPEC_CLASS.items() if n != "longitudinal-profile"]
        for name, cls in [*table, ("bremsstrahlung-yield", None)]:
            for grade in GRADES:
                doc = copy.deepcopy(base)
                doc["extension"]["study"]["benchmarks"].append(dict(extra, benchmark=name, grade=grade))
                with self.subTest(benchmark=name, grade=grade):
                    self.assertEqual(strict_exit(doc), 0 if grade == cls else 1)

    def test_a_self_declared_reference_grade_does_not_upgrade(self):
        """The defect itself: J14's sanity benchmark thin-layer-width relabelled 'reference', passing, with a caught
        control, as the only benchmark of a validated-in-scope record."""
        doc = j14_record()
        width = next(b for b in doc["extension"]["study"]["benchmarks"] if b["benchmark"] == "thin-layer-width")
        forged = dict(width, grade="reference", verdict="pass", validation_evidence=True,
                      negative_control={"status": "caught"})
        doc["extension"]["study"]["benchmarks"] = [forged]
        self.assertEqual(strict_exit(doc), 1)


class SetupMatchedClass(unittest.TestCase):
    """geant4-setup-matched-class (D2): longitudinal-profile compares with one published measurement of one
    configuration, so its class is setup-matched (A1.1), not reference."""

    def test_longitudinal_profile_takes_only_the_setup_matched_grade(self):
        base = j14_record()
        extra = copy.deepcopy(next(b for b in base["extension"]["study"]["benchmarks"]
                                   if b["benchmark"] == "thin-layer-width"))
        for grade in GRADES:
            doc = copy.deepcopy(base)
            doc["extension"]["study"]["benchmarks"].append(dict(extra, benchmark="longitudinal-profile", grade=grade))
            with self.subTest(grade=grade):
                self.assertEqual(strict_exit(doc), 0 if grade == SPEC_CLASS["longitudinal-profile"] else 1)


# program spec A1.1, column "Supported kind" (A1.12 adds shower-maximum to the study spec's kind enum)
SPEC_KINDS = {"stopping-power": {"stopping-power"}, "range": {"range"}, "thin-layer-mpv": {"most-probable-value"},
              "longitudinal-profile": {"shower-maximum"}}
KIND_ENUM = ("activation", "angle", "containment", "energy-deposit", "energy-loss", "energy-resolution", "leakage",
             "most-probable-value", "neutron-capture", "neutron-dose", "neutron-flux", "other", "range",
             "shower-shape", "shower-maximum", "stopping-power", "thin-layer-width")


class ScopeKind(unittest.TestCase):
    """geant4-scope-kind (D1): the declared observable kind must be one the counted benchmark supports."""

    def test_every_declared_kind_against_the_mpv_benchmark(self):
        """Exhaustive over the observable-kind enum: J14's MPV record, validated by thin-layer-mpv, stays valid only
        with the kind that benchmark supports; a declaration without a kind is outside the scope."""
        base = j14_record()
        for kind in (*KIND_ENUM, None):
            doc = copy.deepcopy(base)
            scope = doc["extension"]["study"]["declared_scope"]
            scope.pop("observable_kind", None)
            if kind is not None:
                scope["observable_kind"] = kind
            with self.subTest(kind=kind):
                self.assertEqual(strict_exit(doc), 0 if kind in SPEC_KINDS["thin-layer-mpv"] else 1)

    def test_every_upgrading_benchmark_and_kind(self):
        """Exhaustive over the upgrading benchmarks x the kind enum: J14's thin-layer-mpv result renamed to each
        benchmark (graded by the table) is the only one counted."""
        base = j14_record()
        mpv = next(b for b in base["extension"]["study"]["benchmarks"] if b["benchmark"] == "thin-layer-mpv")
        for name, kinds in SPEC_KINDS.items():
            if name == "longitudinal-profile":
                continue  # its scope dimensions differ (target hash): ScopeDimensions
            for kind in KIND_ENUM:
                doc = copy.deepcopy(base)
                doc["extension"]["study"]["benchmarks"] = [dict(mpv, benchmark=name, grade=SPEC_CLASS[name])]
                doc["extension"]["study"]["declared_scope"]["observable_kind"] = kind
                with self.subTest(benchmark=name, kind=kind):
                    self.assertEqual(strict_exit(doc), 0 if kind in kinds else 1)


class ScopeDimensions(unittest.TestCase):
    """geant4-scope-missing-dimension (D1): every scope dimension of the benchmark (A1.1 fourth column) must be
    declared; categorical by set inclusion, interval by interval inclusion, a scalar read as [v, v] (A1.2)."""
    # J14's thin-layer-mpv scope: mu-, Si_study, 10 GeV, 0.3 mm; per dimension: declared value -> inside?
    CASES = {"particle": [("mu-", True), (["mu-"], True), ("mu+", False), (["mu-", "mu+"], False)],
             "material": [("Si_study", True), ("G4_Si", False), (["Si_study", "G4_Si"], False)],
             "energy_MeV": [([10000.0, 10000.0], True), (10000.0, True), ([9000.0, 10000.0], False),
                            (12000.0, False)],
             "thickness_mm": [([0.3, 0.3], True), (0.3, True), ([0.3, 0.5], False), (0.1, False)]}

    def test_each_dimension_missing_inside_or_outside(self):
        base = j14_record()
        for dim, cases in self.CASES.items():
            for value, inside in [*cases, (None, False)]:
                doc = copy.deepcopy(base)
                scope = doc["extension"]["study"]["declared_scope"]
                if value is None:
                    scope.pop(dim)
                else:
                    scope[dim] = value
                with self.subTest(dimension=dim, declared=value):
                    self.assertEqual(strict_exit(doc), 0 if inside else 1)

    def test_a_scope_that_declares_only_the_kind_is_outside(self):
        """The defect itself: dimensions missing from the declaration were unconstrained."""
        doc = j14_record()
        doc["extension"]["study"]["declared_scope"] = {"observable_kind": "most-probable-value"}
        self.assertEqual(strict_exit(doc), 1)


if __name__ == "__main__":
    unittest.main()
