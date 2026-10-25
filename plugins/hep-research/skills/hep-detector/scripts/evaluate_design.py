#!/usr/bin/env python3
"""Run design evaluations from tool contracts and derive the design report (detector system design, ART-50..ART-56).

Purpose: the hep-detector side of the design loop in
<plugin root>/skills/hep-detector/references/system-design-workflow.md. The agent decides which evidence to produce;
this script produces it exactly as the tool contract states, and contracts/design.py, never this script or the agent,
decides compliance, maturity and staleness.

Subcommands:
- run: one design-evaluation of a candidate. The figure of merit and its denominator come from --requirement (the
  current design-spec) or from --figure-of-merit and --denominator KEY=VALUE. The tool contract operation that computes
  that figure of merit at --fidelity (default F1; --tool TOOL:OPERATION when several do) maps the candidate's
  parameters, the denominator and the upstream evaluations (--upstream, or the single compatible one in the
  artifacts_dir) to the tool's arguments through contracts/design.py (the same recomputation the verdict rules do,
  T-58); the tool runs, and its output file (outputs/), its computational-run (runs/: argv, script_sha256,
  versions.plugin_release, config files in input_manifest) and the evaluation (evaluations/) are written. fidelity,
  bound, parameter_refs, value and uncertainty are taken from the contract and the output, never from the caller.
  With no operation for that figure of merit and fidelity it writes a capability.unavailable evaluation (no value).
  The new evaluation is checked by contracts/design.py; on a design error nothing is kept. Candidate files are bound
  with binding "parameters" and the evaluation records parameter_digest (M2, TRC-04..TRC-08): it goes stale only when
  a parameter it read changes. --replace replaces an evaluation of the same id that design.py finds stale (with its
  run and output); --digest-only prints the parameters it would read and their digest without running (INC-02);
  --input-artifact binds another artifact the operation reads (the statistical-result of the expected-precision
  write-back, CHN-04).
- budget: run for the budget figure of merit of --quantity (mass, power, channel_count, data_rate) (CHN-10).
- response (M2, CHN-01): the F3 response-assembly evaluation of the resolution core (an upstream core evaluation,
  the candidate's alignment term and declared tail) and a parametrized response artifact (responses/, intended_use
  forward_folding) bound to it, for the measurement-spec and the Asimov fit of hep-statistics.
- geometry (M2, ART-33..ART-35): the geometry file of a Geant4 study generated from the candidate with the mapping
  table contracts/rules/design_geometry.json (the fields, the parameters read and their digest); sets the candidate's
  geometry_ref. f4 (ART-31, ART-32): an F4 evaluation from a study record (re-issued first by check_geant4_study.py
  label --upgrade with --label-spec/--label-benchmarks/--label-convergence, and the run records, reference records and
  variation table passed on with --label-run-record/--label-reference-record/--label-variations); value, statistical
  uncertainty and model envelope from the record; bound optimistic for resolution and confusion unless every tail
  source was simulated. A refused upgrade, or a validated-in-scope record without results.<fom>, is incomplete (exit 3)
  with the reasons; label's own exit 1, 2, 3 map to failed, rejected, incomplete.
- f5 (M3, FID-01, FID-06, FID-07): an F5 evaluation from a user-supplied dataset-record's design_measurement, bound
  to the dataset by hash and to the candidate by the digest of the measured configuration's parameters; it decides only
  after a human measurement-acceptance record approves the dataset and covers the candidate.
- calibration (CHN-16): a candidate's calibration residual (--residual SID.parameters.NAME, --mode scale or
  inverse-offset) through propagate_scale_distortion.py response over a spectrum model (--model) into binned yield
  shifts, up/down variations and covariance blocks (outputs/CAL-*.json and its computational-run with argv, script hash
  and the residual's parameter_digest); with --measurement-spec and --out-spec, a new measurement-spec version carries
  them as a shape systematic for the hep-statistics Asimov fit. A subsystem without a calibration control sample is
  refused.
- scan (M4, OQ-18, AGG-08): the figure of merit of one candidate over a grid of parameter values (--vary
  SID.parameters.NAME=V1,V2,..., repeatable), each point run exactly as run would in a scratch copy, stored as one
  summary computational-run (runs/SCAN-*.computational-run.json, scan_summary: the points and the local elasticities at
  the candidate's own values). No evaluation is written, the run is exempt from the orphan-run rule, and a point
  supports no verdict. Operations with required upstreams are not scanned.
- expand (M4): one scan point as a candidate derived from the scanned one (overrides of the scanned parameters), to be
  evaluated with run like any candidate; only expanded points enter comparison.
- search (C1, contracts 3.13.0 search_summary): automated candidate generation at F1 from a search spec
  (design-search-spec/1, --spec, in the artifacts_dir; contracts/schemas/design_search_spec.json): the genome of the
  base candidate's slots and free parameters within the role rules (assets/design-search/roles.json, materials.json),
  Sobol designs plus the designer's proposals (proposer llm), NSGA-II with constrained domination and the exact WFG
  hypervolume (design_search_lib/), F1 search values computed in this process by the tool contracts' tools with the
  arguments contracts/design.py recomputes (main(argv)), the non-binding search front and up to finalists.max
  finalists, and a consistency check of the finalists and a sample of points against run (relative difference at most
  1e-12). Stored as runs/SEARCH-*.computational-run.json (search_summary; large point sets in a .points.jsonl listed in
  output_hashes). It writes no candidate and no evaluation, no verdict and no ranking; the run is exempt from the
  orphan-run rule and an evaluation that names it is design.search_point_not_expanded. From C2 (contracts CV-C2,
  geant4 adapter 0.5.0), budget.geant4 > 0 with a geant4 block adds S2 (--geant4-work DIR, HEP_GEANT4_CONFIG): the
  top_k designs of distinct topologies are refined on Geant4 search values (design_search_lib/geant4_values.py: short
  element_sim and simreco runs, tail sources off, optimistic), each generation in one seed_group (paired comparison,
  gate G-C2a switches to independent seeds), one survivor per topology; the survivors are the finalists, every S is in
  search_summary.seeds.geant4_search, and the runs stay in the work folder. search --diagnose RUN writes
  runs/DIAG-*.computational-run.json (each expanded finalist's F1 and Geant4 search values minus its official
  evaluation; no evaluation, no verdict).
- expand --search (C1): one finalist of a search as a candidate, decoded from its genome as the search decoded it
  (overrides on the base candidate, or an independent candidate when a subsystem is dropped; the effective digest
  must equal the point's); other points are refused. Then run, budget and report as for any candidate; report lists
  each expanded finalist's search value minus its official evaluation (search_minus_official, a diagnostic).
- plan: the suggested next evaluations, per requirement and candidate, from the derived state (RES-04): missing
  evaluations, missing evidence for compliance, stale evaluations, missing gates. Suggestions only.
- report: the design report, a communication artifact derived by contracts/design.py (producer_skill hep-detector):
  gate flags first, the compliance matrix with used and skipped evaluations, maturity, missing evidence, proposed
  dispositions, orphan runs, screening, the comparison basis, ranking and Pareto front or their refusal
  (RPT-01..RPT-10), plus a Markdown
  rendering. --omit EVALUATION hides an evaluation from the rendering only: it stays in the aggregation and is listed
  as omitted (AGG-06, AGG-07). Verdicts are never written by hand.
Decision records live outside the artifacts_dir (--decisions). This script does not import adapters/geant4. The
envelopes' created date is SOURCE_DATE_EPOCH when that is set (reproducible reruns), else today.
Output JSON: status (ok, failed, rejected), status_label (--status of run and budget, else unvalidated), and the
subcommand's fields.
Exit codes: 0 ok; 1 the tool failed, gave no value, or the evaluation has a design error (nothing written); for search,
an in-process search value that differs from run beyond 1e-12 (nothing written); 2 invalid input or a missing file
(JSON with error on stdout).
Usage:
  evaluate_design.py run --artifacts DIR --candidate ID (--requirement ID | --figure-of-merit FOM [--denominator K=V ...])
      [--fidelity F1] [--tool TOOL:OP] [--upstream REL ...] [--input-artifact REL ...] [--id EVAL-ID] [--replace]
      [--digest-only] [--status LABEL]
  evaluate_design.py budget --artifacts DIR --candidate ID --quantity Q [--id EVAL-ID] [--status LABEL]
  evaluate_design.py response --artifacts DIR --candidate ID (--requirement ID | --denominator K=V ...) [--upstream REL]
      [--id EVAL-ID] [--replace] [--status LABEL]
  evaluate_design.py geometry --artifacts DIR --candidate ID --figure-of-merit FOM --denominator K=V ... --id STUDY-ID
  evaluate_design.py f4 --artifacts DIR --candidate ID (--requirement ID | --figure-of-merit FOM --denominator K=V ...)
      --study REL --id SIM-ID [--label-spec S --label-benchmarks B --label-convergence C [--label-project-root R]
      [--label-run-record REL ...] [--label-reference-record REL ...] [--label-variations REL]] [--status LABEL]
  evaluate_design.py f5 --artifacts DIR --candidate ID --dataset REL --id MEAS-ID
  evaluate_design.py calibration --artifacts DIR --candidate ID --residual SID.parameters.NAME --mode MODE --model REL
      --id CAL-ID [--measurement-spec REL --out-spec REL] [--status LABEL]
  evaluate_design.py scan --artifacts DIR --candidate ID --figure-of-merit FOM [--denominator K=V ...] [--fidelity F1]
      --vary SID.parameters.NAME=V1,V2,... [--vary ...] --id SCAN-ID [--max-points N] [--status LABEL]
  evaluate_design.py expand --artifacts DIR --scan REL --point K --candidate-id NAME
  evaluate_design.py search --artifacts DIR --spec REL --id SEARCH-ID [--max-evaluations N] [--status LABEL]
  evaluate_design.py expand --artifacts DIR --search REL --point K --candidate-id NAME
  evaluate_design.py plan --artifacts DIR [--decisions DIR]
  evaluate_design.py report --artifacts DIR [--decisions DIR] [--omit EVALUATION ...] [--name NAME]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
sys.path.insert(0, str(PLUGIN))
from contracts import CONTRACTS_VERSION, design  # noqa: E402
from contracts.identity import plugin_release  # noqa: E402
from contracts.validate import STICKY_STATUSES  # noqa: E402
from core.status import ARTIFACT_LABELS  # noqa: E402

BUDGET_FOMS = {"mass": "mass-budget", "power": "power-budget", "channel_count": "channel-count-budget",
               "data_rate": "data-rate-budget"}
TOOL_TIMEOUT_S = 600


class UsageError(ValueError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=1))
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plugin_version() -> str:
    return json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def token(v) -> str:
    return repr(float(v)) if isinstance(v, float) else str(v)


def parse_value(text: str):
    try:
        return float(text)
    except ValueError:
        return text


def created() -> str:
    """Today, or the date of SOURCE_DATE_EPOCH when set (reproducible reruns)."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch and epoch.isdigit():
        return datetime.datetime.fromtimestamp(int(epoch), datetime.UTC).date().isoformat()
    return datetime.date.today().isoformat()


def envelope(atype: str, aid: str, ext: dict, inputs: list, outputs: list, status: list[str]) -> dict:
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": aid, "artifact_type": atype,
            "objective": f"detector system design: {atype} written by evaluate_design.py",
            "versions": {"plugin": plugin_version(), "contracts": CONTRACTS_VERSION, "plugin_release": plugin_release()},
            "provenance": {"producer_skill": "hep-detector", "created": created()},
            "inputs": inputs, "outputs": outputs, "status": status, "unresolved_inputs": [], "extension": ext}


class Writer:
    """Files written by one subcommand, removed again when the evaluation fails its design check."""

    def __init__(self, proj: design.Project):
        self.proj, self.written = proj, []

    def write(self, rel: str, data: bytes) -> str:
        p = self.proj.root / rel
        if p.exists():
            raise UsageError(f"{rel} exists: choose another --id (evaluations are never overwritten)")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        self.written.append(p)
        return rel

    def json(self, rel: str, doc: dict) -> str:
        return self.write(rel, (json.dumps(doc, indent=1) + "\n").encode("utf-8"))

    def undo(self) -> None:
        for p in self.written:
            p.unlink(missing_ok=True)

    def input_ref(self, rel: str) -> dict:
        p = self.proj.root / rel
        doc = json.loads(p.read_text(encoding="utf-8"))
        out = {"ref": rel, "sha256": sha256(p), "artifact_type": doc["artifact_type"], "artifact_id": doc["artifact_id"]}
        sticky = [s for s in doc.get("status", []) if s in STICKY_STATUSES]
        if sticky:
            out["status"] = sticky
        return out


def statuses(inputs: list[dict], label: str) -> list[str]:
    sticky = sorted({s for i in inputs for s in i.get("status", [])} - {label})
    return [label] + sticky


def load_project(args) -> design.Project:
    if not args.artifacts.is_dir():
        raise UsageError(f"--artifacts {args.artifacts} is not a folder")
    proj = design.Project(args.artifacts, getattr(args, "decisions", None))
    design.analyze_evaluations(proj)
    return proj


def current_spec(proj: design.Project, decisions) -> dict:
    designs = {proj.docs[p]["extension"]["design_id"] for p in proj.specs}
    records = design.load_records(proj, sorted(designs)[0]) if designs else []
    cur, _ = design.current_spec(proj, records)
    if cur is None:
        raise UsageError("no design-spec in the artifacts_dir")
    return proj.docs[cur]


def choose_operation(proj: design.Project, fom: str, fidelity: str, tool: str | None):
    hits = [(c, op, fd) for c, op, fd in proj.registry.designs()
            if fd["id"] == fom and op["design"]["fidelity"] == fidelity
            and (tool is None or f"{c['tool_id']}:{op['operation_id']}" == tool)]
    if len(hits) > 1:
        raise UsageError(f"several operations compute {fom} at {fidelity}: name one with --tool "
                         f"({', '.join(c['tool_id'] + ':' + op['operation_id'] for c, op, _ in hits)})")
    return hits[0] if hits else None


def pick_upstreams(proj: design.Project, ev: design.Evaluation, fd: dict, given: list[str]) -> list[design.Evaluation]:
    if given:
        out = []
        for rel in given:
            e = proj.evals.get(proj.resolve(rel))
            if e is None:
                raise UsageError(f"--upstream {rel} is not a design-evaluation in the artifacts_dir")
            out.append(e)
        return out
    out = []
    for fom in fd.get("required_upstreams", []):
        cands = [e for e in proj.evals.values() if e.fom == fom and not e.errors and not e.stale
                 and not e.ext.get("unavailable") and design.compatible(e, ev)]
        if len(cands) == 1:
            out.append(cands[0])
        elif len(cands) > 1:
            raise UsageError(f"several compatible {fom} evaluations ({', '.join(e.rel for e in cands)}): name one "
                             "with --upstream")
    return out


def remove_stale(proj: design.Project, eid: str) -> list[str]:
    """--replace: an existing evaluation of this id may be replaced only when contracts/design.py finds it stale; its
    run, output and config files go with it."""
    rel = f"evaluations/{eid}.json"
    ev = proj.evals.get(proj.resolve(rel))
    if ev is None:
        return []
    if not ev.stale:
        raise UsageError(f"{rel} is not stale: only a stale evaluation is replaced (--replace)")
    gone = [rel]
    run_ref = ev.ext.get("run_ref")
    if run_ref:
        run = proj.docs.get(proj.resolve(run_ref)) or {}
        gone += [o.get("ref") for o in run.get("outputs") or [] if isinstance(o, dict) and o.get("ref")]
        gone += [m["path"] for m in (run.get("extension") or {}).get("input_manifest", [])
                 if isinstance(m, dict) and str(m.get("path", "")).startswith(f"configs/{eid}.")]
        gone.append(run_ref)
    for r in gone:
        (proj.root / r).unlink(missing_ok=True)
    return gone


def tool_arguments(op: dict, fd: dict, prep: design.Prepared, status: str, config_file) -> list[str]:
    """The tool's arguments after the script, from the inputs contracts/design.py recomputed (T-58): operation
    arguments, positionals, then options in the contract's order. config_file(name, content) stores a config-file
    input and returns its argv token. Shared by run and the in-process search values (C1.4), so both call the tool
    with the same arguments."""
    args_out: list[str] = list(fd.get("operation_args", []))
    by_input = {m["input"]: prep.expected[m["input"]] for m in fd["inputs"] if m["input"] in prep.expected}
    for pos in sorted(op["invocation"].get("positionals", []), key=lambda x: x["position"]):
        val = by_input.get(pos["input"])
        if isinstance(val, design.ConfigValue):
            args_out.append(config_file(pos["input"], dict(val)))
        elif val is not None:
            args_out.append(token(val))
    for o in op["invocation"]["options"]:
        name = o["input"]
        if name in by_input:
            val = by_input[name]
            if val is True:
                args_out.append(o["flag"])
            elif val is not False:
                args_out += [o["flag"]] + [token(x) for x in design.flat(val)]
        elif name == "status" and "status" in fd.get("free_inputs", []):
            args_out += [o["flag"], status]
    return args_out


def tool_result(fd: dict, prep: design.Prepared, den: dict, output):
    """(value, value path, derived bound, validity-domain reasons, uncertainty) of a tool output, as the verdict rules
    derive them (ART-40, CMB, FID-10)."""
    value, path = design.output_value(fd, den, output)
    own, _ = design.own_bound(fd, prep, den, output)
    bound = design.combine_bounds(own, prep.directions)
    domain = design.validity_reasons(fd, prep, den, output)
    return value, path, bound, domain, design.output_uncertainty(fd, output, value)


def run_evaluation(args, digest_only: bool = False) -> dict:
    proj = load_project(args)
    cpath = proj.candidates.get(args.candidate)
    if cpath is None:
        raise UsageError(f"no design-candidate {args.candidate!r} in the artifacts_dir")
    chain = proj.candidate_chain(args.candidate)
    if chain is None:
        raise UsageError(f"a base on the derived_from chain of {args.candidate} is missing")
    if args.requirement:
        spec = current_spec(proj, None)["extension"]
        req = next((r for r in spec["requirements"] + spec["constraints"]
                    if r["id"] == args.requirement or r["id"].endswith(":" + args.requirement)), None)
        if req is None:
            raise UsageError(f"no requirement or constraint {args.requirement!r} in the current design-spec")
        fom = req["quantity"]
        den = {k: v["value"] for k, v in req["denominator"].items()}
    else:
        if not args.figure_of_merit:
            raise UsageError("give --requirement or --figure-of-merit")
        fom = args.figure_of_merit
        den = {}
        for kv in args.denominator or []:
            k, sep, v = kv.partition("=")
            if not sep or not k:
                raise UsageError(f"--denominator {kv!r}: use KEY=VALUE")
            den[k] = parse_value(v)
    ns = args.candidate.split(":", 1)[0]
    short = args.candidate.split(":", 1)[1]
    hit = choose_operation(proj, fom, args.fidelity, args.tool)
    eid = args.id or f"{'EST' if hit is None else ('CALC' if args.fidelity == 'F1' else 'SIM')}-{fom}-{short}-{args.fidelity}"
    if not re.match(r"^(CALC|SIM|MEAS|EST)-[A-Za-z0-9][A-Za-z0-9._-]*$", eid):
        raise UsageError(f"--id {eid!r}: an evaluation id is CALC-, SIM-, MEAS- or EST- followed by letters, digits, '.', '_' "
                         "or '-' (ART-06)")
    replaced: list[str] = []
    if getattr(args, "replace", False) and not digest_only:
        replaced = remove_stale(proj, eid)
        if replaced:
            proj = load_project(args)
    w = Writer(proj)
    chain_rels = [proj.rel(p) for p in chain]
    # TRC-06 (M2): candidate files are bound by the digest of the parameters read
    base_inputs = [dict(w.input_ref(r), binding="parameters") for r in chain_rels]
    extra_rels = list(getattr(args, "input_artifact", None) or [])
    for r in extra_rels:
        if not (proj.root / r).is_file():
            raise UsageError(f"--input-artifact {r} is not a file in the artifacts_dir")
    extra_inputs = [w.input_ref(r) for r in extra_rels]
    ext: dict = {"evaluation_id": f"{ns}:{eid}", "candidate": args.candidate, "figure_of_merit": fom,
                 "denominator": den, "bound": "estimate", "fidelity": args.fidelity}
    if hit is None:  # ART-50, ART-63: no evaluator at this fidelity
        if digest_only:
            return {"status": "ok", "exit": 0, "evaluation": f"evaluations/{eid}.json", "capability": "unavailable",
                    "parameter_refs": [], "parameter_digest": proj.parameter_digest(args.candidate, [])}
        ext.update(unavailable=True, parameter_refs=[], parameter_digest=proj.parameter_digest(args.candidate, []))
        rel = w.json(f"evaluations/{eid}.json", envelope("design-evaluation", f"{ns}-{eid}", ext, base_inputs, [],
                                                          statuses(base_inputs, args.status)))
        return finish(w, rel, {"capability": "unavailable"})
    contract, op, fd = hit
    ev = design.Evaluation(proj.root / f"evaluations/{eid}.json", f"evaluations/{eid}.json",
                           {"extension": dict(ext, unit=fd["unit"]), "inputs": extra_inputs})
    ev.effective = proj.effective_digest(args.candidate)
    ev.upstreams = pick_upstreams(proj, ev, fd, args.upstream or [])
    prep = design.prepare(proj, ev, fd)
    if prep.errors or prep.invalid:
        raise UsageError("; ".join(prep.errors + prep.invalid))
    missing = [r for r in fd.get("required_upstreams", []) if r not in {u.fom for u in ev.upstreams}]
    if digest_only:  # INC-02: the skip key of a workflow step that runs this evaluation
        return {"status": "ok", "exit": 0, "evaluation": f"evaluations/{eid}.json",
                "tool": f"{contract['tool_id']}:{op['operation_id']}", "parameter_refs": sorted(prep.refs),
                "parameter_digest": proj.parameter_digest(args.candidate, prep.refs),
                "upstreams": [{"ref": u.rel, "sha256": proj.sha[u.path]} for u in ev.upstreams]}
    manifest = [{"path": r, "sha256": sha256(proj.root / r)} for r in chain_rels]

    def config_file(name: str, val: dict) -> str:
        rel = w.json(f"configs/{eid}.{name}.json", val)
        manifest.append({"path": rel, "sha256": sha256(proj.root / rel)})
        return rel
    # argv: interpreter, script, operation arguments, positionals, then options in the contract's order
    args_out = tool_arguments(op, fd, prep, args.status, config_file)
    argv = ["python3", contract["entry"], *args_out]
    proc = subprocess.run([sys.executable, "-B", str(PLUGIN / contract["entry"]), *args_out], capture_output=True,
                          cwd=str(proj.root), timeout=TOOL_TIMEOUT_S)
    try:
        output = json.loads(proc.stdout.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        output = None
    if proc.returncode != 0 or not isinstance(output, dict):
        w.undo()
        return {"status": "failed", "exit": 1, "error": f"{contract['entry']} exited {proc.returncode}",
                "tool_output": output, "stderr": proc.stderr.decode("utf-8", "replace")[-2000:]}
    value, path, bound, domain, unc = tool_result(fd, prep, den, output)
    if value is None:
        w.undo()
        return {"status": "failed", "exit": 1, "error": f"the tool gave no number at {path!r} for this denominator",
                "tool_output": output}
    out_rel = w.write(f"outputs/{eid}.json", proc.stdout)
    up_rels = [u.rel for u in ev.upstreams]
    run_inputs = base_inputs + [w.input_ref(r) for r in up_rels] + extra_inputs
    run_ext = {"input_manifest": manifest, "tools": [{"name": contract["tool_id"], "version": plugin_version()}],
               "commands": [" ".join(argv)],
               "environment": {"python": platform.python_version(), "platform": platform.platform(terse=True)},
               "seeds": {}, "tolerances": {}, "exit_status": proc.returncode,
               "output_hashes": {out_rel: sha256(proj.root / out_rel)}, "argv": argv,
               "script_sha256": {contract["entry"]: sha256(PLUGIN / contract["entry"])}}
    run_rel = w.json(f"runs/{eid}.computational-run.json",
                     envelope("computational-run", f"{ns}-{eid}-run", run_ext, run_inputs, [{"ref": out_rel}],
                              statuses(run_inputs, args.status)))
    ext.update(value=value, unit=fd["unit"], bound=bound if bound != "mixed" else "estimate", run_ref=run_rel,
               parameter_refs=sorted(prep.refs), parameter_digest=proj.parameter_digest(args.candidate, prep.refs),
               validity={"assumptions": list(fd.get("assumptions", [])), "in_domain": not domain},
               fidelity=op["design"]["fidelity"])
    if unc is not None:
        ext["uncertainty"] = unc
    ev_inputs = base_inputs + [w.input_ref(run_rel)] + [w.input_ref(r) for r in up_rels] + extra_inputs
    rel = w.json(f"evaluations/{eid}.json", envelope("design-evaluation", f"{ns}-{eid}", ext, ev_inputs, [],
                                                      statuses(ev_inputs, args.status)))
    notes = {"tool": f"{contract['tool_id']}:{op['operation_id']}", "value": value, "bound": ext["bound"],
             "replaced": replaced,
             "fidelity": ext["fidelity"], "outside_validity_domain": domain, "missing_upstreams": missing}
    if bound == "mixed":
        notes["bound_note"] = "the chain mixes optimistic and conservative bounds (bound.mixed, row 9)"
    return finish(w, rel, notes)


def finish(w: Writer, rel: str, notes: dict) -> dict:
    """Check the new evaluation with contracts/design.py; on a design error remove what was written."""
    proj = design.Project(w.proj.root, None)
    design.analyze_evaluations(proj)
    ev = proj.evals.get(proj.resolve(rel))
    errors = [{"code": c, "message": m} for c, m in (ev.errors if ev else [("design.malformed", "not readable")])]
    errors += [e for e in proj.errors if e["path"] == rel]
    if errors:
        w.undo()
        return {"status": "failed", "exit": 1, "error": "the evaluation fails its design check; nothing was kept",
                "design_errors": errors}
    return {"status": "ok", "exit": 0, "evaluation": rel, "files": [w.proj.rel(p) for p in w.written], **notes,
            "note": "verdicts come from contracts/design.py (evaluate_design.py report), never from this output"}


def response(args) -> dict:
    """CHN-01 (M2): the F3 response-assembly evaluation of the resolution core, and a parametrized response artifact
    (form parametrized, intended_use forward_folding) bound to it, for hep-measurement and hep-statistics; the tail is
    the candidate's declared assumption and the response inherits the evaluation's bound."""
    args.fidelity, args.tool, args.figure_of_merit = "F3", "design-estimates:response-assembly", "momentum-resolution-core"
    args.digest_only = False
    out = run_evaluation(args)
    if out.get("status") != "ok":
        return out
    proj = design.Project(args.artifacts, None)
    ev_rel = out["evaluation"]
    ev = json.loads((proj.root / ev_rel).read_text(encoding="utf-8"))
    ext = ev["extension"]
    run = json.loads((proj.root / ext["run_ref"]).read_text(encoding="utf-8"))
    out_ref = run["outputs"][0]["ref"]
    r = ext["denominator"].get("rigidity_GV")
    w = Writer(proj)
    inputs = [w.input_ref(ev_rel)]
    rext = {"form": "parametrized", "truth_axis": "not-applicable", "reco_axis": "not-applicable",
            "orientation": "rows_reco_cols_truth", "normalization": "unnormalized", "inefficiency": "outside_matrix",
            "acceptance": "outside_matrix", "includes": ["migration"], "intended_use": "forward_folding",
            "parametrization": {"variables": ["rigidity"], "function_ref": out_ref,
                                "validity_range": {"rigidity": [r, r]}},
            "conditions": f"design candidate {ext['candidate']} (evaluation {ext['evaluation_id']}); the tail fraction "
                          "and width are declared assumptions of the candidate, not measured",
            "provenance": f"assembled by design_estimates.py response-assembly from {ext['evaluation_id']}; bound "
                          f"{ext['bound']} (inherited from its chain); charge flip and rigidity migration are counted "
                          "once, inside the response (CHN-01)"}
    eid = ext["evaluation_id"].split(":", 1)[1]
    rel = w.json(f"responses/{eid}.response.json",
                 envelope("response", f"{ext['evaluation_id'].replace(':', '-')}-response", rext, inputs,
                          [{"ref": out_ref}], statuses(inputs, "unvalidated")))
    from contracts.validate import validate_artifact
    rep = validate_artifact(json.loads((proj.root / rel).read_text(encoding="utf-8")))
    if not rep.ok:
        w.undo()
        return {"status": "failed", "exit": 1, "error": "the response fails contract validation", "evaluation": ev_rel,
                "findings": [f.as_dict() for f in rep.errors]}
    out["response"] = rel
    return out


def geometry(args) -> dict:
    """ART-33, ART-34 (M2): the geometry file of a Geant4 study generated from the candidate with the mapping table
    (contracts/rules/design_geometry.json): the fields read, the parameters read and their digest, the figure of merit
    the study is for; the candidate's geometry_ref is set to it (ART-30). Like check_geant4_study.py it only reads and
    writes files; the study itself runs with the Geant4 adapter."""
    proj = load_project(args)
    if args.candidate not in proj.candidates:
        raise UsageError(f"no design-candidate {args.candidate!r} in the artifacts_dir")
    mapping = design.load_json(design.GEOMETRY_FILE)
    if args.figure_of_merit not in mapping["figures_of_merit"]:
        raise UsageError(f"the geometry mapping gives no {args.figure_of_merit!r} (it has "
                         f"{', '.join(sorted(mapping['figures_of_merit']))})")
    try:
        fields, refs, digest = design.geometry_fields(proj, args.candidate, mapping)
    except design.ExprError as exc:
        raise UsageError(f"geometry: {exc}") from exc
    den = dict((kv.partition("=")[0], parse_value(kv.partition("=")[2])) for kv in args.denominator or [])
    want = set(mapping["figures_of_merit"][args.figure_of_merit]["denominator"])
    if set(den) != want:
        raise UsageError(f"--denominator needs exactly {sorted(want)}")
    rel = f"studies/{args.id}.geometry.json"
    w = Writer(proj)
    w.json(rel, {"schema": "design-geometry/1", "mapping_version": mapping["mapping_version"],
                 "geometry": mapping["geometry"], "candidate": args.candidate, "figure_of_merit": args.figure_of_merit,
                 "denominator": den, "fields": fields, "parameter_refs": refs, "parameter_digest": digest,
                 "note": "generated by evaluate_design.py geometry; the Geant4 study must list this file in its "
                         "input_manifest and report results.<figure of merit> (value, statistical_uncertainty, "
                         "model_envelope) and tail_sources_simulated in its study block"})
    cpath = proj.candidates[args.candidate]
    cand = json.loads(cpath.read_text(encoding="utf-8"))
    cand["extension"]["geometry_ref"] = rel
    cpath.write_text(json.dumps(cand, indent=1) + "\n", encoding="utf-8")
    return {"status": "ok", "exit": 0, "geometry": rel, "candidate": proj.rel(cpath), "parameter_refs": refs,
            "parameter_digest": digest, "note": "the candidate's geometry_ref now names this file (ART-30)"}


def f4(args) -> dict:
    """ART-31, ART-32 (M2): an F4 evaluation from a Geant4 study record in the artifacts_dir; with --label-spec,
    --label-benchmarks and --label-convergence the record is first re-issued by check_geant4_study.py label
    --upgrade (run records, reference records and the variation table passed on unchanged). Value, statistical
    uncertainty and model envelope are the record's (CV-B2: the study's uncertainty object, coverage 0.90, when it has
    one; the evaluation names the geometry file the study used in geometry_ref; --label-results and --label-geometry
    are passed on to label as --results and --geometry); the bound follows FID-03. A1.17: label exits 0 when it wrote a
    record (granted or refused upgrade) and 2 on unusable input; its exit 1, 2, 3 map to failed, rejected,
    incomplete, and a refused upgrade or a validated record without results.<fom> is incomplete (exit 3)."""
    proj = load_project(args)
    if args.label_spec:
        cmd = [sys.executable, "-B", str(PLUGIN / "skills/hep-detector/scripts/check_geant4_study.py"), "label",
               "--spec", args.label_spec, "--benchmarks", args.label_benchmarks, "--convergence", args.label_convergence,
               "--project-root", str(args.label_project_root or proj.root), "--upgrade", "--write", str(proj.root / args.study)]
        for flag, values in (("--run-record", args.label_run_record), ("--reference-record", args.label_reference_record),
                             ("--variations", [args.label_variations] if args.label_variations else []),
                             ("--results", [args.label_results] if args.label_results else []),
                             ("--geometry", [args.label_geometry] if args.label_geometry else [])):
            for v in values or []:
                cmd += [flag, v]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TOOL_TIMEOUT_S)
        if p.returncode != 0:
            status = {1: "failed", 3: "incomplete"}.get(p.returncode, "rejected")
            return {"status": status, "exit": {"failed": 1, "incomplete": 3}.get(status, 2),
                    "error": f"check_geant4_study.py label --upgrade exited {p.returncode}",
                    "label_output": p.stdout[-3000:]}
        try:
            label_doc = json.loads(p.stdout)
        except ValueError:
            label_doc = {}
        upgrade = label_doc.get("upgrade")
        if upgrade != "re-issued as validated-in-scope":
            return {"status": "incomplete", "exit": 3, "reason": "upgrade-refused",
                    "refused": (upgrade or {}).get("refused") if isinstance(upgrade, dict) else upgrade,
                    "gaps": label_doc.get("gaps", []),
                    "note": "the study record was written unvalidated; an F4 evaluation needs a validated-in-scope "
                            "study (contracts/design.py check_f4)"}
        proj = load_project(args)
    study_path = proj.resolve(args.study)
    study = proj.docs.get(study_path)
    if study is None or study.get("artifact_type") != "computational-run":
        raise UsageError(f"--study {args.study} is not a computational-run in the artifacts_dir")
    chain = proj.candidate_chain(args.candidate)
    if chain is None:
        raise UsageError(f"no design-candidate {args.candidate!r} (or a base) in the artifacts_dir")
    if args.requirement:
        spec = current_spec(proj, None)["extension"]
        req = next((r for r in spec["requirements"] + spec["constraints"]
                    if r["id"] == args.requirement or r["id"].endswith(":" + args.requirement)), None)
        if req is None:
            raise UsageError(f"no requirement {args.requirement!r} in the current design-spec")
        fom, den = req["quantity"], {k: v["value"] for k, v in req["denominator"].items()}
    else:
        fom = args.figure_of_merit
        den = dict((kv.partition("=")[0], parse_value(kv.partition("=")[2])) for kv in args.denominator or [])
    block = (study.get("extension") or {}).get("study") or {}
    result = (block.get("results") or {}).get(fom)
    if not isinstance(result, dict) or not isinstance(result.get("value"), (int, float)):
        if "validated-in-scope" in (study.get("status") or []):
            return {"status": "incomplete", "exit": 3, "reason": "results-missing",
                    "note": f"the validated-in-scope study record reports no results.{fom}.value (ART-36): a study "
                            "that measures the figure of merit writes it (Geant4 program stage B2)"}
        raise UsageError(f"the study record reports no results.{fom}.value (ART-36)")
    mapping = design.load_json(design.GEOMETRY_FILE)
    fom_map = mapping["figures_of_merit"].get(fom) or {}
    tails = set(block.get("tail_sources_simulated") or [])
    bound = "optimistic" if fom_map.get("tail_sensitive") and not set(design.TAIL_SOURCES) <= tails else "estimate"
    _, refs, digest = design.geometry_fields(proj, args.candidate, mapping)
    ns, eid = args.candidate.split(":", 1)[0], args.id
    if not re.match(r"^SIM-[A-Za-z0-9][A-Za-z0-9._-]*$", eid):
        raise UsageError("--id of an F4 evaluation is SIM- followed by letters, digits, '.', '_' or '-'")
    w = Writer(proj)
    inputs = [dict(w.input_ref(proj.rel(p)), binding="parameters") for p in chain] + [w.input_ref(proj.rel(study_path))]
    ext = {"evaluation_id": f"{ns}:{eid}", "candidate": args.candidate, "figure_of_merit": fom, "denominator": den,
           "value": result["value"], "unit": fom_map.get("unit", "1"), "bound": bound, "fidelity": "F4",
           "study_ref": proj.rel(study_path), "parameter_refs": refs, "parameter_digest": digest}
    if isinstance(result.get("statistical_uncertainty"), (int, float)):
        s = float(result["statistical_uncertainty"])
        ext["uncertainty"] = {"minus": s, "plus": s, "coverage": 0.6827, "interval": "central", "distribution": "gaussian"}
    if isinstance(result.get("uncertainty"), dict):  # CV-B2: the study's uncertainty object (coverage 0.90, D0-c (a))
        ext["uncertainty"] = {k: result["uncertainty"][k] for k in ("minus", "plus", "coverage", "interval",
                                                                    "distribution")}
    geo = block.get("geometry") if isinstance(block.get("geometry"), dict) else None
    if geo and isinstance(geo.get("path"), str):  # CV-B2: the evaluation names the geometry file its study used
        ext["geometry_ref"] = geo["path"]
    if isinstance(result.get("model_envelope"), list):
        ext["model_envelope"] = result["model_envelope"]
    rel = w.json(f"evaluations/{eid}.json", envelope("design-evaluation", f"{ns}-{eid}", ext, inputs, [],
                                                      statuses(inputs, args.status)))
    return finish(w, rel, {"value": ext["value"], "bound": bound, "fidelity": "F4"})


def f5(args) -> dict:
    """FID-01 F5 (M3): an F5 evaluation from a user-supplied dataset-record's design_measurement (value, uncertainty,
    denominator, the configuration it was measured in). It is bound to the dataset by hash and to the candidate by the
    digest of the configuration parameters; it decides only after a human measurement-acceptance record approves the
    dataset (FID-06), and a configuration that differs from the candidate's is domain.mismatch (FID-07)."""
    proj = load_project(args)
    ds_path = proj.resolve(args.dataset)
    ds = proj.docs.get(ds_path)
    if ds is None or ds.get("artifact_type") != "dataset-record":
        raise UsageError(f"--dataset {args.dataset} is not a dataset-record in the artifacts_dir")
    dm = (ds.get("extension") or {}).get("design_measurement")
    if not isinstance(dm, dict):
        raise UsageError("the dataset-record has no extension.design_measurement")
    chain = proj.candidate_chain(args.candidate)
    if chain is None:
        raise UsageError(f"no design-candidate {args.candidate!r} (or a base) in the artifacts_dir")
    if not re.match(r"^MEAS-[A-Za-z0-9][A-Za-z0-9._-]*$", args.id):
        raise UsageError("--id of an F5 evaluation is MEAS- followed by letters, digits, '.', '_' or '-'")
    ns = args.candidate.split(":", 1)[0]
    refs = sorted(dm["configuration"])
    w = Writer(proj)
    inputs = [dict(w.input_ref(proj.rel(p)), binding="parameters") for p in chain] + [w.input_ref(proj.rel(ds_path))]
    rules = proj.fom_rules(dm["figure_of_merit"]) or {}
    design_unit = (proj.registry.fom_design(dm["figure_of_merit"]) or {}).get("unit", "1")
    ext = {"evaluation_id": f"{ns}:{args.id}", "candidate": args.candidate, "figure_of_merit": dm["figure_of_merit"],
           "denominator": dm["denominator"], "value": dm["value"], "unit": design_unit, "bound": "estimate",
           "fidelity": "F5", "uncertainty": dm["uncertainty"], "dataset_ref": proj.rel(ds_path),
           "parameter_refs": refs, "parameter_digest": proj.parameter_digest(args.candidate, refs)}
    rel = w.json(f"evaluations/{args.id}.json", envelope("design-evaluation", f"{ns}-{args.id}", ext, inputs, [],
                                                          statuses(inputs, "user-supplied")))
    out = finish(w, rel, {"value": dm["value"], "fidelity": "F5", "known_figure_of_merit": bool(rules)})
    if out.get("status") == "ok":
        out["note"] = ("decides only after a human measurement-acceptance record approves the dataset and covers the "
                       "candidate by the digest of its configuration parameters (FID-06, DEC-06)")
    return out


def parse_vary(proj: design.Project, cid: str, specs: list[str]) -> list[tuple[str, float, list[float]]]:
    """--vary SID.parameters.NAME=V1,V2,...: a numeric parameter of the merged candidate and the values to scan; the
    candidate's own value is always one of the points (the base of the sensitivities)."""
    subs = proj.effective(cid) or {}
    out = []
    for spec in specs:
        ref, sep, vals = spec.partition("=")
        sid, _, name = ref.partition(".parameters.")
        par = ((subs.get(sid) or {}).get("parameters") or {}).get(name) if name else None
        if not sep or par is None:
            raise UsageError(f"--vary {spec!r}: use SID.parameters.NAME=V1,V2,... with a parameter of {cid}")
        if isinstance(par.get("value"), bool) or not isinstance(par.get("value"), (int, float)):
            raise UsageError(f"--vary {ref}: only a numeric parameter can be scanned")
        try:
            values = [float(v) for v in vals.split(",") if v.strip()]
        except ValueError:
            raise UsageError(f"--vary {spec!r}: the values are numbers") from None
        base = float(par["value"])
        out.append((ref, base, sorted(set(values) | {base})))
    if len({r for r, _, _ in out}) != len(out):
        raise UsageError("--vary names a parameter twice")
    return out


def set_parameters(doc: dict, values: dict, proj: design.Project, cid: str, source: str) -> dict:
    """The candidate document with the scanned parameters set: in overrides for a variant, else in its subsystems."""
    doc = json.loads(json.dumps(doc))
    ext = doc["extension"]
    subs = proj.effective(cid) or {}
    for ref, v in values.items():
        sid, _, name = ref.partition(".parameters.")
        par = dict(subs[sid]["parameters"][name], value=v, source=source, status="proposal")
        if ext.get("derived_from"):
            ext.setdefault("overrides", {}).setdefault(sid, {}).setdefault("parameters", {})[name] = par
        else:
            ext["subsystems"][sid]["parameters"][name] = par
    return doc


def sensitivities(points: list[dict], axes: list[tuple[str, float, list[float]]]) -> list[dict]:
    """Local elasticities d ln(value) / d ln(parameter) at the candidate's own point, along each scanned axis with the
    other parameters at their own values: central difference from the two neighbours, one-sided at an end."""
    out = []
    base = {r: b for r, b, _ in axes}
    for ref, b, _ in axes:
        line = sorted((p for p in points if p.get("value") is not None
                       and all(p["parameters"][o] == base[o] for o in base if o != ref)),
                      key=lambda p: p["parameters"][ref])
        idx = next((i for i, p in enumerate(line) if p["parameters"][ref] == b), None)
        if idx is None or len(line) < 2 or b == 0 or line[idx]["value"] == 0:
            out.append({"parameter": ref, "base_value": b, "elasticity": None,
                        "reason": "needs the base point, a neighbour and non-zero base values"})
            continue
        lo, hi = line[max(idx - 1, 0)], line[min(idx + 1, len(line) - 1)]
        dp = (hi["parameters"][ref] - lo["parameters"][ref]) / b
        dv = (hi["value"] - lo["value"]) / line[idx]["value"]
        out.append({"parameter": ref, "base_value": b, "elasticity": dv / dp,
                    "points": [lo["index"], hi["index"]],
                    "difference": "central" if 0 < idx < len(line) - 1 else "one-sided"})
    return out


def calibration(args) -> dict:
    """CHN-16: a candidate's calibration residual (a numeric parameter: the rigidity scale s, or the curvature offset
    delta in 1/unit) propagated by propagate_scale_distortion.py response over a spectrum model into binned yield
    shifts, up/down variations and covariance blocks (outputs/<id>.json and its computational-run, which records argv,
    the script hash and the digest of the residual parameter, so a change of the residual makes the step rerun with
    run_workflow.py --incremental). With --measurement-spec, a new version of that measurement-spec carries the
    variations as a shape systematic bound to the output, for the hep-statistics Asimov fit of the expected precision."""
    proj = load_project(args)
    if proj.candidates.get(args.candidate) is None or proj.candidate_chain(args.candidate) is None:
        raise UsageError(f"no design-candidate {args.candidate!r} (with its bases) in the artifacts_dir")
    if not re.match(r"^CAL-[A-Za-z0-9][A-Za-z0-9._-]*$", args.id):
        raise UsageError(f"--id {args.id!r}: a calibration step id is CAL- followed by letters, digits, '.', '_' or '-'")
    sid, _, name = args.residual.partition(".parameters.")
    par = (((proj.effective(args.candidate) or {}).get(sid) or {}).get("parameters") or {}).get(name) if name else None
    if par is None or isinstance(par.get("value"), bool) or not isinstance(par.get("value"), (int, float)):
        raise UsageError(f"--residual {args.residual}: a numeric parameter SID.parameters.NAME of {args.candidate}")
    calib = ((proj.effective(args.candidate) or {}).get(sid) or {}).get("calibration") or {}
    if not calib.get("control_samples"):
        raise UsageError(f"{sid} has no calibration control sample (CHN-16): a residual without a calibration is not "
                         "propagated")
    model = proj.root / args.model
    if not model.is_file():
        raise UsageError(f"--model {args.model} is not a file in the artifacts_dir")
    for rel in (f"outputs/{args.id}.json", f"runs/{args.id}.computational-run.json"):
        if (proj.root / rel).exists():
            raise UsageError(f"{rel} exists: choose another --id")
    script = "skills/hep-detector/scripts/propagate_scale_distortion.py"
    flag = "--scale" if args.mode == "scale" else "--delta"
    tool_args = ["response", args.model, "--mode", args.mode, flag, token(float(par["value"])), "--status", args.status]
    proc = subprocess.run([sys.executable, "-B", str(PLUGIN / script), *tool_args], capture_output=True,
                          cwd=str(proj.root), timeout=TOOL_TIMEOUT_S)
    try:
        output = json.loads(proc.stdout.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        output = None
    if proc.returncode != 0 or not isinstance(output, dict) or output.get("status") != "ok":
        return {"status": "failed", "exit": 1, "error": f"{script} exited {proc.returncode}", "tool_output": output,
                "stderr": proc.stderr.decode("utf-8", "replace")[-2000:]}
    w = Writer(proj)
    out_rel = w.write(f"outputs/{args.id}.json", proc.stdout)
    chain_rels = [proj.rel(p) for p in proj.candidate_chain(args.candidate)]
    inputs = [dict(w.input_ref(r), binding="parameters") for r in chain_rels]
    model_in = {"ref": args.model, "sha256": sha256(model)}
    argv = ["python3", script, *tool_args]
    digest = proj.parameter_digest(args.candidate, [args.residual])
    run_ext = {"input_manifest": [{"path": r, "sha256": sha256(proj.root / r)} for r in chain_rels] + [
                   {"path": args.model, "sha256": model_in["sha256"]}],
               "tools": [{"name": "propagate_scale_distortion", "version": plugin_version()}],
               "commands": [" ".join(argv)],
               "environment": {"python": platform.python_version(), "platform": platform.platform(terse=True)},
               "seeds": {}, "tolerances": {}, "exit_status": 0, "output_hashes": {out_rel: sha256(proj.root / out_rel)},
               "argv": argv, "script_sha256": {script: sha256(PLUGIN / script)}, "parameter_digest": digest}
    ns = args.candidate.split(":", 1)[0]
    run_rel = w.json(f"runs/{args.id}.computational-run.json",
                     envelope("computational-run", f"{ns}-{args.id}-run", run_ext, inputs + [model_in],
                              [{"ref": out_rel}], statuses(inputs, args.status)))
    result = {"status": "ok", "exit": 0, "output": out_rel, "run": run_rel, "residual": args.residual,
              "residual_value": par["value"], "mode": args.mode, "parameter_digest": digest,
              "max_relative_shift": {n: max((abs(v) for v in c.get("relative_shift_up", []) + c.get(
                  "relative_shift_down", []) if v is not None), default=None)
                  for n, c in (output.get("components") or {}).items()},
              "warnings": output.get("warnings", [])}
    if args.measurement_spec:
        base_path = proj.root / args.measurement_spec
        try:
            base = json.loads(base_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            w.undo()
            raise UsageError(f"--measurement-spec {args.measurement_spec} is not a readable JSON file") from None
        if base.get("artifact_type") != "measurement-spec":
            w.undo()
            raise UsageError(f"--measurement-spec {args.measurement_spec} is not a measurement-spec")
        if not args.out_spec or (proj.root / args.out_spec).exists():
            w.undo()
            raise UsageError("--out-spec names a new file in the artifacts_dir for the measurement-spec version")
        spec = json.loads(json.dumps(base))
        entry = {"name": f"{args.candidate} calibration residual {args.residual} ({args.mode})",
                 "source": f"design candidate {args.candidate}, {sid} calibration ({calib.get('method', 'unstated')})",
                 "effect": "shape",
                 "applied_via": f"up/down variations and covariance block of {out_rel} (propagate_scale_distortion.py)"}
        spec["extension"]["systematics"] = [x for x in spec["extension"].get("systematics", [])
                                            if x.get("name") != entry["name"]] + [entry]
        spec["artifact_id"] = f"{base['artifact_id']}-{args.id.lower()}"
        spec["inputs"] = list(base.get("inputs") or []) + [w.input_ref(args.measurement_spec), w.input_ref(run_rel),
                                                          {"ref": out_rel, "sha256": sha256(proj.root / out_rel)}]
        spec["provenance"] = dict(base.get("provenance") or {}, created=created())
        spec_rel = w.json(args.out_spec, spec)
        from contracts.validate import validate_artifact
        rep = validate_artifact(json.loads((proj.root / spec_rel).read_text(encoding="utf-8")))
        if not rep.ok:
            w.undo()
            return {"status": "failed", "exit": 1, "error": "the measurement-spec version fails contract validation",
                    "findings": [f.as_dict() for f in rep.errors]}
        result["measurement_spec"] = spec_rel
        result["next"] = ("run the hep-statistics Asimov fit on this measurement-spec, then evaluate_design.py run "
                          "--figure-of-merit expected-precision --input-artifact <statistical-result> (CHN-03, CHN-04)")
    return result


def scan(args) -> dict:
    """M4 (OQ-18, AGG-08, RSK-04): the figure of merit of one candidate over a grid of parameter values, run point by
    point in a scratch copy of the artifacts_dir exactly as run would, and stored as one summary computational-run.
    No evaluation file is written: a point takes part in no aggregation and supports no verdict until it is expanded
    (expand) and evaluated like any candidate."""
    import itertools
    import shutil
    import tempfile
    proj = load_project(args)
    cpath = proj.candidates.get(args.candidate)
    if cpath is None or proj.candidate_chain(args.candidate) is None:
        raise UsageError(f"no design-candidate {args.candidate!r} (with its bases) in the artifacts_dir")
    if not re.match(r"^SCAN-[A-Za-z0-9][A-Za-z0-9._-]*$", args.id):
        raise UsageError(f"--id {args.id!r}: a scan id is SCAN- followed by letters, digits, '.', '_' or '-'")
    run_rel = f"runs/{args.id}.computational-run.json"
    if (proj.root / run_rel).exists():
        raise UsageError(f"{run_rel} exists: choose another --id")
    hit = choose_operation(proj, args.figure_of_merit, args.fidelity, args.tool)
    if hit is None:
        raise UsageError(f"no operation computes {args.figure_of_merit} at {args.fidelity}: nothing to scan")
    if hit[2].get("required_upstreams"):
        raise UsageError(f"{args.figure_of_merit} needs upstream evaluations ({', '.join(hit[2]['required_upstreams'])}); "
                         "a scan reruns only operations without upstreams: scan the upstream figure of merit instead")
    axes = parse_vary(proj, args.candidate, args.vary)
    grid = list(itertools.product(*[vals for _, _, vals in axes]))
    if len(grid) > args.max_points:
        raise UsageError(f"{len(grid)} points exceed --max-points {args.max_points}")
    crel = proj.rel(cpath)
    cdoc = json.loads(cpath.read_text(encoding="utf-8"))
    points = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "artifacts"
        shutil.copytree(proj.root, work, ignore=shutil.ignore_patterns("reports"))
        for k, combo in enumerate(grid):
            values = {ref: v for (ref, _, _), v in zip(axes, combo)}
            (work / crel).write_text(json.dumps(set_parameters(cdoc, values, proj, args.candidate,
                                                               f"scan {args.id} point {k}"), indent=1) + "\n",
                                     encoding="utf-8")
            ns = argparse.Namespace(artifacts=work, candidate=args.candidate, requirement=None,
                                    figure_of_merit=args.figure_of_merit, denominator=args.denominator,
                                    fidelity=args.fidelity, tool=args.tool, upstream=None, input_artifact=None,
                                    id=f"CALC-scan-point-{k}", replace=False, status=args.status)
            try:
                res = run_evaluation(ns)
            except UsageError as exc:
                res = {"status": "failed", "error": str(exc)}
            point = {"index": k, "parameters": values}
            if res.get("status") == "ok":
                ev = json.loads((work / res["evaluation"]).read_text(encoding="utf-8"))["extension"]
                point.update(value=ev.get("value"), unit=ev.get("unit"), bound=ev.get("bound"),
                             in_domain=(ev.get("validity") or {}).get("in_domain"))
                if ev.get("uncertainty"):
                    point["uncertainty"] = ev["uncertainty"]
                for f in res.get("files", []):
                    (work / f).unlink(missing_ok=True)
            else:
                point.update(value=None, error=res.get("error"))
            points.append(point)
    w = Writer(proj)
    chain_rels = [proj.rel(p) for p in proj.candidate_chain(args.candidate)]
    inputs = [w.input_ref(r) for r in chain_rels]
    script = "skills/hep-detector/scripts/evaluate_design.py"
    argv = ["python3", script, "scan", "--candidate", args.candidate, "--figure-of-merit", args.figure_of_merit,
            "--fidelity", args.fidelity, *[x for d in args.denominator or [] for x in ("--denominator", d)],
            *[x for v in args.vary for x in ("--vary", v)], "--id", args.id]
    summary = {"candidate": args.candidate, "figure_of_merit": args.figure_of_merit, "fidelity": args.fidelity,
               "denominator": {k: parse_value(v) for k, _, v in (d.partition("=") for d in args.denominator or [])},
               "tool": f"{hit[0]['tool_id']}:{hit[1]['operation_id']}", "parameters": [r for r, _, _ in axes],
               "points": points, "sensitivity": sensitivities(points, axes),
               "note": "scan points are not evaluations: they take part in no aggregation and support no verdict "
                       "(AGG-08); expand a point into a candidate to evaluate and compare it"}
    ext = {"input_manifest": [{"path": r, "sha256": sha256(proj.root / r)} for r in chain_rels],
           "tools": [{"name": "evaluate_design.scan", "version": plugin_version()}], "commands": [" ".join(argv)],
           "environment": {"python": platform.python_version(), "platform": platform.platform(terse=True)},
           "seeds": {}, "tolerances": {}, "exit_status": 0, "output_hashes": {}, "argv": argv,
           "script_sha256": {script: sha256(PLUGIN / script)}, "scan_summary": summary}
    ns_id = args.candidate.split(":", 1)[0]
    w.json(run_rel, envelope("computational-run", f"{ns_id}-{args.id}", ext, inputs, [], statuses(inputs, args.status)))
    return {"status": "ok", "exit": 0, "scan": run_rel, "points": len(points),
            "failed_points": sum(1 for p in points if p.get("value") is None),
            "sensitivity": summary["sensitivity"], "note": summary["note"]}


def expand(args) -> dict:
    """M4: one scan point as a candidate derived from the scanned one (derived_from, overrides of the scanned
    parameters); evaluate it with run like any candidate to bring it into comparison."""
    proj = load_project(args)
    run = proj.docs.get(proj.resolve(args.scan))
    summary = ((run or {}).get("extension") or {}).get("scan_summary")
    if not summary:
        raise UsageError(f"--scan {args.scan} is not a scan summary in the artifacts_dir")
    point = next((p for p in summary["points"] if p.get("index") == args.point), None)
    if point is None:
        raise UsageError(f"--point {args.point}: the scan has points 0..{len(summary['points']) - 1}")
    base = summary["candidate"]
    if proj.candidates.get(base) is None:
        raise UsageError(f"the scanned candidate {base} is no longer in the artifacts_dir")
    ns, short = base.split(":", 1)[0], args.candidate_id
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", short):
        raise UsageError(f"--candidate-id {short!r}: letters, digits, '.', '_' or '-'")
    rel = f"candidates/{short}.json"
    subs = proj.effective(base) or {}
    overrides: dict = {}
    for ref, v in point["parameters"].items():
        sid, _, name = ref.partition(".parameters.")
        par = dict(subs[sid]["parameters"][name], value=v, source=f"{args.scan} point {args.point}", status="proposal")
        overrides.setdefault(sid, {}).setdefault("parameters", {})[name] = par
    w = Writer(proj)
    inputs = [dict(w.input_ref(proj.rel(proj.candidates[base])), binding="parameters"), w.input_ref(args.scan)]
    ext = {"candidate_id": f"{ns}:{short}", "design_id": proj.docs[proj.candidates[base]]["extension"]["design_id"],
           "description": f"point {args.point} of {args.scan} ({', '.join(f'{k}={v}' for k, v in point['parameters'].items())})",
           "derived_from": base, "overrides": overrides}
    w.json(rel, envelope("design-candidate", f"{ns}-{short}", ext, inputs, [], statuses(inputs, "unvalidated")))
    from contracts.validate import validate_artifact
    rep = validate_artifact(json.loads((proj.root / rel).read_text(encoding="utf-8")))
    if not rep.ok:
        w.undo()
        return {"status": "failed", "exit": 1, "error": "the candidate fails contract validation",
                "findings": [f.as_dict() for f in rep.errors]}
    return {"status": "ok", "exit": 0, "candidate": f"{ns}:{short}", "file": rel,
            "next": f"evaluate_design.py run --candidate {ns}:{short} --figure-of-merit {summary['figure_of_merit']}"
                    f" --fidelity {summary['fidelity']} (and every other evaluation the comparison needs)"}


# ---------------------------------------------------------------- automated candidate generation (C1)

SEARCH_ASSETS = PLUGIN / "skills" / "hep-detector" / "assets" / "design-search"
SEARCH_LIB = Path(__file__).resolve().parent / "design_search_lib"
MAX_OBJECTIVES = 4  # exact WFG hypervolume; more objectives are expressed as constraints (section C.4.4)
CONSISTENCY_TOL = 1e-12  # in-process search value against evaluate_design.py run (C1.4)
SEARCH_NOTE = ("search values are not evaluations: they take part in no aggregation and support no verdict; the "
               "search front is non-binding and no optimum is claimed; expand a finalist (expand --search) and "
               "evaluate it with run and budget, then derive verdicts and comparison with report")


def search_lib():
    """The standard-library searcher (design_search_lib: sobol, nsga2, hypervolume), imported on first use."""
    scripts = str(SEARCH_LIB.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from design_search_lib import hypervolume, nsga2, sobol
    return hypervolume, nsga2, sobol


def canonical(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_asset(name: str, key: str, version: str) -> tuple[dict, str]:
    path = SEARCH_ASSETS / name
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get(key) != version:
        raise UsageError(f"the search spec names {key} {version}, the shipped {name} is {doc.get(key)}: a different "
                         "version is a new search spec")
    return doc, sha256(path)


class InProcessTools:
    """C1.4: the F1 tool scripts imported once and called through main(argv) in this process, with stdout captured
    and SystemExit caught; config-file inputs go to a scratch folder."""

    def __init__(self, scratch: Path):
        self.scratch, self.modules, self.calls, self.seconds = scratch, {}, 0, 0.0

    def config_file(self, name: str, val: dict) -> str:
        path = self.scratch / f"{name}.json"
        path.write_text(json.dumps(val, indent=1) + "\n", encoding="utf-8")
        return str(path)

    def call(self, entry: str, argv: list[str]) -> tuple[int, dict | None]:
        import contextlib
        import importlib.util
        import io
        import time
        mod = self.modules.get(entry)
        if mod is None:
            spec = importlib.util.spec_from_file_location(f"_design_search_tool_{len(self.modules)}", PLUGIN / entry)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.modules[entry] = mod
        out, err = io.StringIO(), io.StringIO()
        t0 = time.perf_counter()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = mod.main(argv)
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 2)
        self.seconds += time.perf_counter() - t0
        self.calls += 1
        try:
            output = json.loads(out.getvalue())
        except ValueError:
            output = None
        return int(code or 0), output if isinstance(output, dict) else None


def resolve_target(proj: design.Project, spec_ext: dict, t: dict, kind: str) -> dict:
    """An objective or constraint of the search spec: its figure of merit, denominator, F1 operation (and the
    upstream operation a chained figure of merit needs), direction, threshold and reference point."""
    req = None
    if t.get("requirement"):
        req = next((r for r in spec_ext["requirements"] + spec_ext["constraints"]
                    if r["id"] == t["requirement"] or r["id"].endswith(":" + t["requirement"])), None)
        if req is None:
            raise UsageError(f"{kind} {t['requirement']!r}: no requirement or constraint of that id in the current "
                             "design-spec")
        fom, den = req["quantity"], {k: v["value"] for k, v in req["denominator"].items()}
        comparator, target = req["comparator"], req["target"]
        label = req["id"].split(":", 1)[-1]
    else:
        if not t.get("figure_of_merit"):
            raise UsageError(f"a search {kind} names a requirement or a figure_of_merit")
        fom, den = t["figure_of_merit"], dict(t.get("denominator") or {})
        comparator, target = t.get("comparator"), t.get("target")
        label = fom
        if kind == "constraint" and (comparator is None or target is None):
            raise UsageError(f"constraint {fom}: give a requirement, or comparator and target")
    if proj.fom_rules(fom) is None:
        raise UsageError(f"{kind} {label}: {fom!r} is not a figure of merit of the adequacy table")
    hit = choose_operation(proj, fom, "F1", t.get("tool"))
    if hit is None:
        raise UsageError(f"{kind} {label}: no F1 tool contract computes {fom} (capability.unavailable cannot be "
                         "searched on)")
    contract, op, fd = hit
    if set(den) != set(fd["denominator"]):
        raise UsageError(f"{kind} {label}: the denominator needs exactly {sorted(fd['denominator'])}")
    up = None
    ups = fd.get("required_upstreams", [])
    if len(ups) > 1:
        raise UsageError(f"{kind} {label}: {fom} needs {len(ups)} upstreams; the search chains one")
    if ups:
        uhit = choose_operation(proj, ups[0], "F1", t.get("upstream_tool"))
        if uhit is None or uhit[2].get("required_upstreams"):
            raise UsageError(f"{kind} {label}: its upstream {ups[0]} has no F1 operation without upstreams")
        up = {"figure_of_merit": ups[0], "hit": uhit, "tool": f"{uhit[0]['tool_id']}:{uhit[1]['operation_id']}",
              "denominator": {k: den[k] for k in uhit[2]["denominator"] if k in den}}
        if set(up["denominator"]) != set(uhit[2]["denominator"]):
            raise UsageError(f"{kind} {label}: the denominator lacks fields of its upstream {ups[0]}")
    out = {"label": label, "figure_of_merit": fom, "denominator": den, "requirement": req["id"] if req else None,
           "tool": f"{contract['tool_id']}:{op['operation_id']}", "hit": hit, "upstream": up, "better": fd["better"],
           "comparator": comparator, "target": target}
    if kind == "objective":
        if comparator == "range":
            raise UsageError(f"objective {label}: a range requirement cannot be an objective; make it a constraint")
        ref = t.get("reference_point")
        if ref is None and isinstance(target, (int, float)) and target != 0:
            ref = target * 1.1 if fd["better"] == "smaller" else target / 1.1  # section C.4.7
        if not isinstance(ref, (int, float)) or ref == 0:
            raise UsageError(f"objective {label}: no threshold to place the reference point at; declare a non-zero "
                             "reference_point")
        out["reference_point"] = float(ref)
    return out


def violation_of(t: dict, value) -> float:
    """Normalised shortfall of a constraint on its search value; a missing value counts 1."""
    if value is None:
        return 1.0
    comp, target = t["comparator"], t["target"]
    if comp == "range":
        lo, hi = target
        scale = max(abs(hi - lo), 1e-300)
        return max(0.0, (lo - value) / scale) + max(0.0, (value - hi) / scale)
    scale = max(abs(target), 1e-300)
    if comp in ("<=", "<"):
        return max(0.0, (value - target) / scale)
    return max(0.0, (target - value) / scale)


class SearchSpace:
    """The genome of a search spec (section C.4.5): slots (base subsystems and the subsystems the search may add), their
    enable bits and parent slots, and the parameters the role rules let the search change; the decoder (genome ->
    design-candidate as overrides on the base candidate, or an independent candidate when a subsystem is dropped),
    repair and the violation measure."""

    def __init__(self, proj: design.Project, spec: dict, roles: dict, materials: dict, search_id: str):
        self.proj, self.spec, self.search_id = proj, spec, search_id
        self.rules, self.mothers = roles["roles"], set(roles.get("mothers", []))
        self.rules_version, self.rel_unc = roles["rules_version"], roles.get("budget_relative_uncertainty", 0.25)
        self.materials = materials["materials"]
        self.base = spec["base_candidate"]
        if self.proj.candidates.get(self.base) is None or self.proj.candidate_chain(self.base) is None:
            raise UsageError(f"base candidate {self.base} (with its bases) is not in the artifacts_dir")
        self.ns = self.base.split(":", 1)[0]
        self.design_id = proj.docs[proj.candidates[self.base]]["extension"]["design_id"]
        self.base_subs = json.loads(json.dumps(proj.effective(self.base)))
        self.base_budgets = json.loads(json.dumps(proj.effective_budgets(self.base)))
        self.envelope = (spec.get("envelope") or {}).get("length_m")
        self.regenerate = list(spec.get("regenerate_budgets") or [])
        for sid in self.regenerate:
            if sid not in self.base_subs:
                raise UsageError(f"regenerate_budgets names {sid}, which the base candidate does not have")
        self.genes: list[dict] = []
        self.slots: list[dict] = []
        self._build()

    # -- building the genome
    def _gene(self, gene: dict) -> int:
        self.genes.append(gene)
        return len(self.genes) - 1

    def _rule(self, role: str) -> dict:
        from contracts.vocab import Vocabulary
        if role not in self.rules:
            raise UsageError(f"role {role!r} has no realization rule in roles.json (rules {self.rules_version})")
        if not Vocabulary().has("subsystem_roles", role):
            raise UsageError(f"role {role!r} is not in the subsystem_roles vocabulary")
        return self.rules[role]

    def _param_genes(self, slot: dict, name: str, rule_def: dict, free: dict | None) -> None:
        kind = (free or {}).get("kind") or rule_def["kind"]
        where = f"{slot['sid']}.parameters.{name}"
        if kind != rule_def["kind"]:
            raise UsageError(f"{where}: kind {kind} differs from the role rule's {rule_def['kind']}")
        entry: dict = {"name": name, "kind": kind, "unit": rule_def["unit"]}
        if kind == "categorical":
            choices = list((free or {}).get("choices") or rule_def["choices"])
            if not set(choices) <= set(rule_def["choices"]):
                raise UsageError(f"{where}: choices {choices} outside the role rule's {rule_def['choices']}")
            if name.endswith("material") and not set(choices) <= set(self.materials):
                raise UsageError(f"{where}: a material outside materials.json")
            entry.update(choices=choices, gene=self._gene({"name": where, "type": "cat", "n": len(choices),
                                                           "choices": choices}))
        else:
            lo, hi = (free or {}).get("range") or rule_def["range"]
            rlo, rhi = rule_def["range"]
            if not (rlo <= lo <= hi <= rhi):
                raise UsageError(f"{where}: range [{lo}, {hi}] outside the role rule's [{rlo}, {rhi}] or reversed")
            if kind == "positions":
                nlo, nhi = (free or {}).get("n") or rule_def["n"]
                rnlo, rnhi = rule_def["n"]
                if not (rnlo <= nlo <= nhi <= rnhi):
                    raise UsageError(f"{where}: n [{nlo}, {nhi}] outside the role rule's [{rnlo}, {rnhi}]")
                spacing = (free or {}).get("min_spacing_m", rule_def["min_spacing_m"])
                if spacing < rule_def["min_spacing_m"]:
                    raise UsageError(f"{where}: min_spacing_m {spacing} below the role rule's {rule_def['min_spacing_m']}")
                if (nhi - 1) * spacing > hi - lo:
                    raise UsageError(f"{where}: {nhi} planes at {spacing} m spacing do not fit in [{lo}, {hi}]")
                entry.update(range=[lo, hi], n=[nlo, nhi], min_spacing=spacing,
                             n_gene=self._gene({"name": where + ".n", "type": "int", "lo": nlo, "hi": nhi})
                             if nlo < nhi else None,
                             genes=[self._gene({"name": f"{where}[{i}]", "type": "real", "lo": lo, "hi": hi})
                                    for i in range(nhi)])
            elif kind == "integer":
                entry.update(range=[int(lo), int(hi)], gene=self._gene({"name": where, "type": "int", "lo": int(lo),
                                                                        "hi": int(hi)}))
            else:
                entry.update(range=[lo, hi], gene=self._gene({"name": where, "type": "real", "lo": lo, "hi": hi}))
        slot["params"][name] = entry

    def _build(self) -> None:
        free: dict[str, dict[str, dict]] = {}
        for fp in self.spec.get("free_parameters", []):
            sid, _, name = fp["ref"].partition(".parameters.")
            if name in free.setdefault(sid, {}):
                raise UsageError(f"free_parameters names {fp['ref']} twice")
            free[sid][name] = fp
        slot_spec = {}
        for role, val in (self.spec.get("slots") or {}).items():
            rng, ids = (val, []) if isinstance(val, list) else (val["range"], list(val.get("ids") or []))
            if len(rng) != 2 or rng[0] > rng[1]:
                raise UsageError(f"slots.{role}: [min, max] with min <= max")
            if rng[1] > 1:
                raise UsageError(f"slots.{role}: at most one subsystem per role (main's granularity: one subsystem per "
                                 "role, planes as array parameters)")
            slot_spec[role] = (rng[0], rng[1], ids)
        roles_in_base: dict[str, list[str]] = {}
        for sid in sorted(self.base_subs):
            roles_in_base.setdefault(self.base_subs[sid]["role"], []).append(sid)
        for sid in sorted(self.base_subs):
            role = self.base_subs[sid]["role"]
            slot = {"sid": sid, "role": role, "base": True, "enable_gene": None, "parent_gene": None, "parent_options":
                    [None], "params": {}, "always": True}
            if role in slot_spec:
                lo, hi, _ = slot_spec[role]
                if len(roles_in_base[role]) > hi:
                    raise UsageError(f"slots.{role}: the base candidate already has {len(roles_in_base[role])}")
                if lo == 0:
                    slot["always"] = False
                    slot["enable_gene"] = self._gene({"name": f"{sid}.enabled", "type": "bit"})
            for name, fp in sorted(free.pop(sid, {}).items()):
                rule = self._rule(role)
                if name not in rule["parameters"]:
                    raise UsageError(f"{fp['ref']}: the role rule of {role} does not let the search change {name}")
                if name not in self.base_subs[sid]["parameters"] and name not in rule.get("new_subsystem", {}):
                    raise UsageError(f"{fp['ref']}: not a parameter of the base candidate")
                self._param_genes(slot, name, rule["parameters"][name], fp)
            self._check_per_layer(slot)
            self.slots.append(slot)
        for role in sorted(slot_spec):
            lo, hi, ids = slot_spec[role]
            rule = self._rule(role)
            for k in range(hi - len(roles_in_base.get(role, []))):
                sid = ids[k] if k < len(ids) else f"DES-{rule['code']}-S{k + 1:02d}"
                if sid in self.base_subs:
                    raise UsageError(f"slots.{role}: id {sid} is already a subsystem of the base candidate")
                slot = {"sid": sid, "role": role, "base": False, "enable_gene": None, "parent_gene": None,
                        "parent_options": [None], "params": {}, "always": len(roles_in_base.get(role, [])) + k < lo}
                if not slot["always"]:
                    slot["enable_gene"] = self._gene({"name": f"{sid}.enabled", "type": "bit"})
                for name in sorted(rule["parameters"]):
                    self._param_genes(slot, name, rule["parameters"][name], free.get(sid, {}).pop(name, None))
                free.pop(sid, None)
                self.slots.append(slot)
        if free:
            raise UsageError(f"free_parameters name subsystems that are neither in the base candidate nor slots the "
                             f"search may add: {sorted(free)}")
        for slot in self.slots:  # parent slots: a daughter of an enabled bending or calorimetry slot (section C.4.5)
            if slot["base"]:
                continue
            opts = [None] + [s["sid"] for s in self.slots if s is not slot and s["role"] in self.mothers]
            if len(opts) > 1:
                slot["parent_options"] = opts
                slot["parent_gene"] = self._gene({"name": f"{slot['sid']}.parent", "type": "cat", "n": len(opts),
                                                  "choices": [o or "-1" for o in opts]})
        if not self.genes:
            raise UsageError("the search spec frees no parameter and no slot: nothing to search")

    def _check_per_layer(self, slot: dict) -> None:
        pos = next((p for p in slot["params"].values() if p["kind"] == "positions"), None)
        if pos is None:
            return
        base_n = len(self.base_subs[slot["sid"]]["parameters"].get(pos["name"], {}).get("value") or [])
        if pos["n"] == [base_n, base_n]:
            return
        rule = self.rules[slot["role"]]
        derived = set(rule.get("derived", {})) if self._has_sensor(slot) else set()
        for name in rule.get("per_layer", []):
            par = self.base_subs[slot["sid"]]["parameters"].get(name)
            if par is None or name in derived or not isinstance(par.get("value"), list):
                continue
            vals = par["value"]
            if any(v != vals[0] for v in vals):
                raise UsageError(f"{slot['sid']}.parameters.{name} differs between planes and the number of planes is "
                                 "free: free the sensor material and thickness (derived per plane) or fix n")

    def _has_sensor(self, slot: dict) -> bool:
        return not slot["base"] or bool({"sensor_material", "sensor_thickness_um"} & set(slot["params"]))

    # -- genomes
    def default_genome(self) -> list:
        """The base candidate's values (a disabled added slot with the role rule's new-subsystem values)."""
        g: list = [None] * len(self.genes)
        for slot in self.slots:
            if slot["enable_gene"] is not None:
                g[slot["enable_gene"]] = slot["base"]
            if slot["parent_gene"] is not None:
                g[slot["parent_gene"]] = 0
            defaults = self.rules[slot["role"]].get("new_subsystem", {})
            for name, p in slot["params"].items():
                base = (self.base_subs.get(slot["sid"], {}).get("parameters") or {}).get(name)
                val = base["value"] if base is not None and slot["base"] else defaults.get(name)
                self._set_param(g, p, val)
        return g

    def _set_param(self, g: list, p: dict, val) -> None:
        if p["kind"] == "categorical":
            g[p["gene"]] = p["choices"].index(val) if val in p["choices"] else 0
        elif p["kind"] == "positions":
            vals = sorted(float(v) for v in (val if isinstance(val, list) else []))
            n = min(max(len(vals), p["n"][0]), p["n"][1])
            if p["n_gene"] is not None:
                g[p["n_gene"]] = n
            lo, hi = p["range"]
            extra = [lo + (hi - lo) * (i + 0.5) / len(p["genes"]) for i in range(len(p["genes"]))]
            vals = (vals + extra)[:len(p["genes"])]
            for k, gi in enumerate(p["genes"]):
                g[gi] = vals[k]
        else:
            g[p["gene"]] = float(val) if p["kind"] == "continuous" else int(val)

    def proposal_genome(self, prop: dict) -> list:
        """A designer's seed design (proposer llm): the default genome with the slots and parameters it names."""
        g = self.default_genome()
        by_sid = {s["sid"]: s for s in self.slots}
        for key, on in (prop.get("enabled") or {}).items():
            hits = [s for s in self.slots if s["sid"] == key or s["role"] == key]
            if not hits or any(s["enable_gene"] is None and bool(on) != s["always"] for s in hits):
                raise UsageError(f"proposal {prop['id']}: enabled.{key} names no slot the search may switch")
            for s in hits:
                if s["enable_gene"] is not None:
                    g[s["enable_gene"]] = bool(on)
        for sid, parent in (prop.get("parent") or {}).items():
            s = by_sid.get(sid)
            if s is None or s["parent_gene"] is None or parent not in s["parent_options"]:
                raise UsageError(f"proposal {prop['id']}: parent.{sid} = {parent} is not a parent the search allows")
            g[s["parent_gene"]] = s["parent_options"].index(parent)
        for ref, val in (prop.get("parameters") or {}).items():
            sid, _, name = ref.partition(".parameters.")
            p = (by_sid.get(sid) or {}).get("params", {}).get(name)
            if p is None:
                raise UsageError(f"proposal {prop['id']}: {ref} is not a free parameter of the search")
            self._set_param(g, p, val)
        return g

    def repair(self, g: list) -> tuple[list, list[str]]:
        """Clip to range, reset impossible parents, sort plane positions and push them apart to the minimum spacing
        (section C.4.5); returns the repaired genome and what was repaired."""
        g, notes = list(g), []
        for k, gene in enumerate(self.genes):
            t = gene["type"]
            if t in ("real", "int"):
                v = min(max(g[k], gene["lo"]), gene["hi"])
                v = int(round(v)) if t == "int" else float(v)
                if v != g[k]:
                    notes.append(f"range: {gene['name']} clipped to {v}")
                g[k] = v
            elif t == "cat":
                if not isinstance(g[k], int) or not 0 <= g[k] < gene["n"]:
                    notes.append(f"range: {gene['name']} reset")
                    g[k] = 0
            else:
                g[k] = bool(g[k])
        enabled = {s["sid"]: self._enabled(s, g) for s in self.slots}
        roles = {s["sid"]: s["role"] for s in self.slots}
        for s in self.slots:
            if s["parent_gene"] is None:
                continue
            parent = s["parent_options"][g[s["parent_gene"]]]
            if parent is not None and (not enabled.get(parent) or roles[parent] not in self.mothers):
                g[s["parent_gene"]] = 0
        for s in self.slots:
            for p in s["params"].values():
                if p["kind"] != "positions":
                    continue
                n = g[p["n_gene"]] if p["n_gene"] is not None else p["n"][0]
                lo, hi = p["range"]
                sp = p["min_spacing"]
                x = sorted(g[gi] for gi in p["genes"][:n])
                for i in range(1, n):
                    x[i] = max(x[i], x[i - 1] + sp)
                if n and x[-1] > hi:
                    x[-1] = hi
                    for i in range(n - 2, -1, -1):
                        x[i] = min(x[i], x[i + 1] - sp)
                x = [min(max(v, lo), hi) for v in x]
                for gi, v in zip(p["genes"][:n], x):
                    g[gi] = v
        return g, notes

    def _enabled(self, slot: dict, g: list) -> bool:
        return slot["always"] if slot["enable_gene"] is None else bool(g[slot["enable_gene"]])

    def values(self, g: list) -> dict:
        out = {}
        for s in self.slots:
            params = {}
            for name, p in s["params"].items():
                if p["kind"] == "categorical":
                    params[name] = p["choices"][g[p["gene"]]]
                elif p["kind"] == "positions":
                    n = g[p["n_gene"]] if p["n_gene"] is not None else p["n"][0]
                    params[name] = [g[gi] for gi in p["genes"][:n]]
                else:
                    params[name] = g[p["gene"]]
            out[s["sid"]] = {"enabled": self._enabled(s, g), "params": params,
                             "parent": s["parent_options"][g[s["parent_gene"]]] if s["parent_gene"] is not None else None}
        return out

    def genome_dict(self, g: list) -> dict:
        return {gene["name"]: (gene["choices"][g[k]] if gene["type"] == "cat" else g[k])
                for k, gene in enumerate(self.genes)}

    def genome_from_dict(self, d: dict) -> list:
        g = []
        for gene in self.genes:
            if gene["name"] not in d:
                raise UsageError(f"the point's genome lacks {gene['name']}: the search spec changed")
            v = d[gene["name"]]
            g.append(gene["choices"].index(v) if gene["type"] == "cat" else v)
        return g

    # -- decoding
    def _material(self, name: str) -> dict:
        m = self.materials.get(name)
        if m is None:
            raise UsageError(f"material {name!r} is not in materials.json")
        return m

    def _sensor(self, slot: dict, params: dict) -> tuple[str, float]:
        rule = self.rules[slot["role"]]
        defaults = rule.get("new_subsystem", {})
        old = self.base_subs.get(slot["sid"], {}).get("parameters", {}) if slot["base"] else {}
        mat = params.get("sensor_material", (old.get("sensor_material") or {}).get("value",
                                                                                    defaults.get("sensor_material")))
        thick = params.get("sensor_thickness_um", (old.get("sensor_thickness_um") or {}).get(
            "value", defaults.get("sensor_thickness_um")))
        return str(mat), float(thick)

    def _derived(self, slot: dict, params: dict, n: int | None) -> dict:
        """Per-plane x/X0 from sensor material and thickness (role rule 'derived'), and per-plane arrays of the base
        resized when the number of planes changes."""
        out: dict = {}
        rule = self.rules[slot["role"]]
        if "layer_x_over_x0" in rule.get("derived", {}) and self._has_sensor(slot) and n is not None:
            mat, thick = self._sensor(slot, params)
            out["layer_x_over_x0"] = [thick * 1e-4 / self._material(mat)["radiation_length_cm"]] * n
        if slot["base"] and n is not None:
            for name in rule.get("per_layer", []):
                par = self.base_subs[slot["sid"]]["parameters"].get(name)
                if name in out or par is None or not isinstance(par.get("value"), list) or len(par["value"]) == n:
                    continue
                out[name] = [par["value"][0]] * n
        return out

    def _budget_rows(self, slot: dict, params: dict) -> dict:
        rule = self.rules[slot["role"]]
        model, inp = rule["budget_model"], rule["budget_model"]["inputs"]
        name = model["name"]
        if name == "planes-density-volume":
            n = len(params["layer_positions_m"])
            mat, thick = self._sensor(slot, params)
            dens = self._material(mat)["density_g_cm3"] * 1000.0
            mass = n * inp["plane_area_m2"] * thick * 1e-6 * dens * (1 + inp["support_mass_factor"])
            channels = n * inp["readout_sides"] * math.sqrt(inp["plane_area_m2"]) / (inp["strip_pitch_um"] * 1e-6)
        elif name == "magnet-placeholder":
            mass, channels = inp["mass_per_tesla_kg"] * params["field_T"], 0.0
        elif name == "tof-planes":
            dens = self._material(inp["scintillator_material"])["density_g_cm3"] * 1000.0
            mass = params["n_layers"] * inp["plane_area_m2"] * params["scintillator_thickness_cm"] * 0.01 * dens
            channels = float(params["n_layers"] * inp["paddles_per_layer"] * 2)
        elif name == "calorimeter-block":
            m = self._material(params["absorber_material"])
            mass = inp["block_area_m2"] * params["depth_X0"] * m["radiation_length_cm"] * 0.01 * m["density_g_cm3"] * 1000
            channels = inp["block_area_m2"] / inp["cell_size_m"] ** 2
        elif name == "rich-block":
            mass, channels = inp["block_area_m2"] * inp["areal_mass_kg_m2"], inp["block_area_m2"] / inp["pixel_size_m"] ** 2
        else:
            raise UsageError(f"unknown budget model {name!r} in roles.json")
        power = (inp["power_per_tesla_W"] * params["field_T"] if name == "magnet-placeholder"
                 else channels * inp["power_per_channel_W"])
        data = 0.0 if name == "magnet-placeholder" else channels * inp["data_per_channel_Mbit_s"]
        src = (f"role rule {slot['role']} budget model {name} (roles.json {self.rules_version}): {model['description']}; "
               "assumed model inputs, not a design")
        rows = {}
        for q, unit, est in (("mass", "kg", mass), ("power", "W", power), ("channel_count", "1", channels),
                             ("data_rate", "Mbit/s", data)):
            rows[q] = {"estimate": float(est), "uncertainty": float(est) * self.rel_unc, "unit": unit,
                       "basis": "estimate", "source": src, "fidelity": "F1"}
        return rows

    def decode(self, g: list, source: str, cid: str) -> tuple[dict, dict]:
        """The design-candidate extension of genome g (parameters with this source, status proposal), and facts about
        it: topology, dropped subsystems, parents, extents."""
        vals = self.values(g)
        subs = json.loads(json.dumps(self.base_subs))
        overrides: dict = {}
        rows: dict = {}
        dropped = [s["sid"] for s in self.slots if s["base"] and not vals[s["sid"]]["enabled"]]
        topo = []
        for s in self.slots:
            st = vals[s["sid"]]
            if not st["enabled"]:
                continue
            rule = self.rules.get(s["role"], {})
            units = {n: p["unit"] for n, p in s["params"].items()}
            n_planes = next((len(v) for k, v in st["params"].items() if s["params"][k]["kind"] == "positions"), None)
            if n_planes is None and s["base"]:
                pos = (subs[s["sid"]]["parameters"].get("layer_positions_m") or {}).get("value")
                n_planes = len(pos) if isinstance(pos, list) and s["role"] == "tracking" and self._has_sensor(s) else None
            params = dict(st["params"])
            der = self._derived(s, params, n_planes)
            units.update({k: (rule.get("derived", {}).get(k) or {}).get("unit")
                          or subs.get(s["sid"], {}).get("parameters", {}).get(k, {}).get("unit", "1") for k in der})
            params.update(der)
            new = {k: {"value": v, "unit": units[k], "source": source, "status": "proposal"} for k, v in params.items()}
            if s["base"]:
                old = subs[s["sid"]]["parameters"]
                changed = {k: p for k, p in new.items()
                           if k not in old or old[k].get("value") != p["value"] or old[k].get("unit") != p["unit"]}
                if changed:
                    overrides[s["sid"]] = {"parameters": changed}
                    old.update(changed)
                if s["sid"] in self.regenerate:
                    for q, row in self._budget_rows(s, {k: v["value"] for k, v in old.items()}).items():
                        rows.setdefault(q, {})[s["sid"]] = row
            else:
                sub = {"role": s["role"], "technology": rule["technology"], "parameters": new,
                       "interfaces": [st["parent"]] if st["parent"] else [],
                       "calibration": json.loads(json.dumps(rule["calibration"]))}
                overrides[s["sid"]] = sub
                subs[s["sid"]] = sub
                for q, row in self._budget_rows(s, params).items():
                    rows.setdefault(q, {})[s["sid"]] = row
            topo.append(f"{s['sid']}:{s['role']}" + (f"[N={n_planes}]" if n_planes is not None else ""))
        topology = "+".join(sorted(topo + [f"{sid}:{sub['role']}" for sid, sub in sorted(subs.items())
                                           if sid not in vals and sid not in dropped]))
        ext: dict = {"candidate_id": cid, "design_id": self.design_id}
        if dropped:
            for sid in dropped:
                subs.pop(sid)
            for sub in subs.values():
                if sub.get("interfaces"):
                    sub["interfaces"] = [i for i in sub["interfaces"] if i not in dropped]
            budgets = {q: {sid: r for sid, r in rows_.items() if sid not in dropped}
                       for q, rows_ in json.loads(json.dumps(self.base_budgets)).items()}
            for q, rows_ in rows.items():
                budgets.setdefault(q, {}).update(rows_)
            ext.update(description=f"{source}: an independent copy of {self.base} without {', '.join(dropped)} "
                                   "(a dropped subsystem cannot be an override)", subsystems=subs)
            if any(budgets.values()):
                ext["budgets"] = {q: r for q, r in budgets.items() if r}
        else:
            ext.update(description=f"{source}: overrides on {self.base}", derived_from=self.base, overrides=overrides)
            if rows:
                ext["budgets"] = rows
        facts = {"topology": topology, "dropped": dropped, "values": vals, "subsystems": subs}
        return ext, facts

    def violation(self, facts: dict) -> tuple[float, list[str]]:
        """v = sum of normalised violations (section C.4.5): spacing shortfall / minimum spacing, length outside the
        envelope / envelope length, overlap length / envelope length (or the union of the two extents), and the
        number of daughters nested deeper than one level."""
        v, why = 0.0, []
        vals = facts["values"]
        length = self.envelope
        extents = []
        for s in self.slots:
            st = vals[s["sid"]]
            if not st["enabled"]:
                continue
            for name, p in s["params"].items():
                if p["kind"] != "positions":
                    continue
                x = sorted(st["params"][name])
                for a, b in zip(x, x[1:]):
                    short = p["min_spacing"] - (b - a)
                    if short > 1e-12 * max(1.0, p["min_spacing"]):
                        v += short / p["min_spacing"] if p["min_spacing"] > 0 else 1.0
                        why.append(f"spacing: {s['sid']}.{name} planes {a:.6g} and {b:.6g} closer than {p['min_spacing']}")
                if length:
                    out = sum(max(0.0, -z) + max(0.0, z - length) for z in x)
                    if out > 0:
                        v += out / length
                        why.append(f"envelope: {s['sid']}.{name} reaches outside [0, {length}] m")
            ext = self.rules.get(s["role"], {}).get("extent")
            if ext:
                p = st["params"]
                if s["base"]:  # a base slot decodes only its free parameters: the others keep the base value
                    p = {**{k: q.get("value") for k, q in self.base_subs[s["sid"]]["parameters"].items()}, **p}
                need = [ext["front"]] + ([ext["depth_x0"], ext["material"]] if "depth_x0" in ext
                                         else [ext["length_cm"]])
                if any(p.get(k) is None for k in need):
                    continue
                front = p[ext["front"]]
                if "depth_x0" in ext:
                    size = p[ext["depth_x0"]] * self._material(p[ext["material"]])["radiation_length_cm"] * 0.01 / \
                        ext["absorber_fraction"]
                else:
                    size = p[ext["length_cm"]] * 0.01 + ext["expansion_m"]
                extents.append((s["sid"], st["parent"], front, front + size))
                if length and (front < 0 or front + size > length):
                    v += (max(0.0, -front) + max(0.0, front + size - length)) / length
                    why.append(f"envelope: {s['sid']} extends outside [0, {length}] m")
        for i, (sa, pa, a0, a1) in enumerate(extents):
            for sb, pb, b0, b1 in extents[i + 1:]:
                if pa == sb or pb == sa:
                    continue
                ov = min(a1, b1) - max(a0, b0)
                if ov > 0:
                    v += ov / (length or (max(a1, b1) - min(a0, b0)))
                    why.append(f"overlap: {sa} and {sb} overlap by {ov:.6g} m")
        for s in self.slots:
            parent = vals[s["sid"]]["parent"]
            if vals[s["sid"]]["enabled"] and parent and vals.get(parent, {}).get("parent"):
                v += 1.0
                why.append(f"nesting: {s['sid']} is a daughter of a daughter ({parent})")
        return v, why


def search_value(proj: design.Project, tools: InProcessTools, cid: str, t: dict) -> dict:
    """C1.4: one F1 search value of candidate cid (already in proj) for target t, computed in this process by the
    tool contract's tool with the arguments contracts/design.py recomputes, the upstream first for a chained figure
    of merit. No formula of its own; a value outside the tool's validity domain carries in_domain false."""
    contract, op, fd = t["hit"]
    ns = cid.split(":", 1)[0]
    ups = []
    if t.get("upstream"):
        u = search_value(proj, tools, cid, dict(t["upstream"], upstream=None))
        if u.get("value") is None:
            return {"value": None, "error": f"upstream {t['upstream']['figure_of_merit']}: {u.get('error')}"}
        uext = {"evaluation_id": f"{ns}:CALC-search-upstream", "candidate": cid,
                "figure_of_merit": t["upstream"]["figure_of_merit"], "denominator": t["upstream"]["denominator"],
                "value": u["value"], "bound": u["bound"], "fidelity": "F1"}
        if u.get("uncertainty"):
            uext["uncertainty"] = u["uncertainty"]
        ue = design.Evaluation(proj.root / "evaluations/CALC-search-upstream.json",
                               "evaluations/CALC-search-upstream.json", {"extension": uext, "inputs": []})
        ue.bound = u["derived_bound"]
        ue.better = (proj.registry.fom_design(t["upstream"]["figure_of_merit"]) or {}).get("better")
        ups.append(ue)
    ev = design.Evaluation(proj.root / "evaluations/CALC-search.json", "evaluations/CALC-search.json",
                           {"extension": {"evaluation_id": f"{ns}:CALC-search", "candidate": cid,
                                          "figure_of_merit": t["figure_of_merit"], "denominator": t["denominator"],
                                          "bound": "estimate", "fidelity": "F1", "unit": fd["unit"]}, "inputs": []})
    ev.upstreams = ups
    prep = design.prepare(proj, ev, fd)
    if prep.errors or prep.invalid:
        return {"value": None, "error": "; ".join(prep.errors + prep.invalid)}
    argv = tool_arguments(op, fd, prep, "unvalidated", tools.config_file)
    code, output = tools.call(contract["entry"], argv)
    if code != 0 or output is None:
        return {"value": None, "error": f"{contract['entry']} exited {code}: {(output or {}).get('error', '')}".strip()}
    value, path, bound, domain, unc = tool_result(fd, prep, t["denominator"], output)
    if value is None:
        return {"value": None, "error": f"the tool gave no number at {path!r}"}
    out = {"value": value, "bound": bound if bound != "mixed" else "estimate", "derived_bound": bound,
           "in_domain": not domain}
    if unc is not None:
        out["uncertainty"] = unc
    return out


def search_design(args) -> dict:
    """C1.6: S1 (structure and parameter search on in-process F1 search values: Sobol designs and the designer's
    proposals, then NSGA-II) and S3 (finalists), recorded as one computational-run with a search_summary. Writes no
    design-candidate and no evaluation."""
    import random
    import tempfile
    HV, NSGA2, SOBOL = search_lib()
    proj = load_project(args)
    if not re.match(r"^SEARCH-[A-Za-z0-9][A-Za-z0-9._-]*$", args.id):
        raise UsageError(f"--id {args.id!r}: a search id is SEARCH- followed by letters, digits, '.', '_' or '-'")
    run_rel = f"runs/{args.id}.computational-run.json"
    points_rel = f"runs/{args.id}.points.jsonl"
    if (proj.root / run_rel).exists() or (proj.root / points_rel).exists():
        raise UsageError(f"{run_rel} exists: a new search is a new --id")
    spec_path = proj.root / args.spec
    if not spec_path.is_file():
        raise UsageError(f"--spec {args.spec} is not a file in the artifacts_dir")
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise UsageError(f"--spec {args.spec} is not readable JSON: {exc}") from None
    from contracts.schema import validate as schema_validate
    rep = schema_validate(spec, "design_search_spec.json")
    if not rep.ok:
        raise UsageError("the search spec fails design-search-spec/1: " + "; ".join(
            f"{f.path}: {f.message}" for f in rep.errors[:8]))
    spec_sha = sha256(spec_path)
    cur = current_spec(proj, None)
    cur_rel = next(proj.rel(p) for p, d in proj.docs.items() if d is cur)
    if proj.resolve(spec["design_spec"]["path"]) != proj.resolve(cur_rel) or \
            spec["design_spec"]["sha256"] != sha256(proj.root / cur_rel):
        raise UsageError(f"the search spec names {spec['design_spec']['path']} ({spec['design_spec']['sha256'][:12]}), "
                         f"the current design-spec is {cur_rel} ({sha256(proj.root / cur_rel)[:12]}): a requirement "
                         "change is a new design-spec version and a new search")
    g4_budget = (spec.get("budget") or {}).get("geant4", 0)
    g4 = spec.get("geant4")
    if bool(g4_budget) != bool(g4):
        raise UsageError("budget.geant4 > 0 and the geant4 block go together (C2.2): Geant4 search values need both")
    if g4 and not getattr(args, "geant4_work", None):
        raise UsageError("budget.geant4 > 0: give --geant4-work DIR (runs, scratch artifacts and cache, kept outside "
                         "the artifacts_dir) and HEP_GEANT4_CONFIG (element_sim, simreco, build_record)")
    if g4 and not (g4.get("targets")):
        raise UsageError("geant4.targets names no objective")
    if len(spec["objectives"]) > MAX_OBJECTIVES:
        raise UsageError(f"{len(spec['objectives'])} objectives: at most {MAX_OBJECTIVES} (exact hypervolume); express "
                         "the rest as constraints")
    roles, roles_sha = load_asset("roles.json", "rules_version", spec["rules_version"])
    materials, materials_sha = load_asset("materials.json", "materials_version", spec["materials_version"])
    space = SearchSpace(proj, spec, roles, materials, args.id)
    spec_ext = cur["extension"]
    objectives = [resolve_target(proj, spec_ext, t, "objective") for t in spec["objectives"]]
    constraints = [resolve_target(proj, spec_ext, t, "constraint") for t in spec.get("constraints") or []]
    seen: dict[str, int] = {}
    for t in objectives + constraints:
        n = seen.get(t["label"], 0)
        seen[t["label"]] = n + 1
        if n:
            t["label"] = f"{t['label']}#{n + 1}"
    if g4:
        labels = {t["label"]: t for t in objectives}
        unknown = sorted(set(g4["targets"]) - set(labels))
        if unknown:
            raise UsageError(f"geant4.targets {unknown} are not objective labels ({sorted(labels)})")
    budget = spec["budget"]["evaluations"]
    max_evals = min(budget, args.max_evaluations) if args.max_evaluations else budget
    opt = spec["optimizer"]
    settings = {"seed": opt["seed"], "population": opt["population"], "generations": opt["generations"],
                "eta_c": opt.get("eta_c", 15.0), "eta_m": opt.get("eta_m", 20.0),
                "p_crossover": opt.get("p_crossover", 0.9), "p_mutation": opt.get("p_mutation", 1.0 / len(space.genes)),
                "window": (spec.get("stopping") or {}).get("hypervolume_window"),
                "min_improvement": (spec.get("stopping") or {}).get("min_improvement", 0.0)}
    if len(space.genes) > 128:
        raise UsageError(f"{len(space.genes)} genes exceed the 128 Sobol dimensions shipped")
    proposals = []
    for prop in spec.get("proposals") or []:
        g0 = space.proposal_genome(prop)
        g1, notes = space.repair(g0)
        proposals.append((prop, g1, notes))
    if len(proposals) > opt["population"]:
        raise UsageError("more proposals than the population size")
    sign = [1.0 if t["better"] == "smaller" else -1.0 for t in objectives]
    scale = [abs(t["reference_point"]) for t in objectives]
    ref = [s * t["reference_point"] / a for s, t, a in zip(sign, objectives, scale)]
    cid = f"{space.ns}:search-point"
    cpath = proj.root / ".search" / "search-point.json"
    points: list[dict] = []
    cache: dict[str, int] = {}
    counts = {"F1": 0, "invalid": 0}
    proposal_of: dict[int, str] = {}

    with tempfile.TemporaryDirectory() as tmp:
        tools = InProcessTools(Path(tmp))

        def new_point(g: list, proposer: str) -> int:
            ext0, facts0 = space.decode(g, f"search {args.id}", cid)
            key = canonical({"subsystems": {sid: {"role": s["role"], "interfaces": s.get("interfaces", []),
                                                  "parameters": {n: [p["value"], p["unit"]]
                                                                 for n, p in s["parameters"].items()}}
                                            for sid, s in facts0["subsystems"].items()
                                            if sid not in facts0["dropped"]},
                             "budgets": ext0.get("budgets")})
            if key in cache:
                return cache[key]
            k = len(points)
            ext, facts = space.decode(g, f"search {args.id} point {k}", cid)
            proj.docs[cpath] = {"artifact_type": "design-candidate", "extension": ext}
            proj.candidates[cid] = cpath
            point = {"index": k, "effective_digest": proj.effective_digest(cid), "topology": facts["topology"],
                     "genome": space.genome_dict(g), "proposer": proposer, "values": {}, "violation": 0.0}
            v, why = space.violation(facts)
            vals: dict = {}
            if v > 0:  # C1.3: an invalid design is not evaluated; it competes through its violation
                counts["invalid"] += 1
                point["evaluated"] = False
            else:
                for t in objectives + constraints:
                    r = search_value(proj, tools, cid, t)
                    r.pop("derived_bound", None)
                    vals[t["label"]] = r
                for t in objectives:
                    if vals[t["label"]].get("value") is None:
                        v += 1.0
                        why.append(f"no search value for {t['label']}: {vals[t['label']].get('error')}")
                for t in constraints:
                    cv = violation_of(t, vals[t["label"]].get("value"))
                    if cv > 0:
                        v += cv
                        why.append(f"constraint {t['label']} not met on its search value"
                                   + ("" if vals[t["label"]].get("value") is not None
                                      else f" (no value: {vals[t['label']].get('error')})"))
            point.update(values=vals, violation=v)
            if why:
                point["reasons"] = why
            points.append(point)
            cache[key] = k
            return k

        def objective_vector(k: int) -> list[float]:
            vals = points[k]["values"]
            out = []
            for s, t, a in zip(sign, objectives, scale):
                x = (vals.get(t["label"]) or {}).get("value")
                out.append(s * x / a if x is not None else math.inf)
            return out

        def evaluate(g: list):
            counts["F1"] += 1
            k = new_point(g, "random")
            return NSGA2.Individual(genome=g, objectives=objective_vector(k), violation=points[k]["violation"], key=k)

        def hv_of(pop: list) -> float:
            return HV.hypervolume([i.objectives for i in pop if i.violation == 0], ref)

        try:
            for prop, g, notes in proposals:  # recorded first, as proposer llm; the population evaluates them again
                k = new_point(g, "llm")
                proposal_of.setdefault(k, prop["id"])
                if notes:
                    points[k].setdefault("repairs", []).extend(notes)
            sob = SOBOL.Sobol(len(space.genes)).points(1, opt["population"] - len(proposals))
            initial = [g for _, g, _ in proposals] + [NSGA2.from_unit(space.genes, u) for u in sob]
            result = NSGA2.run(space.genes, initial, evaluate, lambda g: space.repair(g)[0], hv_of, settings, max_evals)
            s2 = geant4_refinement(args, proj, space, spec, objectives, points, new_point, objective_vector,
                                   NSGA2, HV) if g4 else None
        finally:
            proj.docs.pop(cpath, None)
            proj.candidates.pop(cid, None)
        seconds_per_call = tools.seconds / tools.calls if tools.calls else None
        tool_calls = tools.calls
    feasible = [p["index"] for p in points if p["violation"] == 0]
    if feasible:
        vecs = {k: objective_vector(k) for k in feasible}
        front = [k for k in feasible if not any(HV.dominates(vecs[j], vecs[k]) for j in feasible if j != k)]
    else:
        vmin = min((p["violation"] for p in points), default=0.0)
        front = [p["index"] for p in points if p["violation"] == vmin]
    inds = [NSGA2.Individual(genome=[], objectives=objective_vector(k), violation=points[k]["violation"], key=k)
            for k in front]
    NSGA2.crowding(inds, list(range(len(inds))))
    order = sorted(inds, key=lambda i: (-i.crowding, i.key))
    finalists, topologies = [], set()
    for ind in (order if s2 is None else []):
        topo = points[ind.key]["topology"]
        if spec["finalists"].get("distinct_topologies", True) and topo in topologies:
            continue
        topologies.add(topo)
        finalists.append(ind.key)
        if len(finalists) >= spec["finalists"]["max"]:
            break
    if s2 is not None:  # C2.4: the finalists are S2's survivors, fixed from the Geant4 search values before expand
        finalists = list(s2["finalists"])[:spec["finalists"]["max"]]
    finalists.sort()

    def all_values(p: dict) -> bool:
        return all((p["values"].get(t["label"]) or {}).get("value") is not None for t in objectives + constraints)
    rng = random.Random(opt["seed"] + 1)
    pool = [p["index"] for p in points if p["violation"] == 0 and p["index"] not in finalists and all_values(p)]
    n_sample = min(spec.get("consistency_samples", 20), len(pool))
    sample = sorted(rng.sample(pool, n_sample)) if n_sample else []
    checked = [k for k in finalists if all_values(points[k])] + sample  # an invalid design has no value to compare
    consistency = consistency_check(args, proj, space, objectives + constraints, points, checked)
    if consistency["max_relative_difference"] is not None and consistency["max_relative_difference"] > CONSISTENCY_TOL:
        return {"status": "failed", "exit": 1, "error": "an in-process search value differs from evaluate_design.py run "
                f"beyond {CONSISTENCY_TOL} (C1.4); nothing was written", "consistency": consistency}
    front_hv = None
    if len(objectives) <= 3 or len(front) <= 1000:
        front_hv = HV.hypervolume([objective_vector(k) for k in front if points[k]["violation"] == 0], ref)
    for k, pid in proposal_of.items():
        points[k]["proposal"] = pid
    w = Writer(proj)
    inline_max = spec.get("inline_points_max", 2000)
    keep = set(front) | set(finalists) | set(sample)
    summary_points = points if len(points) <= inline_max else [p for p in points if p["index"] in keep]
    output_hashes = {}
    points_file = None
    if summary_points is not points:
        body = "".join(json.dumps(p, sort_keys=True) + "\n" for p in points)
        w.write(points_rel, body.encode("utf-8"))
        output_hashes[points_rel] = sha256(proj.root / points_rel)
        points_file = {"ref": points_rel, "sha256": output_hashes[points_rel], "count": len(points)}
    chain_rels = [proj.rel(p) for p in proj.candidate_chain(space.base)]
    inputs = [w.input_ref(cur_rel)] + [dict(w.input_ref(r), binding="parameters") for r in chain_rels]
    script = "skills/hep-detector/scripts/evaluate_design.py"
    assets = [("skills/hep-detector/assets/design-search/roles.json", roles_sha),
              ("skills/hep-detector/assets/design-search/materials.json", materials_sha),
              ("skills/hep-detector/assets/design-search/sobol_joe_kuo.txt",
               sha256(SEARCH_ASSETS / "sobol_joe_kuo.txt"))]
    used_tools = sorted({t["hit"][0]["entry"] for t in objectives + constraints}
                        | {t["upstream"]["hit"][0]["entry"] for t in objectives + constraints if t.get("upstream")})
    lib = sorted(f"skills/hep-detector/scripts/design_search_lib/{p.name}" for p in SEARCH_LIB.glob("*.py"))
    argv = ["python3", script, "search", "--spec", args.spec, "--id", args.id] + (
        ["--max-evaluations", str(args.max_evaluations)] if args.max_evaluations else [])

    def public(t: dict) -> dict:
        out = {k: t[k] for k in ("label", "figure_of_merit", "denominator", "requirement", "tool", "better",
                                 "comparator", "target") if t.get(k) is not None}
        if t.get("reference_point") is not None:
            out["reference_point"] = t["reference_point"]
        if t.get("upstream"):
            out["upstream"] = {"figure_of_merit": t["upstream"]["figure_of_merit"], "tool": t["upstream"]["tool"],
                               "denominator": t["upstream"]["denominator"]}
        return out
    summary = {
        "search_id": args.id, "search_spec": args.spec, "search_spec_sha256": spec_sha, "design_spec": cur_rel,
        "design_spec_sha256": sha256(proj.root / cur_rel), "base_candidate": space.base,
        "base_candidate_chain": [{"path": r, "sha256": sha256(proj.root / r)} for r in chain_rels],
        "rules_version": spec["rules_version"], "rules_sha256": roles_sha,
        "materials_version": spec["materials_version"], "materials_sha256": materials_sha,
        "objectives": [public(t) for t in objectives], "constraints": [public(t) for t in constraints],
        "reference_point_normalised": ref,
        "budget": {"evaluations": budget, "geant4": g4_budget, "max_evaluations": max_evals},
        "optimizer": {"name": "nsga2", "implementation": "evaluate_design.py search (design_search_lib.nsga2)",
                      "backend": None, "seed": opt["seed"],
                      "config": {k: v for k, v in settings.items() if k != "seed"},
                      "initialisation": {"sobol_skip": 1, "proposals": len(proposals)},
                      "generations_run": result["generations"], "stopped": result["stopped"]},
        "levels": ["F1", "geant4"] if s2 else ["F1"],
        "genome": [{k: v for k, v in g.items()} for g in space.genes],
        "evaluated": {"F1": counts["F1"], "geant4": s2["runs"] if s2 else 0, "distinct_designs": len(points),
                      "topologies": len({p["topology"] for p in points}), "invalid_not_evaluated": counts["invalid"],
                      "tool_calls": tool_calls},
        "points": summary_points, "front": sorted(front),
        "hypervolume": [{"generation": g_, "value": v_} for g_, v_ in result["hypervolume"]],
        "front_hypervolume": front_hv,
        "finalists": [{"index": k, "fixed_before": "expand", "topology": points[k]["topology"],
                       **({"fixed_from": "geant4"} if s2 else {})} for k in finalists],
        "proposals": [{"id": prop["id"], "reason": prop["reason"],
                       "index": next((k for k, pid in proposal_of.items() if pid == prop["id"]), None)}
                      for prop, _, _ in proposals],
        "consistency": consistency,
        "seeds": {"optimizer": opt["seed"], "geant4_search": s2["seeds"] if s2 else []},
        "timing": {"seconds_per_tool_call": seconds_per_call},
        "note": SEARCH_NOTE}
    if points_file:
        summary["points_file"] = points_file
    if s2:
        summary["geant4"] = s2["record"]
    ext = {"input_manifest": [{"path": args.spec, "sha256": spec_sha}, {"path": cur_rel, "sha256": sha256(proj.root / cur_rel)}]
           + [{"path": r, "sha256": sha256(proj.root / r)} for r in chain_rels]
           + [{"path": p, "sha256": h} for p, h in assets]
           + ([{"path": g4["realization"], "sha256": sha256(proj.root / g4["realization"])}] if g4 else []),
           "tools": [{"name": "evaluate_design.search", "version": plugin_version()}]
           + [{"name": Path(e).stem, "version": plugin_version()} for e in used_tools],
           "commands": [" ".join(argv)],
           "environment": {"python": platform.python_version(), "platform": platform.platform(terse=True)},
           "seeds": {"optimizer": opt["seed"]}, "tolerances": {"consistency_relative": CONSISTENCY_TOL},
           "exit_status": 0, "output_hashes": output_hashes, "argv": argv,
           "script_sha256": {p: sha256(PLUGIN / p) for p in [script, *lib, *used_tools]},
           "search_summary": summary}
    run_doc = envelope("computational-run", f"{space.ns}-{args.id}", ext, inputs,
                       [{"ref": points_rel}] if points_file else [], statuses(inputs, args.status))
    w.json(run_rel, run_doc)
    from contracts.validate import validate_artifact
    rep = validate_artifact(json.loads((proj.root / run_rel).read_text(encoding="utf-8")))
    if not rep.ok:
        w.undo()
        return {"status": "failed", "exit": 1, "error": "the search run fails contract validation",
                "findings": [f.as_dict() for f in rep.errors]}
    return {"status": "ok", "exit": 0, "search": run_rel,
            "search_size": {"evaluations": counts["F1"], "distinct_designs": len(points),
                            "topologies": summary["evaluated"]["topologies"]},
            "stopped": result["stopped"], "front": len(front),
            "finalists": [{"index": k, "topology": points[k]["topology"], "violation": points[k]["violation"],
                           "values": {lab: v.get("value") for lab, v in points[k]["values"].items()}} for k in finalists],
            "consistency": {"checked": consistency["checked"],
                            "max_relative_difference": consistency["max_relative_difference"]},
            "next": [f"evaluate_design.py expand --artifacts DIR --search {run_rel} --point {k} --candidate-id NAME"
                     for k in finalists],
            "note": SEARCH_NOTE + "; state the search size and that the finalists are not confirmed in the reply"}


def geant4_refinement(args, proj: design.Project, space: SearchSpace, spec: dict, objectives: list[dict],
                      points: list[dict], new_point, objective_vector, NSGA2, HV) -> dict:
    """C2.2-C2.3, S2: refine the top_k designs of distinct topologies of the S1 search front on Geant4 search values.
    Every generation is one seed_group (S = H(search_id, "search", gen-g)): the survivors are re-evaluated with the
    generation's offspring (continuous genes mutated), so each comparison within a generation is paired. Gate G-C2a:
    in generation 0 (the trial) the median Var(independent) / Var(paired) of the child-parent differences; below the
    threshold the later generations seed every design on its own (noted). Survival keeps one design per topology,
    by constrained non-dominated sorting on the objectives (the Geant4 value where a target is declared, the F1 search
    value otherwise). No verdict, no ranking: the survivors become the finalists."""
    import random
    import statistics as st
    from core.simulation.seeds import search_group_seed
    from core.stats.decisions import paired_statistic
    scripts = str(SEARCH_LIB.parent)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from design_search_lib.geant4_values import Geant4SearchError, Geant4Values
    g4 = spec["geant4"]
    budget = spec["budget"]["geant4"]
    cfg_path = os.environ.get("HEP_GEANT4_CONFIG")
    if not cfg_path:
        raise UsageError("budget.geant4 > 0 needs HEP_GEANT4_CONFIG (element_sim, simreco, build_record)")
    cfg = json.loads(Path(os.path.expanduser(cfg_path)).read_text(encoding="utf-8"))
    try:
        vals = Geant4Values(cfg, Path(args.geant4_work).expanduser().resolve() / args.id, proj.root, args.id, g4,
                            created())
    except Geant4SearchError as exc:
        raise UsageError(str(exc)) from None
    labels = [t["label"] for t in objectives]
    by_label = {t["label"]: t for t in objectives}
    # the top_k designs of distinct topologies: all evaluated designs ranked by constrained non-dominated sorting and,
    # within a front, by crowding distance; the first design of each topology until top_k (the S1 front alone may
    # hold a single topology)
    pool = [NSGA2.Individual(genome=[], objectives=objective_vector(p["index"]), violation=p["violation"],
                             key=p["index"]) for p in points if p.get("evaluated", True)]
    parents: dict[str, int] = {}
    for fr in NSGA2.sort_fronts(pool):
        NSGA2.crowding(pool, fr)
        for i in sorted(fr, key=lambda j: (-pool[j].crowding, pool[j].key)):
            if len(parents) < g4["top_k"]:
                parents.setdefault(points[pool[i].key]["topology"], pool[i].key)
        if len(parents) >= g4["top_k"]:
            break
    cont = [i for i, g in enumerate(space.genes) if g["type"] == "real"]
    rng = random.Random(spec["optimizer"]["seed"] + 2)
    eta = spec["optimizer"].get("eta_m", 20.0)
    threshold = float(g4.get("paired_threshold", 2.0))
    paired, gate, generations, seeds_used = True, None, [], []
    last_vectors: dict[int, list[float]] = {}
    sign = {t["label"]: (1.0 if t["better"] == "smaller" else -1.0) for t in objectives}
    for gen in range(g4["generations"]):
        group = f"gen-{gen}"
        members: list[tuple[int, int | None]] = []
        for topo, k in sorted(parents.items()):
            members.append((k, None))
            for _ in range(g4["offspring"] if cont else 0):
                child = list(space.genome_from_dict(points[k]["genome"]))
                must = rng.choice(cont)
                for i in cont:
                    if i == must or rng.random() < 1.0 / len(cont):
                        gd = space.genes[i]
                        child[i] = NSGA2._poly_mutation(float(child[i]), gd["lo"], gd["hi"], eta, rng)
                kk = new_point(space.repair(child)[0], "random")
                if points[kk]["topology"] == topo and kk not in [m for m, _ in members]:
                    members.append((kk, k))
        need = len(members) * len(g4["targets"])
        if vals.runs + need > budget:
            generations.append({"generation": gen, "stopped": f"the Geant4 budget ({budget} runs) would be exceeded "
                                f"({vals.runs} used, {need} needed)"})
            break
        results: dict[int, dict] = {}
        for k, _ in members:
            seed = search_group_seed(args.id, group if paired else f"{group}:p{k}")
            if seed not in seeds_used:
                seeds_used.append(seed)
            short = f"search-g{gen}-p{k}"
            base_rel = proj.rel(proj.candidates[space.base])
            doc = expanded_candidate(space, points[k], short,
                                     [dict(Writer(proj).input_ref(base_rel), binding="parameters")])
            cid = f"{space.ns}:{short}"
            row = {}
            for label in sorted(g4["targets"]):
                try:
                    row[label] = vals.value(Path(__file__).resolve(), doc, cid, short, points[k]["effective_digest"],
                                            label, by_label[label], seed, group if paired else None, k)
                except Geant4SearchError as exc:
                    row[label] = {"value": None, "error": str(exc)[:500], "seed": seed}
            results[k] = row
            points[k].setdefault("geant4", []).append({"generation": gen, "seed_group": group if paired else None,
                                                       "seed": seed, "values": row})
        if gen == 0:  # gate G-C2a on the trial generation: child-parent differences of each target
            ratios = []
            for k, par in members:
                if par is None:
                    continue
                for label in g4["targets"]:
                    a, b = results[k].get(label) or {}, results[par].get(label) or {}
                    if a.get("blocks") and b.get("blocks") and len(a["blocks"]) == len(b["blocks"]):
                        se_p = paired_statistic((a["blocks"], b["blocks"]), "absolute")["se"]
                        if se_p > 0:
                            ratios.append((a["se"] ** 2 + b["se"] ** 2) / se_p ** 2)
            ratio = st.median(ratios) if ratios else None
            paired = ratio is not None and ratio >= threshold
            gate = {"variance_ratio": ratio, "pairs": len(ratios), "threshold": threshold,
                    "comparison_after_trial": "paired" if paired else "independent",
                    "note": None if paired else "Var(independent) / Var(paired) below the threshold (or not "
                    "measurable): later generations seed every design on its own"}

        def vector(k: int) -> list[float]:
            out = []
            for t, x in zip(objectives, objective_vector(k)):
                r = results[k].get(t["label"]) if t["label"] in g4["targets"] else None
                if r is not None:
                    v = r.get("value")
                    out.append(sign[t["label"]] * v / abs(t["reference_point"]) if v is not None else math.inf)
                else:
                    out.append(x)
            return out
        survivors = {}
        for topo in sorted(parents):
            pool = [NSGA2.Individual(genome=[], objectives=vector(k), violation=points[k]["violation"], key=k)
                    for k, _ in members if points[k]["topology"] == topo]
            survivors[topo] = NSGA2.survive(pool, 1)[0].key
        generations.append({"generation": gen, "seed_group": group if paired or gen == 0 else None,
                            "comparison": "paired" if (paired or gen == 0) else "independent",
                            "members": [{"index": k, "parent": par} for k, par in members],
                            "survivors": sorted(survivors.values())})
        parents = survivors
        last_vectors = {k: vector(k) for k in survivors.values()}
    # the survivors in the order the finalists rule takes them: rank and crowding on their last Geant4 values
    order = sorted(parents.values())
    if generations and "members" in generations[-1]:
        pool = [NSGA2.Individual(genome=[], objectives=last_vectors[k], violation=points[k]["violation"], key=k)
                for k in order]
        ranked = []
        for fr in NSGA2.sort_fronts(pool):
            NSGA2.crowding(pool, fr)
            ranked += [pool[i].key for i in sorted(fr, key=lambda j: (-pool[j].crowding, pool[j].key))]
        order = ranked
    record = {"targets": g4["targets"], "events": vals.events, "blocks": vals.blocks, "top_k": g4["top_k"],
              "generations_declared": g4["generations"], "offspring": g4["offspring"],
              "realization": g4["realization"], "reco": g4["reco"], "versions": vals.versions,
              "gate_g_c2a": gate, "generations": generations, "runs": vals.runs, "cache_hits": vals.cache_hits,
              "labels": labels,
              "note": "Geant4 search values select designs; they are optimistic (no tail source), are not "
                      "evaluations, and their seeds never serve a confirmation study (CV-C2)"}
    return {"finalists": order, "seeds": sorted(seeds_used), "runs": vals.runs, "record": record}


def search_diagnose(args) -> dict:
    """C2.4: the diagnostic run of a search (runs/DIAG-<search id>.computational-run.json): for each candidate expanded
    from one of its finalists, the search value (F1 and, from C2, the last Geant4 search value) minus the official
    evaluation or F4 confirmation of the same figure of merit and denominator. It writes no evaluation and decides
    nothing (winner's curse and model differences, section C.4.6)."""
    proj = load_project(args)
    run_path = proj.resolve(args.diagnose)
    run = proj.docs.get(run_path)
    if run is None or not design.is_search_run(run):
        raise UsageError(f"--diagnose {args.diagnose}: not a search run in the artifacts_dir")
    sid = run["extension"]["search_summary"]["search_id"]
    rows = [r for r in search_minus_official(proj) if r["search"] == sid]
    rel = f"runs/DIAG-{sid}.computational-run.json"
    w = Writer(proj)
    evals = sorted({r["evaluation"] for r in rows})
    eval_rels = [proj.rel(e.path) for e in proj.evals.values() if e.eid in evals]
    inputs = [w.input_ref(proj.rel(run_path))] + [w.input_ref(r) for r in sorted(eval_rels)]
    argv = ["python3", "skills/hep-detector/scripts/evaluate_design.py", "search", "--diagnose", args.diagnose]
    ext = {"input_manifest": [{"path": i["ref"], "sha256": i["sha256"]} for i in inputs],
           "tools": [{"name": "evaluate_design.search_diagnose", "version": plugin_version()}],
           "commands": [" ".join(argv)], "environment": {"python": platform.python_version()}, "seeds": {},
           "tolerances": {}, "exit_status": 0, "output_hashes": {}, "argv": argv,
           "search_diagnostic": {"search": proj.rel(run_path), "rows": rows,
                                 "note": "search values minus official evaluations: a diagnostic of the winner's "
                                         "curse and of model differences; it writes no evaluation and supports no "
                                         "verdict"}}
    doc = envelope("computational-run", f"{sid}-diagnostic", ext, inputs, [], statuses(inputs, "unvalidated"))
    w.json(rel, doc)
    return {"status": "ok", "exit": 0, "diagnostic": rel, "rows": rows,
            "note": "explain any large search_minus_official in the reply; it changes no verdict"}


def expanded_candidate(space: SearchSpace, point: dict, short: str, inputs: list) -> dict:
    ext, _ = space.decode(space.genome_from_dict(point["genome"]), f"search {space.search_id} point {point['index']}",
                          f"{space.ns}:{short}")
    return envelope("design-candidate", f"{space.ns}-{short}", ext, inputs, [], statuses(inputs, "unvalidated"))


def consistency_check(args, proj: design.Project, space: SearchSpace, targets: list[dict], points: list[dict],
                      indices: list[int]) -> dict:
    """C1.4: the in-process search values of the finalists and a sample of points recomputed with run (a subprocess
    of the tool, exactly as an official evaluation) in a scratch copy of the artifacts_dir."""
    import shutil
    import tempfile
    rows, worst = [], None
    if not indices:
        return {"checked": 0, "max_relative_difference": None, "tolerance": CONSISTENCY_TOL, "points": []}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "artifacts"
        shutil.copytree(proj.root, work, ignore=shutil.ignore_patterns("reports", "*.jsonl"))
        for k in indices:
            point = points[k]
            short = f"consistency-{k}"
            base_rel = proj.rel(proj.candidates[space.base])
            doc = expanded_candidate(space, point, short, [dict(Writer(proj).input_ref(base_rel), binding="parameters")])
            (work / "candidates").mkdir(exist_ok=True)
            (work / "candidates" / f"{short}.json").write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
            diffs = {}
            for j, t in enumerate(targets):
                cid = f"{space.ns}:{short}"
                common = dict(artifacts=work, candidate=cid, requirement=None, fidelity="F1", input_artifact=None,
                              replace=False, status="unvalidated")
                ups = []
                if t.get("upstream"):
                    u = run_evaluation(argparse.Namespace(
                        **common, figure_of_merit=t["upstream"]["figure_of_merit"],
                        denominator=[f"{a}={b}" for a, b in t["upstream"]["denominator"].items()],
                        tool=t["upstream"]["tool"], upstream=None, id=f"CALC-cons-{k}-{j}-up"))
                    if u.get("status") != "ok":
                        diffs[t["label"]] = {"error": u.get("error")}
                        continue
                    ups = [u["evaluation"]]
                r = run_evaluation(argparse.Namespace(
                    **common, figure_of_merit=t["figure_of_merit"],
                    denominator=[f"{a}={b}" for a, b in t["denominator"].items()], tool=t["tool"],
                    upstream=ups or None, id=f"CALC-cons-{k}-{j}"))
                mine = (point["values"].get(t["label"]) or {}).get("value")
                if r.get("status") != "ok" or mine is None:
                    diffs[t["label"]] = {"in_process": mine, "run": r.get("value"), "error": r.get("error")}
                    worst = math.inf
                    continue
                d = abs(mine - r["value"]) / max(abs(r["value"]), 1e-300)
                worst = d if worst is None else max(worst, d)
                diffs[t["label"]] = {"in_process": mine, "run": r["value"], "relative_difference": d}
            rows.append({"index": k, "values": diffs})
    return {"checked": len(indices), "max_relative_difference": worst, "tolerance": CONSISTENCY_TOL, "points": rows}


def expand_search(args) -> dict:
    """C1.7: one finalist of a search as a design-candidate, decoded from its genome exactly as the search decoded it
    (the effective digest must agree): derived from the base candidate when it only changes parameters or adds
    subsystems, an independent candidate when it drops one. Points that are not finalists are refused (RSK-04)."""
    proj = load_project(args)
    run_path = proj.resolve(args.search)
    run = proj.docs.get(run_path)
    summary = ((run or {}).get("extension") or {}).get("search_summary")
    if not summary or not design.is_search_run(run or {}):
        raise UsageError(f"--search {args.search} is not a search summary run in the artifacts_dir")
    if args.point not in {f["index"] for f in summary["finalists"]}:
        raise UsageError(f"--point {args.point} is not a finalist of {args.search} (finalists: "
                         f"{', '.join(str(f['index']) for f in summary['finalists']) or 'none'}): only finalists are "
                         "expanded (RSK-04)")
    point = next((p for p in summary["points"] if p["index"] == args.point), None)
    if point is None:
        raise UsageError(f"the search run lacks the record of finalist {args.point}")
    short = args.candidate_id
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", short):
        raise UsageError(f"--candidate-id {short!r}: letters, digits, '.', '_' or '-'")
    rel = f"candidates/{short}.json"
    spec_path = proj.root / summary["search_spec"]
    if not spec_path.is_file() or sha256(spec_path) != summary["search_spec_sha256"]:
        raise UsageError(f"the search spec {summary['search_spec']} is missing or changed since the search")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    roles, roles_sha = load_asset("roles.json", "rules_version", summary["rules_version"])
    materials, materials_sha = load_asset("materials.json", "materials_version", summary["materials_version"])
    if (roles_sha, materials_sha) != (summary["rules_sha256"], summary["materials_sha256"]):
        raise UsageError("the role rules or the materials table changed since the search: rerun the search")
    space = SearchSpace(proj, spec, roles, materials, summary["search_id"])
    w = Writer(proj)
    base_rel = proj.rel(proj.candidates[space.base])
    inputs = [dict(w.input_ref(base_rel), binding="parameters"), w.input_ref(args.search)]
    doc = expanded_candidate(space, point, short, inputs)
    cid = doc["extension"]["candidate_id"]
    if cid in proj.candidates:
        raise UsageError(f"candidate {cid} exists: choose another --candidate-id")
    w.json(rel, doc)
    from contracts.validate import validate_artifact
    rep = validate_artifact(json.loads((proj.root / rel).read_text(encoding="utf-8")))
    if not rep.ok:
        w.undo()
        return {"status": "failed", "exit": 1, "error": "the candidate fails contract validation",
                "findings": [f.as_dict() for f in rep.errors]}
    check = design.Project(proj.root, None)
    design.check_calibration(check)
    design.check_budgets(check)
    errors = [e for e in check.errors if e["path"] == rel]
    if check.effective_digest(cid) != point["effective_digest"]:
        errors.append({"code": "design.contract_mismatch", "message": "the expanded candidate's effective digest "
                       "differs from the point's: the base candidate changed since the search; rerun the search"})
    if errors:
        w.undo()
        return {"status": "failed", "exit": 1, "error": "the expanded candidate fails its design checks",
                "design_errors": errors}
    nxt = []
    for t in summary["objectives"] + summary.get("constraints", []):
        q = next((q for q, f in BUDGET_FOMS.items() if f == t["figure_of_merit"]), None)
        if q:
            nxt.append(f"evaluate_design.py budget --artifacts DIR --candidate {cid} --quantity {q}")
        elif t.get("requirement"):
            nxt.append(f"evaluate_design.py run --artifacts DIR --candidate {cid} --requirement {t['requirement']}")
        else:
            dens = " ".join(f"--denominator {a}={b}" for a, b in t["denominator"].items())
            nxt.append(f"evaluate_design.py run --artifacts DIR --candidate {cid} --figure-of-merit "
                       f"{t['figure_of_merit']} {dens}".rstrip())
    nxt.append("evaluate_design.py plan / report --artifacts DIR (every other evaluation the comparison needs)")
    return {"status": "ok", "exit": 0, "candidate": cid, "file": rel,
            "kind": "derived" if "derived_from" in doc["extension"] else "independent (a subsystem is dropped)",
            "effective_digest": point["effective_digest"], "search_values": {
                lab: v.get("value") for lab, v in point["values"].items()},
            "next": nxt, "note": "the search values are not evaluations; report the expanded candidate's evaluations "
                                 "(report lists search value minus official value, search_minus_official, per finalist)"}


def plan(args) -> dict:
    """RES-04: suggestions for the next evaluations from the derived state."""
    full = design.derive(args.artifacts, args.decisions)
    reg = design.Registry()
    adequacy = design.load_adequacy()
    out = []
    for item in full.get("requirements", []) + full.get("constraints", []):
        rules = adequacy["figures_of_merit"].get(item["quantity"], {})
        for m in item["matrix"]:
            if m["result"] == "pass":
                continue
            cands = m["candidates"]
            levels = [f for f in design.FIDELITIES[1:4] if reg.computes(item["quantity"], f)]
            if m["missing_evaluations"]:
                if levels:
                    s = (f"evaluate_design.py run --requirement {item['id']} --candidate {cands[0]} --fidelity {levels[0]}")
                else:
                    s = (f"no evaluator for {item['quantity']} up to F3: record it with evaluate_design.py run "
                         f"--requirement {item['id']} --candidate {cands[0]} --fidelity {rules.get('screening', 'F1')}")
                out.append({"id": item["id"], "candidates": cands, "why": "no evaluation", "suggest": s})
                continue
            for ev in m["skipped"]:
                if ev.get("code") == "evidence.stale":
                    out.append({"id": item["id"], "candidates": cands, "why": f"{ev['evaluation']} is stale",
                                "suggest": "rerun it (evaluate_design.py run with a new --id); stale files are never edited"})
            for need in m["missing_evidence"]:
                out.append({"id": item["id"], "candidates": cands, "why": f"missing for compliance: {need}",
                            "suggest": "a higher-fidelity evaluation (F2 toy, F3 response, F4 Geant4 study, F5 "
                                       "measurement) or a data validation; where no evaluator exists, record "
                                       "capability.unavailable"})
    for flag in full.get("gate_flags", []):
        out.append({"id": flag, "why": "review gate", "suggest": "prepare the decision record for a human to approve "
                    "(outside the artifacts_dir); a missing gate never blocks computation"})
    return {"status": "ok", "exit": 0, "design_id": full.get("design_id"), "suggestions": out,
            "note": "suggestions only; the program, not the plan, decides compliance"}


def fidelity_cell(m: dict) -> str:
    """MAT-02, MAT-03: the lowest chain fidelity of the deciding evaluations; with none deciding, 'undetermined' and the
    lowest fidelity among the participating ones."""
    if m["maturity"]["lowest_chain_fidelity"]:
        return m["maturity"]["lowest_chain_fidelity"]
    fids = [x["fidelity"] for p in m["maturity"]["participating"] for x in p["fidelity_vector"]]
    return f"undetermined (participating down to {min(fids)})" if fids else "undetermined (no evaluation used)"


def disposition_cell(m: dict) -> str:
    """RPT-05: the proposed disposition; for a derived requirement, approved at H4 under the driving requirement that
    covers it (MAT-04 d)."""
    if m.get("proposed_disposition"):
        under = f" (under {m['disposition_under']})" if m.get("disposition_under") else ""
        return m["proposed_disposition"] + under
    return m.get("disposition_note") or "-"


def render(full: dict, omitted: list[str]) -> str:
    lines = [f"# Design report: {full.get('design_id')}", "",
             f"Derived by contracts/design.py from `{full.get('current_spec')}` (spec version {full.get('spec_version')}); "
             "no verdict is hand-written.", ""]
    lines += [f"**Gate flags (open review gates):** {', '.join(full.get('gate_flags') or ['none'])}.",
              f"**Baseline:** {full.get('baseline', 'draft')}. Only a valid human H4 (design-baseline) record sets it, "
              "taken after the gates above are clear, over this report, the evaluations it used and one disposition per "
              "inconclusive driving requirement of a candidate that survives screening; until then no requirement is "
              "reviewed (MAT-04). The record's actor kind is self-declared, so the review axis is advisory (LIM-01).",
              ""]
    if full.get("adequacy", {}).get("provisional_pass"):
        lines += ["The adequacy table is an initial default until physics review: every pass is provisional.", ""]
    lines += ["| Requirement | Candidates | Result | Reason codes | Lowest fidelity (deciding evaluations) | Status | "
              "Missing for compliance | Proposed disposition |", "|---|---|---|---|---|---|---|---|"]
    for item in full.get("requirements", []) + full.get("constraints", []):
        for m in item["matrix"]:
            kind = item["kind"] + (f", under {item['covered_by']}" if item.get("covered_by") else "") + (
                f"; scope {', '.join(item['subsystems'])}" if item.get("subsystems") else "")
            lines.append(f"| {item['id']} ({kind}) | {', '.join(m['candidates'])} | {m['result']}"
                         f"{' (provisional)' if m['provisional'] else ''} | {', '.join(m['codes']) or '-'} | "
                         f"{fidelity_cell(m)} | "
                         f"{', '.join(m['maturity']['status_axis']) or '-'} | {'; '.join(m['missing_evidence']) or '-'} | "
                         f"{disposition_cell(m)} |")
    lines += ["", "## Evaluations used and skipped", ""]
    for item in full.get("requirements", []) + full.get("constraints", []):
        for m in item["matrix"]:
            for kind in ("used", "skipped"):
                for r in m[kind]:
                    if r["evaluation"] in omitted:
                        continue
                    lines.append(f"- {item['id']} / {', '.join(m['candidates'])}: {kind} {r['evaluation']} "
                                 f"(row {r.get('row', '-')}, {r.get('code')})")
    if omitted:
        lines += ["", f"Omitted from this rendering on request (still aggregated): {', '.join(omitted)}"]
    lines += ["", "## Screening, orphan runs, comparison", ""]
    for c in full.get("candidates", []):
        lines.append(f"- {', '.join(c['candidates'])}: {'screened out by the verdicts above, not by a review decision (' + '; '.join(c['screened_out_reasons']) + ')' if c['screened_out'] else 'not excluded by screening (no driving requirement or hard constraint fails)'}"
                     f"{'; at risk: ' + '; '.join(c['at_risk']) if c['at_risk'] else ''}")
    for o in full.get("orphan_runs", []):
        lines.append(f"- orphan run {o['run']} ({', '.join(o['figures_of_merit'])})")
    if not full.get("orphan_runs"):
        lines.append("- orphan runs: none")
    basis = full.get("comparison_basis", {})
    cl = f" at {basis['coverage_cl']:.0%} one-sided CL" if basis.get("coverage_cl") else ""
    lines.append(f"- comparison basis{' on ' + basis['quantity'] if basis.get('quantity') else ''}{cl}: "
                 f"{'holds' if basis.get('holds') else 'does not hold'}"
                 f"{' (' + basis['reason'] + ')' if basis.get('reason') else ''}"
                 f"{'; basis note: ' + basis['note'] if basis.get('note') else ''}")
    for pr in basis.get("pairs", []):
        shared = (f"; cancelled as the same subsystem with the same budget row in both: {', '.join(pr['shared_items'])}"
                  if pr.get("shared_items") else "; no item is the same subsystem with the same budget row in both")
        how = ("1-sigma budget-row uncertainties, linear within a candidate, in quadrature across the pair"
               if pr.get("item_level") else "the evaluations' total uncertainties in quadrature")
        lines.append(f"  - {'/'.join(pr['candidates'][0])} vs {'/'.join(pr['candidates'][1])} "
                     f"({' vs '.join(pr.get('evaluations', []))}; {how}): difference "
                     f"{pr['difference']:.6g} + one-sided uncertainty {pr['uncertainty_one_sided']:.6g} against "
                     f"tolerance {pr['tolerance']:.6g} ({basis.get('quantity')}){shared}: "
                     f"{'holds' if pr['holds'] else 'does not hold'}")
    rank = full.get("ranking", {})
    if rank.get("status") == "ranked":
        lines.append(f"- ranking on {rank['figure_of_merit']}: "
                     + ", ".join(f"{'/'.join(o['candidates'])} ({o['value']:.6g})" for o in rank["order"])
                     + f"; {rank['note']}")
    else:
        lines.append(f"- ranking: {rank.get('status')}: {'; '.join(rank.get('reasons') or [rank.get('reason')])}")
    par = full.get("pareto", {})
    if par.get("status") == "computed":
        lines.append(f"- Pareto front on {', '.join(par['axes'])}: "
                     + ", ".join("/".join(c) for c in par["front"])
                     + "".join(f"; {'/'.join(x['candidates'])} dominated by {'/'.join(x['by'])}" for x in par["dominated"])
                     + f"; {par['note']}")
    elif par.get("status") == "refused":
        lines.append(f"- Pareto front on {', '.join(par['axes'])}: refused: {'; '.join(par['reasons'])}")
    return "\n".join(lines) + "\n"


def report(args) -> dict:
    full = design.derive(args.artifacts, args.decisions)
    if full.get("status") == "error" and not full.get("requirements"):
        return {"status": "failed", "exit": 1, "error": "the design cannot be derived", "design_errors": full.get("errors")}
    proj = design.Project(args.artifacts, None)
    w = Writer(proj)
    used = sorted({r["file"] for item in full["requirements"] + full["constraints"] for m in item["matrix"]
                   for r in m["used"]})
    inputs = [w.input_ref(full["current_spec"])] + [w.input_ref(f) for f in used]  # RPT-10
    st = statuses(inputs, "unvalidated")
    claims = []
    for item in full["requirements"] + full["constraints"]:
        for m in item["matrix"]:
            claims.append({"text": f"{item['id']} for {', '.join(m['candidates'])}: {m['result']}"
                           f"{' (provisional)' if m['provisional'] else ''} ({', '.join(m['codes']) or 'no codes'})",
                           "result_ref": full["current_spec"], "status": st})
    name = args.name or "design-report"
    md_rel = f"reports/{name}.md"
    if (proj.root / md_rel).exists() or (proj.root / f"reports/{name}.json").exists():
        raise UsageError(f"reports/{name} exists: choose another --name")
    design.analyze_evaluations(proj)
    gaps = search_minus_official(proj)
    text = render(full, args.omit or [])
    if gaps:
        text += "\n## Search values against official evaluations\n\n" + "".join(
            f"- {g['candidate']} ({g['search']} point {g['point']}), {g['figure_of_merit']}: "
            f"{'Geant4 ' if g['search_level'] == 'geant4' else ''}search value "
            f"{g['search_value']:.6g}, official {g['evaluation']} {g['official_value']:.6g} "
            f"(search minus official {g['search_minus_official']:.6g}); search values decide nothing\n" for g in gaps)
    w.write(md_rel, text.encode("utf-8"))
    slim = design.report_payload(full)
    ext = {"claims": claims, "sources_read": [], "limitations": [
        "derived by contracts/design.py; verdicts guard against oversight, not deliberate forgery (LIM-02)",
        "the review axis is advisory: only a valid human design-baseline record sets it (LIM-01)"],
        "design_report": dict(slim, omitted_from_rendering=args.omit or [])}
    rel = w.json(f"reports/{name}.json", envelope("communication", f"{full['design_id']}-{name}", ext, inputs,
                                                   [{"ref": md_rel}], st))
    from contracts.validate import validate_artifact
    rep = validate_artifact(json.loads((proj.root / rel).read_text(encoding="utf-8")))
    if not rep.ok:
        w.undo()
        return {"status": "failed", "exit": 1, "error": "the report fails contract validation",
                "findings": [f.as_dict() for f in rep.errors]}
    out = {"status": "ok", "exit": 0, "report": rel, "rendering": md_rel, "gate_flags": full.get("gate_flags"),
           "design_status": full.get("status"), "design_errors": full.get("errors")}
    if gaps:
        out["search_minus_official"] = gaps
    return out


def search_minus_official(proj: design.Project) -> list[dict]:
    """Section C.4.6: for each candidate expanded from a search finalist, its search value minus the official
    evaluation of the same figure of merit and denominator (a diagnostic of the winner's curse and of model
    differences; it decides nothing)."""
    out = []
    for cid, cpath in sorted(proj.candidates.items()):
        doc = proj.docs[cpath]
        m = re.match(r"^search (SEARCH-[A-Za-z0-9._-]+) point (\d+):", doc["extension"].get("description", ""))
        run = next((proj.docs.get(proj.resolve(i["ref"])) for i in doc.get("inputs") or []
                    if isinstance(i, dict) and design.is_search_run(proj.docs.get(proj.resolve(str(i.get("ref"))), {}))),
                   None)
        if not m or run is None:
            continue
        s = run["extension"]["search_summary"]
        point = next((p for p in s["points"] if p["index"] == int(m.group(2))), None)
        if point is None or point["effective_digest"] != proj.effective_digest(cid):
            continue
        for t in s.get("objectives", []) + s.get("constraints", []):
            sv = (point["values"].get(t["label"]) or {}).get("value")
            g4_rows = [r for r in point.get("geant4") or [] if (r["values"].get(t["label"]) or {}).get("value")
                       is not None]
            gv = g4_rows[-1]["values"][t["label"]]["value"] if g4_rows else None  # C2: the last Geant4 search value
            for ev in sorted(proj.evals.values(), key=lambda e: e.rel):
                ext = ev.ext
                if (ext.get("candidate") != cid or ext.get("figure_of_merit") != t["figure_of_merit"] or ev.errors
                        or ev.stale or ext.get("unavailable") or not isinstance(ext.get("value"), (int, float))
                        or not all(design.close(ext.get("denominator", {}).get(k), v)
                                   for k, v in t["denominator"].items())):
                    continue
                for level, value in (("F1", sv), ("geant4", gv)):
                    if value is not None:
                        out.append({"candidate": cid, "search": m.group(1), "point": int(m.group(2)),
                                    "figure_of_merit": t["figure_of_merit"], "search_level": level,
                                    "search_value": value, "evaluation": ev.eid, "fidelity": ev.fidelity,
                                    "official_value": ext["value"], "search_minus_official": value - ext["value"]})
    return out


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run", help="one design evaluation from a tool contract")
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--requirement")
    p.add_argument("--figure-of-merit", dest="figure_of_merit")
    p.add_argument("--denominator", action="append", help="KEY=VALUE (repeatable)")
    p.add_argument("--fidelity", default="F1", choices=design.FIDELITIES[1:4])
    p.add_argument("--tool", help="TOOL:OPERATION when several operations compute the figure of merit")
    p.add_argument("--upstream", action="append", help="upstream evaluation file (repeatable)")
    p.add_argument("--id", help="evaluation id suffix (default from the figure of merit and candidate)")
    p.add_argument("--input-artifact", dest="input_artifact", action="append",
                   help="another artifact the operation reads (e.g. a statistical-result), bound as an input")
    p.add_argument("--replace", action="store_true", help="replace an evaluation of this id that is stale")
    p.add_argument("--status", choices=ARTIFACT_LABELS, default="unvalidated")
    p.add_argument("--digest-only", dest="digest_only", action="store_true",
                   help="print the parameters the evaluation would read and their digest; run nothing (INC-02)")
    p = sub.add_parser("budget", help="budget sum of one quantity (CHN-10)")
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--quantity", required=True, choices=tuple(BUDGET_FOMS))
    p.add_argument("--id")
    p.add_argument("--replace", action="store_true", help="replace an evaluation of this id that is stale")
    p.add_argument("--digest-only", dest="digest_only", action="store_true")
    p.add_argument("--status", choices=ARTIFACT_LABELS, default="unvalidated")
    p = sub.add_parser("response", help="F3 response assembly and a parametrized response artifact (CHN-01)")
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--requirement")
    p.add_argument("--denominator", action="append", help="KEY=VALUE (repeatable)")
    p.add_argument("--upstream", action="append", help="the core resolution evaluation")
    p.add_argument("--id")
    p.add_argument("--replace", action="store_true")
    p.add_argument("--status", choices=ARTIFACT_LABELS, default="unvalidated")
    p = sub.add_parser("geometry", help="the geometry file of a Geant4 study from the candidate (ART-33, ART-34)")
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--figure-of-merit", dest="figure_of_merit", required=True)
    p.add_argument("--denominator", action="append", help="KEY=VALUE (repeatable)")
    p.add_argument("--id", required=True, help="study id (file studies/<id>.geometry.json)")
    p = sub.add_parser("f4", help="an F4 evaluation from a Geant4 study record (ART-31, ART-32)")
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--requirement")
    p.add_argument("--figure-of-merit", dest="figure_of_merit")
    p.add_argument("--denominator", action="append", help="KEY=VALUE (repeatable)")
    p.add_argument("--study", required=True, help="the study record (a computational-run) in the artifacts_dir")
    p.add_argument("--id", required=True)
    p.add_argument("--label-spec", dest="label_spec")
    p.add_argument("--label-benchmarks", dest="label_benchmarks")
    p.add_argument("--label-convergence", dest="label_convergence")
    p.add_argument("--label-project-root", dest="label_project_root")
    p.add_argument("--label-run-record", dest="label_run_record", action="append",
                   help="a run record passed on to label as --run-record (repeatable)")
    p.add_argument("--label-reference-record", dest="label_reference_record", action="append",
                   help="a reference dataset-record passed on to label as --reference-record (repeatable)")
    p.add_argument("--label-variations", dest="label_variations", help="the variation table passed on to label")
    p.add_argument("--label-results", dest="label_results",
                   help="the f4-results/1 file passed on to label as --results (Geant4 program B2.6)")
    p.add_argument("--label-geometry", dest="label_geometry",
                   help="the design-geometry/1 file passed on to label as --geometry (Geant4 program B2.6)")
    p.add_argument("--status", choices=ARTIFACT_LABELS, default="unvalidated")
    p = sub.add_parser("f5", help="an F5 evaluation from a user-supplied dataset-record (FID-06, FID-07)")
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--dataset", required=True, help="the dataset-record with extension.design_measurement")
    p.add_argument("--id", required=True)
    p = sub.add_parser("calibration", help="a calibration residual into yield shifts and the measurement-spec (CHN-16)")
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--residual", required=True, help="SID.parameters.NAME: the residual scale s or curvature offset")
    p.add_argument("--mode", required=True, choices=("scale", "inverse-offset"))
    p.add_argument("--model", required=True, help="spectrum model JSON in the artifacts_dir (propagate_scale_distortion "
                   "response input)")
    p.add_argument("--id", required=True, help="CAL-... (outputs/<id>.json, runs/<id>.computational-run.json)")
    p.add_argument("--measurement-spec", dest="measurement_spec", help="measurement-spec to version with the systematic")
    p.add_argument("--out-spec", dest="out_spec", help="file of the new measurement-spec version")
    p.add_argument("--status", choices=ARTIFACT_LABELS, default="unvalidated")
    p = sub.add_parser("scan", help="a figure of merit over a parameter grid, stored as one summary run (M4, AGG-08)")
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--figure-of-merit", dest="figure_of_merit", required=True)
    p.add_argument("--denominator", action="append", help="KEY=VALUE (repeatable)")
    p.add_argument("--fidelity", default="F1", choices=design.FIDELITIES[1:4])
    p.add_argument("--tool", help="TOOL:OPERATION when several operations compute the figure of merit")
    p.add_argument("--vary", action="append", required=True, help="SID.parameters.NAME=V1,V2,... (repeatable: a grid)")
    p.add_argument("--max-points", dest="max_points", type=int, default=200)
    p.add_argument("--id", required=True, help="SCAN-... (file runs/<id>.computational-run.json)")
    p.add_argument("--status", choices=ARTIFACT_LABELS, default="unvalidated")
    p = sub.add_parser("search", help="automated candidate generation at F1: search values, search front, finalists "
                                      "(C1); writes no candidate and no evaluation")
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--spec", help="the search spec file (design-search-spec/1) in the artifacts_dir")
    p.add_argument("--id", help="SEARCH-... (file runs/<id>.computational-run.json)")
    p.add_argument("--diagnose", help="C2: a search run; writes runs/DIAG-<id>.computational-run.json with each "
                                      "expanded finalist's search value minus its official evaluation (no search)")
    p.add_argument("--max-evaluations", dest="max_evaluations", type=int,
                   help="safety cap on the evaluations (default: the search spec's budget)")
    p.add_argument("--geant4-work", dest="geant4_work", type=Path,
                   help="C2: the folder for the Geant4 search runs, their scratch artifacts and cache (outside the "
                        "artifacts_dir); needs HEP_GEANT4_CONFIG")
    p.add_argument("--status", choices=ARTIFACT_LABELS, default="unvalidated")
    p = sub.add_parser("expand", help="one scan point or search finalist as a candidate, to evaluate and compare "
                                      "(M4, C1)")
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--scan", help="the scan summary run (runs/SCAN-....computational-run.json)")
    p.add_argument("--search", help="the search run (runs/SEARCH-....computational-run.json); only finalists expand")
    p.add_argument("--point", type=int, required=True)
    p.add_argument("--candidate-id", dest="candidate_id", required=True, help="name of the new candidate (no namespace)")
    for name in ("plan", "report"):
        p = sub.add_parser(name)
        p.add_argument("--artifacts", type=Path, required=True)
        p.add_argument("--decisions", type=Path)
        if name == "report":
            p.add_argument("--omit", action="append", help="evaluation id hidden from the rendering only")
            p.add_argument("--name", help="report file name (default design-report)")
    args = ap.parse_args(argv)
    try:
        if not args.artifacts.is_dir():
            raise UsageError(f"--artifacts {args.artifacts} is not a folder")
        if getattr(args, "decisions", None) is not None and not args.decisions.is_dir():
            raise UsageError(f"--decisions {args.decisions} is not a folder")
        if args.command == "budget":
            args.requirement, args.figure_of_merit = None, BUDGET_FOMS[args.quantity]
            args.denominator, args.fidelity, args.tool, args.upstream = [], "F1", None, None
            args.input_artifact = None
            out = run_evaluation(args, args.digest_only)
        elif args.command == "run":
            out = run_evaluation(args, args.digest_only)
        elif args.command == "f5":
            out = f5(args)
        elif args.command == "geometry":
            out = geometry(args)
        elif args.command == "f4":
            if args.label_spec and not (args.label_benchmarks and args.label_convergence):
                raise UsageError("--label-spec needs --label-benchmarks and --label-convergence")
            out = f4(args)
        elif args.command == "response":
            args.input_artifact = None
            out = response(args)
        elif args.command == "calibration":
            out = calibration(args)
        elif args.command == "scan":
            out = scan(args)
        elif args.command == "search":
            if args.max_evaluations is not None and args.max_evaluations < 1:
                raise UsageError("--max-evaluations is a positive number")
            if args.diagnose:
                if args.spec or args.id:
                    raise UsageError("--diagnose takes no --spec or --id: it reads a finished search")
                out = search_diagnose(args)
            elif not (args.spec and args.id):
                raise UsageError("search needs --spec and --id (or --diagnose SEARCH-RUN)")
            else:
                out = search_design(args)
        elif args.command == "expand":
            if bool(args.scan) == bool(args.search):
                raise UsageError("give exactly one of --scan or --search")
            out = expand_search(args) if args.search else expand(args)
        elif args.command == "plan":
            out = plan(args)
        else:
            out = report(args)
    except UsageError as exc:
        print(json.dumps({"status": "rejected", "status_label": getattr(args, "status", "unvalidated"),
                          "error": str(exc)}, indent=1))
        return 2
    code = out.pop("exit", 0)
    out = {"status": out.pop("status"), "status_label": getattr(args, "status", "unvalidated"), **out}
    print(json.dumps(out, indent=1, default=str))
    return code


if __name__ == "__main__":
    sys.exit(main())
