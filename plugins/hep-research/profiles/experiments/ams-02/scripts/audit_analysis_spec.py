#!/usr/bin/env python3
"""Audit a structured AMS analysis specification (JSON or YAML) against the skill's invariants.

Purpose: turn the non-negotiable invariants (explicit Z/A/units, conditional
denominators, corrections applied once, no automatic cancellation, tail-aware
charge confusion, validated low-count statistics, traceable AMS numbers) into a
repeatable review, and give a verdict-first report a human reviewer can build on.

What it does: reads the specification described in modules/analysis-artifacts.md,
runs the checks, and reports findings in four classes:
  error       the specification would give a wrong or untraceable result as written
  warning     a gap or weak practice that should be closed before the result is trusted
  proposal    an item the specification itself labels [Proposal] (kept visible, not judged)
  unresolved  an input the specification says is missing or unknown (never an error)
Verdict: `blocked` (any error), `needs work` (warnings only), or `acceptable with open
inputs`. A clean audit is NOT approval of the physics: it only means the specification
is internally complete and consistent. Numbers in free text are only heuristically
scanned; register every AMS-specific number in `parameters`.

Usage (from the skill directory):
  python3 profiles/experiments/ams-02/scripts/audit_analysis_spec.py SPEC.json|SPEC.yaml [--claims evidence/claims.json | --no-claims]
                                         [--markdown] [--low-count-threshold N] [--strict]
The low-count threshold (default 20 expected counts in the smallest bin) is a triage
[Proposal], not a statistical result; toy validation is the real criterion.
A `.yaml` or `.yml` file is read with the strict YAML subset of scripts/yaml_subset.py (anything
outside the subset is exit 2, not a guess); every other suffix is read as JSON.
Exit codes: 0 no errors (warnings allowed unless --strict); 1 errors; 2 file unreadable
or not a JSON/YAML object. Standard library only. Importable: audit_spec(spec, claims, threshold).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path
_PLUGIN_ROOT = _Path(__file__).resolve().parents[4]
if str(_PLUGIN_ROOT) not in _sys.path:  # make core/ and contracts/ importable when run as a script
    _sys.path.insert(0, str(_PLUGIN_ROOT))
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import yaml_subset  # noqa: E402  (strict YAML subset, standard library only)

ROOT = Path(__file__).resolve().parents[1]  # the ams-02 profile folder
VARIABLES = {"rigidity": "GV", "momentum": "GeV/c", "total_energy": "GeV", "kinetic_energy": "GeV",
             "kinetic_energy_per_nucleon": "GeV/n"}
TARGETS = {"flux", "ratio", "fraction", "limit", "parameter", "discovery", "efficiency"}
LEVELS = {"detector", "object", "flux"}
CATEGORIES = {"veto", "calibration", "efficiency", "acceptance", "exposure", "livetime", "response"}
PROVENANCE = {"documented", "general_method", "proposal", "user_supplied", "unknown"}
LABELS = {"Documented", "General method", "Proposal", "Unknown/needs input"}
GAUSSIAN_LIKE = {"gaussian", "wilks", "asymptotic", "s_over_sqrt_b"}
SEVERITIES = ("error", "warning", "proposal", "unresolved")
NUMBER_IN_RULE = re.compile(r"[<>≤≥]=?\s*\d|\d\s*[<>≤≥]|=\s*\d")


def _d(x) -> dict:
    return x if isinstance(x, dict) else {}


def _l(x) -> list:
    return x if isinstance(x, list) else []


def _empty(x) -> bool:
    return x is None or x == "" or x == [] or x == {}


class Audit:
    def __init__(self) -> None:
        self.findings: list[dict] = []

    def add(self, severity: str, code: str, path: str, message: str, remedy: str = "") -> None:
        self.findings.append({"severity": severity, "code": code, "path": path, "message": message, "remedy": remedy})


def _measurement(spec: dict, a: Audit) -> None:
    m = spec.get("measurement")
    if not isinstance(m, dict):
        a.add("error", "measurement.missing", "measurement", "measurement object is missing", "Fill measurement with target, estimand, level, species, variable, unit, range")
        return
    if _empty(m.get("estimand")):
        a.add("error", "estimand.missing", "measurement.estimand", "no estimand: the quantity, species, variable, range and what is held fixed are undefined",
              "State one sentence naming the quantity and its conditions")
    if m.get("level") not in LEVELS:
        a.add("error", "level.ambiguous", "measurement.level", f"measurement level must be one of {sorted(LEVELS)}, got {m.get('level')!r}",
              "Say whether the result is a detector-level, object-level, or flux-level statement")
    if m.get("target") not in TARGETS:
        a.add("error", "target.undefined", "measurement.target", f"target must be one of {sorted(TARGETS)}, got {m.get('target')!r}")
    variable = m.get("variable")
    if variable not in VARIABLES:
        a.add("error", "variable.undefined", "measurement.variable", f"variable must be one of {sorted(VARIABLES)}, got {variable!r}",
              "Rigidity, momentum, total energy, kinetic energy and kinetic energy per nucleon are different variables")
    unit = m.get("unit")
    if _empty(unit):
        a.add("error", "unit.undefined", "measurement.unit", "unit not declared")
    elif variable in VARIABLES and unit != VARIABLES[variable]:
        a.add("error", "unit.mismatch", "measurement.unit", f"unit '{unit}' does not belong to variable '{variable}' (expected '{VARIABLES[variable]}')",
              "Do not label rigidity in GeV/c or momentum in GV")
    rng, edges = m.get("range"), m.get("bin_edges")
    if not (isinstance(rng, list) and len(rng) == 2 and all(isinstance(x, (int, float)) for x in rng) and rng[0] < rng[1]):
        a.add("error", "range.invalid", "measurement.range", "range must be [low, high] with low < high")
    if not (isinstance(edges, list) and len(edges) >= 2 and all(isinstance(x, (int, float)) for x in edges)
            and all(b > a for a, b in zip(edges, edges[1:]))):
        a.add("error", "binning.invalid", "measurement.bin_edges", "bin_edges must be strictly increasing numbers (at least two)")
    elif isinstance(rng, list) and len(rng) == 2 and (edges[0] < rng[0] or edges[-1] > rng[1]):
        a.add("warning", "binning.outside_range", "measurement.bin_edges", "bin edges extend outside the declared range")
    species = _l(m.get("species"))
    if not species:
        a.add("error", "species.missing", "measurement.species", "no species declared", "List each species with abs_Z, A, charge_sign, mass_GeV")
    for i, sp in enumerate(species):
        p = f"measurement.species[{i}]"
        sp = _d(sp)
        z = sp.get("abs_Z")
        if isinstance(z, bool) or not isinstance(z, int) or z < 1:
            a.add("error", "species.abs_Z", p, "abs_Z (|Z|) must be a positive integer; rigidity is not momentum for |Z| != 1")
        if sp.get("charge_sign") not in (1, -1, "both", "+1", "-1"):
            a.add("error", "species.charge_sign", p, "charge_sign must be +1, -1 or 'both' (sign comes from the Tracker and is a separate observable)")
        needs_mass = variable in ("total_energy", "kinetic_energy", "kinetic_energy_per_nucleon")
        mass = sp.get("mass_GeV")
        if needs_mass and (not isinstance(mass, (int, float)) or isinstance(mass, bool) or mass <= 0):
            a.add("error", "species.mass", p, f"variable '{variable}' needs a positive mass_GeV")
        if variable == "kinetic_energy_per_nucleon" and (isinstance(sp.get("A"), bool) or not isinstance(sp.get("A"), int) or sp["A"] < 1):
            a.add("error", "species.A", p, "kinetic_energy_per_nucleon needs an integer A")
        elif sp.get("A") is None and variable != "kinetic_energy_per_nucleon":
            a.add("warning", "species.A_missing", p, "A not declared; an elemental target then needs an explicit isotope-composition assumption")
    ds = _d(spec.get("data_scope"))
    if ds.get("data_or_mc") not in ("data", "mc", "both"):
        a.add("error", "data_scope.undefined", "data_scope.data_or_mc", "declare data, mc or both")
    if ds.get("data_or_mc") in ("data", "both") and _empty(_d(ds.get("period")).get("start")):
        a.add("unresolved", "data_scope.period", "data_scope.period", "data-taking period not declared")
    if m.get("sample") not in ("public", "internal"):
        a.add("unresolved", "sample.undeclared", "measurement.sample", "state whether this is public or internal work")


def _observables(spec: dict, a: Audit) -> None:
    obs = _l(spec.get("observables"))
    if not obs:
        a.add("warning", "observables.missing", "observables", "no reconstructed observables or subsystem roles listed")
    for i, o in enumerate(obs):
        o = _d(o)
        if o.get("role") == "charge_sign" and o.get("subsystem") != "Tracker":
            a.add("error", "observable.charge_sign_source", f"observables[{i}]",
                  f"charge sign assigned to '{o.get('subsystem')}': only the Tracker/magnet measures charge sign")


def _validations(items: list, base: str, a: Audit) -> None:
    for i, v in enumerate(items):
        v = _d(v)
        missing = [k for k in ("metric", "threshold", "action") if _empty(v.get(k))]
        if missing:
            a.add("error", "validation.incomplete", f"{base}[{i}]", f"validation lacks {', '.join(missing)}: 'reasonable agreement' is not validation",
                  "State a metric, the deviation that triggers action, and the action")


def _selections(spec: dict, a: Audit) -> None:
    sels = _l(spec.get("selections"))
    if not sels:
        a.add("warning", "selections.missing", "selections", "no selection ledger")
    for i, s in enumerate(sels):
        s, p = _d(s), f"selections[{i}]"
        if _empty(s.get("conditional_denominator")):
            a.add("error", "selection.no_denominator", p, f"selection '{s.get('name')}' has no conditional denominator: its efficiency cannot be combined")
        if _empty(s.get("validation")):
            a.add("error", "selection.no_validation", p, f"selection '{s.get('name')}' has no validation")
        else:
            _validations(_l(s.get("validation")), f"{p}.validation", a)
        if NUMBER_IN_RULE.search(str(s.get("definition", ""))) and _empty(s.get("parameters")):
            a.add("warning", "selection.unregistered_number", p,
                  "definition contains a numeric threshold not registered in parameters (heuristic scan): AMS-specific numbers need provenance")


def _backgrounds(spec: dict, a: Audit) -> None:
    bgs = _l(spec.get("backgrounds"))
    if not bgs:
        a.add("warning", "backgrounds.none", "backgrounds", "no backgrounds listed: justify that none exist or list them")
    for i, b in enumerate(bgs):
        b, p = _d(b), f"backgrounds[{i}]"
        if _empty(b.get("estimator")):
            a.add("error", "background.no_estimator", p, f"background '{b.get('name')}' has no estimator")
        if _empty(b.get("control_region")) and _empty(b.get("constraint")):
            a.add("error", "background.no_constraint", p, f"background '{b.get('name')}' has neither a control region nor another constraint")
        elif not _empty(b.get("control_region")):
            if _empty(b.get("transfer_model")):
                a.add("warning", "background.no_transfer_model", p, "control region used without a transfer model (what is assumed to carry over to the signal region)")
            if _empty(b.get("contamination_correction")):
                a.add("warning", "background.no_contamination", p, "signal contamination of the control region is not addressed")
        if _empty(b.get("closure_test")):
            a.add("warning", "background.no_closure", p, "no closure test")
        if b.get("estimate_basis") == "gaussian_core":
            a.add("error", "tail.gaussian_core", p, "background estimated from a Gaussian core: tails dominate rare backgrounds")


def _corrections(spec: dict, a: Audit) -> None:
    rows = _l(spec.get("corrections"))
    seen: dict[str, list] = {}
    for i, c in enumerate(rows):
        c = _d(c)
        eid = c.get("effect_id")
        if _empty(eid):
            a.add("error", "correction.no_effect_id", f"corrections[{i}]", "each correction needs an effect_id naming the physical effect")
            continue
        if c.get("category") not in CATEGORIES:
            a.add("error", "correction.bad_category", f"corrections[{i}]", f"category must be one of {sorted(CATEGORIES)}, got {c.get('category')!r}")
        seen.setdefault(eid, []).append(c)
    for eid, items in seen.items():
        if len(items) > 1:
            where = "; ".join(f"{x.get('category')} in {x.get('applied_in')}" for x in items)
            a.add("error", "correction.double_applied", "corrections", f"effect '{eid}' is corrected {len(items)} times ({where}); one physical effect belongs in exactly one category",
                  "Keep one row; let a residual systematic cover only what the correction leaves")
    response, estimator = _d(spec.get("response")), _d(spec.get("estimator"))
    in_response = set(_l(response.get("includes"))) | {c.get("category") for c in map(_d, rows) if str(c.get("applied_in", "")).startswith("response")}
    in_estimator = set(_l(estimator.get("applies"))) | {c.get("category") for c in map(_d, rows) if str(c.get("applied_in", "")).startswith("estimator")}
    both = sorted(x for x in (in_response & in_estimator) if x)
    if both:
        a.add("error", "correction.response_and_estimator", "response/estimator", f"{both} applied both inside the response and again in the estimator",
              "Apply each of efficiency, acceptance, exposure once")
    applies = set(_l(estimator.get("applies")))
    if "exposure" in applies and applies & {"acceptance", "livetime"}:
        a.add("error", "exposure.decomposed_and_composite", "estimator.applies",
              "exposure (acceptance x livetime x transmission) is applied together with acceptance or livetime",
              "Use exposure alone, or its factors alone; if 'exposure' here means time only, call it livetime")
    if estimator.get("form") == "diagonal" and _empty(estimator.get("migration_study")):
        a.add("warning", "estimator.diagonal_unvalidated", "estimator", "diagonal estimator without a migration study: it is invalid under appreciable migration",
              "Show negligible migration with the response matrix, or use a response model")


def _response(spec: dict, a: Audit) -> None:
    r, m = _d(spec.get("response")), _d(spec.get("measurement"))
    method, form = _d(spec.get("inference")).get("method"), _d(spec.get("estimator")).get("form")
    needs = method in ("unfolding", "forward_fold") or form in ("response_model", "forward_fold")
    if not r:
        if needs:
            a.add("error", "response.missing", "response", "the method needs a response but none is declared")
        return
    for key in ("truth_variable", "reco_variable", "orientation", "normalization"):
        if _empty(r.get(key)):
            a.add("error", "response.card_incomplete", f"response.{key}", f"response card lacks {key}")
    tv, rv = r.get("truth_variable"), r.get("reco_variable")
    if tv and rv and tv != rv and _empty(r.get("variable_conversion")):
        a.add("error", "response.variable_mixing", "response", f"truth '{tv}' and reconstructed '{rv}' differ with no variable_conversion declared")
    if tv and m.get("variable") and tv != m["variable"]:
        a.add("error", "variable.mixed", "response.truth_variable", f"response truth variable '{tv}' differs from the measurement variable '{m['variable']}'",
              "Convert the binning or the response explicitly (scripts/ams_kinematics.py bins)")


def _ratio(spec: dict, a: Audit) -> None:
    if _d(spec.get("measurement")).get("target") not in ("ratio", "fraction"):
        return
    r = _d(spec.get("ratio"))
    if not r:
        a.add("error", "ratio.missing", "ratio", "a ratio or fraction needs a ratio section: numerator, denominator and the treatment of each shared effect")
        return
    for key in ("numerator", "denominator"):
        if _empty(r.get(key)):
            a.add("error", "ratio.incomplete", f"ratio.{key}", f"ratio lacks {key}")
    cancels = _l(r.get("cancellations"))
    if not cancels:
        a.add("error", "ratio.no_cancellation_analysis", "ratio.cancellations", "no cancellation analysis: acceptance, efficiency and systematics do not cancel automatically")
    for i, c in enumerate(cancels):
        c, p = _d(c), f"ratio.cancellations[{i}]"
        t = c.get("treatment")
        if t not in ("cancels", "correlated", "partial", "independent"):
            a.add("error", "ratio.bad_treatment", p, f"treatment must be cancels/correlated/partial/independent, got {t!r}")
        elif t == "cancels" and (_empty(c.get("correlation_model")) or _empty(c.get("verification"))):
            a.add("error", "ratio.cancellation_unsupported", p, f"'{c.get('effect')}' assumed to cancel without a correlation model and a verification",
                  "Give the correlation model and the check that shows it (per effect, per bin)")
        elif t in ("correlated", "partial") and _empty(c.get("correlation_model")):
            a.add("error", "ratio.no_correlation_model", p, f"'{c.get('effect')}' is {t} but has no correlation model")


def _inference(spec: dict, threshold: float, a: Audit) -> None:
    inf, tgt = _d(spec.get("inference")), _d(spec.get("measurement")).get("target")
    if not inf or _empty(inf.get("method")) or _empty(inf.get("parameters_of_interest")):
        a.add("error", "inference.missing", "inference", "inference needs a method and parameters_of_interest")
        return
    approx = inf.get("approximation")
    if approx in GAUSSIAN_LIKE and inf.get("approximation_validated") is not True:
        low = inf.get("min_expected_counts")
        boundary = inf.get("parameter_on_boundary") is True
        problem = boundary or tgt in ("limit", "discovery") or (isinstance(low, (int, float)) and low < threshold)
        if problem:
            why = "parameter on a boundary" if boundary else ("limit/discovery target" if tgt in ("limit", "discovery") else f"expected counts {low} below {threshold}")
            a.add("error", "inference.gaussian_low_count", "inference.approximation",
                  f"'{approx}' approximation not validated with {why}: Gaussian, Wilks and S/sqrt(B) fail near boundaries and at low counts",
                  "Use exact Poisson or toy-validated intervals and record the seed and configuration")
        elif low is None:
            a.add("unresolved", "inference.expected_counts_unknown", "inference.min_expected_counts", f"'{approx}' approximation with unknown expected counts per bin")
        else:
            a.add("warning", "inference.approximation_unvalidated", "inference.approximation", f"'{approx}' approximation used without validation (counts appear large)")


def _systematics(spec: dict, a: Audit) -> None:
    rows = _l(spec.get("systematics"))
    if not rows:
        a.add("warning", "systematics.none", "systematics", "no systematic registry")
    for i, s in enumerate(rows):
        s, p = _d(s), f"systematics[{i}]"
        scale_like = s.get("effect") == "migration" or s.get("kind") in ("scale", "resolution") or s.get("source") == "calibration"
        if s.get("applied_via") == "final_value" and scale_like:
            a.add("error", "systematic.scale_on_final_value", p, f"'{s.get('name')}' (scale, resolution, or migration effect) is applied to the final values only",
                  "Shift the reconstructed variable and re-run the migration, or use a nuisance or alternate sample")
        if _empty(s.get("applied_via")):
            a.add("warning", "systematic.no_representation", p, f"'{s.get('name')}' does not say how it is propagated (applied_via)")
        if _empty(s.get("correlations_across_bins")):
            a.add("warning", "systematic.no_correlations", p, f"'{s.get('name')}' has no correlation statement across bins")
        if _empty(s.get("validation")):
            a.add("warning", "systematic.no_validation", p, f"'{s.get('name')}' has no validation")
        if _empty(s.get("double_counting_checks")):
            a.add("warning", "systematic.no_double_counting_check", p, f"'{s.get('name')}' lacks double-counting checks")


def _tails(spec: dict, a: Audit) -> None:
    tails = _l(spec.get("tail_estimates"))
    for i, t in enumerate(tails):
        t, p = _d(t), f"tail_estimates[{i}]"
        if t.get("method") == "gaussian_core":
            a.add("error", "tail.gaussian_core", p, f"'{t.get('name')}' is estimated from a Gaussian core: charge confusion and rare misidentification are tail phenomena",
                  "Estimate from the tail (data-driven or MC verified on a tail-populating sample)")
        elif _empty(t.get("tail_validation")):
            a.add("error", "tail.unvalidated", p, f"'{t.get('name')}' has no tail validation")
    signs = [_d(s).get("charge_sign") for s in _l(_d(spec.get("measurement")).get("species"))]
    if any(x in (-1, "-1", "both") for x in signs) and not any(_d(t).get("process") == "charge_confusion" for t in tails):
        a.add("warning", "tail.charge_confusion_missing", "tail_estimates", "negative or both-sign species but no charge-confusion tail estimate")


def _validation(spec: dict, a: Audit) -> None:
    items = _l(spec.get("validation"))
    _validations(items, "validation", a)
    if not any(_d(v).get("kind") == "closure" for v in items):
        a.add("warning", "validation.no_closure", "validation", "no closure test declared")
    if _d(spec.get("inference")).get("method") == "unfolding" and not any(_d(v).get("kind") == "stress" for v in items):
        a.add("warning", "validation.no_stress_test", "validation", "unfolding without a stress test (distorted spectrum, prior variation)")


def _evidence(spec: dict, claims: dict | None, a: Audit) -> None:
    species = {str(_d(s).get("name", "")).lower() for s in _l(_d(spec.get("measurement")).get("species"))}
    for i, p in enumerate(_l(spec.get("parameters"))):
        p, path = _d(p), f"parameters[{i}]"
        prov = p.get("provenance")
        if prov not in PROVENANCE:
            a.add("error", "parameter.no_provenance", path, f"'{p.get('name')}' needs provenance in {sorted(PROVENANCE)}")
        elif prov == "documented":
            ids = _l(p.get("claim_ids"))
            if not ids:
                a.add("error", "parameter.undocumented", path, f"'{p.get('name')}' is labelled documented but cites no claim")
            for cid in ids:
                claim = (claims or {}).get(cid)
                if claims is not None and claim is None:
                    a.add("error", "parameter.unknown_claim", path, f"claim {cid} is not in the ledger")
                elif claim is not None:
                    if not claim.get("numeric_quotation_allowed"):
                        a.add("error", "parameter.numeric_not_allowed", path, f"claim {cid} does not allow numeric quotation")
                    cs = {x.lower() for x in _d(claim.get("scope")).get("species", [])}
                    used = {str(x).lower() for x in _l(_d(p.get("applies_to")).get("species"))} or species
                    if cs and not used <= cs:
                        a.add("warning", "parameter.scope_check", path,
                              f"claim {cid} is scoped to {sorted(cs)} but the parameter is applied to {sorted(used)}: a paper-specific choice is not a universal AMS rule")
        elif prov == "proposal":
            a.add("proposal", "parameter.proposal", path, f"[Proposal] {p.get('name')} = {p.get('value')}")
        elif prov == "unknown":
            a.add("unresolved", "parameter.unknown", path, f"[Unknown/needs input] {p.get('name')}")
    for i, c in enumerate(_l(spec.get("ams_claims"))):
        c, path = _d(c), f"ams_claims[{i}]"
        label = c.get("label")
        if label not in LABELS:
            a.add("error", "claim.label", path, f"label must be one of {sorted(LABELS)}, got {label!r}")
        elif label == "Documented":
            ids = _l(c.get("claim_ids"))
            if not ids:
                a.add("error", "claim.undocumented", path, "a [Documented] statement cites no claim ID")
            elif claims is not None:
                for cid in ids:
                    if cid not in claims:
                        a.add("error", "claim.unknown", path, f"claim {cid} is not in the ledger")
        elif label == "Proposal":
            a.add("proposal", "claim.proposal", path, f"[Proposal] {c.get('text')}")
        elif label == "Unknown/needs input":
            a.add("unresolved", "claim.unknown", path, f"[Unknown/needs input] {c.get('text')}")
    for i, text in enumerate(_l(spec.get("unresolved_inputs"))):
        a.add("unresolved", "input.unresolved", f"unresolved_inputs[{i}]", str(text))


def audit_spec(spec: dict, claims: list | dict | None = None, low_count_threshold: float = 20) -> dict:
    """Audit a parsed specification. `claims` is the parsed claims.json list (or an id->claim dict)."""
    a = Audit()
    lookup = {c["id"]: c for c in claims} if isinstance(claims, list) else claims
    if lookup is not None:  # a bare legacy ID (C31) is the short form of the namespaced one (ams02:C31)
        lookup = {**{k.split(":", 1)[1]: v for k, v in lookup.items() if ":" in k}, **lookup}
    if spec.get("spec_version") != "1":
        a.add("error", "spec.version", "spec_version", f"spec_version must be '1', got {spec.get('spec_version')!r}")
    for step in (_measurement, _observables, _selections, _backgrounds, _corrections, _response, _ratio, _systematics, _tails, _validation):
        step(spec, a)
    _inference(spec, low_count_threshold, a)
    _evidence(spec, lookup, a)
    counts = {s: sum(1 for f in a.findings if f["severity"] == s) for s in SEVERITIES}
    verdict = "blocked" if counts["error"] else ("needs work" if counts["warning"] else "acceptable with open inputs")
    order = {s: i for i, s in enumerate(SEVERITIES)}
    a.findings.sort(key=lambda f: order[f["severity"]])
    return {"verdict": verdict, "counts": counts, "findings": a.findings,
            "note": "A clean audit shows internal completeness and consistency, not that the physics is right."}


def render_markdown(report: dict, title: str = "") -> str:
    """Verdict-first draft (sections 1-4 of the review structure in modules/analysis-artifacts.md)."""
    c, f = report["counts"], report["findings"]
    why = (f"{c['error']} error(s) would give a wrong or untraceable result" if c["error"]
           else f"{c['warning']} warning(s) to close" if c["warning"] else "no errors or warnings; open inputs remain")
    out = [f"# Analysis review{': ' + title if title else ''}", "", "## Verdict", f"**{report['verdict']}**: {why}.", ""]
    for sev, head in (("error", "Defects (errors)"), ("warning", "Gaps (warnings)"), ("proposal", "Proposals"), ("unresolved", "Unresolved inputs")):
        rows = [x for x in f if x["severity"] == sev]
        out.append(f"## {head}")
        if not rows:
            out += ["None.", ""]
            continue
        for x in rows:
            line = f"- `{x['code']}` at `{x['path']}`: {x['message']}"
            out.append(line + (f" Fix: {x['remedy']}" if x["remedy"] else ""))
        out.append("")
    out += ["## What would change the verdict",
            "Closing every error moves `blocked` to `needs work`; closing warnings moves it to `acceptable with open inputs`; "
            "unresolved inputs may add new errors once supplied.", "", report["note"], ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    parser.add_argument("spec", type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--claims", type=Path, default=ROOT / "evidence" / "claims.json", help="claim ledger used to resolve claim_ids")
    group.add_argument("--no-claims", action="store_true", help="skip claim-ID resolution")
    parser.add_argument("--markdown", action="store_true", help="print a verdict-first markdown draft instead of JSON")
    parser.add_argument("--low-count-threshold", type=float, default=20.0)
    parser.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    args = parser.parse_args(argv)
    try:
        text = args.spec.read_text(encoding="utf-8")
        spec = yaml_subset.loads(text) if args.spec.suffix.lower() in (".yaml", ".yml") else json.loads(text)
        if not isinstance(spec, dict):
            raise ValueError("top level must be a JSON or YAML mapping (object)")
        claims = None if args.no_claims else json.loads(args.claims.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"verdict": "unreadable", "error": str(exc)}, indent=2))
        return 2
    report = audit_spec(spec, claims, args.low_count_threshold)
    print(render_markdown(report, _d(spec.get("measurement")).get("title", "")) if args.markdown else json.dumps(report, indent=2))
    if report["counts"]["error"] or (args.strict and report["counts"]["warning"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
