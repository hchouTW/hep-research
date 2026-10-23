#!/usr/bin/env python3
"""Detector system design verdicts (contracts 3.11.0; detector system design spec, section 6): compliance verdicts,
maturity, staleness and gate flags derived from the design artifacts, never declared by the agent.

design.py reads only the artifacts of one artifacts_dir (design-spec, design-candidate, design-evaluation,
computational-run and the files they reference), the decision records of a folder outside it (--decisions, OQ-13),
the tool contracts (contracts/tool_contracts/) and the adequacy table (contracts/rules/design_adequacy.json). It runs no
skill script and trusts no self-reported tool name, fidelity, bound or validity domain (ARC-04).

Per evaluation:
  - its chain (FID-08): itself and, recursively, the design-evaluations among its inputs; the fidelity vector keeps
    each figure of merit's fidelity (FID-09);
  - its contract (ART-60, ART-61): the script and argv of the computational-run its run_ref names select the tool
    contract operation; for an evaluation that is not stale, fidelity and the leaf bound must equal the contract's,
    parameter_refs the parameters the contract's input mapping reads, every argv input the value recomputed from the
    candidate, the denominator and the upstream evaluations (moved per CMB-05/CMB-06), and value the number at the
    contract's location in the run's output file; any difference is the error design.contract_mismatch;
  - its bound (CMB-01..CMB-08): a leaf's comes from the contract piece whose conditions hold; a composite's combines
    the operation's own bound with its upstream inputs' derived bounds and the contract's per-input directions;
  - its verdict per requirement side: the first row of the 18-row table (RUL-01..RUL-18, decide()) whose condition
    holds. A range requirement is two one-sided sides (RUL-00c); on a side opposite to the 'better' direction the
    optimistic and conservative roles swap.
Per requirement (or constraint) and effective candidate (the digest of the merged parameters, AGG-00): aggregation
AGG-01..AGG-10 over every evaluation of that figure of merit in the artifacts_dir (the report cannot choose them), the
maturity axes (MAT-*), and the evidence still missing for compliance. Per project: candidate screening (CHN-11,
CHN-12), orphan runs (AGG-08), the comparison basis (ART-15) and the gate flags (DEC-02, DEC-07..DEC-09, DEC-12 for
H1..H3; the review axis, dispositions and F5 approval follow in M3, OQ-15).

Errors (design.*; ART-64) are malformed artifacts and evaluations that do not match their contract, run or study; an
evaluation with an error takes no part in the decision and its requirement cannot pass. Everything else is a verdict.
Until the adequacy table is frozen by physics review (OQ-05) every pass is reported as provisional. The verdicts guard
against oversight and shortcuts, not against deliberate forgery (LIM-02); nothing here authorizes anything.

Usage: python3 contracts/design.py check --artifacts DIR [--decisions DIR] [--contracts DIR ...]
       python3 contracts/design.py status --artifacts DIR [--decisions DIR] [--contracts DIR ...]
  check prints the full derivation, status the summary of RES-02. Exit codes: 0 no design error, 1 design errors,
  2 unreadable input or bad usage. Output: JSON on stdout.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from statistics import NormalDist
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.release_manifest import canonical_sha256  # noqa: E402
from contracts.schema import validate  # noqa: E402
from contracts.validate import STICKY_STATUSES, validate_artifact  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = PLUGIN_ROOT / "contracts" / "tool_contracts"
ADEQUACY_FILE = PLUGIN_ROOT / "contracts" / "rules" / "design_adequacy.json"
GEOMETRY_FILE = PLUGIN_ROOT / "contracts" / "rules" / "design_geometry.json"
TAIL_SOURCES = ("alignment", "calibration-non-uniformity", "noise-digitization", "pattern-recognition")
FIDELITIES = ("F0", "F1", "F2", "F3", "F4", "F5")
RANK = {f: i for i, f in enumerate(FIDELITIES)}
DESIGN_TYPES = ("design-spec", "design-candidate", "design-evaluation")
DESIGN_CATEGORIES = ("design-scope", "requirements-baseline", "architecture-selection", "design-baseline",
                     "requirement-change", "measurement-acceptance")
BUDGET_QUANTITIES = ("mass", "power", "channel_count", "data_rate")
NOTE = ("derived by contracts/design.py from the artifacts; verdicts guard against oversight and shortcuts, not "
        "deliberate forgery (LIM-02), and authorize nothing")
REL_TOL = 1e-9
_N = NormalDist()

# The single-evaluation verdict table (RUL-01..RUL-18), in order: (row, verdict, reason code).
ROWS: dict[int, tuple[str | None, str]] = {1: ("inconclusive", "capability.unavailable"), 2: ("inconclusive", "evidence.stale"),
        3: ("inconclusive", "evidence.unresolved"), 4: ("inconclusive", "evidence.invalid"),
        5: ("inconclusive", "chain.incomplete"), 6: ("inconclusive", "budget.incomplete"),
        7: ("inconclusive", "domain.mismatch"), 8: ("inconclusive", "fidelity.insufficient"),
        9: ("inconclusive", "bound.mixed"), 10: ("fail", "bound.excludes"), 11: ("inconclusive", "bound.direction"),
        12: ("inconclusive", "fidelity.insufficient"), 13: ("pass", "bound.confirms"),
        14: ("inconclusive", "bound.direction"), 15: ("inconclusive", "uncertainty.missing"),
        16: (None, "estimate.decides"), 17: ("inconclusive", "margin.within_uncertainty"),
        18: ("inconclusive", "rule.unmatched")}


@dataclass(frozen=True)
class Factors:
    """The abstract states the verdict table reads (TST-EX-01, OQ-19). bound is the bound on this requirement side
    (after the role swap of RUL-00c): optimistic, conservative, estimate or mixed. meets: the value meets the side's
    target (bounds). estimate: 'compliant' or 'noncompliant' when the one-sided bound toward the target at the coverage
    CL stays on the value's side, 'within' when it crosses or touches the target."""
    unavailable: bool = False
    stale: bool = False
    unresolved: bool = False
    invalid: bool = False
    chain_incomplete: bool = False
    budget_incomplete: bool = False
    domain_mismatch: bool = False
    below_screening: bool = False
    bound: str = "estimate"
    meets: bool = False
    below_compliance: bool = False
    uncertainty_ok: bool = False
    estimate: str = "within"


def decide(f: Factors) -> tuple[int, str, str]:
    """(row, verdict, code): the first row of the verdict table whose condition holds (RUL-00a, RUL-01..RUL-18)."""
    checks = ((1, f.unavailable), (2, f.stale), (3, f.unresolved), (4, f.invalid), (5, f.chain_incomplete),
              (6, f.budget_incomplete), (7, f.domain_mismatch), (8, f.below_screening), (9, f.bound == "mixed"),
              (10, f.bound == "optimistic" and not f.meets), (11, f.bound == "optimistic" and f.meets),
              (12, f.below_compliance), (13, f.bound == "conservative" and f.meets),
              (14, f.bound == "conservative" and not f.meets), (15, f.bound == "estimate" and not f.uncertainty_ok),
              (16, f.bound == "estimate" and f.estimate in ("compliant", "noncompliant")),
              (17, f.bound == "estimate" and f.estimate == "within"))
    for row, cond in checks:
        if cond:
            code = ROWS[row][1]
            verdict = ("pass" if f.estimate == "compliant" else "fail") if row == 16 else str(ROWS[row][0])
            return row, verdict, code
    return 18, "inconclusive", ROWS[18][1]


# ---------------------------------------------------------------- numbers and expressions


def close(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=REL_TOL, abs_tol=1e-300)
    return a == b


def flat(v) -> list:
    if isinstance(v, list):
        return [x for item in v for x in flat(item)]
    return [v]


def lookup(doc, path: str):
    """The value at a dotted path (integers index lists), or None."""
    cur = doc
    for part in path.split("."):
        if isinstance(cur, list) and part.lstrip("-").isdigit():
            i = int(part)
            cur = cur[i] if -len(cur) <= i < len(cur) else None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
        if cur is None:
            return None
    return cur


def z_one_sided(cl: float) -> float:
    return _N.inv_cdf(cl)


def one_sided_halfwidth(unc: dict | None, side: str, cl: float, counting: bool) -> float | None:
    """The half-width on side ('minus' or 'plus') of the one-sided bound at coverage cl, or None when the declared
    uncertainty cannot give it (RUL-15, RUL-16): declared directly at that coverage (a central interval of coverage C is
    a one-sided bound at (1 + C) / 2 on each side), else converted only for a symmetric Gaussian (asymmetric intervals
    side by side); a counting quantity needs an exact interval and is never converted."""
    if not unc or side not in ("minus", "plus"):
        return None
    hw = float(unc[side])
    c1 = unc["coverage"] if unc["interval"] == "one-sided" else (1 + unc["coverage"]) / 2
    if not 0.5 < c1 < 1:
        return None
    if counting and unc["distribution"] != "exact":
        return None
    if math.isclose(c1, cl, rel_tol=0, abs_tol=1e-9):
        return hw
    if unc["distribution"] == "gaussian" and not counting:
        return hw / z_one_sided(c1) * z_one_sided(cl)
    return None


def sigma_equivalent(unc: dict, side: str) -> float:
    """A 68.27%-equivalent half-width for the minimum-uncertainty comparison (ADQ-01): the Gaussian conversion of the
    declared half-width at its one-sided coverage (also applied, as a scale, to non-Gaussian and exact intervals)."""
    c1 = unc["coverage"] if unc["interval"] == "one-sided" else (1 + unc["coverage"]) / 2
    z = z_one_sided(c1) if 0.5 < c1 < 1 else float("inf")
    return float(unc[side]) / z if z > 0 else 0.0


class ExprError(ValueError):
    pass


# ---------------------------------------------------------------- loading


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_adequacy(path: Path = ADEQUACY_FILE) -> dict:
    return load_json(path)


class Registry:
    """The tool contracts (schema-checked; the help check is contracts/tool_contract.py's job), indexed by entry."""

    def __init__(self, dirs: list[Path] | None = None):
        self.contracts: list[dict] = []
        self.problems: list[str] = []
        for d in dirs or [CONTRACT_DIR]:
            for p in sorted(Path(d).glob("*.json")):
                try:
                    doc = load_json(p)
                except (OSError, ValueError) as exc:
                    self.problems.append(f"{p}: {exc}")
                    continue
                rep = validate(doc, "tool_contract.json")
                if rep.ok:
                    self.contracts.append(doc)
                else:
                    self.problems.append(f"{p}: " + ", ".join(sorted({f.code for f in rep.errors})))

    def by_script(self, script: str) -> dict | None:
        s = script.replace("\\", "/")
        for c in self.contracts:
            if s == c["entry"] or s.endswith("/" + c["entry"]):
                return c
        return None

    def designs(self):
        for c in self.contracts:
            for op in c["operations"]:
                for fom in (op.get("design") or {}).get("figures_of_merit", []):
                    yield c, op, fom

    def computes(self, fom_id: str, fidelity: str) -> list[str]:
        """'tool:operation' of every contract operation that computes fom_id at fidelity (ART-63)."""
        return [f"{c['tool_id']}:{op['operation_id']}" for c, op, f in self.designs()
                if f["id"] == fom_id and op["design"]["fidelity"] == fidelity]

    def fom_design(self, fom_id: str) -> dict | None:
        """The first design declaration of a figure of merit (for its 'better' direction and denominator)."""
        return next((f for _, _, f in self.designs() if f["id"] == fom_id), None)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict) and k != "value":
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


# ---------------------------------------------------------------- per-evaluation facts


@dataclass
class Evaluation:
    path: Path
    rel: str
    doc: dict
    errors: list = field(default_factory=list)          # [(code, message)]: design.* (ART-64)
    stale: list = field(default_factory=list)
    unresolved: list = field(default_factory=list)
    invalid: list = field(default_factory=list)
    domain: list = field(default_factory=list)          # validity-domain reasons (row 7)
    chain_missing: list = field(default_factory=list)   # required upstreams missing (row 5)
    compliance_missing: list = field(default_factory=list)  # 'with' upstreams missing (row 5 at compliance)
    budget_missing: list = field(default_factory=list)  # row 6
    upstreams: list = field(default_factory=list)       # direct upstream Evaluation objects
    bound: str = "estimate"                             # derived bound (CMB), may be 'mixed'
    vector: list = field(default_factory=list)          # [(fom, fidelity, evaluation_id)] of the chain
    f4_unqualified: bool = False                        # ART-31: below screening
    unreviewed: bool = False                            # F5 without measurement-acceptance (FID-06)
    better: str | None = None
    contract: str | None = None                         # 'tool:operation'
    effective: str | None = None
    statuses: set = field(default_factory=set)

    @property
    def ext(self) -> dict:
        return self.doc.get("extension") or {}

    @property
    def eid(self) -> str:
        return self.ext.get("evaluation_id", self.rel)

    @property
    def fom(self) -> str:
        return self.ext.get("figure_of_merit", "")

    @property
    def fidelity(self) -> str:
        return self.ext.get("fidelity", "F0")

    def err(self, code: str, message: str) -> None:
        self.errors.append((code, message))


class Project:
    def __init__(self, artifacts: Path, decisions: Path | None = None, registry: Registry | None = None,
                 adequacy: dict | None = None):
        self.root = Path(artifacts).resolve()
        self.decisions_dir = Path(decisions).resolve() if decisions else None
        self.registry = registry or Registry()
        self.adequacy = adequacy or load_adequacy()
        self.errors: list[dict] = []
        self.docs: dict[Path, dict] = {}
        self.sha: dict[Path, str] = {}
        self.specs: list[Path] = []
        self.candidates: dict[str, Path] = {}
        self.evals: dict[Path, Evaluation] = {}
        self.runs: list[Path] = []
        self.records: list[dict] = []
        self._scan()

    # -- loading
    def error(self, code: str, where: str, message: str) -> None:
        self.errors.append({"severity": "error", "path": where, "code": code, "message": message})

    def rel(self, p: Path) -> str:
        try:
            return p.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(p)

    def resolve(self, ref: str) -> Path:
        p = Path(ref)
        return (p if p.is_absolute() else self.root / p).resolve()

    def _scan(self) -> None:
        for p in sorted(self.root.rglob("*.json")):
            if any(part.startswith(".") for part in p.relative_to(self.root).parts):
                continue
            try:
                raw = p.read_bytes()
                doc = json.loads(raw.decode("utf-8"))
            except (OSError, ValueError, UnicodeDecodeError):
                continue
            if not isinstance(doc, dict) or "artifact_type" not in doc:
                continue
            p = p.resolve()
            self.docs[p], self.sha[p] = doc, hashlib.sha256(raw).hexdigest()
            at = doc["artifact_type"]
            if at in DESIGN_TYPES:
                rep = validate_artifact(doc)
                bad = sorted({f"{f.code} at {f.path}" for f in rep.errors})
                if bad:
                    self.error("design.malformed", self.rel(p), "; ".join(bad[:6]))
                    continue
            ext = doc.get("extension") or {}
            if at == "design-spec":
                self.specs.append(p)
            elif at == "design-candidate":
                cid = ext["candidate_id"]
                if cid in self.candidates:
                    self.error("design.duplicate_id", self.rel(p), f"candidate id {cid} is also {self.rel(self.candidates[cid])}")
                self.candidates[cid] = p
            elif at == "design-evaluation":
                self.evals[p] = Evaluation(p, self.rel(p), doc)
            elif at == "computational-run":
                self.runs.append(p)

    # -- candidates
    def candidate_chain(self, cid: str) -> list[Path] | None:
        """Files of the derived_from chain, the candidate first (None when a base is missing or the chain loops)."""
        out: list[Path] = []
        while cid:
            p = self.candidates.get(cid)
            if p is None or p in out:
                return None
            out.append(p)
            cid = (self.docs[p]["extension"]).get("derived_from")
        return out

    def effective(self, cid: str) -> dict | None:
        """Effective subsystems after merging overrides along derived_from (ART-20)."""
        chain = self.candidate_chain(cid)
        if chain is None:
            return None
        subs: dict = {}
        for p in reversed(chain):
            ext = self.docs[p]["extension"]
            subs = deep_merge(subs, ext.get("subsystems") or {})
            subs = deep_merge(subs, ext.get("overrides") or {})
        return subs

    def effective_budgets(self, cid: str) -> dict:
        chain = self.candidate_chain(cid) or []
        budgets: dict = {}
        for p in reversed(chain):
            budgets = deep_merge(budgets, self.docs[p]["extension"].get("budgets") or {})
        return budgets

    def effective_digest(self, cid: str) -> str | None:
        """AGG-00: the digest of the merged parameters; copies with the same parameters share it."""
        subs = self.effective(cid)
        if subs is None:
            return None
        return canonical_sha256({sid: s.get("parameters", {}) for sid, s in subs.items()})

    def parameter_objects(self, cid: str, refs) -> dict:
        """TRC-05: the complete objects the parameter_refs name in the merged candidate (value, unit, source and status
        of a parameter; the subsystem list; a budget item); a missing one is None."""
        subs = self.effective(cid) or {}
        budgets = self.effective_budgets(cid)
        out: dict = {}
        for ref in sorted(set(refs)):
            if ref == "subsystems":
                out[ref] = sorted(subs)
            elif ref.startswith("budgets."):
                _, q, sid = (ref.split(".", 2) + ["", ""])[:3]
                out[ref] = (budgets.get(q) or {}).get(sid)
            else:
                sid, _, rest = ref.partition(".parameters.")
                out[ref] = ((subs.get(sid) or {}).get("parameters") or {}).get(rest) if rest else None
        return out

    def parameter_digest(self, cid: str, refs) -> str:
        return canonical_sha256(self.parameter_objects(cid, refs))

    def species(self, name: str) -> dict | None:
        table = self.adequacy.get("species", {})
        return table.get(name) if isinstance(table.get(name), dict) else None

    def fom_rules(self, fom: str) -> dict | None:
        return self.adequacy["figures_of_merit"].get(fom)


# ---------------------------------------------------------------- dependency rows (RUL-02..RUL-04)

ROW2_CODES = {"dependency.hash_mismatch"}
ROW3_CODES = {"dependency.no_hash", "dependency.external_unresolved", "dependency.source_unresolved"}


def _input_index(ev: Evaluation, ref: str) -> int:
    return next((k for k, i in enumerate(ev.doc.get("inputs") or []) if isinstance(i, dict) and i.get("ref") == ref), -1)


def dependency_rows(proj: Project, ev: Evaluation) -> None:
    """Rows 2-4 from contracts/dependencies.py over the evaluation's whole input closure (a hash mismatch anywhere in
    the chain is stale, so staleness propagates down the chain, TRC-09)."""
    from contracts.dependencies import validate_dependencies
    rep = validate_dependencies(ev.path, proj.root)
    for f in rep["findings"]:
        msg = f"{f['path']}: {f['code']}"
        if (f["code"] == "dependency.source_invalid" and ev.ext.get("study_ref")
                and f["path"].endswith(":$.inputs[" + str(_input_index(ev, ev.ext["study_ref"])) + "]")
                and all(c.startswith("geant4.") for c in f["message"].rsplit(": ", 1)[-1].split(", "))):
            continue  # ART-31: a study record that fails only the upgrade rules is below screening (row 8)
        if f["code"] in ROW2_CODES:
            ev.stale.append(msg)
        elif f["code"] in ROW3_CODES or f["severity"] == "unresolved":
            ev.unresolved.append(msg)
        elif f["severity"] == "error":
            ev.invalid.append(msg)
    if rep.get("failed_upstream"):
        ev.invalid.append("an input carries 'failed'")


# ---------------------------------------------------------------- argv and contract checks (ART-60..ART-63)


def parse_argv(argv: list[str], op_args: list[str], options: dict[str, str], n_positionals: int):
    """(script, {input: [tokens]}, problems) from argv: the interpreter, the script, the operation arguments, the
    positional arguments, then options each followed by its values up to the next '--' token."""
    problems: list[str] = []
    k = next((i for i, a in enumerate(argv) if a.endswith(".py")), None)
    if k is None:
        return None, {}, ["argv names no .py script"]
    script, rest = argv[k], argv[k + 1:]
    if rest[:len(op_args)] != op_args:
        problems.append(f"argv does not start the operation with {op_args}")
    rest = rest[len(op_args):]
    got: dict[str, list[str]] = {}
    i = 0
    pos = 0
    while i < len(rest) and not rest[i].startswith("--"):
        got[f"#{pos}"] = [rest[i]]
        pos += 1
        i += 1
    if pos != n_positionals:
        problems.append(f"argv has {pos} positional argument(s), the contract declares {n_positionals}")
    while i < len(rest):
        flag = rest[i]
        vals = []
        i += 1
        while i < len(rest) and not rest[i].startswith("--"):
            vals.append(rest[i])
            i += 1
        name = options.get(flag)
        if name is None:
            problems.append(f"argv passes {flag}, which the contract does not declare")
            continue
        if name in got:
            problems.append(f"argv passes {flag} twice")
        got[name] = vals
    return script, got, problems


def tokens_match(expected, tokens: list[str]) -> bool:
    if expected is True:
        return tokens == []
    exp = flat(expected)
    if len(exp) != len(tokens):
        return False
    for e, t in zip(exp, tokens):
        if isinstance(e, (int, float)) and not isinstance(e, bool):
            try:
                if not close(float(t), e):
                    return False
            except ValueError:
                return False
        elif str(e) != t:
            return False
    return True


class ConfigValue(dict):
    """The content of a config-file input (ART-41, ART-72): written to a file whose path is the argv token."""


class Evaluator:
    """Recomputes contract inputs for one evaluation (ART-41, ART-61)."""

    def __init__(self, proj: Project, ev: Evaluation, subs: dict, upstream_values: dict):
        self.proj, self.ev, self.subs, self.up = proj, ev, subs, upstream_values
        self.refs: set[str] = set()

    def param(self, spec: dict):
        hits = [sid for sid, s in self.subs.items() if s.get("role") == spec["role"]]
        if len(hits) != 1:
            raise ExprError(f"{len(hits)} subsystems with role {spec['role']!r} (the mapping needs exactly one)")
        sid = hits[0]
        par = (self.subs[sid].get("parameters") or {}).get(spec["name"])
        if not isinstance(par, dict):
            raise ExprError(f"{sid} has no parameter {spec['name']!r}")
        if par.get("unit") != spec["unit"]:
            raise ExprError(f"{sid}.parameters.{spec['name']} is in {par.get('unit')!r}, the contract reads {spec['unit']!r}")
        self.refs.add(f"{sid}.parameters.{spec['name']}")
        return par["value"]

    def budget(self, spec: dict) -> list:
        """The budget items of a quantity over the subsystems, sorted by subsystem id; the subsystem list itself is a
        parameter read (CHN-10), and a row without estimate and uncertainty is skipped (row 6 reports it)."""
        rows = self.proj.effective_budgets(self.ev.ext.get("candidate", "")).get(spec["quantity"], {})
        self.refs.add("subsystems")
        out = []
        for sid in sorted(self.subs):
            item = rows.get(sid)
            if isinstance(item, dict) and "estimate" in item and "uncertainty" in item:
                self.refs.add(f"budgets.{spec['quantity']}.{sid}")
                out.append(item[spec["field"]])
        return out

    def __call__(self, e: dict):
        den = self.ev.ext.get("denominator") or {}
        if "parameter" in e:
            return self.param(e["parameter"])
        if "budget" in e:
            return self.budget(e["budget"])
        if "parameters_all" in e:  # CHN-14: one parameter over every subsystem that declares it (coupling)
            spec, out = e["parameters_all"], []
            for sid in sorted(self.subs):
                par = (self.subs[sid].get("parameters") or {}).get(spec["name"])
                if isinstance(par, dict):
                    if par.get("unit") != spec["unit"]:
                        raise ExprError(f"{sid}.parameters.{spec['name']} is in {par.get('unit')!r}, the contract reads "
                                        f"{spec['unit']!r}")
                    self.refs.add(f"{sid}.parameters.{spec['name']}")
                    out += flat(par["value"])
            self.refs.add("subsystems")  # a new subsystem may bring the parameter
            return out
        if "denominator" in e:
            if e["denominator"] not in den:
                raise ExprError(f"the denominator has no {e['denominator']!r}")
            return den[e["denominator"]]
        if "species" in e:
            name = den.get(e.get("of", "species"))
            sp = self.proj.species(str(name))
            if sp is None or (e["species"] != "charge_number" and e["species"] not in sp):
                raise ExprError(f"species {name!r} has no {e['species']!r} in the adequacy table")
            return abs(sp["charge"]) if e["species"] == "charge_number" else sp[e["species"]]
        if "upstream" in e:
            if e["upstream"] not in self.up:
                raise ExprError(f"no upstream evaluation of {e['upstream']!r} among the inputs")
            return self.up[e["upstream"]]
        if "const" in e:
            return e["const"]
        if "input_artifact" in e:
            refs = [i["ref"] for i in self.ev.doc.get("inputs") or [] if isinstance(i, dict)
                    and self.proj.docs.get(self.proj.resolve(str(i.get("ref"))), {}).get("artifact_type") == e["input_artifact"]]
            if len(refs) != 1:
                raise ExprError(f"{len(refs)} bound inputs of type {e['input_artifact']!r} (the mapping needs exactly one)")
            return refs[0]
        if "list" in e:
            return [x for a in e["list"] for x in flat(self(a))]
        if "object" in e:
            return {k: self(v) for k, v in e["object"].items()}
        if "zip" in e:  # lists of one common length into objects; scalars and constants repeat whole
            cols = {k: self(v) for k, v in e["zip"].items()}
            whole = {k for k, v in e["zip"].items() if "const" in v}
            lengths = {len(v) for k, v in cols.items() if isinstance(v, list) and k not in whole}
            if len(lengths) != 1:
                raise ExprError("zip needs lists of one common length")
            size = lengths.pop()
            return [{k: (v[i] if isinstance(v, list) and k not in whole else v) for k, v in cols.items()}
                    for i in range(size)]
        if "span" in e:
            vals = [x for x in flat(self(e["span"])) if isinstance(x, (int, float)) and not isinstance(x, bool)]
            if len(vals) < 2:
                raise ExprError("span needs at least two numbers")
            return max(vals) - min(vals)
        if "config" in e:
            val = self(e["config"])
            if not isinstance(val, dict):
                raise ExprError("a config file holds a JSON object")
            return ConfigValue(val)
        args = [self(a) for a in (e.get("sum") or e.get("product") or e.get("quotient") or [])]
        nums = [flat(a) for a in args]
        if any(not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in n) for n in nums):
            raise ExprError("arithmetic on a non-number")
        if "sum" in e:
            return math.fsum(x for n in nums for x in n)
        out = nums[0] if len(nums[0]) > 1 else nums[0][0]
        for arg in nums[1:]:
            if len(arg) != 1:
                raise ExprError("product and quotient take scalars after the first argument")
            if "quotient" in e and arg[0] == 0:
                raise ExprError("division by zero")
            op = (lambda a, b: a * b) if "product" in e else (lambda a, b: a / b)
            out = [op(x, arg[0]) for x in out] if isinstance(out, list) else op(out, arg[0])
        return out


def same(a, b) -> bool:
    """Deep equality with numbers compared by close()."""
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return close(a, b)


def condition_holds(c: dict, inputs: dict, den: dict, output, up_bounds: dict) -> bool | None:
    """A validity or bound condition (tool_contract.json $defs/condition); None when it cannot be evaluated."""
    def within(vals) -> bool:
        return all(("min" not in c or v >= c["min"]) and ("max" not in c or v <= c["max"]) for v in vals)
    if "input" in c:
        v = inputs.get(c["input"])
        vals = [x for x in flat(v) if isinstance(x, (int, float))] if v is not None else None
        return None if not vals else within(vals)
    if "denominator" in c:
        v = den.get(c["denominator"])
        return None if not isinstance(v, (int, float)) else within([v])
    if "output_ge" in c:
        vals = [lookup(output, pth) for pth in c["output_ge"]]
        if output is None or not all(isinstance(v, (int, float)) for v in vals):
            return None
        return all(vals[i] >= vals[i + 1] for i in range(len(vals) - 1))
    if "upstream_bound" in c:
        b = up_bounds.get(c["upstream_bound"])
        return None if b is None else b in c.get("in", [])
    return None


def combine_bounds(own: str, inputs: list[tuple[str, str]]) -> str:
    """CMB-01..CMB-04: own is the operation's declared bound (an order-preserving input); inputs are (derived bound,
    direction) of the upstream inputs. Returns optimistic, conservative, estimate or mixed."""
    pairs = [(own, "order-preserving")] + list(inputs)
    if any(b == "mixed" for b, _ in pairs):
        return "mixed"
    if any(d == "non-monotonic" for _, d in pairs):
        return "estimate" if all(b == "estimate" for b, _ in pairs) else "mixed"    # CMB-02
    swap = {"optimistic": "conservative", "conservative": "optimistic", "estimate": "estimate"}
    bounds = {swap[b] if d == "reversed" else b for b, d in pairs}                  # CMB-03
    if {"optimistic", "conservative"} <= bounds:
        return "mixed"                                                               # CMB-04
    if "optimistic" in bounds:
        return "optimistic"                                                          # CMB-05
    if "conservative" in bounds:
        return "conservative"                                                        # CMB-06
    return "estimate"                                                                # CMB-07


def moved_upstream_value(up: Evaluation, direction: str, case: str, n_estimates: int, cl: float, counting: bool):
    """The upstream value fed to a composite (CMB-05, CMB-06): a bound is used as it is; an estimate input moves to its
    one-sided favorable (optimistic case) or unfavorable (conservative case) bound at the Bonferroni level
    1 - (1 - CL)/n; in an all-estimate chain it stays central (CMB-07)."""
    v = up.ext.get("value")
    if up.bound != "estimate" or case == "estimate" or v is None:
        return v
    level = 1 - (1 - cl) / max(1, n_estimates)
    # favorable for the output: the upstream better direction for an order-preserving input, the opposite if reversed
    toward_better = (case == "optimistic") == (direction != "reversed")
    smaller = (up.better == "smaller") == toward_better
    hw = one_sided_halfwidth(up.ext.get("uncertainty"), "minus" if smaller else "plus", level, counting)
    if hw is None:
        raise ExprError(f"upstream estimate {up.eid} has no uncertainty convertible to the one-sided {level:.4g} level")
    return v - hw if smaller else v + hw


@dataclass
class Prepared:
    """What a contract operation's design block gives for one evaluation before and after its tool runs: the inputs
    recomputed from the candidate, the denominator and the upstream evaluations (ART-41, ART-61), the parameters read,
    the upstream (bound, direction) pairs, and problems (errors and invalid-input reasons)."""
    expected: dict
    refs: set
    directions: list
    up_bounds: dict
    errors: list
    invalid: list


def prepare(proj: Project, ev: Evaluation, fd: dict) -> Prepared:
    """Recompute the inputs of design block fd for evaluation ev (shared by contracts/design.py and evaluate_design.py,
    so an evaluation is written with exactly the inputs the verdict rules recompute; T-58)."""
    from contracts.tool_contract import expr_refs
    rules = proj.fom_rules(fd["id"]) or {}
    errors: list[str] = []
    invalid: list[str] = []
    ups_by_fom: dict[str, list[Evaluation]] = {}
    for u in ev.upstreams:
        ups_by_fom.setdefault(u.fom, []).append(u)
    for f, us in ups_by_fom.items():
        if len(us) > 1:  # which one fed the input would be the agent's choice
            errors.append(f"{len(us)} upstream evaluations of {f} among the inputs; bind one")
    directions, feeds = [], []
    for m in fd["inputs"]:
        for uf in expr_refs(m["from"])[1]:
            for u in ups_by_fom.get(uf, [])[:1]:
                directions.append((u.bound, m.get("direction", "order-preserving")))
                feeds.append((u, m.get("direction", "order-preserving")))
    fed = {u.fom for u, _ in feeds}
    for fom, direction in (fd.get("upstream_directions") or {}).items():  # read through another artifact (CHN-04)
        for u in ups_by_fom.get(fom, [])[:1]:
            if fom not in fed:
                directions.append((u.bound, direction))
    pre_case = combine_bounds("estimate", directions)
    cl = rules.get("coverage_cl", proj.adequacy.get("default_coverage_cl", 0.95))
    n_est = sum(1 for u, _ in feeds if u.bound == "estimate")
    upstream_values = {}
    try:
        for u, d in feeds:
            urules = proj.fom_rules(u.fom) or {}
            upstream_values[u.fom] = moved_upstream_value(u, d, pre_case, n_est, cl, bool(urules.get("counting")))
    except ExprError as exc:
        invalid.append(str(exc))
        upstream_values = {u.fom: u.ext.get("value") for u, _ in feeds}
    evaluator = Evaluator(proj, ev, proj.effective(ev.ext.get("candidate", "")) or {}, upstream_values)
    expected: dict[str, Any] = {}
    for m in fd["inputs"]:
        try:
            expected[m["input"]] = evaluator(m["from"])
        except ExprError as exc:
            if "no upstream evaluation" in str(exc):
                continue  # a missing required upstream is chain.incomplete (row 5), not a contract error
            errors.append(f"input {m['input']}: {exc}")
    return Prepared(expected, evaluator.refs, directions, {u.fom: u.bound for u in ev.upstreams}, errors, invalid)


def own_bound(fd: dict, prep: Prepared, den: dict, output) -> tuple[str, str | None]:
    """(the operation's bound: the first piece whose conditions hold, ART-40; a problem when a condition cannot be
    evaluated)."""
    pieces = fd["bound"] if isinstance(fd["bound"], list) else [{"bound": fd["bound"]}]
    for piece in pieces:
        held = [condition_holds(c, prep.expected, den, output, prep.up_bounds) for c in piece.get("when", [])]
        if any(h is None for h in held):
            return piece["bound"], "a bound condition of the contract cannot be evaluated for this run"
        if all(held):
            return piece["bound"], None
    return "estimate", None


def validity_reasons(fd: dict, prep: Prepared, den: dict, output) -> list[str]:
    """FID-10: the contract's validity conditions that do not hold (row 7)."""
    out = []
    for c in fd.get("validity", []):
        if condition_holds(c, prep.expected, den, output, prep.up_bounds) is False:
            out.append(c.get("note") or f"outside the contract's validity domain: {json.dumps(c, sort_keys=True)}")
    return out


def output_value(fd: dict, den: dict, output):
    """(value, path) at the contract's value location (ART-32, ART-60 c)."""
    loc = fd["value"]
    path = loc.get("path") or loc.get("paths", {}).get(str(den.get(loc.get("by_denominator"))))
    v = lookup(output, path) if path and output is not None else None
    return (v if isinstance(v, (int, float)) and not isinstance(v, bool) else None), path


def output_uncertainty(fd: dict, output, value) -> dict | None:
    """The uncertainty the contract declares for the operation's value (absolute at a path, or relative), or None."""
    spec = fd.get("uncertainty")
    if not spec or value is None:
        return None
    if "relative" in spec:
        hw = abs(value) * spec["relative"]
    else:
        hw = lookup(output, spec["path"])
        if not isinstance(hw, (int, float)):
            return None
    return {"minus": float(hw), "plus": float(hw), "coverage": spec["coverage"], "interval": spec["interval"],
            "distribution": spec["distribution"]}


def check_contract(proj: Project, ev: Evaluation) -> None:
    """ART-60..ART-63, FID-02, FID-04, TRC-02, TRC-08 and the bound derivation (CMB) of one evaluation."""
    ext, fid = ev.ext, ev.fidelity
    rules = proj.fom_rules(ev.fom)
    if rules is None:
        ev.err("design.unknown_figure_of_merit", f"{ev.fom!r} is not in the adequacy table")
        return
    design = proj.registry.fom_design(ev.fom)
    ev.better = design["better"] if design else None
    if ext.get("unavailable"):  # ART-63
        if "value" in ext or "run_ref" in ext or ext.get("bound") != "estimate":
            ev.err("design.contract_mismatch", "an unavailable evaluation is an estimate with no value and no run")
        ops = proj.registry.computes(ev.fom, fid)
        if ops:
            ev.err("design.contract_mismatch", f"declared unavailable, but {', '.join(ops)} computes {ev.fom} at {fid}")
        ev.bound = "estimate"
        return
    if fid == "F0":  # FID-01, ART-63
        if ext.get("bound") != "estimate" or ext.get("derivation") != "heuristic-argument" or "run_ref" in ext:
            ev.err("design.contract_mismatch", "an F0 evaluation is an estimate labelled heuristic-argument, with no run")
        ev.bound = "estimate"
        return
    if "value" not in ext:
        ev.err("design.malformed", "every evaluation except an unavailable one and F0 carries a value")
        return
    if ev.stale:  # ART-61: a stale evaluation is not compared with its contract, study or dataset
        ev.bound = ext.get("bound", "estimate")
        ev.unreviewed = fid == "F5"
        return
    if fid == "F4":
        check_f4(proj, ev)
        return
    if fid == "F5":
        check_f5(proj, ev)
        return
    run_ref = ext.get("run_ref")
    if not run_ref:
        ev.err("design.contract_mismatch", f"an {fid} evaluation names its computational-run in run_ref")
        return
    run_path = proj.resolve(run_ref)
    run = proj.docs.get(run_path)
    if run is None or run.get("artifact_type") != "computational-run":
        ev.err("design.contract_mismatch", f"run_ref {run_ref!r} is not a computational-run in the artifacts_dir")
        return
    rext = run.get("extension") or {}
    argv = rext.get("argv")
    if not isinstance(argv, list) or not argv:
        ev.err("design.contract_mismatch", f"{run_ref} records no argv (ART-70)")
        return
    script = next((a for a in argv if a.endswith(".py")), "")
    contract = proj.registry.by_script(script)
    if contract is None:
        ev.err("design.contract_mismatch", f"no tool contract for {script!r}")
        return
    cand = [(op, f) for op in contract["operations"] for f in (op.get("design") or {}).get("figures_of_merit", [])
            if f["id"] == ev.fom and argv[argv.index(script) + 1:][:len(f.get("operation_args", []))]
            == f.get("operation_args", [])]
    if len(cand) != 1:
        ev.err("design.contract_mismatch", f"{contract['tool_id']}: {len(cand)} operations compute {ev.fom} for this argv")
        return
    op, fd = cand[0]
    ev.contract = f"{contract['tool_id']}:{op['operation_id']}"
    ev.better = fd["better"]
    if fid != op["design"]["fidelity"]:  # ART-60 (a), FID-02
        ev.err("design.contract_mismatch", f"fidelity {fid}, the contract declares {op['design']['fidelity']}")
    if fd["unit"] != ext.get("unit"):
        ev.err("design.contract_mismatch", f"unit {ext.get('unit')!r}, the contract declares {fd['unit']!r}")
    den = ext.get("denominator") or {}
    if set(den) != set(fd["denominator"]) or any(
            (kind == "number") != (isinstance(den[k], (int, float)) and not isinstance(den[k], bool))
            for k, kind in fd["denominator"].items() if k in den):
        ev.err("design.contract_mismatch", f"denominator fields {sorted(den)} differ from the contract's {sorted(fd['denominator'])}")
    # output file (ART-60 c)
    outs = [o.get("ref") for o in run.get("outputs") or [] if isinstance(o, dict)]
    output = None
    if len(outs) != 1:
        ev.err("design.contract_mismatch", f"{run_ref} lists {len(outs)} outputs[].ref; the tool output is one file")
    else:
        opath = proj.resolve(str(outs[0]))
        hashes = rext.get("output_hashes") or {}
        try:
            data = opath.read_bytes()
            output = json.loads(data.decode("utf-8"))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            ev.err("design.contract_mismatch", f"output {outs[0]!r} is not readable JSON: {exc}")
        else:
            if hashlib.sha256(data).hexdigest() not in hashes.values():
                ev.err("design.contract_mismatch", f"output {outs[0]!r} does not match the run's output_hashes")
    prep = prepare(proj, ev, fd)
    for msg in prep.errors:
        ev.err("design.contract_mismatch", msg)
    ev.invalid += prep.invalid
    own, problem = own_bound(fd, prep, den, output)
    if problem:
        ev.err("design.contract_mismatch", problem)
    ev.bound = combine_bounds(own, prep.directions)
    if ev.bound != "mixed" and ext.get("bound") != ev.bound:  # ART-60 (a); composite: derived (CMB-*)
        ev.err("design.contract_mismatch", f"bound {ext.get('bound')!r}, the contract and chain give {ev.bound!r}")
    ev.domain += validity_reasons(fd, prep, den, output)
    # argv inputs (ART-61), config files (ART-72) and parameter_refs (ART-60 b, TRC-08)
    options = {o["flag"]: o["input"] for o in op["invocation"]["options"]}
    positionals = {f"#{p['position']}": p["input"] for p in op["invocation"].get("positionals", [])}
    _, got, problems = parse_argv(argv, fd.get("operation_args", []), options, len(positionals))
    got = {positionals.get(k, k): v for k, v in got.items()}
    for p in problems:
        ev.err("design.contract_mismatch", p)
    free = set(fd.get("free_inputs", []))
    for name in sorted(set(got) - set(prep.expected) - free - {m["input"] for m in fd["inputs"]}):
        ev.err("design.contract_mismatch", f"argv passes input {name!r}, which the contract's mapping does not set")
    manifest = {i.get("path"): i.get("sha256") for i in rext.get("input_manifest") or [] if isinstance(i, dict)}
    for name, val in prep.expected.items():
        if name not in got:
            ev.err("design.contract_mismatch", f"argv lacks input {name!r}")
        elif isinstance(val, ConfigValue):
            ev.errors += [("design.contract_mismatch", m) for m in config_problems(proj, name, val, got[name], manifest)]
        elif not tokens_match(val, got[name]):
            ev.err("design.contract_mismatch", f"argv input {name!r} is {got[name]}, recomputed {val!r}")
    if set(ext.get("parameter_refs") or []) != prep.refs:
        ev.err("design.contract_mismatch",
               f"parameter_refs {sorted(ext.get('parameter_refs') or [])} differ from the parameters the contract reads "
               f"{sorted(prep.refs)}")
    if output is not None:
        got_v, path = output_value(fd, den, output)
        if got_v is None or not close(got_v, ext["value"]):
            ev.err("design.contract_mismatch", f"value {ext['value']!r}, the output file has {got_v!r} at {path!r}")
        unc = output_uncertainty(fd, output, got_v)
        if unc is not None and not same(unc, ext.get("uncertainty")):
            ev.err("design.contract_mismatch", f"uncertainty {ext.get('uncertainty')!r}, the contract gives {unc!r}")


def config_problems(proj: Project, name: str, val: ConfigValue, tokens: list[str], manifest: dict) -> list[str]:
    """ART-72: a config-file input is one path whose file is in the run's input_manifest with its hash and holds the
    content recomputed from the candidate."""
    if len(tokens) != 1:
        return [f"config input {name!r} takes one path"]
    p = proj.resolve(tokens[0])
    try:
        data = p.read_bytes()
        doc = json.loads(data.decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        return [f"config file {tokens[0]!r} of input {name!r} is not readable JSON: {exc}"]
    out = []
    if manifest.get(tokens[0]) != hashlib.sha256(data).hexdigest():
        out.append(f"config file {tokens[0]!r} is not in the run's input_manifest with its sha256 (ART-72)")
    if not same(doc, dict(val)):
        out.append(f"config file {tokens[0]!r} differs from the content recomputed from the candidate")
    return out


def geometry_fields(proj: Project, cid: str, mapping: dict | None = None) -> tuple[dict, list[str], str]:
    """ART-34, ART-35: the geometry fields the mapping table reads from the merged candidate, the parameters read and
    their digest (TRC-05)."""
    mapping = mapping or load_json(GEOMETRY_FILE)
    ev = Evaluation(Path("."), ".", {"extension": {"candidate": cid, "denominator": {}}})
    evaluator = Evaluator(proj, ev, proj.effective(cid) or {}, {})
    fields = {f["field"]: evaluator(f["from"]) for f in mapping["fields"]}
    refs = sorted(evaluator.refs)
    return fields, refs, proj.parameter_digest(cid, refs)


def candidate_geometry_ref(proj: Project, cid: str) -> str | None:
    for p in proj.candidate_chain(cid) or []:
        ref = proj.docs[p]["extension"].get("geometry_ref")
        if ref:
            return ref
    return None


def check_f4(proj: Project, ev: Evaluation) -> None:
    """ART-30..ART-36, FID-03, FID-05: only a study record that passes the 3.1.0 upgrade rules with validated-in-scope
    counts as F4 (else below screening, row 8); the record must have used this candidate's geometry file, whose
    parameter digest matches the current candidate (a changed candidate: stale; otherwise a mismatch: a study of
    another layout cannot stand in); its observable must be this figure of merit (else domain.mismatch); value,
    statistical uncertainty and model envelope are the record's; the bound is optimistic for a tail-sensitive figure of
    merit unless the study simulated every tail source."""
    ext = ev.ext
    study_ref = ext.get("study_ref")
    study = proj.docs.get(proj.resolve(study_ref)) if study_ref else None
    ev.bound = ext.get("bound", "estimate")
    if study is None or study.get("artifact_type") != "computational-run":
        ev.f4_unqualified = True
        return
    sext = study.get("extension") or {}
    rep = validate_artifact(study)
    if "validated-in-scope" not in (study.get("status") or []) or not rep.ok or "study" not in sext:
        ev.f4_unqualified = True  # ART-31: not reissued, or not passing the upgrade rules
    block: dict = sext["study"] if isinstance(sext.get("study"), dict) else {}
    try:
        mapping = load_json(GEOMETRY_FILE)
    except (OSError, ValueError) as exc:
        ev.err("design.contract_unreadable", f"geometry mapping: {exc}")
        return
    cid = ext.get("candidate", "")
    gref = candidate_geometry_ref(proj, cid)
    if not gref:
        ev.err("design.binding_incomplete", "an F4 evaluation's candidate names its geometry in geometry_ref (ART-30)")
    else:
        gpath = proj.resolve(gref)
        try:
            gdata = gpath.read_bytes()
            geometry = json.loads(gdata.decode("utf-8"))
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            ev.err("design.contract_mismatch", f"geometry {gref!r} is not readable JSON: {exc}")
            geometry = None
        if geometry is not None:
            manifest = {m.get("path"): m.get("sha256") for m in sext.get("input_manifest") or [] if isinstance(m, dict)}
            if manifest.get(gref) != hashlib.sha256(gdata).hexdigest():
                ev.err("design.contract_mismatch", f"the study record did not use {gref} (input_manifest): a study of "
                       "another layout cannot stand in (ART-35)")
            try:
                _, _, now = geometry_fields(proj, cid, mapping)
            except ExprError as exc:
                now = f"unresolved: {exc}"
            if geometry.get("parameter_digest") != now:
                changed = any(i.get("sha256") != proj.sha.get(proj.resolve(i["ref"])) for i in ev.doc.get("inputs") or []
                              if isinstance(i, dict) and proj.docs.get(proj.resolve(str(i.get("ref"))), {}).get(
                                  "artifact_type") == "design-candidate")
                if changed:
                    ev.stale.append("a geometry parameter changed since the study (ART-35)")
                else:
                    ev.err("design.contract_mismatch", "the geometry's parameter digest does not match the candidate (ART-35)")
            if geometry.get("figure_of_merit") != ev.fom:
                ev.domain.append(f"the study geometry was generated for {geometry.get('figure_of_merit')}, not {ev.fom} (ART-36)")
    fom_map = mapping["figures_of_merit"].get(ev.fom)
    result = (block.get("results") or {}).get(ev.fom) if isinstance(block.get("results"), dict) else None
    if fom_map is None or not isinstance(result, dict):
        ev.domain.append(f"the study's observables do not include {ev.fom} (ART-36)")
        return
    if not isinstance(result.get("value"), (int, float)) or not close(result["value"], ext.get("value")):
        ev.err("design.contract_mismatch", f"value {ext.get('value')!r}, the study record has {result.get('value')!r} (ART-32)")
    stat = result.get("statistical_uncertainty")
    want_unc = ({"minus": float(stat), "plus": float(stat), "coverage": 0.6827, "interval": "central",
                 "distribution": "gaussian"} if isinstance(stat, (int, float)) else None)
    if want_unc is not None and not same(want_unc, ext.get("uncertainty")):
        ev.err("design.contract_mismatch", "uncertainty differs from the study's statistical error (FID-01 F4)")
    env = result.get("model_envelope")
    if (env is not None or "model_envelope" in ext) and not same(env, ext.get("model_envelope")):
        ev.err("design.contract_mismatch", "model_envelope differs from the study record (FID-05)")
    tails = set(block.get("tail_sources_simulated") or [])
    ev.bound = "optimistic" if fom_map.get("tail_sensitive") and not set(TAIL_SOURCES) <= tails else "estimate"
    if ext.get("bound") != ev.bound:
        ev.err("design.contract_mismatch", f"F4 bound {ext.get('bound')!r}; the study's simulated tail sources give "
               f"{ev.bound!r} (FID-03)")


def check_f5(proj: Project, ev: Evaluation) -> None:
    """FID-01, FID-06, FID-07, DEC-06: F5 is an estimate from a user-supplied dataset-record whose design_measurement
    gives the figure of merit, denominator, value, uncertainty and the configuration it was measured in. The value and
    uncertainty are the dataset's (else a contract mismatch); a configuration that differs from the candidate's
    parameters is domain.mismatch (a measurement of another layout cannot stand in); the evaluation decides only when
    a valid human measurement-acceptance record approves the dataset as it is now and covers this candidate through
    the digest of its measurement-configuration parameters; until then evidence.unreviewed."""
    ev.bound = "estimate"
    if ev.ext.get("bound") != "estimate":
        ev.err("design.contract_mismatch", "an F5 evaluation is an estimate")
    ref = ev.ext.get("dataset_ref")
    ds_path = proj.resolve(ref) if ref else None
    ds = proj.docs.get(ds_path) if ds_path else None
    ev.unreviewed = True
    if ds is None or ds.get("artifact_type") != "dataset-record":
        ev.err("design.contract_mismatch", "an F5 evaluation names its dataset-record in dataset_ref")
        return
    dm = (ds.get("extension") or {}).get("design_measurement")
    if not isinstance(dm, dict):
        ev.err("design.contract_mismatch", "the dataset-record has no design_measurement")
        return
    if dm.get("figure_of_merit") != ev.fom:
        ev.domain.append(f"the dataset measures {dm.get('figure_of_merit')}, not {ev.fom}")
    if not close(dm.get("value"), ev.ext.get("value")) or not same(dm.get("uncertainty"), ev.ext.get("uncertainty")):
        ev.err("design.contract_mismatch", "value or uncertainty differ from the dataset's design_measurement")
    if not same(dm.get("denominator"), ev.ext.get("denominator")):
        ev.err("design.contract_mismatch", "denominator differs from the dataset's design_measurement")
    cid = ev.ext.get("candidate", "")
    config = dm.get("configuration") or {}
    current = proj.parameter_objects(cid, config)
    for pref, want in sorted(config.items()):
        have = current.get(pref)
        if not isinstance(have, dict) or have.get("unit") != want.get("unit") or not same(have.get("value"), want.get("value")):
            ev.domain.append(f"measured with {pref} = {want.get('value')} {want.get('unit')}; the candidate has "
                             f"{(have or {}).get('value')} {(have or {}).get('unit')} (FID-07)")
    digest = proj.parameter_digest(cid, config)
    ds_sha = proj.sha.get(ds_path) if ds_path else None
    for rec in proj.records:
        if rec["category"] != "measurement-acceptance" or not rec["_valid"]:
            continue
        arts = {proj.resolve(a["ref"]): a for a in rec.get("artifacts", [])}
        cand_ok = any(proj.docs.get(p, {}).get("artifact_type") == "design-candidate"
                      and proj.docs[p]["extension"].get("candidate_id") in
                      {proj.docs[c]["extension"]["candidate_id"] for c in (proj.candidate_chain(cid) or [])}
                      and a.get("binding") == "parameters" and a.get("parameter_digest") == digest
                      for p, a in arts.items())
        if ds_path in arts and arts[ds_path].get("sha256") == ds_sha and cand_ok:
            ev.unreviewed = False
            return


def check_calibration(proj: Project) -> None:
    """CHN-16: every subsystem's calibration names at least one control sample."""
    for cid, p in proj.candidates.items():
        for sid, sub in (proj.effective(cid) or {}).items():
            cal = sub.get("calibration")
            if not isinstance(cal, dict) or not cal.get("method") or not cal.get("control_samples"):
                proj.error("design.calibration_incomplete", proj.rel(p),
                           f"{cid} {sid}: a calibration method and at least one control sample (CHN-16)")


# ---------------------------------------------------------------- the evaluation pipeline


def analyze_evaluations(proj: Project) -> None:
    """Chain, dependency rows, contract checks and bounds of every evaluation, upstreams first."""
    done: set[Path] = set()
    visiting: set[Path] = set()

    def visit(ev: Evaluation) -> None:
        if ev.path in done:
            return
        if ev.path in visiting:
            ev.err("design.malformed", "the evaluation chain loops")
            return
        visiting.add(ev.path)
        bound_refs = {}
        for inp in ev.doc.get("inputs") or []:
            if isinstance(inp, dict) and isinstance(inp.get("ref"), str):
                bound_refs[proj.resolve(inp["ref"])] = inp
        for p in bound_refs:
            if p in proj.evals:
                up = proj.evals[p]
                visit(up)
                ev.upstreams.append(up)
        ext = ev.ext
        chain = proj.candidate_chain(ext.get("candidate", ""))
        if chain is None:
            ev.err("design.malformed", f"candidate {ext.get('candidate')!r} or a base on its derived_from chain is missing")
        else:
            ev.effective = proj.effective_digest(ext["candidate"])
            missing = [proj.rel(p) for p in chain if p not in bound_refs]
            if missing:  # ART-21, TRC-03: bind every file of the derived_from chain
                ev.err("design.binding_incomplete", f"inputs do not bind candidate file(s) {missing}")
        if ext.get("run_ref") and proj.resolve(ext["run_ref"]) not in bound_refs:
            ev.err("design.binding_incomplete", f"inputs do not bind the run {ext['run_ref']!r} (TRC-02)")
        for key in ("study_ref", "dataset_ref"):
            if ext.get(key) and proj.resolve(ext[key]) not in bound_refs:
                ev.err("design.binding_incomplete", f"inputs do not bind {key} {ext[key]!r}")
        dependency_rows(proj, ev)
        parameter_binding(proj, ev, bound_refs)
        check_contract(proj, ev)
        ev.statuses = {s for s in ev.doc.get("status") or [] if s in STICKY_STATUSES}
        own = (ev.fom, ev.fidelity, ev.eid)
        ev.vector = [own] + [v for u in ev.upstreams for v in u.vector]
        if any(u.stale for u in ev.upstreams):  # RUL-02: staleness propagates down the chain
            ev.stale.append("an upstream evaluation is stale")
        chain_rules(proj, ev)
        visiting.discard(ev.path)
        done.add(ev.path)

    for ev in list(proj.evals.values()):
        visit(ev)


def parameter_binding(proj: Project, ev: Evaluation, bound_refs: dict) -> None:
    """TRC-04..TRC-08 (M2): an evaluation whose candidate inputs carry binding "parameters" is stale only when the
    digest of the parameters it read (parameter_refs) differs in the current merged candidate; when no candidate file
    changed, a different digest is a contract mismatch (the recorded digest does not describe the parameters)."""
    ext = ev.ext
    cands = [(p, inp) for p, inp in bound_refs.items() if proj.docs.get(p, {}).get("artifact_type") == "design-candidate"]
    if not any(inp.get("binding") == "parameters" for _, inp in cands):
        return
    if "parameter_digest" not in ext or "parameter_refs" not in ext:
        ev.err("design.binding_incomplete", "a parameter-bound evaluation records parameter_refs and parameter_digest")
        return
    now = proj.parameter_digest(ext.get("candidate", ""), ext["parameter_refs"])
    if now == ext["parameter_digest"]:
        return
    if any(inp.get("sha256") != proj.sha.get(p) for p, inp in cands):
        ev.stale.append("a parameter it read changed in the candidate (parameter_digest)")
    else:
        ev.err("design.contract_mismatch", "parameter_digest does not match the parameters it names (TRC-05)")


def compatible(up: Evaluation, ev: Evaluation) -> bool:
    """FID-11: same effective candidate, and the shared denominator fields agree."""
    if up.effective is None or up.effective != ev.effective:
        return False
    a, b = up.ext.get("denominator") or {}, ev.ext.get("denominator") or {}
    return all(close(a[k], b[k]) for k in set(a) & set(b))


def chain_rules(proj: Project, ev: Evaluation) -> None:
    """Rows 5 and 6 inputs: required upstreams (contract, adequacy 'with' conditions, FID-11) and budget rows."""
    design = None
    if ev.contract:
        tool, _, op_id = ev.contract.partition(":")
        c = next((c for c in proj.registry.contracts if c["tool_id"] == tool), None)
        op = next((o for o in (c or {}).get("operations", []) if o["operation_id"] == op_id), None)
        design = next((f for f in (op or {}).get("design", {}).get("figures_of_merit", []) if f["id"] == ev.fom), None)
    required = list((design or {}).get("required_upstreams", []))
    present = {u.fom for u in ev.upstreams if compatible(u, ev) and not u.ext.get("unavailable")}
    ev.chain_missing = [r for r in required if r not in present]
    rules = proj.fom_rules(ev.fom) or {}
    for group in rules.get("compliance_upstreams", []):
        if not set(group) & present:
            ev.compliance_missing.append(" or ".join(group))
    if rules.get("kind") == "budget" and not ev.ext.get("unavailable") and ev.fidelity != "F0":
        q = rules["budget_quantity"]
        subs = proj.effective(ev.ext.get("candidate", "")) or {}
        rows = proj.effective_budgets(ev.ext.get("candidate", "")).get(q, {})
        for sid in sorted(subs):
            item = rows.get(sid)
            if not item or "estimate" not in item or "uncertainty" not in item:
                ev.budget_missing.append(f"{sid}: no {q} row with estimate and uncertainty")


def chain_threshold_states(proj: Project, ev: Evaluation, min_fidelity: str | None) -> tuple[bool, bool, list]:
    """(below screening, below compliance, [(fom, fidelity, needed)] below compliance) over the fidelity vector; the
    requirement's verification minimum applies to its own figure of merit when it is stricter (ART-13)."""
    below_s, below_c, short = False, False, []
    for fom, fid, _ in ev.vector:
        rules = proj.fom_rules(fom) or {}
        s, c = rules.get("screening", "F5"), rules.get("compliance", "F5")
        if fom == ev.fom and min_fidelity and RANK[min_fidelity] > RANK[c]:
            c = min_fidelity
        if fid == "F0" or RANK[fid] < RANK[s]:
            below_s = True
        if RANK[fid] < RANK[c]:
            below_c = True
            short.append((fom, fid, c))
    if ev.f4_unqualified:
        below_s = True
    return below_s, below_c, short


# ---------------------------------------------------------------- requirement sides and verdicts


@dataclass
class Side:
    comparator: str   # '<=' or '>='
    target: float


def sides(req: dict) -> list[Side]:
    if req["comparator"] == "range":
        lo, hi = req["target"][0], req["target"][1]
        return [Side(">=", lo), Side("<=", hi)]
    t = req["target"]
    return [Side(req["comparator"], t if isinstance(t, (int, float)) else t[0])]


def side_bound(bound: str, better: str | None, side: Side) -> str:
    """RUL-00b, RUL-00c: on a side opposite to the 'better' direction the optimistic and conservative roles swap."""
    agrees = (side.comparator == "<=") == (better != "larger")
    if agrees or bound not in ("optimistic", "conservative"):
        return bound
    return "conservative" if bound == "optimistic" else "optimistic"


def meets(value: float, side: Side) -> bool:
    return value <= side.target if side.comparator == "<=" else value >= side.target


def denominator_mismatch(ev: Evaluation, req: dict) -> list[str]:
    """RUL-07: different fields, or values outside the requirement's tolerance."""
    a, r = ev.ext.get("denominator") or {}, req.get("denominator") or {}
    if set(a) != set(r):
        return [f"denominator fields {sorted(a)} differ from the requirement's {sorted(r)}"]
    out = []
    for k, spec in r.items():
        v, want, tol = a[k], spec["value"], spec["tolerance"]
        if isinstance(want, (int, float)) and isinstance(v, (int, float)):
            if abs(v - want) > tol:
                out.append(f"{k} = {v}, the requirement needs {want} +- {tol}")
        elif v != want:
            out.append(f"{k} = {v!r}, the requirement needs {want!r}")
    return out


def estimate_state(proj: Project, ev: Evaluation, side: Side) -> tuple[bool, str]:
    """(uncertainty usable, 'compliant'|'noncompliant'|'within') for rows 15-17."""
    rules = proj.fom_rules(ev.fom) or {}
    unc, v = ev.ext.get("uncertainty"), ev.ext.get("value")
    cl = rules.get("coverage_cl", proj.adequacy.get("default_coverage_cl", 0.95))
    counting = bool(rules.get("counting"))
    if v is None or not unc:
        return False, "within"
    minimum = rules.get("min_relative_uncertainty", 0.0)
    if ev.fidelity == "F5":
        minimum = max(minimum, proj.adequacy.get("f5_min_relative_uncertainty", 0.0))
    if v != 0 and min(sigma_equivalent(unc, "minus"), sigma_equivalent(unc, "plus")) < minimum * abs(v) * (1 - 1e-12):
        return False, "within"
    env = ev.ext.get("model_envelope")
    if isinstance(env, list) and len(env) == 2 and env[0] != env[1]:  # FID-05: each end of the envelope on its own
        states = [estimate_state(proj, _with_value(ev, x), side)[1] for x in env]
        if states[0] == states[1] and states[0] in ("compliant", "noncompliant"):
            return True, states[0]
        return True, "within"
    ok = meets(v, side)
    # the one-sided bound toward the target: from a compliant value toward the non-compliant side and back
    toward = ("plus" if side.comparator == "<=" else "minus") if ok else ("minus" if side.comparator == "<=" else "plus")
    hw = one_sided_halfwidth(unc, toward, cl, counting)
    if hw is None:
        return False, "within"
    edge = v + hw if toward == "plus" else v - hw
    if ok:
        clear = edge < side.target if side.comparator == "<=" else edge > side.target
        return True, "compliant" if clear else "within"
    clear = edge > side.target if side.comparator == "<=" else edge < side.target
    return True, "noncompliant" if clear else "within"


def _with_value(ev: Evaluation, value: float) -> Evaluation:
    ext = {k: v for k, v in ev.ext.items() if k != "model_envelope"}
    return Evaluation(ev.path, ev.rel, dict(ev.doc, extension=dict(ext, value=value)))


@dataclass
class Verdict:
    row: int
    verdict: str
    code: str
    rows: list
    reasons: list


def evaluate(proj: Project, ev: Evaluation, req: dict) -> Verdict:
    """The verdict of one evaluation for one requirement (or constraint), over its sides (RUL-00c)."""
    min_fid = (req.get("verification") or {}).get("min_fidelity")
    below_s, below_c, _ = chain_threshold_states(proj, ev, min_fid)
    den_bad = denominator_mismatch(ev, req)
    reasons = []
    unavailable = bool(ev.ext.get("unavailable"))
    if unavailable:
        reasons.append(f"no evaluator computes {ev.fom} at {ev.fidelity}")
    reasons += ev.stale + ev.unresolved + ev.invalid
    chain_missing = list(ev.chain_missing) + [
        r for r in (req.get("verification") or {}).get("required_upstreams", [])
        if r not in {u.fom for u in ev.upstreams if compatible(u, ev) and not u.ext.get("unavailable")}]
    if not below_c:  # ADQ-02: the 'with' conditions are required upstreams once the chain reaches compliance
        chain_missing += ev.compliance_missing
    reasons += [f"missing upstream {m}" for m in chain_missing] + ev.budget_missing + ev.domain + den_bad
    results = []
    for side in sides(req):
        b = side_bound(ev.bound, ev.better, side)
        v = ev.ext.get("value")
        unc_ok, est = estimate_state(proj, ev, side) if b == "estimate" else (False, "within")
        f = Factors(unavailable=unavailable, stale=bool(ev.stale), unresolved=bool(ev.unresolved),
                    invalid=bool(ev.invalid), chain_incomplete=bool(chain_missing),
                    budget_incomplete=bool(ev.budget_missing), domain_mismatch=bool(ev.domain or den_bad),
                    below_screening=below_s, bound=b, meets=v is not None and meets(v, side),
                    below_compliance=below_c, uncertainty_ok=unc_ok, estimate=est)
        results.append(decide(f))
    if any(r[1] == "fail" for r in results):
        row, verdict, code = next(r for r in results if r[1] == "fail")
    elif all(r[1] == "pass" for r in results):
        row, verdict, code = results[0]
    else:
        row, verdict, code = next(r for r in results if r[1] == "inconclusive")
    return Verdict(row, verdict, code, [r[0] for r in results], reasons)


def adverse(proj: Project, ev: Evaluation, req: dict) -> bool:
    """AGG-01: an excluded evaluation with a value whose own bound or estimate rule (ignoring fidelity and the
    validity domain) puts it on the non-compliant side; an estimate without a usable uncertainty counts by its value."""
    v = ev.ext.get("value")
    if v is None or denominator_mismatch(ev, req):
        return False
    for side in sides(req):
        b = side_bound(ev.bound, ev.better, side)
        if b == "optimistic" and not meets(v, side):
            return True
        if b in ("estimate", "mixed"):
            ok, est = estimate_state(proj, ev, side)
            if (ok and est == "noncompliant") or (not ok and not meets(v, side)):
                return True
    return False


# ---------------------------------------------------------------- aggregation (AGG) and maturity (MAT)


def lowest(vector: list) -> int:
    return min(RANK[f] for _, f, _ in vector) if vector else -1


def aggregate(proj: Project, req: dict, effective: str, orphans: dict) -> dict:
    """AGG-00..AGG-10 for one requirement and one effective candidate."""
    evals = [e for e in proj.evals.values() if e.fom == req["quantity"] and e.effective == effective]
    used, skipped, errored = [], [], []
    for e in evals:
        if e.errors:
            errored.append(e)
            skipped.append({"evaluation": e.eid, "file": e.rel, "code": e.errors[0][0],
                            "reasons": [m for _, m in e.errors]})
            continue
        v = evaluate(proj, e, req)
        rec: dict[str, Any] = {"evaluation": e.eid, "file": e.rel, "row": v.row, "verdict": v.verdict, "code": v.code,
               "bound": e.bound, "fidelity_vector": [{"figure_of_merit": f, "fidelity": x, "evaluation": i}
                                                      for f, x, i in e.vector], "reasons": v.reasons, "_e": e, "_v": v}
        if v.row <= 7:
            skipped.append(rec)
        elif e.unreviewed:  # FID-06
            rec = dict(rec, code="evidence.unreviewed", verdict="inconclusive")
            skipped.append(rec)
        else:
            used.append(rec)
    codes: list[str] = []
    deciding: list = []
    adverse_hit = any(adverse(proj, r["_e"], req) for r in skipped if "_e" in r)
    if not evals:
        result, codes = "inconclusive", []                                           # AGG-05
    elif not used:
        result, codes = "inconclusive", sorted({r["code"] for r in skipped})          # AGG-05
    else:
        fails10 = [r for r in used if r["verdict"] == "fail" and 10 in r["_v"].rows]
        passes = [r for r in used if r["verdict"] == "pass"]
        if fails10 and passes:
            result, codes = "inconclusive", ["evidence.conflict"]                    # AGG-02
        elif fails10:
            result, codes, deciding = "fail", ["bound.excludes"], fails10            # AGG-03
        else:                                                                         # AGG-04
            top_rank = max(lowest(r["_e"].vector) for r in used)
            top = [r for r in used if lowest(r["_e"].vector) == top_rank]
            verdicts = {r["verdict"] for r in top}
            if "inconclusive" in verdicts:
                result, codes = "inconclusive", sorted({r["code"] for r in top})
            elif verdicts == {"pass"}:
                result, codes, deciding = "pass", sorted({r["code"] for r in top}), top
            elif verdicts == {"fail"}:
                result, codes, deciding = "fail", sorted({r["code"] for r in top}), top
            else:
                result, codes = "inconclusive", ["evidence.conflict"]
    extra = []
    if adverse_hit:
        extra.append("evidence.excluded_adverse")
    if orphans.get((req["quantity"], effective)):
        extra.append("evidence.orphan_run")
    if errored:
        extra.append(errored[0].errors[0][0])
    if extra:  # AGG-10, OQ-12: never pass; a fail stays fail with the codes as additional reasons
        if result == "pass":
            result, codes, deciding = "inconclusive", [], []
        elif result != "fail":
            deciding = []
        codes = sorted(set(codes) | set(extra))
    if "evidence.conflict" in codes:
        flagged = [r for r in used if r["verdict"] in ("pass", "fail")]
        conflict = [{"evaluation": r["evaluation"], "contract": r["_e"].contract, "verdict": r["verdict"],
                     "bound": r["bound"]} for r in flagged]  # RPT-04
    else:
        conflict = []
    participating = used if not deciding else deciding
    maturity = {
        "fidelity_axis": ([{"evaluation": r["evaluation"], "fidelity_vector": r["fidelity_vector"]} for r in deciding]
                          if deciding else "undetermined"),                                       # MAT-02, MAT-03
        "lowest_chain_fidelity": (FIDELITIES[min(lowest(r["_e"].vector) for r in deciding)] if deciding else None),
        "participating": [{"evaluation": r["evaluation"], "fidelity_vector": r["fidelity_vector"]} for r in participating],
        "review_axis": "not-reviewed",                                                             # MAT-04 (M3)
        "status_axis": sorted({s for r in used + [x for x in skipped if "_e" in x] for s in r["_e"].statuses}),  # MAT-09
    }
    clean = lambda rows: [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]  # noqa: E731
    return {"result": result, "codes": codes, "missing_evaluations": not evals,
            "used": clean(used), "skipped": clean(skipped), "conflict_inspect": conflict, "maturity": maturity,
            "_deciding": deciding, "_used": used}


def missing_evidence(proj: Project, req: dict, agg: dict, effective: str | None = None) -> list[str]:
    """What compliance still needs (RPT-03, M0 acceptance): the compliance fidelity of each figure of merit in the
    chains, the adequacy table's 'with' upstreams and the requirement's own upstreams."""
    if agg["result"] == "pass":
        return []
    if agg["result"] == "fail" and "bound.excludes" in agg["codes"]:
        # an optimistic bound already misses the target: higher fidelity only adds effects that make it worse
        return ["none: excluded by an optimistic bound; change the candidate or the requirement"]
    rules = proj.fom_rules(req["quantity"]) or {}
    need = rules.get("compliance", "F5")
    mf = (req.get("verification") or {}).get("min_fidelity")
    if mf and RANK[mf] > RANK[need]:
        need = mf
    out: list[str] = []
    # the evaluations of this effective candidate only: another candidate's evidence never clears this row
    evs = [r["_e"] for r in agg["_used"]] or [e for e in proj.evals.values() if e.fom == req["quantity"]
                                              and e.effective == effective]
    evs = [e for e in evs if not e.ext.get("unavailable")]  # an unavailable record has no fidelity to count

    def present(e, foms) -> bool:  # the same test as the verdict rules (FID-11): compatible, not unavailable
        return any(u.fom in foms and compatible(u, e) and not u.ext.get("unavailable") for u in e.upstreams)
    if not any(RANK[e.fidelity] >= RANK[need] for e in evs):
        out.append(f"{req['quantity']} at {need} or above (compliance threshold)")
    for e in evs:
        for fom, fid, _ in e.vector[1:]:  # upstream entries; the evaluation's own is above
            rules_u = proj.fom_rules(fom) or {}
            c = rules_u.get("compliance", "F5")
            if RANK[fid] < RANK[c]:
                out.append(f"{fom} at {c} or above (in the chain of {e.eid}, now {fid})")
    for group in rules.get("compliance_upstreams", []):
        if not any(present(e, set(group)) for e in evs):
            alts = [f"{g} at {(proj.fom_rules(g) or {}).get('compliance', 'F5')} or above" for g in group]
            out.append(f"{' or '.join(alts)} (required for compliance, ADQ-02)")
    for r in (req.get("verification") or {}).get("required_upstreams", []):
        if not any(present(e, {r}) for e in evs):
            out.append(f"{r} (required by the requirement's verification)")
    return sorted(dict.fromkeys(out))


# ---------------------------------------------------------------- spec checks, orphans, screening, basis


def current_spec(proj: Project, records: list[dict]) -> tuple[Path | None, list[str]]:
    """DEC-08: the version the latest valid requirement-change points to, else the earliest created version; and the
    DEC-09 flags."""
    if not proj.specs:
        return None, []
    order = sorted(proj.specs, key=lambda p: (proj.docs[p]["provenance"]["created"],
                                              proj.docs[p]["extension"]["spec_version"]))
    current = order[0]
    pointed: set[Path] = set()
    changes = sorted((r for r in records if r["category"] == "requirement-change" and r["_valid"]),
                     key=lambda r: r["time"])
    for r in changes:
        paths = [p for p in r["_paths"] if p in proj.specs]
        if len(paths) == 2:
            after = max(paths, key=lambda p: proj.docs[p]["extension"]["spec_version"])
            pointed.add(after)
            current = after
    flags = []
    cur_v = proj.docs[current]["extension"]["spec_version"]
    if any(proj.docs[p]["extension"]["spec_version"] > cur_v and p not in pointed for p in proj.specs):
        flags.append("gate.requirement_change_missing")
    return current, flags


def check_spec(proj: Project, spec_path: Path) -> None:
    """ART-11, ART-12, ADQ-06: malformed-spec errors (design.*)."""
    ext = proj.docs[spec_path]["extension"]
    where = proj.rel(spec_path)
    ns = ext["design_id"]
    ids = [x["id"] for k in ("objectives", "requirements", "allocations", "constraints") for x in ext.get(k, [])]
    for i in ids:
        if not i.startswith(ns + ":"):
            proj.error("design.namespace", where, f"{i} is not in the design namespace {ns} (ART-06)")
    if len(set(ids)) != len(ids):
        proj.error("design.duplicate_id", where, "an id is declared twice")
    for a in ext.get("allocations", []):
        if a["rule"] == "quadrature" and not a.get("independent") and not a.get("correlation"):
            proj.error("design.allocation_dependence", where,
                       f"{a['id']}: a quadrature allocation needs independent items or a correlation matrix (ART-12)")
        req = next((r for r in ext.get("requirements", []) if r["id"] == a["requirement"]), None)
        if req is not None and req["comparator"] == "<=" and isinstance(req["target"], (int, float)):
            vals = [i["value"] for i in a["items"]]
            total = math.fsum(vals) if a["rule"] == "linear" else math.sqrt(math.fsum(v * v for v in vals))
            if total + a["margin"] > req["target"] * (1 + 1e-12):  # ART-12: the allocation closes on its target
                proj.error("design.allocation_not_closed", where,
                           f"{a['id']}: the items combine ({a['rule']}) to {total:.6g}; with the margin {a['margin']:g} "
                           f"that exceeds the target {req['target']:g} of {req['id']}")
        if a.get("correlation"):
            n = len(a["items"])
            c = a["correlation"]
            if len(c) != n or any(len(row) != n for row in c):
                proj.error("design.allocation_dependence", where, f"{a['id']}: the correlation matrix is not {n} x {n}")
    for kind in ("requirements", "constraints"):
        for r in ext.get(kind, []):
            if r["comparator"] == "range" and not (isinstance(r["target"], list) and len(r["target"]) == 2
                                                   and r["target"][0] <= r["target"][1]):
                proj.error("design.malformed", where, f"{r['id']}: a range target is [low, high]")
            elif r["comparator"] != "range" and not isinstance(r["target"], (int, float)):
                proj.error("design.malformed", where, f"{r['id']}: a one-sided target is a number")
            rules = proj.fom_rules(r["quantity"])
            if rules is None:
                continue
            missing = [d for d in rules.get("denominator_required", []) if d not in r["denominator"]]
            if missing:
                proj.error("design.denominator_incomplete", where, f"{r['id']}: the denominator lacks {missing} (ADQ-06)")
            design = proj.registry.fom_design(r["quantity"])
            if design and set(r["denominator"]) != set(design["denominator"]):
                proj.error("design.denominator_structure", where,
                           f"{r['id']}: denominator fields {sorted(r['denominator'])} do not follow the tool contract's "
                           f"{sorted(design['denominator'])} (ART-11)")


def check_budgets(proj: Project) -> None:
    """ART-24, ART-25: an author-entered budget uncertainty below the adequacy minimum of its basis is an error; an
    item without a source counts as 'estimate'."""
    mins = proj.adequacy.get("budget_min_relative_uncertainty", {})
    for cid, p in proj.candidates.items():
        for q, rows in (proj.docs[p]["extension"].get("budgets") or {}).items():
            for sid, item in rows.items():
                basis = item["basis"] if item.get("source") else "estimate"
                if "estimate" in item and "uncertainty" in item and item["estimate"] > 0:
                    need = mins.get(basis, max(mins.values() or [0])) * item["estimate"]
                    if item["uncertainty"] < need * (1 - 1e-12):
                        proj.error("design.budget_uncertainty_below_minimum", proj.rel(p),
                                   f"{cid} {q}.{sid}: uncertainty {item['uncertainty']} below the {basis} minimum {need:g}")


def orphan_runs(proj: Project) -> tuple[list[dict], dict]:
    """AGG-08: design runs (their script has a contract with a design block) that no evaluation's run_ref names."""
    referenced = {proj.resolve(e.ext["run_ref"]) for e in proj.evals.values() if e.ext.get("run_ref")}
    out, index = [], {}
    for p in proj.runs:
        doc = proj.docs[p]
        rext = doc.get("extension") or {}
        argv = rext.get("argv")
        if p in referenced or not isinstance(argv, list) or rext.get("scan_summary"):
            continue
        script = next((a for a in argv if isinstance(a, str) and a.endswith(".py")), "")
        c = proj.registry.by_script(script)
        if c is None:
            continue
        foms = {f["id"] for op in c["operations"] for f in (op.get("design") or {}).get("figures_of_merit", [])}
        if not foms:
            continue
        cands = [proj.docs[proj.resolve(i["ref"])]["extension"]["candidate_id"] for i in doc.get("inputs") or []
                 if isinstance(i, dict) and proj.docs.get(proj.resolve(str(i.get("ref"))), {}).get("artifact_type")
                 == "design-candidate"]
        bases = {b for c_ in cands for b in [proj.docs[x]["extension"].get("derived_from") for x in
                                              (proj.candidate_chain(c_) or [])] if b}
        leaves = [c_ for c_ in cands if c_ not in bases]
        digests = sorted({d for d in (proj.effective_digest(c_) for c_ in leaves) if d})
        out.append({"run": proj.rel(p), "figures_of_merit": sorted(foms), "candidates": leaves})
        for f in foms:
            for d in digests:
                index[(f, d)] = True
    return out, index


def comparison_basis(proj: Project, spec: dict, groups: dict) -> dict:
    """ART-15: the basis holds only if every pair of effective candidates that are not screened out differs by less
    than the tolerance after adding the propagated uncertainty at the coverage CL, from their F1 budget evaluations of
    the basis quantity. Budget items the two candidates share unchanged cancel in the difference and its uncertainty."""
    basis = spec["extension"].get("comparison_basis")
    if not basis:
        return {"declared": False, "holds": False, "reason": "comparison_basis is not declared"}
    q = basis["quantity"]
    rules = proj.fom_rules(q) or {}
    cl = rules.get("coverage_cl", proj.adequacy.get("default_coverage_cl", 0.95))
    vals, cids = {}, {}
    for d in groups:
        evs = [e for e in proj.evals.values() if e.fom == q and e.effective == d and e.fidelity == "F1"
               and not e.errors and not e.stale and e.ext.get("value") is not None and e.ext.get("uncertainty")]
        if not evs:
            return {"declared": True, "holds": False, "quantity": q,
                    "reason": f"no F1 {q} evaluation with an uncertainty for {groups[d]}"}
        e = evs[0]
        u = e.ext["uncertainty"]
        refs = [r for r in e.ext.get("parameter_refs", []) if r.startswith("budgets.")]
        items = proj.parameter_objects(e.ext.get("candidate", ""), refs) if refs else {}
        vals[d] = (e.ext["value"], max(sigma_equivalent(u, "minus"), sigma_equivalent(u, "plus")),
                   items if items and all(isinstance(x, dict) for x in items.values()) else None)
        cids[d] = e.ext.get("candidate", "")
    pairs = []
    holds = True
    k = z_one_sided(cl)
    for a, b in itertools.combinations(sorted(vals), 2):
        (va, sa, ia), (vb, sb, ib) = vals[a], vals[b]
        ref = (abs(va) + abs(vb)) / 2 or 1.0
        diff, sig, shared = abs(va - vb), math.hypot(sa, sb), []
        if ia is not None and ib is not None:
            # ART-15: a budget item cancels in the difference only when both candidates carry the same subsystem
            # (identical merged definition) with the same budget row (estimate, uncertainty, unit, basis, source):
            # equal numbers on different hardware are not the same object. The other items of each candidate add
            # linearly, as in budget-sum, and the two candidates add in quadrature.
            same = ("estimate", "uncertainty", "unit", "basis", "source")
            subs_a, subs_b = proj.effective(cids[a]) or {}, proj.effective(cids[b]) or {}
            shared = sorted(r for r in ia if isinstance(ib.get(r), dict)
                            and all(ia[r].get(f) == ib[r].get(f) for f in same)
                            and r.split(".", 2)[2] in subs_a
                            and subs_a[r.split(".", 2)[2]] == subs_b.get(r.split(".", 2)[2]))
            own_a = sum(float(ia[r].get("uncertainty") or 0.0) for r in ia if r not in shared)
            own_b = sum(float(ib[r].get("uncertainty") or 0.0) for r in ib if r not in shared)
            sig = math.hypot(own_a, own_b)
        ok = diff + k * sig <= basis["tolerance_relative"] * ref
        holds &= ok
        pairs.append({"candidates": [groups[a], groups[b]], "difference": diff, "uncertainty_one_sided": k * sig,
                      "shared_items": [r.split(".", 2)[2] for r in shared],
                      "tolerance": basis["tolerance_relative"] * ref, "holds": ok})
    return {"declared": True, "holds": holds and bool(pairs), "quantity": q, "coverage_cl": cl, "pairs": pairs,
            "reason": None if holds and pairs else ("fewer than two candidates" if not pairs else
                                                    "a difference with its uncertainty exceeds the tolerance")}


# ---------------------------------------------------------------- decision records and gates (DEC)


def load_records(proj: Project, design_id: str) -> list[dict]:
    """Design decision records of this design (DEC-17) from --decisions, with their validity (lineage.check_decision:
    schema, file hashes, the not-applicable closure) and the resolved artifact paths."""
    from contracts.lineage import check_decision
    out: list[dict] = []
    if proj.decisions_dir is None or not proj.decisions_dir.is_dir():
        return out
    for p in sorted(proj.decisions_dir.glob("*.json")):
        try:
            rec = load_json(p)
        except (OSError, ValueError):
            continue
        if not isinstance(rec, dict) or rec.get("category") not in DESIGN_CATEGORIES or rec.get("analysis") != design_id:
            continue
        rep = check_decision(rec, None, proj.root)
        # the record's name relative to the decisions folder's parent: no host path in the derived report
        rel = str(p.relative_to(proj.decisions_dir.parent))
        rec = dict(rec, _file=rel, _valid=rep.ok and (rec.get("actor") or {}).get("kind") == "human",  # DEC-05
                   _findings=sorted({f.code for f in rep.findings if f.severity == "error"}),
                   _paths=[proj.resolve(a["ref"]) for a in rec.get("artifacts", [])])
        out.append(rec)
    return out


def gate_flags(proj: Project, records: list[dict], current: Path, screened: set, verdict_rows: dict) -> tuple[list, list]:
    """DEC-02, DEC-07, DEC-12 for H1..H3: a gate is clear when a valid human record of its category lists exactly the
    artifacts DEC-12 names for the current state."""
    spec = proj.docs[current]["extension"]
    status = []

    def covers(cat: str, wanted: set[Path], content_ok: bool, why: str) -> bool:
        hits = [r for r in records if r["category"] == cat]
        ok = any(r["_valid"] and set(r["_paths"]) == wanted and content_ok for r in hits)
        status.append({"category": cat, "clear": ok, "records": [{"file": r["_file"], "valid": r["_valid"],
                       "findings": r["_findings"], "exact_artifacts": set(r["_paths"]) == wanted} for r in hits],
                       "content": None if content_ok else why})
        return ok

    flags = []
    h1_ok = bool(spec.get("objectives")) and all(o.get("observable") and o.get("range") for o in spec["objectives"])
    if not covers("design-scope", {current}, h1_ok, "each goal needs an observable and a range"):
        flags.append("gate.H1_missing")
    allocs = {a["id"]: a for a in spec.get("allocations", [])}
    driving = [r for r in spec["requirements"] if r["kind"] == "driving"]
    h2_ok = bool(spec.get("comparison_basis")) and all(
        r.get("denominator") and r.get("allocation") in allocs and "margin" in allocs[r["allocation"]] for r in driving)
    if not covers("requirements-baseline", {current}, h2_ok,
                  "each driving requirement needs a denominator, an allocation with margin, and comparison_basis"):
        flags.append("gate.H2_missing")
    # H3: listed candidates plus all capability.unavailable evaluations of them
    h3 = [r for r in records if r["category"] == "architecture-selection"]
    h3_ok = False
    for r in h3:
        cands = [p for p in r["_paths"] if proj.docs.get(p, {}).get("artifact_type") == "design-candidate"]
        cids = {proj.docs[p]["extension"]["candidate_id"] for p in cands}
        unav = {e.path for e in proj.evals.values() if e.ext.get("unavailable") and e.ext.get("candidate") in cids}
        complete = bool(cids) and all(
            verdict_rows.get((req["id"], cid)) for req in spec["requirements"] for cid in cids) and not (cids & screened)
        if r["_valid"] and set(r["_paths"]) == set(cands) | unav and complete:
            h3_ok = True
    status.append({"category": "architecture-selection", "clear": h3_ok,
                   "records": [{"file": r["_file"], "valid": r["_valid"], "findings": r["_findings"]} for r in h3]})
    if not h3_ok:
        flags.append("gate.H3_missing")
    return flags, status


# ---------------------------------------------------------------- the whole derivation


def derive(artifacts: Path, decisions: Path | None = None, contract_dirs: list[Path] | None = None,
           adequacy: dict | None = None) -> dict:
    proj = Project(artifacts, decisions, Registry(contract_dirs) if contract_dirs else None, adequacy)
    for prob in proj.registry.problems:
        proj.error("design.contract_unreadable", "$contracts", prob)
    designs = {proj.docs[p]["extension"]["design_id"] for p in proj.specs}
    if len(designs) > 1:
        proj.error("design.several_designs", ".", f"one artifacts_dir holds one design; found {sorted(designs)}")
    design_id = sorted(designs)[0] if designs else None
    records = load_records(proj, design_id) if design_id else []
    proj.records = records  # measurement-acceptance approvals are read by check_f5 (FID-06)
    analyze_evaluations(proj)
    for e in proj.evals.values():
        for code, msg in e.errors:
            proj.error(code, e.rel, msg)
    check_budgets(proj)
    check_calibration(proj)
    current, change_flags = current_spec(proj, records)
    out: dict = {"design_id": design_id, "note": NOTE,
                 "adequacy": {"version": proj.adequacy.get("adequacy_version"), "state": proj.adequacy.get("state"),
                              "frozen": bool(proj.adequacy.get("frozen")),
                              "provisional_pass": not proj.adequacy.get("frozen")}}
    if current is None:
        proj.error("design.no_spec", ".", "no design-spec in the artifacts_dir")
        out.update(status="error", errors=proj.errors)
        return out
    check_spec(proj, current)
    spec = proj.docs[current]
    groups: dict[str, list[str]] = {}
    for cid in sorted(proj.candidates):
        d = proj.effective_digest(cid)
        if d:
            groups.setdefault(d, []).append(cid)
    orphans, orphan_index = orphan_runs(proj)
    rows_out = {}
    verdict_rows: dict = {}
    for kind in ("requirements", "constraints"):
        items = []
        for req in spec["extension"].get(kind, []):
            per = []
            for d, cids in groups.items():
                agg = aggregate(proj, req, d, orphan_index)
                row = {"effective_candidate": d, "candidates": cids, "result": agg["result"], "codes": agg["codes"],
                       "provisional": agg["result"] == "pass" and not proj.adequacy.get("frozen"),
                       "missing_evaluations": agg["missing_evaluations"], "used": agg["used"],
                       "skipped": agg["skipped"], "conflict_inspect": agg["conflict_inspect"],
                       "maturity": agg["maturity"], "missing_evidence": missing_evidence(proj, req, agg, d)}
                if kind == "requirements" and req["kind"] == "driving" and agg["result"] == "inconclusive":
                    row["proposed_disposition"] = ("accept-risk" if agg["codes"] == ["capability.unavailable"]
                                                   else "next-study")  # RPT-05
                per.append(row)
                for cid in cids:
                    verdict_rows[(req["id"], cid)] = any(r["row"] >= 9 for r in agg["used"]) or any(
                        r.get("code") == "capability.unavailable" for r in agg["skipped"])
            items.append({"id": req["id"], "kind": req.get("kind", req.get("hardness")), "quantity": req["quantity"],
                          "comparator": req["comparator"], "target": req["target"], "unit": req["unit"],
                          "matrix": per})
        rows_out[kind] = items
    # screening (CHN-11, CHN-12)
    screened, cand_out = set(), []
    for d, cids in groups.items():
        hard = {x["id"] for x in spec["extension"]["constraints"] if x["hardness"] == "hard"}
        reasons = [f"{c['id']} fails" for c in rows_out["constraints"] if c["id"] in hard
                   and any(m["effective_candidate"] == d and m["result"] == "fail" for m in c["matrix"])]
        reasons += [f"{r['id']} fails" for r in rows_out["requirements"] if r["kind"] == "driving"
                    and any(m["effective_candidate"] == d and m["result"] == "fail" for m in r["matrix"])]
        at_risk = []
        for e in proj.evals.values():
            if e.effective == d and e.fidelity == "F0":
                at_risk.append(f"{e.eid}: F0 evaluation")
                for c in spec["extension"]["constraints"]:
                    v = e.ext.get("value")
                    if c["quantity"] == e.fom and v is not None and not all(meets(v, s) for s in sides(c)):
                        at_risk.append(f"{e.eid}: F0 estimate exceeds {c['id']}")
        if reasons:
            screened |= set(cids)
        cand_out.append({"effective_candidate": d, "candidates": cids, "screened_out": bool(reasons),
                         "screened_out_reasons": reasons, "at_risk": sorted(set(at_risk))})
    flags, gates = gate_flags(proj, records, current, screened, verdict_rows)
    flags = flags + change_flags
    for item in rows_out["requirements"]:  # RPT-05: dispositions are proposed for candidates entering convergence only
        for m in item["matrix"]:
            if set(m["candidates"]) & screened:
                m["screened_out"] = True
                m.pop("proposed_disposition", None)
                if m["result"] == "inconclusive":
                    m["disposition_note"] = "none: the candidate is screened out"
            elif item["kind"] != "driving" and m["result"] == "inconclusive":
                m["disposition_note"] = "none required at H4: derived requirement (RPT-05, MAT-04 d)"
    basis = comparison_basis(proj, spec, {d: c for d, c in groups.items() if not set(c) & screened})  # CHN-11 first
    stale = sorted(e.eid for e in proj.evals.values() if e.stale)
    out.update({
        "status": "error" if proj.errors else "ok",
        "current_spec": proj.rel(current), "spec_version": spec["extension"]["spec_version"],
        "gate_flags": sorted(flags), "gates": gates,
        "candidates": cand_out,
        "requirements": rows_out["requirements"], "constraints": rows_out["constraints"],
        "orphan_runs": orphans,
        "unavailable": sorted(e.eid for e in proj.evals.values() if e.ext.get("unavailable")),
        "stale_evaluations": stale,
        "comparison_basis": basis,
        "ranking": ranking(proj, {d: c for d, c in groups.items() if not set(c) & screened}, basis),
        "evaluations": [{"evaluation": e.eid, "file": e.rel, "figure_of_merit": e.fom, "fidelity": e.fidelity,
                         "bound_derived": e.bound, "contract": e.contract,
                         "fidelity_vector": [{"figure_of_merit": f, "fidelity": x, "evaluation": i} for f, x, i in e.vector],
                         "stale": e.stale, "errors": [c for c, _ in e.errors]} for e in proj.evals.values()],
        "errors": proj.errors,
    })
    review = review_axis(proj, records, out)
    if review["reviewed"]:
        for item in out["requirements"] + out["constraints"]:
            for m in item["matrix"]:
                m["maturity"]["review_axis"] = "reviewed"
    out["review"] = review
    out["baseline"] = "baselined" if review["reviewed"] else "draft"
    return out


def ranking(proj: Project, groups: dict, basis: dict) -> dict:
    """CHN-00, CHN-06, RPT-07: candidates are ranked on expected measurement precision only when the comparison basis
    holds and every candidate that survives screening has a usable expected-precision evaluation (not stale, no error,
    not an optimistic bound) with the same fidelity vector and the same denominator; otherwise the ranking is refused
    with every reason that applies. A ranking is an ordering of these candidates, never a claim of a global optimum."""
    fom = "expected-precision"
    reasons = []
    if not basis.get("holds"):
        reasons.append(f"comparison_basis does not hold: {basis.get('reason')} (ART-15, RPT-07)")
    if len(groups) < 2:
        reasons.append("fewer than two candidates survive screening")
    picks, lacking = {}, []
    for d, cids in groups.items():
        usable = [e for e in proj.evals.values() if e.fom == fom and e.effective == d and not e.errors and not e.stale
                  and not e.invalid and not e.unresolved and e.bound in ("estimate", "conservative")
                  and e.ext.get("value") is not None]
        if not usable:
            lacking += cids
            continue
        picks[d] = max(usable, key=lambda e: lowest(e.vector))
    if lacking:
        reasons.append(f"{', '.join(sorted(lacking))} have no non-optimistic, current {fom} evaluation (CHN-06)")
    if reasons:
        return {"status": "refused", "reason": "; ".join(reasons), "reasons": reasons}
    vectors = {tuple(sorted((f, x) for f, x, _ in e.vector)) for e in picks.values()}
    dens = {json.dumps(e.ext.get("denominator"), sort_keys=True) for e in picks.values()}
    if len(vectors) != 1:
        return {"status": "refused", "reason": "the expected-precision evaluations have different fidelity vectors (CHN-06)"}
    if len(dens) != 1:
        return {"status": "refused", "reason": "the expected-precision evaluations have different denominators (CHN-06)"}
    order = sorted(picks.items(), key=lambda kv: kv[1].ext["value"])
    return {"status": "ranked", "figure_of_merit": fom, "fidelity_vector": [list(v) for v in sorted(vectors.pop())],
            "order": [{"candidates": groups[d], "evaluation": e.eid, "value": e.ext["value"],
                       "uncertainty": e.ext.get("uncertainty"), "bound": e.bound} for d, e in order],
            "note": "an ordering of these candidates on expected precision (smaller is better); differences within the "
                    "uncertainties are not decided, and no global optimum is claimed"}


def report_payload(full: dict) -> dict:
    """The derivation as the design report stores it (evaluate_design.py report): everything but the per-evaluation
    list."""
    return {k: v for k, v in full.items() if k != "evaluations"}


def payload_digest(payload: dict, exclusions) -> str:
    """MAT-05: the canonical hash of a report payload without the excluded keys (at any depth): the fields the H4
    approval itself sets, and the rendering choices."""
    def strip(v):
        if isinstance(v, dict):
            return {k: strip(x) for k, x in v.items() if k not in exclusions}
        if isinstance(v, list):
            return [strip(x) for x in v]
        return v
    return canonical_sha256(strip(payload))


def review_axis(proj: Project, records: list[dict], full: dict) -> dict:
    """MAT-04..MAT-08, DEC-12, DEC-13, DEC-20: only a design-baseline (H4) record sets the review axis, and only when
    the actor is human and every hash matches, artifacts[] is exactly the derived design report and the evaluations it
    used, the report equals the one recomputed now (MAT-05 exclusions), and dispositions[] covers every inconclusive
    driving requirement of a candidate that survives screening; in addition (an interpretation: H4 follows H1-H3 in
    the phase order) no earlier gate flag is open. The axis is advisory: the actor is self-declared (LIM-01)."""
    excl = set((proj.adequacy.get("hash_exclusions") or {}).get("fields", []))
    now = payload_digest(report_payload(full), excl)
    used = {proj.resolve(r["file"]) for item in full.get("requirements", []) + full.get("constraints", [])
            for m in item["matrix"] for r in m["used"]}
    open_driving = {item["id"] for item in full.get("requirements", []) if item["kind"] == "driving"
                    and any(m["result"] == "inconclusive" and not m.get("screened_out") for m in item["matrix"])}
    open_gates = sorted(f for f in full.get("gate_flags", []) if f.startswith("gate."))
    out = []
    reviewed_by = None
    for r in (x for x in records if x["category"] == "design-baseline"):
        reasons = []
        if open_gates:
            reasons.append(f"earlier gates still open: {', '.join(open_gates)} (H4 follows H1-H3)")
        if not r["_valid"]:
            reasons.append("not a valid human record (actor, schema or a changed hash): " + ", ".join(r["_findings"]))
        reports = [p for p in r["_paths"] if proj.docs.get(p, {}).get("artifact_type") == "communication"
                   and "design_report" in (proj.docs[p].get("extension") or {})]
        evals = {p for p in r["_paths"] if proj.docs.get(p, {}).get("artifact_type") == "design-evaluation"}
        others = set(r["_paths"]) - set(reports) - evals
        if len(reports) != 1:
            reasons.append("artifacts[] lists exactly one derived design report")
        elif payload_digest(proj.docs[reports[0]]["extension"]["design_report"], excl) != now:
            reasons.append("the approved report differs from the one recomputed now (MAT-04 e)")
        if evals != used or others:
            reasons.append("artifacts[] is not exactly the report and the evaluations it used (MAT-04 c)")
        missing = sorted(open_driving - {d["requirement"] for d in r.get("dispositions") or []})
        if missing:
            reasons.append(f"no disposition for the inconclusive driving requirement(s) {missing} (DEC-13)")
        out.append({"file": r["_file"], "sets_review_axis": not reasons, "reasons": reasons})
        if not reasons:
            reviewed_by = r["_file"]
    return {"reviewed": reviewed_by is not None, "record": reviewed_by, "records": out,
            "note": "advisory: the actor is self-declared; formal approval is a trusted gate outside the agent (LIM-01)"}


def status_summary(full: dict) -> dict:
    """RES-02: verdicts, stale evaluations, requirements without evaluations, missing gates, screened-out and at-risk."""
    reqs = full.get("requirements", []) + full.get("constraints", [])
    return {"status": full.get("status"), "design_id": full.get("design_id"), "current_spec": full.get("current_spec"),
            "gate_flags": full.get("gate_flags", []),
            "verdicts": [{"id": r["id"], "candidates": m["candidates"], "result": m["result"], "codes": m["codes"],
                          "provisional": m["provisional"]} for r in reqs for m in r["matrix"]],
            "stale_evaluations": full.get("stale_evaluations", []),
            "missing_evaluations": [{"id": r["id"], "candidates": m["candidates"]} for r in reqs for m in r["matrix"]
                                    if m["missing_evaluations"]],
            "screened_out": [c["candidates"] for c in full.get("candidates", []) if c["screened_out"]],
            "at_risk": [{"candidates": c["candidates"], "flags": c["at_risk"]} for c in full.get("candidates", [])
                        if c["at_risk"]],
            "orphan_runs": full.get("orphan_runs", []), "errors": full.get("errors", []), "note": NOTE}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "status"):
        p = sub.add_parser(name)
        p.add_argument("--artifacts", type=Path, required=True)
        p.add_argument("--decisions", type=Path)
        p.add_argument("--contracts", type=Path, action="append",
                       help="tool contract folder (repeatable; default contracts/tool_contracts)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if not args.artifacts.is_dir() or (args.decisions is not None and not args.decisions.is_dir()):
        print(json.dumps({"status": "unreadable", "error": "--artifacts and --decisions name folders"}))
        return 2
    full = derive(args.artifacts, args.decisions, args.contracts)
    print(json.dumps(full if args.cmd == "check" else status_summary(full), indent=1, default=str))
    return 1 if full.get("status") == "error" else 0


if __name__ == "__main__":
    sys.exit(main())
