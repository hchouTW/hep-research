"""Detector system design follow-ups of the M3 reviews (contracts 3.12.0, adequacy table 1.1.0): a derived requirement
is covered by a driving one (covered_by, MAT-04 d), a hard constraint states its subsystem scope (subsystems), and the
measured curvature offset must cover the offset a charge-confusion requirement assumes (ADQ-02 value check). Every
project is the SYNTHETIC spectrometer of tests/contracts/design_fixtures.py."""
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "tests" / "contracts"))
from contracts import design  # noqa: E402
from design_fixtures import NS, copy_fixture, derive, edit, gauss, matrix  # noqa: E402

EVAL = PLUGIN / "skills" / "hep-detector" / "scripts" / "evaluate_design.py"
_spec = importlib.util.spec_from_file_location("evaluate_design_followups", EVAL)
EV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EV)


def derived_req(covered_by=None):
    req = {"id": f"{NS}:REQ-ACC-001", "quantity": "geometric-acceptance", "comparator": ">=", "target": 0.3,
           "unit": "m2 sr", "kind": "derived",
           "denominator": {"rigidity_GV": {"value": 1000.0, "tolerance": 0}, "species": {"value": "proton", "tolerance": 0}}}
    if covered_by:
        req["covered_by"] = f"{NS}:{covered_by}"
    return req


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.b = copy_fixture(Path(self.tmp.name) / "p")

    def tearDown(self):
        self.tmp.cleanup()

    def spec(self, fn):
        edit(self.b, "design-spec.v1.json", lambda s: fn(s["extension"]))


class DerivedCoverage(Base):
    def test_derived_needs_a_driving_cover(self):
        """MAT-04 (d): a derived requirement without covered_by, or covered by another derived one, is an error."""
        self.spec(lambda e: e["requirements"].append(derived_req()))
        self.assertIn("design.derived_uncovered", {x["code"] for x in derive(self.b)["errors"]})
        self.spec(lambda e: e["requirements"].__setitem__(-1, derived_req("REQ-ACC-001")))
        self.assertIn("design.derived_uncovered", {x["code"] for x in derive(self.b)["errors"]})

    def test_disposition_is_proposed_under_the_driving_requirement(self):
        self.spec(lambda e: e["requirements"].append(derived_req("REQ-CC-001")))
        d = derive(self.b)
        self.assertNotIn("design.derived_uncovered", {x["code"] for x in d["errors"]})
        m = matrix(d, "REQ-ACC-001", "cand-A")
        self.assertEqual((m["result"], m["proposed_disposition"], m["disposition_under"]),
                         ("inconclusive", "next-study", f"{NS}:REQ-CC-001"))
        md = EV.render(d, [])
        row = next(x for x in md.splitlines() if "REQ-ACC-001" in x and "cand-A" in x)
        self.assertIn(f"(derived, under {NS}:REQ-CC-001)", row)
        self.assertTrue(row.endswith(f"| next-study (under {NS}:REQ-CC-001) |"), row)


class ConstraintScope(Base):
    def test_hard_constraint_needs_a_scope(self):
        self.spec(lambda e: e["constraints"][0].pop("subsystems"))
        self.assertIn("design.constraint_scope_missing", {x["code"] for x in derive(self.b)["errors"]})

    def test_a_candidate_lacking_a_scoped_subsystem_cannot_pass(self):
        """A partial budget sum cannot pass a hard constraint: pass becomes inconclusive with chain.incomplete and the
        missing subsystem is listed; the scope is shown in the report."""
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(EV.main(["budget", "--candidate", f"{NS}:cand-A", "--quantity", "mass", "--status",
                                      "synthetic", "--artifacts", str(self.b.art)]), 0)
        before = matrix(derive(self.b), "CON-MASS-001", "cand-A")
        self.assertEqual(before["result"], "pass", before)
        self.spec(lambda e: e["constraints"][0].update(subsystems=["DES-TRK-001", "DES-MAG-001", "DES-ECAL-001"]))
        d = derive(self.b)
        m = matrix(d, "CON-MASS-001", "cand-A")
        self.assertEqual((m["result"], m["scope_missing"]), ("inconclusive", ["DES-ECAL-001"]))
        self.assertIn("chain.incomplete", m["codes"])
        self.assertTrue(any("DES-ECAL-001" in x for x in m["missing_evidence"]))
        self.assertIn("scope DES-TRK-001, DES-MAG-001, DES-ECAL-001", EV.render(d, []))


class OffsetValueCheck(Base):
    """ADQ-02 value check (adequacy 1.1.0): |measured - assumed| + z sigma <= the assumed tolerance."""

    def evals(self, value, sigma):
        den = {"rigidity_GV": 1000.0, "species": "proton", "charge_sign": "negative", "curvature_offset_per_GV": 0.0}
        ev = design.Evaluation(self.b.art / "evaluations/X.json", "evaluations/X.json",
                               {"extension": {"figure_of_merit": "charge-confusion-rate", "denominator": den}})
        up = design.Evaluation(self.b.art / "evaluations/OFF.json", "evaluations/OFF.json",
                               {"extension": {"figure_of_merit": "rigidity-scale-offset", "value": value,
                                              "uncertainty": gauss(sigma),
                                              "denominator": {"rigidity_GV": 1000.0, "species": "proton"}}})
        ev.effective = up.effective = "same-candidate"
        ev.upstreams = [up]
        return ev

    def req(self, tol):
        return {"denominator": {"curvature_offset_per_GV": {"value": 0.0, "tolerance": tol}}}

    def test_cases(self):
        proj = design.Project(self.b.art)
        z = design.z_one_sided(0.95)
        cases = [  # (measured, sigma, assumed tolerance, covered)
            (0.0, 1e-5, 0.0, False),  # an exact zero offset can never be covered by a measurement
            (1e-5, 1e-5, 1e-5 + z * 1e-5, True),
            (1e-5, 1e-5, 1e-5 + z * 1e-5 - 1e-7, False),
            (-3e-5, 2e-6, 4e-5, True),
            (-3e-5, 2e-6, 3e-5, False),
        ]
        for value, sigma, tol, covered in cases:
            with self.subTest(value=value, sigma=sigma, tol=tol):
                fails = design.upstream_value_failures(proj, self.evals(value, sigma), self.req(tol))
                self.assertEqual(not fails, covered, fails)
                if fails:
                    self.assertIn("ADQ-02 value check", fails[0])

    def test_no_upstream_is_left_to_the_presence_check(self):
        proj = design.Project(self.b.art)
        ev = self.evals(0.0, 1e-5)
        ev.upstreams = []
        self.assertEqual(design.upstream_value_failures(proj, ev, self.req(0.0)), [])

    def test_adequacy_declares_the_check(self):
        rules = design.Project(self.b.art).fom_rules("charge-confusion-rate")
        self.assertEqual([c["upstream"] for c in rules["upstream_value_checks"]], ["rigidity-scale-offset"])


class Calibration(Base):
    """CHN-16: the candidate's curvature-offset residual through propagate_scale_distortion.py into yield shifts and a
    new measurement-spec version."""

    MODEL = {"variable": "rigidity", "unit": "GV", "edges": [100.0, 200.0, 400.0, 800.0],
             "components": [{"name": "proton", "charge_sign": 1, "spectrum": {"kind": "power-law", "index": 2.7, "norm": 1.0}},
                            {"name": "antiproton", "charge_sign": -1,
                             "spectrum": {"kind": "power-law", "index": 2.7, "norm": 1e-4}}],
             "ratio": {"numerator": "antiproton", "denominator": "proton"}}

    def setUp(self):
        super().setUp()
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"]["subsystems"]["DES-TRK-001"]["parameters"]
             .update(curvature_offset_residual_per_GV={"value": 1e-5, "unit": "1/GV", "source": "alignment goal",
                                                       "status": "proposal"}))
        self.b.write("models/spectrum.json", self.MODEL)
        self.b.write("specs/measurement.json",
                     __import__("json").loads((PLUGIN / "contracts/fixtures/artifacts/valid/measurement_ratio.json")
                                              .read_text(encoding="utf-8")))

    def cal(self, *extra, sid="CAL-A-OFF"):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = EV.main(["calibration", "--candidate", f"{NS}:cand-A", "--residual",
                            "DES-TRK-001.parameters.curvature_offset_residual_per_GV", "--mode", "inverse-offset",
                            "--model", "models/spectrum.json", "--id", sid, *extra, "--artifacts", str(self.b.art)])
        return code, __import__("json").loads(buf.getvalue())

    def test_shifts_and_measurement_spec_version(self):
        code, out = self.cal("--measurement-spec", "specs/measurement.json", "--out-spec", "specs/measurement.v2.json")
        self.assertEqual(code, 0, out)
        res = self.b.read(out["output"])
        comps = res["components"]
        # first order (2 - gamma) q x delta: negative for the positive charge, positive for the negative one
        self.assertTrue(all(v < 0 for v in comps["proton"]["relative_shift_up"]))
        self.assertTrue(all(v > 0 for v in comps["antiproton"]["relative_shift_up"]))
        g, lo, hi = 2.7, 100.0, 200.0  # spectrum-weighted mean rigidity of the first bin
        x_eff = ((lo ** (2 - g) - hi ** (2 - g)) / (g - 2)) / ((lo ** (1 - g) - hi ** (1 - g)) / (g - 1))
        first = (2 - g) * x_eff * 1e-5
        self.assertAlmostEqual(comps["proton"]["relative_shift_up"][0], first, delta=abs(first) * 0.01)
        run = self.b.read(out["run"])["extension"]
        self.assertEqual(run["parameter_digest"], design.Project(self.b.art).parameter_digest(
            f"{NS}:cand-A", ["DES-TRK-001.parameters.curvature_offset_residual_per_GV"]))
        self.assertIn("propagate_scale_distortion.py", run["argv"][1])
        spec = self.b.read(out["measurement_spec"])
        entry = spec["extension"]["systematics"][-1]
        self.assertEqual(entry["effect"], "shape")
        self.assertIn(out["output"], entry["applied_via"])
        self.assertIn(out["output"], {i["ref"] for i in spec["inputs"]})
        from contracts.validate import validate_artifact
        self.assertTrue(validate_artifact(spec).ok)

    def test_digest_follows_the_residual_only(self):
        """INC-02: the step reruns when the residual changes, not when another parameter does."""
        code, out = self.cal()
        self.assertEqual(code, 0, out)
        proj = lambda: design.Project(self.b.art)  # noqa: E731
        ref = ["DES-TRK-001.parameters.curvature_offset_residual_per_GV"]
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"]["subsystems"]["DES-MAG-001"]["parameters"]
             ["field_T"].update(value=0.6))
        self.assertEqual(proj().parameter_digest(f"{NS}:cand-A", ref), out["parameter_digest"])
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"]["subsystems"]["DES-TRK-001"]["parameters"]
             ["curvature_offset_residual_per_GV"].update(value=2e-5))
        self.assertNotEqual(proj().parameter_digest(f"{NS}:cand-A", ref), out["parameter_digest"])

    def test_refusals(self):
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"]["subsystems"]["DES-TRK-001"]["calibration"]
             .update(control_samples=[]))
        code, out = self.cal()
        self.assertEqual(code, 2, out)
        self.assertIn("CHN-16", out["error"])
        self.setUp()
        code, out = self.cal("--measurement-spec", "specs/measurement.json")
        self.assertEqual(code, 2, out)  # a new version needs --out-spec


if __name__ == "__main__":
    unittest.main()
