"""v6.3 D01 gap runs: characterization tests that pin today's behaviour of the known gaps. Each test names the work
package expected to flip it; until then it asserts the current behaviour so the gate stays green. Public and synthetic
inputs only (examples/ams-flux-ratio artifacts, the registry fixtures, throwaway campaigns in a temporary folder).
The cases built on the AMS example skip in the AMS-optional copy (tools/check_ams_optional.py), which removes it.
Nothing here changes core/partition: campaigns are synthetic ones these tests create."""
import contextlib
import copy
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import analysis_bundle as ab  # noqa: E402
from contracts import communication_project as cproj  # noqa: E402
from contracts.project import load_project  # noqa: E402
from contracts.registry import validate_registry  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

ART = ROOT / "examples" / "ams-flux-ratio" / "output" / "artifacts"
RECIPE = ROOT / "contracts" / "semantics" / "recipes" / "flux_from_counts.json"
TABLE = ROOT / "contracts" / "semantics" / "tables" / "differential_flux.json"
AMS = ROOT / "profiles" / "experiments" / "ams-02"
HAVE_AMS = (ART / "measurement_spec.json").is_file() and (AMS / "profile.json").is_file()
NEEDS_AMS = unittest.skipUnless(HAVE_AMS, "the AMS example or profile is not in this copy")
ANY_SPEC = ROOT / "contracts" / "fixtures" / "artifacts" / "valid" / "measurement_ratio.json"
INCOMPATIBLE = ROOT / "contracts" / "fixtures" / "registry" / "incompatible_version" / "profiles" / "experiments" / "a"
R4_KEYS = ("target_scope", "calibration_digest", "variation_id", "stage")
SPEC_ARTIFACTS = ("measurement_spec.json", "response_proton_synthetic-period-1.json",
                  "response_proton_synthetic-period-2.json", "response_helium_synthetic-period-1.json",
                  "response_helium_synthetic-period-2.json", "dataset_synthetic-period-1.json",
                  "dataset_synthetic-period-2.json")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ams_vocab() -> Vocabulary:
    return Vocabulary.with_profiles([load(AMS / "profile.json")])


def run(*args, cwd=ROOT) -> tuple[int, dict]:
    p = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=cwd)
    return p.returncode, json.loads(p.stdout)


def write_project(root: Path, profile_id: str, version: str, local: list[str] = ()) -> Path:
    cfg = {"schema_version": "1.0.0", "plugin_version": ">=0.11,<1.0",
           "experiments": [{"profile": profile_id, "version": version}]}
    if local:
        cfg["local_profile_paths"] = list(local)
    path = root / "hep-research.project.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    return path


def incompatible_project(tmp: Path) -> Path:
    """A project binding the registry fixture's incompatible_version profile as a local profile."""
    shutil.copytree(INCOMPATIBLE, tmp / "local-profiles" / "exp-a")
    return write_project(tmp, "experiment:fixture-exp-a", "1.0.0", ["local-profiles/exp-a"])


class Gap1UnknownR4Keys(unittest.TestCase):
    """Gap 1 (flipped by D05a, V36): spec corrections carrying the R4 key fields that recipe_semantics reads get
    measurement.unknown_key, because MEASUREMENT_KEYS['corrections'] lacks them."""

    @NEEDS_AMS
    def test_r4_fields_on_a_spec_correction_are_unknown_keys(self):
        spec = load(ART / "measurement_spec.json")
        spec["extension"]["corrections"][0].update(target_scope="species:proton/period:synthetic-period-1",
                                                   calibration_digest="none", variation_id="nominal",
                                                   stage="estimator")
        rep = validate_artifact(spec, ams_vocab(), strict=True)
        flagged = {f.path.rsplit(".", 1)[-1] for f in rep.findings
                   if f.code == "measurement.unknown_key" and f.severity == "warning"}
        self.assertEqual(flagged, set(R4_KEYS))

    def test_recipe_semantics_reads_the_same_fields(self):
        from contracts.recipe_semantics import KEY_FIELDS, upstream_instances
        self.assertEqual(KEY_FIELDS, R4_KEYS)
        key = dict(zip(R4_KEYS, ("species:proton", "none", "nominal", "estimator")))
        art = {"extension": {"corrections": [dict(effect_id="efficiency", **key)]}}
        self.assertEqual(upstream_instances(art), [("efficiency", key)])


class Gap2ReviewIgnoresLoadReport(unittest.TestCase):
    """Gap 2 (flipped by D03a): review_measurement_spec.py builds its vocabulary from load_project(...).profiles
    without checking the load report, so it proceeds with a profile the registry reports as incompatible."""

    def test_review_proceeds_with_an_incompatible_profile(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = incompatible_project(Path(td))
            proj = load_project(cfg)
            self.assertIn("profile.incompatible_version", {f.code for f in proj.report.errors})
            spec = Path(td) / "spec.json"
            shutil.copy(ANY_SPEC, spec)
            code, out = run(ROOT / "skills" / "hep-measurement" / "scripts" / "review_measurement_spec.py", spec,
                            "--profiles-from", cfg)
        self.assertNotEqual(code, 2, "today the incompatible profile is not a usage or input error")
        codes = {d["code"] for d in out["defects"]} | {w["code"] for w in out["warnings"]}
        self.assertNotIn("profile.incompatible_version", codes, "today the load report never reaches the review")


class Gap3IncompatibleProfilesKept(unittest.TestCase):
    """Gap 3 (flipped by D03a): the registry adds an error for an incompatible profile and still returns it as
    loaded; load_project binds it, and communication_project lists it with only a warning."""

    def test_registry_keeps_an_incompatible_profile(self):
        reg = INCOMPATIBLE.parents[1] / "registry.json"
        rep, loaded = validate_registry(reg)
        self.assertIn("profile.incompatible_version", {f.code for f in rep.errors})
        self.assertIn("experiment:fixture-exp-a", loaded)

    def test_load_project_binds_an_incompatible_profile(self):
        with tempfile.TemporaryDirectory() as td:
            proj = load_project(incompatible_project(Path(td)))
        self.assertFalse(proj.report.ok)
        self.assertEqual([p["id"] for p in proj.profiles], ["experiment:fixture-exp-a"])

    def test_communication_project_lists_it_with_a_warning_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            incompatible_project(root)
            (root / "record.json").write_text("{}", encoding="utf-8")
            ctx = cproj.resolve_context(root / "record.json", root)
        self.assertEqual(ctx["profiles"], ["experiment:fixture-exp-a"])
        sev = {f["code"]: f["severity"] for f in ctx["findings"]}
        self.assertEqual(sev.get("resolution.project_config_invalid"), "warning")


@NEEDS_AMS
class Gap4CrossArtifactError(unittest.TestCase):
    """Gap 4 (main G-M0 evidence; flipped by D06, V34): a cross-artifact contradiction that every existing check
    passes. The spec says migration is corrected by unfolding with the response, the response's intended use is
    unfolding and it includes migration, but the recipe (the data correction chain) has no unfold step and lists
    migration as not_applied. Each artifact is consistent alone; only the relation is wrong."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        for name in SPEC_ARTIFACTS:
            shutil.copy(ART / name, self.root / name)
        spec = load(self.root / "measurement_spec.json")
        mig = [c for c in spec["extension"]["corrections"] if c["category"] == "migration"]
        self.assertEqual(len(mig), 1)
        mig[0]["applied_in"] = "unfolding"
        (self.root / "measurement_spec.json").write_text(json.dumps(spec, indent=1), encoding="utf-8")
        (self.root / "recipe.json").write_bytes(RECIPE.read_bytes())
        (self.root / "table.json").write_bytes(TABLE.read_bytes())
        (self.root / "environment.lock").write_text("synthetic environment lock for a characterization test\n")
        self.cfg = write_project(self.root, "experiment:ams-02", load(AMS / "profile.json")["version"])

    def test_the_relation_is_contradictory(self):
        spec = load(self.root / "measurement_spec.json")
        recipe = load(self.root / "recipe.json")
        response = load(self.root / "response_proton_synthetic-period-1.json")["extension"]
        self.assertIn("unfolding", {c["applied_in"] for c in spec["extension"]["corrections"]})
        self.assertEqual((response["intended_use"], response["includes"]), ("unfolding", ["migration"]))
        self.assertIn("migration", {n["effect_id"] for n in recipe["not_applied"]})
        self.assertFalse({"unfold", "unfold_with_efficiency"} & {s["operator"] for s in recipe["steps"]})

    def test_l1_passes_every_artifact(self):
        for name in SPEC_ARTIFACTS:
            with self.subTest(artifact=name):
                code, out = run(ROOT / "contracts" / "validate.py", self.root / name, "--profiles-from", self.cfg)
                self.assertEqual(code, 0, out)
                self.assertFalse([f for f in out["findings"] if f["severity"] in ("error", "warning")])

    def test_l2_passes_the_recipe(self):
        code, out = run(ROOT / "contracts" / "recipe_semantics.py", self.root / "recipe.json",
                        "--table", self.root / "table.json")
        self.assertEqual((code, out["status"]), (0, "pass"), out)

    def test_bundle_verify_passes(self):
        items = [{"role": "measurement-spec", "id": "spec", "ref": "measurement_spec.json"},
                 {"role": "recipe", "id": "recipe", "ref": "recipe.json"},
                 {"role": "semantics-table", "id": "table", "ref": "table.json"},
                 {"role": "environment-lock", "id": "env", "ref": "environment.lock"}]
        # the bundle has no response role (analysis_bundle.ROLES): the response cannot even be a typed member
        self.assertNotIn("response", ab.ROLES)
        bundle = ab.freeze(self.root, "v63-gap4", items)
        (self.root / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
        code, out = run(ROOT / "contracts" / "analysis_bundle.py", "verify", self.root / "bundle.json",
                        "--root", self.root)
        self.assertEqual((code, out["status"]), (0, "identical"), out)


class Gap4bRepeatAcrossInstances(unittest.TestCase):
    """Gap 4b (flipped by D06, V21): the same effect on one path under two calibrations, split over two recipe
    instances. L2 catches it inside one recipe or through a keyed upstream record, but recipes carry no data-flow
    link, so two instances checked together each pass."""

    def keyed(self, calibration: str) -> dict:
        r = load(RECIPE)
        r["recipe_version"] = "1.1.0"
        key = {"target_scope": "species:proton/period:synthetic-period-1", "calibration_digest": calibration,
               "variation_id": "nominal", "stage": "estimator"}
        r["steps"][1]["effect_keys"] = {"exposure": key, "efficiency": key}
        return r

    def test_two_instances_each_pass(self):
        with tempfile.TemporaryDirectory() as td:
            paths = []
            for i, cal in enumerate(("a" * 64, "b" * 64)):
                p = Path(td) / f"instance{i}.json"
                p.write_text(json.dumps(self.keyed(cal)), encoding="utf-8")
                paths.append(p)
            code, out = run(ROOT / "contracts" / "recipe_semantics.py", *paths, "--table", TABLE)
        self.assertEqual((code, [r["status"] for r in out["recipes"]]), (0, ["pass", "pass"]), out)

    def test_l2_catches_it_only_when_the_first_application_is_recorded_upstream(self):
        from contracts import recipe_semantics as rs
        table = load(TABLE)
        first = self.keyed("a" * 64)["steps"][1]["effect_keys"]["efficiency"]
        upstream = [{"extension": {"corrections": [dict(effect_id="efficiency", **first)]}}]
        res = rs.check_recipe(self.keyed("b" * 64), {table["table_id"]: table}, upstream, contracts=[])
        self.assertIn("semantics.repeated_correction", {f["code"] for f in res["findings"]})


class Gap5ExecutionFacts(unittest.TestCase):
    """Gap 5 (observed for D05d, V62/V63): a campaign without collection records merges with only
    merge.provenance_unrecorded; the batch-partition example's submissions carry null bundle digests."""

    def test_campaign_without_collected_warns_only(self):
        from core.partition import campaign as cp
        from tests.core.partition_helpers import ScriptedExecutor, make_campaign
        with tempfile.TemporaryDirectory() as td:
            cdir, _, _ = make_campaign(Path(td))
            state = json.loads((cdir / "state.json").read_text())
            for k in ("campaign_uid", "collected"):
                state.pop(k)
            (cdir / "state.json").write_text(json.dumps(state))
            ex = ScriptedExecutor({})
            cp.submit(cdir, ex, {}, approved=True)
            self.assertTrue(cp.poll(cdir, ex)["complete"])
            cp.poll(cdir, ex)
            rep = cp.merge(cdir)
        self.assertEqual(rep["status"], "complete", rep)
        self.assertEqual([w["code"] for w in rep["provenance_warnings"]], ["merge.provenance_unrecorded"])

    def test_batch_example_submissions_have_null_bundle_digests(self):
        try:
            import numpy  # noqa: F401  (the example's worker needs it)
        except ImportError:
            self.skipTest("numpy is not installed")
        spec = importlib.util.spec_from_file_location("v63_batch_example", ROOT / "examples" / "batch-partition" / "run.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        manifest = mod.engine.make_manifest("synthetic-angular-histogram", mod.t21.N_ITEMS, mod.t21.CHUNK, mod.t21.SEED)
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            res = mod.campaign("slurm", Path(td), copy.deepcopy(manifest))
        execution = res["artifact"]["extension"]["environment"]["execution"]
        self.assertTrue(execution["bundles"])
        self.assertEqual(set(execution["bundles"].values()), {None})
        self.assertIsNotNone(execution["campaign_uid"])


if __name__ == "__main__":
    unittest.main()
