"""The phase-3 Geant4 production and evidence drivers (tests/core/calibration_phase3_g4.py, wave 3 WP-I): the run cards
(seeds and intervals of section 6.6, check-spec and the simulate preflight), the Geant4 task's refusals, tell and the
section 6.6 check on told products, the plane radius of the RICH photons, and the whole path on STAND-IN products
(`--local`, never Geant4) with the merge decisions. Each negative test has a positive control."""
from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import calibration_phase3_g4 as G  # noqa: E402
import calibration_rich_fixture as R  # noqa: E402
import calibration_zdc_fixture as Z  # noqa: E402

from core.calibration import io  # noqa: E402

SCRATCH = {"dir": tempfile.TemporaryDirectory()}        # removed at interpreter exit (TemporaryDirectory's finalizer)


def calo_root(name: str, events: int = 60) -> Path:
    root = Path(SCRATCH["dir"].name) / name
    G.write_cards(root, events, 40, check=False, rich=False)
    return root


def products(root: Path, wrong_birks=None):
    for row in G.load_manifest(root)["runs"]:
        G.standin_calo_products(root / row["campaign"] / "runs" / row["name"], row,
                               wrong_birks if row["name"] == "kB-high" else None)


class CalorimeterCards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = calo_root("cards", events=G.CALO_EVENTS)
        cls.man = G.load_manifest(cls.root)
        cls.runs = {r["name"]: r for r in cls.man["runs"]}

    def card(self, name, doc):
        return json.loads((self.root / G.CALO / "cards" / name / f"{doc}.json").read_text())

    def test_runs_seeds_and_intervals(self):
        self.assertEqual(list(self.runs), ["nominal", "kB-low", "kB-high", "kB-centre", "reference", "LY-low",
                                           "LY-high"])
        paired = {(r["logical_run_seed"], r["first_event"], r["events"]) for n, r in self.runs.items()
                  if n != "reference"}
        self.assertEqual(paired, {(G.calo_seeds()["nominal"][0], 0, G.CALO_EVENTS)})     # common random numbers
        self.assertNotEqual(self.runs["reference"]["logical_run_seed"], self.runs["nominal"]["logical_run_seed"])
        for n, r in self.runs.items():
            run = self.card(n, "run")["run"]
            self.assertEqual((run["logical_run_seed"], run["first_event"], run["events"], run["threads"]),
                             (r["logical_run_seed"], 0, G.CALO_EVENTS, 1))
            rec = io.load(str(self.root / r["state"]))["points"]["0"]          # the ask state, re-pointed
            self.assertEqual((rec["logical_run_seed"], rec["first_event"], rec["events"]),
                             (r["logical_run_seed"], 0, G.CALO_EVENTS))
        mat = {n: self.card(n, "detector")["materials"][Z.MATERIAL] for n in self.runs}
        self.assertEqual(mat["kB-high"]["ionisation"]["birks_mm_per_MeV"], "0.4")
        self.assertEqual(mat["kB-low"]["ionisation"]["birks_mm_per_MeV"], "0.02")
        self.assertEqual(mat["LY-low"]["scintillation"]["yield_per_MeV"], "180.0")
        self.assertEqual(mat["nominal"], mat["reference"])
        self.assertEqual([s["quantity"] for s in self.card("nominal", "request")["scorers"]],
                         ["edep_visible_ly_split", "edep_by_dedx_class", "edep_visible"])

    def test_preflight_refuses_a_card_without_scintillation(self):
        """Negative: the crystal material without its scintillation block -> refused (scintillation-undeclared);
        a surface-tolerance UI command -> refused by check-spec. Positive control: the registered card passes."""
        row = self.runs["nominal"]
        docs = {k: self.card("nominal", k) for k in ("detector", "request", "run")}
        self.assertEqual(G.preflight({**row, "documents": docs}, self.root / G.CALO / "cards" / "nominal"), [])
        with tempfile.TemporaryDirectory() as f:
            bad = copy.deepcopy(docs)
            del bad["detector"]["materials"][Z.MATERIAL]["scintillation"]
            bad["run"]["ui_commands"] = ["/geom/setSurfaceTolerance 1"]
            for k, v in bad.items():
                (Path(f) / f"{k}.json").write_text(json.dumps(v))
            out = " ".join(G.preflight({**row, "documents": bad}, Path(f)))
        self.assertIn("scintillation-undeclared", out)
        self.assertIn("surface-tolerance", out)

    def test_card_hashes_are_deterministic(self):
        again = Path(SCRATCH["dir"].name) / "cards-again"
        G.write_cards(again, G.CALO_EVENTS, 40, check=False, rich=False)
        self.assertEqual([r["sha256"] for r in G.load_manifest(again)["runs"]], [r["sha256"] for r in self.man["runs"]])


@unittest.skipUnless(R.AVAILABLE, R.SKIP_REASON)
class RichCards(unittest.TestCase):
    def test_design_and_samples(self):
        root = Path(SCRATCH["dir"].name) / "rich-cards"
        G.write_cards(root, 50, G.RICH_EVENTS, check=False)
        rows = [r for r in G.load_manifest(root)["runs"] if r["campaign"] == G.RICH]
        self.assertEqual(len(rows), 64)
        for s in R.SAMPLES:
            mine = [r for r in rows if r["sample"] == s["name"]]
            self.assertEqual(len({r["logical_run_seed"] for r in mine}), 1)
            self.assertEqual([r["role"] for r in mine].count("held-back"), 8)
        self.assertEqual(len({r["logical_run_seed"] for r in rows}), 2)
        row = rows[0]
        folder = root / G.RICH / "cards" / row["name"]
        docs = {k: json.loads((folder / f"{k}.json").read_text()) for k in ("detector", "request", "run")}
        self.assertEqual(docs["run"]["physics"]["reference_list"], "FTFP_BERT_EMZ")
        self.assertEqual(G.preflight({**row, "documents": docs}, folder), [])


class Geant4Task(unittest.TestCase):
    def test_refuses_changed_cards_and_another_program(self):
        """Negative: a card edited after registration, a program other than the build -> refused, nothing run;
        positive control: the registered cards and the build's hash -> g4sim_run.py simulate is called."""
        root = calo_root("task")
        prog = root / "g4sim_run"
        prog.write_text("not a program")
        calls = []

        def runner(cmd, **kw):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"status": "ok"}), stderr="")
        r = G.run_geant4_task(0, root, prog, G._sha(prog), runner=runner)
        self.assertEqual((r["status"], len(calls)), ("ok", 1))
        self.assertIn("simulate", calls[0])
        r = G.run_geant4_task(0, root, prog, "0" * 64, runner=runner)
        self.assertEqual((r["status"], len(calls)), ("refused", 1))
        card = root / G.CALO / "cards" / "nominal" / "run.json"
        card.write_text(card.read_text().replace('"threads": 1', '"threads": 2'))
        r = G.run_geant4_task(0, root, prog, G._sha(prog), runner=runner)
        self.assertEqual(r["status"], "refused")
        self.assertIn("run.json", r["problems"][0])
        self.assertEqual(len(G.geant4_tasks()), 7 + 64)


class TellAndIntervals(unittest.TestCase):
    def test_told_products_pass_the_interval_check(self):
        root = calo_root("tell")
        products(root)
        rep = G.tell_all(root, build_hash="standin")
        self.assertEqual((rep["status"], len(rep["told"])), ("passed", 7), rep["refused"])
        self.assertEqual(rep["interval_check"]["status"], "passed")
        b = G.told_batch(root, G.CALO, "kB-high")
        self.assertEqual(b["point"], {"birks": 0.4})

    def test_products_of_another_interval_are_refused(self):
        """Negative: the products of kB-low are told against a state that asked other events -> refused (tell.interval);
        a run without products -> incomplete. Positive control: the other runs are told."""
        root = calo_root("tell-bad")
        products(root)
        st = root / G.CALO / "state" / "kB-low.json"
        s = io.load(str(st))
        s["points"]["0"]["first_event"] = 1000
        io.write_json(str(st), s)
        rep = G.tell_all(root, build_hash="standin")
        self.assertEqual(rep["status"], "failed")
        self.assertIn("not the asked seed and interval", rep["refused"][f"{G.CALO}/kB-low"])
        self.assertEqual(len(rep["told"]), 6)
        root2 = calo_root("tell-missing")
        products(root2)
        (root2 / G.CALO / "runs" / "LY-high" / "summary.json").unlink()
        self.assertEqual(G.tell_all(root2, build_hash="standin")["status"], "incomplete")

    def test_a_reference_on_the_nominal_events_is_caught(self):
        """Negative: the independent `reference` run registered on the nominal block and events -> the section 6.6
        check fails (an overlap between uses). Positive control: as registered it passes (test above)."""
        root = calo_root("tell-overlap")
        man = G.load_manifest(root)
        ref = next(r for r in man["runs"] if r["name"] == "reference")
        ref["logical_run_seed"] = man["runs"][0]["logical_run_seed"]
        io.write_json(str(root / "manifest.json"), man)
        st = root / ref["state"]
        s = io.load(str(st))
        s["points"]["0"]["logical_run_seed"] = ref["logical_run_seed"]
        io.write_json(str(st), s)
        products(root)
        rep = G.tell_all(root, build_hash="standin")
        self.assertEqual(rep["status"], "failed")
        self.assertIn("design.interval_overlap_uses", {f["code"] for f in rep["interval_check"]["findings"]})


class PlaneRadius(unittest.TestCase):
    def detector(self, height="470.0"):
        det = {"params": {"height_mm": height, "foil_mm": "0.75", "aero_mm": "25.0"}, "materials": {
            "aerogel": {"optical": {"rindex": {"energy_eV": ["1", "5"], "value": ["1.05", "1.05"]}}},
            "foil_pmma": {"optical": {"rindex": {"energy_eV": ["1", "5"], "value": ["1.5", "1.5"]}}}}}
        return det

    def test_one_photon_through_the_layers(self):
        """A photon emitted 10 mm above the aerogel's lower face at the Cherenkov angle of beta = 1: its radius is
        10 tan(theta_c) + f tan(theta_f) + H tan(theta_out); it moves with H (calib_eval's ring_radius would not)."""
        tc = math.acos(1 / 1.05)
        so = 1.05 * math.sin(tc)
        def batch(h):
            row = [0, "plane", 3, 0, 0, 3.0, 226.0, 0.0, h + 0.75 + 10.0, so, 0.0, -math.sqrt(1 - so * so), 1]
            return {"first_event": 0, "events": 1, "photons": [row],
                    "primaries": [[0, 1e5, 226.0, 0.0, 530.0, 0, 0, -1]]}
        sf = so / 1.5
        want = 10 * math.tan(tc) + 0.75 * sf / math.sqrt(1 - sf * sf) + 470.0 * math.tan(math.asin(so))
        self.assertAlmostEqual(float(G.plane_radius(batch(470.0), self.detector())[0]), want, places=9)
        self.assertAlmostEqual(float(G.plane_radius(batch(480.0), self.detector("480.0"))[0]) - want,
                               10.0 * math.tan(math.asin(so)), places=9)
        b = batch(470.0)
        b2 = dict(b, photons=[b["photons"][0][:12] + [2]])                       # a secondary's photon is not the ring's
        self.assertTrue(np.isnan(G.plane_radius(b2, self.detector())[0]))

    def test_merge_parts_keeps_photons(self):
        import g4sim_calib_eval as E
        parts = [{"logical_run_seed": 1, "first_event": 0, "events": 1, "cells": [], "primaries": [], "photons": [[0]]},
                 {"logical_run_seed": 1, "first_event": 1, "events": 1, "cells": [], "primaries": [], "photons": [[1]]}]
        self.assertEqual(E.merge_parts(parts)["photons"], [[0], [1]])
        self.assertNotIn("photons", E.merge_parts([dict(parts[0], photons=[])]))


class LocalPath(unittest.TestCase):
    """The whole path on stand-in products at tiny sizes; the decisions are the stand-ins' (not evidence)."""

    @classmethod
    def setUpClass(cls):
        cls.out = G.smoke(Path(SCRATCH["dir"].name) / "local", toys=2, reseed=2)
        cls.m = cls.out["merged"]

    def test_tell_and_decisions(self):
        self.assertEqual(self.out["tell"], "passed")
        self.assertEqual(self.out["interval_findings"], [])
        self.assertTrue(all(v == [] for v in self.out["preflight"].values()), self.out["preflight"])
        p = self.m["passed"]
        self.assertTrue(p["zdc-p0-response"])
        self.assertTrue(p["zdc-birks-rerun"])
        # the stand-in's recorded finding: the nominal-split re-digitization is biased at the upper k_B extreme
        self.assertFalse(p["zdc-p0-birks"])
        self.assertIn("zdc-p0-birks", self.m["failed"])
        if R.AVAILABLE:
            r = self.m["results"]["rich-p3-p6"]
            self.assertTrue(r["p3_passed"])
            self.assertEqual(r["single-beta"]["p3"]["finding"], "p3.not_identifiable")
            self.assertEqual(self.m["results"]["rich-note6/single-beta"]["kinds"],
                             {"basins=0 tie=False no-admitted=True nonidentified-below=False": 2})
            self.assertTrue(p["rich-note6/two-beta"])

    def test_a_mislabelled_birks_run_fails_the_rerun_item(self):
        """Negative: the run told as k_B = 0.02 was made at k_B = 0.22 -> zdc-birks-rerun fails at kB-low. Positive
        control: the same item on the correctly made runs passes (test above), and here at kB-high."""
        out = G.smoke(Path(SCRATCH["dir"].name) / "local-wrong", wrong=("kB-low", 0.22), rich=False)
        rows = {r["run"]: r for r in out["merged"]["results"]["zdc-birks-rerun"]["rows"]}
        self.assertFalse(rows["kB-low"]["passed"])
        self.assertTrue(rows["kB-high"]["passed"])
        self.assertIn("zdc-birks-rerun", out["merged"]["failed"])

    def test_merge_reports_missing_tasks(self):
        tasks = G.evidence_tasks(0, 1)[:3]
        with tempfile.TemporaryDirectory() as f:
            rep = G.merge(Path(f), Path(f) / "m.json", tasks, 0, 2)
        self.assertFalse(rep["complete"])
        self.assertEqual(rep["missing_tasks"], [0, 1, 2])


class Note6Rule(unittest.TestCase):
    def chunk(self, toys, same, reseed=10):
        return {"result": {"toys": toys, "unchanged": same, "reseedings": reseed, "kinds": {}}}

    def test_rule(self):
        """>= 0.99 of >= 1000 toys under 10 reseedings: 10 x 100 toys with 99 unchanged each passes; negative: 98
        each fails; fewer than 1000 toys or another reseeding count is not complete and does not pass."""
        self.assertTrue(G.judge_note6([self.chunk(100, 99)] * 10)["passed"])
        self.assertFalse(G.judge_note6([self.chunk(100, 98)] * 10)["passed"])
        self.assertFalse(G.judge_note6([self.chunk(100, 100)] * 9)["passed"])
        self.assertFalse(G.judge_note6([self.chunk(100, 100, reseed=3)] * 10)["passed"])
        self.assertEqual(len(G.evidence_tasks()), 4 + 2 * G.NOTE6_TOYS // G.NOTE6_PER_TASK)


if __name__ == "__main__":
    unittest.main()
