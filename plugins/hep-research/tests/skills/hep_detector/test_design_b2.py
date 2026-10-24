"""Geant4 program B2.6 (CV-B2): the F4 results file through check_geant4_study.py label --results --geometry and
evaluate_design.py f4 (both paths), the evaluation's own geometry_ref and uncertainty object, and the test reaching a
decisive row of design.py's verdict table (B2.10).

The design project is the SYNTHETIC spectrometer of tests/contracts/design_fixtures.py; the study is J14's MPV study
(examples/geant4-thin-silicon, offline replay), a J14-type study whose upgrade any covering reference allows
(unchanged by CV-B2), given a SYNTHETIC f4-results/1 file for the momentum-resolution-core geometry. The live chain
(geometry -> from-geometry -> element_sim -> reco -> table -> label -> f4 -> report) is gate G-B2, run outside the
test suite (VALIDATION GEANT4-F4)."""
import hashlib
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "tests" / "contracts"))
from design_fixtures import NS, derive, entry  # noqa: E402
from tests.contracts.test_geant4_upgrade import j14_output, tearDownModule  # noqa: E402,F401
from tests.skills.hep_detector.test_design_m2 import Base, ev  # noqa: E402

J14 = PLUGIN / "examples" / "geant4-thin-silicon"
CHECK = PLUGIN / "skills" / "hep-detector" / "scripts" / "check_geant4_study.py"
RUNS = ["nominal", "control", "cut-0.1", "cut-0.03", "em-option0", "em-option3", "pai", "ftfp-bert-emz"]
TAILS = ["alignment", "calibration-non-uniformity", "noise-digitization", "pattern-recognition"]


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class F4Results(Base):
    def setUp(self):
        super().setUp()
        self.j14 = self.b.art / "j14"  # inside the project root: label refs everything relative to it
        self.j14.mkdir()
        for name in ("study-mpv.json", "literature-input.json", "specs", "refdata", "recorded"):
            src = J14 / name
            (shutil.copytree if src.is_dir() else shutil.copyfile)(src, self.j14 / name)
        shutil.copytree(j14_output(), self.j14 / "output")
        self.ok("geometry", "--candidate", f"{NS}:cand-B", "--figure-of-merit", "momentum-resolution-core",
                "--denominator", "rigidity_GV=1000", "--denominator", "species=proton", "--id", "g1")
        self.geom = self.b.art / "studies" / "g1.geometry.json"
        self.reco = None

    def reco_record(self, tails, name):
        """A SYNTHETIC reconstruction record (a copy of J14's nominal run record without its simulation block) that
        the results file names: label binds the results to an evidence record with the same tail sources."""
        d = json.loads((self.j14 / "output" / "artifacts" / "runs" / "mpv-nominal.computational-run.json")
                       .read_text(encoding="utf-8"))
        d["artifact_id"] = f"reco-{name}"
        d["extension"].pop("simulation", None)
        d["extension"]["reconstruction"] = {"program": {"name": "simreco"}, "tail_sources_simulated": list(tails),
                                            "reco_spec": {"schema": "simreco.spec/1", "note": "SYNTHETIC"}}
        path = self.b.art / "studies" / f"reco-{name}.computational-run.json"
        path.write_text(json.dumps(d, indent=1), encoding="utf-8")
        return path

    def results(self, value=0.3, half=0.07, tails=TAILS, geometry=None, name="f4-results.json"):
        """A SYNTHETIC f4-results/1 file (the shape geant4_run.py table --f4-results writes) and its reco record."""
        g = geometry or self.geom
        self.reco = self.reco_record(tails, name.removesuffix(".json"))
        doc = {"schema": "f4-results/1", "tail_sources_simulated": list(tails),
               "reco_record": {"artifact_id": f"reco-{name.removesuffix('.json')}", "sha256": sha(self.reco)},
               "geometry": {"path": str(g), "sha256": sha(g)},
               "results": {"momentum-resolution-core": {
                   "value": value, "statistical_uncertainty": half / 1.753, "dof": 15,
                   "uncertainty": {"minus": half, "plus": half, "coverage": 0.9, "interval": "central",
                                   "distribution": "non-gaussian"},
                   "model_envelope": [value * 0.98, value * 1.01],
                   "estimator": {"name": "gaussian-core", "observable": "core", "truncation_sigma": 2.0},
                   "denominator": {"rigidity_GV": 1000.0, "species": "proton"}}}}
        path = self.b.art / "studies" / name
        path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        return path

    def label_args(self):
        o = self.j14 / "output"
        runs = [a for r in RUNS for a in ("--run-record", str(o / "artifacts" / "runs" / f"mpv-{r}.computational-run.json"))]
        if self.reco is not None:
            runs += ["--run-record", str(self.reco)]
        return ["--spec", str(self.j14 / "study-mpv.json"), "--benchmarks", str(o / "benchmarks-mpv.json"),
                "--convergence", str(o / "convergence-mpv.json"), "--variations", str(o / "variations-mpv.json"),
                "--project-root", str(self.b.art), *runs]

    def label(self, *extra, write="studies/s-i.computational-run.json"):
        p = subprocess.run([sys.executable, "-B", str(CHECK), "label", *self.label_args(), "--upgrade", "--write",
                            str(self.b.art / write), *map(str, extra)], capture_output=True, text=True, timeout=600)
        return p.returncode, json.loads(p.stdout)

    def f4_ii(self, results, study="studies/s-ii.computational-run.json", eid="SIM-ii"):
        flags = ["--label-" + a[2:] if a.startswith("--") else a for a in self.label_args()]
        return ev(self.b, "f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study", study,
                  "--id", eid, *flags, "--label-results", results, "--label-geometry", self.geom)

    def test_label_keeps_results_tail_sources_and_manifest(self):
        res = self.results()
        code, out = self.label("--results", res, "--geometry", self.geom)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["upgrade"], "re-issued as validated-in-scope", out)
        rec = json.loads((self.b.art / "studies/s-i.computational-run.json").read_text(encoding="utf-8"))
        study = rec["extension"]["study"]
        self.assertEqual(study["results"]["momentum-resolution-core"]["value"], 0.3)
        self.assertEqual(study["tail_sources_simulated"], TAILS)
        self.assertEqual(study["geometry"], {"path": "studies/g1.geometry.json", "sha256": sha(self.geom)})
        manifest = {m["path"]: m["sha256"] for m in rec["extension"]["input_manifest"]}
        self.assertEqual(manifest.get("studies/g1.geometry.json"), sha(self.geom))
        self.assertIn(sha(res), manifest.values())

    def test_geometry_sha_mismatch_and_geometry_without_results_exit_2(self):
        other = self.b.art / "studies" / "other.geometry.json"
        other.write_text(self.geom.read_text(encoding="utf-8") + " ", encoding="utf-8")
        code, out = self.label("--results", self.results(), "--geometry", other)
        self.assertEqual(code, 2, out)
        self.assertIn("sha256", out["error"])
        code, out = self.label("--geometry", self.geom)
        self.assertEqual(code, 2, out)
        bad = self.root / "bad.json"
        bad.write_text(json.dumps({"schema": "something-else"}), encoding="utf-8")
        self.assertEqual(self.label("--results", bad)[0], 2)

    def test_both_f4_paths_give_the_same_evaluation(self):
        res = self.results()
        code, out = self.label("--results", res, "--geometry", self.geom)
        self.assertEqual(code, 0, out)
        out_i = self.ok("f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study",
                        "studies/s-i.computational-run.json", "--id", "SIM-i")
        code, out_ii = self.f4_ii(res)
        self.assertEqual(code, 0, out_ii)
        self.assertEqual((out_i["bound"], out_ii["bound"]), ("estimate", "estimate"))
        ei = json.loads((self.b.art / "evaluations/SIM-i.json").read_text(encoding="utf-8"))["extension"]
        eii = json.loads((self.b.art / "evaluations/SIM-ii.json").read_text(encoding="utf-8"))["extension"]
        drop = ("evaluation_id", "study_ref")
        self.assertEqual({k: v for k, v in ei.items() if k not in drop}, {k: v for k, v in eii.items() if k not in drop})
        self.assertEqual(ei["geometry_ref"], "studies/g1.geometry.json")
        self.assertEqual(ei["uncertainty"], {"minus": 0.07, "plus": 0.07, "coverage": 0.9, "interval": "central",
                                             "distribution": "non-gaussian"})

    def test_a_refused_upgrade_lists_the_gaps(self):
        """Without the variation table label refuses; f4 --label-spec is incomplete and lists label's gaps."""
        res = self.results()
        args = [a for a in self.label_args()]
        i = args.index("--variations")
        del args[i:i + 2]
        flags = ["--label-" + a[2:] if a.startswith("--") else a for a in args]
        code, out = ev(self.b, "f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study",
                       "studies/s-r.computational-run.json", "--id", "SIM-r", *flags, "--label-results", res,
                       "--label-geometry", self.geom)
        self.assertEqual((code, out["status"], out["reason"]), (3, "incomplete", "upgrade-refused"), out)
        self.assertIn("no variation table", out["gaps"])

    def test_decisive_row_with_the_d0c_uncertainty(self):
        """B2.10: an upgraded F4 estimate whose uncertainty (statistical (+) replica spread, D0-c option (a)) reaches
        the adequacy minimum (resolution 0.2 relative, as a sigma: the 90 % half-width / 1.645) decides at row 16 (estimate.decides); one with a 1-3 %
        uncertainty stops at row 15 (uncertainty.missing), the live G-B2 outcome."""
        for half, want, name in ((0.12, (16, "estimate.decides"), "wide"), (0.006, (15, "uncertainty.missing"), "narrow")):
            res = self.results(half=half, name=f"{name}.json")
            code, out = self.label("--results", res, "--geometry", self.geom, write=f"studies/{name}.computational-run.json")
            self.assertEqual(code, 0, out)
            self.ok("f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study",
                    f"studies/{name}.computational-run.json", "--id", f"SIM-{name}")
            e = entry(derive(self.b), "REQ-TRK-001", "cand-B", f"SIM-{name}")
            self.assertEqual((e["row"], e["code"]), want, e)

    def test_results_must_come_from_an_evidence_reco_record(self):
        """CV-B2: results whose reco record is not among the run records, or whose tail list differs from it, are a
        gap (the upgrade is refused)."""
        res = self.results()
        reco, self.reco = self.reco, None
        code, out = self.label("--results", res, "--geometry", self.geom)
        self.assertEqual(code, 0, out)
        self.assertTrue(any("not one of the study's run records" in g for g in out["gaps"]), out["gaps"])
        self.reco = reco
        doc = json.loads(res.read_text(encoding="utf-8"))
        doc["tail_sources_simulated"] = TAILS[:1]
        res.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.label("--results", res, "--geometry", self.geom)
        self.assertTrue(any("lists tail sources" in g for g in out["gaps"]), out["gaps"])
        self.assertIn("refused", out["upgrade"])

    def test_without_every_tail_source_the_evaluation_is_optimistic(self):
        res = self.results(tails=TAILS[:2])
        self.assertEqual(self.label("--results", res, "--geometry", self.geom)[0], 0)
        out = self.ok("f4", "--candidate", f"{NS}:cand-B", "--requirement", "REQ-TRK-001", "--study",
                      "studies/s-i.computational-run.json", "--id", "SIM-opt")
        self.assertEqual(out["bound"], "optimistic")


if __name__ == "__main__":
    unittest.main()
