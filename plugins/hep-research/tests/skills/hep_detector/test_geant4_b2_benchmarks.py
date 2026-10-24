"""Geant4 program B2.7 and B2.8 (CV-B2): the decision engine's change (toys at the tolerance, power, and the
unchanged rate at no difference; the exact branch), the regression-comparison benchmark on two recorded summaries
(J14's offline replay), the qualification path's conjunction of conditions (each matched by its own scope keys; J14-type
studies keep the CV-A1 rule), and the core-width estimator of multiple-scattering-reference against Lynch and Dahl's
definition (a Gaussian fitted to the central 98 %). All inputs are SYNTHETIC except the recorded J14 summaries."""
import argparse
import json
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "skills" / "hep-detector" / "scripts"))
import geant4_benchmarks as G  # noqa: E402
from contracts.validate import (GEANT4_QUALIFICATION, qualification_missing, qualification_reference,  # noqa: E402
                                qualified_uncertainty)
from core.stats.decisions import ALPHA, change  # noqa: E402
from core.stats.distributions import t_ppf  # noqa: E402

BLOCKS = PLUGIN / "examples" / "geant4-thin-silicon" / "recorded" / "blocks"
H = "a" * 64


class ChangeToys(unittest.TestCase):
    """B2.10: P(changed) at a true difference equal to the tolerance is at most alpha/m + 3 sigma_MC; the power at
    2 tol and the unchanged rate at no difference are reported (asserted against loose floors)."""

    N, NU = 6000, 15

    def rates(self, true, sigma, tol, m, seed):
        rng = random.Random(seed)
        out = {"changed": 0, "unchanged": 0, "unresolved": 0}
        for _ in range(self.N):
            diff = rng.gauss(true, sigma)
            se = sigma * math.sqrt(sum(rng.gauss(0, 1) ** 2 for _ in range(self.NU)) / self.NU)
            out[change(diff, se, self.NU, tol, m)["verdict"]] += 1
        return {k: v / self.N for k, v in out.items()}

    def test_size_at_the_tolerance(self):
        for m in (1, 3):
            with self.subTest(m=m):
                r = self.rates(1.0, 0.4, 1.0, m, 11 + m)
                bound = ALPHA / m
                self.assertLessEqual(r["changed"], bound + 3 * math.sqrt(bound * (1 - bound) / self.N), r)

    def test_power_and_the_unchanged_rate(self):
        power = self.rates(2.0, 0.3, 1.0, 1, 5)["changed"]
        same = self.rates(0.0, 0.3, 1.0, 1, 6)["unchanged"]
        # with sigma = 0.3 tol: changed needs |diff| > tol + t_0.95(15) se, about 1.53 tol at the median se
        self.assertGreater(power, 0.9)
        self.assertGreater(same, 0.8)  # about 0.88: unchanged needs |diff| + t_0.95(15) se <= tol

    def test_the_exact_branch(self):
        self.assertEqual(change(None, None, None, 0.1, 1, interval90=(-0.05, 0.04), interval_m=(-0.06, 0.05))["verdict"],
                         "unchanged")
        self.assertEqual(change(None, None, None, 0.1, 1, interval90=(0.15, 0.3), interval_m=(0.12, 0.35))["verdict"],
                         "changed")
        self.assertEqual(change(None, None, None, 0.1, 1, interval90=(0.05, 0.3), interval_m=(0.02, 0.35))["verdict"],
                         "unresolved")

    def test_the_se_branch_margins(self):
        t = t_ppf(1 - ALPHA, 15)
        self.assertEqual(change(0.0, 0.01, 15, 0.05)["verdict"], "unchanged")
        self.assertEqual(change(0.05 + t * 0.01 + 1e-6, 0.01, 15, 0.05)["verdict"], "changed")
        self.assertEqual(change(0.05, 0.01, 15, 0.05)["verdict"], "unresolved")


class Regression(unittest.TestCase):
    """B2.7: regression-comparison between two independent runs (J14's nominal and control summaries; the control
    has a denser slab), decided by change; a regression result is never validation evidence."""

    def bench(self, a, b, tol):
        return G.run_benchmark({"benchmark": "regression-comparison", "summary_a": f"{a}.json", "summary_b": f"{b}.json",
                                "observable": "mean_deposit_MeV", "tolerance": tol, "version_a": a, "version_b": b},
                               {}, BLOCKS)

    def test_changed_unchanged_and_never_evidence(self):
        changed = self.bench("mpv-nominal", "mpv-control", 0.002)
        self.assertEqual((changed["grade"], changed["verdict"]), ("regression", "changed"), changed)
        self.assertFalse(changed["validation_evidence"])
        same = self.bench("mpv-nominal", "mpv-nominal", 0.05)
        self.assertEqual(same["verdict"], "unchanged", same)
        self.assertEqual(same["decision"]["verdict"], "unchanged")

    def test_regression_does_not_enter_a_qualification(self):
        declared = dict(SCOPE)
        with_reg = qualification_missing(declared, PASSING + [self.bench("mpv-nominal", "mpv-control", 0.002)])
        self.assertEqual(with_reg, [])


SCOPE = {"observable_kind": "tracking-resolution", "particle": "proton", "material": "G4_Si",
         "thickness_x0": [0.0032, 0.0032], "rigidity_GV": [1.0, 1.0], "field_configuration_sha256": H,
         "reco_spec_sha256": H, "geometry_sha256": H, "realization_sha256": H}
PASSING = [
    {"benchmark": "material-definition", "grade": "verification", "verdict": "pass",
     "scope": {"geometry_sha256": H, "realization_sha256": H}, "validation_evidence": False},
    {"benchmark": "field-propagation", "grade": "verification", "verdict": "pass",
     "scope": {"field_configuration_sha256": H}, "validation_evidence": False},
    {"benchmark": "reco-closure", "grade": "verification", "verdict": "pass", "scope": {"reco_spec_sha256": H},
     "validation_evidence": False},
    {"benchmark": "multiple-scattering-reference", "grade": "reference", "verdict": "pass",
     "negative_control": {"status": "caught"}, "validation_evidence": True,
     "scope": {"particle": ["proton"], "material": ["G4_Si"], "thickness_x0": 0.0032, "rigidity_GV": 1.0}}]


class Qualification(unittest.TestCase):
    """B2.8: a tracking-resolution study is upgradable only through all four conditions, each matched by its own
    declared-scope keys; charge confusion needs ms-tail-reference (D0-b); other kinds keep the CV-A1 rule."""

    def test_all_four_conditions_qualify(self):
        self.assertEqual(qualification_missing(SCOPE, PASSING), [])
        self.assertEqual(GEANT4_QUALIFICATION["tracking-resolution"],
                         ("material-definition", "field-propagation", "reco-closure", "multiple-scattering-reference"))

    def test_each_missing_or_failed_condition_is_named(self):
        cases = {
            "missing": ([b for b in PASSING if b["benchmark"] != "reco-closure"], "reco-closure: not present"),
            "failed": ([dict(b, verdict="fail") if b["benchmark"] == "field-propagation" else b for b in PASSING],
                       "field-propagation: verdict 'fail'"),
            "control": ([dict(b, negative_control={"status": "not-caught"}) if b["grade"] == "reference" else b
                         for b in PASSING], "negative control not caught"),
            "hash": ([dict(b, scope={"reco_spec_sha256": "b" * 64}) if b["benchmark"] == "reco-closure" else b
                      for b in PASSING], "reco_spec_sha256"),
            "rigidity": ([dict(b, scope=dict(b["scope"], rigidity_GV=2.0)) if b["grade"] == "reference" else b
                          for b in PASSING], "rigidity_GV"),
        }
        for name, (benches, why) in cases.items():
            with self.subTest(case=name):
                missing = qualification_missing(SCOPE, benches)
                self.assertTrue(any(why in m for m in missing), missing)

    def test_verification_alone_is_never_evidence_and_charge_confusion_needs_the_tail_benchmark(self):
        self.assertTrue(all(not b["validation_evidence"] for b in PASSING if b["grade"] == "verification"))
        missing = qualification_missing(dict(SCOPE, observable_kind="charge-confusion"), PASSING)
        self.assertTrue(any(m.startswith("ms-tail-reference: not present") for m in missing), missing)
        tail = G.bench_ms_tail_reference({}, Path("."))
        self.assertEqual(tail["verdict"], "not-applicable")

    def test_j14_type_kinds_keep_the_cv_a1_rule(self):
        self.assertIsNone(qualification_missing({"observable_kind": "most-probable-value"}, PASSING))


class CoreWidth(unittest.TestCase):
    """multiple-scattering-reference's estimator is Lynch and Dahl's: the sigma of a Gaussian fitted to the central
    98 % (truncated-normal maximum likelihood), not RMS(central 98 %) / 0.8673, which a single-scattering tail inside
    the window inflates (about +11 % in the B2 trial on 0.3 mm of silicon; PLAN and VALIDATION GEANT4-F4)."""

    def test_a_pure_gaussian_and_a_gaussian_with_a_tail(self):
        rng = random.Random(3)
        pure = [rng.gauss(0, 1.0) for _ in range(200000)]
        self.assertAlmostEqual(G._core98(pure), 1.0, delta=0.01)
        tailed = pure + [rng.gauss(0, 1.0) / max(rng.random(), 1e-6) ** 0.5 * 0.6 for _ in range(10000)]
        core = G._core98(tailed)
        cut = int(0.01 * len(tailed))
        s = sorted(tailed)[cut:len(tailed) - cut]
        rms98 = math.sqrt(sum(x * x for x in s) / len(s)) / G.TRUNC_98
        self.assertLess(abs(core - 1.0), abs(rms98 - 1.0))
        self.assertLess(abs(core - 1.0), 0.05)

    def test_lynch_dahl_reference_and_a_density_control(self):
        """A dump of Gaussian exit angles with the Lynch-Dahl width passes; one 10 % wider (the control) fails."""
        p, t = 1000.0, 0.3
        study = {"materials": [{"name": "G4_Si", "z": 14, "a_g_mole": 28.0855, "density_g_cm3": 2.329,
                                "radiation_length_mm": 93.7, "reference_source": "PDG 2024 (test)",
                                "reference_origin": "independent"}]}
        mass = 938.27208943
        theta = G.lynch_dahl_theta0(14, 28.0855, t / 10 * 2.329, p, p / math.hypot(p, mass))
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            spec = {"elements": [{"name": "Slab"}, {"name": "Plane"}]}
            (d / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
            for name, w in (("nominal", 1.0), ("control", 1.1)):
                rng = random.Random(7 if name == "nominal" else 8)
                rows = ["event_id,track_id,plane_id,dx,dy,dz"]
                for e in range(20000):
                    ay, az = rng.gauss(0, theta * w), rng.gauss(0, theta * w)
                    rows.append(f"{e},1,1,1.0,{math.tan(ay)},{math.tan(az)}")
                (d / f"{name}.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
            b = {"element_spec": "spec.json", "crossings": "nominal.csv", "measuring_plane": "Plane",
                 "material": "G4_Si", "particle": "proton", "momentum_MeV": p, "thickness_mm": t,
                 "tolerance": {"reference_accuracy_relative": 0.02, "k_sigma": 3.0}}
            nominal = G.bench_ms_reference(b, study, d)
            control = G.bench_ms_reference(b, study, d, "control.csv")
        self.assertEqual(nominal["verdict"], "pass", nominal)
        self.assertEqual(control["verdict"], "fail", control)
        self.assertAlmostEqual(nominal["scope"]["thickness_x0"], t / 93.7)
        self.assertAlmostEqual(nominal["scope"]["rigidity_GV"], 1.0)


class D0cUncertaintyAndFloor(unittest.TestCase):
    """D0-c as recommended and approved (2026-10-24): label widens an F4 result's uncertainty by the qualifying
    reference's tolerance (qualified_uncertainty), and design.py uses the qualification path's floor (adequacy
    f4_qualified_min_relative_uncertainty: 0.02 for momentum-resolution-core) instead of the F1-bias floor 0.2 only
    for an F4 estimate of that kind whose uncertainty holds the term."""

    REF = PASSING[3]

    def result(self, half=0.0005, value=0.018):
        return {"value": value, "uncertainty": {"minus": half, "plus": half, "coverage": 0.9, "interval": "central",
                                                "distribution": "non-gaussian"}}

    def test_the_qualification_term(self):
        ref = dict(self.REF, tolerance={"total": 0.04})
        self.assertIs(qualification_reference("tracking-resolution", PASSING[:3] + [ref]), ref)
        out = qualified_uncertainty(self.result(), ref)
        self.assertAlmostEqual(out["uncertainty"]["plus"], math.hypot(0.0005, 0.04 * 0.018))
        self.assertEqual(out["uncertainty_components"]["qualification"]["relative_tolerance"], 0.04)
        self.assertIsNone(qualification_reference("tracking-resolution", PASSING[:3] + [
            dict(ref, negative_control={"status": "not-caught"})]))
        self.assertIsNone(qualification_reference("most-probable-value", PASSING[:3] + [ref]))

    def evaluation(self, half, kind="tracking-resolution", tol=0.04, unqualified=False):
        from contracts import design
        ev = design.Evaluation(Path("e.json"), "e.json", {"extension": {
            "figure_of_merit": "momentum-resolution-core", "fidelity": "F4", "value": 0.018, "bound": "estimate",
            "uncertainty": {"minus": half, "plus": half, "coverage": 0.9, "interval": "central",
                            "distribution": "non-gaussian"}}})
        ev.f4_kind, ev.f4_qualification_tolerance, ev.f4_unqualified = kind, tol, unqualified
        return ev

    def test_the_f4_floor(self):
        from contracts import design
        with tempfile.TemporaryDirectory() as d:
            proj = design.Project(Path(d))
            side = design.Side("<=", 0.03)
            with_term = math.hypot(0.0005, 0.04 * 0.018)  # what label writes
            self.assertEqual(design.estimate_state(proj, self.evaluation(with_term), side), (True, "compliant"))
            enveloped = self.evaluation(with_term)  # each end of a model envelope keeps the study's qualification
            enveloped.doc["extension"]["model_envelope"] = [0.0179, 0.0181]
            self.assertEqual(design.estimate_state(proj, enveloped, side), (True, "compliant"))
            # without the term, of another kind, or with no qualifying reference: the default floor 0.2 applies
            for ev in (self.evaluation(0.0005), self.evaluation(with_term, kind="most-probable-value"),
                       self.evaluation(with_term, tol=None)):
                self.assertEqual(design.estimate_state(proj, ev, side)[0], False)
            self.assertEqual(proj.adequacy["adequacy_version"], "1.2.0")
            self.assertEqual(proj.adequacy["f4_qualified_min_relative_uncertainty"]["momentum-resolution-core"]["value"],
                             0.02)


class ReviewFixes(unittest.TestCase):
    """Fixes from the B2 independent review: the qualification hashes come from the study's own inputs; the counted
    reference keeps A1.3's isolation check on the qualification path; material-definition checks the passive slab
    and the list length; a negative control counts only when its run carries the stated injection; a flat window has
    no core width."""

    def test_isolation_is_checked_on_the_qualification_path(self):
        from contracts.validate import Report, _study_upgrade
        study = {"declared_scope": SCOPE, "benchmarks": [dict(b) for b in PASSING],
                 "convergence": {"gate": "pass"}}
        doc = {"artifact_type": "computational-run", "artifact_id": "s-study-validated", "status": ["validated-in-scope"],
               "inputs": [], "extension": {"study": study, "evidence_records": [{"ref": "r.json"}]}}
        rep = Report()
        _study_upgrade(doc, doc["extension"], {"validated-in-scope"}, rep, a1=True, b2=True)
        self.assertIn("geant4.configuration_missing", {f.code for f in rep.errors})

    def test_the_declared_hashes_must_be_the_studys_own(self):
        import check_geant4_study as C
        geo = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        geo.write("{}")
        geo.close()
        study = {"physics": {"element_sim": {"elements": [], "field": {}, "provenance": {
            "realization": {"sha256": H}, "geometry": {"sha256": "c" * 64}}}}}
        args = argparse.Namespace(geometry=geo.name, run_record=[])
        gaps = C.bound_inputs(study, SCOPE, True, None, args)
        Path(geo.name).unlink()
        self.assertTrue(any("derived from geometry" in g for g in gaps), gaps)
        self.assertTrue(any("declared geometry_sha256" in g for g in gaps), gaps)
        self.assertTrue(any("field_configuration_sha256" in g for g in gaps), gaps)
        self.assertTrue(any("reco_spec_sha256 cannot be derived" in g for g in gaps), gaps)
        self.assertEqual(C.bound_inputs(study, SCOPE, False, None, args), [])

    def test_a_flat_window_has_no_core_width(self):
        with self.assertRaises(G.BenchmarkError):
            G._core98([i / 1000 - 0.5 for i in range(1001)] * 3)

    def test_a_control_without_the_injection_in_its_run_is_not_counted(self):
        def record(d, name, density, half):
            hx = float.hex
            rec = {"extension": {"simulation": {"effective_config": {"geometry": {"tree": {
                "materials": [{"name": "Si", "density_g_cm3": hx(density)}],
                "logical_volumes": [{"name": "Slab", "material": "Si",
                                     "solid": {"parameters": {"half_x_mm": hx(half)}}}]}}}}}}
            (d / name).write_text(json.dumps(rec), encoding="utf-8")
            return name
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            b = {"run_record": record(d, "n.json", 2.33, 0.15)}
            good = {"run_record": record(d, "c.json", 2.33 * 1.13, 0.15), "injected_relative": 0.13}
            same = {"run_record": record(d, "s.json", 2.33, 0.15), "injected_relative": 0.13}
            self.assertAlmostEqual(G._areal_density_change(b, good, d), 0.13)
            self.assertAlmostEqual(G._areal_density_change(b, same, d), 0.0)
            self.assertIsNone(G._areal_density_change(b, {"run_record": None}, d))


if __name__ == "__main__":
    unittest.main()
