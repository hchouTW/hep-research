"""evaluate_design.py and design_estimates.py (detector system design spec M1): evaluations run from the tool
contracts pass value, validity domain, fidelity and bound through unchanged (T-58), config-file inputs (ART-41,
ART-72), capability.unavailable records (ART-50, ART-63), the report (RPT-*: T-31 omitted evaluations stay in the
aggregation, T-35 ranking refused without a holding comparison basis), the plan (RES-04), and the M1 contracts'
declared directions (T-57). Every project is the SYNTHETIC spectrometer of tests/contracts/design_fixtures.py."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from statistics import NormalDist

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "tests" / "contracts"))
from contracts import design  # noqa: E402
from design_fixtures import NS, copy_fixture, derive, edit, param  # noqa: E402

SCRIPTS = PLUGIN / "skills" / "hep-detector" / "scripts"
EVAL = SCRIPTS / "evaluate_design.py"
EST = SCRIPTS / "design_estimates.py"
PHI = NormalDist().cdf


def run(script, *args):
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True, timeout=600)
    return p.returncode, (json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout)


class Project(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.b = copy_fixture(Path(self.tmp.name) / "p")

    def tearDown(self):
        self.tmp.cleanup()

    def ev(self, *args):
        return run(EVAL, *args, "--artifacts", self.b.art)

    def add_pid_and_apertures(self, cand="cand-B"):
        """TOF, RICH and aperture parameters on a candidate (the fixture candidates have only tracker and magnet)."""
        def add(doc):
            subs = doc["extension"]["subsystems"]
            n = len(subs["DES-TRK-001"]["parameters"]["layer_positions_m"]["value"])
            subs["DES-TRK-001"]["parameters"]["layer_aperture_radius_m"] = param([0.5] * n, "m")
            subs["DES-TRK-001"]["parameters"]["layer_lateral_offset_m"] = param([0.0] * n, "m")
            calib = {"method": "synthetic", "control_samples": ["synthetic"]}
            subs["DES-TOF-001"] = {"role": "tof", "technology": "scintillator", "calibration": calib,
                                   "parameters": {"path_m": param(1.2, "m"), "time_resolution_ps": param(100.0, "ps")}}
            subs["DES-RICH-001"] = {"role": "rich", "technology": "aerogel RICH", "calibration": calib,
                                    "parameters": {"refractive_index": param(1.05, "1"),
                                                   "radiator_length_cm": param(3.0, "cm"),
                                                   "n0_per_cm": param(90.0, "1/cm"),
                                                   "single_photon_resolution_mrad": param(5.0, "mrad"),
                                                   "track_resolution_mrad": param(1.0, "mrad")}}
        edit(self.b, f"candidates/{cand}.json", add)


class PassThrough(Project):
    """T-58, REP-10: what evaluate_design.py writes is exactly what the contract and the tool output give."""

    def assert_passthrough(self, rel, fom):
        doc = self.b.read(rel)
        ext = doc["extension"]
        run_doc = self.b.read(ext["run_ref"])
        out = json.loads((self.b.art / run_doc["outputs"][0]["ref"]).read_text())
        proj = design.Project(self.b.art)
        design.analyze_evaluations(proj)
        ev = proj.evals[proj.resolve(rel)]
        self.assertEqual(ev.errors, [], ev.errors)
        reg = design.Registry()
        c = reg.by_script(next(a for a in run_doc["extension"]["argv"] if a.endswith(".py")))
        fd = next(f for op in c["operations"] for f in (op.get("design") or {}).get("figures_of_merit", [])
                  if f["id"] == fom and run_doc["extension"]["argv"][2:2 + len(f.get("operation_args", []))]
                  == f.get("operation_args", []))
        value, _ = design.output_value(fd, ext["denominator"], out)
        self.assertEqual(ext["value"], value)
        self.assertEqual(ext["bound"], ev.bound)
        self.assertEqual(ext["validity"]["in_domain"], not ev.domain)
        return ext, ev

    def test_resolution_and_composite(self):
        rc, out = self.ev("run", "--candidate", f"{NS}:cand-A", "--requirement", "REQ-TRK-001", "--id", "CALC-TRK-A2",
                          "--status", "synthetic")
        self.assertEqual(rc, 0, out)
        ext, _ = self.assert_passthrough(out["evaluation"], "momentum-resolution-core")
        fixture = self.b.read("evaluations/CALC-TRK-A.json")["extension"]
        for k in ("value", "bound", "fidelity", "parameter_refs", "denominator"):
            self.assertEqual(ext[k], fixture[k], k)  # the M0 fixture builder and the wrapper agree
        rc, out = self.ev("run", "--candidate", f"{NS}:cand-A", "--requirement", "REQ-CC-001", "--id", "CALC-CC-A2",
                          "--upstream", "evaluations/CALC-TRK-A2.json", "--status", "synthetic")
        self.assertEqual(rc, 0, out)
        ext, _ = self.assert_passthrough(out["evaluation"], "charge-confusion-rate")
        self.assertEqual(ext["value"], self.b.read("evaluations/CALC-CC-A.json")["extension"]["value"])

    def test_below_crossover_estimate_passes_through(self):
        rc, out = self.ev("run", "--candidate", f"{NS}:cand-A", "--figure-of-merit", "momentum-resolution-core",
                          "--denominator", "rigidity_GV=10", "--denominator", "species=proton", "--status", "synthetic")
        self.assertEqual(rc, 0, out)
        ext, _ = self.assert_passthrough(out["evaluation"], "momentum-resolution-core")
        self.assertEqual(ext["bound"], "estimate")

    def test_mdr_two_operations_and_config_file(self):
        """ART-41, ART-72: multiple_scattering reads a stack file generated from the candidate; the tracker's exact-fit
        MDR is optimistic, the Gluckstern one an estimate with its uncertainty from the contract."""
        args = ["--candidate", f"{NS}:cand-B", "--figure-of-merit", "maximum-detectable-rigidity",
                "--denominator", "species=proton", "--denominator", "mdr_definition=intrinsic", "--status", "synthetic"]
        rc, out = self.ev("run", *args)
        self.assertEqual(rc, 2, out)  # two operations compute it at F1: --tool is required
        rc, out = self.ev("run", *args, "--tool", "multiple-scattering:resolution", "--id", "CALC-MDR-B-ms")
        self.assertEqual(rc, 0, out)
        ext, _ = self.assert_passthrough(out["evaluation"], "maximum-detectable-rigidity")
        self.assertEqual((ext["bound"], ext["uncertainty"]["minus"]), ("estimate", 0.12 * ext["value"]))
        run_doc = self.b.read(ext["run_ref"])
        cfg = [m for m in run_doc["extension"]["input_manifest"] if m["path"].startswith("configs/")]
        self.assertEqual(len(cfg), 1)
        stack = json.loads((self.b.art / cfg[0]["path"]).read_text())
        self.assertEqual(stack["field_tesla"], 0.5)
        self.assertAlmostEqual(stack["lever_arm_m"], 3.0)
        rc, out = self.ev("run", *args, "--tool", "tracker-resolution:momentum", "--id", "CALC-MDR-B-tr")
        self.assertEqual(rc, 0, out)
        ext2, _ = self.assert_passthrough(out["evaluation"], "maximum-detectable-rigidity")
        self.assertEqual(ext2["bound"], "optimistic")
        self.assertLess(ext["value"], ext2["value"])  # Gluckstern (N = 5) overstates the intrinsic term
        # tampering with the config file after the run is a contract mismatch
        p = self.b.art / cfg[0]["path"]
        p.write_text(json.dumps(dict(stack, field_tesla=0.6)))
        proj = design.Project(self.b.art)
        design.analyze_evaluations(proj)
        self.assertIn("design.contract_mismatch", {c for c, _ in proj.evals[proj.resolve("evaluations/CALC-MDR-B-ms.json")].errors})

    def test_pid_chain_acceptance_and_rich(self):
        self.add_pid_and_apertures()
        for rel in ("runs/CALC-TRK-B.computational-run.json", "evaluations/CALC-TRK-B.json",
                    "runs/CALC-CC-B.computational-run.json", "evaluations/CALC-CC-B.json"):
            self.b.rebind(rel)
        pid = ["--denominator", "momentum_GeV=2", "--denominator", "species=proton",
               "--denominator", "background_species=positron", "--denominator", "separation_convention=single"]
        rc, out = self.ev("run", "--candidate", f"{NS}:cand-B", "--figure-of-merit", "pid-separation-power", *pid,
                          "--tool", "pid-separation-power:separation", "--id", "CALC-TOF-B")
        self.assertEqual(rc, 0, out)
        sep, _ = self.assert_passthrough(out["evaluation"], "pid-separation-power")
        rc, out = self.ev("run", "--candidate", f"{NS}:cand-B", "--figure-of-merit", "pid-rejection", *pid,
                          "--denominator", "working_point_efficiency=0.9", "--id", "CALC-REJ-B")
        self.assertEqual(rc, 0, out)
        rej, _ = self.assert_passthrough(out["evaluation"], "pid-rejection")
        s = sep["value"]
        self.assertAlmostEqual(rej["value"], 1 / PHI(NormalDist().inv_cdf(0.9) - s), places=6)
        self.assertEqual(rej["bound"], "optimistic")
        rc, out = self.ev("run", "--candidate", f"{NS}:cand-B", "--figure-of-merit", "geometric-acceptance",
                          "--denominator", "rigidity_GV=100", "--denominator", "species=proton",
                          "--denominator", "charge_sign=positive", "--id", "CALC-ACC-B")
        self.assertEqual(rc, 0, out)
        acc, _ = self.assert_passthrough(out["evaluation"], "geometric-acceptance")
        self.assertGreater(acc["value"], 0)
        rc, out = self.ev("run", "--candidate", f"{NS}:cand-B", "--figure-of-merit", "pid-separation-power",
                          "--denominator", "momentum_GeV=3", "--denominator", "species=pion",
                          "--denominator", "background_species=kaon", "--denominator", "separation_convention=single",
                          "--tool", "cherenkov-angle:kinematics", "--id", "CALC-RICH-B")
        self.assertEqual(rc, 0, out)
        self.assert_passthrough(out["evaluation"], "pid-separation-power")

    def test_offsets_put_acceptance_outside_the_domain(self):
        """ART-48: with lateral offsets the straight-line value is outside the contract's validity domain."""
        self.add_pid_and_apertures()
        edit(self.b, "candidates/cand-B.json", lambda d: d["extension"]["subsystems"]["DES-TRK-001"]["parameters"]
             ["layer_lateral_offset_m"].update(value=[0.0, 0.02, 0.0, 0.0, 0.0]))
        rc, out = self.ev("run", "--candidate", f"{NS}:cand-B", "--figure-of-merit", "geometric-acceptance",
                          "--denominator", "rigidity_GV=100", "--denominator", "species=proton",
                          "--denominator", "charge_sign=positive", "--id", "CALC-ACC-B")
        self.assertEqual(rc, 0, out)
        self.assertTrue(out["outside_validity_domain"])
        ext, ev = self.assert_passthrough(out["evaluation"], "geometric-acceptance")
        self.assertFalse(ext["validity"]["in_domain"])

    def test_budget_sum(self):
        rc, out = self.ev("budget", "--candidate", f"{NS}:cand-A", "--quantity", "mass", "--status", "synthetic")
        self.assertEqual(rc, 0, out)
        ext, _ = self.assert_passthrough(out["evaluation"], "mass-budget")
        self.assertEqual((ext["value"], ext["uncertainty"]["minus"]), (2400.0, 480.0))  # linear sum (CHN-10)
        self.assertIn("subsystems", ext["parameter_refs"])


class Records(Project):
    def test_unavailable_and_mismatch(self):
        """ART-50, ART-63: with no evaluator at that fidelity an unavailable evaluation is written."""
        rc, out = self.ev("run", "--candidate", f"{NS}:cand-A", "--figure-of-merit", "momentum-resolution-core",
                          "--denominator", "rigidity_GV=1000", "--denominator", "species=proton", "--fidelity", "F3")
        self.assertEqual((rc, out["capability"]), (0, "unavailable"), out)
        doc = self.b.read(out["evaluation"])["extension"]
        self.assertTrue(doc["unavailable"])
        self.assertNotIn("value", doc)

    def test_nothing_kept_on_failure(self):
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"]["subsystems"]["DES-MAG-001"]["parameters"]
             .pop("field_T"))
        before = sorted(p.relative_to(self.b.art) for p in self.b.art.rglob("*"))
        rc, out = self.ev("run", "--candidate", f"{NS}:cand-A", "--requirement", "REQ-TRK-001", "--id", "X")
        self.assertEqual(rc, 2, out)
        self.assertIn("field_T", out["error"])
        self.assertEqual(sorted(p.relative_to(self.b.art) for p in self.b.art.rglob("*")), before)

    def test_existing_id_is_never_overwritten(self):
        rc, out = self.ev("run", "--candidate", f"{NS}:cand-A", "--requirement", "REQ-TRK-001", "--id", "CALC-TRK-A")
        self.assertEqual(rc, 2, out)
        self.assertIn("exists", out["error"])


class Report(Project):
    def test_t31_omitted_evaluation_stays_aggregated(self):
        """AGG-06, AGG-07: --omit hides an evaluation from the rendering; the matrix still uses it."""
        rc, out = self.ev("report", "--omit", f"{NS}:CALC-TRK-P")
        self.assertEqual(rc, 0, out)
        rep = self.b.read(out["report"])
        self.assertEqual(rep["artifact_type"], "communication")
        self.assertEqual(rep["provenance"]["producer_skill"], "hep-detector")
        dr = rep["extension"]["design_report"]
        self.assertEqual(dr["omitted_from_rendering"], [f"{NS}:CALC-TRK-P"])
        row = next(m for r in dr["requirements"] if r["id"].endswith("REQ-TRK-001") for m in r["matrix"]
                   if f"{NS}:cand-P" in m["candidates"])
        self.assertEqual((row["result"], [u["evaluation"] for u in row["used"]]), ("fail", [f"{NS}:CALC-TRK-P"]))
        md = (self.b.art / out["rendering"]).read_text()
        self.assertTrue(md.startswith("# Design report"))
        self.assertIn("gate.H1_missing", md.split("\n\n")[2])  # RPT-02: gate flags at the top
        self.assertIn("Omitted from this rendering on request (still aggregated)", md)
        self.assertNotIn(f"used {NS}:CALC-TRK-P ", md)
        refs = {i["ref"] for i in rep["inputs"]}
        self.assertIn("design-spec.v1.json", refs)  # RPT-10
        self.assertIn("evaluations/CALC-TRK-P.json", refs)

    def test_t35_ranking_refused(self):
        """ART-15, RPT-07: undeclared basis, a basis that does not hold, and one that holds (ranking still not given in
        the first release, OQ-04)."""
        edit(self.b, "design-spec.v1.json", lambda s: s["extension"].pop("comparison_basis"))
        d = derive(self.b)
        self.assertEqual(d["ranking"]["status"], "refused")
        self.assertFalse(d["comparison_basis"]["declared"])
        edit(self.b, "design-spec.v1.json", lambda s: s["extension"].update(
            comparison_basis={"quantity": "mass-budget", "tolerance_relative": 0.05}))
        for c in ("cand-A", "cand-B"):
            self.assertEqual(self.ev("budget", "--candidate", f"{NS}:{c}", "--quantity", "mass", "--status",
                                     "synthetic")[0], 0)
        d = derive(self.b)  # 20% estimate-basis uncertainties: the difference plus its uncertainty exceeds 5%
        self.assertEqual((d["comparison_basis"]["holds"], d["ranking"]["status"]), (False, "refused"))
        rc, out = self.ev("report", "--name", "r1")
        self.assertIn("ranking: refused", (self.b.art / out["rendering"]).read_text())

    def test_plan(self):
        rc, out = self.ev("plan")
        self.assertEqual(rc, 0, out)
        whys = [s["why"] for s in out["suggestions"]]
        self.assertTrue(any("no evaluation" in w for w in whys))  # the mass constraint
        self.assertTrue(any("gate" in w for w in whys))


class Estimates(unittest.TestCase):
    """design_estimates.py: oracles and the declared directions of its contract (T-57)."""

    def test_acceptance_matches_sullivan(self):
        for r1, r2, d in ((0.5, 0.5, 1.0), (0.3, 0.6, 2.0), (0.1, 0.1, 0.5)):
            rc, out = run(EST, "straight-line-acceptance", "--z-m", 0, d, "--radius-m", r1, r2,
                          "--lateral-offset-m", 0, 0)
            self.assertEqual(rc, 0, out)
            self.assertAlmostEqual(out["acceptance_m2sr"] / out["sullivan_two_aperture_m2sr"], 1.0, delta=2e-4)

    def test_acceptance_is_an_upper_bound(self):
        """A middle aperture can only remove lines (the straight-line value of the outer pair is an upper bound)."""
        two = run(EST, "straight-line-acceptance", "--z-m", 0, 1, "--radius-m", 0.5, 0.5, "--lateral-offset-m", 0, 0)[1]
        three = run(EST, "straight-line-acceptance", "--z-m", 0, 0.5, 1, "--radius-m", 0.5, 0.3, 0.5,
                    "--lateral-offset-m", 0, 0, 0)[1]
        self.assertLess(three["acceptance_m2sr"], two["acceptance_m2sr"])
        off = run(EST, "straight-line-acceptance", "--z-m", 0, 1, "--radius-m", 0.5, 0.5, "--lateral-offset-m", 0, 0.1)[1]
        self.assertTrue(off["warnings"])

    def test_pid_rejection_directions(self):
        """ART-45: separation (order-preserving) at two points; ART-46: heavier tails give a lower rejection."""
        r = lambda s: run(EST, "pid-rejection", "--separation", s, "--efficiency", 0.9, "--convention", "single")[1]  # noqa: E731
        self.assertGreater(r(4)["rejection"], r(3)["rejection"])
        q = run(EST, "pid-rejection", "--separation", 4 / math.sqrt(2), "--efficiency", 0.9, "--convention",
                "quadrature")[1]
        self.assertAlmostEqual(q["rejection"], r(4)["rejection"], places=6)
        g = r(4)
        t = g["cut_sigma"]
        tail = 0.99 * PHI(t - 4) + 0.01 * 0.5 * math.exp(-(4 - t) / 1.0)  # a 1% exponential tail toward the signal
        self.assertGreater(tail, g["misidentification"])

    def test_budget_rules(self):
        lin = run(EST, "budget-sum", "--estimates", 1, 2, "--uncertainties", 3, 4)[1]
        quad = run(EST, "budget-sum", "--estimates", 1, 2, "--uncertainties", 3, 4, "--rule", "quadrature")[1]
        self.assertEqual((lin["total"], lin["uncertainty"], quad["uncertainty"]), (3.0, 7.0, 5.0))
        self.assertEqual(run(EST, "budget-sum", "--estimates", 1, "--uncertainties", 1, 2)[0], 2)


if __name__ == "__main__":
    unittest.main()
