"""Geant4 search values and F4 confirmation (Geant4 program stage C2, contracts CV-C2 in the unreleased 3.13.0): the
seed rule (an evaluation never reuses a Geant4 search seed), the seed_group uniqueness rule, the refusal of a search
run as study evidence, and the search side of C2 (Geant4 search values, paired selection, cache, winner's curse).
Every project is SYNTHETIC: Example A (examples/design-space-spectrometer)."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
from contracts import design  # noqa: E402
from core.simulation import seeds  # noqa: E402

EVAL = PLUGIN / "skills" / "hep-detector" / "scripts" / "evaluate_design.py"
sys.path.insert(0, str(EVAL.parent))
_spec = importlib.util.spec_from_file_location("evaluate_design_search_g4", EVAL)
EV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EV)
CHECK = PLUGIN / "skills" / "hep-detector" / "scripts" / "check_geant4_study.py"

EXAMPLE_A = PLUGIN / "examples" / "design-space-spectrometer" / "output" / "artifacts"
NS_A = "ams-like-v1"


def ev(art: Path, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = EV.main([*map(str, args), "--artifacts", str(art)])
    return code, json.loads(buf.getvalue())


def sim_run(seed: int, spec: str, group=None, blocks=16, block_size=64, role="search", version="3.13.0") -> dict:
    sim = {"seed_scheme": "hash-v1", "logical_run_seed": seed, "spec_sha256": spec, "seeding": "per-event",
           "evidence_role": role, "blocks": {"blocks": blocks, "block_size": block_size}}
    if group:
        sim["seed_group"] = group
    return {"artifact_type": "computational-run", "artifact_id": f"geant4-run-{spec}", "contract_version": version,
            "status": ["unvalidated"], "extension": {"simulation": sim}}


def seed_errors(art: Path) -> list[str]:
    return [e["message"] for e in design.derive(art)["errors"] if e["code"] == "design.seed_reuse"]


class SeedGroupRule(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.art = Path(self.tmp.name) / "a"
        shutil.copytree(EXAMPLE_A, self.art, ignore=shutil.ignore_patterns("reports"))
        (self.art / "runs" / "g4").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name: str, doc: dict) -> None:
        (self.art / "runs" / "g4" / f"{name}.computational-run.json").write_text(json.dumps(doc), encoding="utf-8")

    def test_one_seed_group_is_accepted(self):
        s = seeds.search_group_seed("SEARCH-X", "gen-1")
        self.put("a", sim_run(s, "spec-a", "gen-1"))
        self.put("b", sim_run(s, "spec-b", "gen-1"))
        self.assertEqual(seed_errors(self.art), [])

    def test_seed_repeated_outside_a_seed_group(self):
        self.put("a", sim_run(77, "spec-a", role="nominal"))
        self.put("b", sim_run(77, "spec-b", role="nominal"))
        self.assertTrue(any("outside one declared seed_group" in m for m in seed_errors(self.art)))

    def test_equal_spec_hashes_within_a_seed_group(self):
        self.put("a", sim_run(78, "spec-a", "gen-1"))
        self.put("b", sim_run(78, "spec-a", "gen-1"))
        self.assertTrue(any("same spec hash" in m for m in seed_errors(self.art)))

    def test_unequal_blocks_within_a_seed_group(self):
        self.put("a", sim_run(79, "spec-a", "gen-1"))
        self.put("b", sim_run(79, "spec-b", "gen-1", blocks=8))
        self.assertTrue(any("differ in blocks" in m for m in seed_errors(self.art)))

    def test_older_records_are_not_constrained(self):
        self.put("a", sim_run(80, "spec-a", role="nominal", version="3.12.0"))
        self.put("b", sim_run(80, "spec-b", role="nominal", version="3.12.0"))
        self.assertEqual(seed_errors(self.art), [])


class SearchSeedRule(unittest.TestCase):
    """CV-C2: an evaluation whose run used a seed a search_summary lists among its Geant4 search seeds is
    design.contract_mismatch."""

    def test_reused_search_seed_is_a_contract_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "a"
            shutil.copytree(EXAMPLE_A, art, ignore=shutil.ignore_patterns("reports"))
            s = seeds.search_group_seed("SEARCH-Z", "gen-1")
            search = {"artifact_type": "computational-run", "artifact_id": "search-z", "contract_version": "3.13.0",
                      "status": ["synthetic"], "extension": {"search_summary": {
                          "search_spec_sha256": "0" * 64, "points": [], "front": [], "finalists": [],
                          "seeds": {"geant4_search": [{"seed_group": "gen-1", "seed": s}]}}}}
            (art / "runs" / "SEARCH-Z.computational-run.json").write_text(json.dumps(search), encoding="utf-8")
            ev_doc = json.loads((art / "evaluations" / "CALC-TRK-S.json").read_text(encoding="utf-8"))
            run_path = art / ev_doc["extension"]["run_ref"]
            clean = design.derive(art)
            self.assertFalse(any("Geant4 search seed" in e["message"] for e in clean["errors"]))
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["extension"]["seeds"] = {"element_sim": s}
            run_path.write_text(json.dumps(run), encoding="utf-8")
            d = design.derive(art)
            hits = [e for e in d["errors"] if "Geant4 search seed" in e["message"]]
            self.assertTrue(hits, d["errors"][:5])
            self.assertEqual(hits[0]["code"], "design.contract_mismatch")


class SearchRunIsNoEvidence(unittest.TestCase):
    def test_label_refuses_a_search_run(self):
        """CV-C2: check_geant4_study.py label refuses a run record with evidence_role search (J15's recorded study
        inputs, with a search run offered as evidence)."""
        study = PLUGIN / "examples" / "design-minimal-spectrometer" / "recorded" / "artifacts" / "studies" / "N4-TRK1"
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "search.computational-run.json"
            p.write_text(json.dumps(sim_run(5, "spec-a", "gen-1")), encoding="utf-8")
            r = subprocess.run([sys.executable, "-B", str(CHECK), "label", "--spec", str(study / "study.json"),
                                "--benchmarks", str(study / "bench.results.json"), "--convergence",
                                str(study / "convergence.json"), "--run-record", str(p), "--project-root", tmp],
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 2, r.stdout[-800:])
            self.assertIn("evidence_role search", r.stdout)


J15 = PLUGIN / "examples" / "design-minimal-spectrometer"


def j15_project(dst: Path) -> Path:
    """J15's design-spec and candidates (examples/design-minimal-spectrometer/run.py write_design) in dst."""
    spec = importlib.util.spec_from_file_location("j15_run_g4", J15 / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    art = mod.write_design(dst)
    shutil.copy(J15 / "j15.realization.json", art / "j15.realization.json")
    return art


def j15_search_spec(art: Path, free: list, slots: dict | None = None) -> dict:
    import hashlib
    return {"search_spec_version": 1,
            "design_spec": {"path": "design-spec.v1.json",
                            "sha256": hashlib.sha256((art / "design-spec.v1.json").read_bytes()).hexdigest()},
            "base_candidate": "j15-v1:cand-N6", "objectives": [{"requirement": "REQ-TRK-001"}],
            "free_parameters": free, "slots": slots or {}, "rules_version": "1.1.0", "materials_version": "1.0.0",
            "budget": {"evaluations": 24, "geant4": 0},
            "optimizer": {"name": "nsga2", "population": 8, "generations": 2, "seed": 7},
            "finalists": {"max": 2, "distinct_topologies": True}}


class DecodedSpecs(unittest.TestCase):
    """C2.9: an element_sim.spec/1 derived from a decoded candidate (evaluate_design.py geometry, then geant4_run.py
    from-geometry with J15's realization profile) passes geant4_run.py check-spec in a subprocess, for decoded
    candidates that change each role: tracking (plane positions), bending (field), tof (plane positions, thickness and
    time resolution), calorimetry-em (depth and passive material: the sampling structure derived by role rules 1.1.0
    passes from-geometry's depth check), rich (added; the geometry mapping has no RICH, so it does not enter the
    spec). Role rules 1.1.0 name the TOF's and calorimeter's geometry in the mapping's parameters, so the search can
    vary them in Geant4 (1.0.0 named them for the F1 tools only)."""

    CASES = {
        "tracking": ([{"ref": "DES-TRK-001.parameters.layer_positions_m", "kind": "positions", "n": [6, 6],
                       "range": [0.0, 0.8], "min_spacing_m": 0.05}], {}),
        "bending": ([{"ref": "DES-MAG-001.parameters.field_T", "range": [0.3, 0.7]}], {}),
        "tof": ([{"ref": "DES-TOF-001.parameters.layer_positions_m", "kind": "positions", "n": [4, 4],
                  "range": [-0.4, 1.1], "min_spacing_m": 0.02},
                 {"ref": "DES-TOF-001.parameters.layer_thickness_m", "range": [0.005, 0.02]},
                 {"ref": "DES-TOF-001.parameters.time_resolution_ps", "range": [60.0, 200.0]}], {}),
        "calorimetry-em": ([{"ref": "DES-CAL-001.parameters.depth_x0", "range": [10.0, 25.0]},
                            {"ref": "DES-CAL-001.parameters.passive_material", "choices": ["G4_Pb"]}], {}),
        "rich": ([], {"rich": [0, 1]}),
    }

    def test_check_spec_per_role(self):
        sys.path.insert(0, str(PLUGIN / "tests" / "skills" / "hep_detector"))
        from test_design_search import space_for
        run = PLUGIN / "adapters" / "geant4" / "assets" / "geant4_run.py"
        for role, (free, slots) in self.CASES.items():
            with self.subTest(role=role), tempfile.TemporaryDirectory() as tmp:
                art = j15_project(Path(tmp) / "proj")
                space = space_for(art, j15_search_spec(art, free, slots))
                prop = {"id": "P", "reason": "r", **({"enabled": {"rich": True}} if role == "rich" else {}),
                        **({"parameters": {free[0]["ref"]: 0.55}} if role == "bending" else {}),
                        **({"parameters": {free[0]["ref"]: [-0.32, -0.3, 1.0, 1.02], free[1]["ref"]: 0.012}}
                           if role == "tof" else {}),
                        **({"parameters": {free[0]["ref"]: 20.0}} if role == "calorimetry-em" else {})}
                g, _ = space.repair(space.proposal_genome(prop))
                name = f"cand-{role}"
                doc = EV.expanded_candidate(space, {"index": 0, "genome": space.genome_dict(g)}, name, [
                    dict(EV.Writer(design.Project(art)).input_ref("candidates/cand-N6.json"), binding="parameters")])
                (art / "candidates" / f"{name}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
                code, out = ev(art, "geometry", "--candidate", f"j15-v1:{name}", "--figure-of-merit",
                               "momentum-resolution-core", "--denominator", "rigidity_GV=1", "--denominator",
                               "species=proton", "--id", f"G-{role}")
                self.assertEqual(code, 0, out)
                geom = json.loads((art / "studies" / f"G-{role}.geometry.json").read_text(encoding="utf-8"))
                fields = geom.get("fields") or {}
                if role in ("tof", "calorimetry-em"):
                    self.assertIn("tof_layer_positions_m" if role == "tof" else "calo_depth_x0", fields)
                out_spec = Path(tmp) / "spec.json"
                p = subprocess.run([sys.executable, "-B", str(run), "from-geometry", "--geometry",
                                    str(art / "studies" / f"G-{role}.geometry.json"), "--profile",
                                    str(art / "j15.realization.json"), "--out", str(out_spec)],
                                   capture_output=True, text=True, timeout=120)
                self.assertEqual(p.returncode, 0, p.stdout[-800:])
                p = subprocess.run([sys.executable, "-B", str(run), "check-spec", "--spec", str(out_spec)],
                                   capture_output=True, text=True, timeout=120)
                self.assertEqual(p.returncode, 0, p.stdout[-800:])
                self.assertTrue(json.loads(p.stdout)["ok"])
                eff = design.Project(art).effective(f"j15-v1:{name}")
                if role == "tof":
                    tof = eff["DES-TOF-001"]["parameters"]
                    self.assertEqual(fields["tof_time_resolution_ps"], tof["time_resolution_ps"]["value"])
                    self.assertEqual(fields["tof_layer_positions_m"], [-0.32, -0.3, 1.0, 1.02])
                    self.assertEqual(fields["tof_layer_thickness_m"], 0.012)
                    self.assertAlmostEqual(tof["path_m"]["value"], 1.34)  # derived: the F1 flight path
                    derived_spec = json.loads(out_spec.read_text(encoding="utf-8"))
                    tofs = [e for e in derived_spec["elements"] if e["role"] == "tof-layer"]
                    self.assertEqual([min(e["half_mm"]) for e in tofs], [6.0] * 4)  # half of 12 mm on the stack axis
                if role == "calorimetry-em":
                    cal = eff["DES-CAL-001"]["parameters"]
                    self.assertEqual(fields["calo_depth_x0"], 20.0)
                    self.assertEqual(cal["sampling_layers"]["value"], 20)
                    self.assertEqual(fields["calo_passive_thickness_mm"], cal["passive_thickness_mm"]["value"])


class FakeValues:
    """A stand-in for design_search_lib.geant4_values.Geant4Values (no Geant4): every design has the same true value
    TRUTH; block b of a run carries a block effect shared by every run of one seed (common random numbers, size
    COMMON) and the design's own noise (OWN), so the search's selection and its paired gate run on known truth."""
    TRUTH, COMMON, OWN = 0.020, 0.0010, 0.0004
    instances: list = []

    def __init__(self, cfg, work, artifacts, search_id, g4, created):
        self.g4, self.events, self.blocks = g4, int(g4["events"]), int(g4.get("blocks", 16))
        self.versions = {"adapter": "fake"}
        self.runs = 0
        self.cache_hits = 0
        self.seen: dict = {}
        FakeValues.instances.append(self)

    def value(self, evaluate_design, candidate_doc, cid, short, digest, label, target, seed, seed_group, point):
        import random
        import statistics
        key = (digest, label, seed)
        if key in self.seen:
            self.cache_hits += 1
            return dict(self.seen[key], cached=True)
        self.runs += 1
        common = random.Random(f"common:{seed}")
        own = random.Random(f"own:{seed}:{digest}:{label}")
        blocks = [self.TRUTH + common.gauss(0, self.COMMON) + own.gauss(0, self.OWN) for _ in range(self.blocks)]
        out = {"value": statistics.fmean(blocks), "se": statistics.stdev(blocks) / self.blocks ** 0.5,
               "dof": self.blocks - 1, "blocks": blocks, "bound": "optimistic", "seed": seed,
               "seed_group": seed_group, "run": f"fake-{seed}-{point}"}
        self.seen[key] = out
        return dict(out, cached=False)


def g4_spec(art: Path, **over) -> dict:
    sys.path.insert(0, str(PLUGIN / "tests" / "skills" / "hep_detector"))
    from test_design_search import spec_a
    spec = spec_a(art, budget={"evaluations": 48, "geant4": 200},
                  optimizer={"name": "nsga2", "population": 12, "generations": 4, "seed": 2026},
                  finalists={"max": 3, "distinct_topologies": True}, consistency_samples=1)
    spec["geant4"] = {"realization": "realization.json", "reco": {}, "events": 1024, "blocks": 16,
                      "targets": {"REQ-TRK-001": {"observable": {"source_column": "inv_rig_res",
                                                                   "estimator": "gaussian-core",
                                                                   "bins": {"lo": -1, "hi": 1, "width": 0.0005}},
                                                  "particle": "proton"}},
                      "top_k": 3, "generations": 2, "offspring": 6}
    spec.update(over)
    return spec


class Geant4Refinement(unittest.TestCase):
    """S2 on Example A with the fake backend: seed groups, the paired gate, survival per topology, the budget, the
    summary, and the winner's curse (gate G-C2b)."""

    @classmethod
    def setUpClass(cls):
        import design_search_lib.geant4_values as GV
        cls.GV, cls.real = GV, GV.Geant4Values
        GV.Geant4Values = FakeValues
        cls.tmp = tempfile.TemporaryDirectory()
        cls.cfg = Path(cls.tmp.name) / "cfg.json"
        cls.cfg.write_text("{}")
        cls.env = os.environ.get("HEP_GEANT4_CONFIG")
        os.environ["HEP_GEANT4_CONFIG"] = str(cls.cfg)
        cls.art = Path(cls.tmp.name) / "a"
        shutil.copytree(EXAMPLE_A, cls.art, ignore=shutil.ignore_patterns("reports"))
        (cls.art / "realization.json").write_text("{}")
        cls.run_search("SEARCH-G", g4_spec(cls.art))

    @classmethod
    def run_search(cls, sid, spec):
        (cls.art / "search").mkdir(exist_ok=True)
        (cls.art / "search" / f"{sid}.spec.json").write_text(json.dumps(spec), encoding="utf-8")
        FakeValues.instances.clear()
        code, out = ev(cls.art, "search", "--spec", f"search/{sid}.spec.json", "--id", sid, "--status", "synthetic",
                       "--geant4-work", Path(cls.tmp.name) / "g4work")
        assert code == 0, out
        doc = json.loads((cls.art / "runs" / f"{sid}.computational-run.json").read_text(encoding="utf-8"))
        setattr(cls, sid.replace("-", "_"), doc["extension"]["search_summary"])
        return doc["extension"]["search_summary"]

    @classmethod
    def tearDownClass(cls):
        cls.GV.Geant4Values = cls.real
        if cls.env is None:
            os.environ.pop("HEP_GEANT4_CONFIG", None)
        else:
            os.environ["HEP_GEANT4_CONFIG"] = cls.env
        cls.tmp.cleanup()

    def test_generations_share_a_seed_group_and_record_their_seeds(self):
        s = self.SEARCH_G
        self.assertEqual(s["levels"], ["F1", "geant4"])
        g = s["geant4"]
        self.assertEqual(g["gate_g_c2a"]["comparison_after_trial"], "paired")
        self.assertGreater(g["gate_g_c2a"]["variance_ratio"], 2.0)
        want = [seeds.search_group_seed("SEARCH-G", f"gen-{i}") for i in range(len(g["generations"]))]
        self.assertEqual(s["seeds"]["geant4_search"], sorted(want))
        for gen in g["generations"]:
            self.assertEqual(gen["comparison"], "paired")
            members = {m["index"] for m in gen["members"]}
            self.assertTrue(set(gen["survivors"]) <= members)

    def test_survivors_are_re_evaluated_each_generation(self):
        s = self.SEARCH_G
        g0, g1 = s["geant4"]["generations"][:2]
        pts = {p["index"]: p for p in s["points"]}
        for k in g0["survivors"]:
            self.assertIn(k, {m["index"] for m in g1["members"]})
            gens = [r["generation"] for r in pts[k]["geant4"]]
            self.assertEqual(gens[-2:], [0, 1])
            seeds_k = [r["seed"] for r in pts[k]["geant4"][-2:]]
            self.assertNotEqual(seeds_k[0], seeds_k[1])  # a re-evaluation is a new evaluation (new S, no cache)

    def test_finalists_are_the_survivors_one_per_topology(self):
        s = self.SEARCH_G
        last = s["geant4"]["generations"][-1]
        fin = [f["index"] for f in s["finalists"]]
        self.assertEqual(sorted(fin), sorted(last["survivors"])[:3])
        self.assertTrue(all(f["fixed_from"] == "geant4" and f["fixed_before"] == "expand" for f in s["finalists"]))
        self.assertEqual(len({f["topology"] for f in s["finalists"]}), len(fin))
        self.assertEqual(s["evaluated"]["geant4"], s["geant4"]["runs"])
        self.assertLessEqual(s["geant4"]["runs"], 200)

    def test_the_summary_validates_and_expands(self):
        from contracts.validate import validate_artifact
        doc = json.loads((self.art / "runs" / "SEARCH-G.computational-run.json").read_text(encoding="utf-8"))
        self.assertTrue(validate_artifact(doc).ok)
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "a"
            shutil.copytree(self.art, art)
            k = self.SEARCH_G["finalists"][0]["index"]
            code, out = ev(art, "expand", "--search", "runs/SEARCH-G.computational-run.json", "--point", k,
                           "--candidate-id", "cand-G")
            self.assertEqual(code, 0, out)
            code, r = ev(art, "run", "--candidate", f"{NS_A}:cand-G", "--requirement", "REQ-TRK-001", "--id",
                         "CALC-TRK-G")
            self.assertEqual(code, 0, r)
            code, d = ev(art, "search", "--diagnose", "runs/SEARCH-G.computational-run.json")
            self.assertEqual(code, 0, d)
            rows = {row["search_level"]: row for row in d["rows"] if row["figure_of_merit"] == "momentum-resolution-core"}
            self.assertEqual(set(rows), {"F1", "geant4"})
            self.assertEqual(rows["F1"]["search_minus_official"], 0.0)
            self.assertAlmostEqual(rows["geant4"]["search_value"], FakeValues.TRUTH, delta=0.002)
            diag = json.loads((art / d["diagnostic"]).read_text(encoding="utf-8"))
            self.assertTrue(validate_artifact(diag).ok)
            self.assertFalse(any(e["code"] != "design.orphan_run" and "DIAG" in e["path"]
                                 for e in design.derive(art)["errors"]))

    def test_winners_curse_toy(self):
        """Gate G-C2b: on designs that all have the same true value, the survivors' search values are optimistic
        (selection on noise) while a confirmation on independent seeds is unbiased."""
        import random
        import statistics
        s = self.SEARCH_G
        pts = {p["index"]: p for p in s["points"]}
        search_err, confirm_err = [], []
        def value(k, g):
            return next(x for x in pts[k]["geant4"] if x["generation"] == g)["values"]["REQ-TRK-001"]["value"]
        for gen in s["geant4"]["generations"]:
            g = gen["generation"]
            for k in gen["survivors"]:
                topo = pts[k]["topology"]
                group = [value(m["index"], g) for m in gen["members"] if pts[m["index"]]["topology"] == topo]
                # the seed_group's common offset cancels within a generation: the optimism is the survivor's value
                # against its own selection pool, all of which have the same true value
                search_err.append(value(k, g) - statistics.fmean(group))
                rng = random.Random(f"confirm:{k}:{gen['generation']}")
                confirm = statistics.fmean(FakeValues.TRUTH + rng.gauss(0, FakeValues.COMMON) + rng.gauss(
                    0, FakeValues.OWN) for _ in range(16))
                confirm_err.append(confirm - FakeValues.TRUTH)
        own_se = FakeValues.OWN / 4
        self.assertLess(statistics.fmean(search_err), -0.5 * own_se, search_err)
        se_c = (FakeValues.COMMON ** 2 + FakeValues.OWN ** 2) ** 0.5 / 4 / len(confirm_err) ** 0.5
        self.assertLess(abs(statistics.fmean(confirm_err)), 3 * se_c)

    def test_gate_switches_to_independent_without_common_random_numbers(self):
        old = FakeValues.COMMON
        FakeValues.COMMON = 0.0
        try:
            s = self.run_search("SEARCH-I", g4_spec(self.art))
        finally:
            FakeValues.COMMON = old
        g = s["geant4"]
        self.assertEqual(g["gate_g_c2a"]["comparison_after_trial"], "independent")
        self.assertIn("independent", g["gate_g_c2a"]["note"])
        later = [x for x in g["generations"][1:] if "comparison" in x]
        self.assertTrue(later and all(x["comparison"] == "independent" for x in later))
        self.assertEqual(len(s["seeds"]["geant4_search"]), len(set(s["seeds"]["geant4_search"])))

    def test_budget_and_spec_rules(self):
        with self.assertRaises(AssertionError):
            self.run_search("SEARCH-B", g4_spec(self.art, budget={"evaluations": 48, "geant4": 0}))
        spec = g4_spec(self.art, budget={"evaluations": 48, "geant4": 4})
        s = self.run_search("SEARCH-S", spec)
        self.assertIn("would be exceeded", s["geant4"]["generations"][0]["stopped"])
        bad = g4_spec(self.art)
        bad["geant4"]["targets"] = {"REQ-NOPE": bad["geant4"]["targets"]["REQ-TRK-001"]}
        with self.assertRaises(AssertionError):
            self.run_search("SEARCH-N", bad)


if __name__ == "__main__":
    unittest.main()
