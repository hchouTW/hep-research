"""WP2 B-D, G, H: skills/hep-detector/scripts/check_geant4_study.py (spec, run with the convergence gate, variations,
label and the study record).

SYNTHETIC run summaries for the gate and the statistical target; the J14 recorded study (examples/geant4-thin-silicon)
for the study record, copied into a temporary project root and checked with contracts/validate.py --strict and
contracts/dependencies.py, including the phase-2 failure mode: a record relabelled validated-in-scope without the
input status declarations is caught. Standard library only."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "check_geant4_study.py"
ASSETS = PLUGIN / "skills" / "hep-detector" / "assets"
J14 = PLUGIN / "examples" / "geant4-thin-silicon"


def run(*args, cwd=None):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600, cwd=cwd)
    return p.returncode, json.loads(p.stdout)


def contract(tool, *args, cwd=None):
    p = subprocess.run([sys.executable, "-B", str(PLUGIN / "contracts" / tool), *map(str, args)], capture_output=True,
                       text=True, timeout=600, cwd=cwd)
    return p.returncode, json.loads(p.stdout)


class _Tmp(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        shutil.copyfile(ASSETS / "geant4-layered-sim.example.json", self.d / "geant4-layered-sim.example.json")
        self.example = json.loads((ASSETS / "geant4-study-spec.example.json").read_text(encoding="utf-8"))

    def tearDown(self):
        self._t.cleanup()

    def write(self, name, doc):
        p = self.d / name
        p.write_text(json.dumps(doc), encoding="utf-8")
        return p

    def study(self, **over):
        s = copy.deepcopy(self.example)
        s["physics"]["layered_sim_spec"] = "geant4-layered-sim.example.json"
        for k, v in over.items():
            if v is None:
                s.pop(k, None)
            else:
                s[k] = v
        return self.write("study.json", s)

    def summary(self, name, cut, mean, se, events=60000, mpv=0.084, tail=0.03, **settings):
        ls = json.loads((self.d / "geant4-layered-sim.example.json").read_text(encoding="utf-8"))
        st = {"default_cut_mm": cut, "step_limit_mm": 0.0, "em_constructor": ls["physics"].get("em_constructor"),
              "reference_list": ls["physics"].get("reference_list"), "ui_commands": [],
              "particle": ls["gun"]["particle"], "energy_MeV": ls["gun"]["energy_MeV"]}
        st.update(settings)
        doc = {"schema": "geant4-run-summary/1", "run_record": {"artifact_id": f"geant4-run-{name}", "sha256": "0" * 64},
               "csv": {"name": f"{name}.csv", "sha256": "0" * 64}, "events": events, "settings": st,
               "spec_sha256": None, "data_path_problems": [], "datasets_content_match": True,
               "bootstrap": {"resamples": 200, "seed": 1}, "mpv_bin_MeV": 0.002,
               "observables": {"mean_deposit_MeV": {"value": mean, "se": se},
                               "mpv_deposit_MeV": {"value": mpv, "se": 0.0002},
                               "mpv_loss_MeV": {"value": mpv, "se": 0.0005},
                               "tail_fraction": {"value": tail, "se": 0.0004}}}
        return self.write(f"{name}.summary.json", doc)


class Spec(_Tmp):
    def test_example_is_ok_and_reports_rule_coverage(self):
        code, out = run("spec", "--spec", ASSETS / "geant4-study-spec.example.json")
        self.assertEqual(code, 0, out)
        cov = out["rule_coverage"]
        self.assertGreater(cov["rules"], 5)
        self.assertIn("G4R-THIN-CUT-SCAN", cov["applicable_ids"])
        self.assertIn("most-probable-value", cov["kinds_with_a_rule"])

    def test_missing_observable_target_or_scope_exits_1(self):
        for drop in ("observable", "statistical_target"):
            with self.subTest(drop=drop):
                code, out = run("spec", "--spec", self.study(**{drop: None}))
                self.assertEqual(code, 1, out)
                self.assertIn(drop, out["blocking_missing"])
        vp = copy.deepcopy(self.example["validation_plan"])
        vp.pop("scope")
        code, out = run("spec", "--spec", self.study(validation_plan=vp))
        self.assertEqual(code, 1, out)
        self.assertIn("validation_plan.scope", out["blocking_missing"])

    def test_a_firing_rule_names_its_source(self):
        obs = dict(self.example["observable"], kind="neutron-flux", domain="hadronic")
        particle = {"name": "neutron", "energy_MeV": 1.0}
        code, out = run("spec", "--spec", self.study(observable=obs, particle=particle))
        self.assertEqual(code, 1, out)
        f = next(f for f in out["findings"] if f["rule"] == "G4R-HP-NEUTRON")
        self.assertEqual(f["severity"], "error")
        self.assertIn("G4HadronPhysicsQGSP_BIC_HP.cc", f["source"]["document"])

    def test_shower_and_citation_rules(self):
        obs = dict(self.example["observable"], kind="leakage")
        obs.pop("leakage_faces", None)
        down = {"kind": "paper", "handoff": ["hep-authoring"]}
        code, out = run("spec", "--spec", self.study(observable=obs, downstream_use=down, citations=None))
        fired = {f["rule"] for f in out["findings"]}
        self.assertIn("G4R-SHOWER", fired)
        self.assertIn("G4R-CITATION", fired)
        obs["leakage_faces"] = ["rear"]
        code, out = run("spec", "--spec", self.study(observable=obs, downstream_use=down,
                                                     citations={"literature_record": "lit.json"}))
        fired = {f["rule"] for f in out["findings"]}
        self.assertNotIn("G4R-SHOWER", fired)
        self.assertNotIn("G4R-CITATION", fired)

    def test_a_rule_without_a_source_is_refused(self):
        rules = json.loads((ASSETS / "geant4-physics-rules.json").read_text(encoding="utf-8"))
        rules["rules"][0].pop("source")
        code, out = run("spec", "--spec", ASSETS / "geant4-study-spec.example.json", "--rules",
                        self.write("rules.json", rules))
        self.assertEqual(code, 2, out)
        self.assertIn("without a source", out["error"])

    def test_every_shipped_rule_has_a_versioned_source(self):
        for r in json.loads((ASSETS / "geant4-physics-rules.json").read_text(encoding="utf-8"))["rules"]:
            with self.subTest(rule=r["id"]):
                self.assertTrue(r["source"]["document"] and r["source"]["section"])
                self.assertIn(r["source"]["version"], ("11.4.3", "RPP 2024"))


class RunGate(_Tmp):
    def test_converged_scan_passes(self):
        sp = self.study()
        args = ["--summary", f"nominal={self.summary('n', 0.01, 0.1050, 0.0001)}",
                "--summary", f"scan={self.summary('a', 0.03, 0.1052, 0.0001)}",
                "--summary", f"scan={self.summary('b', 0.1, 0.1056, 0.0001)}"]
        code, out = run("run", "--spec", sp, *args)
        self.assertEqual(out["convergence"]["gate"], "pass", out)

    def test_too_coarse_cut_fails_the_gate(self):
        sp = self.study()
        args = ["--summary", f"nominal={self.summary('n', 0.01, 0.1050, 0.0001)}",
                "--summary", f"scan={self.summary('a', 0.03, 0.1090, 0.0001)}",
                "--summary", f"scan={self.summary('b', 0.1, 0.1120, 0.0001)}"]
        code, out = run("run", "--spec", sp, *args)
        self.assertEqual(code, 1, out)
        self.assertEqual(out["convergence"]["gate"], "fail")
        row = next(o for o in out["convergence"]["parameters"][0]["observables"] if o["observable"] == "mean_deposit_MeV")
        self.assertEqual(row["verdict"], "fail")

    def test_an_unresolved_difference_does_not_pass(self):
        sp = self.study()
        args = ["--summary", f"nominal={self.summary('n', 0.01, 0.1050, 0.003)}",
                "--summary", f"scan={self.summary('a', 0.03, 0.1052, 0.003)}",
                "--summary", f"scan={self.summary('b', 0.1, 0.1056, 0.003)}"]
        code, out = run("run", "--spec", sp, *args)
        row = next(o for o in out["convergence"]["parameters"][0]["observables"] if o["observable"] == "mean_deposit_MeV")
        self.assertEqual(row["verdict"], "unresolved")
        self.assertEqual(out["convergence"]["gate"], "incomplete")  # A1.8: unresolved is incomplete, not fail

    def test_a_missing_declared_value_makes_the_gate_incomplete(self):
        """D11 (A1.16): the finest declared cut has no summary; the gate does not pass on the coarser two."""
        sp = self.study()
        args = ["--summary", f"scan={self.summary('a', 0.03, 0.1052, 0.0001)}",
                "--summary", f"scan={self.summary('b', 0.1, 0.1056, 0.0001)}"]
        code, out = run("run", "--spec", sp, *args)
        self.assertEqual((code, out["convergence"]["gate"]), (3, "incomplete"), out)
        p = out["convergence"]["parameters"][0]
        self.assertEqual((p["reason"], p["missing_values"]), ("missing-scan-value", [0.01]))

    def test_too_few_events_reports_the_n_needed(self):
        sp = self.study()
        nominal = self.summary("n", 0.01, 0.105, 0.0003, events=1000)
        doc = json.loads(nominal.read_text(encoding="utf-8"))
        doc["observables"]["mpv_loss_MeV"]["se"] = 0.003  # 3.6 % against a 1 % target
        nominal.write_text(json.dumps(doc))
        code, out = run("run", "--spec", sp, "--summary", f"nominal={nominal}")
        self.assertNotEqual(code, 0, out)
        st = out["statistical_target"]
        self.assertEqual(st["verdict"], "target-missed")  # A1.9: incomplete, never topped up
        self.assertGreater(st["events_needed"], 10000)
        self.assertIn("not topped up", st["estimate"])

    def test_a_record_that_disagrees_with_the_spec_fails(self):
        sp = self.study()
        bad = self.summary("n", 0.01, 0.105, 0.0003, particle="proton")
        doc = json.loads(bad.read_text(encoding="utf-8"))
        doc["data_path_problems"] = ["G4LEDATA resolved to another copy"]
        doc["datasets_content_match"] = False
        bad.write_text(json.dumps(doc))
        code, out = run("run", "--spec", sp, "--summary", f"nominal={bad}")
        self.assertEqual(code, 1, out)
        text = " ".join(out["record_problems"])
        for word in ("gun", "data paths", "content hash", "spec hash"):
            self.assertIn(word, text)


class Variations(_Tmp):
    def test_same_model_is_excluded_and_a_new_model_listed(self):
        sp = self.study()
        nominal = self.summary("n", 0.01, 0.105, 0.0003)
        same = self.summary("same", 0.01, 0.105, 0.0003, em_constructor=None, reference_list="FTFP_BERT_EMZ")
        other = self.summary("opt0", 0.01, 0.106, 0.0003, em_constructor="G4EmStandardPhysics", mpv=0.085)
        code, out = run("variations", "--spec", sp, "--nominal", nominal, "--variation", f"same={same}",
                        "--variation", f"opt0={other}")
        listed = {v["variation"]: v["listed"] for v in out["variations"]}
        self.assertEqual(listed, {"same": False, "opt0": True})
        self.assertIn("not a standard deviation", out["note"])

    def test_hadronic_model_assignment(self):
        study = copy.deepcopy(self.example)
        study["observable"]["domain"] = "hadronic"
        study["physics"]["layered_sim_spec"] = "geant4-layered-sim.example.json"
        sp = self.write("study.json", study)
        for particle, energy, expect in (("pi+", 10000.0, False), ("proton", 1000.0, True)):
            with self.subTest(particle=particle):
                a = self.summary("a", 0.01, 0.1, 0.001, reference_list="QGSP_BIC", em_constructor=None,
                                 particle=particle, energy_MeV=energy)
                b = self.summary("b", 0.01, 0.1, 0.001, reference_list="FTFP_BERT", em_constructor=None,
                                 particle=particle, energy_MeV=energy)
                code, out = run("variations", "--spec", sp, "--nominal", a, "--variation", f"ftfp={b}")
                self.assertEqual(out["variations"][0]["listed"], expect, out["variations"][0])


class StudyRecord(unittest.TestCase):
    """The J14 study records, rebuilt in a temporary project root."""

    @classmethod
    def setUpClass(cls):
        cls._t = tempfile.TemporaryDirectory()
        cls.root = Path(cls._t.name) / "project"
        shutil.copytree(J14 / "output", cls.root / "output")
        for name in ("study-sp.json", "specs"):
            src = J14 / name
            (shutil.copytree if src.is_dir() else shutil.copyfile)(src, cls.root / name)
        cls.rec = cls.root / "output" / "artifacts" / "sp.study.computational-run.json"

    @classmethod
    def tearDownClass(cls):
        cls._t.cleanup()

    def test_record_validates_strictly_and_has_no_dependency_finding(self):
        code, out = contract("validate.py", self.rec, "--strict")
        self.assertEqual(code, 0, out)
        code, out = contract("dependencies.py", self.rec, "--root", self.root)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["dependency_consistency_ok"])
        doc = json.loads(self.rec.read_text(encoding="utf-8"))
        self.assertEqual(doc["status"], ["unvalidated"])
        self.assertTrue(all(i["status"] == ["unvalidated"] and len(i["sha256"]) == 64 for i in doc["inputs"]))
        study = doc["extension"]["study"]
        for k in ("benchmarks", "convergence", "variations", "declared_scope", "gaps", "phase2_upgrade_eligible_scopes"):
            self.assertIn(k, study)
        self.assertEqual(study["highest_usable_label"], "unvalidated")

    def test_relabelled_validated_in_scope_without_input_statuses_is_caught(self):
        doc = json.loads(self.rec.read_text(encoding="utf-8"))
        doc["status"] = ["validated-in-scope"]
        for i in doc["inputs"]:
            i.pop("status")
        bad = self.root / "output" / "artifacts" / "relabelled.computational-run.json"
        bad.write_text(json.dumps(doc), encoding="utf-8")
        code, out = contract("dependencies.py", bad, "--root", self.root)
        self.assertNotEqual(code, 0, out)
        codes = {f["code"] for f in out["findings"]}
        self.assertIn("dependency.status_undeclared", codes)
        bad.unlink()

    def test_a_written_result_without_a_literature_record_is_a_gap(self):
        spec = json.loads((self.root / "study-sp.json").read_text(encoding="utf-8"))
        spec["citations"] = {"literature_record": "missing.json"}
        (self.root / "nolit.json").write_text(json.dumps(spec), encoding="utf-8")
        o = "output"
        code, out = run("label", "--spec", "nolit.json", "--benchmarks", f"{o}/benchmarks-sp.json", "--convergence",
                        f"{o}/convergence-sp.json", "--variations", f"{o}/variations-sp.json", "--project-root", ".",
                        cwd=self.root)
        self.assertTrue(any("literature record" in g for g in out["gaps"]), out["gaps"])

    def test_label_propagates_user_supplied_from_a_reference_record(self):
        lit = self.root / "output" / "artifacts" / "geant4.literature-record.json"
        o = "output"
        code, out = run("label", "--spec", "study-sp.json", "--benchmarks", f"{o}/benchmarks-sp.json",
                        "--convergence", f"{o}/convergence-sp.json", "--variations", f"{o}/variations-sp.json",
                        "--run-record", f"{o}/artifacts/runs/sp-nominal.computational-run.json",
                        "--reference-record", f"{o}/artifacts/geant4.literature-record.json" if lit.is_file() else "",
                        "--project-root", ".", cwd=self.root)
        self.assertEqual(code, 0, out)
        self.assertEqual(out["labels"], ["unvalidated", "user-supplied"])
        self.assertEqual(out["highest_usable_label"], "unvalidated")


class EffectiveConfigInputs(unittest.TestCase):
    """Geant4 program A2.4/A2.6: the hadronic model assignment reads the probe first (the declared table otherwise;
    both present and different is an error), and the thin-layer rule reads the minimum thickness from the effective
    config's geometry tree when one is given."""

    @staticmethod
    def config(models, recorded=True):
        h = float.hex
        return {"recorded": recorded, "sections": {"geant4": {"hadronic": [
            {"particle": "proton", "process": "protonInelastic", "via": None,
             "models": [{"name": n, "min_MeV": h(lo), "max_MeV": h(hi)} for n, lo, hi in models]}]}}}

    def setUp(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import check_geant4_study as C
        self.C = C
        self.ftfp_bert = [("FTFP", 3000.0, 1e8), ("BertiniCascade", 0.0, 6000.0)]

    def test_probe_first_with_the_declared_table_as_fallback(self):
        settings = {"reference_list": "FTFP_BERT", "particle": "proton", "energy_MeV": 4000.0, "ui_commands": []}
        ma = self.C.model_assignment(settings, "hadronic", self.config(self.ftfp_bert))
        self.assertEqual((ma["model"], ma["source"]), ("BERT/FTFP", "probe"))
        self.assertNotIn("source", self.C.model_assignment(settings, "hadronic"))  # declared
        self.assertNotIn("source", self.C.model_assignment(settings, "hadronic",
                                                           self.config(self.ftfp_bert, recorded=False)))
        for e, want in ((1000.0, "BERT"), (3000.0, "BERT"), (4500.0, "BERT/FTFP"), (6000.0, "BERT/FTFP"),
                        (10000.0, "FTFP")):
            self.assertEqual(self.C.probe_hadronic_model(self.config(self.ftfp_bert), "proton", e), want)
        # the edge convention agrees with the declared table at every FTFP_BERT boundary (review finding)
        for e in (3000.0, 6000.0, 12000.0, 25000.0):
            s = {**settings, "energy_MeV": e}
            self.assertEqual(self.C.model_assignment(s, "hadronic", self.config(self.ftfp_bert))["model"],
                             self.C.model_assignment(s, "hadronic")["model"])

    def test_probe_and_declaration_disagreeing_is_an_error(self):
        settings = {"reference_list": "FTFP_BERT", "particle": "proton", "energy_MeV": 1000.0, "ui_commands": []}
        with self.assertRaises(self.C.StudyError):
            self.C.model_assignment(settings, "hadronic", self.config([("Binary Cascade", 0.0, 6000.0)]))

    def test_em_constructor_follows_the_physics_list_factory(self):
        """Review finding (A8): the suffix alone does not decide the EM constructor (Geant4 11.4.3 lists)."""
        em = self.C.em_constructor_of
        self.assertEqual(em("FTFP_BERT"), "G4EmStandardPhysics")
        self.assertEqual(em("FTFP_BERT_EMZ"), "G4EmStandardPhysics_option4")
        self.assertEqual(em("QGSP_BIC_HP"), "G4EmStandardPhysics_option4")  # registers option 4 itself
        self.assertEqual(em("QGSP_BIC_HP_EMY"), "G4EmStandardPhysics_option3")
        self.assertEqual(em("FTFP_BERT_TRV"), "G4EmStandardPhysicsGS")
        self.assertEqual(em("FTFP_BERT_EM0"), "G4EmStandardPhysics")
        self.assertEqual(em("LBE_EMZ"), em("LBE"))  # the factory ignores an EM suffix on LBE
        ma = lambda ref: self.C.model_assignment({"reference_list": ref, "particle": "e-", "energy_MeV": 100.0,
                                                  "ui_commands": []}, "em")["em_constructor"]
        self.assertEqual(ma("FTFP_BERT_EMZ"), ma("QGSP_BIC_HP"))  # same EM model: no EM variation

    def test_hadronic_table_matches_exact_list_names(self):
        """Review finding (A8): FTFP_BERT_ATL moves the transition, QGSP_BIC_AllHP uses ParticleHP: not in the table."""
        s = {"particle": "proton", "energy_MeV": 8000.0, "ui_commands": []}
        self.assertTrue(self.C.model_assignment({**s, "reference_list": "FTFP_BERT_EMZ"}, "hadronic")["known"])
        for ref in ("FTFP_BERT_ATL", "QGSP_BIC_AllHP", "QGSP_BIC_HP"):
            self.assertFalse(self.C.model_assignment({**s, "reference_list": ref}, "hadronic")["known"], ref)

    def test_datasets_rule_applies_to_a_reference_list(self):
        """Review finding (A8): G4R-DATASETS tested physics.layered_sim.reference_list, a field that does not exist."""
        rule = next(r for r in self.C.load_rules(self.C.RULES) if r["id"] == "G4R-DATASETS")
        study = {"physics": {"layered_sim": {"physics": {"reference_list": "FTFP_BERT"}}},
                 "reproducibility": {"data_paths_recorded": False}}
        self.assertTrue(self.C.holds(rule["condition"], study))
        self.assertFalse(self.C.holds(rule["requires"], study))

    def test_thin_layer_rule_reads_the_geometry_tree(self):
        h = float.hex
        ec = {"recorded": True, "geometry": {"tree": {
            "logical_volumes": [{"id": 0, "name": "World", "solid": {"type": "G4Box", "parameters": {
                "half_x_mm": h(1.0), "half_y_mm": h(1.0), "half_z_mm": h(1.0)}}, "material": "V"},
                {"id": 1, "name": "Si", "solid": {"type": "G4Box", "parameters": {
                    "half_x_mm": h(0.025), "half_y_mm": h(1.0), "half_z_mm": h(1.0)}}, "material": "S"}],
            "placements": [{"name": "World", "copy_number": 0, "logical": 0, "mother_logical": None},
                           {"name": "Si", "copy_number": 0, "logical": 1, "mother_logical": 0}]}}}
        study = {"physics": {"layered_sim": {"geometry": {"layers": [{"slabs": [{"name": "Si", "thickness_mm": 0.3}]}]},
                                             "physics": {"em_constructor": "G4EmStandardPhysics_option4"}}}}
        self.assertEqual(self.C.derived(study)["min_thickness_mm"], 0.3)
        self.assertNotIn("min_thickness_basis", self.C.derived(study))  # spec/1: output unchanged
        d = self.C.derived(study, ec)
        self.assertEqual((d["min_thickness_mm"], d["min_thickness_basis"]), (0.05, "effective config"))
        with self.assertRaises(self.C.StudyError):
            self.C.derived(study, {"recorded": False})


class RealizationEntryTests(unittest.TestCase):
    """The realization profile named by an element_sim spec enters the input manifest from its recorded path, or,
    when that path is from another machine, from a same-named copy above the spec whose sha256 matches; the entry
    keeps the recorded path, so a replayed campaign writes the same record on every machine."""

    def setUp(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import check_geant4_study as C
        self.C = C
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        self.esp = self.root / "artifacts" / "specs" / "x.spec.json"
        self.esp.parent.mkdir(parents=True)
        self.esp.write_text("{}", encoding="utf-8")
        self.profile = self.root / "artifacts" / "p.realization.json"
        self.profile.write_text('{"mapping": "1.1.0"}', encoding="utf-8")
        self.sha = C.sha256_file(self.profile)

    def tearDown(self):
        self._t.cleanup()

    def test_recorded_path_present_is_used(self):
        entry = self.C.realization_entry({"path": str(self.profile), "sha256": self.sha}, self.esp, self.root)
        self.assertEqual(entry, {"path": "artifacts/p.realization.json", "sha256": self.sha})

    def test_path_from_another_machine_resolves_to_the_matching_copy(self):
        rp = "~/no-such-machine-folder/p.realization.json"
        entry = self.C.realization_entry({"path": rp, "sha256": self.sha}, self.esp, self.root)
        self.assertEqual(entry, {"path": rp, "sha256": self.sha})

    def test_copy_with_another_hash_or_no_recorded_hash_is_not_used(self):
        rp = "~/no-such-machine-folder/p.realization.json"
        self.assertIsNone(self.C.realization_entry({"path": rp, "sha256": "0" * 64}, self.esp, self.root))
        self.assertIsNone(self.C.realization_entry({"path": rp}, self.esp, self.root))

    def test_no_copy_found_outside_root(self):
        inner = self.root / "inner"
        (inner / "specs").mkdir(parents=True)
        esp = inner / "specs" / "y.spec.json"
        esp.write_text("{}", encoding="utf-8")
        rp = "~/no-such-machine-folder/p.realization.json"
        self.assertIsNone(self.C.realization_entry({"path": rp, "sha256": self.sha}, esp, inner))


if __name__ == "__main__":
    unittest.main()
