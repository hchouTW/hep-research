"""Follow-ups of the g4sim evaluator (phase 3, WP-B, after WP-F): the re-digitization coupled across theta (quantile
coupling of the multinomial: smooth widths, g4sim's marginal law, G1 on widths with sigma_noise), the scale binding of a
spectrum (n(E) -> s n(E)) with its model-identity mask, and the photons.csv observables (photon hits, Cherenkov angle,
ring radius). Synthetic products only, no Geant4."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration_rich_fixture as R  # noqa: E402
import calibration_zdc_fixture as Z  # noqa: E402
import g4sim_calib_eval as E  # noqa: E402

from contracts.schema import validate  # noqa: E402
from core.calibration import design_g4sim as DG  # noqa: E402
from core.calibration import evaluator, model_identity  # noqa: E402
from core.calibration import evaluator_problem as EP  # noqa: E402
from core.calibration import fit as F  # noqa: E402
from core.calibration import likelihood as L  # noqa: E402
from core.simulation import digitize  # noqa: E402

JOB = {"schema": digitize.SCHEMA, "run_seed": 11, "replica": 0, "readout": "bar", "channels": ["a", "b", "c"],
       "stage": {"name": "scintillation", "light_yield_per_MeV": 200.0, "resolution_scale": 0.6},
       "efficiencies": {"0": [0.3, 0.2, 0.1], "1": [0.05, 0.4, 0.2]}, "timing": None,
       "sensor": {"name": "sensor", "gain": 1.0, "excess_noise": 0.1, "dark_rate_per_ns": 1e-3, "gate_ns": 50.0},
       "electronics": {"name": "electronics", "noise_sigma": 0.5, "threshold": 1.0, "lsb": 0.5, "bits": 10}}


def roughness(e, par, grid):
    """The width observable on a fine grid of one parameter: its residual about a straight line, relative."""
    w = np.array([e.evaluate({par: float(g)})["pred"][e.observables.index("pe_std")] for g in grid])
    A = np.vstack([np.ones_like(grid), grid - grid[0]]).T
    r = w - A @ np.linalg.lstsq(A, w, rcond=None)[0]
    return float(r.std() / w.mean())


class Coupling(unittest.TestCase):
    """Re-digitization under common random numbers, coupled so that predictions vary smoothly in theta."""

    def test_marginal_law_is_g4sims(self):
        """At fixed theta, per-channel means, variances and the channel covariance of coupled_digitize agree with
        digitize.digitize (different events, the same law), in the Poisson (mean <= 10) and Gaussian regimes."""
        for scale in (0.02, 0.5):                     # bin means ~ 4 and ~ 100 photons
            rows = [(e, 1, b, scale * 0.8 * (1 + b), scale * 0.2, 5) for e in range(3000) for b in (0, 1)]
            ref = np.array([[r[3] for r in digitize.digitize({**JOB, "run_seed": 11}, rows)[0]]]).reshape(-1, 3)
            cpl = np.array([r[3] for r in E.coupled_digitize({**JOB, "run_seed": 12}, rows)]).reshape(-1, 3)
            n = len(ref)
            for c in range(3):
                se = np.sqrt(ref[:, c].var() / n + cpl[:, c].var() / n)
                self.assertLess(abs(ref[:, c].mean() - cpl[:, c].mean()), 4 * se)
                self.assertLess(abs(np.log(ref[:, c].var() / cpl[:, c].var())), 4 * np.sqrt(4.0 / n))
            cr, cc = np.corrcoef(ref.T)[0, 1], np.corrcoef(cpl.T)[0, 1]
            self.assertLess(abs(cr - cc), 4 * np.sqrt(2.0 / n))

    def test_same_stream_for_every_theta_and_monotone(self):
        rows = [(e, 1, 0, 0.3, 0.05, 5) for e in range(200)]
        a = E.coupled_digitize(JOB, rows)
        self.assertEqual(a, E.coupled_digitize(JOB, rows))                         # one stream, deterministic
        more = E.coupled_digitize({**JOB, "stage": {**JOB["stage"], "light_yield_per_MeV": 201.0}}, rows)
        tot = np.array([[r[3] for r in a], [r[3] for r in more]]).reshape(2, -1, 3).sum(axis=2)
        self.assertTrue(np.all(tot[1] >= tot[0]))                                  # monotone in the yield
        self.assertLessEqual(int(np.abs(tot[1] - tot[0]).max()), 3)                # no redraw of a whole multinomial
        with self.assertRaises(DG.CheckError):
            E.coupled_digitize({**JOB, "timing": {"decay_ns": 2.0, "transit": {"kind": "exponential",
                                                                                "transit_ns": 1.0}}}, rows)

    def test_widths_are_smooth_in_birks_and_light_yield(self):
        bs = {"nominal": Z.batch(61, 0, 600, use="fit")}
        out = {}
        for coupling in ("g4sim", "quantile"):
            p = Z.plan(bs)
            p["evaluator"]["coupling"] = coupling
            e = evaluator.make(p, Z.contract(thetas=("birks", "light_yield")))
            out[coupling] = (roughness(e, "birks", np.linspace(0.15, 0.16, 11)),
                             roughness(e, "light_yield", np.linspace(200.0, 202.0, 11)))
        self.assertLess(out["quantile"][0], 0.8 * out["g4sim"][0], out)
        self.assertLess(out["quantile"][1], 0.5 * out["g4sim"][1], out)
        p = Z.plan(bs)
        p["evaluator"]["coupling"] = "bogus"
        with self.assertRaises(DG.CheckError):
            evaluator.make(p, Z.contract())

    def test_g4sim_coupling_is_digitize(self):
        bs = {"nominal": Z.batch(61, 0, 40, use="fit")}
        p = Z.plan(bs)
        p["evaluator"]["coupling"] = "g4sim"
        e = evaluator.make(p, Z.contract())
        tab = E.batch_tables(bs["nominal"], e.scorers)
        job = DG.job_from_documents(e.documents["pipeline"], e.documents["maps"]["light"], "zdc",
                                    sorted({r[2] for r in tab["split"]}), 61)
        self.assertEqual(e._digitize(e.nominal_theta, tab, bs["nominal"], None, None),
                         digitize.digitize(job, tab["split"])[0])
        self.assertEqual(e.evaluate({})["digitization"], "job")

    def test_fit_on_widths_passes_g1(self):
        """A fit on the mean and the width through EvaluatorProblem, with sigma_noise from five independent batches
        (section 8.1), passes G1 on truth-MC pseudo-data (D6)."""
        bs = {"nominal": Z.batch(61, 0, 300, use="fit"), "truth": Z.batch(62, 0, 1200, use="G8-truth")}
        bs.update({f"s{k}": Z.batch(70 + k, 0, 300, use="sigma-noise", set=k) for k in range(5)})
        c = Z.contract(observables=("pe_mean", "pe_std"), exposure=1000)
        e = evaluator.make(Z.plan(bs, nominal="nominal", observables=("pe_mean", "pe_std")), c)
        pr = EP.EvaluatorProblem(e, c, seeds={"batch": "nominal"})
        events = Z.truth_events(e, {"birks": 0.15}, "truth")
        q = pr.with_data(pr.pseudo_data(events, {"kind": "fixed", "events": 1000}, np.random.default_rng(3)))
        q.sigma_noise = EP.estimate_sigma_noise(q, [0.15], [f"s{k}" for k in range(5)])
        self.assertGreater(q.sigma_noise, 0.0)
        lk = L.Likelihood(q.layout, q.observed, q.reference(np.array([0.21]), None))
        f = F.iterate(q, lk.initial_beta({"birks": 0.21}))
        self.assertEqual(F.g1(f, q)["status"], "passed", f.reason)
        self.assertLess(abs(f.beta[0] - 0.15), 4 * float(f.sigma_tot[0]))
        with self.assertRaises(ValueError):
            EP.estimate_sigma_noise(q, [0.15], ["s0", "s1"])


@unittest.skipUnless(R.AVAILABLE, R.SKIP_REASON)
class ScaleBinding(unittest.TestCase):
    """A theta that rescales a spectrum: n(E) -> s n(E) on materials.aerogel.optical.rindex (RICH precondition (a))."""

    def setUp(self):
        self.docs = R.documents()
        self.plan = {"node_binding": {"parameters": R.BINDINGS}}
        self.ptr = R.BINDINGS["index_scale"]["pointer"]

    def test_apply_and_nominal(self):
        old = DG.pointer_get(self.docs["detector"], self.ptr)
        scaled = DG.apply_theta(self.docs, self.plan, {"index_scale": 1.01})
        self.assertEqual(DG.pointer_get(scaled["detector"], self.ptr), [repr(float(v) * 1.01) for v in old])
        self.assertEqual(DG.pointer_get(self.docs["detector"], self.ptr), old)          # the input is not changed
        self.assertEqual(DG.nominal_value(self.docs, R.BINDINGS["index_scale"]), 1.0)
        self.assertEqual(R.apply(self.docs, {"index_scale": 1.01}), scaled)                 # the fixture uses it
        bad = {"node_binding": {"parameters": {"s": {"document": "detector", "pointer": "/params/height_mm",
                                                     "form": "scale"}}}}
        with self.assertRaises(DG.CheckError):                                            # a scale binds an array
            DG.apply_theta(self.docs, bad, {"s": 1.1})

    def test_contract_binding_and_mask(self):
        c = {"parameters": [{"name": "index_scale", "role": "theta", "bindings": [
            {"document": "detector-spec", "pointer": self.ptr, "form": "scale"}]}]}
        self.assertEqual(DG.contract_bindings(c)["index_scale"]["form"], "scale")
        zc = Z.contract()
        base = len(validate(zc, "calibration_contract.json").errors)
        zc["parameters"][0]["bindings"][0]["form"] = "scale"         # the schema knows the form
        self.assertEqual(len(validate(zc, "calibration_contract.json").errors), base)
        zc["parameters"][0]["bindings"][0]["form"] = "log"
        self.assertGreater(len(validate(zc, "calibration_contract.json").errors), base)
        ml = model_identity.masks(c)["detector-spec"]
        self.assertEqual(ml, [self.ptr + model_identity.SCALE_SUFFIX])
        det = self.docs["detector"]
        a = model_identity.mask(det, ml)
        b = model_identity.mask(DG.apply_theta(self.docs, self.plan, {"index_scale": 1.03})["detector"], ml)
        self.assertEqual(a, b)                                       # the identity does not move with s
        other = copy.deepcopy(det)
        vals = DG.pointer_get(other, self.ptr)
        vals[3] = repr(float(vals[3]) * 1.01)                        # a different shape is a different model
        self.assertNotEqual(model_identity.mask(other, ml), a)
        with self.assertRaises(model_identity.IdentityError):        # without the scale form an array is refused
            model_identity.mask(det, [self.ptr])
        plan = {"node_binding": {"parameters": {"index_scale": {"document": "detector", "pointer": self.ptr}}}}
        with self.assertRaises(DG.CheckError):                       # plan and contract must agree on the form
            DG.resolve(plan, {"parameters": c["parameters"]})


def photon_row(event, volume, direction, scorer="pmt"):
    return [event, scorer, volume, 1.0, 0.5, 3.0, 0, 0, 0, *direction, 1]


class Photons(unittest.TestCase):
    """Observables from photons.csv (RICH precondition (b))."""

    def test_hits_angle_and_radius(self):
        th = 0.25
        rows, prim = [], []
        for e in range(4):
            prim.append([e, 1000.0, 0, 0, 0, 0, 0, 1])
            for k in range(e + 1):                                    # e + 1 photons on a cone of half-angle th
                phi = 2 * np.pi * k / (e + 1)
                rows.append(photon_row(e, 7, [np.sin(th) * np.cos(phi), np.sin(th) * np.sin(phi), np.cos(th)]))
        rows.append(photon_row(1, 7, [1.0, 0.0, 0.0]))                # a reflected photon at 90 degrees
        rows.append(photon_row(2, 8, [0.0, 0.0, 1.0], scorer="other"))
        tab = E.batch_tables({"first_event": 0, "events": 5, "primaries": prim, "photons": rows}, {})
        ev = np.arange(5)
        hits = E.photon_values({"name": "n", "quantity": "photon_hits", "scorer": "pmt"}, tab, ev)
        np.testing.assert_array_equal(hits, [1, 3, 3, 4, 0])
        ang = E.photon_values({"name": "a", "quantity": "cherenkov_angle", "scorer": "pmt", "max_angle_rad": 1.0},
                              tab, ev)
        np.testing.assert_allclose(ang[:4], th, atol=1e-12)
        self.assertTrue(np.isnan(ang[4]))                             # no photon: no angle
        rad = E.photon_values({"name": "r", "quantity": "ring_radius", "scorer": "pmt", "expansion_mm": 400.0,
                               "max_angle_rad": 1.0}, tab, ev)
        np.testing.assert_allclose(rad[:4], 400.0 * np.tan(th), rtol=1e-12)
        wide = E.photon_values({"name": "a", "quantity": "cherenkov_angle", "scorer": "pmt"}, tab, ev)
        self.assertGreater(wide[1], th)                               # without the cut the reflected photon enters
        axis = E.photon_values({"name": "a", "quantity": "cherenkov_angle", "axis": [0, 0, 1], "volumes": [8]},
                               tab, ev)
        self.assertAlmostEqual(axis[2], 0.0)
        with self.assertRaises(DG.CheckError):
            E.photon_values({"name": "r", "quantity": "ring_radius"}, tab, ev)

    def test_through_the_evaluator(self):
        prim = [[e, 1000.0, 0, 0, 0, 0, 0, 1] for e in range(50)]
        r = np.random.default_rng(5)
        rows = []
        for e in range(50):
            for _ in range(int(r.integers(1, 6))):
                phi = r.uniform(0, 2 * np.pi)
                rows.append(photon_row(e, 7, [np.sin(0.2) * np.cos(phi), np.sin(0.2) * np.sin(phi), np.cos(0.2)]))
        batch = {"logical_run_seed": 9, "first_event": 0, "events": 50, "primaries": prim, "photons": rows,
                 "cells": []}
        p = Z.plan({"nominal": batch}, observables=())
        p["evaluator"]["observables"] = [{"name": "hits", "quantity": "photon_hits", "functional": "mean"},
                                         {"name": "radius", "quantity": "ring_radius", "functional": "mean",
                                          "expansion_mm": 100.0}]
        out = evaluator.make(p).evaluate({})
        self.assertAlmostEqual(out["pred"][0], len(rows) / 50)
        self.assertAlmostEqual(out["pred"][1], 100.0 * np.tan(0.2))
        self.assertIsNone(out["digitization"])


if __name__ == "__main__":
    unittest.main()
