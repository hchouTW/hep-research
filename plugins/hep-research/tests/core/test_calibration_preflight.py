"""A0 (Part B sections 4.2, 5.1, 14; section 15.3.1 A0) and the D37 rule of the contract checker (approval A7),
phase 1. The ZDC linearity example is the section 8.7 calibration of the A0 smoothing model (registered in the task
card: reachable at 0.5% and 1.0%, unreachable at 3.5% and 5.0%, threshold 2%)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_fixtures as F  # noqa: E402
from core.calibration import contract as cc  # noqa: E402
from core.calibration import data_release as observed  # noqa: E402
from core.calibration import preflight as pf  # noqa: E402

E = np.arange(1.0, 9.0)
KIND = "max_relative_deviation_from_proportionality"
THRESHOLD = {"observables": [f"lin_E{int(e)}" for e in E], "control": list(E), "quantity": KIND, "threshold": 0.02,
             "smoothing_model": {"kind": "polynomial", "degree": 2}}


def linearity_example(dev: float, seed: int = 1) -> dict:
    """The synthetic ZDC linearity example: response E (1 - a E) at 1-8 GeV with the given maximum relative deviation
    from a line through the origin, 0.2% relative scatter per point."""
    a = brentq(lambda a: pf.quantity(E, E * (1 - a * E), KIND, 2) - dev, 0.0, 0.05)
    y = E * (1 - a * E) * (1 + 0.002 * np.random.default_rng(seed).standard_normal(len(E)))
    return {f"lin_E{int(e)}": float(v) for e, v in zip(E, y)}


class A0(unittest.TestCase):
    def test_linearity_example(self):
        """Section 8.7 row 'smoothing model of A0' (calibration 2 of the card) and section 15.3.1 A0."""
        for dev, reachable in ((0.005, True), (0.010, True), (0.035, False), (0.050, False)):
            r = pf.preflight({"thresholds": {"linearity": THRESHOLD}}, linearity_example(dev))
            self.assertEqual(r["a0_summary"], {"unreachable_thresholds": [] if reachable else ["linearity"]}, dev)
            self.assertEqual(r["decisions"][0]["reachable"], reachable)
            if not reachable:
                self.assertEqual(r["findings"][0]["code"], "a0.unreachable")

    def test_summary_holds_names_only(self):
        r = pf.preflight({"thresholds": {"linearity": THRESHOLD}}, linearity_example(0.035))
        self.assertEqual(set(r["a0_summary"]), {"unreachable_thresholds"})
        for d in r["decisions"]:
            self.assertFalse({"_quantity", "_lower"} & set(d))
        c = F.contract()
        c["a0_summary"] = r["a0_summary"]
        self.assertNotIn("contract.a0_values", {f["code"] for f in cc.check(c)["findings"]})

    def test_declarations(self):
        with self.assertRaises(pf.PreflightError):
            pf.check_threshold("x", {k: v for k, v in THRESHOLD.items() if k != "smoothing_model"}, {})
        with self.assertRaises(pf.PreflightError) as cm:
            pf.check_threshold("x", THRESHOLD, {})
        self.assertEqual(cm.exception.code, "a0.no_value")

    def test_read_through_the_provider(self):
        """The A0 read goes through calib_data's provider: a fit read with the draft's series as channel on every raw
        unit; a release the contract does not declare as calibration data is refused."""
        rel = F.release("calibration", ["u1", "u2"], [], {})
        rel["content"] = {"values": linearity_example(0.01)}
        h = observed.release_hash(rel)
        led = observed.Ledger()
        values, seq = led.provide_values(rel, {"series": "zdc-linearity"}, [h])
        self.assertEqual(len(values), 8)
        ev = [e for e in led.state["events"] if e["seq"] == seq]
        self.assertEqual({e["unit"] for e in ev}, {"u1", "u2"})
        self.assertEqual({e["kind"] for e in ev}, {"fit"})
        self.assertEqual(ev[0]["channel"], {"series": "zdc-linearity", "draft": 1})
        with self.assertRaises(observed.DataError):
            led.provide_values(rel, {"series": "zdc-linearity"}, [])


class D37(unittest.TestCase):
    def contract_with_psi(self, sigma=0.01):
        c = F.contract()
        psi = {"name": "beam_spread", "role": "psi", "nodes": ["input"], "uncertainty": "negligible"}
        if sigma is not None:
            psi["constraint"] = {"sigma": sigma}
        c["parameters"].append(psi)
        return c

    def design(self, ratio):
        return {"theta": ["light_yield", "pde"], "sigma_tot": [2.0, 0.01],
                "psi_effect": {"beam_spread": [0.0, ratio * 0.01]}}

    def test_psi_above_the_bound(self):
        r = cc.check(self.contract_with_psi(), design=self.design(0.2))
        self.assertIn("parameters.psi_not_negligible", {f["code"] for f in r["findings"]})

    def test_psi_below_the_bound(self):
        r = cc.check(self.contract_with_psi(), design=self.design(0.05))
        self.assertFalse({"parameters.psi_not_negligible", "parameters.psi_sigma"} & {f["code"] for f in r["findings"]})

    def test_psi_without_uncertainty_or_design(self):
        r = cc.check(self.contract_with_psi(sigma=None), design=self.design(0.05))
        self.assertIn("parameters.psi_sigma", {f["code"] for f in r["findings"]})
        r = cc.check(self.contract_with_psi())                 # never accepted unchecked (review F9)
        self.assertIn("parameters.psi_needs_design", {f["code"] for f in r["findings"]})


if __name__ == "__main__":
    unittest.main()
