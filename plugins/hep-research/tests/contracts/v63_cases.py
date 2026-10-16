"""v6.3 D08 case builders: CASE-CHAIN from the public examples/ams-flux-ratio artifacts and the recipe
contracts/semantics/recipes/flux_from_counts.json, and a reduced synthetic positive case (O12). Each builder writes a
project folder, lets a variant edit the draft (files, items, context) and freezes a v2 bundle with
contracts.analysis_check.freeze. Public and synthetic content only; nothing is written outside the given folder."""
from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ART = ROOT / "examples" / "ams-flux-ratio" / "output" / "artifacts"
RECIPE = ROOT / "contracts" / "semantics" / "recipes" / "flux_from_counts.json"
TABLE = ROOT / "contracts" / "semantics" / "tables" / "differential_flux.json"
HAVE_AMS = (ART / "measurement_spec.json").is_file()
SPECIES = ("proton", "helium")
PERIODS = ("synthetic-period-1", "synthetic-period-2")
SHORT = {"synthetic-period-1": "p1", "synthetic-period-2": "p2"}
AGENT = {"kind": "agent", "id": "claude-code"}
CAP = "measurement:correction-keys-v1"


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


class Case:
    """A draft before freezing: files (ref -> dict or str), items ([{role, id, ref}]), context (draft, no obligations)."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.files: dict[str, object] = {}
        self.items: list[dict] = []
        self.context: dict = {}

    def add(self, role: str, item_id: str, ref: str, content) -> None:
        self.files[ref] = content
        self.items.append({"role": role, "id": item_id, "ref": ref})

    def doc(self, item_id: str):
        ref = next(i["ref"] for i in self.items if i["id"] == item_id)
        return self.files[ref]

    def remove(self, item_id: str) -> None:
        ref = next(i["ref"] for i in self.items if i["id"] == item_id)
        self.items = [i for i in self.items if i["id"] != item_id]
        self.files.pop(ref)

    def write(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for ref, content in self.files.items():
            p = self.root / ref
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content if isinstance(content, str) else json.dumps(content, indent=1), encoding="utf-8")

    def freeze(self, analysis: str = "v63-case") -> Path:
        from contracts import analysis_check as ac
        self.write()
        bundle = ac.freeze(self.root, analysis, self.items, self.context)
        out = self.root / "bundle.json"
        out.write_text(json.dumps(bundle, indent=1), encoding="utf-8")
        return out


def mapping(effects_to_instances: dict, author=AGENT) -> list[dict]:
    return [{"declaration_id": f"map-{eff}", "type": "instance_mapping", "asserted_by": dict(author),
             "basis": {"rationale": "the spec's corrections apply to every species and period of this analysis"},
             "content": {"correction": eff, "instances": list(insts)}} for eff, insts in effects_to_instances.items()]


def chain_case(root: Path, variant=None, freeze: bool = True):
    """CASE-CHAIN: one recipe template, four instances (2 species x 2 periods), four flux roots, the example's spec,
    responses and dataset records. The example's ratio root is outside the chain suite (ratio-subset, M2b)."""
    c = Case(root)
    c.add("measurement-spec", "spec", "artifacts/measurement_spec.json", load(ART / "measurement_spec.json"))
    c.add("recipe", "flux-from-counts", "recipes/flux_from_counts.json", load(RECIPE))
    c.add("semantics-table", "differential-flux", "tables/differential_flux.json", load(TABLE))
    c.add("environment-lock", "env", "environment.lock", "synthetic environment lock for a v6.3 test case\n")
    for s in SPECIES:
        for p in PERIODS:
            c.add("response", f"response-{s}-{SHORT[p]}", f"artifacts/response_{s}_{p}.json", load(ART / f"response_{s}_{p}.json"))
    for p in PERIODS:
        c.add("dataset-record", f"dataset-{SHORT[p]}", f"artifacts/dataset_{p}.json", load(ART / f"dataset_{p}.json"))
    insts = [f"{s}-{SHORT[p]}" for s in SPECIES for p in PERIODS]
    c.context = {
        "context_version": "1.0.0", "suite": {"id": "counting-chain", "version": "1.0.0"}, "spec": "spec",
        "scope_axes": {"species": list(SPECIES), "period": list(PERIODS)},
        "roots": [{"root_id": f"flux-{s}-{SHORT[p]}", "quantity": "differential_flux", "unit": "1/(m2 sr s GV)",
                   "binning": {"item": "spec", "pointer": "/extension/observable/variables/0/edges"},
                   "scope": f"species:{s}/period:{p}", "output": {"instance": f"{s}-{SHORT[p]}"}}
                  for s in SPECIES for p in PERIODS],
        "recipe_instances": [{"instance_id": f"{s}-{SHORT[p]}", "recipe": "flux-from-counts",
                              "scope": f"species:{s}/period:{p}", "variation": "nominal", "role": "nominal",
                              "nominal": None, "calibrations": {}} for s in SPECIES for p in PERIODS],
        "bindings": [],
        "declarations": mapping({c2["effect_id"]: insts for c2 in c.doc("spec")["extension"]["corrections"]}),
    }
    if variant:
        variant(c)
    return c.freeze("case-chain") if freeze else c


def positive_case(root: Path, variant=None, freeze: bool = True):
    """Reduced synthetic positive case (O12): one instance, explicit spec applicability (correction keys), a recipe
    whose every operation has defined coverage, no response; every obligation is decidable."""
    c = Case(root)
    spec = load(ART / "measurement_spec.json") if HAVE_AMS else load(ROOT / "contracts" / "fixtures" / "artifacts" /
                                                                       "valid" / "measurement_ratio.json")
    scope = "species:proton/period:synthetic-period-1"
    spec["required_capabilities"] = sorted(set(spec.get("required_capabilities", [])) | {CAP})
    spec["extension"]["corrections"] = [
        {"effect_id": "selection_efficiency", "category": "selection_efficiency", "applied_in": "estimator",
         "target_scope": scope, "variation_id": "nominal", "application_id": "efficiency"},
        {"effect_id": "acceptance", "category": "acceptance", "applied_in": "normalization", "factor_of": "exposure",
         "target_scope": scope, "variation_id": "nominal"}]
    c.add("measurement-spec", "spec", "spec.json", spec)
    recipe = load(RECIPE)
    recipe["recipe_id"] = "flux-reduced"
    recipe["steps"] = [{"step_id": "background", "operator": "subtract_background"},
                       {"step_id": "efficiency", "operator": "correct_efficiency"},
                       {"step_id": "exposure", "operator": "divide_exposure"},
                       {"step_id": "bin-width", "operator": "divide_bin_width"}]
    recipe["not_applied"] = [{"effect_id": "migration", "reason": "synthetic reduced case: identical true and "
                                                                  "reconstructed binning, no migration"}]
    c.add("recipe", "flux-reduced", "recipe.json", recipe)
    c.add("semantics-table", "differential-flux", "table.json", load(TABLE))
    c.add("environment-lock", "env", "environment.lock", "synthetic environment lock for a v6.3 test case\n")
    c.context = {
        "context_version": "1.0.0", "suite": {"id": "counting-chain", "version": "1.0.0"}, "spec": "spec",
        "scope_axes": {"species": ["proton"], "period": ["synthetic-period-1"]},
        "roots": [{"root_id": "flux-proton-p1", "quantity": "differential_flux", "unit": "1/(m2 sr s GV)",
                   "binning": {"item": "spec", "pointer": "/extension/observable/variables/0/edges"},
                   "scope": scope, "output": {"instance": "proton-p1"}}],
        "recipe_instances": [{"instance_id": "proton-p1", "recipe": "flux-reduced", "scope": scope,
                              "variation": "nominal", "role": "nominal", "nominal": None, "calibrations": {}}],
        "bindings": [], "declarations": []}
    if variant:
        variant(c)
    return c.freeze("case-positive") if freeze else c


def custom_table(c, table_id, extra_op, extra_cov, recipe_id="flux-reduced", drop_cov=()):
    """A bundle-supplied table and coverage contract for a synthetic operator (no plugin coverage exists for it)."""
    from contracts.effect_catalog import load_coverage
    from contracts.recipe_semantics import canonical_sha256
    table = copy.deepcopy(c.doc("differential-flux"))
    table["table_id"] = table_id
    if extra_op:
        table["operators"].append(extra_op)
    c.remove("differential-flux")
    c.add("semantics-table", table_id, f"{table_id}.json", table)
    c.doc(recipe_id)["semantics"] = {"table_id": table_id, "sha256": canonical_sha256(table)}
    cov = copy.deepcopy(load_coverage("differential-flux"))
    cov.update(table_id=table_id, table_sha256=canonical_sha256(table))
    cov["operators"] = [o for o in cov["operators"] if o["operator_id"] not in drop_cov]
    if extra_cov:
        cov["operators"].append(extra_cov)
    c.add("coverage-contract", f"{table_id}-coverage", f"{table_id}.coverage.json", cov)


def copy_case(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst / "bundle.json"


def deep(obj):
    return copy.deepcopy(obj)


def ratio_case(root: Path, variant=None, freeze: bool = True):
    """RATIO-FACTORS / RATIO-EVIDENCE (v6.3 M2b): two species in one period, each a reduced chain; a ratio root over
    the species axis; one calibration item that gives trigger efficiency as a common scalar and selection efficiency
    per species (different bins of one table); a validation record for the selection-efficiency independence claim."""
    c = positive_case(root, None, freeze=False)
    period = "synthetic-period-1"
    scopes = {s: f"species:{s}/period:{period}" for s in SPECIES}
    spec = c.doc("spec")
    spec["extension"]["corrections"] = [
        {"effect_id": "trigger_efficiency", "category": "trigger_efficiency", "applied_in": "estimator", "variation_id": "nominal"},
        {"effect_id": "selection_efficiency", "category": "selection_efficiency", "applied_in": "estimator", "variation_id": "nominal"}]
    spec["extension"]["ratio"] = {"numerator": "helium flux", "denominator": "proton flux", "cancellations": [
        {"effect": "trigger_efficiency", "treatment": "cancels", "correlation_model": "one per-period estimate divides both species"},
        {"effect": "selection_efficiency", "treatment": "independent", "correlation_model": "separate control samples per species"}]}
    cov_extra = None
    custom_table(c, "differential-flux-r", None, cov_extra, recipe_id="flux-reduced")
    cov = c.doc("differential-flux-r-coverage")
    op = next(o for o in cov["operators"] if o["operator_id"] == "correct_efficiency")
    op["class_coverage"]["efficiency"] = {"members": ["trigger_efficiency", "selection_efficiency"],
                                          "basis": "synthetic: the operator divides by trigger and selection efficiency"}
    edges = spec["extension"]["observable"]["variables"][0]["edges"]
    n = len(edges) - 1
    c.add("calibration", "eff-cal", "efficiency-calibration.json", {"factor_table_version": "1.0.0", "factors": {
        "trigger_efficiency": {"scalar": 0.97},
        "selection_efficiency": {"by_scope": {scopes["proton"]: [0.90 + 0.005 * k for k in range(n)],
                                              scopes["helium"]: [0.80 + 0.010 * k for k in range(n)]}}}})
    c.add("validation-record", "vr-selection", "validation-selection.json", {
        "validation_record_version": "1.0.0", "claim": {"effect": "selection_efficiency", "relation": "independent"},
        "subjects": [{"root": "flux-helium-p1", "version": "synthetic-1"}, {"root": "flux-proton-p1", "version": "synthetic-1"}],
        "method": "separate control samples per species; no shared events (synthetic)", "tolerance": "exact by construction",
        "scope": f"period:{period}"})
    insts = []
    c.context["scope_axes"] = {"species": list(SPECIES), "period": [period]}
    c.context["roots"], c.context["recipe_instances"] = [], []
    for s in SPECIES:
        iid = f"{s}-p1"
        insts.append(iid)
        c.context["recipe_instances"].append({"instance_id": iid, "recipe": "flux-reduced", "scope": scopes[s], "variation": "nominal",
                                              "role": "nominal", "nominal": None,
                                              "calibrations": {"trigger_efficiency": "eff-cal", "selection_efficiency": "eff-cal"}})
        c.context["roots"].append({"root_id": f"flux-{s}-p1", "quantity": "differential_flux", "unit": "1/(m2 sr s GV)",
                                   "binning": {"item": "spec", "pointer": "/extension/observable/variables/0/edges"},
                                   "scope": scopes[s], "output": {"instance": iid}})
    c.context["declarations"] = mapping({"trigger_efficiency": insts, "selection_efficiency": insts})
    c.context["suites"] = [{"id": "ratio-subset", "version": "1.0.0"}]
    c.context["ratio_roots"] = [{"root_id": "ratio-p1", "numerator": {"root": "flux-helium-p1"},
                                 "denominator": {"root": "flux-proton-p1"}, "over_axis": "species", "quantity": "ratio", "unit": "1"}]
    if variant:
        variant(c)
    return c.freeze("case-ratio") if freeze else c
