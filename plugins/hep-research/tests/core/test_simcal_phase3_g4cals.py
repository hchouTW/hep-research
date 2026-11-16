"""The Geant4 version of the section 8.7 row 2004 calibration (P6 part) on the RICH replica (tests/core/
calibration_phase3_g4cals.py, simcal phase 3 WP-L): the task table (every repetition's two members at every point and
sample, exactly once), the seeds, the run cards, the Geant4 task's refusals, the streamed plane radius against
calibration_phase3_g4.plane_radius, one P6 repetition (a biased surrogate caught next to a correct one), the registered
rule, and the whole path on STAND-IN products (never Geant4). Synthetic; no Slurm."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

import calibration_phase3_g4 as G  # noqa: E402
import calibration_phase3_g4cals as W  # noqa: E402
import calibration_rich_fixture as R  # noqa: E402

from core.calibration import design as D  # noqa: E402

SMALL = {"events": 6, "reps": 4, "points": 32, "h_configs": [8, 32], "chunk": {"R_p100": 2, "R_p2.4": 4},
         "p6_reps": 2}
SCRATCH = {"dir": tempfile.TemporaryDirectory()}


def fresh(name: str) -> Path:
    p = Path(SCRATCH["dir"].name) / name
    if p.exists():
        shutil.rmtree(p)
    return p


class TaskTable(unittest.TestCase):
    def test_every_member_of_every_repetition_once(self):
        t = W.tasks()
        g4 = [x for x in t if x["kind"] == "geant4"]
        p6 = [x for x in t if x["kind"] == "p6"]
        cfg = W.CONFIG
        self.assertEqual(len(g4), sum(cfg["reps"] // c for c in cfg["chunk"].values()) * cfg["points"])
        self.assertEqual(len(g4), 15360)
        self.assertEqual(len(p6), 20)
        self.assertEqual([x["task"] for x in t], list(range(len(t))))
        n, full = cfg["events"], 2 * cfg["reps"] * cfg["events"]
        cover: dict = {}
        for x in g4:
            cover.setdefault((x["sample"], x["point"]), []).append(x)
            self.assertEqual(x["first_event"], 2 * x["reps"][0] * n)        # rep r = members 2r and 2r + 1
            self.assertEqual(x["events"], 2 * (x["reps"][1] - x["reps"][0]) * n)
        self.assertEqual(len(cover), 2 * cfg["points"])
        for rows in cover.values():
            rows.sort(key=lambda x: x["first_event"])
            pos = 0
            for x in rows:
                self.assertEqual(x["first_event"], pos)
                pos += x["events"]
            self.assertEqual(pos, full)
        reps = sorted(r for x in p6 for r in range(*x["reps"]))
        self.assertEqual(reps, list(range(cfg["reps"])))
        for x in p6:
            need = {(g["sample"], g["point"], g["chunk"]) for g in g4 if g["reps"][0] < x["reps"][1] and
                    g["reps"][1] > x["reps"][0]}
            self.assertEqual({(g4[a]["sample"], g4[a]["point"], g4[a]["chunk"]) for a in x["after"]}, need)

    def test_seeds_one_block_per_sample_none_registered(self):
        s = W.seeds()
        self.assertEqual(set(s), {"R_p100", "R_p2.4"})
        self.assertEqual(len({v[0] for v in s.values()}), 2)
        self.assertFalse({v[0] for v in s.values()} & set(W.registered_seeds()))
        self.assertEqual(len(W.registered_seeds()), 4)
        self.assertEqual(W.seeds(), s)                                       # deterministic
        for x in W.tasks():
            if x["kind"] == "geant4":
                self.assertEqual(x["logical_run_seed"], s[x["sample"]][0])  # one seed shared by every point

    def test_points_in_the_box_and_nested(self):
        pts = W.points()
        box = W.box()
        self.assertEqual(len(pts), 32)
        for p in pts:
            for k, (lo, hi) in box.items():
                self.assertTrue(lo <= p[k] <= hi)
        self.assertEqual(pts[:8], D.sobol_points(box, 8, W.DESIGN_SEED))      # H = 8: a balanced Sobol set itself

    def test_rule_is_the_registered_one(self):
        self.assertEqual(W.MAX_FALSE_ALARMS, 29)
        self.assertEqual(W.CONFIG["reps"], 2000)
        self.assertEqual(tuple(W.VEMU), (0.0, 1.0))


@unittest.skipUnless(R.AVAILABLE, R.SKIP_REASON)
class Cards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = fresh("cards")
        cls.man = W.write_cards(cls.root, SMALL, check=False)

    def test_deterministic_and_interval_only(self):
        other = fresh("cards2")
        m2 = W.write_cards(other, SMALL, check=False)
        self.assertEqual([r["sha256"] for r in self.man["runs"]], [r["sha256"] for r in m2["runs"]])
        for r in self.man["runs"]:
            card = json.loads((self.root / r["card"]).read_text())["run"]
            self.assertEqual((card["logical_run_seed"], card["first_event"], card["events"], card["threads"]),
                             (r["logical_run_seed"], r["first_event"], r["events"], 1))
        self.assertEqual(self.man["problems"], {})

    def test_documents_at_the_point_and_preflight(self):
        r = self.man["runs"][3]
        folder = self.root / W.CAMPAIGN / "cards" / W._name(r["sample"], r["point"])
        det = json.loads((folder / "detector.json").read_text())
        self.assertAlmostEqual(float(det["params"]["height_mm"]), r["theta"]["height_mm"])
        docs = {k: json.loads((folder / f"{k}.json").read_text()) for k in ("detector", "request", "run")}
        self.assertEqual(G.preflight({"claims": list(R.CLAIMS), "documents": docs}, folder), [])


@unittest.skipUnless(R.AVAILABLE, R.SKIP_REASON)
class Geant4Task(unittest.TestCase):
    def setUp(self):
        self.root = fresh("g4task")
        W.write_cards(self.root, SMALL, check=False)
        self.calls = []
        inner = W.standin_runner(self.root)

        def runner(cmd):
            self.calls.append(cmd)
            return inner(cmd)
        self.runner = runner
        self.prog = Path(W.__file__)
        self.psha = W._sha(self.prog)

    def run_task(self, k=0, **kw):
        return W.run_geant4_task(k, self.root, self.root / "out", runner=kw.pop("runner", self.runner),
                                 program=self.prog, program_sha256=kw.pop("sha", self.psha), **kw)

    def test_positive_control(self):
        rec = self.run_task()
        self.assertEqual(rec["status"], "ok")
        self.assertEqual(rec["reduced"]["events"], 2 * 2 * SMALL["events"])
        work = self.root / W.CAMPAIGN / "runs" / rec["name"]
        self.assertFalse((work / "photons.csv").exists())                     # deleted after reduction
        self.assertIn("photons.csv", rec["products_sha256"])
        self.assertTrue((self.root / rec["reduced"]["path"]).exists())

    def test_refuses_a_changed_card_and_another_program(self):
        card = self.root / W.load_manifest(self.root)["runs"][0]["card"]
        good = card.read_text()
        card.write_text(good.replace('"threads": 1', '"threads": 2'))
        self.assertEqual(self.run_task()["status"], "refused")
        card.write_text(good)
        self.assertEqual(self.run_task(sha="0" * 64)["status"], "refused")
        self.assertEqual(self.calls, [])                                     # nothing ran
        self.assertEqual(self.run_task()["status"], "ok")

    def test_refuses_products_of_another_interval(self):
        inner = W.standin_runner(self.root)

        def shifted(cmd):
            i = cmd.index("--run") + 1
            card = json.loads(Path(cmd[i]).read_text())
            card["run"]["first_event"] += 1
            p = Path(self.root / "shifted.json")
            p.write_text(json.dumps(card))
            return inner(cmd[:i] + [str(p)] + cmd[i + 1:])
        rec = self.run_task(runner=shifted)
        self.assertEqual(rec["status"], "refused")
        self.assertIn("asked events", rec["problems"][0])


@unittest.skipUnless(R.AVAILABLE, R.SKIP_REASON)
class PlaneRadii(unittest.TestCase):
    def test_streamed_equals_the_reference(self):
        root = fresh("radii")
        man = W.write_cards(root, SMALL, check=False)
        row = man["runs"][40]
        folder = root / W.CAMPAIGN / "cards" / W._name(row["sample"], row["point"])
        det = json.loads((folder / "detector.json").read_text())
        work = root / "w"
        G.standin_rich_products(work, {"sample": row["sample"], "logical_run_seed": 7, "first_event": 100,
                                       "events": 9}, det, photons_per_event=3.0)
        rows = G.E.read_csv_rows(work / "photons.csv")
        z = float(det["params"]["height_mm"]) + 0.75 + 10.0
        rows += [[101, "plane", 3, 0, 0, 2.5, 226.0, 0.0, z, 0.1, 0.0, -0.99, 2],     # not the primary's photon
                 [101, "plane", 3, 0, 0, 2.5, 226.0, 0.0, z, 0.1, 0.0, 0.99, 1],      # going up
                 [102, "plane", 3, 0, 0, 2.5, 226.0, 0.0, 5.0, 0.1, 0.0, -0.99, 1]]    # emitted outside the aerogel
        G._write_csv(work / "photons.csv", rows)
        b = {"first_event": 100, "events": 10, "primaries": G.E.read_csv_rows(work / "primaries.csv"),
             "photons": G.E.read_csv_rows(work / "photons.csv")}
        ref = G.plane_radius(b, det)
        got = W.plane_radii(work / "photons.csv", work / "primaries.csv", det, 100, 10, block=7)
        self.assertTrue(np.isnan(ref[-1]))                                      # event 109: no primary, no photons
        np.testing.assert_array_equal(np.isnan(got), np.isnan(ref))
        ok = np.isfinite(ref)
        np.testing.assert_allclose(got[ok], ref[ok], rtol=1e-13)


def _sides(H=32, n=400, seed=5, corr=0.5):
    """Per-event radii of both sides at H points: per side an event effect shared by the points (correlation corr)."""
    g = np.random.default_rng(seed)
    full, sur = [], []
    common = {s["name"]: [g.standard_normal(n), g.standard_normal(n)] for s in W.SAMPLES}
    for h in range(H):
        f, s_ = {}, {}
        for smp in W.SAMPLES:
            nm = smp["name"]
            a, b = common[nm]
            f[nm] = 160 + h * 0.01 + np.sqrt(corr) * a + np.sqrt(1 - corr) * g.standard_normal(n)
            s_[nm] = 160 + h * 0.01 + np.sqrt(corr) * b + np.sqrt(1 - corr) * g.standard_normal(n)
        full.append(f)
        sur.append(s_)
    return full, sur


class OneRepetition(unittest.TestCase):
    def setUp(self):
        self.contract = G.rich_contract(W.SAMPLES)
        self.contract["exposure"] = {s["name"]: 400 for s in W.SAMPLES}

    def test_correct_surrogate_passes_and_a_biased_one_is_caught(self):
        full, sur = _sides()
        ok = W.p6_rep(full, sur, self.contract, 0, [8, 32])
        self.assertFalse(ok["32"]["0.0"]["failed"])
        self.assertFalse(ok["8"]["0.0"]["failed"])
        self.assertIsNone(ok["8"]["0.0"]["chi2_failed"])                         # H < 30: |Delta m| only
        self.assertIsNotNone(ok["32"]["0.0"]["chi2_failed"])
        self.assertGreater(ok["32"]["cross_point_corr_median"], 0.3)
        shift = np.zeros((32, 2))
        shift[3, 1] = 8 * np.sqrt(2.0 / 400)                                     # 8 sigma_Delta at one point
        bad = W.p6_rep(full, sur, self.contract, 0, [8, 32], shift=shift)
        self.assertTrue(bad["32"]["0.0"]["delta_m_failed"])
        self.assertTrue(bad["8"]["0.0"]["failed"])

    def test_nan_events_carry_no_contribution(self):
        full, sur = _sides(H=8)
        full[0]["R_p2.4"][:5] = np.nan
        r = W.p6_rep(full, sur, self.contract, 0, [8])
        self.assertLess(r["8"]["finite_fraction"], 1.0)
        self.assertIn("failed", r["8"]["0.0"])


class Rule(unittest.TestCase):
    def rows(self, fails, reps=2000):
        return [{"r": r, "data_term_over_sigma_delta": 0.2, "finite_fraction": 1.0,
                 **{str(v): {"failed": r < fails and v == 0.0, "delta_m_failed": False, "z_only_failed": False,
                             "max_ratio": 0.5, "chi2": None, "dof": None, "p_value": None, "chi2_failed": None}
                    for v in W.VEMU}} for r in range(reps)]

    def test_29_of_2000_passes_30_fails(self):
        self.assertTrue(W.judge({"8": self.rows(29)}, 2000)["passed"])
        res = W.judge({"8": self.rows(30)}, 2000)
        self.assertFalse(res["passed"])
        self.assertIsNone(res["configurations"]["8|1.0"]["passed"])             # v = 1 reported, not judged

    def test_incomplete_repetitions_fail(self):
        self.assertFalse(W.judge({"8": self.rows(0, reps=1999)}, 2000)["passed"])


@unittest.skipUnless(R.AVAILABLE, R.SKIP_REASON)
class LocalPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = fresh("local")
        with contextlib.redirect_stdout(io.StringIO()), np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                cls.rep = W.smoke_run(cls.out, SMALL)

    def test_tasks_merge_and_interval_check(self):
        m = self.rep["merged"]
        self.assertEqual(self.rep["label"], "smoke")
        self.assertEqual(self.rep["preflight"], [])
        self.assertEqual(m["n_missing"], 0)
        self.assertEqual(m["not_ok_tasks"], [])
        self.assertEqual(m["interval_check"]["status"], "passed")
        self.assertEqual(set(m["result"]["configurations"]), {"8|0.0", "8|1.0", "32|0.0", "32|1.0"})
        self.assertEqual(m["result"]["configurations"]["32|0.0"]["reps"], SMALL["reps"])
        self.assertIn("provisional-thresholds", m["flags"])

    def test_merge_reports_a_missing_task(self):
        d = self.out / "tasks-missing"
        shutil.copytree(self.out / "tasks", d)
        (d / "task_00003.json").unlink()
        m = W.merge(d, self.out / "m.json", self.out / "root", max_false_alarms=0)
        self.assertEqual(m["n_missing"], 1)
        self.assertFalse(m["complete"])
        self.assertFalse(m["passed"])

    def test_overlapping_chunks_fail_the_interval_check(self):
        man = W.load_manifest(self.out / "root")
        recs = [json.loads(f.read_text()) for f in sorted((self.out / "tasks").glob("task_*.json"))]
        g4 = [r for r in recs if r["kind"] == "geant4"]
        self.assertEqual(W.interval_check(man, g4)["status"], "passed")
        bad = copy.deepcopy(g4)
        a = next(i for i, r in enumerate(bad) if r["sample"] == bad[0]["sample"] and r["point"] == bad[0]["point"]
                 and r["chunk"] == 1)
        bad[0]["first_event"] = bad[a]["first_event"]          # chunk 0 run on chunk 1's events: a gap and a double
        chk = W.interval_check(man, bad)
        self.assertEqual(chk["status"], "failed")
        self.assertTrue(chk["coverage_gaps"])
        other = copy.deepcopy(g4)
        other[0]["logical_run_seed"] = man["registered_seeds"][2]               # a p3-g4 seed reused
        chk = W.interval_check(man, other)
        self.assertEqual(chk["status"], "failed")
        self.assertEqual(chk["wrong_seed"], [other[0]["name"]])


class Cli(unittest.TestCase):
    def test_list_prints_the_table(self):
        cp = subprocess.run([sys.executable, "-I", str(HERE / "calibration_phase3_g4cals.py"), "--list", "--root",
                             str(Path(SCRATCH["dir"].name) / "none")], capture_output=True, text=True, timeout=300)
        self.assertEqual(cp.returncode, 0, cp.stderr[-500:])
        t = json.loads(cp.stdout)
        self.assertEqual(len(t), 15380)
        self.assertEqual(t[-1]["kind"], "p6")


if __name__ == "__main__":
    unittest.main()
