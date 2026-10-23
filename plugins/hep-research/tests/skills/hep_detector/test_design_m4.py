"""Detector system design M4 (design space): parameter scans stored as one summary computational-run (OQ-18, AGG-08,
RSK-04), local sensitivities, expansion of a scan point into a candidate, and the Pareto front gated by the comparison
basis and the CHN-06 evaluations (ART-15, RPT-07). Every project is the SYNTHETIC spectrometer of
tests/contracts/design_fixtures.py."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "tests" / "contracts"))
from design_fixtures import NS, copy_fixture, derive, edit, fake_contract, fake_eval, gauss, write_contracts  # noqa: E402

EVAL = PLUGIN / "skills" / "hep-detector" / "scripts" / "evaluate_design.py"
_spec = importlib.util.spec_from_file_location("evaluate_design_m4", EVAL)
EV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EV)

TRK = ["--figure-of-merit", "momentum-resolution-core", "--denominator", "rigidity_GV=1000",
       "--denominator", "species=proton"]


def ev(b, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = EV.main([*map(str, args), "--artifacts", str(b.art)])
    return code, json.loads(buf.getvalue())


def verdicts(d: dict) -> dict:
    return {(item["id"], tuple(m["candidates"])): (m["result"], tuple(m["codes"]))
            for item in d["requirements"] + d["constraints"] for m in item["matrix"]}


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

    def scan(self, sid="SCAN-A-1", *vary):
        vary = vary or ("DES-TRK-001.parameters.point_resolution_um=5,20", "DES-MAG-001.parameters.field_T=0.25,1.0")
        return self.ok("scan", "--candidate", f"{NS}:cand-A", *TRK, *[x for v in vary for x in ("--vary", v)],
                       "--id", sid, "--status", "synthetic")


class Scan(Base):
    def test_one_summary_run_and_no_evaluation(self):
        """OQ-18, RSK-04: a 3 x 3 grid (the candidate's own values included) is one computational-run with every point;
        no evaluation file is written and the derived verdicts do not change (AGG-08)."""
        before = verdicts(derive(self.b))
        n_evals = len(list((self.b.art / "evaluations").glob("*.json")))
        out = self.scan()
        self.assertEqual((out["points"], out["failed_points"]), (9, 0))
        run = self.b.read(out["scan"])["extension"]
        summary = run["scan_summary"]
        self.assertEqual(summary["parameters"], ["DES-TRK-001.parameters.point_resolution_um",
                                                 "DES-MAG-001.parameters.field_T"])
        self.assertEqual(len(list((self.b.art / "evaluations").glob("*.json"))), n_evals)
        self.assertFalse((self.b.art / "outputs" / "CALC-scan-point-0.json").exists())
        d = derive(self.b)
        self.assertEqual(verdicts(d), before)
        self.assertEqual(d["orphan_runs"], [])  # AGG-08: the scan summary is exempt
        self.assertEqual(d["status"], "ok", d["errors"])
        own = next(p for p in summary["points"] if p["parameters"] == {
            "DES-TRK-001.parameters.point_resolution_um": 10.0, "DES-MAG-001.parameters.field_T": 0.5})
        trk_a = self.b.read("evaluations/CALC-TRK-A.json")["extension"]
        self.assertAlmostEqual(own["value"], trk_a["value"], places=12)  # the candidate's own point reproduces run

    def test_sensitivities_at_the_candidates_own_values(self):
        """At 1 TV the resolution is measurement-dominated: d ln sigma/d ln point resolution is near +1 and
        d ln sigma/d ln B near -1 (sigma_p/p ~ sigma_x p / (B L^2))."""
        sens = {s["parameter"]: s for s in self.scan()["sensitivity"]}
        self.assertGreater(sens["DES-TRK-001.parameters.point_resolution_um"]["elasticity"], 0.8)
        self.assertLess(sens["DES-MAG-001.parameters.field_T"]["elasticity"], -0.8)
        self.assertEqual(sens["DES-MAG-001.parameters.field_T"]["difference"], "central")

    def test_refusals(self):
        cases = {
            "unknown parameter": ["--vary", "DES-TRK-001.parameters.nothing=1,2"],
            "non-numeric": ["--vary", "DES-TRK-001.parameters.layer_positions_m=1,2"],
            "bad id": ["--vary", "DES-MAG-001.parameters.field_T=0.4", "--id-override"],
        }
        for label, extra in cases.items():
            with self.subTest(case=label):
                sid = "bad" if label == "bad id" else "SCAN-X"
                extra = [x for x in extra if x != "--id-override"]
                code, out = ev(self.b, "scan", "--candidate", f"{NS}:cand-A", *TRK, *extra, "--id", sid)
                self.assertEqual(code, 2, out)
        code, out = ev(self.b, "scan", "--candidate", f"{NS}:cand-A", *TRK, "--vary",
                       "DES-MAG-001.parameters.field_T=0.1,0.2,0.3,0.4", "--max-points", "3", "--id", "SCAN-X")
        self.assertEqual(code, 2, out)
        self.assertIn("exceed", out["error"])
        code, out = ev(self.b, "scan", "--candidate", f"{NS}:cand-A", "--figure-of-merit", "charge-confusion-rate",
                       "--denominator", "rigidity_GV=1000", "--denominator", "species=proton",
                       "--denominator", "charge_sign=positive", "--denominator", "curvature_offset_per_GV=0",
                       "--vary", "DES-MAG-001.parameters.field_T=0.4", "--id", "SCAN-X")
        self.assertEqual(code, 2, out)  # an operation with required upstreams is not scanned
        self.assertIn("upstream", out["error"])

    def test_a_scan_point_supports_no_verdict(self):
        """AGG-08: an evaluation that names a scan summary as its run is a design error and decides nothing."""
        out = self.scan()
        doc = self.b.read("evaluations/CALC-TRK-A.json")
        doc["extension"]["run_ref"] = out["scan"]
        doc["artifact_id"] = f"{NS}-CALC-FROM-SCAN"
        doc["extension"]["evaluation_id"] = f"{NS}:CALC-FROM-SCAN"
        self.b.write("evaluations/CALC-FROM-SCAN.json", doc)
        d = derive(self.b)
        self.assertIn("design.scan_point_not_expanded",
                      {e["code"] for e in d["errors"] if "CALC-FROM-SCAN" in e["path"]})


class Expand(Base):
    def test_only_expanded_points_enter_comparison(self):
        """M4 acceptance: a point becomes a candidate (derived_from, overrides of the scanned parameters) and enters the
        compliance matrix only when expanded and evaluated; its evaluation reproduces the scan point."""
        out = self.scan()
        summary = self.b.read(out["scan"])["extension"]["scan_summary"]
        point = next(p for p in summary["points"] if p["parameters"]["DES-MAG-001.parameters.field_T"] == 1.0
                     and p["parameters"]["DES-TRK-001.parameters.point_resolution_um"] == 5.0)
        d = derive(self.b)
        self.assertNotIn(f"{NS}:cand-A-hi", {c for x in d["candidates"] for c in x["candidates"]})
        exp = self.ok("expand", "--scan", out["scan"], "--point", point["index"], "--candidate-id", "cand-A-hi")
        cand = self.b.read(exp["file"])["extension"]
        self.assertEqual(cand["derived_from"], f"{NS}:cand-A")
        self.assertEqual(cand["overrides"]["DES-MAG-001"]["parameters"]["field_T"]["value"], 1.0)
        res = self.ok("run", "--candidate", f"{NS}:cand-A-hi", "--requirement", "REQ-TRK-001", "--id", "CALC-TRK-A-hi",
                      "--status", "synthetic")
        self.assertAlmostEqual(res["value"], point["value"], places=12)
        d = derive(self.b)
        rows = [m for item in d["requirements"] if item["id"].endswith("REQ-TRK-001") for m in item["matrix"]
                if f"{NS}:cand-A-hi" in m["candidates"]]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["used"][0]["evaluation"], f"{NS}:CALC-TRK-A-hi")

    def test_expand_refuses_a_missing_point(self):
        out = self.scan()
        code, res = ev(self.b, "expand", "--scan", out["scan"], "--point", 99, "--candidate-id", "cand-x")
        self.assertEqual(code, 2, res)
        code, res = ev(self.b, "expand", "--scan", "evaluations/CALC-TRK-A.json", "--point", 0, "--candidate-id", "x")
        self.assertEqual(code, 2, res)


class Pareto(Base):
    def setup_axes(self, ep, mass, axes=("expected-precision", "mass-budget")):
        """Two candidates with expected-precision (F3 estimate) and F1 mass evaluations; values per candidate."""
        epc = fake_contract("syn-ep", "expected-precision", "estimate", "F3")
        mc = fake_contract("syn-mass", "mass-budget", "estimate", "F1", denominator={}, unit="kg")
        dirs = [write_contracts(self.root / "c", epc, mc)]
        for c in ("A", "B"):
            fake_eval(self.b, f"SIM-EP-{c}", f"cand-{c}", epc, ep[c][0], uncertainty=gauss(ep[c][1]))
            fake_eval(self.b, f"CALC-MASS-{c}", f"cand-{c}", mc, mass[c][0], denominator={},
                      uncertainty=gauss(mass[c][1]))
        edit(self.b, "design-spec.v1.json", lambda s: s["extension"]["comparison_basis"].update(pareto_axes=list(axes)))
        return dirs

    def test_not_requested_without_axes(self):
        self.assertEqual(derive(self.b)["pareto"]["status"], "not-requested")

    def test_front_with_a_dominated_candidate(self):
        """CHN-06: B is better on expected precision beyond the uncertainties and no heavier, so A is dominated."""
        dirs = self.setup_axes({"A": (0.06, 0.005), "B": (0.04, 0.005)}, {"A": (2400.0, 10.0), "B": (2395.0, 10.0)})
        d = derive(self.b, dirs)
        self.assertTrue(d["comparison_basis"]["holds"], d["comparison_basis"])
        par = d["pareto"]
        self.assertEqual(par["status"], "computed", par)
        self.assertEqual(par["front"], [[f"{NS}:cand-B"]])
        self.assertEqual(par["dominated"], [{"candidates": [f"{NS}:cand-A"], "by": [f"{NS}:cand-B"]}])
        self.assertIn("no global optimum", par["note"])

    def test_trade_off_keeps_both(self):
        """A lighter but less precise candidate is not dominated: both stay on the front."""
        dirs = self.setup_axes({"A": (0.06, 0.005), "B": (0.04, 0.005)}, {"A": (2350.0, 10.0), "B": (2400.0, 10.0)})
        par = derive(self.b, dirs)["pareto"]
        self.assertEqual((par["status"], len(par["front"]), par["dominated"]), ("computed", 2, []))

    def test_differences_within_the_uncertainties_dominate_nothing(self):
        dirs = self.setup_axes({"A": (0.050, 0.01), "B": (0.045, 0.01)}, {"A": (2400.0, 10.0), "B": (2395.0, 10.0)})
        par = derive(self.b, dirs)["pareto"]
        self.assertEqual((par["status"], par["dominated"]), ("computed", []))

    def test_refusals(self):
        """RPT-07: refused, with every reason, when the basis does not hold, without expected precision (CHN-00), or
        with an optimistic evaluation (CHN-06)."""
        dirs = self.setup_axes({"A": (0.06, 0.005), "B": (0.04, 0.005)}, {"A": (2400.0, 10.0), "B": (3000.0, 10.0)})
        par = derive(self.b, dirs)["pareto"]
        self.assertEqual(par["status"], "refused")
        self.assertTrue(any("ART-15" in r for r in par["reasons"]), par)
        b2 = copy_fixture(self.root / "q")
        self.b = b2
        dirs = self.setup_axes({"A": (0.06, 0.005), "B": (0.04, 0.005)}, {"A": (2400.0, 10.0), "B": (2395.0, 10.0)},
                               axes=("mass-budget", "power-budget"))
        par = derive(self.b, dirs)["pareto"]
        self.assertTrue(any("CHN-00" in r for r in par["reasons"]), par)
        self.assertTrue(any("power-budget" in r and "CHN-06" in r for r in par["reasons"]), par)
        b3 = copy_fixture(self.root / "r")
        self.b = b3
        epc = fake_contract("syn-ep", "expected-precision", "optimistic", "F3")
        mc = fake_contract("syn-mass", "mass-budget", "estimate", "F1", denominator={}, unit="kg")
        dirs = [write_contracts(self.root / "c3", epc, mc)]
        for c in ("A", "B"):
            fake_eval(self.b, f"SIM-EP-{c}", f"cand-{c}", epc, 0.05, uncertainty=gauss(0.005))
            fake_eval(self.b, f"CALC-MASS-{c}", f"cand-{c}", mc, 2400.0, denominator={}, uncertainty=gauss(10.0))
        edit(self.b, "design-spec.v1.json", lambda s: s["extension"]["comparison_basis"].update(
            pareto_axes=["expected-precision", "mass-budget"]))
        par = derive(self.b, dirs)["pareto"]
        self.assertEqual(par["status"], "refused")
        self.assertTrue(any("non-optimistic" in r for r in par["reasons"]), par)

    def test_report_renders_the_front(self):
        dirs = self.setup_axes({"A": (0.06, 0.005), "B": (0.04, 0.005)}, {"A": (2400.0, 10.0), "B": (2395.0, 10.0)})
        full = EV.design.derive(self.b.art, self.b.dec, [EV.design.CONTRACT_DIR, *dirs])
        md = EV.render(full, [])
        self.assertIn(f"Pareto front on expected-precision, mass-budget: {NS}:cand-B", md)
        self.assertIn(f"{NS}:cand-A dominated by {NS}:cand-B", md)


if __name__ == "__main__":
    unittest.main()
