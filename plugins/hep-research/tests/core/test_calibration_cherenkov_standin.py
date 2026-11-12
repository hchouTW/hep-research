"""The RICH-replica items of Part B (phase 3, WP-F) on the ANALYTIC CHERENKOV STAND-IN (core/calibration/
cherenkov_standin.py), never Geant4: section 15.2 (P3 with a single beta: refractive index and radiator height not
identifiable, with the "multiple beta" hint; with a second momentum or particle, P3 passes), section 8.7 note 6 (the
section 7.4 basin classification on the degeneracy, design stage: a few toys and reseedings), and the Slurm-scale
Geant4 configuration on the S7 case (tests/core/calibration_rich_fixture.py; not run). Items that need Geant4 are
skipped and say so."""
from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration_rich_fixture as R  # noqa: E402

from core.calibration import cherenkov_standin as C  # noqa: E402
from core.calibration import evaluator_problem as EP  # noqa: E402
from core.calibration import identify  # noqa: E402
from core.calibration import likelihood as L  # noqa: E402

ONE = [{"name": "R_p100", "beta": C.beta_of(100.0)}]
MOMENTUM = ONE + [{"name": "R_p2.4", "beta": C.beta_of(2.4)}]
SPECIES = ONE + [{"name": "R_he2.4", "beta": C.beta_of(2.4, 0.931494)}]       # helium-4 at 2.4 GeV per nucleon
CENTRE = {"height_mm": 470.0, "index_scale": 1.0}


def problem(samples, truth=None, seed=None):
    ev = C.CherenkovStandIn(samples)
    p = EP.EvaluatorProblem(ev, C.contract(samples), degeneracy_modes=[C.MODE])
    tc = p.beta(CENTRE)
    if seed is None:                                                        # Asimov at the prior centre (P3)
        p.observed = L.Observations(y_gauss=p.h(tc if truth is None else p.beta(truth)))
    else:
        p.observed = p.simulate(p.beta(truth), np.random.default_rng(seed))
    return p


def nominal_beta(p):
    lk = L.Likelihood(p.layout, p.observed, p.reference(p.beta(CENTRE), None))
    return lk.initial_beta(CENTRE)


class Relation(unittest.TestCase):
    def test_ring_radius(self):
        b = C.beta_of(100.0)
        r = C.ring_radius(1.05, b, 470.0, 25.0)
        tc = math.acos(1 / (1.05 * b))
        self.assertAlmostEqual(r, 12.5 * math.tan(tc) + 470.0 * math.tan(math.asin(1.05 * math.sin(tc))))
        self.assertTrue(math.isnan(C.ring_radius(1.05, 0.95, 470.0, 25.0)))           # below threshold
        self.assertGreater(C.ring_radius(1.05, b, 480.0, 25.0), r)
        out = C.CherenkovStandIn(MOMENTUM).evaluate(CENTRE)
        self.assertEqual(out["flags"], [C.LABEL])


class P3MultipleBeta(unittest.TestCase):
    """Section 15.2 g4sim (RICH replica), on the stand-in."""

    def test_single_beta_is_not_identifiable_with_the_hint(self):
        r = identify.p3(problem(ONE), nominal_beta(problem(ONE)))
        self.assertEqual((r["status"], r["finding"]), ("failed", "p3.not_identifiable"))
        self.assertEqual([h["mode"] for h in r["hints"]], ["refractive index and geometric scale"])
        self.assertIn("multiple beta", r["hints"][0]["signal"])

    def test_a_second_momentum_or_particle_passes(self):
        for samples in (MOMENTUM, SPECIES):
            p = problem(samples)
            r = identify.p3(p, nominal_beta(p))
            self.assertEqual(r["status"], "passed", (samples, r))
            self.assertGreaterEqual(r["lambda_min"], identify.P3_LAMBDA)

    def test_control_two_nearby_momenta_stay_degenerate(self):
        """Control: a second beta too close to the first (3 GeV per nucleon) leaves lambda_min < 0.1 (fails)."""
        p = problem(ONE + [{"name": "R_p3", "beta": C.beta_of(3.0)}])
        self.assertEqual(identify.p3(p, nominal_beta(p))["status"], "failed")

    @unittest.skip("requires Geant4: P3 from the replica's g4sim_run products at the design points of "
                   "calibration_rich_fixture.ask (full optical tracking; Slurm), and a ring-radius observable from "
                   "photons.csv, which the g4sim evaluator does not provide")
    def test_with_geant4(self):
        pass


class Basins(unittest.TestCase):
    """Section 8.7 note 6, phase 3 for the RICH replica, design stage on the stand-in: the classification under
    reseeding of the section 7.4 starts (the calibration itself: >= 10^3 toys and 10 reseedings, not run)."""

    def run_toys(self, samples, n_toys=4, n_reseed=3):
        truth = {"height_mm": 465.0, "index_scale": 1.0005}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return C.reseeding_stability(lambda j: problem(samples, truth, seed=(9, j)), n_toys, n_reseed,
                                         nominal_beta, seed=11)

    def test_single_beta_valley_is_classified_as_no_admitted_basin(self):
        r = self.run_toys(ONE)
        self.assertEqual((r["unchanged"], r["fraction"]), (4, 1.0))
        self.assertEqual(list(r["kinds"]), ["basins=0 tie=False no-admitted=True nonidentified-below=False"])

    def test_two_beta_one_basin_at_the_truth(self):
        r = self.run_toys(MOMENTUM)
        self.assertEqual(r["fraction"], 1.0)
        self.assertEqual(list(r["kinds"]), ["basins=1 tie=False no-admitted=False nonidentified-below=False"])

    @unittest.skip("requires Geant4 and the section 8.7 note 6 calibration (>= 1000 toys x 10 reseedings on the "
                   "replica's surrogate or g4sim products; Slurm)")
    def test_note_6_calibration(self):
        pass


@unittest.skipUnless(R.AVAILABLE, R.SKIP_REASON)
class Geant4Configuration(unittest.TestCase):
    """The Slurm-scale configuration of the real evidence (not run)."""

    def test_cards_per_point_and_sample(self):
        pts = [CENTRE, {"height_mm": 480.0, "index_scale": 1.001}]
        reqs = R.ask(pts, "simcal-p3", "rich", events=2000)
        self.assertEqual(len(reqs), 4)
        by = {(r["sample"], r["point_id"]): r for r in reqs}
        a, b = by[("R_p100", "0")], by[("R_p100", "1")]
        self.assertEqual((a["logical_run_seed"], a["first_event"]), (b["logical_run_seed"], b["first_event"]))
        self.assertNotEqual(a["logical_run_seed"], by[("R_p2.4", "0")]["logical_run_seed"])  # independent samples
        self.assertEqual(b["detector"]["params"]["height_mm"], "480.0")
        n0 = [float(v) for v in R.documents()["detector"]["materials"]["aerogel"]["optical"]["rindex"]["value"]]
        n1 = [float(v) for v in b["detector"]["materials"]["aerogel"]["optical"]["rindex"]["value"]]
        np.testing.assert_allclose(np.array(n1) / np.array(n0), 1.001)                # the whole spectrum
        self.assertEqual(by[("R_p2.4", "0")]["request"]["source"]["energy"]["mono"]["energy_MeV"], "2400.0")
        self.assertEqual(a["run_sha256"], b["run_sha256"])                          # one card per sample
        from contracts import geometry
        for r in (a, b):
            chk = geometry.check_spec(json.dumps(r["detector"]).encode(), claims=R.CLAIMS, folder=R.CASE)
            self.assertEqual(chk["status"], "ok", chk.get("findings"))
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "run.json").write_text(json.dumps(a["run"]))
            out = subprocess.run([sys.executable, "-I", str(ROOT / "adapters" / "geant4" / "assets" / "g4sim_run.py"),
                                  "check-spec", "--run", str(Path(folder) / "run.json")], capture_output=True,
                                 text=True, timeout=120)
            self.assertEqual(json.loads(out.stdout)["status"], "ok", out.stdout + out.stderr)

    def test_production_estimate(self):
        r = R.production()
        self.assertEqual((r["runs"], r["events_per_run"]), (64, 2000))
        self.assertLess(r["cpu_hours"], 5.0)


if __name__ == "__main__":
    unittest.main()
