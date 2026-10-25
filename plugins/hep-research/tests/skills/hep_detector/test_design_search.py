"""Automated candidate generation at F1 (geant4 program stage C1, contracts 3.13.0 CV-C1): the search spec and its
cross-field rules, the role rules and the decoder, validity and repair, in-process F1 search values against
evaluate_design.py run, the search_summary and the orphan-run exemption, expand --search, and the closure tests of
C1.8 (plane placement, structure choice, reproducibility, consistency; DTLZ2 is in test_design_search_lib.py).
Every project is SYNTHETIC: Example A (examples/design-space-spectrometer) or the spectrometer of
tests/contracts/design_fixtures.py."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "tests" / "contracts"))
from contracts import design  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from design_fixtures import Builder, magnet_subsystem, tracker_subsystem  # noqa: E402

EVAL = PLUGIN / "skills" / "hep-detector" / "scripts" / "evaluate_design.py"
_spec = importlib.util.spec_from_file_location("evaluate_design_search", EVAL)
EV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EV)

EXAMPLE_A = PLUGIN / "examples" / "design-space-spectrometer" / "output" / "artifacts"
NS_A = "ams-like-v1"
ASSETS = PLUGIN / "skills" / "hep-detector" / "assets" / "design-search"


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ev(art: Path, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = EV.main([*map(str, args), "--artifacts", str(art)])
    return code, json.loads(buf.getvalue())


def example_a(dst: Path) -> Path:
    shutil.copytree(EXAMPLE_A, dst, ignore=shutil.ignore_patterns("reports"))
    return dst


def spec_a(art: Path, **over) -> dict:
    spec = {"search_spec_version": 1,
            "design_spec": {"path": "design-spec.v1.json", "sha256": sha(art / "design-spec.v1.json")},
            "base_candidate": f"{NS_A}:cand-S",
            "objectives": [{"requirement": "REQ-TRK-001"}, {"requirement": "CON-MASS-001"}],
            "constraints": [{"requirement": "REQ-CC-001"}],
            "free_parameters": [
                {"ref": "DES-TRK-001.parameters.layer_positions_m", "kind": "positions", "n": [4, 9],
                 "range": [0.0, 2.0], "min_spacing_m": 0.05},
                {"ref": "DES-MAG-001.parameters.field_T", "range": [0.1, 1.0]}],
            "slots": {"tof": [0, 1]},
            "regenerate_budgets": ["DES-TRK-001", "DES-MAG-001"],
            "rules_version": "1.1.0", "materials_version": "1.0.0",
            "budget": {"evaluations": 240, "geant4": 0},
            "optimizer": {"name": "nsga2", "population": 24, "generations": 30, "seed": 12345},
            "stopping": {"hypervolume_window": 10, "min_improvement": 0.001, "reference_point": "auto"},
            "finalists": {"max": 3, "distinct_topologies": True},
            "proposals": [{"id": "P-base", "reason": "the base layout as a seed",
                           "parameters": {"DES-MAG-001.parameters.field_T": 0.14}},
                          {"id": "P-tof", "reason": "a time-of-flight pair for low-rigidity PID",
                           "enabled": {"tof": True}}],
            "consistency_samples": 3}
    spec.update(over)
    return spec


def write_spec(art: Path, spec: dict, name: str = "SEARCH-A") -> str:
    rel = f"search/{name}.spec.json"
    (art / "search").mkdir(exist_ok=True)
    (art / rel).write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
    return rel


def space_for(art: Path, spec: dict, sid: str = "SEARCH-T") -> "EV.SearchSpace":
    proj = design.Project(art)
    roles, _ = EV.load_asset("roles.json", "rules_version", spec["rules_version"])  # as the tool loads them
    materials = json.loads((ASSETS / "materials.json").read_text(encoding="utf-8"))
    return EV.SearchSpace(proj, spec, roles, materials, sid)


def curvature_factor(xs) -> float:
    """A of sigma_k^2 = A sigma^2 / L^4 (k = 2c of the least-squares parabola, equal weights), exact rational
    arithmetic: the independent oracle of section C Appendix A (design_search_closure.py)."""
    lo, hi = min(xs), max(xs)
    z = [(Fraction(x) - Fraction(lo)) / (Fraction(hi) - Fraction(lo)) for x in xs]
    s = [sum(x ** p for x in z) for p in range(5)]
    m = [[s[0], s[1], s[2] / 2], [s[1], s[2], s[3] / 2], [s[2] / 2, s[3] / 2, s[4] / 4]]
    det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
           + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    return float((m[0][0] * m[1][1] - m[0][1] * m[1][0]) / det)


class SharedSearch(unittest.TestCase):
    """One small search on Example A (cand-S, positions and field free, an optional TOF slot), shared by the tests that
    only read its record."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.art = example_a(Path(cls.tmp.name) / "a")
        cls.n_eval_files = len(list((cls.art / "evaluations").glob("*.json")))
        cls.n_cand_files = len(list((cls.art / "candidates").glob("*.json")))
        cls.spec_rel = write_spec(cls.art, spec_a(cls.art))
        cls.code, cls.out = ev(cls.art, "search", "--spec", cls.spec_rel, "--id", "SEARCH-A", "--status", "synthetic")
        cls.run_rel = "runs/SEARCH-A.computational-run.json"
        cls.record = json.loads((cls.art / cls.run_rel).read_text(encoding="utf-8")) if cls.code == 0 else None

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_search_writes_only_its_run(self):
        """C1.10: search writes no design-candidate and no evaluation; the population lives in the summary."""
        self.assertEqual(self.code, 0, self.out)
        self.assertEqual(len(list((self.art / "evaluations").glob("*.json"))), self.n_eval_files)
        self.assertEqual(len(list((self.art / "candidates").glob("*.json"))), self.n_cand_files)
        self.assertFalse((self.art / "outputs" / "CALC-search.json").exists())
        s = self.record["extension"]["search_summary"]
        self.assertEqual(s["evaluated"]["F1"], 240)
        self.assertEqual(s["evaluated"]["distinct_designs"], len(s["points"]))
        self.assertEqual(s["levels"], ["F1"])
        self.assertEqual(s["seeds"]["geant4_search"], [])
        self.assertIn("support no verdict", s["note"])
        for key in ("verdict", "verdicts", "ranking", "pareto", "recommended", "screened_out", "at_risk"):
            self.assertNotIn(key, s)
            self.assertFalse(any(key in p for p in s["points"]))
        self.assertEqual(self.out["search_size"]["evaluations"], 240)

    def test_pre_declaration(self):
        """Section C.3 rule 4: the spec, design-spec, base chain, rule and material hashes, budget, optimizer and seed
        are on the record."""
        s = self.record["extension"]["search_summary"]
        self.assertEqual(s["search_spec_sha256"], sha(self.art / self.spec_rel))
        self.assertEqual(s["design_spec_sha256"], sha(self.art / "design-spec.v1.json"))
        self.assertEqual(s["rules_sha256"], sha(ASSETS / "roles.json"))
        self.assertEqual(s["materials_sha256"], sha(ASSETS / "materials.json"))
        self.assertEqual(s["optimizer"]["seed"], 12345)
        self.assertEqual(s["budget"]["evaluations"], 240)
        manifest = {m["path"] for m in self.record["extension"]["input_manifest"]}
        self.assertTrue({self.spec_rel, "design-spec.v1.json", "candidates/cand-S.json",
                         "skills/hep-detector/assets/design-search/roles.json"} <= manifest)

    def test_proposals_are_flagged(self):
        """Section C.3 rule 5: the designer's proposals are proposer llm and take the same pipeline."""
        s = self.record["extension"]["search_summary"]
        llm = [p for p in s["points"] if p["proposer"] == "llm"]
        self.assertEqual(sorted(p["proposal"] for p in llm), ["P-base", "P-tof"])
        self.assertEqual({p["id"] for p in s["proposals"]}, {"P-base", "P-tof"})
        tof = next(p for p in llm if p["proposal"] == "P-tof")
        self.assertTrue(tof["genome"]["DES-TOF-S01.enabled"])
        self.assertIn("REQ-TRK-001", tof["values"])

    def test_summary_schema_and_orphan_exemption(self):
        """C1.10: the search_summary passes its schema; the run is no orphan; the verdicts are those of the
        candidates only."""
        rep = validate_artifact(self.record, strict=True)
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors])
        self.assertTrue(design.is_search_run(self.record))
        d = design.derive(self.art)
        self.assertEqual(d["orphan_runs"], [])
        self.assertEqual(d["status"], "ok", d.get("errors"))

    def test_an_evaluation_naming_the_search_run_is_refused(self):
        """C1.10, CV-C1: an evaluation whose run_ref is a search run is design.search_point_not_expanded."""
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "a"
            shutil.copytree(self.art, art)
            doc = json.loads((art / "evaluations" / "CALC-TRK-S.json").read_text(encoding="utf-8"))
            doc["extension"]["run_ref"] = self.run_rel
            doc["extension"]["evaluation_id"] = f"{NS_A}:CALC-TRK-S-search"
            doc["artifact_id"] = f"{NS_A}-CALC-TRK-S-search"
            (art / "evaluations" / "CALC-TRK-S-search.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
            d = design.derive(art)
            codes = {e["code"] for e in d["errors"] if "CALC-TRK-S-search" in e["path"]}
            self.assertIn("design.search_point_not_expanded", codes)

    def test_consistency_with_run(self):
        """C1.4, C1.10: the finalists and a sample of points recomputed with run agree to 1e-12 (chain included)."""
        c = self.record["extension"]["search_summary"]["consistency"]
        s = self.record["extension"]["search_summary"]
        self.assertEqual(c["checked"], len(s["finalists"]) + 3)
        self.assertLessEqual(c["max_relative_difference"], 1e-12)
        labels = {lab for row in c["points"] for lab in row["values"]}
        self.assertEqual(labels, {"REQ-TRK-001", "CON-MASS-001", "REQ-CC-001"})

    def test_front_and_finalists(self):
        """S3: the search front is non-dominated among the feasible points; finalists come from distinct topologies."""
        s = self.record["extension"]["search_summary"]
        pts = {p["index"]: p for p in s["points"]}
        self.assertTrue(s["front"])
        self.assertTrue(all(pts[k]["violation"] == 0 for k in s["front"]))
        topos = [f["topology"] for f in s["finalists"]]
        self.assertEqual(len(topos), len(set(topos)))
        self.assertTrue(all(f["fixed_before"] == "expand" for f in s["finalists"]))
        self.assertTrue({f["index"] for f in s["finalists"]} <= set(s["front"]))

    def test_expand_only_finalists_then_run_budget_report(self):
        """C1.7, C1.10: only finalists expand; the candidate goes through run, budget and report, the verdicts appear
        as usual and the ranking is refused without expected precision."""
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / "a"
            shutil.copytree(self.art, art)
            s = self.record["extension"]["search_summary"]
            fin = s["finalists"][0]["index"]
            other = next(p["index"] for p in s["points"] if p["index"] not in {f["index"] for f in s["finalists"]})
            code, out = ev(art, "expand", "--search", self.run_rel, "--point", other, "--candidate-id", "cand-no")
            self.assertEqual(code, 2, out)
            self.assertIn("not a finalist", out["error"])
            code, out = ev(art, "expand", "--search", self.run_rel, "--point", fin, "--candidate-id", "cand-F")
            self.assertEqual(code, 0, out)
            cand = json.loads((art / "candidates" / "cand-F.json").read_text(encoding="utf-8"))
            self.assertTrue(validate_artifact(cand).ok)
            self.assertEqual(cand["extension"].get("derived_from"), f"{NS_A}:cand-S")
            self.assertEqual({i["ref"] for i in cand["inputs"]}, {"candidates/cand-S.json", self.run_rel})
            for pars in [o.get("parameters", {}) for o in cand["extension"]["overrides"].values()]:
                for p in pars.values():
                    self.assertEqual((p["source"], p["status"]), (f"search SEARCH-A point {fin}", "proposal"))
            point = next(p for p in s["points"] if p["index"] == fin)
            self.assertEqual(design.Project(art).effective_digest(f"{NS_A}:cand-F"), point["effective_digest"])
            code, r = ev(art, "run", "--candidate", f"{NS_A}:cand-F", "--requirement", "REQ-TRK-001", "--id",
                         "CALC-TRK-F")
            self.assertEqual(code, 0, r)
            self.assertEqual(r["value"], point["values"]["REQ-TRK-001"]["value"])
            code, r = ev(art, "budget", "--candidate", f"{NS_A}:cand-F", "--quantity", "mass", "--id", "CALC-MASS-F")
            self.assertEqual(code, 0, r)
            self.assertEqual(r["value"], point["values"]["CON-MASS-001"]["value"])
            code, r = ev(art, "report", "--name", "after-search")
            self.assertEqual(code, 0, r)
            gaps = {g["figure_of_merit"]: g for g in r["search_minus_official"]}  # section C.4.6 diagnostic
            self.assertEqual(set(gaps), {"momentum-resolution-core", "mass-budget"})
            self.assertTrue(all(g["search_minus_official"] == 0.0 and g["point"] == fin for g in gaps.values()))
            d = design.derive(art)
            row = next(m for item in d["requirements"] if item["id"].endswith("REQ-TRK-001")
                       for m in item["matrix"] if f"{NS_A}:cand-F" in m["candidates"])
            self.assertIn(row["result"], ("inconclusive", "fail"))
            self.assertEqual(d["ranking"]["status"], "refused")
            self.assertTrue(any("expected-precision" in r for r in d["ranking"]["reasons"]))
            md = (art / "reports" / "after-search.md").read_text(encoding="utf-8")
            self.assertIn("cand-F", md)
            code, out = ev(art, "expand", "--search", self.run_rel, "--point", fin, "--candidate-id", "cand-F")
            self.assertEqual(code, 2, out)


class SpecRules(unittest.TestCase):
    """C1.1, C1.10: the schema and the cross-field rules, each refusal with exit 2 and nothing written."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.art = example_a(Path(self.tmp.name) / "a")

    def tearDown(self):
        self.tmp.cleanup()

    def refused(self, spec: dict, needle: str, sid: str = "SEARCH-X"):
        rel = write_spec(self.art, spec, sid)
        code, out = ev(self.art, "search", "--spec", rel, "--id", sid)
        self.assertEqual(code, 2, out)
        self.assertIn(needle, out["error"])
        self.assertFalse((self.art / "runs" / f"{sid}.computational-run.json").exists())

    def test_schema(self):
        self.refused(dict(spec_a(self.art), search_spec_version=2), "design-search-spec/1")
        self.refused({k: v for k, v in spec_a(self.art).items() if k != "objectives"}, "design-search-spec/1")
        self.refused(dict(spec_a(self.art), optimizer={"name": "cma-es", "population": 8, "generations": 1, "seed": 1}),
                     "design-search-spec/1")
        self.refused(dict(spec_a(self.art), unknown_key=1), "design-search-spec/1")

    def test_objective_limits_and_targets(self):
        five = [{"requirement": "REQ-TRK-001"}] * 5
        self.refused(spec_a(self.art, objectives=five), "at most 4")
        self.refused(spec_a(self.art, objectives=[{"requirement": "REQ-NOPE-001"}]), "no requirement or constraint")
        self.refused(spec_a(self.art, objectives=[{"figure_of_merit": "not-a-fom", "reference_point": 1.0}]),
                     "not a figure of merit of the adequacy table")
        self.refused(spec_a(self.art, objectives=[{"figure_of_merit": "shower-containment",
                                                  "denominator": {"energy_GeV": 10, "species": "electron"},
                                                  "reference_point": 0.9}]), "capability.unavailable")
        self.refused(spec_a(self.art, objectives=[{"figure_of_merit": "momentum-resolution-core",
                                                  "denominator": {"rigidity_GV": 100}, "reference_point": 0.1}]),
                     "denominator needs exactly")
        self.refused(spec_a(self.art, objectives=[{"figure_of_merit": "mass-budget"}]), "reference_point")
        self.refused(spec_a(self.art, constraints=[{"figure_of_merit": "mass-budget"}]), "comparator and target")
        self.refused(spec_a(self.art, objectives=[{"figure_of_merit": "maximum-detectable-rigidity",
                                                  "denominator": {"species": "proton", "mdr_definition": "intrinsic"},
                                                  "reference_point": 1000.0}]), "several operations")

    def test_parameters_slots_and_versions(self):
        a = self.art
        self.refused(spec_a(a, free_parameters=[{"ref": "DES-TRK-001.parameters.layer_positions_m",
                                                 "kind": "positions", "n": [4, 9], "range": [0.0, 30.0]}]),
                     "outside the role rule")
        self.refused(spec_a(a, free_parameters=[{"ref": "DES-MAG-001.parameters.bore_m", "range": [0.1, 1.0]}]),
                     "does not let the search change")
        self.refused(spec_a(a, free_parameters=[{"ref": "DES-XYZ-001.parameters.field_T", "range": [0.1, 1.0]}]),
                     "neither in the base candidate")
        self.refused(spec_a(a, free_parameters=[{"ref": "DES-MAG-001.parameters.field_T", "kind": "integer",
                                                 "range": [1, 2]}]), "kind integer")
        self.refused(spec_a(a, free_parameters=[{"ref": "DES-TRK-001.parameters.layer_positions_m",
                                                 "kind": "positions", "n": [4, 9], "range": [0.0, 0.2],
                                                 "min_spacing_m": 0.05}]), "do not fit")
        self.refused(spec_a(a, slots={"tof": [0, 2]}), "at most one subsystem per role")
        self.refused(spec_a(a, slots={"trd": [0, 1]}), "no realization rule")
        self.refused(spec_a(a, slots={"not-a-role": [0, 1]}), "no realization rule")
        self.refused(spec_a(a, rules_version="9.9.9"), "a different version is a new search spec")
        self.refused(spec_a(a, budget={"evaluations": 10, "geant4": 5}), "the geant4 block go together")
        self.refused(spec_a(a, design_spec={"path": "design-spec.v1.json", "sha256": "0" * 64}), "new design-spec")
        self.refused(spec_a(a, regenerate_budgets=["DES-NOPE-001"]), "regenerate_budgets")
        self.refused(spec_a(a, proposals=[{"id": "P", "reason": "r", "parameters": {"DES-TRK-001.parameters.x": 1}}]),
                     "not a free parameter")
        self.refused(spec_a(a, proposals=[{"id": "P", "reason": "r", "enabled": {"rich": True}}]), "names no slot")
        self.refused(spec_a(a, free_parameters=[], slots={}), "nothing to search")

    def test_non_uniform_per_layer_array_needs_sensor_genes(self):
        cand = json.loads((self.art / "candidates" / "cand-S.json").read_text(encoding="utf-8"))
        cand["extension"]["subsystems"]["DES-TRK-001"]["parameters"]["layer_x_over_x0"]["value"][0] = 0.02
        (self.art / "candidates" / "cand-S.json").write_text(json.dumps(cand, indent=1), encoding="utf-8")
        self.refused(spec_a(self.art), "differs between planes")


class RolesAndDecoding(unittest.TestCase):
    """C1.2, C1.3: the role rules (parameters, derived x/X0, budget models, calibration), decoding into overrides or an
    independent candidate, and the candidates passing validate_artifact and the design.py candidate checks."""

    @classmethod
    def setUpClass(cls):
        cls.roles = json.loads((ASSETS / "roles.json").read_text(encoding="utf-8"))
        cls.materials = json.loads((ASSETS / "materials.json").read_text(encoding="utf-8"))["materials"]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.art = example_a(Path(self.tmp.name) / "a")

    def tearDown(self):
        self.tmp.cleanup()

    def test_rules_cover_the_roles_and_tools(self):
        roles = self.roles["roles"]
        self.assertEqual(set(roles), {"tracking", "bending", "tof", "calorimetry-em", "rich"})
        from contracts.vocab import Vocabulary
        reads = set()
        for _c, _op, fd in design.Registry().designs():
            for role, name in _parameter_reads(fd["inputs"]):
                reads.add((role, name))
        for role, rule in roles.items():
            self.assertTrue(Vocabulary().has("subsystem_roles", role))
            self.assertTrue(rule["calibration"]["method"] and rule["calibration"]["control_samples"])
            names = set(rule["parameters"]) | set(rule.get("derived", {}))
            self.assertTrue({n for r, n in reads if r == role} & names, role)  # it feeds an F1 tool
            for name, p in rule["parameters"].items():
                if p["kind"] == "categorical":
                    if name.endswith("material"):
                        self.assertTrue(set(p["choices"]) <= set(self.materials))
                else:
                    self.assertLessEqual(p["range"][0], p["range"][1])
                    self.assertIn("tolerance", p)
            for k, v in rule.get("new_subsystem", {}).items():
                self.assertIn(k, rule["parameters"])
                d = rule["parameters"][k]
                if d["kind"] in ("continuous", "integer"):
                    self.assertTrue(d["range"][0] <= v <= d["range"][1], (role, k))
        for c, _op, fd in design.Registry().designs():
            for spec in _parameter_specs(fd["inputs"]):
                rule = roles.get(spec["role"], {})
                d = rule.get("parameters", {}).get(spec["name"]) or rule.get("derived", {}).get(spec["name"])
                if d is not None:
                    self.assertEqual(d["unit"], spec["unit"], (spec, c["tool_id"]))

    def new_slot_candidate(self, role: str) -> tuple[dict, dict, "EV.SearchSpace"]:
        spec = spec_a(self.art, free_parameters=[], slots={role: [0, 1]}, regenerate_budgets=[])
        space = space_for(self.art, spec)
        prop = {"id": "P", "reason": "r", "enabled": {role: True}}
        g, _ = space.repair(space.proposal_genome(prop))
        ext, facts = space.decode(g, "search SEARCH-T point 0", f"{NS_A}:cand-new")
        return ext, facts, space

    def write_and_check(self, ext: dict, name: str) -> dict:
        doc = EV.envelope("design-candidate", f"{NS_A}-{name}", dict(ext, candidate_id=f"{NS_A}:{name}"), [], [],
                          ["synthetic"])
        rep = validate_artifact(doc)
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors])
        (self.art / "candidates" / f"{name}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
        proj = design.Project(self.art)
        design.check_calibration(proj)
        design.check_budgets(proj)
        self.assertEqual([e for e in proj.errors if name in e["path"]], [])
        return doc

    def test_each_role_decodes_with_calibration_and_budget_rows(self):
        expect = {  # hand computation of each budget model at the role's new-subsystem values
            "tof": 2 * 1.0 * 1.0 * 0.01 * self.materials["G4_PLASTIC_SC_VINYLTOLUENE"]["density_g_cm3"] * 1000,
            "calorimetry-em": 1.0 * 20 * round(self.materials["G4_Pb"]["radiation_length_cm"] * 10 * (
                17.0 / 20 - 5.0 / (self.materials["G4_PLASTIC_SC_VINYLTOLUENE"]["radiation_length_cm"] * 10)), 3)
            * 1e-3 * self.materials["G4_Pb"]["density_g_cm3"] * 1000,
            "rich": 30.0, "bending": None, "tracking": None}
        for role in ("tof", "calorimetry-em", "rich"):
            with self.subTest(role=role):
                ext, facts, space = self.new_slot_candidate(role)
                sid = next(s for s in ext["overrides"] if s not in ("DES-TRK-001", "DES-MAG-001"))
                sub = ext["overrides"][sid]
                rule = self.roles["roles"][role]
                self.assertEqual(sub["role"], role)
                self.assertEqual(set(sub["parameters"]), set(rule["parameters"]) | set(rule.get("derived", {})))
                for name, p in sub["parameters"].items():
                    self.assertEqual(p["unit"], (rule["parameters"].get(name) or rule["derived"][name])["unit"])
                    self.assertEqual((p["source"], p["status"]), ("search SEARCH-T point 0", "proposal"))
                self.assertEqual(sub["calibration"], rule["calibration"])
                rows = {q: ext["budgets"][q][sid] for q in ("mass", "power", "channel_count", "data_rate")}
                self.assertAlmostEqual(rows["mass"]["estimate"], expect[role], places=9)
                for row in rows.values():
                    self.assertEqual(row["basis"], "estimate")
                    self.assertIn(rule["budget_model"]["name"], row["source"])
                    self.assertAlmostEqual(row["uncertainty"], 0.25 * row["estimate"])
                self.write_and_check(ext, f"cand-{role}")

    def test_earlier_rules_version_still_decodes(self):
        """A recorded search names the rules it ran with: 1.0.0 is kept as roles-1.0.0.json (its TOF and calorimeter
        in the F1 tools' names), so expand --search of such a search still finds the same bytes."""
        doc, digest = EV.load_asset("roles.json", "rules_version", "1.0.0")
        self.assertEqual(digest, sha(ASSETS / "roles-1.0.0.json"))
        self.assertIn("n_layers", doc["roles"]["tof"]["parameters"])
        space = space_for(self.art, spec_a(self.art, free_parameters=[], regenerate_budgets=[], rules_version="1.0.0",
                                           slots={"tof": [0, 1], "calorimetry-em": [0, 1]}))
        g, _ = space.repair(space.proposal_genome({"id": "P", "reason": "r", "enabled": {"tof": True,
                                                                                     "calorimetry-em": True}}))
        ext, _ = space.decode(g, "s", f"{NS_A}:x")
        tof = ext["overrides"]["DES-TOF-S01"]
        self.assertEqual(set(tof["parameters"]), {"n_layers", "time_resolution_ps", "scintillator_thickness_cm", "path_m"})
        self.assertAlmostEqual(ext["budgets"]["mass"]["DES-TOF-S01"]["estimate"], 2 * 1.0 * 0.01 * self.materials[
            "G4_PLASTIC_SC_VINYLTOLUENE"]["density_g_cm3"] * 1000)
        self.assertIn("depth_X0", ext["overrides"]["DES-ECAL-S01"]["parameters"])
        with self.assertRaises(EV.UsageError):
            EV.load_asset("roles.json", "rules_version", "0.9.0")

    def test_tracking_x_over_x0_from_material_and_thickness(self):
        spec = spec_a(self.art, free_parameters=[
            {"ref": "DES-TRK-001.parameters.layer_positions_m", "kind": "positions", "n": [4, 9],
             "range": [0.0, 2.0], "min_spacing_m": 0.05},
            {"ref": "DES-TRK-001.parameters.sensor_thickness_um", "range": [100.0, 500.0]}], slots={})
        space = space_for(self.art, spec)
        g, _ = space.repair(space.proposal_genome({"id": "P", "reason": "r", "parameters": {
            "DES-TRK-001.parameters.sensor_thickness_um": 200.0,
            "DES-TRK-001.parameters.layer_positions_m": [0.0, 0.5, 1.0, 1.5, 2.0]}}))
        ext, facts = space.decode(g, "s", f"{NS_A}:x")
        pars = ext["overrides"]["DES-TRK-001"]["parameters"]
        x0 = self.materials["G4_Si"]["radiation_length_cm"]
        self.assertEqual(pars["layer_x_over_x0"]["value"], [200e-4 / x0] * 5)
        self.assertEqual(pars["layer_positions_m"]["value"], [0.0, 0.5, 1.0, 1.5, 2.0])
        self.assertIn("[N=5]", facts["topology"])
        self.write_and_check(ext, "cand-thin")

    def test_uniform_per_layer_array_follows_the_plane_count(self):
        space = space_for(self.art, spec_a(self.art, slots={}))
        g, _ = space.repair(space.proposal_genome({"id": "P", "reason": "r", "parameters": {
            "DES-TRK-001.parameters.layer_positions_m": [0.0, 1.0, 2.0, 1.5]}}))
        ext, _ = space.decode(g, "s", f"{NS_A}:x")
        self.assertEqual(ext["overrides"]["DES-TRK-001"]["parameters"]["layer_x_over_x0"]["value"], [0.01] * 4)

    def test_regenerated_budget_rows(self):
        space = space_for(self.art, spec_a(self.art, slots={}))
        g, _ = space.repair(space.proposal_genome({"id": "P", "reason": "r", "parameters": {
            "DES-MAG-001.parameters.field_T": 0.5}}))
        ext, _ = space.decode(g, "s", f"{NS_A}:x")
        self.assertAlmostEqual(ext["budgets"]["mass"]["DES-MAG-001"]["estimate"], 14000.0 * 0.5)
        n = len(ext["overrides"].get("DES-TRK-001", {}).get("parameters", {}).get("layer_positions_m", {}).get(
            "value", [0] * 9))
        si = self.materials["G4_Si"]["density_g_cm3"] * 1000
        self.assertAlmostEqual(ext["budgets"]["mass"]["DES-TRK-001"]["estimate"], n * 1.0 * 300e-6 * si * 2.0)
        self.write_and_check(ext, "cand-regen")

    def test_dropping_a_subsystem_gives_an_independent_candidate(self):
        """Section C.4.5: deep_merge cannot remove, so a topology without a base subsystem is an independent copy."""
        cand = json.loads((self.art / "candidates" / "cand-S.json").read_text(encoding="utf-8"))
        ext0, _, _ = self.new_slot_candidate("tof")
        cand["extension"]["subsystems"]["DES-TOF-001"] = ext0["overrides"]["DES-TOF-S01"]
        for q in ext0["budgets"]:
            cand["extension"]["budgets"][q]["DES-TOF-001"] = ext0["budgets"][q]["DES-TOF-S01"]
        (self.art / "candidates" / "cand-S.json").write_text(json.dumps(cand, indent=1), encoding="utf-8")
        space = space_for(self.art, spec_a(self.art, slots={"tof": [0, 1]}))
        g, _ = space.repair(space.proposal_genome({"id": "P", "reason": "r", "enabled": {"tof": False}}))
        ext, facts = space.decode(g, "search SEARCH-T point 0", f"{NS_A}:x")
        self.assertNotIn("derived_from", ext)
        self.assertNotIn("overrides", ext)
        self.assertEqual(sorted(ext["subsystems"]), ["DES-MAG-001", "DES-TRK-001"])
        self.assertTrue(all("DES-TOF-001" not in rows for rows in ext["budgets"].values()))
        self.assertIn("without DES-TOF-001", ext["description"])
        self.assertEqual(facts["dropped"], ["DES-TOF-001"])
        self.write_and_check(ext, "cand-drop")
        g2, _ = space.repair(space.proposal_genome({"id": "P", "reason": "r", "enabled": {"tof": True}}))
        ext2, _ = space.decode(g2, "s", f"{NS_A}:y")
        self.assertEqual(ext2["derived_from"], f"{NS_A}:cand-S")


class Validity(unittest.TestCase):
    """C1.3, C1.10: every kind of invalid design (range, spacing, envelope, overlap, nesting) gives its reason and a
    positive violation, and is not evaluated."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.art = example_a(Path(self.tmp.name) / "a")

    def tearDown(self):
        self.tmp.cleanup()

    def test_range_is_repaired_with_a_reason(self):
        space = space_for(self.art, spec_a(self.art))
        g, notes = space.repair(space.proposal_genome({"id": "P", "reason": "r", "parameters": {
            "DES-MAG-001.parameters.field_T": 5.0}}))
        self.assertTrue(any(n.startswith("range: DES-MAG-001.parameters.field_T clipped to 1.0") for n in notes))
        self.assertEqual(space.values(g)["DES-MAG-001"]["params"]["field_T"], 1.0)

    def test_spacing_and_envelope(self):
        spec = spec_a(self.art, envelope={"length_m": 1.5})
        space = space_for(self.art, spec)
        g = space.proposal_genome({"id": "P", "reason": "r", "parameters": {
            "DES-TRK-001.parameters.layer_positions_m": [0.0, 0.01, 1.0, 2.0]}})
        _, facts = space.decode(g, "s", f"{NS_A}:x")  # unrepaired: too close, and outside the 1.5 m envelope
        v, why = space.violation(facts)
        self.assertGreater(v, 0)
        self.assertTrue(any(w.startswith("spacing:") for w in why))
        self.assertTrue(any(w.startswith("envelope:") for w in why))
        g2, _ = space.repair(g)  # repair pushes the planes apart; the envelope violation remains
        _, facts2 = space.decode(g2, "s", f"{NS_A}:x")
        v2, why2 = space.violation(facts2)
        self.assertFalse(any(w.startswith("spacing:") for w in why2))
        self.assertTrue(any(w.startswith("envelope:") for w in why2))
        self.assertAlmostEqual(v2, 0.5 / 1.5)

    def test_overlap_and_nesting(self):
        spec = spec_a(self.art, free_parameters=[], slots={"calorimetry-em": [0, 1], "rich": [0, 1]},
                      regenerate_budgets=[])
        space = space_for(self.art, spec)
        prop = {"id": "P", "reason": "r", "enabled": {"calorimetry-em": True, "rich": True},
                "parameters": {"DES-ECAL-S01.parameters.front_position_m": 2.0,
                               "DES-RICH-S01.parameters.z_front_m": 2.1}}
        g, _ = space.repair(space.proposal_genome(prop))
        _, facts = space.decode(g, "s", f"{NS_A}:x")
        v, why = space.violation(facts)
        self.assertGreater(v, 0)
        self.assertTrue(any(w.startswith("overlap: DES-ECAL-S01 and DES-RICH-S01") for w in why))
        prop["parent"] = {"DES-RICH-S01": "DES-ECAL-S01", "DES-ECAL-S01": "DES-MAG-001"}
        g, _ = space.repair(space.proposal_genome(prop))
        _, facts = space.decode(g, "s", f"{NS_A}:x")
        v, why = space.violation(facts)
        self.assertTrue(any(w.startswith("nesting: DES-RICH-S01") for w in why))
        self.assertFalse(any(w.startswith("overlap:") for w in why))  # a daughter may sit inside its mother
        prop["parent"] = {"DES-RICH-S01": "DES-ECAL-S01"}
        g, _ = space.repair(space.proposal_genome(prop))
        ext, facts = space.decode(g, "s", f"{NS_A}:x")
        self.assertEqual(space.violation(facts)[0], 0.0)
        self.assertEqual(ext["overrides"]["DES-RICH-S01"]["interfaces"], ["DES-ECAL-S01"])

    def base_with_ecal_and_rich(self) -> None:
        """Put a calorimeter (front 2.9 m, 17 X0 of Pb) and a RICH (front 2.7 m, 3 cm radiator) into cand-S."""
        space = space_for(self.art, spec_a(self.art, free_parameters=[], regenerate_budgets=[],
                                           slots={"calorimetry-em": [0, 1], "rich": [0, 1]}))
        g, _ = space.repair(space.proposal_genome({"id": "P", "reason": "r", "enabled": {
            "calorimetry-em": True, "rich": True}}))
        ext, _ = space.decode(g, "s", f"{NS_A}:x")
        cand = json.loads((self.art / "candidates" / "cand-S.json").read_text(encoding="utf-8"))
        for new, sid, z in (("DES-ECAL-001", "DES-ECAL-S01", 2.9), ("DES-RICH-001", "DES-RICH-S01", 2.7)):
            sub = ext["overrides"][sid]
            sub["parameters"]["front_position_m" if new == "DES-ECAL-001" else "z_front_m"]["value"] = z
            cand["extension"]["subsystems"][new] = sub
            for q in ext["budgets"]:
                cand["extension"]["budgets"][q][new] = ext["budgets"][q][sid]
        (self.art / "candidates" / "cand-S.json").write_text(json.dumps(cand, indent=1), encoding="utf-8")

    def base_extent_violation(self, free: list[str], values: dict) -> tuple[float, list[str]]:
        self.base_with_ecal_and_rich()
        fps = [{"ref": f"{sid}.parameters.{name}", "range": rng} for sid, name, rng in free]
        space = space_for(self.art, spec_a(self.art, free_parameters=fps, slots={}, regenerate_budgets=[],
                                           envelope={"length_m": 3.0}))
        g = space.proposal_genome({"id": "P", "reason": "r", "parameters": values})
        _, facts = space.decode(g, "s", f"{NS_A}:x")
        return space.violation(facts)

    def expected_base_extent_violation(self, v: float, why: list[str]) -> None:
        mats = json.loads((ASSETS / "materials.json").read_text(encoding="utf-8"))["materials"]
        x0p, x0a = (mats[m]["radiation_length_cm"] * 10 for m in ("G4_Pb", "G4_PLASTIC_SC_VINYLTOLUENE"))
        tp = round(x0p * (17.0 / 20 - 5.0 / x0a), 3)  # the template's 20 layers with 5 mm of scintillator, 17 X0
        ecal = (2.9, 2.9 + 20 * (tp + 5.0) * 1e-3)
        rich = (2.7, 2.7 + 0.03 + 0.3)
        expect = (ecal[1] - 3.0) / 3.0 + (rich[1] - 3.0) / 3.0 + (rich[1] - ecal[0]) / 3.0
        self.assertIn("envelope: DES-ECAL-001 extends outside [0, 3.0] m", why)
        self.assertIn("envelope: DES-RICH-001 extends outside [0, 3.0] m", why)
        self.assertTrue(any(w.startswith("overlap: DES-ECAL-001 and DES-RICH-001") for w in why), why)
        self.assertAlmostEqual(v, expect)

    def test_base_slot_with_only_the_front_free(self):
        """A base calorimeter or RICH with only its front free takes the sampling structure and radiator from the
        base."""
        v, why = self.base_extent_violation(
            [("DES-ECAL-001", "front_position_m", [0.0, 20.0]), ("DES-RICH-001", "z_front_m", [0.0, 20.0])],
            {"DES-ECAL-001.parameters.front_position_m": 2.9, "DES-RICH-001.parameters.z_front_m": 2.7})
        self.expected_base_extent_violation(v, why)

    def test_base_slot_with_the_front_fixed(self):
        """A base calorimeter or RICH with depth_x0 or radiator_length_cm free and its front fixed is still checked
        for envelope and overlap, from the base front."""
        v, why = self.base_extent_violation(
            [("DES-ECAL-001", "depth_x0", [5.0, 30.0]), ("DES-RICH-001", "radiator_length_cm", [1.0, 200.0])],
            {"DES-ECAL-001.parameters.depth_x0": 17.0, "DES-RICH-001.parameters.radiator_length_cm": 3.0})
        self.expected_base_extent_violation(v, why)

    def test_parent_reset_when_the_mother_is_disabled(self):
        spec = spec_a(self.art, free_parameters=[], slots={"calorimetry-em": [0, 1], "rich": [0, 1]},
                      regenerate_budgets=[])
        space = space_for(self.art, spec)
        g = space.proposal_genome({"id": "P", "reason": "r", "enabled": {"rich": True, "calorimetry-em": False},
                                   "parent": {"DES-RICH-S01": "DES-ECAL-S01"}})
        g, _ = space.repair(g)
        self.assertIsNone(space.values(g)["DES-RICH-S01"]["parent"])

    def test_invalid_designs_are_not_evaluated(self):
        spec = spec_a(self.art, envelope={"length_m": 1.0}, budget={"evaluations": 30}, consistency_samples=0,
                      optimizer={"name": "nsga2", "population": 10, "generations": 2, "seed": 3}, proposals=[])
        rel = write_spec(self.art, spec)
        code, out = ev(self.art, "search", "--spec", rel, "--id", "SEARCH-ENV")
        self.assertEqual(code, 0, out)
        s = json.loads((self.art / "runs" / "SEARCH-ENV.computational-run.json").read_text(encoding="utf-8"))
        bad = [p for p in s["extension"]["search_summary"]["points"] if p.get("evaluated") is False]
        self.assertTrue(bad)
        for p in bad:
            self.assertGreater(p["violation"], 0)
            self.assertEqual(p["values"], {})
            self.assertTrue(any(r.startswith("envelope:") for r in p["reasons"]))


class Closure(unittest.TestCase):
    """C1.8: plane placement, structure choice and reproducibility (gate G-C1)."""

    def test_plane_placement(self):
        """N = 6, fixed lever arm, measurement term only, minimum spacing L/32: the searcher reaches A <= 47.66 x 1.01
        (section C Appendix A: equal spacing 66.96, best of the exhaustive 1/32 grid 47.66)."""
        with tempfile.TemporaryDirectory() as tmp:
            b = Builder(Path(tmp) / "p")
            b.spec(1)
            b.candidate("cand-S", {"DES-TRK-001": tracker_subsystem(6, 1.0, layer_x0=0.0, passive_x0=0.0),
                                   "DES-MAG-001": magnet_subsystem(1.0)}, None, description="equal spacing")
            self.assertAlmostEqual(curvature_factor([i / 5 for i in range(6)]), 66.964, places=3)
            spec = {"search_spec_version": 1,
                    "design_spec": {"path": "design-spec.v1.json", "sha256": sha(b.art / "design-spec.v1.json")},
                    "base_candidate": "spectrometer-demo:cand-S", "objectives": [{"requirement": "REQ-TRK-001"}],
                    "free_parameters": [{"ref": "DES-TRK-001.parameters.layer_positions_m", "kind": "positions",
                                         "n": [6, 6], "range": [0.0, 1.0], "min_spacing_m": 1 / 32}],
                    "rules_version": "1.1.0", "materials_version": "1.0.0", "budget": {"evaluations": 5000},
                    "optimizer": {"name": "nsga2", "population": 100, "generations": 49, "seed": 12345},
                    "finalists": {"max": 1}, "consistency_samples": 0}
            rel = write_spec(b.art, spec, "SEARCH-P")
            code, out = ev(b.art, "search", "--spec", rel, "--id", "SEARCH-P")
            self.assertEqual(code, 0, out)
            s = b.read("runs/SEARCH-P.computational-run.json")["extension"]["search_summary"]
            self.assertLessEqual(s["evaluated"]["F1"], 5000)
            fin = next(p for p in s["points"] if p["index"] == s["finalists"][0]["index"])
            pos = sorted(v for k, v in fin["genome"].items() if "[" in k)
            self.assertGreater(pos[-1] - pos[0], 1 - 1e-6)  # the planes span the whole lever arm
            self.assertTrue(all(b_ - a_ >= 1 / 32 - 1e-12 for a_, b_ in zip(pos, pos[1:])))
            a_found = curvature_factor(pos)
            self.assertLessEqual(a_found, 47.66 * 1.01)
            # the search value is the tool's: resolution proportional to sqrt(A) at fixed field, rigidity and sigma
            res = fin["values"]["REQ-TRK-001"]["value"]
            k = 0.299792458
            a_tool = (res * k * 1.0 / 1000.0) ** 2 * (pos[-1] - pos[0]) ** 4 / (10e-6) ** 2
            self.assertAlmostEqual(a_tool / a_found, 1.0, places=9)

    def test_structure_choice(self):
        """Example A's design-spec, a base candidate without the magnet, 0-1 bending slot: every feasible front design
        has the magnet and at least three planes, every design without field is infeasible, and the report's verdicts
        on the expanded finalists agree with their feasibility on search values."""
        with tempfile.TemporaryDirectory() as tmp:
            art = example_a(Path(tmp) / "a")
            cand = json.loads((art / "candidates" / "cand-S.json").read_text(encoding="utf-8"))
            ext = cand["extension"]
            ext["candidate_id"], cand["artifact_id"] = f"{NS_A}:cand-N", f"{NS_A}-cand-N"
            ext["description"] = "SYNTHETIC: the tracker of cand-S without its magnet"
            ext["subsystems"].pop("DES-MAG-001")
            ext["subsystems"]["DES-TRK-001"]["interfaces"] = []
            for rows in ext["budgets"].values():
                rows.pop("DES-MAG-001")
            (art / "candidates" / "cand-N.json").write_text(json.dumps(cand, indent=1), encoding="utf-8")
            spec = spec_a(art, base_candidate=f"{NS_A}:cand-N",
                          objectives=[{"requirement": "REQ-TRK-001"}, {"requirement": "CON-MASS-001"}],
                          constraints=[{"requirement": "REQ-TRK-001"}],
                          free_parameters=[{"ref": "DES-TRK-001.parameters.layer_positions_m", "kind": "positions",
                                            "n": [3, 9], "range": [0.0, 2.0], "min_spacing_m": 0.05}],
                          slots={"bending": {"range": [0, 1], "ids": ["DES-MAG-001"]}}, regenerate_budgets=[],
                          budget={"evaluations": 600}, proposals=[], consistency_samples=2,
                          optimizer={"name": "nsga2", "population": 40, "generations": 50, "seed": 7})
            rel = write_spec(art, spec, "SEARCH-S")
            code, out = ev(art, "search", "--spec", rel, "--id", "SEARCH-S")
            self.assertEqual(code, 0, out)
            run_rel = "runs/SEARCH-S.computational-run.json"
            s = json.loads((art / run_rel).read_text(encoding="utf-8"))["extension"]["search_summary"]
            pts = {p["index"]: p for p in s["points"]}
            no_field = [p for p in s["points"] if not p["genome"]["DES-MAG-001.enabled"]]
            self.assertTrue(no_field)
            self.assertTrue(all(p["violation"] > 0 for p in no_field))
            feasible_front = [pts[k] for k in s["front"] if pts[k]["violation"] == 0]
            self.assertTrue(feasible_front)
            for p in feasible_front:
                self.assertTrue(p["genome"]["DES-MAG-001.enabled"])
                self.assertGreaterEqual(p["genome"]["DES-TRK-001.parameters.layer_positions_m.n"], 3)
            for f in s["finalists"]:
                name = f"cand-F{f['index']}"
                code, o = ev(art, "expand", "--search", run_rel, "--point", f["index"], "--candidate-id", name)
                self.assertEqual(code, 0, o)
                code, o = ev(art, "run", "--candidate", f"{NS_A}:{name}", "--requirement", "REQ-TRK-001", "--id",
                             f"CALC-TRK-F{f['index']}")
                self.assertEqual(code, 0, o)
            d = design.derive(art)
            for f in s["finalists"]:
                row = next(m for item in d["requirements"] if item["id"].endswith("REQ-TRK-001")
                           for m in item["matrix"] if f"{NS_A}:cand-F{f['index']}" in m["candidates"])
                feasible = pts[f["index"]]["violation"] == 0
                self.assertEqual(row["result"] != "fail", feasible, (row, pts[f["index"]]))

    def test_reproducibility(self):
        """The same search spec and seed give a bit-identical search_summary (timestamps and timing excepted)."""
        out = []
        with tempfile.TemporaryDirectory() as tmp:
            for k in range(2):
                art = example_a(Path(tmp) / f"a{k}")
                rel = write_spec(art, spec_a(art, consistency_samples=1, inline_points_max=50))
                code, o = ev(art, "search", "--spec", rel, "--id", "SEARCH-R")
                self.assertEqual(code, 0, o)
                run = json.loads((art / "runs" / "SEARCH-R.computational-run.json").read_text(encoding="utf-8"))
                s = copy.deepcopy(run["extension"]["search_summary"])
                s.pop("timing")
                out.append((json.dumps(s, sort_keys=True),
                            (art / "runs" / "SEARCH-R.points.jsonl").read_bytes()))
                self.assertIn("points_file", s)  # more than inline_points_max: the points go to a JSON Lines file
                self.assertEqual(run["extension"]["output_hashes"]["runs/SEARCH-R.points.jsonl"],
                                 s["points_file"]["sha256"])
                self.assertTrue(validate_artifact(run, strict=True).ok)
        self.assertEqual(out[0], out[1])


class InProcessCalls(unittest.TestCase):
    """C1.4: the four tools take argv in main() (no change to --help), and the in-process values of every new role's F1
    tool equal run's."""

    def test_main_takes_argv(self):
        import inspect
        for name in ("multiple_scattering", "pid_separation_power", "cherenkov_angle", "calorimeter_resolution",
                     "tracker_resolution"):
            p = PLUGIN / "skills" / "hep-detector" / "scripts" / f"{name}.py"
            spec = importlib.util.spec_from_file_location(f"_t_{name}", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertIn("argv", inspect.signature(mod.main).parameters, name)

    def test_role_tools_in_process_equal_run(self):
        targets = {"tof": {"figure_of_merit": "pid-separation-power", "tool": "pid-separation-power:separation",
                           "denominator": {"momentum_GeV": 2.0, "species": "pion", "background_species": "kaon",
                                           "separation_convention": "single"}, "reference_point": 1.0},
                   "rich": {"figure_of_merit": "pid-separation-power", "tool": "cherenkov-angle:kinematics",
                            "denominator": {"momentum_GeV": 5.0, "species": "pion", "background_species": "kaon",
                                            "separation_convention": "single"}, "reference_point": 1.0},
                   "calorimetry-em": {"figure_of_merit": "calorimeter-energy-resolution",
                                      "denominator": {"energy_GeV": 10.0, "species": "electron"},
                                      "reference_point": 0.1}}
        for role, obj in targets.items():
            with self.subTest(role=role), tempfile.TemporaryDirectory() as tmp:
                art = example_a(Path(tmp) / "a")
                spec = spec_a(art, objectives=[obj], constraints=[], free_parameters=[],
                              slots={role: [1, 1]}, regenerate_budgets=[], proposals=[], budget={"evaluations": 12},
                              optimizer={"name": "nsga2", "population": 6, "generations": 1, "seed": 1},
                              consistency_samples=2)
                rel = write_spec(art, spec)
                code, out = ev(art, "search", "--spec", rel, "--id", "SEARCH-T")
                self.assertEqual(code, 0, out)
                c = json.loads((art / "runs" / "SEARCH-T.computational-run.json").read_text(encoding="utf-8"))[
                    "extension"]["search_summary"]["consistency"]
                self.assertGreaterEqual(c["checked"], 2)
                self.assertLessEqual(c["max_relative_difference"], 1e-12)


@unittest.skipUnless(os.environ.get("HEP_DESIGN_SEARCH_MATERIALS_DUMP"),
                     "set HEP_DESIGN_SEARCH_MATERIALS_DUMP to a Geant4 materials.json dump to check materials.json")
class MaterialsAgainstDump(unittest.TestCase):
    def test_materials_equal_the_dump(self):
        dump = {m["name"]: m for m in json.loads(Path(os.environ["HEP_DESIGN_SEARCH_MATERIALS_DUMP"]).read_text(
            encoding="utf-8"))["materials"]}
        mats = json.loads((ASSETS / "materials.json").read_text(encoding="utf-8"))["materials"]
        for name, m in mats.items():
            for key in ("density_g_cm3", "radiation_length_cm", "nuclear_interaction_length_cm"):
                self.assertEqual(m[key], dump[name][key], (name, key))


def _parameter_specs(expr):
    if isinstance(expr, dict):
        for k, v in expr.items():
            if k in ("parameter", "parameters_all") and isinstance(v, dict) and "name" in v:
                yield {"role": v.get("role", "*"), "name": v["name"], "unit": v["unit"]}
            else:
                yield from _parameter_specs(v)
    elif isinstance(expr, list):
        for x in expr:
            yield from _parameter_specs(x)


def _parameter_reads(inputs):
    return [(s["role"], s["name"]) for s in _parameter_specs(inputs)]


if __name__ == "__main__":
    unittest.main()
