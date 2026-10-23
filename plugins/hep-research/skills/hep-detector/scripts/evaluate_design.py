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
- plan: the suggested next evaluations, per requirement and candidate, from the derived state (RES-04): missing
  evaluations, missing evidence for compliance, stale evaluations, missing gates. Suggestions only.
- report: the design report, a communication artifact derived by contracts/design.py (producer_skill hep-detector):
  gate flags first, the compliance matrix with used and skipped evaluations, maturity, missing evidence, proposed
  dispositions, orphan runs, screening, the comparison basis and ranking refusal (RPT-01..RPT-10), plus a Markdown
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


def render(full: dict, omitted: list[str]) -> str:
    lines = [f"# Design report: {full.get('design_id')}", "",
             f"Derived by contracts/design.py from `{full.get('current_spec')}` (spec version {full.get('spec_version')}); "
             "no verdict is hand-written.", ""]
    lines += [f"**Gate flags:** {', '.join(full.get('gate_flags') or ['none'])}", ""]
    if full.get("adequacy", {}).get("provisional_pass"):
        lines += ["The adequacy table is an initial default until physics review: every pass is provisional.", ""]
    lines += ["| Requirement | Candidates | Result | Reason codes | Lowest fidelity | Status | Missing for compliance |",
              "|---|---|---|---|---|---|---|"]
    for item in full.get("requirements", []) + full.get("constraints", []):
        for m in item["matrix"]:
            lines.append(f"| {item['id']} | {', '.join(m['candidates'])} | {m['result']}"
                         f"{' (provisional)' if m['provisional'] else ''} | {', '.join(m['codes']) or '-'} | "
                         f"{m['maturity']['lowest_chain_fidelity'] or 'undetermined'} | "
                         f"{', '.join(m['maturity']['status_axis']) or '-'} | {'; '.join(m['missing_evidence']) or '-'} |")
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
        lines.append(f"- {', '.join(c['candidates'])}: {'screened out (' + '; '.join(c['screened_out_reasons']) + ')' if c['screened_out'] else 'not screened out'}"
                     f"{'; at risk: ' + '; '.join(c['at_risk']) if c['at_risk'] else ''}")
    for o in full.get("orphan_runs", []):
        lines.append(f"- orphan run {o['run']} ({', '.join(o['figures_of_merit'])})")
    basis = full.get("comparison_basis", {})
    lines.append(f"- comparison basis: {'holds' if basis.get('holds') else 'does not hold'}"
                 f"{' (' + basis['reason'] + ')' if basis.get('reason') else ''}")
    lines.append(f"- ranking: {full.get('ranking', {}).get('status')}: {full.get('ranking', {}).get('reason')}")
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
    slim = {k: v for k, v in full.items() if k not in ("evaluations",)}
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
        elif args.command == "geometry":
            out = geometry(args)
        elif args.command == "f4":
            if args.label_spec and not (args.label_benchmarks and args.label_convergence):
                raise UsageError("--label-spec needs --label-benchmarks and --label-convergence")
            out = f4(args)
        elif args.command == "response":
            args.input_artifact = None
            out = response(args)
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
