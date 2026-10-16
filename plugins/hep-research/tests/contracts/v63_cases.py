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


def copy_case(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst / "bundle.json"


def deep(obj):
    return copy.deepcopy(obj)
