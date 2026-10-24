"""Detector system design M2 (fidelity and sensitivity): parameter-level invalidation (TRC-04..TRC-10, T-36 and T-37
from M2), incremental reruns of run_workflow.py (INC-01..INC-04, T-51..T-53; the acceptance "changing the B field
reruns only the steps that read field parameters"), the F2 toy and in-field acceptance, the F3 response assembly and
response artifact (CHN-01), the expected-precision write-back and the ranking it enters (CHN-04..CHN-06, the acceptance
"expected-precision enters comparison"), and the F4 path (ART-30..ART-36, FID-03, FID-05; T-33, T-46, T-47). Every
project is the SYNTHETIC spectrometer of tests/contracts/design_fixtures.py."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "tests" / "contracts"))
from design_fixtures import (NS, copy_fixture, derive, edit, entry, fake_contract, fake_eval, gauss, matrix,  # noqa: E402
                             param, sha256, write_contracts)

SCRIPTS = PLUGIN / "skills" / "hep-detector" / "scripts"
EVAL = SCRIPTS / "evaluate_design.py"
EST = SCRIPTS / "design_estimates.py"
WORKFLOW = PLUGIN / "skills" / "hep-computing" / "scripts" / "run_workflow.py"
KNOWN = {"release": "9.9.9", "digest": "a" * 64}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def call(mod, argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = mod.main(argv)
    return code, json.loads(buf.getvalue())


EV = load_module(EVAL, "evaluate_design_m2")


def ev(b, *args):
    return call(EV, [*map(str, args), "--artifacts", str(b.art)])


def add_m2_parameters(b, cand="cand-A"):
    """Aperture, tolerance, alignment and tail parameters on a candidate (the M0 fixture has none of them)."""
    def add(doc):
        p = doc["extension"]["subsystems"]["DES-TRK-001"]["parameters"]
        n = len(p["layer_positions_m"]["value"])
        p["layer_aperture_radius_m"] = param([0.5] * n, "m")
        p["layer_lateral_offset_m"] = param([0.0] * n, "m")
        p["aperture_radius_tolerance_m"] = param(0.005, "m")
        p["alignment_curvature_per_GV"] = param(1e-4, "1/GV")
        p["resolution_tail_fraction"] = param(0.05, "1")
        p["resolution_tail_width_factor"] = param(3.0, "1")
    edit(b, f"candidates/{cand}.json", add)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.b = copy_fixture(self.root / "p")

    def tearDown(self):
        self.tmp.cleanup()

    def ok(self, *args):
        code, out = ev(self.b, *args)
        self.assertEqual(code, 0, out)
        return out


class ParameterLevel(Base):
    """TRC-04..TRC-10 from M2: an evaluation is stale only when a parameter it read changed."""

    def test_t37_field_change_stales_only_field_readers(self):
        add_m2_parameters(self.b)
        c = f"{NS}:cand-A"
        self.ok("run", "--candidate", c, "--requirement", "REQ-TRK-001", "--id", "CALC-R", "--status", "synthetic")
        self.ok("run", "--candidate", c, "--requirement", "REQ-CC-001", "--id", "CALC-C", "--upstream",
                "evaluations/CALC-R.json", "--status", "synthetic")
        self.ok("budget", "--candidate", c, "--quantity", "mass", "--id", "CALC-M", "--status", "synthetic")
        self.ok("run", "--candidate", c, "--figure-of-merit", "geometric-acceptance", "--denominator", "rigidity_GV=100",
                "--denominator", "species=proton", "--denominator", "charge_sign=positive", "--id", "CALC-A",
                "--status", "synthetic")
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"]["subsystems"]["DES-MAG-001"]["parameters"]
             ["field_T"].update(value=0.6))
        stale = set(derive(self.b)["stale_evaluations"])
        self.assertIn(f"{NS}:CALC-R", stale)
        self.assertIn(f"{NS}:CALC-C", stale)  # staleness propagates down the chain (TRC-09)
        self.assertNotIn(f"{NS}:CALC-M", stale)
        self.assertNotIn(f"{NS}:CALC-A", stale)
        self.assertIn(f"{NS}:CALC-TRK-A", stale)  # the M0 fixture evaluation is file-bound (TRC-03)
        out = self.ok("run", "--candidate", c, "--requirement", "REQ-TRK-001", "--id", "CALC-R", "--replace",
                      "--status", "synthetic")
        self.assertIn("evaluations/CALC-R.json", out["replaced"])
        code, out = ev(self.b, "budget", "--candidate", c, "--quantity", "mass", "--id", "CALC-M", "--replace")
        self.assertEqual(code, 2)  # a current evaluation is never replaced
        self.assertIn("not stale", out["error"])

    def test_t36_variant_override_shields_the_base_change(self):
        """ART-21, TRC-07: a variant that overrides the changed base parameter keeps its evaluation; one that reads
        the changed base parameter goes stale."""
        self.b.candidate("cand-A-v", None, None, derived_from="cand-A",
                         overrides={"DES-TRK-001": {"parameters": {"point_resolution_um": param(8.0, "um")}}})
        self.ok("run", "--candidate", f"{NS}:cand-A-v", "--requirement", "REQ-TRK-001", "--id", "CALC-V",
                "--status", "synthetic")
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"]["subsystems"]["DES-TRK-001"]["parameters"]
             ["point_resolution_um"].update(value=12.0))
        self.assertNotIn(f"{NS}:CALC-V", derive(self.b)["stale_evaluations"])
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"]["subsystems"]["DES-MAG-001"]["parameters"]
             ["field_T"].update(value=0.6))
        self.assertIn(f"{NS}:CALC-V", derive(self.b)["stale_evaluations"])

    def test_dependencies_warn_instead_of_stale(self):
        """TRC-06: a changed parameter-bound file is a warning in contracts/dependencies.py, not a hash mismatch."""
        from contracts.dependencies import validate_dependencies
        self.ok("budget", "--candidate", f"{NS}:cand-A", "--quantity", "mass", "--id", "CALC-M")
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"].update(description="changed"))
        rep = validate_dependencies(self.b.art / "evaluations/CALC-M.json", self.b.art)
        codes = {f["code"] for f in rep["findings"]}
        self.assertIn("dependency.parameters_bound_file_changed", codes)
        self.assertNotIn("dependency.hash_mismatch", codes)

    def test_forged_digest_is_a_mismatch(self):
        self.ok("budget", "--candidate", f"{NS}:cand-A", "--quantity", "mass", "--id", "CALC-M")
        edit(self.b, "evaluations/CALC-M.json", lambda d: d["extension"].update(parameter_digest="0" * 64))
        d = derive(self.b)
        self.assertIn("design.contract_mismatch", {e["code"] for e in d["errors"] if "CALC-M" in e["path"]})


class Incremental(Base):
    """INC-01..INC-04 with run_workflow.py; the M2 acceptance for the B field."""

    def setUp(self):
        super().setUp()
        self.wf_mod = load_module(WORKFLOW, "run_workflow_m2")
        self.wf_mod.plugin_release = lambda root=None: dict(KNOWN)  # a known release digest (INC-03)
        os.environ["SOURCE_DATE_EPOCH"] = "1792800000"

    def tearDown(self):
        os.environ.pop("SOURCE_DATE_EPOCH", None)
        super().tearDown()

    def run_wf(self, wf: dict, *extra):
        path = self.root / "wf.json"
        path.write_text(json.dumps(wf))
        code, out = call(self.wf_mod, [str(path), "--work", str(self.b.art), "--created", "2026-10-24", *extra])
        self.assertEqual(code, 0, out)
        return {s["id"].removeprefix("step-"): s.get("skipped", False) for s in out["steps"]}

    def design_step(self, sid, sub, *args, needs=(), inputs=()):
        """A workflow step running evaluate_design.py SUB; its skip key uses the parameters it reads (INC-02)."""
        script = ["{python}", "{plugin}/skills/hep-detector/scripts/evaluate_design.py", sub]
        common = ["--candidate", f"{NS}:cand-A", *args, "--id", sid, "--artifacts", "."]
        # the step id differs from the evaluation id: run_workflow.py writes runs/<step id>.computational-run.json
        return {"id": f"step-{sid}", "needs": [f"step-{n}" for n in needs], "inputs": ["candidates/cand-A.json", *inputs],
                "outputs": [f"evaluations/{sid}.json"], "argv": script + ["--replace"] + common,
                "parameter_digest": {"argv": script + ["--digest-only"] + common,
                                     "replaces": ["candidates/cand-A.json"]}}

    def test_b_field_reruns_only_field_steps(self):
        add_m2_parameters(self.b)
        wf = {"workflow": "design", "steps": [
            self.design_step("CALC-R", "run", "--requirement", "REQ-TRK-001"),
            self.design_step("CALC-C", "run", "--requirement", "REQ-CC-001", "--upstream", "evaluations/CALC-R.json",
                             needs=["CALC-R"], inputs=["evaluations/CALC-R.json"]),
            self.design_step("CALC-M", "budget", "--quantity", "mass"),
            self.design_step("CALC-A", "run", "--figure-of-merit", "geometric-acceptance", "--denominator",
                             "rigidity_GV=100", "--denominator", "species=proton", "--denominator", "charge_sign=positive")]}
        self.assertEqual(self.run_wf(wf, "--incremental"), dict.fromkeys(["CALC-R", "CALC-C", "CALC-M", "CALC-A"], False))
        records = {p.name: p.read_bytes() for p in (self.b.art / "runs").glob("*CALC-?.computational-run.json")}
        self.assertEqual(self.run_wf(wf, "--incremental"), dict.fromkeys(["CALC-R", "CALC-C", "CALC-M", "CALC-A"], True))
        self.assertEqual({p.name: p.read_bytes() for p in (self.b.art / "runs").glob("*CALC-?.computational-run.json")},
                         records)  # INC-04: nothing rewritten
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"]["subsystems"]["DES-MAG-001"]["parameters"]
             ["field_T"].update(value=0.6))
        self.assertEqual(self.run_wf(wf, "--incremental"),
                         {"CALC-R": False, "CALC-C": False, "CALC-M": True, "CALC-A": True})
        d = derive(self.b)
        self.assertFalse({f"{NS}:CALC-R", f"{NS}:CALC-C", f"{NS}:CALC-M", f"{NS}:CALC-A"} & set(d["stale_evaluations"]))
        self.assertFalse([e for e in d["errors"] if "CALC-" in e["path"] and "TRK-A" not in e["path"]], d["errors"])

    def simple_wf(self):
        (self.root / "step.py").write_text("import sys\nopen(sys.argv[1], 'w').write('x')\n")
        shutil.copy(self.root / "step.py", self.b.art / "step.py")
        return {"workflow": "w", "steps": [{"id": "s", "inputs": ["step.py"], "outputs": ["out.txt"],
                                            "argv": ["{python}", "step.py", "out.txt"]}]}

    def test_t51_rerun_is_identical_and_skipped(self):
        wf = self.simple_wf()
        self.assertEqual(self.run_wf(wf), {"s": False})
        rec = (self.b.art / "runs/s.computational-run.json").read_bytes()
        self.assertEqual(self.run_wf(wf), {"s": False})
        self.assertEqual((self.b.art / "runs/s.computational-run.json").read_bytes(), rec)  # INC-04
        doc = json.loads(rec)
        self.assertEqual(doc["extension"]["argv"], ["python3", "step.py", "out.txt"])  # INC-01
        self.assertEqual(doc["extension"]["script_sha256"], {"step.py": sha256(self.b.art / "step.py")})
        self.assertEqual(doc["versions"]["plugin_release"], KNOWN)
        self.assertIn("numpy", doc["extension"]["environment"])
        self.assertEqual(self.run_wf(wf, "--incremental"), {"s": True})

    def test_t52_changed_script_reruns(self):
        wf = self.simple_wf()
        self.run_wf(wf)
        (self.b.art / "step.py").write_text("import sys\nopen(sys.argv[1], 'w').write('y')\n")
        self.assertEqual(self.run_wf(wf, "--incremental"), {"s": False})

    def test_t53_unknown_digest_never_skips(self):
        wf = self.simple_wf()
        self.run_wf(wf)
        self.wf_mod.plugin_release = lambda root=None: {"release": "unreleased", "digest": "unknown"}
        self.run_wf(wf)
        self.assertEqual(self.run_wf(wf, "--incremental"), {"s": False})


class FidelityLadder(Base):
    def test_f2_toy_and_infield_acceptance(self):
        add_m2_parameters(self.b)
        out = self.ok("run", "--candidate", f"{NS}:cand-A", "--requirement", "REQ-TRK-001", "--fidelity", "F2",
                      "--id", "SIM-TOY", "--status", "synthetic")
        self.assertEqual((out["tool"], out["bound"]), ("toy-spectrometer:resolution", "estimate"))
        e = entry(derive(self.b), "REQ-TRK-001", "cand-A", "SIM-TOY")
        self.assertEqual((e["row"], e["code"]), (12, "fidelity.insufficient"))  # compliance needs F3
        out = self.ok("run", "--candidate", f"{NS}:cand-A", "--figure-of-merit", "geometric-acceptance",
                      "--denominator", "rigidity_GV=100", "--denominator", "species=proton",
                      "--denominator", "charge_sign=positive", "--fidelity", "F2", "--id", "SIM-ACC")
        doc = self.b.read(out["evaluation"])["extension"]
        self.assertEqual((doc["bound"], doc["fidelity"]), ("estimate", "F2"))
        self.assertGreater(doc["uncertainty"]["minus"], 0)

    def test_infield_acceptance_physics(self):
        """Straight-line limit at high rigidity; charge symmetry of two apertures (Liouville and time reversal);
        a dog-leg of three apertures favours one charge sign (ART-48)."""
        est = load_module(EST, "design_estimates_m2")
        straight = est.straight_line_acceptance([0, 1], [0.5, 0.5], [0, 0])[0]["acceptance_m2sr"]
        hi = est.infield_acceptance([0, 1], [0.5, 0.5], [0, 0], 0.5, 1e6, "positive", 0.0, 50000, 3)
        self.assertLess(abs(hi["acceptance_m2sr"] - straight), 3 * hi["statistical_m2sr"])
        low = est.infield_acceptance([0, 1], [0.5, 0.5], [0, 0], 0.5, 0.3, "positive", 0.0, 20000, 3)
        self.assertLess(low["acceptance_m2sr"], straight)
        two = [est.infield_acceptance([0, 1], [0.5, 0.5], [0, 0.6], 0.5, 1.0, s, 0.0, 20000, 3)["acceptance_m2sr"]
               for s in ("positive", "negative")]
        self.assertLess(abs(two[0] - two[1]), 0.02)
        three = [est.infield_acceptance([0, 1, 2], [0.5] * 3, [0, 0.3, 0.3], 0.5, 1.0, s, 0.0, 20000, 3)
                 for s in ("positive", "negative")]
        diff = abs(three[0]["acceptance_m2sr"] - three[1]["acceptance_m2sr"])
        self.assertGreater(diff, 4 * max(t["statistical_m2sr"] for t in three))

    def test_f3_response_assembly(self):
        """CHN-01: the F3 response evaluation and a parametrized response artifact for forward folding; assembled
        from an F1 core it stays optimistic (ADQ-05)."""
        add_m2_parameters(self.b)
        self.ok("run", "--candidate", f"{NS}:cand-A", "--requirement", "REQ-TRK-001", "--id", "CALC-R",
                "--status", "synthetic")
        out = self.ok("response", "--candidate", f"{NS}:cand-A", "--requirement", "REQ-TRK-001", "--upstream",
                      "evaluations/CALC-R.json", "--id", "SIM-RESP", "--status", "synthetic")
        self.assertEqual(out["bound"], "optimistic")
        resp = self.b.read(out["response"])
        self.assertEqual((resp["artifact_type"], resp["extension"]["form"], resp["extension"]["intended_use"]),
                         ("response", "parametrized", "forward_folding"))
        self.assertEqual(resp["inputs"][0]["ref"], out["evaluation"])
        m = matrix(derive(self.b), "REQ-TRK-001", "cand-A")
        self.assertTrue(any("in the chain of" in x and "now F1" in x for x in m["missing_evidence"]))


class Sensitivity(Base):
    """CHN-03..CHN-06: the expected precision written back from an Asimov statistical-result enters the comparison
    only when its chain is not optimistic and the fidelity vectors and denominators agree."""

    def stat_result(self, rel, value):
        doc = json.loads((PLUGIN / "contracts/fixtures/artifacts/valid/statres_v26.json").read_text())
        doc["status"] = ["synthetic", "asimov"]
        doc["extension"]["results"] = {"expected_relative_uncertainty": value}
        return self.b.write(rel, doc)

    def test_expected_precision_enters_comparison(self):
        r3 = fake_contract("syn-res3", "momentum-resolution-core", "estimate", "F3")
        cc4 = fake_contract("syn-cc4", "charge-confusion-rate", "estimate", "F4",
                            denominator={"rigidity_GV": "number", "species": "string", "charge_sign": "string",
                                         "curvature_offset_per_GV": "number"})
        mass = fake_contract("syn-mass", "mass-budget", "estimate", "F1", denominator={}, unit="kg")
        dirs = [write_contracts(self.root / "c", r3, cc4, mass)]
        cc_den = {"rigidity_GV": 1000.0, "species": "proton", "charge_sign": "positive", "curvature_offset_per_GV": 0.0}
        for c, prec in (("A", 0.06), ("B", 0.04)):
            r = fake_eval(self.b, f"SIM-R3-{c}", f"cand-{c}", r3, 0.3, uncertainty=gauss(0.08))
            cc = fake_eval(self.b, f"SIM-CC4-{c}", f"cand-{c}", cc4, 1e-4, denominator=cc_den,
                           uncertainty=gauss(4e-5, 0.95, distribution="exact"), fidelity="F3")
            fake_eval(self.b, f"CALC-MASS-{c}", f"cand-{c}", mass, 2400.0, denominator={}, uncertainty=gauss(10.0))
            sr = self.stat_result(f"stats/asimov-{c}.json", prec)
            out = self.ok("run", "--candidate", f"{NS}:cand-{c}", "--figure-of-merit", "expected-precision",
                          "--fidelity", "F3", "--upstream", r, "--upstream", cc, "--input-artifact", sr,
                          "--id", f"SIM-EP-{c}", "--status", "synthetic")
            self.assertEqual(out["bound"], "estimate")
        d = derive(self.b, dirs)
        self.assertTrue(d["comparison_basis"]["holds"], d["comparison_basis"])
        self.assertEqual(d["ranking"]["status"], "ranked", d["ranking"])
        self.assertEqual([o["candidates"] for o in d["ranking"]["order"]], [[f"{NS}:cand-B"], [f"{NS}:cand-A"]])
        self.assertIn("no global optimum", d["ranking"]["note"])

    def test_optimistic_chain_cannot_be_ranked(self):
        """CHN-05: built on F1 charge confusion the expected precision is optimistic and can only exclude."""
        for c in ("A", "B"):
            sr = self.stat_result(f"stats/asimov-{c}.json", 0.05)
            out = self.ok("run", "--candidate", f"{NS}:cand-{c}", "--figure-of-merit", "expected-precision",
                          "--fidelity", "F3", "--upstream", f"evaluations/CALC-TRK-{c}.json",
                          "--upstream", f"evaluations/CALC-CC-{c}.json", "--input-artifact", sr, "--id", f"SIM-EP-{c}",
                          "--status", "synthetic")
            self.assertEqual(out["bound"], "optimistic")
        mass = fake_contract("syn-mass", "mass-budget", "estimate", "F1", denominator={}, unit="kg")
        dirs = [write_contracts(self.root / "c", mass)]
        for c in ("A", "B"):
            fake_eval(self.b, f"CALC-MASS-{c}", f"cand-{c}", mass, 2400.0, denominator={}, uncertainty=gauss(10.0))
        d = derive(self.b, dirs)
        self.assertEqual(d["ranking"]["status"], "refused")
        self.assertIn("non-optimistic", d["ranking"]["reason"])

    def test_writeback_needs_an_asimov_result(self):
        doc = json.loads((PLUGIN / "contracts/fixtures/artifacts/valid/statres_v26.json").read_text())
        doc["extension"]["results"] = {"expected_relative_uncertainty": 0.05}
        sr = self.b.write("stats/observed.json", doc)
        code, out = ev(self.b, "run", "--candidate", f"{NS}:cand-A", "--figure-of-merit", "expected-precision",
                       "--fidelity", "F3", "--upstream", "evaluations/CALC-TRK-A.json", "--upstream",
                       "evaluations/CALC-CC-A.json", "--input-artifact", sr, "--id", "SIM-EP-A")
        self.assertEqual(code, 1, out)
        self.assertIn("Asimov", json.dumps(out["tool_output"]))


class F4Path(Base):
    """ART-30..ART-36, FID-03, FID-05 with SYNTHETIC study records (no Geant4 run)."""

    def study(self, rel, geometry_rel, value=0.3, tails=(), status=("unvalidated",), stat=0.01, envelope=None):
        result = {"value": value, "statistical_uncertainty": stat}
        if envelope:
            result["model_envelope"] = envelope
        ext = {"input_manifest": [{"path": geometry_rel, "sha256": sha256(self.b.art / geometry_rel)}],
               "tools": [{"name": "geant4", "version": "11.4.3"}], "commands": ["synthetic"], "environment": {},
               "seeds": {}, "tolerances": {}, "exit_status": 0, "output_hashes": {},
               "study": {"results": {"momentum-resolution-core": result}, "tail_sources_simulated": list(tails)}}
        return self.b.write(rel, self.b.envelope("computational-run", f"{NS}-study", ext, status=status))

    def setup_f4(self):
        self.ok("geometry", "--candidate", f"{NS}:cand-B", "--figure-of-merit", "momentum-resolution-core",
                "--denominator", "rigidity_GV=1000", "--denominator", "species=proton", "--id", "g1")
        return "studies/g1.geometry.json"

    def test_t46_not_upgraded_study_is_below_screening(self):
        g = self.setup_f4()
        s = self.study("studies/s1.computational-run.json", g, status=("validated-in-scope",))  # self-labelled
        self.ok("f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study", s, "--id", "SIM-G4")
        e = entry(derive(self.b), "REQ-TRK-001", "cand-B", "SIM-G4")
        self.assertEqual((e["row"], e["code"]), (8, "fidelity.insufficient"))

    def test_t33_study_of_another_geometry(self):
        """ART-35: a study that used another geometry file, or a geometry whose digest does not describe the
        candidate, is a contract mismatch."""
        g = self.setup_f4()
        other = self.b.write("studies/other.geometry.json", {"schema": "design-geometry/1", "parameter_digest": "0" * 64})
        s = self.study("studies/s1.computational-run.json", other)
        code, out = ev(self.b, "f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study", s,
                       "--id", "SIM-G4")
        self.assertEqual(code, 1, out)
        self.assertIn("design.contract_mismatch", {e["code"] for e in out["design_errors"]})
        edit(self.b, g, lambda d: d.update(parameter_digest="1" * 64))
        s2 = self.study("studies/s2.computational-run.json", g)
        code, out = ev(self.b, "f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study", s2,
                       "--id", "SIM-G5")
        self.assertEqual(code, 1, out)

    def test_t47_f4_without_tail_sources_is_optimistic(self):
        """FID-03: without alignment, calibration, digitization and pattern recognition simulated, an F4 resolution
        is optimistic; labelled estimate it is a contract mismatch."""
        g = self.setup_f4()
        s = self.study("studies/s1.computational-run.json", g)
        out = self.ok("f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study", s, "--id", "SIM-G4")
        self.assertEqual(out["bound"], "optimistic")
        edit(self.b, "evaluations/SIM-G4.json", lambda d: d["extension"].update(bound="estimate"))
        d = derive(self.b)
        self.assertIn("design.contract_mismatch", {e["code"] for e in d["errors"] if "SIM-G4" in e["path"]})
        s2 = self.study("studies/s2.computational-run.json", g, tails=("alignment", "calibration-non-uniformity",
                                                                       "noise-digitization", "pattern-recognition"))
        out = self.ok("f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study", s2, "--id", "SIM-G5")
        self.assertEqual(out["bound"], "estimate")

    def test_geometry_change_makes_f4_stale(self):
        g = self.setup_f4()
        s = self.study("studies/s1.computational-run.json", g)
        self.ok("f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study", s, "--id", "SIM-G4")
        edit(self.b, "candidates/cand-B.json", lambda d: d["extension"]["subsystems"]["DES-MAG-001"]["parameters"]
             ["field_T"].update(value=0.6))
        self.assertIn(f"{NS}:SIM-G4", derive(self.b)["stale_evaluations"])

    def test_fid05_envelope_straddling_the_target(self):
        """FID-05: an estimate whose model envelope straddles the target is margin.within_uncertainty."""
        r = fake_contract("syn-res3", "momentum-resolution-core", "estimate", "F3")
        dirs = [write_contracts(self.root / "c", r)]
        fake_eval(self.b, "SIM-ENV", "cand-B", r, 0.3, uncertainty=gauss(0.07), model_envelope=[0.2, 0.8])
        fake_eval(self.b, "SIM-ENV2", "cand-A", r, 0.3, uncertainty=gauss(0.08), model_envelope=[0.2, 0.35])
        d = derive(self.b, dirs)
        self.assertEqual(entry(d, "REQ-TRK-001", "cand-B", "SIM-ENV")["code"], "margin.within_uncertainty")
        self.assertEqual(entry(d, "REQ-TRK-001", "cand-A", "SIM-ENV2")["row"], 16)


if __name__ == "__main__":
    unittest.main()
