"""Plugin-wide CLI contract (F-04): exit codes 0-3 only, a JSON "status" on a refused input, and --status.

The contract is the hep-computing one (skills/hep-computing/SKILL.md), with the shared vocabulary in core/status.py:
1. No command-line tool exits with a code outside 0-3 (static scan of sys.exit/exit calls, and of integer returns of
   main/run and every function annotated "-> int" in a tool; plugin scripts, skill assets, adapter assets, profile
   scripts).
2. Pointed at a missing input (tests/skills/test_cli_robustness.py MISSING_FILE_ARGS), a tool prints one JSON object
   with a "status" key and exits 1, 2 or 3. Tools with a --json switch are run with it. Scripts outside this batch's
   scope (hep-theory, hep-computing, hep-ml) that do not do this yet are listed in JSON_STATUS_FOLLOW_UP; no script
   outside the list may fail. The list is not required to match exactly: some adapters stop earlier, with a JSON
   missing-dependency status, when an optional package is absent, so what fails depends on the environment.
3. Every hep-theory, hep-computing and hep-ml tool takes --status (the artifact label of its inputs, default
   unvalidated), or is listed in STATUS_FLAG_EXEMPT with the reason.
"""
import ast
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.status import EXIT_CODES  # noqa: E402
from tests.skills.test_cli_robustness import HC_CONTRACT, MISSING_FILE_ARGS  # noqa: E402


def _tools(patterns):
    out = []
    for pat in patterns:
        for p in glob.glob(str(ROOT / pat)):
            if "__main__" in Path(p).read_text(encoding="utf-8"):
                out.append(os.path.relpath(p, ROOT))
    return sorted(out)


TOOLS = _tools(["skills/*/scripts/*.py", "skills/*/assets/*.py", "adapters/*/assets/*.py",
                "profiles/*/*/scripts/*.py"])
SCOPED = re.compile(r"^skills/hep-(theory|computing|ml)/")

# rule 2, outside this batch's scope: (script, reason). Follow-up items of the upgrade plan; remove an entry when the
# script prints a JSON status on a refused input.
JSON_STATUS_FOLLOW_UP = {
    "adapters/crdb/assets/crdb_query.py": "adapter: argparse/text error on a missing input",
    "adapters/literature-lookup/assets/literature_lookup.py": "adapter: text error on a missing replay file",
    "adapters/pyhf-combine/assets/reproduce_published_likelihood.py": "adapter: text error once pyhf is installed",
    "adapters/root-uproot/assets/coffea_dijet_processor.py": "adapter: text error",
    "adapters/root-uproot/assets/pyroot_rdf_cutflow_analysis.py": "adapter: text error",
    "adapters/root-uproot/assets/pyroot_roofit_signal_background.py": "adapter: text error",
    "adapters/root-uproot/assets/root_to_parquet.py": "adapter: text error",
    "adapters/root-uproot/assets/uproot_awkward_analysis.py": "adapter: text error",
    "adapters/unbinned-fit/assets/unbinned_fit.py": "adapter: text error",
    "skills/hep-literature/scripts/build_lit_matrix.py": "hep-literature: text error",
    "skills/hep-writing/scripts/check_diagram_sources.py": "hep-writing: text error",
    "skills/hep-writing/scripts/check_manuscript.py": "hep-writing: text error",
    "skills/hep-measurement/scripts/check_systematic_variations.py": "hep-measurement: text error",
    "skills/hep-measurement/scripts/cr_spectrum_powerlaw_fit.py": "hep-measurement: text error",
    "skills/hep-measurement/scripts/make_yield_table.py": "hep-measurement: text error",
    "skills/hep-measurement/scripts/mask_blinded_bins.py": "hep-measurement: text error",
    "skills/hep-measurement/scripts/review_analysis_change.py": "hep-measurement: text error",
    "skills/hep-measurement/scripts/review_measurement_spec.py": "hep-measurement: text error",
    "skills/hep-measurement/scripts/systematics_table_tex.py": "hep-measurement: text error",
    "skills/hep-statistics/scripts/combine_measurements.py": "hep-statistics: text error",
}

# rule 3: hep-theory, hep-computing and hep-ml tools without --status, and why the label does not apply
STATUS_FLAG_EXEMPT = {
    "skills/hep-computing/scripts/audit_blinded_outputs.py": "audits files for blinded values; reports no result",
    "skills/hep-computing/scripts/audit_histograms.py": "checks the structure of a histogram bundle; no derived numbers",
    "skills/hep-computing/scripts/roofit_workspace_summary.py": "lists the contents of a workspace; no derived numbers",
    "skills/hep-computing/scripts/create_story_card.py": "writes a planning note",
    "skills/hep-computing/scripts/find_python.py": "chooses an interpreter",
    "skills/hep-computing/scripts/inspect_root_file.py": "lists the contents of a file; no derived numbers",
    "skills/hep-computing/scripts/lint_task.py": "checks a task description",
    "skills/hep-computing/scripts/local_partition.py": "runs and merges jobs; the label belongs to the job's outputs",
    "skills/hep-computing/scripts/make_synthetic_nanoaod.py": "its output is synthetic by construction",
    "skills/hep-computing/scripts/validate_agile_notes.py": "checks planning notes",
    "skills/hep-ml/assets/ddp_train_skeleton.py": "a training skeleton the user adapts; synthetic demo data",
    "skills/hep-ml/assets/lora_finetune.py": "a fine-tuning skeleton the user adapts; synthetic demo data",
    "skills/hep-ml/assets/set_classifier.py": "a model template with a synthetic smoke run",
    "skills/hep-ml/assets/transformer_classifier.py": "a model template with a synthetic smoke run",
    "skills/hep-ml/assets/vision_transfer.py": "a model template with a synthetic smoke run",
    "skills/hep-ml/scripts/benchmark_model.py": "times a synthetic model",
    "skills/hep-ml/scripts/check_dataset_contract.py": "checks a synthetic dataset contract",
    "skills/hep-ml/scripts/check_pytorch_env.py": "inspects the environment",
    "skills/hep-ml/scripts/estimate_compute_budget.py": "arithmetic on resource numbers",
    "skills/hep-ml/scripts/estimate_training_memory.py": "arithmetic on resource numbers",
    "skills/hep-ml/scripts/find_nan_batches.py": "debugs a synthetic dataset",
    "skills/hep-ml/scripts/inspect_checkpoint.py": "lists the contents of a checkpoint; no derived numbers",
    "skills/hep-ml/scripts/profile_dataloader.py": "times a synthetic data loader",
    "skills/hep-ml/scripts/serving_capacity.py": "arithmetic on resource numbers",
}

HAS_JSON_SWITCH = {f"skills/hep-computing/scripts/{name}" for name, cases in HC_CONTRACT.items()
                   if any("--json" in args for args, _ in cases)}


def _int_const(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _int_const(node.operand)
        return None if v is None else -v
    return None


def bad_exit_codes(path):
    """(line, code) of exit calls and integer returns of main-like functions with a code outside 0-3."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and node.args:
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            owner = getattr(f.value, "id", None) if isinstance(f, ast.Attribute) else None
            if name == "exit" and (owner in (None, "sys", "_sys", "os") or isinstance(f, ast.Name)):
                v = _int_const(node.args[0])
                if v is not None and v not in EXIT_CODES:
                    bad.append((node.lineno, v))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            returns_int = isinstance(node.returns, ast.Name) and node.returns.id == "int"
            if node.name in ("main", "run", "_main", "_run", "cli") or returns_int:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Return) and sub.value is not None:
                        v = _int_const(sub.value)
                        if v is not None and v not in EXIT_CODES and (node.name in ("main", "_main", "cli") or v >= 0):
                            bad.append((sub.lineno, v))
    return bad


def run(script, args, timeout=180):
    with tempfile.TemporaryDirectory() as cwd:
        return subprocess.run([sys.executable, "-I", str(ROOT / script), *args], capture_output=True, text=True,
                              timeout=timeout, cwd=cwd)


def refused_input_violation(script):
    """None when a missing input gives one JSON object with a status and exit 1-3, else the reason."""
    args = list(MISSING_FILE_ARGS[script]) + (["--json"] if script in HAS_JSON_SWITCH else [])
    res = run(script, args)
    if res.returncode not in (1, 2, 3):
        return f"exit {res.returncode}"
    try:
        doc = json.loads(res.stdout)
    except ValueError:
        return f"stdout is not JSON: {(res.stdout + res.stderr).strip()[-160:]!r}"
    if not isinstance(doc, dict) or "status" not in doc:
        return "JSON without a status key"
    return None


def has_status_flag(script):
    text = (ROOT / script).read_text(encoding="utf-8")
    return bool(re.search(r"""add_argument\(\s*['"]--status['"]""", text) or "add_status_argument(" in text)


class CliContract(unittest.TestCase):
    def test_exit_codes_are_0_to_3(self):
        found = {s: bad_exit_codes(ROOT / s) for s in TOOLS}
        self.assertEqual({s: b for s, b in found.items() if b}, {})

    def test_refused_input_prints_a_json_status(self):
        scripts = sorted(s for s in MISSING_FILE_ARGS if s in TOOLS)
        violations = {s: v for s in scripts if (v := refused_input_violation(s))}
        new = {s: v for s, v in violations.items() if s not in JSON_STATUS_FOLLOW_UP}
        self.assertEqual(new, {}, json.dumps(new, indent=1))
        self.assertFalse([s for s in JSON_STATUS_FOLLOW_UP if SCOPED.match(s)],
                         "theory, computing and ml scripts cannot be deferred")

    def test_scoped_tools_take_status(self):
        missing = [s for s in TOOLS if SCOPED.match(s) and s not in STATUS_FLAG_EXEMPT and not has_status_flag(s)]
        self.assertEqual(missing, [])
        stale = [s for s in STATUS_FLAG_EXEMPT if s not in TOOLS or has_status_flag(s)]
        self.assertEqual(stale, [], "remove exemptions for tools that no longer exist or now take --status")


if __name__ == "__main__":
    unittest.main()
