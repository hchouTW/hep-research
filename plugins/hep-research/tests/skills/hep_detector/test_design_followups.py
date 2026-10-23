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


if __name__ == "__main__":
    unittest.main()
