"""Run-lineage rules (v6.3 M2c, C9; design docs/dev/cross-artifact-check/m2c-design.md): post-execution evidence through a result
binding (contracts/schemas/result_binding.json) that names the analysis bundle and lock used, the computational-runs
with explicit input sources, the campaigns, and per root the result file and its producer.

Before execution (no binding) every obligation is unverified (check.not_executed). Single runs are read at the
declared level: their manifests are self-reported, and contracts.verify_run only shows them mutually consistent. A
campaign is campaign-recorded only when the adapter's computational-run, state.json collection records, chunk files
and one common recorded execution bundle (core.partition.bundle digest_of and check_campaign) agree; those records are
agent-writable, so that level guards against mistakes and forged chunk files, not a forged state.json. The checker
never re-decides which attempt is valid, never matches by mere membership of a hash in a set, and never reads result
values into a report: outcomes carry digests, paths and labels only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

from contracts.release_manifest import canonical_sha256

# dataset_statuses (contracts/vocab/core.json) a blinded spec's lineage may reach (DR-7: simulated may be permitted);
# a result envelope's own status labels (asimov, synthetic) are no evidence (G7) and are not read
PERMITTED_DATA = ("synthetic", "simulated")
GLOB = set("*?[]")


def outcome(state, reason, message="", evidence=(), declarations=(), **extra):
    from contracts.analysis_checks.rules import outcome as _outcome
    return _outcome(state, reason, message, evidence, declarations, **extra)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _rel_ok(rel: str) -> bool:
    p = PurePosixPath(str(rel))
    return bool(str(rel)) and not p.is_absolute() and ".." not in p.parts


class Evidence:
    """The binding and the records it names, read once per evaluation."""

    def __init__(self, view: dict):
        self.view = view
        self.binding = view.get("results")
        self.root = Path(view.get("root") or ".")
        self.bundle = view.get("bundle") or {}
        self.items = {it["id"]: it for it in self.bundle.get("items", []) if isinstance(it, dict) and "id" in it}
        b = self.binding or {}
        self.recs: dict[str, list[dict]] = {}
        for r in b.get("runs", []):
            self.recs.setdefault(r["run_id"], []).append(r)
        self.campaigns = {c["campaign_uid"]: c for c in b.get("campaigns", [])}
        self._docs: dict[str, tuple] = {}

    def read(self, rel: str, base: str = "") -> bytes | None:
        if not (_rel_ok(rel) and (not base or _rel_ok(base))):
            return None
        p = (self.root / base / rel).resolve()
        if self.root.resolve() not in p.parents:
            return None
        try:
            return p.read_bytes()
        except OSError:
            return None

    def json_at(self, rel: str, base: str = ""):
        data = self.read(rel, base)
        try:
            return json.loads(data) if data is not None else None
        except ValueError:
            return None

    def run(self, run_id: str) -> tuple[dict | None, dict | None, str | None]:
        """(record, document, problem) of a run named once in the binding."""
        if run_id in self._docs:
            return self._docs[run_id]
        recs = self.recs.get(run_id, [])
        if len(recs) != 1:
            res: tuple = (recs[0] if recs else None, None, "ambiguous" if recs else "unlisted")
        else:
            data = self.read(recs[0]["ref"])
            if data is None:
                res = (recs[0], None, "unreadable")
            elif _sha(data) != recs[0]["sha256"]:
                res = (recs[0], None, "changed")
            else:
                try:
                    res = (recs[0], json.loads(data), None)
                except ValueError:
                    res = (recs[0], None, "unreadable")
        self._docs[run_id] = res
        return res

    def result(self, root_id: str) -> dict | None:
        return next((r for r in (self.binding or {}).get("results", []) if r.get("root") == root_id), None)

    def lineage(self, run_id: str) -> tuple[list[str], bool]:
        """The runs a run depends on through product sources, itself first; True when a cycle exists."""
        order: list[str] = []
        state: dict[str, int] = {}
        cycle = False

        def visit(rid: str) -> None:
            nonlocal cycle
            if state.get(rid) == 1:
                cycle = True
                return
            if state.get(rid) == 2:
                return
            state[rid] = 1
            order.append(rid)
            for rec in self.recs.get(rid, []):
                for i in rec.get("inputs", []):
                    prod = (i.get("source") or {}).get("product")
                    if prod:
                        visit(str(prod.get("run")))
            state[rid] = 2
        visit(run_id)
        return order, cycle

    def known_bytes(self) -> set[str]:
        out = {it.get("bytes_sha256") or it.get("sha256") for it in self.items.values()}
        for rid in self.recs:
            _, doc, _ = self.run(rid)
            out |= set(((doc or {}).get("extension") or {}).get("output_hashes", {}).values())
        return {x for x in out if x}


def _evidence(env) -> Evidence:
    ev = getattr(env, "_run_evidence", None)
    if ev is None:
        ev = Evidence(env.view)
        env._run_evidence = ev
    return ev


def _succeeded(doc: dict) -> bool:
    return ((doc.get("extension") or {}).get("exit_status") == 0) and "failed" not in (doc.get("status") or [])


NOT_EXECUTED = ("unverified", "check.not_executed", "no result binding: the analysis has not been bound to results")


# --- r-run.binding --------------------------------------------------------------------------------------------
def r_run_binding(ob: dict, env) -> dict:
    e, rid = _evidence(env), ob["subject"]["root"]
    if e.binding is None:
        return outcome(*NOT_EXECUTED)
    b = e.binding
    ev = [{"root": rid}]
    if b.get("analysis_bundle_sha256") != e.bundle.get("bundle_digest"):
        return outcome("violated", "check.binding_wrong_subject", "the binding names another analysis bundle", ev)
    lock = next((it for it in e.items.values() if it.get("role") == "semantic-lock"), {})
    if b.get("semantic_lock_sha256") != lock.get("sha256"):
        return outcome("violated", "check.semantic_drift",
                       "the lock bound in the result binding is not this bundle's lock: the results ran under other semantics", ev)
    res = e.result(rid)
    if res is None:
        return outcome("unverified", "check.result_unbound", "the binding has no result for this root", ev)
    ev.append({"file": res.get("file"), "sha256": res.get("sha256")})
    data = e.read(str(res.get("file")))
    if data is None or _sha(data) != res.get("sha256"):
        return outcome("violated", "check.result_digest", "the result file is missing or its bytes differ from the binding", ev)
    root = env.roots.get(rid) or {}
    diff = [k for k in ("unit", "scope") if res.get(k) != root.get(k)]
    if res.get("binning") != root.get("binning"):
        diff.append("binning")
    if diff:
        return outcome("violated", "check.result_identity", f"the result's {diff} differ from the root's", ev)
    # 1.1.0 (G8, DR-1): the binding is agent-writable, so its own asserted_by.kind 'person' never removes the flag
    return outcome("satisfied", "check.result_bound",
                   "bound to this bundle and lock, with the root's identity (the attribution is a declaration, C12)", ev,
                   ["result-binding"])


# --- r-run.status ---------------------------------------------------------------------------------------------
def r_run_status(ob: dict, env) -> dict:
    e, rid = _evidence(env), ob["subject"]["root"]
    if e.binding is None:
        return outcome(*NOT_EXECUTED)
    res = e.result(rid)
    if res is None:
        return outcome("unverified", "check.producer_unbound", "no result is bound for this root")
    prod = res.get("producer") or {}
    if "campaign" in prod:
        camp = e.campaigns.get(prod["campaign"])
        art = e.json_at(camp["run_ref"]) if camp else None
        if not isinstance(art, dict):
            return outcome("unverified", "check.producer_unbound", "the campaign's computational-run cannot be read")
        ext = art.get("extension") or {}
        if not _succeeded(art) or "merged" not in (ext.get("output_hashes") or {}):
            return outcome("violated", "check.failed_promoted", "an incomplete or failed campaign merge is cited as the result")
        return outcome("satisfied", "check.producer_succeeded", "a complete campaign merge")
    run_id = str(prod.get("run"))
    order, cycle = e.lineage(run_id)
    if cycle:
        return outcome("violated", "check.run_cycle", "the product references of the root's runs form a cycle", [{"run": run_id}])
    for r in order:
        if len(e.recs.get(r, [])) > 1:
            return outcome("violated", "check.producer_ambiguous", f"run {r!r} is listed more than once", [{"run": r}])
    rec, doc, problem = e.run(run_id)
    if doc is None:
        return outcome("unverified", "check.producer_unbound", f"the named run {run_id!r} is {problem}", [{"run": run_id}])
    outs = (doc.get("extension") or {}).get("output_hashes") or {}
    if outs.get(res.get("file")) != res.get("sha256"):
        return outcome("unverified", "check.producer_unbound", f"run {run_id!r} does not record this result file", [{"run": run_id}])
    if not _succeeded(doc):
        return outcome("violated", "check.failed_promoted", f"run {run_id!r} failed; its output is not a result", [{"run": run_id}])
    for r in order[1:]:
        _, up, problem = e.run(r)
        if up is None:
            return outcome("unverified", "check.producer_unbound", f"upstream run {r!r} is {problem}", [{"run": r}])
        if not _succeeded(up):
            return outcome("violated", "check.failed_upstream", f"upstream run {r!r} failed", [{"run": r}])
    return outcome("satisfied", "check.producer_succeeded", f"the named terminal run {run_id!r} and its upstream runs succeeded",
                   [{"run": r} for r in order])


# --- r-run.closure (R-CLOSE) ----------------------------------------------------------------------------------
def _input_state(e: Evidence, base: str, path: str, sha: str, src: dict | None, known: set) -> str:
    """ok, reserialized, unbound, open or mismatch for one input of a run."""
    if src is None:
        return "unbound" if sha in known else "open"
    if "item" in src:
        it = e.items.get(src["item"])
        if it is None:
            return "mismatch"
        if sha == (it.get("bytes_sha256") or it.get("sha256")):
            return "ok"
        if it.get("digest_kind") == "canonical-json":
            doc = e.json_at(path, base)
            if doc is not None and canonical_sha256(doc) == it.get("sha256"):
                return "reserialized"
        return "mismatch"
    if "external" in src:
        manifest = (e.view.get("items", {}).get(src["external"].get("item")) or {}).get("doc") or {}
        entry = next((f for f in manifest.get("files", []) if isinstance(f, dict) and f.get("path") == src["external"].get("entry")), None)
        return "ok" if entry is not None and entry.get("sha256") == sha else "mismatch"
    if "product" in src:
        _, up, _ = e.run(str(src["product"].get("run")))
        outs = ((up or {}).get("extension") or {}).get("output_hashes") or {}
        return "ok" if outs.get(src["product"].get("output")) == sha else "mismatch"
    return "mismatch"


def _worst(states: dict) -> tuple[str, str, str] | None:
    for st, state, reason in (("open", "violated", "check.closure_open"), ("mismatch", "violated", "check.closure_mismatch"),
                              ("reserialized", "unverified", "check.closure_reserialized"),
                              ("unbound", "unverified", "check.closure_unbound")):
        if states.get(st):
            return state, reason, f"{st}: {sorted(states[st])[:5]}"
    return None


def r_run_closure(ob: dict, env) -> dict:
    from contracts.verify_run import verify_run
    e, rid = _evidence(env), ob["subject"]["root"]
    if e.binding is None:
        return outcome(*NOT_EXECUTED)
    res = e.result(rid)
    if res is None:
        return outcome("unverified", "check.closure_unbound", "no result is bound for this root")
    prod = res.get("producer") or {}
    known = e.known_bytes()
    states: dict[str, list] = {}
    if "campaign" in prod:
        camp = e.campaigns.get(prod["campaign"])
        art = e.json_at(camp["run_ref"]) if camp else None
        bdoc = e.json_at(f"bundles/{camp['execution_bundle_sha256']}.json", camp["dir"]) if camp and camp.get("execution_bundle_sha256") else None
        if not (isinstance(art, dict) and isinstance(bdoc, dict)):
            return outcome("unverified", "check.closure_unbound", "the campaign record or its execution bundle cannot be read")
        frozen = {f.get("path"): f.get("sha256") for f in bdoc.get("files", []) if isinstance(f, dict) and f.get("role") == "campaign"}
        for i in (art.get("extension") or {}).get("input_manifest", []):
            st = "ok" if frozen.get(i.get("path")) == i.get("sha256") else ("mismatch" if i.get("path") in frozen else "open")
            states.setdefault(st, []).append(i.get("path"))
        w = _worst({k: v for k, v in states.items() if k != "ok"})
        if w:
            return outcome(w[0], w[1], w[2])
        return outcome("satisfied", "check.closure_complete",
                       "every campaign input is a file of the frozen execution bundle", [{"campaign": prod["campaign"]}], level="declared")
    order, _ = e.lineage(str(prod.get("run")))
    for run_id in order:
        rec, doc, problem = e.run(run_id)
        if doc is None or rec is None:
            states.setdefault("unbound" if problem in ("unlisted", "ambiguous") else "mismatch", []).append(run_id)
            continue
        if verify_run(doc, e.root / rec.get("base", ""))["status"] == "error":
            states.setdefault("mismatch", []).append(f"{run_id}: outputs")
        sources = {i["path"]: i.get("source") for i in rec.get("inputs", [])}
        for i in (doc.get("extension") or {}).get("input_manifest", []):
            st = _input_state(e, rec.get("base", ""), str(i.get("path")), str(i.get("sha256")), sources.get(i.get("path")), known)
            states.setdefault(st, []).append(f"{run_id}:{i.get('path')}")
    w = _worst({k: v for k, v in states.items() if k != "ok"})
    if w:
        return outcome(w[0], w[1], w[2], [{"run": r} for r in order])
    return outcome("satisfied", "check.closure_complete",
                   "every input maps to a frozen item, an external manifest entry or a bound upstream product (declared level: "
                   "self-reported manifests)", [{"run": r} for r in order], level="declared")


# --- r-run.campaign -------------------------------------------------------------------------------------------
def _campaign_closure(e: Evidence, camp: dict) -> tuple[str, str, str]:
    """G6 (result binding 1.1.0, V82): a campaign's listed inputs, each matching its source (a frozen item, an external
    manifest entry or an upstream run's product), with at least one analysis item among them. A digest mismatch is
    violated; no inputs, an input without a matching source, or no analysis item is unverified."""
    inputs = camp.get("inputs")
    if not inputs:
        return ("unverified", "check.campaign_inputs_unbound",
                "the binding lists no inputs for the campaign (result binding 1.1.0 campaigns[].inputs): whether it read "
                "the analysis cannot be judged")
    known = e.known_bytes()
    states = []  # one per listed input: the same path may be listed twice with different sources
    for i in inputs:
        data = e.read(str(i.get("path")))
        sha = _sha(data) if data is not None else ""
        states.append((str(i.get("path")), _input_state(e, "", str(i.get("path")), sha, i.get("source"), known)))
    bad = sorted({p for p, st in states if st == "mismatch"})
    if bad:
        return ("violated", "check.closure_mismatch", f"campaign inputs whose bytes differ from their source: {bad}")
    loose = sorted({p for p, st in states if st not in ("ok", "reserialized")})
    if loose:
        return ("unverified", "check.campaign_inputs_unbound", f"campaign inputs without a matching source: {loose}")
    if not any("item" in (i.get("source") or {}) for i in inputs):
        return ("unverified", "check.campaign_closure_no_analysis",
                "no input of the campaign is an analysis item: its closure does not reach the analysis")
    return ("satisfied", "", "")


def r_run_campaign(ob: dict, env) -> dict:
    from core.partition.bundle import check_campaign, digest_of
    e, rid = _evidence(env), ob["subject"]["root"]
    if e.binding is None:
        return outcome(*NOT_EXECUTED)
    res = e.result(rid)
    prod = (res or {}).get("producer") or {}
    if res is None:
        return outcome("unverified", "check.campaign_unreadable", "no result is bound for this root")
    if "campaign" not in prod:
        return outcome("not_applicable", "check.no_campaign", "a single-run producer: no campaign records apply")
    camp = e.campaigns.get(prod["campaign"])
    if camp is None:
        return outcome("unverified", "check.campaign_unreadable", "the producer campaign is not listed in the binding")
    ev = [{"campaign": camp["campaign_uid"]}]
    state = e.json_at("state.json", camp["dir"])
    art_bytes = e.read(camp["run_ref"])
    if not isinstance(state, dict) or art_bytes is None or _sha(art_bytes) != camp.get("run_sha256"):
        return outcome("unverified", "check.campaign_unreadable", "state.json or the bound computational-run cannot be read", ev)
    art = json.loads(art_bytes)
    ext = art.get("extension") or {}
    execution = (ext.get("environment") or {}).get("execution") or {}
    if state.get("campaign_uid") != camp["campaign_uid"] or execution.get("campaign_uid") != camp["campaign_uid"]:
        return outcome("violated", "check.campaign_mismatch", "the records belong to another campaign (a same name does not pass)", ev)
    hashes = ext.get("output_hashes") or {}
    chunks = sorted(k[len("chunks/"):-len(".json")] for k in hashes if k.startswith("chunks/") and k.endswith(".json"))
    collected = state.get("collected") or {}
    for cid in chunks:
        c = collected.get(cid)
        if c is None:
            continue
        actual = e.read(f"chunks/{cid}.json", camp["dir"])
        if hashes[f"chunks/{cid}.json"] != c.get("sha256") or actual is None or _sha(actual) != c.get("sha256"):
            return outcome("violated", "check.chunk_digest_conflict",
                           f"chunk {cid}: the adopted output differs from the one the collection record names", ev)
    result = e.json_at(str(res.get("file")))
    if result is None or hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest() != hashes.get("merged"):
        return outcome("violated", "check.merge_mismatch", "the result file is not the campaign's merge (adapter digest kind)", ev)
    closure = _campaign_closure(e, camp)  # 1.1.0 (G6): the campaign's inputs must reach the analysis
    if closure[0] == "violated":
        return outcome(*closure, ev)
    if not chunks or any(cid not in collected for cid in chunks):
        return outcome("unverified", "check.campaign_uncollected", "a merged chunk has no collection record: declared level only", ev)
    owner = {r.get("attempt_id"): r.get("submission") for row in (state.get("chunks") or {}).values()
             for r in row.get("attempt_records", []) if isinstance(r, dict)}
    subs = {s.get("id"): s for s in state.get("submissions", []) if isinstance(s, dict)}
    owning = [subs.get(owner.get(collected[cid].get("attempt_id"))) or {} for cid in chunks]
    if any(s.get("status") != "submitted" for s in owning):
        return outcome("unverified", "check.campaign_orphan", "a collected output belongs to a submission that is not submitted: declared level only", ev)
    digests = {s.get("bundle_digest") for s in owning}
    if None in digests or len(digests) != 1:
        return outcome("unverified", "check.campaign_bundle_unrecorded",
                       "the submissions owning collected attempts lack one common recorded bundle digest: declared level only", ev)
    d = next(iter(digests))
    bdoc = e.json_at(f"bundles/{d}.json", camp["dir"])
    if not isinstance(bdoc, dict) or digest_of(bdoc) != d or check_campaign(bdoc, e.root / camp["dir"]):
        return outcome("unverified", "check.campaign_bundle_invalid", "the recorded execution bundle does not verify or belong to the campaign", ev)
    if camp.get("execution_bundle_sha256") != d:
        return outcome("violated", "check.execution_bundle_mismatch", "the binding names another execution bundle than the campaign recorded", ev)
    if closure[0] == "unverified":
        return outcome(*closure, ev)
    return outcome("satisfied", "check.campaign_recorded",
                   "campaign-recorded: collected chunks, interface record and one verified execution bundle agree. These records "
                   "are agent-writable: this guards against mistakes and forged chunk files, not a forged state.json", ev,
                   level="campaign-recorded")


# --- r-run.blinding -------------------------------------------------------------------------------------------
def _blinded(env, policy) -> bool:
    """The spec's own flag, or the project's blinded list naming the spec's artifact_id (G13, DR-9)."""
    spec = env.spec if isinstance(env.spec, dict) else {}
    bl = (spec.get("extension") or {}).get("blinding") if isinstance(spec.get("extension"), dict) else None
    bl = bl if isinstance(bl, dict) else spec.get("blinding")
    listed = policy.get("blinded") if isinstance(policy, dict) else None
    return (isinstance(bl, dict) and bl.get("blinded") is True) or (
        isinstance(listed, list) and spec.get("artifact_id") is not None and spec.get("artifact_id") in listed)


def _data_leaves(e: Evidence, run_id: str | None, inputs: list | None = None) -> tuple[list[tuple[str, str | None]], bool]:
    """The data leaves of a run's lineage, or of a campaign's inputs (DR-7), as (where, dataset status or None), and
    whether a leaf cannot be classified. A frozen dataset-record item is a data leaf with its dataset status; an
    external-data manifest entry is a data leaf of unknown status; another frozen item (spec, recipe, calibration) is
    not data; a product of an upstream run is followed; an input without a source cannot be classified."""
    from contracts.dependencies import _dataset_status
    order: list[str] = []
    cycle = False
    for rid in ([run_id] if run_id else []) + [str((i.get("source") or {}).get("product", {}).get("run"))
                                               for i in inputs or [] if "product" in (i.get("source") or {})]:
        sub, c = e.lineage(rid)
        order += [r for r in sub if r not in order]
        cycle |= c
    leaves: list[tuple[str, str | None]] = []
    unknown = cycle
    every = list(inputs or [])
    for rid in order:
        rec, _, problem = e.run(rid)
        if problem:
            unknown = True
            continue
        every += (rec or {}).get("inputs", [])
    for i in every:
        src = i.get("source") or {}
        if "item" in src:
            doc = (e.view.get("items", {}).get(src["item"]) or {}).get("doc")
            if isinstance(doc, dict) and doc.get("artifact_type") == "dataset-record":
                leaves.append((f"item:{src['item']}", _dataset_status(doc)))
        elif "external" in src:
            leaves.append((f"external:{src['external'].get('item')}/{src['external'].get('entry')}", None))
        elif "product" not in src:
            unknown = True
    return leaves, unknown


def r_run_blinding(ob: dict, env) -> dict:
    """1.1.0 (DR-7, DR-9): blinding applies by the spec's flag or the project's blinded list (G13); a result is
    permitted by its run lineage, never by its own status label (G7). Every data leaf a dataset record with a
    permitted dataset status (synthetic, simulated) is satisfied. No data leaf is unverified (lineage_no_data): the
    run records are agent-writable, so leaving the data input out must not pass (P4). A leaf of unknown status, or a
    result no run produced (a label only), is unverified. Real data is permitted only by the project's allowed_outputs."""
    e, rid = _evidence(env), ob["subject"]["root"]
    if e.binding is None:
        return outcome(*NOT_EXECUTED)
    policy = e.view.get("blinding")
    if not _blinded(env, policy):
        return outcome("not_applicable", "check.not_blinded", "the spec is not blinded (its flag and the project's blinded list)")
    res = e.result(rid)
    if res is None:
        return outcome("unverified", "check.not_executed", "no result is bound for this root")
    doc = e.json_at(str(res.get("file")))
    status: list = (doc["status"] if isinstance(doc, dict) and isinstance(doc.get("status"), list)
                    else list(res.get("status") or []))
    ev: list[dict] = [{"file": res.get("file"), "sha256": res.get("sha256"), "status": sorted(status)}]
    prod = res.get("producer") or {}
    run_id = prod.get("run")
    camp_inputs = (e.campaigns.get(prod["campaign"]) or {}).get("inputs") if prod.get("campaign") else None
    lineage = None
    if run_id or camp_inputs:
        leaves, unknown = _data_leaves(e, str(run_id) if run_id else None, None if run_id else camp_inputs)
        ev.append({"run" if run_id else "campaign": run_id or prod.get("campaign"),
                   "data_leaves": [{"source": w, "dataset_status": st} for w, st in leaves]})
        real = [w for w, st in leaves if st not in PERMITTED_DATA]
        if leaves and not real and not unknown:
            return outcome("satisfied", "check.blinding_permitted",
                           "every data leaf of the result's lineage is a synthetic or simulated dataset record", ev)
        lineage = ("real" if [w for w, st in leaves if st is not None and st not in PERMITTED_DATA]
                   else "unknown" if real or unknown else "no_data")
    if not isinstance(policy, dict):
        if lineage == "real":
            return outcome("unverified", "check.blinding_policy_unknown", "no project blinding block was given", ev)
    path = str(PurePosixPath(str(res.get("file"))))
    policy = policy if isinstance(policy, dict) else {}
    aid = doc.get("artifact_id") if isinstance(doc, dict) else None
    bare = False
    for entry in policy.get("allowed_outputs") or []:
        entry = str(entry)
        if entry.startswith("artifact:") and aid is not None and entry[len("artifact:"):] == aid:
            return outcome("satisfied", "check.blinding_permitted", "an allowed_outputs artifact entry names it (a policy declaration)",
                           ev, ["blinding.allowed_outputs"])
        if entry.startswith("path:"):
            p = entry[len("path:"):]
            if _rel_ok(p) and not (set(p) & GLOB) and str(PurePosixPath(p)) == path:
                return outcome("satisfied", "check.blinding_permitted", "an allowed_outputs path entry names it (a policy declaration)",
                               ev, ["blinding.allowed_outputs"])
        elif not entry.startswith("artifact:") and entry in (path, PurePosixPath(path).name, aid):
            bare = True
    if bare:
        return outcome("unverified", "check.allowed_output_ambiguous",
                       "only an unprefixed allowed_outputs entry names it; use 'path:' or 'artifact:'", ev)
    if lineage is None:
        return outcome("unverified", "check.blinding_label_only",
                       "no run, and no campaign with listed inputs, produced this result: its status label alone is not evidence", ev)
    if lineage == "no_data":
        return outcome("unverified", "check.lineage_no_data",
                       "the result's lineage records no data input: whether blinded data entered cannot be judged", ev)
    if lineage == "unknown":
        return outcome("unverified", "check.lineage_status_unknown",
                       "a data leaf of the result's lineage has no dataset status, or an input cannot be classified", ev)
    return outcome("violated", "check.blinded_result_cited", "a blinded spec's binding cites a result that is not a permitted derivative", ev)


RULES = {"r-run.binding": r_run_binding, "r-run.status": r_run_status, "r-run.closure": r_run_closure,
         "r-run.campaign": r_run_campaign, "r-run.blinding": r_run_blinding}
