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
  label --upgrade with --label-spec/--label-benchmarks/--label-convergence); value, statistical uncertainty and model
  envelope from the record; bound optimistic for resolution and confusion unless every tail source was simulated.
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
Exit codes: 0 ok; 1 the tool failed, gave no value, or the evaluation has a design error (nothing written); 2 invalid
input or a missing file (JSON with error on stdout).
Usage:
  evaluate_design.py run --artifacts DIR --candidate ID (--requirement ID | --figure-of-merit FOM [--denominator K=V ...])
      [--fidelity F1] [--tool TOOL:OP] [--upstream REL ...] [--input-artifact REL ...] [--id EVAL-ID] [--replace]
      [--digest-only] [--status LABEL]
  evaluate_design.py budget --artifacts DIR --candidate ID --quantity Q [--id EVAL-ID] [--status LABEL]
  evaluate_design.py response --artifacts DIR --candidate ID (--requirement ID | --denominator K=V ...) [--upstream REL]
      [--id EVAL-ID] [--replace] [--status LABEL]
  evaluate_design.py geometry --artifacts DIR --candidate ID --figure-of-merit FOM --denominator K=V ... --id STUDY-ID
  evaluate_design.py f4 --artifacts DIR --candidate ID (--requirement ID | --figure-of-merit FOM --denominator K=V ...)
      --study REL --id SIM-ID [--label-spec S --label-benchmarks B --label-convergence C [--label-project-root R]]
      [--status LABEL]
  evaluate_design.py f5 --artifacts DIR --candidate ID --dataset REL --id MEAS-ID
  evaluate_design.py calibration --artifacts DIR --candidate ID --residual SID.parameters.NAME --mode MODE --model REL
      --id CAL-ID [--measurement-spec REL --out-spec REL] [--status LABEL]
  evaluate_design.py scan --artifacts DIR --candidate ID --figure-of-merit FOM [--denominator K=V ...] [--fidelity F1]
      --vary SID.parameters.NAME=V1,V2,... [--vary ...] --id SCAN-ID [--max-points N] [--status LABEL]
  evaluate_design.py expand --artifacts DIR --scan REL --point K --candidate-id NAME
  evaluate_design.py plan --artifacts DIR [--decisions DIR]
  evaluate_design.py report --artifacts DIR [--decisions DIR] [--omit EVALUATION ...] [--name NAME]
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
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
    # argv: interpreter, script, operation arguments, positionals, then options in the contract's order
    args_out: list[str] = list(fd.get("operation_args", []))
    manifest = [{"path": r, "sha256": sha256(proj.root / r)} for r in chain_rels]
    by_input = {m["input"]: prep.expected[m["input"]] for m in fd["inputs"] if m["input"] in prep.expected}
    for pos in sorted(op["invocation"].get("positionals", []), key=lambda x: x["position"]):
        val = by_input.get(pos["input"])
        if isinstance(val, design.ConfigValue):
            rel = w.json(f"configs/{eid}.{pos['input']}.json", dict(val))
            manifest.append({"path": rel, "sha256": sha256(proj.root / rel)})
            args_out.append(rel)
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
            args_out += [o["flag"], args.status]
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
    value, path = design.output_value(fd, den, output)
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
    own, _ = design.own_bound(fd, prep, den, output)
    bound = design.combine_bounds(own, prep.directions)
    domain = design.validity_reasons(fd, prep, den, output)
    ext.update(value=value, unit=fd["unit"], bound=bound if bound != "mixed" else "estimate", run_ref=run_rel,
               parameter_refs=sorted(prep.refs), parameter_digest=proj.parameter_digest(args.candidate, prep.refs),
               validity={"assumptions": list(fd.get("assumptions", [])), "in_domain": not domain},
               fidelity=op["design"]["fidelity"])
    unc = design.output_uncertainty(fd, output, value)
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
    --upgrade. Value, statistical uncertainty and model envelope are the record's; the bound follows FID-03."""
    proj = load_project(args)
    if args.label_spec:
        cmd = [sys.executable, "-B", str(PLUGIN / "skills/hep-detector/scripts/check_geant4_study.py"), "label",
               "--spec", args.label_spec, "--benchmarks", args.label_benchmarks, "--convergence", args.label_convergence,
               "--project-root", str(args.label_project_root or proj.root), "--upgrade", "--write", str(proj.root / args.study)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=TOOL_TIMEOUT_S)
        if p.returncode != 0:
            return {"status": "failed", "exit": 1, "error": "check_geant4_study.py label --upgrade refused the study",
                    "label_output": p.stdout[-3000:]}
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
    w.write(md_rel, render(full, args.omit or []).encode("utf-8"))
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
    return {"status": "ok", "exit": 0, "report": rel, "rendering": md_rel, "gate_flags": full.get("gate_flags"),
            "design_status": full.get("status"), "design_errors": full.get("errors")}


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
    p = sub.add_parser("expand", help="one scan point as a derived candidate, to evaluate and compare (M4)")
    p.add_argument("--artifacts", type=Path, required=True)
    p.add_argument("--scan", required=True, help="the scan summary run (runs/SCAN-....computational-run.json)")
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
        elif args.command == "expand":
            out = expand(args)
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
