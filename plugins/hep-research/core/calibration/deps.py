"""Dependencies between calibration results (Part B sections 5.2 clause 5, 10.2, 10.3, 10.4; owner calib_deps.py).

Phase 0 content (section 17): hash references, cycle checks, derivation of upstream roles from usage, and the
acyclic computation of version ids; phase 2: the conflict rules of section 10.4; phase 4: upstream invalidation and the
change of simulation identity (section 10.3) with the T2 carry-over of approval A21 (section 19-g7). Standard library
only.

Roles are derived, never declared (section 10.2): any central usage makes the upstream `central`; only variation sets
or envelopes make it `variation`; no usage is rejected. A role written in the contract must equal the derived one.
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from statistics import NormalDist

from core.calibration import model_identity
from core.calibration.data_release import kappa_id
from core.canonical import canonical_sha256

# Section 5.2 clause 5: the usages an upstream reference can declare, and the role each implies (section 10.2).
CENTRAL_USAGES = frozenset({"phi-center", "nuisance-posterior", "xi", "fixed-value"})
VARIATION_USAGES = frozenset({"variation-set", "envelope"})
USAGES = CENTRAL_USAGES | VARIATION_USAGES
ROLES = ("central", "variation")

SHA256 = re.compile(r"^[0-9a-f]{64}$")


class DependencyError(ValueError):
    """A dependency the workflow rejects; `code` is a stable name, `path` locates it."""

    def __init__(self, code: str, message: str, path: str = "$"):
        super().__init__(message)
        self.code, self.path = code, path


def derive_role(usages) -> str:
    """Role of an upstream from its usages (Appendix C.3 "Role"). Raises ValueError on no or unknown usage."""
    usages = set(usages)
    if not usages:
        raise ValueError("upstream reference without usage")
    unknown = usages - USAGES
    if unknown:
        raise ValueError(f"unknown usage {sorted(unknown)}")
    return "central" if usages & CENTRAL_USAGES else "variation"


def is_hash_reference(value) -> bool:
    """A result is cited by its SHA-256 (lower-case hex), never by numbers or a name (section 15.3.17)."""
    return isinstance(value, str) and bool(SHA256.match(value))


def check_upstream_entries(entries) -> list[dict]:
    """Section 5.2 clause 5 for a contract's upstream[]: each entry cites a result by hash and lists its usages; a
    written role must equal the derived one. Returns findings (code, path, message); empty means accepted."""
    out: list[dict] = []
    if not isinstance(entries, list):
        return [{"code": "upstream.not_list", "path": "$.upstream", "message": "upstream must be a list"}]
    seen: set[str] = set()
    for i, e in enumerate(entries):
        p = f"$.upstream[{i}]"
        if not isinstance(e, dict):
            out.append({"code": "upstream.not_object", "path": p, "message": "an upstream entry is an object"})
            continue
        ref = e.get("result_sha256")
        if not is_hash_reference(ref):
            out.append({"code": "upstream.not_hash", "path": f"{p}.result_sha256",
                        "message": "an upstream result is cited by its SHA-256, not by numbers or a name"})
        elif ref in seen:
            out.append({"code": "upstream.duplicate", "path": f"{p}.result_sha256",
                        "message": "the same upstream result is listed twice; list all its usages in one entry"})
        else:
            seen.add(str(ref))                  # a hash reference: a string
        try:
            role = derive_role(e.get("usages") or [])
        except ValueError as exc:
            out.append({"code": "upstream.usage", "path": f"{p}.usages", "message": str(exc)})
            continue
        if "role" in e and e["role"] != role:
            out.append({"code": "upstream.role_mismatch", "path": f"{p}.role",
                        "message": f"role written as {e['role']!r} but the usages {sorted(e['usages'])} make it "
                                   f"{role!r}; roles are derived from usage (section 10.2)"})
    return out


def find_cycle(graph: dict) -> list[str] | None:
    """A cycle in a result dependency graph {result: [upstream results]}, as a list of results closing on its first
    element, or None. Section 10.3: cycles are rejected and must be merged into one joint fit."""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {n: WHITE for n in graph}
    for ups in graph.values():
        for u in ups:
            colour.setdefault(u, WHITE)
    for start in sorted(colour):
        if colour[start] != WHITE:
            continue
        stack = [(start, iter(sorted(graph.get(start, ()))))]
        path = [start]
        colour[start] = GREY
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                colour[node] = BLACK
                stack.pop()
                path.pop()
            elif colour[nxt] == GREY:
                return path[path.index(nxt):] + [nxt]
            elif colour[nxt] == WHITE:
                colour[nxt] = GREY
                stack.append((nxt, iter(sorted(graph.get(nxt, ())))))
                path.append(nxt)
    return None


def check_acyclic(graph: dict) -> None:
    cyc = find_cycle(graph)
    if cyc:
        raise DependencyError("deps.cycle", "circular dependency " + " -> ".join(cyc)
                              + "; merge the cycle into one joint fit (section 10.3)")


def central_closure(result: str, upstreams: dict) -> set[str]:
    """Every result in the `central` dependency closure of `result` (section 10.4, version lineage): its central
    upstreams taken recursively. upstreams maps a result to its upstream[] entries ({result_sha256, usages})."""
    out: set[str] = set()
    todo = [result]
    while todo:
        r = todo.pop()
        for e in upstreams.get(r, ()):
            u = e["result_sha256"]
            if derive_role(e["usages"]) == "central" and u not in out:
                out.add(u)
                todo.append(u)
    return out


# ------------------------------------------------------------------ versions (section 10.4, acyclic ids)
# Fields that are the version's own id, the final result hash, or back-filled from them: never inside update_digest.
BACKFILLED = frozenset({"version_id", "result_sha256", "result_hash"})


def _strip_backfilled(payload: dict) -> dict:
    """The payload without its own top-level id and result-hash fields; nested values are content and stay."""
    return {k: v for k, v in payload.items() if k not in BACKFILLED}


def update_digest(payload: dict) -> str:
    """update_digest = hash(contract, data and plan hashes, engine version, parent versions, fit and export values),
    excluding its own id, the final result hash and fields back-filled from them (section 10.4)."""
    required = ("contract_sha256", "data_sha256", "plan_sha256", "engine_version", "parent_versions", "values")
    missing = [k for k in required if k not in payload]
    if missing:
        raise DependencyError("version.payload_incomplete", f"version payload lacks {missing}")
    for i, p in enumerate(payload["parent_versions"]):
        if not is_hash_reference(p):
            raise DependencyError("version.parent_not_hash", "a parent version is cited by its id (SHA-256)",
                                  f"$.parent_versions[{i}]")
    body = _strip_backfilled(payload)
    body["parent_versions"] = sorted(set(payload["parent_versions"]))   # the order of listing is not content
    return canonical_sha256(body)


def version_id(payload: dict) -> str:
    """version id = hash(normalized list of parent version ids, update_digest). Normalized: sorted, without
    duplicates, so the order in which parents are listed does not change the id."""
    return canonical_sha256({"parents": sorted(set(payload["parent_versions"])),
                             "update_digest": update_digest(payload)})


def finalize_result(result: dict, payload: dict) -> dict:
    """Write the version id into the result, then compute the result hash over the result with the id (and without
    a result hash field). Returns a new dict with version_id and result_sha256. The id never depends on the hash."""
    out = {k: v for k, v in result.items() if k not in ("result_sha256", "result_hash")}
    out["version_id"] = version_id(payload)
    out["result_sha256"] = canonical_sha256({k: v for k, v in out.items() if k != "result_sha256"})
    return out


def rebuild_order(versions: dict) -> list[str]:
    """Rebuild versions in acyclic order: versions maps an id to its payload. Each id is recomputed from its payload
    after its parents (a parent outside the set is taken as given). Raises on a cycle among parents or an id that
    does not recompute (section 15.3a: versions and result hashes can be rebuilt in acyclic order)."""
    graph = {v: [p for p in pl["parent_versions"] if p in versions] for v, pl in versions.items()}
    check_acyclic(graph)
    done: list[str] = []
    placed: set[str] = set()
    while len(done) < len(versions):
        ready = sorted(v for v in versions if v not in placed and all(p in placed for p in graph[v]))
        for v in ready:
            got = version_id(versions[v])
            if got != v:
                raise DependencyError("version.not_reproducible", f"version {v[:12]} recomputes to {got[:12]}")
            done.append(v)
            placed.add(v)
    return done


# ------------------------------------------------------------------ conflict rules over packages (section 10.4, 15.3a)
def source_set(uncertainty: dict, upstreams: dict) -> set:
    """The source set of an uncertainty object: xi of result U is {U} union the central closure of U; a shared nuisance
    version has its lineage (the updater and its central closure)."""
    if uncertainty["kind"] == "xi":
        return {uncertainty["result"]} | central_closure(uncertainty["result"], upstreams)
    if uncertainty["kind"] == "zeta":
        return {uncertainty["updater"]} | central_closure(uncertainty["updater"], upstreams)
    raise DependencyError("deps.object", f"unknown uncertainty object kind {uncertainty['kind']!r}", "kind")


def check_packages(packages: list, upstreams: dict, common_sources: dict | None = None) -> list:
    """The decision of section 10.4: first the atomic packages (xi_U with its matching joint zeta version of the same
    upstream), then the dependencies between packages. Findings:
    - `deps.package_split`: a package whose zeta is not the version exported with its xi (the decomposition must stay
      intact);
    - `deps.version_conflict`: two packages constraining the same nuisance key with different versions (joint fit);
    - `deps.source_overlap`: intersecting source sets of different packages (sibling, triangle, xi and xi,
      parent-child) unless an explicit joint factor covers them;
    - `deps.common_source`: disjoint source sets but a shared raw-data lineage, MC sample, external measurement,
      shared prior or efficiency-map basis (`common_sources` = {package id: set of keys}); disjointness is not proof;
    - `deps.theta_nu_split`: theta and nu of one upstream exported separately;
    - `deps.xi_version`: a package citing a version of xi: xi has no versions (A21, section 19-g8); a downstream that
      pulls an upstream xi is handled by the conflict rule (a joint fit), see forced_joint_fits().
    A package: {id, upstream, zeta: {key: version}, exported_zeta: {key: version}, zeta_updaters?, joint_factor?,
    exports?}. The same key and version create one variable and one constraint only."""
    out = []
    for p in packages:
        if p.get("xi_version") is not None:
            out.append({"code": "deps.xi_version", "package": p["id"]})
        if p.get("exports") and {"theta", "nu"} <= set(p["exports"]):
            out.append({"code": "deps.theta_nu_split", "package": p["id"]})
        if p.get("exported_zeta") is not None and p.get("zeta") is not None:
            for k, v in p["zeta"].items():
                if k in p["exported_zeta"] and p["exported_zeta"][k] != v:
                    out.append({"code": "deps.package_split", "package": p["id"], "key": k})
    by_key: dict = {}
    for p in packages:
        for k, v in (p.get("zeta") or {}).items():
            by_key.setdefault(k, set()).add(v)
    for k, vs in by_key.items():
        if len(vs) > 1:
            out.append({"code": "deps.version_conflict", "key": k, "versions": sorted(vs)})
    sets = {}
    for p in packages:
        s = source_set({"kind": "xi", "result": p["upstream"]}, upstreams)
        for v in (p.get("zeta_updaters") or {}).values():
            s |= source_set({"kind": "zeta", "updater": v}, upstreams)
        sets[p["id"]] = s
    ids = [p["id"] for p in packages]
    joint = {frozenset(p.get("joint_factor") or ()) for p in packages}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            if any({a, b} <= set(jf) for jf in joint):
                continue
            inter = sets[a] & sets[b]
            if inter:
                out.append({"code": "deps.source_overlap", "packages": [a, b], "sources": sorted(inter)})
            elif common_sources and (common_sources.get(a, set()) & common_sources.get(b, set())):
                out.append({"code": "deps.common_source", "packages": [a, b],
                            "sources": sorted(common_sources[a] & common_sources[b])})
    return out


# ------------------------------------------------------------------ upstream invalidation (section 10.3)
GRADE_RANK = {"incomplete": -1, "failed": 0, "projection": 1, "calibrated-unvalidated": 2, "validated-in-scope": 3}


def _result_hash(r, where: str) -> str:
    if not isinstance(r, dict) or not is_hash_reference(r.get("result_sha256")):
        raise DependencyError("invalidate.result_hash", "a result is identified by its result_sha256", where)
    return r["result_sha256"]


def kappa(r: dict) -> str:
    """kappa of a result (section 9.5): its `kappa` field, else the hash of (contract hash, plan hash, engine version)
    (core.calibration.data_release.kappa_id)."""
    if r.get("kappa"):
        return r["kappa"]
    parts = [r.get(k) for k in ("contract_sha256", "plan_sha256", "engine_version")]
    if not all(isinstance(x, str) and x for x in parts):
        raise DependencyError("invalidate.kappa", "a result states kappa or its contract, plan hashes and engine "
                              "version", "$.kappa")
    return kappa_id(str(parts[0]), str(parts[1]), str(parts[2]))


def _standing(r: dict) -> tuple:
    g = r.get("grade") or {}
    return g.get("effective_grade"), frozenset(g.get("uses") or ())


def upstream_change(old, successor) -> dict:
    """Classify the successor `new` of an upstream result `old` (section 10.3): `rejudgment` when the same kappa is
    re-judged after the records it waited for are resolved (old had pending inputs: no own grade, waiting records)
    and the (effective grade, use) is unchanged, which is not an upstream revision; otherwise `downgrade` when the
    effective grade falls or uses are lost, else `revision`; `none` for the same result."""
    a, b = _result_hash(old, "$.old"), _result_hash(successor, "$.new")
    out = {"old": a, "new": b, "kappa_old": kappa(old), "kappa_new": kappa(successor)}
    if a == b:
        return dict(out, kind="none")
    (ga, ua), (gb, ub) = _standing(old), _standing(successor)
    if ga not in GRADE_RANK or gb not in GRADE_RANK:
        raise DependencyError("invalidate.grade", "each result states grade.effective_grade", "$.grade")
    pending = (old.get("grade") or {}).get("own_grade") is None and bool(old.get("waiting_records"))
    if out["kappa_old"] == out["kappa_new"] and pending and (gb, ub) == (ga, ua):
        return dict(out, kind="rejudgment")
    return dict(out, kind="downgrade" if GRADE_RANK[gb] < GRADE_RANK[ga] or not ua <= ub else "revision")


def invalidate(downstreams: list, changes: list, marked=()) -> dict:
    """Section 10.3: a downstream citing (upstream[]) a revised or downgraded upstream is marked as needing a redo; a
    re-judgment of the same kappa is not a revision and is recorded as earlier and later decisions of that kappa;
    `marked` (e.g. results whose simulation identity changed, `identity_decision`) are marked too. A result citing a
    result marked for a redo is marked in turn (its upstream will be revised). changes: [{old, new}] result documents.
    Returns {redo: {result: [reasons]}, same_kappa: [{downstream, kappa, earlier, later}], changes: [...]}."""
    classified = {}
    for i, c in enumerate(changes):
        if not isinstance(c, dict):
            raise DependencyError("invalidate.change", "a change is {old, new}", f"$.changes[{i}]")
        change = upstream_change(c.get("old"), c.get("new"))
        classified[change["old"]] = change
    ups = {}
    for i, r in enumerate(downstreams):
        h = _result_hash(r, f"$.results[{i}]")
        entries = r.get("upstream") or []
        if check_upstream_entries(entries):
            raise DependencyError("invalidate.upstream", "the upstream[] entries are not valid (calib_deps.py roles)",
                                  f"$.results[{i}].upstream")
        ups[h] = entries
    redo: dict[str, list] = {}
    same: list = []
    for m in marked:
        if not is_hash_reference(m):
            raise DependencyError("invalidate.marked", "a marked result is cited by its SHA-256", "$.marked")
        redo.setdefault(m, []).append({"code": "marked"})
    for h, entries in sorted(ups.items()):
        for e in entries:
            ch = classified.get(e["result_sha256"])
            if ch is None or ch["kind"] == "none":
                continue
            if ch["kind"] == "rejudgment":
                same.append({"downstream": h, "kappa": ch["kappa_old"], "earlier": ch["old"], "later": ch["new"]})
            else:
                redo.setdefault(h, []).append({"code": f"upstream.{ch['kind']}", "upstream": ch["old"],
                                               "successor": ch["new"], "role": derive_role(e["usages"])})
    grown = True
    while grown:
        grown = False
        for h, entries in sorted(ups.items()):
            hit = sorted(e["result_sha256"] for e in entries if e["result_sha256"] in redo)
            if hit and h not in redo:
                redo[h] = [{"code": "upstream.needs_redo", "upstream": u} for u in hit]
                grown = True
    return {"redo": dict(sorted(redo.items())), "same_kappa": same,
            "changes": [classified[k] for k in sorted(classified)]}


# ------------------------------------------------------------------ change of simulation identity (10.3, A21 19-g7)
CARRIED_OVER = "identity-carried-over"
PROVISIONAL = "provisional-thresholds"
T2_MARGIN = 0.1            # x sigma_tot^design per observable: provisional threshold of A21 (section 19-g7)
T2_ALPHA = 0.05            # TOST level per observable; all must pass (intersection-union test)
T2_SCHEMA = "calibration-identity-equivalence/1"
THETA_HAT = "theta-hat"


def _identities(value, where: str) -> dict:
    """[{model, identity}] as {model: identity}."""
    if not isinstance(value, list) or not all(isinstance(x, dict) and isinstance(x.get("model"), str)
                                              and isinstance(x.get("identity"), dict) for x in value):
        raise DependencyError("identity.shape", "model identities are [{model, identity: {the five items}}]", where)
    out = {x["model"]: x["identity"] for x in value}
    if len(out) != len(value):
        raise DependencyError("identity.shape", "a model is listed twice", where)
    return out


def identity_changes(recorded: dict, current: dict) -> dict:
    """{model: [changed items]} between the identities a result recorded and the current ones (the five masked items
    of section 5.1, model_identity.changed_items); a model added or removed is a change of every item."""
    out = {}
    for m in sorted(set(recorded) | set(current)):
        items = model_identity.changed_items(recorded.get(m) or {}, current.get(m) or {})
        if items:
            out[m] = items
    return out


def _time(value, where: str):
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        t = None
    if t is None or t.tzinfo is None:
        raise DependencyError("t2.time", "a time is ISO 8601 with a time zone", where)
    return t


def _number(value, where: str, positive=False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) \
            or value < 0 or (positive and value == 0):
        raise DependencyError("t2.number", "a finite number" + (" > 0" if positive else " >= 0"), where)
    return float(value)


def _real(value, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise DependencyError("t2.number", "a finite number", where)
    return float(value)


def tost(before: float, after: float, se_old: float, se_new: float, margin: float, alpha: float = T2_ALPHA) -> dict:
    """Two one-sided tests of |after - before| < margin with independent Gaussian MC errors: equivalence when both
    one-sided nulls are rejected at alpha, i.e. the (1 - 2 alpha) interval of the difference lies inside
    (-margin, margin). p is the larger one-sided p-value."""
    d, se = after - before, math.hypot(se_old, se_new)
    if se == 0:
        p = 0.0 if abs(d) < margin else 1.0
    else:
        nd = NormalDist()
        p = max(1 - nd.cdf((d + margin) / se), 1 - nd.cdf((margin - d) / se))
    return {"difference": d, "se": se, "margin": margin, "p": p, "equivalent": p < alpha}


def _record_shape(record) -> None:
    if not isinstance(record, dict) or record.get("schema") != T2_SCHEMA or not isinstance(
            record.get("registration"), dict) or not isinstance(record.get("outcome"), dict):
        raise DependencyError("t2.shape", f"a T2 record is {{schema: {T2_SCHEMA}, registration, outcome}}", "$.record")
    reg = record["registration"]
    for k in ("result_sha256", "old_identities", "new_identities", "points", "observables", "mc_events",
              "margin_fraction", "alpha", "registered_at"):
        if k not in reg:
            raise DependencyError("t2.shape", f"the registration lacks {k}", "$.record.registration")
    if not isinstance(reg["points"], list) or not all(isinstance(p, dict) and isinstance(p.get("label"), str)
                                                      and isinstance(p.get("theta"), dict) for p in reg["points"]):
        raise DependencyError("t2.shape", "registration points are [{label, theta: {name: value}}]",
                              "$.record.registration.points")
    if not isinstance(reg["observables"], list) or not all(
            isinstance(o, dict) and isinstance(o.get("name"), str) for o in reg["observables"]):
        raise DependencyError("t2.shape", "registration observables are [{name, sigma_tot_design}]",
                              "$.record.registration.observables")
    if not isinstance(record["outcome"].get("points"), list):
        raise DependencyError("t2.shape", "the outcome lists its points", "$.record.outcome.points")


def t2_check(record: dict, basis: dict) -> dict:
    """The T2 equivalence record of approval A21 (section 19-g7) against the result it would carry over (each observable's
    sigma_tot_design is sqrt of the diagonal of the design-stage total covariance in link space at theta_ref, A22). basis:
    result_sha256, recorded (the result's identities {model: identity}), current (the current ones), theta_hat {name: value},
    spot_checks [{name: value}] (the section 5.4 points of the result), observables [calibration observable names],
    mc_events (the result's own MC size per evaluation), new_build_first_run (ISO time of the new build's first run,
    from the execution record; None if unknown). Returns {passed, reasons, tests}: a record that is registered after
    the new build ran, loosens the margin or alpha, does not cover theta-hat, every spot-check point and every
    calibration observable at the result's MC size, or fails a TOST, does not pass."""
    _record_shape(record)
    reg, outcome = record["registration"], record["outcome"]
    reasons = []

    def no(code, message):
        reasons.append({"code": code, "message": message})

    if reg["result_sha256"] != basis["result_sha256"]:
        no("t2.other_result", "the record is registered for another result")
    if _identities(reg["old_identities"], "$.record.registration.old_identities") != basis["recorded"] \
            or _identities(reg["new_identities"], "$.record.registration.new_identities") != basis["current"]:
        no("t2.identities", "the record's old and new identities are not the result's recorded and the current ones")
    registered = _time(reg["registered_at"], "$.record.registration.registered_at")
    if basis.get("new_build_first_run") is None:
        no("t2.order_unknown", "the new build's first run time is not given: registration before it is not shown")
    elif registered >= _time(basis["new_build_first_run"], "$.new_build_first_run"):
        no("t2.registered_late", "the record was registered after the new build ran (A21: registered before)")
    margin = _number(reg["margin_fraction"], "$.record.registration.margin_fraction", positive=True)
    alpha = _number(reg["alpha"], "$.record.registration.alpha", positive=True)
    if margin > T2_MARGIN or alpha > T2_ALPHA:
        no("t2.loosened", f"margin {margin} sigma_tot^design and alpha {alpha} may be tightened from "
                          f"{T2_MARGIN} and {T2_ALPHA}, never loosened")
    labels = [p["label"] for p in reg["points"]]
    if len(set(labels)) != len(labels):
        raise DependencyError("t2.shape", "point labels are unique", "$.record.registration.points")
    thetas = [p["theta"] for p in reg["points"]]
    hat = [p["theta"] for p in reg["points"] if p["label"] == THETA_HAT]
    if hat != [basis.get("theta_hat")]:
        no("t2.theta_hat", "the record has no theta-hat point equal to the result's theta-hat")
    missing = [s for s in basis.get("spot_checks") or () if s not in thetas]
    if missing:
        no("t2.spot_checks", f"the section 5.4 spot-check points {missing} are not in the record")
    sig = {o["name"]: _number(o.get("sigma_tot_design"), "$.record.registration.observables", positive=True)
           for o in reg["observables"]}
    if set(sig) != set(basis.get("observables") or ()):
        no("t2.observables", f"the record's observables {sorted(sig)} are not the calibration observables "
                             f"{sorted(basis.get('observables') or ())}")
    if reg["mc_events"] != basis.get("mc_events"):
        no("t2.mc_size", f"registered at {reg['mc_events']} MC events, the result's own size is "
                         f"{basis.get('mc_events')}")
    if outcome.get("registration_sha256") != canonical_sha256(reg):
        no("t2.outcome_unbound", "the outcome is not bound to this registration (registration_sha256)")
    got = {p.get("label"): p for p in outcome["points"] if isinstance(p, dict)}
    tests = []
    for label in labels:
        p = got.get(label)
        if p is None:
            no("t2.outcome_missing", f"no outcome at point {label!r}")
            continue
        if p.get("mc_events") != {"old": reg["mc_events"], "new": reg["mc_events"]}:
            no("t2.mc_size", f"point {label!r} was not evaluated at the registered MC size for both identities")
        obs = p.get("observables") or {}
        for name in sorted(sig):
            o = obs.get(name)
            if not isinstance(o, dict):
                no("t2.outcome_missing", f"no outcome for {name!r} at point {label!r}")
                continue
            w = f"$.record.outcome.points[{label}].{name}"
            t = tost(_real(o.get("old"), w), _real(o.get("new"), w), _number(o.get("se_old"), w),
                     _number(o.get("se_new"), w), margin * sig[name], alpha)
            tests.append(dict(t, point=label, observable=name))
            if not t["equivalent"]:
                no("t2.not_equivalent", f"{name} at {label!r}: |difference| {abs(t['difference']):.4g} not shown "
                                        f"< {t['margin']:.4g} (TOST p = {t['p']:.3g} >= {alpha})")
    return {"passed": not reasons, "reasons": reasons, "tests": tests}


def identity_decision(result: dict, current: list, record: dict | None = None, basis: dict | None = None) -> dict:
    """Section 10.3 change of simulation identity with approval A21 (section 19-g7). result: a calibration-result
    with result_sha256 and model_identities [{model, identity}]; current: the current [{model, identity}] (from
    model_identity.identity). Unchanged identities (theta, phi values and provenance_id are masked, section 5.1):
    `unchanged`. A changed item: `redo`, unless a T2 record (t2_check with basis) passes, which keeps the result
    flagged identity-carried-over, with the new identities, labelled provisional-thresholds (the margin is
    provisional)."""
    h = _result_hash(result, "$.result")
    old = _identities(result.get("model_identities"), "$.result.model_identities")
    now = _identities(current, "$.current")
    changed = identity_changes(old, now)
    out = {"result_sha256": h, "changed": changed}
    if not changed:
        return dict(out, status="ok", decision="unchanged")
    if record is None:
        return dict(out, status="failed", decision="redo",
                    reasons=[{"code": "t2.missing", "message": "the identity changed and no T2 equivalence record "
                                                               "was registered (A21: redo)"}])
    t2 = t2_check(record, dict(basis or {}, result_sha256=h, recorded=old, current=now))
    if not t2["passed"]:
        return dict(out, status="failed", decision="redo", reasons=t2["reasons"], tests=t2["tests"])
    return dict(out, status="ok", decision="carried-over", flags=[CARRIED_OVER, PROVISIONAL],
                model_identities=[{"model": m, "identity": now[m]} for m in sorted(now)], tests=t2["tests"])


# Findings of check_packages that force a joint fit (section 10.4 rules 2 to 4): the packages cannot be multiplied
# independently. package_split, theta_nu_split and xi_version are refusals of one package, not joint fits.
JOINT_FIT_CODES = {"deps.version_conflict": "rule 2: the same shared nuisance constrained with different versions",
                   "deps.source_overlap": "rule 3: intersecting source sets",
                   "deps.common_source": "rules 3 and 4: a common random source outside the result lineage"}


def forced_joint_fits(packages: list, findings: list) -> list[dict]:
    """Each joint fit the conflict rules force (A21, section 19-g8: xi has no versions, so a downstream pull of an
    upstream xi is made correct by these joint fits, and each one is reported). Packages linked by a forcing finding
    are fitted together: one entry per connected group, {packages, reasons: [{code, rule, packages, key | sources}],
    xi_involved}. xi_involved is true when the group joins packages through their xi source sets (source overlap),
    the case versions of xi would otherwise address. Sorted by the packages' ids; empty when nothing is forced."""
    parent = {p["id"]: p["id"] for p in packages}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    reasons = []
    for f in findings:
        if f["code"] not in JOINT_FIT_CODES:
            continue
        if f["code"] == "deps.version_conflict":
            members = sorted(p["id"] for p in packages if f["key"] in (p.get("zeta") or {}))
            r = {"key": f["key"], "versions": f["versions"]}
        else:
            members = sorted(f["packages"])
            r = {"sources": f["sources"]}
        for a in members[1:]:
            parent[find(a)] = find(members[0])
        reasons.append({"code": f["code"], "rule": JOINT_FIT_CODES[f["code"]], "packages": members, **r})
    groups: dict = {}
    for r in reasons:
        groups.setdefault(find(r["packages"][0]), []).append(r)
    out = []
    for rs in groups.values():
        members = sorted({m for r in rs for m in r["packages"]})
        out.append({"packages": members, "reasons": rs,
                    "xi_involved": any(r["code"] == "deps.source_overlap" for r in rs)})
    return sorted(out, key=lambda g: g["packages"])
