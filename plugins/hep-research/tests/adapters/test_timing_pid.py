"""adapters/timing-pid, T10 stage 2: R35's dE/dx retention (row R35-6) and the PID rows (PID-T10a to d) of
t10-timing-stage-plan.md section 6, on hand-made inputs only. Every expected value is computed here from the stage plan's
section 6.1, never by the recipe's modules; tolerances are its section 6.2. Synthetic; no PID or dE/dx quality claim.

Run from the plugin root: python -m unittest tests.adapters.test_timing_pid -v
"""
from __future__ import annotations

import copy
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "timing-pid" / "assets"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ASSETS))

from timing_recipe import dedx, event_time, pid, time_chain, timing_payload  # noqa: E402

C = 29.9792458
TIME_TOL = 1e-12
REL_TOL = 1e-12
SOURCE = "T10 stage 2 hand-made constants; no measurement (R31)"
SPECIES = [{"name": "hypothesis-a", "mass_gev": 0.14}, {"name": "hypothesis-b", "mass_gev": 0.94}]   # fixture masses, not a source
MOMENTUM = {"value_gev": 1.2, "source": "fixture constant", "unconstrained_modes": ["mode.curvature-offset"]}
SIGMA_T = 0.1
WORKING_POINT = {"select": "hypothesis-b", "over": "hypothesis-a", "threshold": 2.0}


def samples(rows):
    return [{"sample_id": i, "layer": layer, "deposit_mev": dep, "path_length_cm": path, "saturated": sat}
            for i, (layer, dep, path, sat) in enumerate(rows)]


ROWS = [(0, 0.30, 0.10, False), (1, 0.36, 0.12, False), (2, 0.90, 0.10, False), (3, 0.28, 0.10, False), (4, 0.45, 0.15, False),
        (5, 0.33, 0.11, False)]
NORM = {"value_mev_per_cm": 2.9, "source": "fixture reference value (a MIP most probable value in a calibration)"}


class DedxRetention(unittest.TestCase):  # R35-6
    def expected(self, rows, fraction):
        values = sorted(((dep / path, i) for i, (_, dep, path, _) in enumerate(rows)))
        drop = math.floor(fraction * len(rows))
        kept = values[:len(rows) - drop]
        mean = sum(v for v, _ in kept) / len(kept)
        return [i for _, i in kept], [i for _, i in values[len(rows) - drop:]], mean

    def test_samples_paths_and_sets_are_kept_and_recomputable(self):
        rec = dedx.measure(samples(ROWS), 0.3, NORM, track_id=5)
        self.assertEqual(rec["track_id"], 5)                                      # fix round 1, N3: tied to its track
        kept, dropped, mean = self.expected(ROWS, 0.3)
        self.assertEqual(rec["format"], "timing-dedx/1")
        self.assertEqual([s["sample_id"] for s in rec["samples"]], list(range(6)))
        for s, (layer, dep, path, sat) in zip(rec["samples"], ROWS):
            self.assertEqual((s["layer"], s["deposit_mev"], s["path_length_cm"], s["saturated"]), (layer, dep, path, sat))
            self.assertLessEqual(abs(s["dedx_mev_per_cm"] - dep / path), REL_TOL * dep / path)
        self.assertEqual((rec["kept"], rec["dropped"], rec["n"], rec["truncation_fraction"]), (sorted(kept), sorted(dropped), 6, 0.3))
        self.assertEqual(len(rec["dropped"]), 1)                     # floor(0.3 * 6) = 1, the highest (sample 2)
        self.assertEqual(rec["dropped"], [2])
        self.assertLessEqual(abs(rec["truncated_mean_mev_per_cm"] - mean), REL_TOL * mean)
        self.assertLessEqual(abs(rec["normalized"] - mean / 2.9), REL_TOL * mean / 2.9)
        self.assertEqual(rec["normalization"], NORM)
        self.assertEqual(rec["flags"], [])
        dedx.check(rec)

    def test_reader_refuses_a_value_without_its_samples(self):
        rec = dedx.measure(samples(ROWS), 0.3, NORM)
        cases = {"no samples": lambda r: r.__setitem__("samples", []),
                 "mean edited": lambda r: r.__setitem__("truncated_mean_mev_per_cm", r["truncated_mean_mev_per_cm"] * 1.01),
                 "kept edited": lambda r: r.__setitem__("kept", r["kept"][1:]),
                 "path edited": lambda r: r["samples"][0].__setitem__("path_length_cm", 0.2),
                 "normalized edited": lambda r: r.__setitem__("normalized", 1.0),
                 "flags dropped": lambda r: r.__setitem__("flags", ["few-samples"]),
                 "malformed": lambda r: r.__setitem__("samples", None)}
        for name, change in cases.items():
            bad = copy.deepcopy(rec)
            change(bad)
            with self.subTest(case=name), self.assertRaises(dedx.InputError):
                dedx.check(bad)

    def test_input_refusals(self):
        for name, rows in {"zero path": [(0, 0.3, 0.0, False)] * 5, "negative deposit": [(0, -0.3, 0.1, False)] * 5}.items():
            with self.subTest(case=name), self.assertRaises(dedx.InputError):
                dedx.measure(samples(rows), 0.3, NORM)
        with self.assertRaises(dedx.InputError):
            dedx.measure(samples(ROWS), 1.0, NORM)                     # nothing would be kept
        with self.assertRaises(dedx.InputError):
            dedx.measure([], 0.3, NORM)

    def test_few_samples_flag(self):  # PID-T10b, few samples
        rec = dedx.measure(samples(ROWS[:3]), 0.3, NORM)
        self.assertEqual(rec["flags"], ["few-samples"])
        self.assertEqual(rec["dropped"], [])                         # floor(0.9) = 0
        dedx.check(rec)

    def test_saturation_flag(self):  # PID-T10b, saturation
        rows = [r if i != 0 else (0, 0.30, 0.10, True) for i, r in enumerate(ROWS)]   # sample 0 saturated, kept
        rec = dedx.measure(samples(rows), 0.3, NORM)
        self.assertEqual(rec["flags"], ["saturated-in-kept"])
        rows = [r if i != 2 else (2, 0.90, 0.10, True) for i, r in enumerate(ROWS)]   # sample 2 saturated, dropped
        self.assertEqual(dedx.measure(samples(rows), 0.3, NORM)["flags"], [])


def payloads(offsets=(1.0, 2.0, 3.0, 4.0)):
    return {step: timing_payload.read(timing_payload.payload_bytes(step, list(values), 4, 1, "nominal", SOURCE))
            for step, values in (("offset", offsets), ("walk", (0.5, 0.6, 0.7, 0.8)), ("propagation", (15.0, 15.0, 16.0, 16.0)))}


def hits():
    rows = [(10, 1, 0, 40.0, 100.0, 30.0, 300.0), (11, 2, 1, 45.0, 64.0, 50.0, 320.0), (12, 3, 2, 50.0, 25.0, 10.0, 350.0),
            (13, 4, 3, 42.0, 400.0, 80.0, 310.0)]
    return [{"hit_id": h, "track_id": t, "counter": c, "raw_time_ns": r, "amplitude": a, "position_cm": d, "path_length_cm": l}
            for h, t, c, r, a, d, l in rows]


WEIGHTS = {10: 0.1, 11: 0.2, 12: 0.3, 13: 0.4}


class Hypotheses(unittest.TestCase):  # PID-T10a
    def setUp(self):
        self.records = time_chain.correct(hits(), payloads())
        self.start = event_time.external(3.25, "fixture start counter")
        self.tof = event_time.tof(self.records[1], self.start)

    def expected(self, tof, path, mass):
        beta = MOMENTUM["value_gev"] / math.sqrt(MOMENTUM["value_gev"] ** 2 + mass ** 2)
        t_pred = path / (C * beta)
        r = tof - t_pred
        return beta, t_pred, r, -r * r / (2 * SIGMA_T ** 2) - math.log(SIGMA_T * math.sqrt(2 * math.pi))

    def test_likelihoods_ratios_support_and_working_point(self):
        rec = pid.hypotheses(self.tof, MOMENTUM, SPECIES, SIGMA_T, WORKING_POINT)
        self.assertEqual((rec["format"], rec["status"]), ("timing-pid/1", "ok"))
        lls = {}
        for h, sp in zip(rec["hypotheses"], SPECIES):
            beta, t_pred, r, ll = self.expected(self.tof["tof_ns"], 320.0, sp["mass_gev"])
            self.assertEqual(h["name"], sp["name"])
            self.assertLessEqual(abs(h["t_pred_ns"] - t_pred), TIME_TOL)
            self.assertLessEqual(abs(h["residual_ns"] - r), TIME_TOL)
            self.assertLessEqual(abs(h["log_likelihood"] - ll), 1e-12)
            lls[sp["name"]] = ll
        llr, = rec["llr"]
        self.assertEqual((llr["a"], llr["b"]), ("hypothesis-a", "hypothesis-b"))
        self.assertLessEqual(abs(llr["value"] - (lls["hypothesis-a"] - lls["hypothesis-b"])), 1e-12)
        self.assertEqual(llr["meaning"], "log-likelihood ratio, not a probability")
        self.assertIsNone(rec["probabilities"])
        self.assertIsNone(rec["priors"])
        t_a = self.expected(0, 320.0, 0.14)[1]
        t_b = self.expected(0, 320.0, 0.94)[1]
        support, = rec["support"]
        self.assertLessEqual(abs(support["separation_sigma"] - abs(t_a - t_b) / SIGMA_T), 1e-9)
        self.assertEqual(support["within_support"], abs(t_a - t_b) / SIGMA_T >= 3.0)
        self.assertEqual(rec["working_point"], WORKING_POINT)
        self.assertEqual(rec["selected"], lls["hypothesis-b"] - lls["hypothesis-a"] >= 2.0)
        self.assertEqual(rec["momentum"], MOMENTUM)                    # the source and its unconstrained mode travel (A37)
        self.assertEqual(rec["event_time"], self.tof["event_time"])
        self.assertEqual(rec["tof_beta"], self.tof["beta"])                       # fix round 1, M5
        self.assertEqual(rec["selected_within_support"], support["within_support"])   # fix round 1, M6: the working-point pair
        pid.check(rec)

    def test_probability_only_with_priors(self):
        priors = {"hypothesis-a": 0.9, "hypothesis-b": 0.1}
        rec = pid.hypotheses(self.tof, MOMENTUM, SPECIES, SIGMA_T, WORKING_POINT, priors=priors)
        lls = [h["log_likelihood"] for h in rec["hypotheses"]]
        top = max(lls)
        weights = [priors[s["name"]] * math.exp(ll - top) for s, ll in zip(SPECIES, lls)]
        for s, w in zip(SPECIES, weights):
            self.assertLessEqual(abs(rec["probabilities"][s["name"]] - w / sum(weights)), 1e-12)
        self.assertLessEqual(abs(sum(rec["probabilities"].values()) - 1.0), 1e-12)
        self.assertEqual(rec["probability_meaning"], "probability given the stated priors")
        pid.check(rec)
        with self.assertRaises(pid.InputError):
            pid.hypotheses(self.tof, MOMENTUM, SPECIES, SIGMA_T, WORKING_POINT, priors={"hypothesis-a": 0.9, "hypothesis-b": 0.3})

    def test_likelihood_ratio_is_never_a_probability(self):  # control llr-as-probability, recipe side of the check
        rec = pid.hypotheses(self.tof, MOMENTUM, SPECIES, SIGMA_T, WORKING_POINT)
        bad = copy.deepcopy(rec)
        bad["probabilities"] = {"hypothesis-a": 1.0, "hypothesis-b": 0.0}
        with self.assertRaises(pid.InputError):
            pid.check(bad)
        bad = copy.deepcopy(rec)
        bad["llr"][0]["meaning"] = "probability"
        with self.assertRaises(pid.InputError):
            pid.check(bad)
        bad = copy.deepcopy(rec)
        bad["hypotheses"][0]["residual_ns"] += 1.0
        with self.assertRaises(pid.InputError):
            pid.check(bad)

    def test_outside_support_above_the_momentum_ceiling(self):  # PID-T10c, overlapping species
        fast = dict(MOMENTUM, value_gev=20.0)
        rec = pid.hypotheses(self.tof, fast, SPECIES, SIGMA_T, WORKING_POINT)
        self.assertFalse(rec["support"][0]["within_support"])

    def test_momentum_and_tof_inputs_are_checked(self):  # fix round 1, M5
        for name, momentum in {"no mode": dict(MOMENTUM, unconstrained_modes=[]), "source not text": dict(MOMENTUM, source=3),
                               "mode not text": dict(MOMENTUM, unconstrained_modes=[None])}.items():
            with self.subTest(case=name), self.assertRaises(pid.InputError):
                pid.hypotheses(self.tof, momentum, SPECIES, SIGMA_T, WORKING_POINT)
        with self.assertRaises(pid.InputError):                                 # a TOF record whose beta does not follow from it
            pid.hypotheses(dict(self.tof, beta=self.tof["beta"] * 1.001), MOMENTUM, SPECIES, SIGMA_T, WORKING_POINT)

    def test_priors_that_weigh_nothing_are_refused(self):  # fix round 1, N4
        sigma = 0.05
        b = self.expected(0, 320.0, 0.94)[1]
        near_b = dict(self.tof, tof_ns=b, beta=320.0 / (C * b))
        with self.assertRaises(pid.InputError):
            pid.hypotheses(near_b, MOMENTUM, SPECIES, sigma, WORKING_POINT, priors={"hypothesis-a": 1.0, "hypothesis-b": 0.0})

    def test_missing_input_is_never_zeros(self):  # PID-T10d
        rec = pid.missing(hit_id=None, track_id=7, reason="no timing hit on this track")
        self.assertEqual(rec["status"], "missing-input")
        self.assertIsNone(rec["hypotheses"])
        self.assertIsNone(rec["llr"])
        self.assertIsNone(rec["tof_ns"])
        pid.check(rec)
        bad = copy.deepcopy(rec)
        bad["tof_ns"] = 0.0
        bad["llr"] = [{"a": "hypothesis-a", "b": "hypothesis-b", "value": 0.0, "meaning": "log-likelihood ratio, not a probability"}]
        with self.assertRaises(pid.InputError):
            pid.check(bad)
        with self.assertRaises(pid.InputError):
            pid.hypotheses(None, MOMENTUM, SPECIES, SIGMA_T, WORKING_POINT)
        for name, change in {"extra number": lambda r: r.__setitem__("log_likelihood", 0.0),           # fix round 1, M4
                             "empty reason": lambda r: r.__setitem__("reason", ""), "no reason": lambda r: r.__setitem__("reason", None)}.items():
            bad = copy.deepcopy(rec)
            change(bad)
            with self.subTest(case=name), self.assertRaises(pid.InputError):
                pid.check(bad)


class Migration(unittest.TestCase):  # PID-T10c
    TRUE = ["hypothesis-a"] * 6 + ["hypothesis-b"] * 4
    SELECTED = ["hypothesis-a"] * 5 + ["hypothesis-b"] + ["hypothesis-b"] * 3 + ["hypothesis-a"]

    def test_efficiency_and_purity_are_different_quantities(self):
        table = pid.migration(self.TRUE, self.SELECTED, ["hypothesis-a", "hypothesis-b"])
        self.assertEqual(table["counts"], {"hypothesis-a": {"hypothesis-a": 5, "hypothesis-b": 1},
                                           "hypothesis-b": {"hypothesis-a": 1, "hypothesis-b": 3}})
        p = table["p_selected_given_true"]
        self.assertLessEqual(abs(p["hypothesis-a"]["hypothesis-b"] - 1 / 6), 1e-15)
        self.assertLessEqual(abs(p["hypothesis-b"]["hypothesis-b"] - 3 / 4), 1e-15)
        for composition in ({"hypothesis-a": 0.5, "hypothesis-b": 0.5}, {"hypothesis-a": 0.99, "hypothesis-b": 0.01}):
            pur = pid.purity(table, composition)
            want = (3 / 4 * composition["hypothesis-b"]) / (3 / 4 * composition["hypothesis-b"] + 1 / 6 * composition["hypothesis-a"])
            with self.subTest(composition=composition):
                self.assertLessEqual(abs(pur["p_true_given_selected"]["hypothesis-b"]["hypothesis-b"] - want), 1e-15)
                self.assertEqual(pur["composition"], composition)
        rare = pid.purity(table, {"hypothesis-a": 0.99, "hypothesis-b": 0.01})["p_true_given_selected"]["hypothesis-b"]["hypothesis-b"]
        self.assertLess(rare, p["hypothesis-b"]["hypothesis-b"])          # a modest efficiency is not a purity
        with self.assertRaises(pid.InputError):
            pid.purity(table, {"hypothesis-a": 0.5, "hypothesis-b": 0.6})
        with self.assertRaises(pid.InputError):
            pid.migration(self.TRUE, self.SELECTED[:-1], ["hypothesis-a", "hypothesis-b"])


class Diagnostics(unittest.TestCase):  # PID-T10b, derived in section 6.1
    DELTA = 0.25

    def tofs(self, records, start_of):
        return {r["hit_id"]: event_time.tof(r, start_of(r, records), records)["tof_ns"] for r in records}

    def test_shared_clock_moves_external_tof_and_cancels_internally(self):
        before = time_chain.correct(hits(), payloads())
        after = time_chain.correct(hits(), payloads(offsets=tuple(o + self.DELTA for o in (1.0, 2.0, 3.0, 4.0))))
        external = lambda r, recs: event_time.external(3.25, "fixture start counter")  # noqa: E731
        common = lambda r, recs: event_time.common_linear(recs, WEIGHTS, 1.0)  # noqa: E731
        loo = lambda r, recs: event_time.leave_one_out(recs, WEIGHTS, 1.0, track_id=r["track_id"])  # noqa: E731
        for name, start_of, want in (("external", external, -self.DELTA), ("common", common, 0.0), ("leave-one-out", loo, 0.0)):
            tb, ta = self.tofs(before, start_of), self.tofs(after, start_of)
            for h in tb:
                with self.subTest(start=name, hit=h):
                    self.assertLessEqual(abs((ta[h] - tb[h]) - want), TIME_TOL)

    def test_wrong_bunch_and_wrong_path(self):
        records = time_chain.correct(hits(), payloads())
        right, late = event_time.external(3.25, "bunch 0"), event_time.external(3.25 + 2.0, "bunch 1 (wrong)")
        for r in records:
            tr, tl = event_time.tof(r, right), event_time.tof(r, late)
            a = pid.hypotheses(tr, MOMENTUM, SPECIES, SIGMA_T, WORKING_POINT)
            b = pid.hypotheses(tl, MOMENTUM, SPECIES, SIGMA_T, WORKING_POINT)
            for ha, hb in zip(a["hypotheses"], b["hypotheses"]):
                with self.subTest(hit=r["hit_id"], case="bunch"):
                    self.assertLessEqual(abs((hb["residual_ns"] - ha["residual_ns"]) + 2.0), TIME_TOL)
            longer = dict(tr, path_length_cm=tr["path_length_cm"] * 1.01, beta=tr["path_length_cm"] * 1.01 / (C * tr["tof_ns"]))
            c = pid.hypotheses(longer, MOMENTUM, SPECIES, SIGMA_T, WORKING_POINT)
            for ha, hc in zip(a["hypotheses"], c["hypotheses"]):
                with self.subTest(hit=r["hit_id"], case="path"):
                    self.assertLessEqual(abs(hc["t_pred_ns"] - 1.01 * ha["t_pred_ns"]), REL_TOL * ha["t_pred_ns"])
                    self.assertLessEqual(abs((hc["residual_ns"] - ha["residual_ns"]) + 0.01 * ha["t_pred_ns"]), TIME_TOL)



class Tool(unittest.TestCase):  # the scoring-side run on seeded synthetic events, and its controls
    def test_cli_pid_and_its_controls(self):
        import json
        import subprocess
        import tempfile
        script = ASSETS / "fixture_tools" / "t10_stage2.py"
        with tempfile.TemporaryDirectory() as scratch:
            base = [sys.executable, "-B", str(script), "pid", "--seed", "5", "--events", "20"]
            p = subprocess.run(base + ["--out", str(Path(scratch) / "ok")], capture_output=True, text=True, timeout=120)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("RESULT t10-pid PASS", p.stdout)
            migration = json.loads((Path(scratch) / "ok" / "t10-pid.json").read_text())["migration"]       # fix round 1, M6
            self.assertEqual(sorted(migration["by_support"]), ["inside", "outside"])
            self.assertEqual(migration["by_support"]["inside"]["tracks"] + migration["by_support"]["outside"]["tracks"], migration["tracks"])
            doc = json.loads((Path(scratch) / "ok" / "t10-pid.json").read_text())
            self.assertEqual((doc["format"], doc["status_label"]), ("t10-pid-record/1", "synthetic"))
            self.assertEqual(sorted(doc["items"]), ["dedx", "hypotheses", "migration", "missing-input", "path", "shared-clock",
                                                    "wrong-bunch"])
            for plant, item in (("llr-as-probability", "hypotheses"), ("clock-not-cancelled", "shared-clock"),
                                ("purity-as-efficiency", "migration"), ("zero-filled-missing", "missing-input"),
                                ("dedx-without-samples", "dedx")):
                with self.subTest(plant=plant):
                    q = subprocess.run(base + ["--out", str(Path(scratch) / plant), "--plant", plant], capture_output=True, text=True,
                                       timeout=120)
                    self.assertEqual(q.returncode, 1, q.stdout + q.stderr)
                    self.assertIn(f"PLANT {plant} item {item} FAIL", q.stdout)
                    self.assertIn(f"RESULT t10-pid FAIL failed items {item} plant {plant}", q.stdout)   # fix round 1, I4: only its own item
            again = subprocess.run(base + ["--out", str(Path(scratch) / "ok")], capture_output=True, text=True, timeout=120)
            self.assertEqual(again.returncode, 2)


if __name__ == "__main__":
    unittest.main()
