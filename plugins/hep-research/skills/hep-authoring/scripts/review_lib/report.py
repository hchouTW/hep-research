"""report.md (spec A8): generated from the event log, the private canary files and the configuration; the author
agent attaches it unchanged. Deterministic: the same files give the same bytes."""
from __future__ import annotations

from contracts.review import CONFIG_RULES, effective_config, filter_pool, fold, slot_state, weak_config
from review_lib.store import read_json

LIMITATIONS = [
    "Guards against negligence and laziness only; deliberate fraud by the author agent is out of scope (spec 0, 10).",
    "Canaries and sampling measure only a lower bound; a canary hit may be a false hit (see the exact-correction rate).",
    "P1 has facts and design canaries only: sources and bypass slots run without quality control (no_control).",
    "Isolation preconditions confirm setting values and times, not how a running session behaves.",
    "Reviewer identity is self-reported; same_identity and arbiter_identity catch only identical names.",
    "Refutation attempts are checked only for empty targets and repeated (method, target) pairs.",
    "tool-output evidence is not checked for relevance; locators only for being read with location and hash.",
    "Shared-directory files written during an attempt window are attributed to the reviewer; parallel slots cannot be told apart.",
    "A closed agent review is not a review record by a non-author reviewer (v6.3 O04/O14; maintainer decision "
    "2026-10-21): the author agent could forge it (spec 10). It is advisory input a human reviewer may cite.",
]


def _pct(a, b):
    return f"{a}/{b} ({100.0 * a / b:.0f}%)" if b else "0/0"


def build(rv, events: list) -> str:
    st = fold(events)
    slots_priv = rv.slots()
    first = st["rounds"][min(st["rounds"])]
    cfg = st["rounds"][st["round"]]["config"]
    eff = effective_config(cfg)
    out = [f"# Independent review report: {st['review_id']}", "",
           f"- Document: `{st['document']}`", f"- Rounds: {st['round']}", f"- State: {st['terminal'] or 'open'}",
           f"- Author: {first['author'].get('identity')} (model {first['author'].get('model')})", ""]
    out += ["## Configuration used", "", "| Setting | Value | Default |", "|---|---|---|"]
    out.append(f"| models | {', '.join(eff['models'])} | required |")
    for k, (default, *_r) in CONFIG_RULES.items():
        out.append(f"| {k} | {eff[k]} | {default} |")
    out.append(f"| extra_lenses | {', '.join(eff.get('extra_lenses') or []) or '-'} | - |")
    if eff.get("lens_models"):
        out.append("| lens_models | " + ", ".join(f"{k}={v}" for k, v in sorted(eff["lens_models"].items())) + " | - |")
    if eff.get("filter"):
        out.append(f"| filter | model {eff['filter']['model']} | - |")
    weak = weak_config(cfg)
    out += ["", f"weak_config: {', '.join(weak) if weak else 'none'}", ""]
    out += ["## Slots", "", "| Round | Slot | Role | Lens | Model | Attempts | Outcome | Reasons | Skim marks | "
            "Deep verdicts | Partially supported | Bases (independent / external / tool-output / internal) |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    dispatched_total = 0
    hits = {"skim": [0, 0], "deep": [0, 0]}
    exact = [0, 0]
    shortfall, nocontrol, returned_empty = [], [], []
    for (r, sid), atts in sorted(st["attempts"].items(), key=lambda x: (x[0][0], _num(x[0][1]))):
        info = slots_priv.get(str(r), {}).get(sid, {})
        dispatched_total += len(atts)
        last = atts[max(atts)]
        reasons = []
        for k in sorted(atts):
            a = atts[k]
            if a["outcome"] == "rejected":
                reasons.append(f"a{k}: rejected {', '.join(a['data']['codes'])}")
            elif a["outcome"] == "withdrawn":
                reasons.append(f"a{k}: withdrawn ({a['data']['reason']})")
            if a["returned"] and a["outcome"] == "withdrawn" and a["data"]["reason"] == "host-failure":
                returned_empty.append(f"{r}/{sid}/{k}")
        m = (last["data"] or {}).get("metrics", {}) if last["outcome"] == "accepted" else {}
        b = m.get("bases", {})
        out.append(f"| {r} | {sid} | {info.get('role', '?')} | {info.get('lens') or '-'} | {info.get('model', '?')} | "
                   f"{len(atts)} | {last['outcome'] or 'open'} | {'; '.join(reasons) or '-'} | "
                   f"{_dist(m.get('skim'))} | {_dist(m.get('deep_verdicts'))} | {m.get('partially_supported_share', '-')} | "
                   f"{b.get('independent', 0)} / {b.get('external', 0)} / {b.get('tool-output', 0)} / {b.get('internal', 0)} |")
        for c in m.get("canaries", []):
            hits[c["place"]][1] += 1
            hits[c["place"]][0] += int(c["hit"])
            if c["hit"]:
                exact[1] += 1
                exact[0] += int(c["exact"])
        d = last["dispatched"]
        if d["canaries_expected"]:
            (nocontrol if d["canaries"] == 0 else shortfall if d["canaries"] < d["canaries_expected"] else []).append(f"{r}/{sid}")
    out += ["", f"Agents dispatched: {dispatched_total}.", ""]
    for r in sorted(st["rounds"]):
        sp = rv.private / f"round-{r}" / "sample.json"
        sample = read_json(sp) if sp.exists() else {}
        for lens, why in sorted((sample.get("no_slot") or {}).items()):
            out.append(f"- Round {r}, lens {lens}: {why}.")
        if sample.get("copies"):
            out.append(f"- Round {r}: copies or versions of the document were readable by reviewers (a record citing "
                       f"one is rejected): {', '.join(sample['copies'])}.")
    out.append("")
    out += ["## Canaries", "", f"- Hit rate (skim): {_pct(*hits['skim'])}", f"- Hit rate (deep): {_pct(*hits['deep'])}",
            f"- Exact-correction rate: {_pct(*exact)}",
            f"- canary_shortfall: {', '.join(shortfall) or 'none'}",
            f"- no_control (no quality control): {', '.join(nocontrol) or 'none'}", "", "Witnesses:", ""]
    for p in sorted(rv.private.glob("round-*/*/attempt-*/canary.json")):
        for c in read_json(p).get("canaries", []):
            rel = p.parent.relative_to(rv.private).as_posix()
            out.append(f"- {rel} {c['unit']} ({c['type']}): original right: {_w(c['witness_right'])}; "
                       f"new wrong: {_w(c['witness_wrong'])}")
    out += ["", "## Shadow review", ""]
    for (r, sid), atts in sorted(st["attempts"].items(), key=lambda x: (x[0][0], _num(x[0][1]))):
        info = slots_priv.get(str(r), {}).get(sid, {})
        if info.get("role") == "shadow":
            last = atts[max(atts)]
            m = (last["data"] or {}).get("metrics", {}) if last["outcome"] == "accepted" else {}
            out.append(f"- round {r} {sid} (shadow of {info.get('lens')}): {last['outcome'] or 'open'}, "
                       f"deep verdicts {_dist(m.get('deep_verdicts'))}")
    decisions = {d["finding"]: d for d in ((st.get("filter") or {}).get("decisions") or [])}
    if eff.get("filter"):
        out += ["", "## Filtering pass", ""] + _filter_lines(st, decisions)
    if not decisions:
        out += ["", "## Findings", "", "| Finding | Severity | State | Disposition | Verification |", "|---|---|---|---|---|"]
        for g, f in sorted(st["findings"].items()):
            out.append(f"| {g} | {f['severity']} | {f['state']} | {_disp(f)} |")
    else:  # kept (and unfiltered) findings first; the dropped ones apart, with the filter's reasons; nothing is deleted
        out += ["", "## Findings", "", "Findings the filtering pass kept, then findings it did not judge (controls, later "
                "rounds).", "", "| Finding | Severity | State | Disposition | Verification | Filter |", "|---|---|---|---|---|---|"]
        kept = [g for g in sorted(st["findings"]) if decisions.get(g, {}).get("decision") == "keep"]
        rest = [g for g in sorted(st["findings"]) if g not in decisions]
        for g in kept + rest:
            f = st["findings"][g]
            why = f"keep: {_cell(decisions[g]['reason'])}" if g in decisions else "-"
            out.append(f"| {g} | {f['severity']} | {f['state']} | {_disp(f)} | {why} |")
        out += ["", "## Findings the filter dropped", "",
                "Advice, not a disposition: each is still disposed by the author like any other finding.", "",
                "| Finding | Severity | State | Disposition | Verification | Reason | Duplicate of |",
                "|---|---|---|---|---|---|---|"]
        for g in sorted(x for x, d in decisions.items() if d["decision"] == "drop"):
            f = st["findings"].get(g, {"severity": "?", "state": "?", "disposals": []})
            d = decisions[g]
            out.append(f"| {g} | {f['severity']} | {f['state']} | {_disp(f)} | {_cell(d['reason'])} | "
                       f"{d.get('duplicate_of') or '-'} |")
    out += ["", "## Events", ""]
    for e in events:
        if e["event"] in ("arbitration_resolved", "change_reverted", "change_confirmed", "change_rejected", "late",
                          "escalated", "human_resolved", "superseded"):
            out.append(f"- {e['time']} {e['event']}: {_brief(e['data'])}")
    out += [f"- returned-empty: {', '.join(returned_empty) or 'none'}", ""]
    obs = st["observed"] or {}
    host = obs.get("host", {})
    out += ["## Host checks", "", f"- Isolation precondition: {host.get('precondition')}",
            f"- Session start time: {host.get('session_start') or 'not obtainable'}",
            f"- Instruction files recorded: {len(obs.get('instruction_files', {}))}",
            f"- Shared directories checked: {len(obs.get('shared_dirs', {}).get('checked', []))}; "
            f"contaminated: {len(obs.get('shared_dirs', {}).get('contaminated', []))}",
            "- Tool outputs the host saved during attempts: " + (", ".join(obs.get("shared_dirs", {}).get("in_window", [])) or "none"),
            "- Warnings: " + ("; ".join(obs.get("warnings", [])) or "none")]
    cats = sorted({c for (r, s), atts in st["attempts"].items() for a in atts.values()
                   for c in ((a["data"] or {}).get("host_injected") or [])})
    out += [f"- Host-injected content categories: {', '.join(cats) or 'none reported'}", ""]
    others = sorted(p.name for p in rv.dir.parent.iterdir() if p.is_dir() and p.name != rv.id
                    and (p / "review_log.jsonl").is_file() and _doc_of(p) == st["document"])
    out += ["## Reviews of this document", "", f"- {st['review_id']} (this review)"] + [f"- {x}" for x in others] + [""]
    out += ["## Limitations that applied", ""] + [f"- {x}" for x in LIMITATIONS] + [""]
    return "\n".join(out)


def _disp(f) -> str:
    d = f["disposals"][-1] if f["disposals"] else {}
    ver = d.get("verification") or {}
    vtext = "verified: " + ver["verified"] if ver.get("verified") else "adopted-unverified" if ver.get("adopted_unverified") else "-"
    return f"{d.get('disposition', '-')} | {vtext}"


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def _filter_lines(st: dict, decisions: dict) -> list[str]:
    """What happened to the filtering pass (spec 6.9, A8)."""
    f = st.get("filter")
    if f is None:
        return ["- Not run: no accepted round-1 finding to judge." if not filter_pool(st) else "- Pending."]
    r, sid = f["round"], f["slot_id"]
    atts = st["attempts"].get((r, sid), {})
    head = f"- Slot {sid}, model {f['model']}: {len(f['findings'])} findings, {len(atts)} attempt(s)."
    reasons = []
    for k in sorted(atts):
        a = atts[k]
        if a["outcome"] == "rejected":
            reasons.append(f"a{k}: rejected {', '.join(a['data']['codes'])}")
        elif a["outcome"] == "withdrawn":
            reasons.append(f"a{k}: withdrawn ({a['data']['reason']})")
    out = [head]
    if reasons:
        out.append("- " + "; ".join(reasons) + ".")
    if decisions:
        kept = sum(1 for d in decisions.values() if d["decision"] == "keep")
        out.append(f"- Applied: kept {kept}, dropped {len(decisions) - kept}. Dropped findings are listed apart below "
                   "with their reasons; nothing is deleted.")
    elif slot_state(st, r, sid)["state"] == "exhausted":
        out.append("- Not applied: the filter slot used up its attempts; the findings below are unfiltered.")
    else:
        out.append("- Not applied yet.")
    return out


def _doc_of(p):
    import json
    try:
        return json.loads((p / "review_log.jsonl").read_text(encoding="utf-8").split("\n", 1)[0])["data"]["document"]
    except (OSError, ValueError, KeyError):
        return None


def _num(sid):
    return int(sid[1:]) if sid[1:].isdigit() else 0


def _dist(d):
    return ", ".join(f"{k} {v}" for k, v in sorted((d or {}).items())) or "-"


def _w(w):
    return ", ".join(f"{k}={v}" for k, v in sorted(w.items()) if k != "content") if w else "-"


def _brief(d):
    keys = ("finding", "item_id", "conclusion", "item", "decision", "items", "slot_id", "attempt", "reason", "by")
    return ", ".join(f"{k}={d[k]}" for k in keys if k in d)
