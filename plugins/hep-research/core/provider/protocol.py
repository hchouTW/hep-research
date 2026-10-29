"""Rules of the provider protocol cr-provider/1. The contract schema contracts/schemas/cr_provider.json states the same
rules; core does not read it (tests keep the two in agreement).

A request names the provider, its version, parameter points (canonical parameter names -> numbers), observables with
an axis (rigidity in GV or ekn in GeV/n) and contiguous bins, and what it wants: only "lis" (unmodulated predictions,
one per observable, in request order) and "components" (additive pieces of each prediction; only from a decomposable
provider). Providers never modulate unless the declaration carries a modulation block (contracts 3.15.0): the
force-field model, the implementation, the modulation parameters phi_<period>_gv (each in the domain; a phi_<period>_gv
in the domain needs the block) and a passing conformance result (the provider's modulated output equals the plugin's
force-field tool applied to its own isotopic LIS within a tolerance no looser than MODULATION_TOLERANCE_MAX;
tools/provider_registry.py --conformance). Without the block a phi parameter is an unknown parameter and a
top-of-atmosphere prediction is an invalid response (check_modulation); with it a point carrying two modulation
parameters would be modulated twice and is refused (invalid-request), and a prediction is top-of-atmosphere exactly
when its point carries a nonzero modulation parameter. Any other wanted item fails the request with reason
unsupported-want.

A response holds one result per point, in request order. A result is "ok" with predictions (and components) and an
evaluation record, or "failed" with a reason code and no prediction. Out of the declared domain the default is
refusal (reason out-of-domain); only with the option --allow-outside-validated-range is the point evaluated, and its
result is labelled outside-validated-range. The response status is ok (every result ok), failed (none ok, or the
request was refused) or incomplete (some ok).

Every check returns a list of problems (empty when it passes); nothing here raises on bad input.
"""
from __future__ import annotations

import copy
import math
import re

from core.provider.hashing import point_hash
from core.status import ARTIFACT_LABELS

PROTOCOL = "cr-provider/1"
WANTED_ITEMS = ("lis", "components")
AXIS_UNITS = {"rigidity": "GV", "ekn": "GeV/n"}
COMPONENT_KINDS = ("primary", "channel", "energy-basis")
RESULT_STATUSES = ("ok", "failed")
RESPONSE_STATUSES = ("ok", "failed", "incomplete")
OUTSIDE_OPTION = "--allow-outside-validated-range"
OUTSIDE_LABEL = "outside-validated-range"
USER_LABEL = "user-supplied"
FAILED_LABEL = "failed"
# reason codes of a failed request or result (free strings in the schema, a closed list here)
REASONS = ("out-of-domain", "unknown-parameter", "unregistered-provider", "provider-version-mismatch",
           "unsupported-want", "not-decomposable", "unsupported-observable", "invalid-request", "invalid-response",
           "provider-failed", "provider-timeout", "provider-error")
# keys removed before two responses are compared (PRV-2): run time and any time stamp
VOLATILE_KEYS = frozenset({"elapsed_s", "timestamp", "created", "started", "finished"})

PROVIDER_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
PARAMETER_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
ENTRYPOINT = re.compile(r"^(?!/)(?!.*(^|/)\.\.(/|$))(?!.*\\)[A-Za-z0-9_./-]+\.py$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUEST_KEYS = {"protocol", "provider", "provider_version", "theory_spec_ref", "transport", "points", "observables",
                "want", "seed"}
DECLARATION_KEYS = {"id", "entrypoint", "protocol", "version", "description", "domain", "axis_ranges", "observables",
                    "axes", "decomposable", "deterministic", "output_units", "modulation"}
DECLARATION_REQUIRED = DECLARATION_KEYS - {"version", "description", "axis_ranges", "modulation"}
# provider-side modulation (contracts 3.15.0): the declared exception to "providers never modulate"
MODULATION_PARAMETER = re.compile(r"^phi_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*_gv$")
MODULATION_MODELS = ("force-field",)
MODULATION_KEYS = {"model", "implementation", "parameters", "conformance"}
CONFORMANCE_KEYS = {"reference_point", "observables", "tolerance", "result"}
CONFORMANCE_RESULT_KEYS = {"status", "max_relative_deviation", "nodes_compared", "isotopes", "tool"}
MODULATION_TOLERANCE_MAX = 1e-3  # the conformance tolerance is no looser than this (F1's force-field agreement)
MODULATED_LEVEL = "top-of-atmosphere"


def _number(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value))


def _range_problems(where: str, value) -> list[str]:
    if not isinstance(value, dict) or set(value) != {"min", "max"} or not all(_number(value.get(k)) for k in ("min", "max")):
        return [f"{where}: a range is {{'min': number, 'max': number}}"]
    return [] if value["min"] <= value["max"] else [f"{where}: min > max"]


def check_declaration(declaration) -> list[str]:
    """Problems of one provider declaration (the 'provider' field of adapter.json or profile.json)."""
    if not isinstance(declaration, dict):
        return ["a provider declaration is an object"]
    problems = [f"missing field '{k}'" for k in sorted(DECLARATION_REQUIRED - set(declaration))]
    problems += [f"unknown field '{k}'" for k in sorted(set(declaration) - DECLARATION_KEYS)]
    if problems:
        return problems
    if not isinstance(declaration["id"], str) or not PROVIDER_ID.match(declaration["id"]):
        problems.append("id: lower-case letters, digits and '-', at most 64 characters")
    if not isinstance(declaration["entrypoint"], str) or not ENTRYPOINT.match(declaration["entrypoint"]):
        problems.append("entrypoint: a relative .py path inside the declaring folder (no '..', no leading '/')")
    if declaration["protocol"] != PROTOCOL:
        problems.append(f"protocol must be '{PROTOCOL}'")
    if "version" in declaration and not (isinstance(declaration["version"], str) and declaration["version"]):
        problems.append("version: a non-empty string")
    domain = declaration["domain"]
    if not isinstance(domain, dict):
        problems.append("domain: canonical parameter name -> {min, max}")
    else:
        for name, rng in domain.items():
            if not PARAMETER_NAME.match(name):
                problems.append(f"domain: '{name}' is not a parameter name")
            problems += _range_problems(f"domain.{name}", rng)
    axes = declaration["axes"]
    if not isinstance(axes, list) or not axes or any(a not in AXIS_UNITS for a in axes):
        problems.append(f"axes: a non-empty list of {sorted(AXIS_UNITS)}")
    for axis, rng in (declaration.get("axis_ranges") or {}).items():
        if axis not in AXIS_UNITS:
            problems.append(f"axis_ranges: unknown axis '{axis}'")
        problems += _range_problems(f"axis_ranges.{axis}", rng)
    observables = declaration["observables"]
    if not isinstance(observables, list) or not observables or not all(isinstance(o, str) and o for o in observables):
        problems.append("observables: a non-empty list of observable ids")
    for key in ("decomposable", "deterministic"):
        if not isinstance(declaration[key], bool):
            problems.append(f"{key}: true or false")
    units = declaration["output_units"]
    if not isinstance(units, dict) or not all(isinstance(v, str) for v in units.values()):
        problems.append("output_units: name -> unit string")
    if isinstance(domain, dict):
        problems += _modulation_problems(declaration.get("modulation"), domain, declaration)
    return problems


def modulation_parameters(declaration: dict) -> list[str]:
    """The declared modulation parameters (phi_<period>_gv) of a provider; [] without a modulation block."""
    block = declaration.get("modulation")
    return list(block.get("parameters") or []) if isinstance(block, dict) else []


def _modulation_problems(block, domain: dict, declaration: dict) -> list[str]:
    """The modulation block (optional): force-field only, the implementation, the parameters (each in the domain, and
    every phi_<period>_gv of the domain listed) and a passing conformance result within its tolerance."""
    in_domain = sorted(n for n in domain if MODULATION_PARAMETER.match(n))
    if block is None:
        return [f"domain: {in_domain} are modulation parameters; a provider that modulates declares a modulation "
                "block (providers never modulate otherwise)"] if in_domain else []
    if not isinstance(block, dict):
        return ["modulation: an object"]
    problems = [f"modulation: missing field '{k}'" for k in sorted(MODULATION_KEYS - set(block))]
    problems += [f"modulation: unknown field '{k}'" for k in sorted(set(block) - MODULATION_KEYS)]
    if problems:
        return problems
    if block["model"] not in MODULATION_MODELS:
        problems.append(f"modulation.model must be one of {list(MODULATION_MODELS)}")
    if not isinstance(block["implementation"], str) or not block["implementation"].strip():
        problems.append("modulation.implementation: a non-empty string naming the code that modulates")
    params = block["parameters"]
    if not isinstance(params, list) or not params or not all(isinstance(p, str) for p in params) \
            or len(set(params)) != len(params):
        problems.append("modulation.parameters: a non-empty list of distinct phi_<period>_gv names")
        params = []
    for name in params:
        if not MODULATION_PARAMETER.match(name):
            problems.append(f"modulation.parameters: '{name}' is not a phi_<period>_gv name")
        elif name not in domain:
            problems.append(f"modulation.parameters: '{name}' is not in the declared domain")
    unlisted = [n for n in in_domain if n not in params]
    if unlisted:
        problems.append(f"domain: modulation parameters {unlisted} are not listed in modulation.parameters")
    return problems + _conformance_problems(block["conformance"], params, domain, declaration)


def _conformance_problems(conf, params: list, domain: dict, declaration: dict) -> list[str]:
    where = "modulation.conformance"
    if not isinstance(conf, dict):
        return [f"{where}: an object (a provider declares modulation only after the conformance gate passes)"]
    problems = [f"{where}: missing field '{k}'" for k in sorted(CONFORMANCE_KEYS - set(conf))]
    problems += [f"{where}: unknown field '{k}'" for k in sorted(set(conf) - CONFORMANCE_KEYS)]
    if problems:
        return problems
    point = conf["reference_point"]
    if not isinstance(point, dict) or not all(isinstance(k, str) and _number(v) for k, v in point.items()):
        problems.append(f"{where}.reference_point: canonical parameter name -> finite number")
    else:
        used = [n for n in params if point.get(n)]
        if len(used) != 1:
            problems.append(f"{where}.reference_point: exactly one modulation parameter {params} with a nonzero value")
        problems += [f"{where}.reference_point: '{n}' is not in the declared domain" for n in sorted(point)
                     if n not in domain]
        problems += [f"{where}.reference_point: {n}={point[n]!r} is outside the declared domain" for n in sorted(point)
                     if n in domain and not _range_problems(n, domain[n])
                     and not domain[n]["min"] <= point[n] <= domain[n]["max"]]
    observables = conf["observables"]
    if not isinstance(observables, list) or not observables:
        problems.append(f"{where}.observables: a non-empty list of observable requests (id, axis, unit, bins)")
    else:
        for i, obs in enumerate(observables):
            if not isinstance(obs, dict) or set(obs) != {"id", "axis", "unit", "bins"} \
                    or obs["id"] not in (declaration.get("observables") or []) \
                    or obs["axis"] not in AXIS_UNITS or obs["unit"] != AXIS_UNITS[obs["axis"]] \
                    or bin_edges(obs["bins"]) is None:
                problems.append(f"{where}.observables[{i}]: a declared observable with id, axis, unit and "
                                "increasing contiguous bins")
    tol = conf["tolerance"]
    if not _number(tol) or not 0 < tol <= MODULATION_TOLERANCE_MAX:
        problems.append(f"{where}.tolerance: a relative tolerance in (0, {MODULATION_TOLERANCE_MAX:g}]")
        tol = None
    result = conf["result"]
    if not isinstance(result, dict) or set(result) != CONFORMANCE_RESULT_KEYS:
        return problems + [f"{where}.result: exactly {sorted(CONFORMANCE_RESULT_KEYS)}"]
    if result["status"] != "passed":
        problems.append(f"{where}.result.status must be 'passed': a provider without a passing conformance result "
                        "does not modulate")
    dev = result["max_relative_deviation"]
    if not _number(dev) or dev < 0:
        problems.append(f"{where}.result.max_relative_deviation: a number >= 0")
    elif tol is not None and dev > tol:
        problems.append(f"{where}.result.max_relative_deviation {dev:g} exceeds the tolerance {tol:g}")
    nodes = result["nodes_compared"]
    if isinstance(nodes, bool) or not isinstance(nodes, int) or nodes < 1:
        problems.append(f"{where}.result.nodes_compared: an integer >= 1")
    isotopes = result["isotopes"]
    if not isinstance(isotopes, list) or not isotopes or not all(isinstance(x, str) and x for x in isotopes):
        problems.append(f"{where}.result.isotopes: a non-empty list of nuclide names")
    if not isinstance(result["tool"], str) or not result["tool"]:
        problems.append(f"{where}.result.tool: the force-field tool the provider was compared with")
    return problems


def declarations_of(field) -> list:
    """The declarations of a 'provider' field: one object or a list of them."""
    return list(field) if isinstance(field, list) else [field]


def bin_edges(bins) -> list[float] | None:
    """Edges of increasing contiguous bins [[lo, hi], ...], or None when the bins are not of that form."""
    if not isinstance(bins, list) or not bins:
        return None
    edges: list[float] = []
    for pair in bins:
        if not isinstance(pair, list) or len(pair) != 2 or not all(_number(x) for x in pair):
            return None
        low, high = float(pair[0]), float(pair[1])
        if not high > low or (edges and low != edges[-1]):
            return None
        if not edges:
            edges.append(low)
        edges.append(high)
    return edges


def check_request(request) -> list[str]:
    """Structural problems of a request (the reason invalid-request). Wanted items outside lis/components are not a
    structural problem: they fail the request with unsupported-want (request_refusal)."""
    if not isinstance(request, dict):
        return ["a request is a JSON object"]
    problems = [f"missing field '{k}'" for k in ("protocol", "provider", "provider_version", "points",
                                                  "observables", "want") if k not in request]
    problems += [f"unknown field '{k}'" for k in sorted(set(request) - REQUEST_KEYS)]
    if problems:
        return problems
    if request["protocol"] != PROTOCOL:
        problems.append(f"protocol must be '{PROTOCOL}'")
    if not isinstance(request["provider"], str) or not PROVIDER_ID.match(request["provider"]):
        problems.append("provider: a provider id")
    if not isinstance(request["provider_version"], str) or not request["provider_version"]:
        problems.append("provider_version: a non-empty string")
    if "theory_spec_ref" in request and not isinstance(request["theory_spec_ref"], str):
        problems.append("theory_spec_ref: a string")
    if request.get("transport") is not None and not isinstance(request["transport"], dict):
        problems.append("transport: an object or null")
    seed = request.get("seed")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        problems.append("seed: an integer or null")
    points = request["points"]
    if not isinstance(points, list) or not points:
        problems.append("points: a non-empty list")
    else:
        for i, point in enumerate(points):
            if not isinstance(point, dict):
                problems.append(f"points[{i}]: an object")
                continue
            for name, value in point.items():
                if not PARAMETER_NAME.match(name):
                    problems.append(f"points[{i}]: '{name}' is not a parameter name")
                if not _number(value):
                    problems.append(f"points[{i}].{name}: a finite number")
    observables = request["observables"]
    if not isinstance(observables, list) or not observables:
        problems.append("observables: a non-empty list")
    else:
        for i, obs in enumerate(observables):
            if not isinstance(obs, dict) or set(obs) != {"id", "axis", "unit", "bins"}:
                problems.append(f"observables[{i}]: exactly id, axis, unit and bins")
                continue
            if not isinstance(obs["id"], str) or not obs["id"]:
                problems.append(f"observables[{i}].id: a non-empty string")
            if obs["axis"] not in AXIS_UNITS:
                problems.append(f"observables[{i}].axis: one of {sorted(AXIS_UNITS)}")
            elif obs["unit"] != AXIS_UNITS[obs["axis"]]:
                problems.append(f"observables[{i}].unit: '{AXIS_UNITS[obs['axis']]}' for axis {obs['axis']}")
            if bin_edges(obs["bins"]) is None:
                problems.append(f"observables[{i}].bins: [[low, high], ...], increasing and contiguous")
    want = request["want"]
    if not isinstance(want, list) or not want or not all(isinstance(w, str) for w in want):
        problems.append("want: a non-empty list of strings")
    elif len(set(want)) != len(want):
        problems.append("want: an item is listed twice")
    return problems


def request_refusal(request: dict, declaration: dict, allow_outside: bool = False):
    """(reason, detail, outside) for a structurally valid request this provider cannot answer, or (None, '', outside).
    outside is True when the bins leave the declared axis ranges and allow_outside lets them through."""
    extra = [w for w in request["want"] if w not in WANTED_ITEMS]
    if extra:
        return "unsupported-want", f"want accepts only {list(WANTED_ITEMS)}; got {extra} (providers never modulate)", False
    if "components" in request["want"] and not declaration["decomposable"]:
        return "not-decomposable", f"provider {declaration['id']} declares decomposable: false", False
    outside = False
    for obs in request["observables"]:
        if obs["id"] not in declaration["observables"]:
            return "unsupported-observable", f"{obs['id']!r} is not among {declaration['observables']}", False
        if obs["axis"] not in declaration["axes"]:
            return "unsupported-observable", f"axis {obs['axis']!r} is not among {declaration['axes']}", False
        rng = (declaration.get("axis_ranges") or {}).get(obs["axis"])
        edges = bin_edges(obs["bins"]) or []
        if rng and edges and (edges[0] < rng["min"] or edges[-1] > rng["max"]):
            if not allow_outside:
                return ("out-of-domain", f"{obs['id']} bins [{edges[0]:g}, {edges[-1]:g}] {obs['unit']} leave the "
                        f"declared {obs['axis']} range [{rng['min']:g}, {rng['max']:g}]", False)
            outside = True
    return None, "", outside


def point_refusal(point: dict, declaration: dict, allow_outside: bool = False):
    """(reason, detail, outside) for one point: unknown-parameter for a name outside the declared domain,
    invalid-request for two modulation parameters (the prediction would be modulated twice), out-of-domain for a
    value outside its range (unless allow_outside), else (None, '', outside)."""
    domain = declaration["domain"]
    unknown = sorted(set(point) - set(domain))
    if unknown:
        return "unknown-parameter", f"parameters {unknown} are not in the declared domain {sorted(domain)}", False
    twice = sorted(set(point) & set(modulation_parameters(declaration)))
    if len(twice) > 1:
        return ("invalid-request", f"the point carries the modulation parameters {twice}: one prediction is modulated "
                "once, at the potential of one period", False)
    beyond = [f"{name}={point[name]!r} not in [{domain[name]['min']!r}, {domain[name]['max']!r}]"
              for name in sorted(point) if not domain[name]["min"] <= point[name] <= domain[name]["max"]]
    if beyond and not allow_outside:
        return "out-of-domain", "; ".join(beyond), False
    return None, "", bool(beyond)


def failed_result(index: int, point: dict, reason: str, detail: str = "", labels=()) -> dict:
    out = {"point_index": index, "point": dict(point), "status": "failed", "reason": reason,
           "labels": sorted(set(labels) | {FAILED_LABEL})}
    if detail:
        out["detail"] = detail
    return out


def response_status(results: list[dict]) -> str:
    ok = sum(r.get("status") == "ok" for r in results)
    return "ok" if results and ok == len(results) else ("failed" if ok == 0 else "incomplete")


def failed_response(request, reason: str, detail: str = "") -> dict:
    """A refused request: status failed, the reason, no result."""
    req = request if isinstance(request, dict) else {}
    out = {"protocol": PROTOCOL, "provider": str(req.get("provider", "")),
           "provider_version": str(req.get("provider_version", "")), "status": "failed", "reason": reason,
           "results": []}
    if detail:
        out["detail"] = detail
    return out


def check_response(response, request: dict) -> list[str]:
    """Problems of a provider response to `request` (a valid request): structure, one result per point in order, the
    points echoed, a reason and no prediction on failure, an evaluation record with the point hash, one numerical
    prediction per observable whose edges and value counts match the bins, components when wanted."""
    if not isinstance(response, dict):
        return ["a response is a JSON object"]
    problems = []
    for key in ("protocol", "provider", "provider_version", "status", "results"):
        if key not in response:
            problems.append(f"missing field '{key}'")
    if problems:
        return problems
    problems += [f"unknown field '{k}'" for k in sorted(set(response) - {"protocol", "provider", "provider_version",
                                                                          "status", "reason", "detail", "results"})]
    if response["protocol"] != PROTOCOL:
        problems.append(f"protocol must be '{PROTOCOL}'")
    if response["status"] not in RESPONSE_STATUSES:
        problems.append(f"status must be one of {list(RESPONSE_STATUSES)}")
    results = response["results"]
    if not isinstance(results, list):
        return problems + ["results: a list"]
    if response.get("reason") is not None and response["reason"] not in REASONS:
        problems.append(f"reason {response['reason']!r} is not a protocol reason")
    if not results:
        if response["status"] != "failed" or not response.get("reason"):
            problems.append("a response without results is a refused request: status failed with a reason")
        return problems
    if response["provider"] != request["provider"] or response["provider_version"] != request["provider_version"]:
        problems.append("provider and provider_version must echo the request")
    if len(results) != len(request["points"]):
        return problems + [f"{len(results)} results for {len(request['points'])} points"]
    if response["status"] != response_status(results):
        problems.append(f"status {response['status']!r} does not match the results ({response_status(results)!r})")
    edges = [bin_edges(o["bins"]) for o in request["observables"]]
    want = set(request["want"])
    for i, (res, point) in enumerate(zip(results, request["points"])):
        where = f"results[{i}]"
        if not isinstance(res, dict):
            problems.append(f"{where}: an object")
            continue
        problems += [f"{where}: unknown field '{k}'" for k in sorted(set(res) - {
            "point_index", "point", "status", "reason", "detail", "labels", "predictions", "components", "evaluation"})]
        if res.get("point_index") != i:
            problems.append(f"{where}.point_index must be {i}")
        if res.get("point") != point:
            problems.append(f"{where}.point must echo the request's point")
        labels = res.get("labels")
        if not isinstance(labels, list) or any(x not in ARTIFACT_LABELS for x in labels):
            problems.append(f"{where}.labels: artifact status labels")
            labels = []
        if res.get("status") == "failed":
            if res.get("reason") not in REASONS:
                problems.append(f"{where}: a failed result has a protocol reason")
            if "predictions" in res or "components" in res:
                problems.append(f"{where}: a failed result carries no prediction")
            if FAILED_LABEL not in labels:
                problems.append(f"{where}: a failed result is labelled failed")
            continue
        if res.get("status") != "ok":
            problems.append(f"{where}.status must be ok or failed")
            continue
        if FAILED_LABEL in labels:
            problems.append(f"{where}: an ok result is not labelled failed")
        problems += _evaluation_problems(where, res.get("evaluation"), request, point)
        if "lis" in want:
            problems += _prediction_problems(where, res.get("predictions"), request["observables"], edges)
        elif "predictions" in res:
            problems.append(f"{where}: predictions were not wanted")
        if "components" in want:
            problems += _component_problems(where, res.get("components"), request["observables"], edges)
        elif "components" in res:
            problems.append(f"{where}: components were not wanted")
    return problems


def check_modulation(result: dict, declaration: dict) -> list[str]:
    """Problems of one ok result against the declared modulation (contracts 3.15.0): a top-of-atmosphere prediction
    from a provider without a modulation block; with the block, a top-of-atmosphere prediction for a point without a
    nonzero modulation parameter, or a prediction of another level for a point with one (the provider ignored it)."""
    if not isinstance(result, dict) or result.get("status") != "ok":
        return []
    params = modulation_parameters(declaration)
    point = result.get("point")
    if not isinstance(point, dict):
        point = {}
    modulated = any(point.get(n) for n in params)
    problems = []
    for k, pred in enumerate(result.get("predictions") or []):
        obs = pred.get("observable") if isinstance(pred, dict) else None
        level = obs.get("level") if isinstance(obs, dict) else None
        where = f"predictions[{k}]"
        if level == MODULATED_LEVEL and not params:
            problems.append(f"{where}: a {MODULATED_LEVEL} prediction from provider {declaration.get('id')!r}, whose "
                            "declaration has no modulation block (providers never modulate otherwise)")
        elif level == MODULATED_LEVEL and not modulated:
            problems.append(f"{where}: a {MODULATED_LEVEL} prediction for a point without a modulation parameter "
                            f"{params}")
        elif modulated and level != MODULATED_LEVEL:
            problems.append(f"{where}: level {level!r} for a point carrying a modulation parameter {params}: the "
                            f"declared modulation gives {MODULATED_LEVEL} values")
    return problems


def _evaluation_problems(where: str, evaluation, request: dict, point: dict) -> list[str]:
    if not isinstance(evaluation, dict) or set(evaluation) != {"computational_run_ref", "input_hash", "elapsed_s",
                                                               "numerical_tolerance"}:
        return [f"{where}.evaluation: computational_run_ref, input_hash, elapsed_s and numerical_tolerance"]
    problems = []
    if evaluation["computational_run_ref"] is not None and not isinstance(evaluation["computational_run_ref"], str):
        problems.append(f"{where}.evaluation.computational_run_ref: a string or null")
    if not _number(evaluation["elapsed_s"]) or evaluation["elapsed_s"] < 0:
        problems.append(f"{where}.evaluation.elapsed_s: a number >= 0")
    tol = evaluation["numerical_tolerance"]
    if tol is not None and (not _number(tol) or tol < 0):
        problems.append(f"{where}.evaluation.numerical_tolerance: a number >= 0 or null")
    expected = point_hash(request.get("transport"), request["provider"], request["provider_version"], point)
    if evaluation["input_hash"] != expected:
        problems.append(f"{where}.evaluation.input_hash is not the point hash {expected}")
    return problems


def _prediction_problems(where: str, predictions, observables: list, edges: list) -> list[str]:
    if not isinstance(predictions, list) or len(predictions) != len(observables):
        return [f"{where}.predictions: one per observable, in request order"]
    problems = []
    for k, (pred, want_edges) in enumerate(zip(predictions, edges)):
        pw = f"{where}.predictions[{k}]"
        if not isinstance(pred, dict):
            problems.append(f"{pw}: an object")
            continue
        for key in ("observable", "parameter_point", "representation", "values", "uncertainties",
                    "allowed_transformations"):
            if key not in pred:
                problems.append(f"{pw}: missing field '{key}'")
        if pred.get("representation") != "numerical":
            problems.append(f"{pw}.representation must be numerical")
        values = pred.get("values")
        if not isinstance(values, dict) or values.get("edges") != want_edges:
            problems.append(f"{pw}.values.edges must equal the requested bin edges")
        elif not isinstance(values.get("values"), list) or len(values["values"]) != len(want_edges) - 1 \
                or not all(_number(v) for v in values["values"]):
            problems.append(f"{pw}.values.values: one finite number per bin")
    return problems


def _component_problems(where: str, components, observables: list, edges: list) -> list[str]:
    if not isinstance(components, list) or not components:
        return [f"{where}.components: wanted but missing"]
    nbins = {o["id"]: len(e) - 1 for o, e in zip(observables, edges)}
    problems = []
    for k, comp in enumerate(components):
        cw = f"{where}.components[{k}]"
        if not isinstance(comp, dict) or not {"observable", "id", "kind", "values", "unit"} <= set(comp):
            problems.append(f"{cw}: observable, id, kind, values and unit")
            continue
        if comp["observable"] not in nbins:
            problems.append(f"{cw}.observable: not a requested observable")
        elif not isinstance(comp["values"], list) or len(comp["values"]) != nbins[comp["observable"]] \
                or not all(_number(v) for v in comp["values"]):
            problems.append(f"{cw}.values: one finite number per bin")
        if comp["kind"] not in COMPONENT_KINDS:
            problems.append(f"{cw}.kind: one of {list(COMPONENT_KINDS)}")
    return problems


def strip_volatile(value):
    """A copy without run times and time stamps (VOLATILE_KEYS), for the PRV-2 comparison."""
    if isinstance(value, dict):
        return {k: strip_volatile(v) for k, v in value.items() if k not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [strip_volatile(v) for v in value]
    return copy.deepcopy(value)
