#!/usr/bin/env python3
"""Independent review of one Markdown document by agents that did not write it (docs/dev/independent-review-spec.md,
P1): the process driver. The author agent runs `start`, then `next` repeatedly and does the action it prints, until
`stop`; when the host reports that an agent has finished, it runs `returned`. The plugin dispatches no agent: `dispatch`
prints a fixed two-line message, which the author agent passes to a new agent through the host's own mechanism.

Usage: python3 review.py COMMAND [options]   (run from the project root, or pass --project)
  start DOC [--supersede ID --reason TEXT] [--seed S] [--author NAME] [--author-model M] [--models A,B]
  next                         observe, decide, print the next action (JSON)
  dispatch SLOT                build this attempt's packet, validate its example, print the dispatch message
  returned SLOT                the host reported the agent finished
  receive SLOT                 validate review_record.json; write accepted or rejected
  withdraw SLOT --reason timeout|host-failure|isolation-failure|other [--explanation TEXT]
  dispose FINDING --as changed|partially-changed|declined|unresolved --reason TEXT [--verified EVID | --adopted-unverified]
  arbitrate | rereview | escalate --reason TEXT | report | close
  resolve ITEM --by NAME --decision D --reason TEXT    a human resolves an escalated item
  repair CODE                  how to fix a repair code; the next `next` confirms the fix
Common options: --project DIR (default: current folder), --review ID (default: the only open review), --now
YYYY-MM-DDTHH:MM:SSZ (default: the clock), --observation FILE (fixed host facts, for reproducible runs).
Files: <project>/reviews/review-config.json (created with defaults by start when missing), <project>/reviews/<id>/,
and the private directory (config private_dir, else $XDG_STATE_HOME/hep-research/reviews/ or
~/.local/state/hep-research/reviews/). `python3 <plugin root>/contracts/review.py check <review dir>` checks a review.
Output: one JSON object with a "status" key. Exit 0 ok, 1 negative result (a stop on error, a reverted change at close),
2 refused command or bad input, 3 incomplete. A closed review here is not a review record by a non-author reviewer
in the sense of docs/dev/v6.3/decision-enforce.md (maintainer decision 2026-10-21); it is advisory input a human
reviewer may cite.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import secrets
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2]
sys.dont_write_bytecode = True
for _p in (str(PLUGIN), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from contracts import review as R  # noqa: E402
from review_lib import canary as CAN  # noqa: E402
from review_lib import observe as OBS  # noqa: E402
from review_lib import packet as PKT  # noqa: E402
from review_lib import receipt as REC  # noqa: E402
from review_lib import report as REP  # noqa: E402
from review_lib import units as U  # noqa: E402
from review_lib.store import Review, ReviewError, default_private_root, find_reviews, load_asset, read_json, write_json  # noqa: E402

FIX = {
    "config_changed": "Restore reviews/review-config.json to the configuration recorded for this round, or restart with "
                      "start DOC --supersede ID --reason TEXT.",
    "config_out_of_range": "Fix the configuration value(s) listed. If the configuration was changed after the review "
                           "started, use start --supersede.",
    "canary_in_deliverable": "A mutated unit's text appears in the delivered document: delete it.",
    "isolation_precondition": "Set CLAUDE_CODE_FORK_SUBAGENT=0 in env of settings.json (then restart the host), or add "
                              "Agent(fork) to permissions.deny; then run next.",
    "isolation_not_yet_effective": "The settings changed after the host session started: restart the host, then run "
                                   "next. All review state is in files, so the review resumes directly.",
    "shared_dir_contamination": "Move the listed files to the private directory or delete them.",
    "change_without_edit": "Edit the document so the finding's units change, then dispose the finding again (or dispose "
                           "it differently).",
}


def now_text() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class Ctx:
    def __init__(self, args):
        self.args = args
        self.project = Path(args.project).resolve()
        self.now = args.now or now_text()
        if not R.TIMESTAMP.match(self.now):
            raise ReviewError("--now must be YYYY-MM-DDTHH:MM:SSZ")
        self.given = None
        if args.observation:
            try:
                self.given = read_json(Path(args.observation))
            except (OSError, ValueError) as exc:
                raise ReviewError(f"unreadable --observation file: {exc}") from exc
        self.cfg_path = self.project / "reviews" / "review-config.json"
        cfg = read_json(self.cfg_path) if self.cfg_path.is_file() else {}
        self.private_root = Path(os.path.expanduser(cfg["private_dir"])) if cfg.get("private_dir") else default_private_root()
        self._rv = None

    @property
    def rv(self) -> Review:
        if self._rv is None:
            rid = self.args.review
            if not rid:
                open_ = [x for x in find_reviews(self.project)
                         if R.fold(Review(self.project, x, self.private_root).events())["terminal"] is None]
                if not open_ and len(find_reviews(self.project)) == 1:
                    open_ = find_reviews(self.project)  # a finished review answers next with stop
                if len(open_) != 1:
                    raise ReviewError(f"{len(open_)} open reviews in {self.project / 'reviews'}; name one with --review")
                rid = open_[0]
            self._rv = Review(self.project, rid, self.private_root)
            if not self._rv.log.is_file():
                raise ReviewError(f"no review {rid}")
        return self._rv

    def state(self):
        events, problems = self.rv.verified()
        return events, R.fold(events) if events else None, problems

    def observe(self):
        """Run observe and write its events; return (events, state, problems) after it."""
        events, problems = self.rv.verified()
        if problems:
            return events, None, problems
        if R.fold(events)["terminal"]:
            return self.state()  # a closed or superseded review is never written again
        data, late = OBS.observe(self.rv, self.now, self.given, self.private_root)
        for d in late:
            self.rv.append("late", self.now, d)
        self.rv.append("observed", self.now, data)
        return self.state()

    def decide(self):
        events, st, problems = self.observe()
        if problems:
            return events, st, {"row": 1, "action": "stop", "reason": f"error: {problems[0]}"}
        return events, st, R.decide(R.snapshot(st))


def lens_table() -> dict:
    return load_asset("review-lenses.json")["lenses"]


def host_terms() -> list[str]:
    return load_asset("review-hosts.json")["hosts"]["claude-code"]["terms"]


def round_seed(rv: Review, r: int) -> str:
    """The round seed; the master seed is bound to the review id, so one --seed reused for several reviews never
    repeats their nonces, slot labels or samples."""
    return U.derive(rv.seeds()["master"], "round", r)


def attempt_seed(rv: Review, r: int, sid: str, k: int) -> str:
    return U.derive(round_seed(rv, r), "attempt", sid, k)


def allocate_slots(lenses: list[str], models: list[str], seed: str, first: int = 1, offset: int = 0) -> dict:
    """A2: one lens and one shadow slot per lens, random labels, models in rotation (a shadow's model differs from its
    lens's when there is more than one model)."""
    roles = [("lens", L) for L in lenses] + [("shadow", L) for L in lenses]
    ids = [f"S{i}" for i in range(first, first + len(roles))]
    U.rng(U.derive(seed, "slots")).shuffle(ids)
    out = {}
    m = len(models)
    for n, ((role, lens), sid) in enumerate(zip(roles, ids)):
        i = lenses.index(lens)
        model = models[(i + offset) % m] if role == "lens" else models[(i + offset + 1) % m]
        out[sid] = {"role": role, "lens": lens, "model": model}
    return out


def build_round(ctx: Ctx, rv: Review, r: int, text: str, lenses: list[str], prev_units=None) -> tuple[list, dict, dict]:
    units = U.unit_table(text, lenses, lens_table(), host_terms())
    mapping = U.map_units(prev_units, units) if prev_units is not None else None
    table = {"units_version": "1.0.0", "round": r, "source_sha256": U.sha256_text(text), "units": units, "mapping": mapping}
    write_json(rv.units_path(r), table)
    (rv.private / f"round-{r}").mkdir(parents=True, exist_ok=True)
    (rv.private / f"round-{r}" / "source.md").write_bytes(text.encode("utf-8"))
    return units, table, mapping


# --- commands --------------------------------------------------------------------------------------------------------

def cmd_start(ctx: Ctx) -> dict:
    a = ctx.args
    doc = Path(a.doc)
    doc = (doc if doc.is_absolute() else ctx.project / doc).resolve()
    if not doc.is_file():
        raise ReviewError(f"no document {a.doc}")
    try:
        rel = doc.relative_to(ctx.project).as_posix()
    except ValueError as exc:
        raise ReviewError("the document must be inside the project") from exc
    text = OBS.read_doc(doc)
    if not ctx.cfg_path.is_file():
        models = [m for m in (a.models or "host-default").split(",") if m]
        write_json(ctx.cfg_path, {"config_version": "1.0.0", "models": models})
    cfg = read_json(ctx.cfg_path)
    probs = R.config_problems(cfg) + OBS.private_dir_problems(cfg, ctx.project, ctx.private_root, ctx.given)
    if probs:
        raise ReviewError("config_out_of_range: " + "; ".join(probs))
    eff = R.effective_config(cfg)
    table_l = lens_table()
    unknown = [x for x in eff["extra_lenses"] if x not in table_l]
    if unknown:
        raise ReviewError(f"extra_lenses not in the lens table: {unknown}")
    open_same = []
    for x in find_reviews(ctx.project):
        old = Review(ctx.project, x, ctx.private_root)
        st = R.fold(old.events())
        if st["terminal"] is None and st["document"] == rel:
            open_same.append(old)
    if open_same and not a.supersede:
        raise ReviewError(f"{rel} already has an unfinished review ({open_same[0].id}); use --supersede ID --reason TEXT")
    seed = a.seed if a.seed is not None else secrets.token_hex(16)
    source_sha = U.sha256_text(text)
    rid = "R" + U.derive(source_sha, ctx.now, seed)[:10]
    if a.supersede:
        if not a.reason:
            raise ReviewError("--supersede needs --reason")
        old = [o for o in open_same if o.id == a.supersede]
        if not old:
            raise ReviewError(f"{a.supersede} is not an unfinished review of {rel}")
        old[0].append("superseded", ctx.now, {"by": rid, "reason": a.reason})
    rv = Review(ctx.project, rid, ctx.private_root)
    if rv.log.exists():
        raise ReviewError(f"review {rid} exists")
    ctx._rv = rv
    master = U.derive(str(seed), rid)
    rv.save_seeds({"seed": str(seed), "master": master})
    lenses = U.active_lenses(text, table_l, eff["extra_lenses"])
    units, table, _ = build_round(ctx, rv, 1, text, lenses)
    rs = round_seed(rv, 1)
    deep = {L: U.sample_deep(units, [u["id"] for u in units if u["in_scope"][L]], int(eff["deep_sample"]),
                             U.derive(rs, "deep", L)) for L in lenses}
    slots = allocate_slots(lenses, eff["models"], rs)
    rv.save_slots({"1": slots})
    write_json(rv.private / "round-1" / "sample.json", {"lenses": lenses, "deep": deep})
    rv.save_seeds({"seed": str(seed), "master": master, "rounds": {"1": rs}})
    rv.append("round_started", ctx.now, {
        "review_id": rid, "round": 1, "document": rel, "source_sha256": source_sha,
        "units_sha256": R.sha256_file(rv.units_path(1)), "config": cfg, "config_sha256": R.sha256_file(ctx.cfg_path),
        "slots": [{"slot_id": s, "model": slots[s]["model"]} for s in sorted(slots, key=R._slot_order)],
        "author": {"identity": a.author, "model": a.author_model}, "carry_forward": {}, "removed_findings": []})
    ctx.observe()
    return {"status": "ok", "review_id": rid, "round": 1, "units": len(units), "lenses": lenses,
            "slots": len(slots), "next": "run next"}


def cmd_next(ctx: Ctx) -> dict:
    _, _, act = ctx.decide()
    act = dict(act)
    if act["action"] == "repair":
        act["fix"] = {c: FIX[c] for c in act["codes"]}
    status = "error" if act["row"] == 1 else "ok"
    return dict({"status": status, "review_id": ctx.rv.id}, **act)


def _require(act: dict, action: str, slot: str | None = None):
    if act["action"] != action or (slot and slot not in act.get("slots", [])):
        raise ReviewError(f"decide asks for {act['action']} (row {act['row']}), not {action}" + (f" {slot}" if slot else ""))


def _main_lens_canaries(ctx: Ctx, rv: Review, r: int, main_sid: str, lens: str, k: int | None = None) -> list[dict]:
    """The canaries of a lens slot's attempt k (default: its latest dispatched attempt, else attempt 1), generated
    once and kept in the private directory, so the lens and its shadow see the same choice."""
    st = R.fold(rv.events())
    atts = st["attempts"].get((r, main_sid), {})
    if k is None:  # the lens's live or accepted attempt; after a reject or withdraw, the attempt it will dispatch next
        k = (max(atts) + (1 if atts[max(atts)]["outcome"] in ("rejected", "withdrawn") else 0)) if atts else 1
    path = rv.private_attempt(r, main_sid, k) / "canary.json"
    if path.exists():
        return read_json(path)["canaries"]
    cfg = R.effective_config(st["rounds"][r]["config"])
    units = read_json(rv.units_path(r))["units"]
    text = OBS.read_doc(rv.private / f"round-{r}" / "source.md")
    exclude = set()
    for p in rv.private.glob(f"round-{r}/*/attempt-*/canary.json"):
        if p.parent.parent.name != main_sid:
            exclude |= {c["unit"] for c in read_json(p)["canaries"]}
    lt = lens_table().get(lens, {})
    eligible = [u["id"] for u in units if u["in_scope"].get(lens)]
    cans, rejected = ([], []) if lt.get("canary") not in ("facts", "design") else \
        CAN.make_canaries(lt["canary"], units, text, eligible, exclude, int(cfg["canaries_per_slot"]),
                          U.derive(attempt_seed(rv, r, main_sid, k), "canaries"))
    salt = U.derive(attempt_seed(rv, r, main_sid, k), "salt")
    write_json(path, {"canaries": cans, "rejected": rejected, "salt": salt})
    return cans


def _verdict_bundle(rv: Review, gid: str) -> dict:
    """The full text of an accepted verdict: claim, verdict, cited evidence and findings (for items.json)."""
    r, sid, cid = gid.split("/", 2)
    st = R.fold(rv.events())
    k = max(x for x, a in st["attempts"][(int(r), sid)].items() if a["outcome"] == "accepted")
    rec = read_json(rv.attempt_dir(int(r), sid, k) / "review_record.json")
    v = next(x for x in rec["verdicts"] if x["claim_id"] == cid)
    claim = next(x for x in rec["claims"] if x["id"] == cid)
    ev = [e for e in rec["evidence"] if e["id"] in v["evidence_ids"]]
    fs = [f for f in rec["findings"] if f["id"] in v["finding_ids"]]
    return {"claim": claim, "verdict": v["verdict"], "rationale": v["rationale"], "evidence": ev,
            "refutation_attempts": v["refutation_attempts"], "findings": fs}


def cmd_dispatch(ctx: Ctx) -> dict:
    sid = ctx.args.slot
    events, st, act = ctx.decide()
    _require(act, "dispatch", sid)
    rv = ctx.rv
    r = st["round"]
    slots = rv.slots()[str(r)]
    info = slots[sid]
    cfg = R.effective_config(st["rounds"][r]["config"])
    k = st["attempts"].get((r, sid), {}) and max(st["attempts"][(r, sid)]) or 0
    k += 1
    aseed = attempt_seed(rv, r, sid, k)
    units = read_json(rv.units_path(r))["units"]
    text = OBS.read_doc(rv.private / f"round-{r}" / "source.md")
    sample = read_json(rv.private / f"round-{r}" / "sample.json")
    role, lens = info["role"], info.get("lens")
    texts, roles_map, items, cans = {}, {}, None, []
    skim, deep, focus, carry = [], [], [], []
    doc = text
    if role == "lens":
        cans = _main_lens_canaries(ctx, rv, r, sid, lens, k)
        doc = CAN.apply(text, cans)
        for c in cans:
            u = next(x for x in units if x["id"] == c["unit"])
            texts[c["unit"]] = u["text"].replace(c["original"], c["mutated"], 1)
        deep = list(sample["deep"][lens])
        skim = [u["id"] for u in units if u["in_scope"].get(lens)]
        for c in st["rounds"][r]["carry_forward"].get(sid, []):
            carry.append({"ref": c["ref"], "kind": c["kind"], "units": c["units"], "previous": _previous(rv, c)})
    elif role == "shadow":
        main = next(s for s, v in slots.items() if v["role"] == "lens" and v["lens"] == lens)
        mc = _main_lens_canaries(ctx, rv, r, main, lens)
        cu = [c["unit"] for c in mc]
        focus = cu + _decoys(units, sample["deep"][lens], set(cu), lens, U.derive(aseed, "decoys"))
        focus = [u["id"] for u in units if u["id"] in set(focus)]
    else:
        it = st["items"][info["item"]]
        texts_orig = {u["id"]: u["text"] for u in units}
        entry = {"item_id": it["item_id"], "type": it["type"], "lenses": it["lenses"]}
        if it["type"] == "conflict":
            entry["first"], entry["second"] = _verdict_bundle(rv, it["first"]), _verdict_bundle(rv, it["second"])
            us = entry["first"]["claim"]["units"] + entry["second"]["claim"]["units"]
        else:
            f = st["findings"][it["finding"]]
            fr, fsid, fid = it["finding"].split("/", 2)
            fk = max(x for x, a in st["attempts"][(int(fr), fsid)].items() if a["outcome"] == "accepted")
            rec = read_json(rv.attempt_dir(int(fr), fsid, fk) / "review_record.json")
            entry["finding"] = next(x for x in rec["findings"] if x["id"] == fid)
            entry["decline_reason"] = f["disposals"][-1]["reason"]
            us = f["units"]
        entry["units"] = sorted(set(us), key=R.unit_pos)
        entry["unit_texts"] = {u: texts_orig.get(u, "") for u in entry["units"]}
        items = [entry]
    for u in skim:
        roles_map[u] = "skim"
    for u in deep:
        roles_map[u] = "deep"
    for u in focus:
        roles_map[u] = "focus"
    scope = {"slot_id": sid, "lens": lens, "skim_units": skim, "deep_units": deep, "focus_units": focus,
             "max_units_per_claim": cfg["max_units_per_claim"], "na_max_ratio": cfg["na_max_ratio"],
             "unresolved_max_ratio": cfg["unresolved_max_ratio"], "refutation_duplicate_max": cfg["refutation_duplicate_max"],
             "refutation_min_attempts_effective": R.refutation_threshold(cfg, len(deep) + len(focus)),
             "carry_forward": carry}
    kind = role if role in ("lens", "shadow") else "arbiter"
    pdir = rv.attempt_dir(r, sid, k) / "packet"
    instructions = PKT.render_instructions(kind=kind, lens=lens or "facts", lens_info=lens_table().get(lens or "", {}),
                                           scope=scope, review_id=rv.id, round_=r, attempt=k, plugin=PLUGIN,
                                           example=PKT.example_record(kind, sid))
    sums = PKT.write_packet(pdir, slot_id=sid, document=PKT.packet_document(doc, sid),
                            units=PKT.packet_units(units, lens if role != "arbiter" else None, texts, roles_map),
                            scope=scope, items=items, instructions=instructions)
    try:
        PKT.validate_written_example(pdir / "instructions.md", "arbiter" if kind == "arbiter" else "reviewer",
                                     int(cfg["max_units_per_claim"]))
    except ReviewError:
        import shutil
        shutil.rmtree(rv.attempt_dir(r, sid, k), ignore_errors=True)
        raise
    (rv.attempt_dir(r, sid, k) / "work").mkdir(exist_ok=True)
    priv = rv.private_attempt(r, sid, k)
    salt = U.derive(aseed, "salt")
    if not (priv / "canary.json").exists():
        write_json(priv / "canary.json", {"canaries": [], "rejected": [], "salt": salt})
    write_json(priv / "sample_seed", {"round_seed": round_seed(rv, r), "attempt_seed": aseed})
    nonce = U.derive(aseed, "nonce")[:20]
    obs = st["observed"]
    rv.append("dispatched", ctx.now, {
        "round": r, "slot_id": sid, "attempt": k, "packet_sha256": sums["packet_sha256"], "nonce": nonce,
        "instructions_sha256": sums["instructions_sha256"], "deadline": OBS.deadline(ctx.now, cfg),
        "canary_commitment": R.sha256_bytes((salt + R.canonical_sha256(cans)).encode()),
        "seed_commitment": R.sha256_bytes((salt + aseed).encode()), "started": ctx.now,
        "canaries": len(cans), "canaries_expected": int(cfg["canaries_per_slot"]) if role == "lens" else 0,
        "instruction_files_sha256": OBS.instruction_hash(obs)})
    msg = PKT.dispatch_message(nonce, pdir / "instructions.md", sums["instructions_sha256"])
    return {"status": "ok", "slot": sid, "attempt": k, "message": msg,
            "note": "Pass exactly these two lines, and nothing else, to a new agent; on Claude Code name a non-fork "
                    "subagent type. Run returned SLOT when the host reports the agent has finished."}


def _previous(rv: Review, c: dict) -> dict:
    r, sid, local = c["target"].split("/", 2)
    st = R.fold(rv.events())
    k = max(x for x, a in st["attempts"][(int(r), sid)].items() if a["outcome"] == "accepted")
    rec = read_json(rv.attempt_dir(int(r), sid, k) / "review_record.json")
    if c["kind"] == "finding":
        f = next(x for x in rec["findings"] if x["id"] == local)
        return {"finding": {k2: f[k2] for k2 in ("kind", "severity", "value", "correction", "description", "fix")}}
    v = next(x for x in rec["verdicts"] if x["claim_id"] == local)
    claim = next(x for x in rec["claims"] if x["id"] == local)
    return {"claim": claim["summary"], "verdict": v["verdict"], "rationale": v["rationale"]}


def _decoys(units: list[dict], lens_deep: list[str], exclude: set, lens: str, seed: str) -> list[str]:
    """Two decoys for a shadow: from the main lens's deep units first, then its in-scope units; facts and sources
    decoys must carry a plugin path, file:line or URL (spec 4.5)."""
    by = {u["id"]: u for u in units}

    def ok(uid):
        if uid in exclude:
            return False
        t = by[uid]["text"]
        return lens not in ("facts", "sources") or bool(U.plugin_paths_in(t) or U.FILE_LINE.search(t) or U.URL.search(t))

    r = U.rng(seed)
    first = [u for u in lens_deep if ok(u)]
    r.shuffle(first)
    out = first[:2]
    if len(out) < 2:
        rest = [u["id"] for u in units if u["in_scope"].get(lens) and ok(u["id"]) and u["id"] not in out]
        r.shuffle(rest)
        out += rest[:2 - len(out)]
    return out


def cmd_returned(ctx: Ctx) -> dict:
    sid = ctx.args.slot
    _, st, problems = ctx.state()
    if problems:
        raise ReviewError(problems[0])
    r = st["round"]
    atts = st["attempts"].get((r, sid))
    if not atts or atts[max(atts)]["outcome"] is not None or atts[max(atts)]["returned"]:
        raise ReviewError(f"{sid} has no running attempt in round {r}")
    ctx.rv.append("returned", ctx.now, {"round": r, "slot_id": sid, "attempt": max(atts)})
    return {"status": "ok", "slot": sid, "attempt": max(atts)}


def cmd_withdraw(ctx: Ctx) -> dict:
    a = ctx.args
    if a.reason == "other" and not a.explanation:
        raise ReviewError("--reason other needs --explanation")
    _, st, problems = ctx.state()
    if problems:
        raise ReviewError(problems[0])
    r = st["round"]
    atts = st["attempts"].get((r, a.slot))
    if not atts or atts[max(atts)]["outcome"] is not None:
        raise ReviewError(f"{a.slot} has no running attempt in round {r}")
    d = {"round": r, "slot_id": a.slot, "attempt": max(atts), "reason": a.reason}
    if a.explanation:
        d["explanation"] = a.explanation
    ctx.rv.append("withdrawn", ctx.now, d)
    return {"status": "ok", "slot": a.slot, "attempt": max(atts), "reason": a.reason}


def cmd_receive(ctx: Ctx) -> dict:
    sid = ctx.args.slot
    events, st, act = ctx.decide()
    _require(act, "receive", sid)
    rv = ctx.rv
    r = st["round"]
    k = max(st["attempts"][(r, sid)])
    a = st["attempts"][(r, sid)][k]
    info = rv.slots()[str(r)][sid]
    path = rv.attempt_dir(r, sid, k) / "review_record.json"
    raw = path.read_bytes()
    review_sha = R.sha256_bytes(raw)
    try:
        record = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        record = None
    item_lenses, parties = {}, []
    if info["role"] == "arbiter":
        it = st["items"][info["item"]]
        item_lenses[it["item_id"]] = it["lenses"]
        for g in [it["first"], it["second"], it["finding"]]:
            if g:
                gr, gs, _ = g.split("/", 2)
                gk = max(x for x, aa in st["attempts"][(int(gr), gs)].items() if aa["outcome"] == "accepted")
                parties.append(read_json(rv.attempt_dir(int(gr), gs, gk) / "review_record.json")["reviewer"]["identity"].strip())
    obs = st["observed"]
    rctx = REC.build_context(rv, r=r, sid=sid, k=k, slot=info, dispatched=a["dispatched"],
                             author=st["author"]["identity"], shared=OBS.shared_dirs(rv.project, ctx.given),
                             instructions_changed=OBS.instruction_hash(obs) != a["dispatched"]["instruction_files_sha256"],
                             parties=parties, item_lenses=item_lenses, record=record)
    problems = R.receipt_codes(record, rctx) if record is not None else [("schema_invalid", "not JSON")]
    recomputed = {p: f["sha256"] for p, f in sorted(rctx["files"].items()) if f["local"]}
    base = {"round": r, "slot_id": sid, "attempt": k, "review_sha256": review_sha, "recomputed": recomputed}
    if problems:
        codes = sorted({c for c, _ in problems})
        rv.append("rejected", ctx.now, dict(base, codes=codes, problems=[m for _, m in problems][:40]))
        return {"status": "rejected", "slot": sid, "attempt": k, "codes": codes,
                "problems": [m for _, m in problems], "next": "run next (re-dispatch while attempts remain)"}
    metrics = R.record_metrics(record, rctx)
    data = dict(base, metrics=metrics, identity=record["reviewer"]["identity"],
                host_injected=record["isolation"]["host_injected"])
    follow = []
    if info["role"] != "arbiter":
        cu = {c["unit"] for c in rctx["canaries"]}
        claims = {c["id"]: c for c in record["claims"]}
        data["verdicts"] = [{"claim_id": v["claim_id"], "units": claims[v["claim_id"]]["units"], "verdict": v["verdict"],
                             "finding_ids": v["finding_ids"],
                             "eligible": not (info["role"] == "lens" and set(claims[v["claim_id"]]["units"]) & cu)}
                            for v in record["verdicts"]]
        data["findings"] = [{"id": f["id"], "kind": f["kind"], "severity": f["severity"], "units": f["units"]}
                            for f in record["findings"]]
        hits = R.canary_hits(record, rctx["canaries"], rctx["unit_text"], int(rctx["limits"]["max_units_per_claim"]))
        hit_ids = {x for fs in hits.values() for x in fs}
        for f in record["findings"]:
            if f["id"] in hit_ids and set(f["units"]) <= cu:
                follow.append(("disposed", {"finding": f"{r}/{sid}/{f['id']}", "disposition": "auto-canary",
                                            "reason": "a control finding (hit)", "verification": None,
                                            "edited_units": [], "finding_units": f["units"], "round": r, "by": "review.py"}))
        refs = {c["ref"]: c for c in st["rounds"][r]["carry_forward"].get(sid, [])}
        for c in record.get("carry_forward", []):
            ref = refs.get(c["ref"])
            if ref and ref["kind"] == "finding":
                ev = "change_confirmed" if c["status"] == "confirmed" else "change_rejected"
                follow.append((ev, {"finding": ref["target"], "round": r, "slot_id": sid}))
    else:
        for res in record["resolves"]:
            follow.append(("arbitration_resolved", {"round": r, "item_id": res["item_id"], "conclusion": res["conclusion"],
                                                    "record_sha256": review_sha}))
    rv.append("accepted", ctx.now, data)
    for ev, d in follow:
        rv.append(ev, ctx.now, d)
    return {"status": "ok", "slot": sid, "attempt": k, "accepted": True, "events": [e for e, _ in follow]}


def _mapped_units(rv: Review, st: dict, g: str) -> list[str]:
    f = st["findings"][g]
    return list(f.get("units_now") or f["units"])


def cmd_dispose(ctx: Ctx) -> dict:
    a = ctx.args
    _, st, problems = ctx.state()
    if problems:
        raise ReviewError(problems[0])
    g = a.finding
    f = st["findings"].get(g)
    if f is None:
        raise ReviewError(f"no finding {g}")
    allowed = {"open": ("changed", "partially-changed", "declined", "unresolved"),
               "reopened": ("changed", "partially-changed", "unresolved"),
               "removed-pending": ("changed", "declined")}.get(f["state"])
    if not allowed:
        raise ReviewError(f"{g} is {f['state']}; nothing to dispose")
    if a.as_ not in allowed:
        raise ReviewError(f"{g} is {f['state']}: dispose as one of {list(allowed)}")
    changed = a.as_ in ("changed", "partially-changed")
    if changed and not (a.verified or a.adopted_unverified):
        raise ReviewError("changed and partially-changed need --verified EVID or --adopted-unverified")
    if not changed and (a.verified or a.adopted_unverified):
        raise ReviewError("--verified and --adopted-unverified apply only to changed and partially-changed")
    try:
        text = OBS.read_doc(ctx.project / st["document"])
    except (OSError, UnicodeDecodeError):
        text = None
    chg, rem = OBS.changed_removed(ctx.rv, st, text)
    ver = {"verified": a.verified} if a.verified else {"adopted_unverified": True} if a.adopted_unverified else None
    d = {"finding": g, "disposition": a.as_, "reason": a.reason, "verification": ver, "edited_units": sorted(set(chg + rem)),
         "finding_units": _mapped_units(ctx.rv, st, g), "round": st["round"], "by": a.by}
    ctx.rv.append("disposed", ctx.now, d)
    covered = bool(set(d["edited_units"]) & set(d["finding_units"]))
    return {"status": "ok", "finding": g, "disposition": a.as_,
            "edit_covers_finding": covered if changed else None}


def cmd_arbitrate(ctx: Ctx) -> dict:
    _, st, act = ctx.decide()
    _require(act, "arbitrate")
    rv = ctx.rv
    r = st["round"]
    allslots = rv.slots()
    slots = allslots[str(r)]
    cfg = R.effective_config(st["rounds"][r]["config"])
    nums = [int(s[1:]) for s in slots if s[1:].isdigit()]
    n_items = len(st["items"])
    made = []
    for it in act["items"]:
        n_items += 1
        nums.append(max(nums) + 1)
        sid = f"S{nums[-1]}"
        refs = [x for x in (it["first"], it["second"], it["finding"]) if x]
        involved = [x.split("/")[1] for x in refs]
        party_models = {allslots[x.split("/")[0]][x.split("/")[1]]["model"] for x in refs}
        free = [m for m in cfg["models"] if m not in party_models]
        model = free[0] if free else cfg["models"][n_items % len(cfg["models"])]
        lenses = sorted({allslots[x.split("/")[0]][x.split("/")[1]]["lens"] for x in refs})
        iid = f"A{r}.{n_items}"
        slots[sid] = {"role": "arbiter", "lens": None, "model": model, "item": iid}
        rv.save_slots(allslots)
        rv.append("arbitration_needed", ctx.now, {"round": r, "item_id": iid, "type": it["type"], "slot_id": sid,
                                                   "model": model, "first": it["first"], "second": it["second"],
                                                   "finding": it["finding"], "lenses": lenses,
                                                   "involved": involved})
        made.append({"item_id": iid, "type": it["type"], "slot": sid})
    return {"status": "ok", "items": made, "next": "run next (the arbitration slots are dispatched like any other)"}


def cmd_rereview(ctx: Ctx) -> dict:
    _, st, act = ctx.decide()
    _require(act, "rereview")
    rv = ctx.rv
    r = st["round"]
    nr = r + 1
    text = OBS.read_doc(ctx.project / st["document"])
    prev = read_json(rv.units_path(r))["units"]
    prev_sample = read_json(rv.private / f"round-{r}" / "sample.json")
    cfg = R.effective_config(st["rounds"][r]["config"])
    lenses = list(dict.fromkeys(prev_sample["lenses"] + U.active_lenses(text, lens_table(), cfg["extra_lenses"])))
    seeds = rv.seeds()
    seeds.setdefault("rounds", {})[str(nr)] = U.derive(seeds["master"], "round", nr)
    rv.save_seeds(seeds)
    units, table, mapping = build_round(ctx, rv, nr, text, lenses, prev)
    rs = round_seed(rv, nr)
    allslots = rv.slots()
    old = allslots[str(r)]
    slots = allocate_slots(lenses, cfg["models"], rs, offset=r)
    allslots[str(nr)] = slots
    rv.save_slots(allslots)
    new_lens_slot = {v["lens"]: s for s, v in slots.items() if v["role"] == "lens"}
    plan, removed = R.carry_forward_plan(st, mapping, allslots, new_lens_slot)
    old_to_new = {a: b for a, b in mapping["unchanged"] + mapping["changed"]}
    new_ids = {b for _, b in mapping["changed"]} | set(mapping["added"])
    deep = {}
    for L in lenses:
        scope_ids = [u["id"] for u in units if u["in_scope"].get(L)]
        base = [u for u in scope_ids if u in new_ids]
        for g, f in st["findings"].items():
            if f["round"] == r and old.get(f["slot"], {}).get("lens") == L:
                base += [old_to_new[u] for u in f["units"] if u in old_to_new]
        deep[L] = U.top_up(units, base, scope_ids, int(cfg["deep_sample"]), U.derive(rs, "deep", L))
    write_json(rv.private / f"round-{nr}" / "sample.json", {"lenses": lenses, "deep": deep})
    rv.append("round_started", ctx.now, {
        "review_id": rv.id, "round": nr, "document": st["document"], "source_sha256": table["source_sha256"],
        "units_sha256": R.sha256_file(rv.units_path(nr)), "config": st["rounds"][r]["config"],
        "config_sha256": st["rounds"][r]["config_sha256"],
        "slots": [{"slot_id": s, "model": slots[s]["model"]} for s in sorted(slots, key=R._slot_order)],
        "author": st["author"], "carry_forward": plan, "removed_findings": removed})
    ctx.observe()
    return {"status": "ok", "round": nr, "mapping": {k: len(v) for k, v in mapping.items()},
            "carry_forward": sum(len(v) for v in plan.values()), "removed_findings": removed}


def cmd_escalate(ctx: Ctx) -> dict:
    _, st, act = ctx.decide()
    _require(act, "escalate")
    ctx.rv.append("escalated", ctx.now, {"items": act["items"], "reason": ctx.args.reason, "row": act["row"]})
    return {"status": "ok", "items": act["items"], "next": "run next: it asks for report, then waits for resolve"}


def write_report(ctx: Ctx, closing: bool = False) -> str:
    events = ctx.rv.events()
    text = REP.build(ctx.rv, events)
    if closing:
        text = text.replace("- State: open", "- State: closed", 1)
    (ctx.rv.dir / "report.md").write_text(text, encoding="utf-8")
    return R.sha256_bytes(text.encode("utf-8"))


def cmd_report(ctx: Ctx) -> dict:
    _, _, problems = ctx.state()
    if problems:
        raise ReviewError(problems[0])
    sha = write_report(ctx)
    ctx.rv.append("reported", ctx.now, {"report_sha256": sha})
    return {"status": "ok", "report": str(ctx.rv.dir / "report.md"), "report_sha256": sha,
            "note": "Attach report.md unchanged. report does not close the review."}


def cmd_close(ctx: Ctx) -> dict:
    _, st, act = ctx.decide()
    _require(act, "close")
    rv = ctx.rv
    r = st["round"]
    text = OBS.read_doc(ctx.project / st["document"])
    chg, rem = OBS.changed_removed(rv, st, text)
    edited = set(chg) | set(rem)
    reverted = sorted(g for g, f in st["findings"].items() if f["state"] == "changed" and f["changed_round"] == r
                      and not set(f["disposals"][-1]["finding_units"]) & edited)
    if reverted:
        for g in reverted:
            rv.append("change_reverted", ctx.now, {"finding": g})
        return {"status": "reverted", "change_reverted": reverted,
                "next": "run next: the reverted findings go back to dispose"}
    sha = write_report(ctx, closing=True)
    rv.append("closed", ctx.now, {"report_sha256": sha, "document_sha256": R.sha256_bytes(text.encode("utf-8"))})
    return {"status": "ok", "closed": True, "report": str(rv.dir / "report.md"), "report_sha256": sha}


def cmd_resolve(ctx: Ctx) -> dict:
    a = ctx.args
    _, st, problems = ctx.state()
    if problems:
        raise ReviewError(problems[0])
    snap = R.snapshot(st)
    pending = (snap["escalation"] or {}).get("pending", [])
    if a.item not in pending:
        raise ReviewError(f"{a.item} is not an escalated item awaiting a human (pending: {pending})")
    kind = a.item.split(":", 1)[0] if ":" in a.item else a.item
    if kind == "item":
        kind = "item-" + st["items"][a.item.split(":", 1)[1]]["type"]
    allowed = R.HUMAN_DECISIONS[kind]
    if a.decision not in allowed:
        raise ReviewError(f"decision for {a.item} must be one of {list(allowed)}")
    ctx.rv.append("human_resolved", ctx.now, {"item": a.item, "by": a.by, "decision": a.decision, "reason": a.reason})
    return {"status": "ok", "item": a.item, "decision": a.decision}


def cmd_repair(ctx: Ctx) -> dict:
    code = ctx.args.code
    if code not in FIX:
        raise ReviewError(f"unknown repair code {code}; known: {sorted(FIX)}")
    _, st, problems = ctx.state()
    obs = (st or {}).get("observed") or {}
    detail = {"config_out_of_range": obs.get("config_problems"),
              "shared_dir_contamination": (obs.get("shared_dirs") or {}).get("contaminated"),
              "change_without_edit": OBS.unedited_changes(st) if st else None}.get(code)
    return {"status": "ok", "code": code, "fix": FIX[code], "detail": detail,
            "next": "fix it, then run next: observe confirms the fix"}


COMMANDS = {"start": cmd_start, "next": cmd_next, "dispatch": cmd_dispatch, "returned": cmd_returned,
            "receive": cmd_receive, "withdraw": cmd_withdraw, "dispose": cmd_dispose, "arbitrate": cmd_arbitrate,
            "rereview": cmd_rereview, "escalate": cmd_escalate, "report": cmd_report, "close": cmd_close,
            "resolve": cmd_resolve, "repair": cmd_repair}


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", default=".", help="project root (default: current folder)")
    common.add_argument("--review", help="review id (default: the only open review)")
    common.add_argument("--now", help="time of this command, YYYY-MM-DDTHH:MM:SSZ (default: the clock)")
    common.add_argument("--observation", help="JSON file with fixed host facts (reproducible runs)")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], epilog=__doc__.split("\n\n", 1)[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("start", parents=[common])
    p.add_argument("doc")
    p.add_argument("--supersede")
    p.add_argument("--reason")
    p.add_argument("--seed")
    p.add_argument("--author", default="author-agent")
    p.add_argument("--author-model", default="unspecified")
    p.add_argument("--models", help="models for a new review-config.json, comma-separated")
    for name in ("next", "arbitrate", "rereview", "report", "close"):
        sub.add_parser(name, parents=[common])
    for name in ("dispatch", "returned", "receive"):
        sub.add_parser(name, parents=[common]).add_argument("slot")
    p = sub.add_parser("withdraw", parents=[common])
    p.add_argument("slot")
    p.add_argument("--reason", required=True, choices=("timeout", "host-failure", "isolation-failure", "other"))
    p.add_argument("--explanation")
    p = sub.add_parser("dispose", parents=[common])
    p.add_argument("finding")
    p.add_argument("--as", dest="as_", required=True, choices=("changed", "partially-changed", "declined", "unresolved"))
    p.add_argument("--reason", required=True)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--verified", metavar="EVID")
    g.add_argument("--adopted-unverified", action="store_true")
    p.add_argument("--by", default="author-agent")
    p = sub.add_parser("escalate", parents=[common])
    p.add_argument("--reason", required=True)
    p = sub.add_parser("resolve", parents=[common])
    p.add_argument("item")
    p.add_argument("--by", required=True)
    p.add_argument("--decision", required=True)
    p.add_argument("--reason", required=True)
    p = sub.add_parser("repair", parents=[common])
    p.add_argument("code")
    return ap


def main(argv=None) -> int:
    try:
        args = parser().parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        out = COMMANDS[args.cmd](Ctx(args))
    except ReviewError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 2
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        return 2
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return {"ok": 0, "rejected": 1, "reverted": 1, "error": 1}.get(out["status"], 0)


if __name__ == "__main__":
    sys.exit(main())
