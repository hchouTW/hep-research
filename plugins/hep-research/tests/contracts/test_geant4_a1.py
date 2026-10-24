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


DEPS = PLUGIN / "contracts" / "dependencies.py"
BENCH = PLUGIN / "skills" / "hep-detector" / "scripts" / "geant4_benchmarks.py"


def spec_v1_oracle(sim: dict, targets: set) -> tuple[str, str]:
    """Independent implementation of the A1.3 text (program spec, "spec-v1 normal form" and "isolated"), written
    from the spec, not from contracts.validate: (configuration, target hash)."""
    import hashlib
    geo, mats = sim["geometry"], {m["name"]: m for m in sim.get("materials", [])}
    placed = []
    for layer in geo["layers"]:
        placed += list(layer["slabs"]) * layer.get("repeat", 1)
    rows = []
    for s in placed:
        if s["name"] in targets:
            m = {k: v for k, v in mats.get(s["material"], {}).items() if k not in ("name", "source")}
            num = (lambda x: float(x).hex() if isinstance(x, (int, float)) and not isinstance(x, bool) else x)
            rows.append({"name": s["name"], "material": s["material"], "thickness_mm": num(s["thickness_mm"]),
                         "lateral_mm": num(geo["lateral_mm"]), "shift_mm": num(s.get("shift_mm", 0.0)),
                         "composition": {k: num(v) for k, v in m.items()}})
    world = geo["world"]["material"]
    vacuum = world == "G4_Galactic" or mats.get(world, {}).get("density_g_cm3", 1.0) < 1e-20
    isolated = vacuum and all(s["name"] in targets for s in placed)
    return ("isolated" if isolated else "embedded",
            hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest())


def run_cli(script: Path, *args) -> tuple[int, dict]:
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True,
                       timeout=600)
    try:
        return p.returncode, json.loads(p.stdout)
    except ValueError:
        return p.returncode, {"raw": p.stdout[-500:], "stderr": p.stderr[-500:]}


class Isolation(unittest.TestCase):
    """geant4-isolation (A1.3): a counted reference benchmark needs an isolated target whose configuration is derived
    from a named run record; a setup-matched one also the measured target hash; dependencies.py re-derives."""

    def counted(self, doc):
        return next(b for b in doc["extension"]["study"]["benchmarks"] if b["benchmark"] == "thin-layer-mpv")

    def test_missing_or_embedded_configuration_is_refused(self):
        cases = {"no configuration": lambda b: [b.pop(k, None) for k in ("configuration", "configuration_basis",
                                                                          "target_geometry_sha256", "hash_scheme")],
                 "embedded": lambda b: b.update(configuration="embedded"),
                 "no hash": lambda b: b.pop("target_geometry_sha256"),
                 "unknown scheme": lambda b: b.update(hash_scheme="spec-v0")}
        for name, tamper in cases.items():
            doc = j14_record()
            tamper(self.counted(doc))
            with self.subTest(name):
                self.assertEqual(strict_exit(doc), 1)

    def test_setup_matched_needs_the_measured_target_hash(self):
        doc = j14_record()
        b = self.counted(doc)
        b.update(benchmark="longitudinal-profile", grade="setup-matched")
        scope = doc["extension"]["study"]["declared_scope"]
        scope.update(observable_kind="shower-maximum", target_geometry_sha256=b["target_geometry_sha256"],
                     hash_scheme=b["hash_scheme"])
        b["scope"].update(target_geometry_sha256=b["target_geometry_sha256"], hash_scheme=b["hash_scheme"])
        for measured, ok in ((b["target_geometry_sha256"], True), ("0" * 64, False), (None, False)):
            d = copy.deepcopy(doc)
            cb = self.counted_by_name(d, "longitudinal-profile")
            if measured is not None:
                cb["measured_configuration"] = {"target_geometry_sha256": measured, "hash_scheme": b["hash_scheme"]}
            with self.subTest(measured=measured):
                self.assertEqual(strict_exit(d), 0 if ok else 1)

    @staticmethod
    def counted_by_name(doc, name):
        return next(b for b in doc["extension"]["study"]["benchmarks"] if b["benchmark"] == name)

    def test_dependencies_re_derive_the_configuration_from_the_run_record(self):
        """The record says isolated, but the evidence run record it names ran in an air world: re-derived embedded."""
        import hashlib
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "j14"
            shutil.copytree(j14_output(), root / "output")
            shutil.copytree(PLUGIN / "examples" / "geant4-thin-silicon" / "recorded", root / "recorded")
            rec_path = root / "output" / RECORD
            self.assertEqual(run_cli(DEPS, rec_path, "--root", root)[0], 0, "J14's record must pass first")
            doc = json.loads(rec_path.read_text(encoding="utf-8"))
            basis = self.counted(doc)["configuration_basis"]
            ev = next(r for r in doc["extension"]["evidence_records"] if r["artifact_id"] == basis["artifact_id"])
            run_path = root / "output" / "artifacts" / ev["ref"].split("artifacts/", 1)[1]
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["extension"]["simulation"]["geometry"]["world"]["material"] = "G4_AIR"
            run_path.write_text(json.dumps(run, indent=1), encoding="utf-8")
            sha = hashlib.sha256(run_path.read_bytes()).hexdigest()
            ev["sha256"], basis["sha256"] = sha, sha
            rec_path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
            self.assertEqual(run_cli(DEPS, rec_path, "--root", root)[0], 1)

    def test_configuration_against_an_independent_implementation(self):
        """Exhaustive over world (G4_Galactic, a declared vacuum, a declared gas, G4_AIR) x placements (the target
        alone, an absorber outside the target, the absorber inside the target, two repeats): configuration and
        target hash from geant4_benchmarks.py against spec_v1_oracle."""
        si = {"name": "Si_study", "z": 14, "a_g_mole": 28.0855, "density_g_cm3": 2.329}
        worlds = {"G4_Galactic": [], "Vac": [{"name": "Vac", "z": 1, "a_g_mole": 1.008, "density_g_cm3": 1e-25}],
                  "Gas": [{"name": "Gas", "z": 1, "a_g_mole": 1.008, "density_g_cm3": 1e-5}], "G4_AIR": []}
        layouts = {"target alone": ([[{"name": "Si", "material": "Si_study", "thickness_mm": 0.3}]], 1, ["Si"]),
                   "absorber outside": ([[{"name": "Si", "material": "Si_study", "thickness_mm": 0.3},
                                          {"name": "Ab", "material": "G4_W", "thickness_mm": 3.5}]], 1, ["Si"]),
                   "absorber inside": ([[{"name": "Si", "material": "Si_study", "thickness_mm": 0.3},
                                         {"name": "Ab", "material": "G4_W", "thickness_mm": 3.5}]], 1, ["Si", "Ab"]),
                   "two repeats": ([[{"name": "Si", "material": "Si_study", "thickness_mm": 0.3},
                                     {"name": "Ab", "material": "G4_W", "thickness_mm": 3.5}]], 2, ["Si", "Ab"])}
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            for world, extra in worlds.items():
                for lname, (slabs, rep, targets) in layouts.items():
                    sim = {"geometry": {"lateral_mm": 10.0, "world": {"material": world, "scale": 1.2},
                                        "layers": [{"repeat": rep, "slabs": s} for s in slabs]},
                           "materials": [si, *extra]}
                    (d / "run.json").write_text(json.dumps({"artifact_type": "computational-run", "artifact_id": "r",
                                                            "extension": {"simulation": sim}}))
                    (d / "events.csv").write_text("# SIMULATION\nevent,primary_eloss_MeV,edep_Si_MeV,primary_fate,"
                                                  "primary_end_process\n0,1.0,1.0,1,Transportation\n"
                                                  "1,1.1,1.0,1,Transportation\n")
                    (d / "study.json").write_text(json.dumps({"materials": [dict(si, z_over_a=0.4985)]}))
                    (d / "cfg.json").write_text(json.dumps({"schema": "geant4-benchmarks/1", "study_spec": "study.json",
                                                            "benchmarks": [{"benchmark": "published-data",
                                                                            "csv": "events.csv", "column": "edep_Si_MeV",
                                                                            "particle": "mu-", "energy_MeV": 1000.0,
                                                                            "run_record": "run.json",
                                                                            "target_slabs": targets}]}))
                    code, out = run_cli(BENCH, "run", "--config", d / "cfg.json")
                    b = out["benchmarks"][0]
                    with self.subTest(world=world, layout=lname):
                        self.assertEqual((b["configuration"], b["target_geometry_sha256"]),
                                         spec_v1_oracle(sim, set(targets)))


CHECK = PLUGIN / "skills" / "hep-detector" / "scripts" / "check_geant4_study.py"
J14 = PLUGIN / "examples" / "geant4-thin-silicon"


class ScanCompleteness(unittest.TestCase):
    """geant4-gate-scan-completeness (D11, A1.16): every declared scan value needs a summary, else the gate is
    incomplete (exit 3); 'the two finest' are the two finest declared values."""

    def gate(self, cuts: list[float]) -> tuple[int, dict]:
        """J14's MPV study (declared cuts 0.1, 0.03, 0.01 mm; 0.01 mm is the nominal run) with the given summaries."""
        args = []
        for c in cuts:
            args += ["--summary", "nominal=recorded/summaries/mpv-nominal.json" if c == 0.01 else
                     f"scan=recorded/summaries/mpv-cut-{c}.json"]
        p = subprocess.run([sys.executable, "-B", str(CHECK), "run", "--spec", "study-mpv.json", *args],
                           capture_output=True, text=True, timeout=600, cwd=J14)
        return p.returncode, json.loads(p.stdout)

    def test_every_subset_of_the_declared_values(self):
        """Exhaustive over the non-empty subsets of the three declared cuts: only the full set gives J14's pass."""
        import itertools
        declared = [0.1, 0.03, 0.01]
        for n in (1, 2, 3):
            for cuts in itertools.combinations(declared, n):
                code, out = self.gate(list(cuts))
                with self.subTest(cuts=cuts):
                    self.assertEqual(code, 0 if n == 3 else 3, out.get("convergence"))

    def test_the_two_finest_are_declared_values(self):
        code, out = self.gate([0.1, 0.03, 0.01])
        self.assertEqual(out["convergence"]["parameters"][0]["two_finest"], [0.01, 0.03])


if __name__ == "__main__":
    unittest.main()
