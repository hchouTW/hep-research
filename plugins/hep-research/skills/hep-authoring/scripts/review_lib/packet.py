"""Packets and the instruction-file generator (spec section 5.2).

instructions.md is assembled from contracts/schemas/review_record.json (field names, enums, required fields and
descriptions, the evidence-basis table), the configuration and the slot role; only the task paragraph comes from the
lens table. The output example is then extracted from the instructions.md actually written and checked with the same
rules as check --record-only; the build stops when it fails.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from contracts.review import ALLOWED_CONCLUSIONS, ROLE_REQUIRED, record_rules
from contracts.schema import load_schema
from review_lib.store import ReviewError, dumps

PLUGIN = Path(__file__).resolve().parents[4]
EXAMPLE_HEAD = "## Output example"
BASIS_ORDER = ("locator", "third-party", "tool-output", "exhaustive", "person", "internal")
SUBTABLES = {"reviewer": ("path_read", "skim_mark", "claim", "verdict", "refutation_attempt", "carry_item", "finding", "output_file"),
             "arbiter": ("path_read", "resolve", "output_file")}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _enum_text(node: dict) -> str:
    if "enum" in node:
        return " (one of: " + ", ".join(f"`{x}`" for x in node["enum"]) + ")"
    return ""


def _fields_table(obj: dict, required, extra_required=()) -> list[str]:
    rows = ["| Field | Required | How to fill it |", "|---|---|---|"]
    for name, node in obj.get("properties", {}).items():
        req = "yes" if name in required or name in extra_required else "no"
        desc = node.get("description", "")
        if "$ref" in node and not desc:
            desc = _resolve(node["$ref"]).get("description", "")
        rows.append(f"| `{name}` | {req} | {desc}{_enum_text(node)} |")
    return rows


def _resolve(ref: str) -> dict:
    schema = load_schema("review_record.json")
    if ref.startswith("#/$defs/"):
        return schema["$defs"][ref.split("/")[-1]]
    return {}


def basis_table() -> list[str]:
    """The evidence-basis table, in full, from the schema's evidence_* definitions."""
    defs = load_schema("review_record.json")["$defs"]
    rows = ["| basis | Required fields | Counts as external / independent, and rules |", "|---|---|---|"]
    for b in BASIS_ORDER:
        d = defs["evidence_" + b.replace("-", "_")]
        req = ", ".join(f"`{x}`" for x in d["required"] if x not in ("id", "basis"))
        rows.append(f"| `{b}` | {req} | {d['description']} |")
    return rows


def _rules(kind: str, lens: str, scope: dict) -> list[str]:
    t = scope
    if kind == "arbiter":
        return [
            "- Your record is rejected (`schema_invalid`) unless it follows the schema above; also when `packet_sha256`, "
            "`dispatch_nonce` or `instructions_sha256` differ from the dispatch (`packet_mismatch`, `dispatch_mismatch`).",
            "- `prior_conversation`: you report having seen a prior conversation. `arbiter_identity`: your identity is the "
            "author's or a reviewer's under arbitration.",
            "- `read_outside_packet`, `file_hash_mismatch`, `output_mismatch`, `instructions_changed`: see the read rules.",
            "- `resolves_incomplete`: `resolves` must hold exactly one conclusion for every item in items.json.",
            "- `resolution_type`: a decline item allows `" + "`, `".join(ALLOWED_CONCLUSIONS["decline"]) + "`; a conflict item "
            "allows `" + "`, `".join(ALLOWED_CONCLUSIONS["conflict"]) + "`. `uphold-first` keeps the verdict listed first.",
            "- `resolution_basis`: a conclusion other than `unresolved` needs evidence; external evidence when any lens of the "
            "item is not design or bypass (`lenses` in items.json).",
        ]
    deep = "deep and focus units" if t["focus_units"] else "deep units"
    strict = lens not in ("design", "bypass")
    out = [
        "- `schema_invalid`, `packet_mismatch`, `dispatch_mismatch`, `prior_conversation`, `same_identity` (your identity "
        "must differ from the author's), `read_outside_packet`, `file_hash_mismatch`, `output_mismatch`, "
        "`instructions_changed`: see the fields and read rules above.",
        f"- `claim_shape`: each claim cites 1 to {t['max_units_per_claim']} contiguous units of units.json and has exactly "
        "one verdict.",
        f"- `finding_shape`: each finding cites 1 to {t['max_units_per_claim']} contiguous units, and its `value` is an exact "
        "excerpt of those units' text as given in units.json.",
        f"- `deep_missing`: every one of the {deep} in scope.json is covered by at least one claim.",
        f"- `skim_missing`: every skim unit has a mark; every `issue` names a finding; at most a share of "
        f"{t['na_max_ratio']} of the skim units may be `n/a`.",
        "- `basis_missing`: every verdict on a " + deep.split(" and ")[0] + " that is not `unresolved` cites "
        + ("external evidence (any basis except `internal`)" if strict else "at least one evidence item") + ".",
        "- `self_citation`: `internal` evidence never cites the claim's own units or any unit within two positions of them; "
        "a refutation attempt never targets the claim's own unit.",
        "- `refutation_weak`: every `supported` verdict has at least one refutation attempt with a non-empty target. When the "
        f"refutation attempts on your {deep} total {t['refutation_min_attempts_effective']} or more (min(configured value, "
        f"number of {deep}), at least 3), at most a share of {t['refutation_duplicate_max']} of them may repeat a "
        "(method, target) pair.",
        "- `verdict_without_finding`: a `partially-supported` or `unsupported` verdict lists at least one finding.",
        f"- `unresolved_dominant`: at most a share of {t['unresolved_max_ratio']} of your {deep} may have only "
        "`unresolved` verdicts. Not found does not mean does not exist: fetch tools may truncate or summarise.",
    ]
    if t.get("carry_forward"):
        out.append("- `carry_forward_missing`: every item in `carry_forward` of scope.json gets an entry with `confirmed` "
                   "(and evidence ids) or `reopened`. A reopened item is judged again by a claim in this round; a verdict "
                   "that is not supported carries a finding.")
    return out


def example_record(kind: str, slot_id: str) -> dict:
    """The output example of a role; it passes check --record-only for that role."""
    h = "0123456789abcdef" * 4
    base = {"packet_sha256": h, "dispatch_nonce": "n0nce-from-dispatch-line", "instructions_sha256": h,
            "role": "arbiter" if kind == "arbiter" else "reviewer",
            "reviewer": {"identity": "reviewer-agent-7", "context": "fresh", "model": "model-name", "host": "claude-code",
                         "slot_id": slot_id},
            "isolation": {"saw_prior_conversation": False, "host_injected": ["memory file"], "instruction_files_seen": "unknown"},
            "paths_read": [{"path": "packet/document.md", "sha256": h}, {"path": "packet/units.json", "sha256": h}],
            "evidence": [{"id": "E1", "basis": "locator", "ref": "docs/maintenance.md", "lines": "118-126", "sha256": h,
                          "source_kind": "page"},
                         {"id": "E2", "basis": "internal", "units": ["U0009"]}],
            "limitations": "Did not run the scripts; URLs not fetched."}
    if kind == "arbiter":
        base["resolves"] = [{"item_id": "A1.1", "conclusion": "uphold-finding", "rationale": "The cited file says 126, not 135.",
                             "evidence_ids": ["E1"]}]
        return base
    base.update({
        "skim": [{"unit": "U0002", "mark": "ok"}, {"unit": "U0004", "mark": "issue", "finding_id": "F1"},
                 {"unit": "U0005", "mark": "n/a"}],
        "claims": [{"id": "C1", "units": ["U0002"], "summary": "The evidence bases follow docs/maintenance.md."},
                   {"id": "C2", "units": ["U0004"], "summary": "The cited lines define the locator basis."}],
        "verdicts": [{"claim_id": "C1", "verdict": "supported", "rationale": "Lines 118-126 define the bases as stated.",
                      "evidence_ids": ["E1"], "finding_ids": [],
                      "refutation_attempts": [{"method": "read the cited range for a contradicting definition",
                                               "target": "docs/maintenance.md:118-126", "outcome": "none found"}]},
                     {"claim_id": "C2", "verdict": "unsupported", "rationale": "The definition is on lines 120-121, not 130.",
                      "evidence_ids": ["E1", "E2"], "finding_ids": ["F1"], "refutation_attempts": []}],
        "findings": [{"id": "F1", "kind": "wrong-citation", "severity": "medium", "units": ["U0004"],
                      "value": "lines 130-131", "correction": "lines 120-121",
                      "description": "The cited range does not contain the locator definition.",
                      "fix": "Cite docs/maintenance.md:120-121."}],
        "carry_forward": []})
    return base


def render_instructions(*, kind: str, lens: str, lens_info: dict, scope: dict, review_id: str, round_: int,
                        attempt: int, plugin: Path = PLUGIN, example: dict | None = None) -> str:
    schema = load_schema("review_record.json")
    role = "arbiter" if kind == "arbiter" else "reviewer"
    max_units = scope["max_units_per_claim"]
    lines = [f"# Review instructions: slot {scope['slot_id']}", "",
             f"Review packet {review_id}, round {round_}, attempt {attempt}. Role: `{role}`.", ""]
    lines += ["## R0 isolation self-check", "",
              "Before anything else: if any earlier conversation is visible to you, set "
              "`isolation.saw_prior_conversation` to true, write the record and stop. Record the categories of content the "
              "host added to your context in `isolation.host_injected`, and the instruction files you can see in "
              "`isolation.instruction_files_seen` (or `unknown`).", ""]
    lines += ["## Read rules and working directory", "",
              "- This file is in your packet folder. Its parent is your attempt folder; `work/` there is your only "
              "working directory. Write every file you create (fetched copies, script outputs, scripts) in `work/`.",
              "- Read the packet files freely. You may read files of the hep-research plugin and public web pages as "
              "evidence; save a copy of every fetched page in `work/` and record its URL.",
              "- Never read: the original delivered document (review the packet's document.md), the private review "
              "directory, the review event log, other slots' or other attempts' folders, the author's traceability "
              "records, or the mechanism's implementation files (skills/hep-authoring/scripts/review*.py, "
              "skills/hep-authoring/scripts/review_lib/, skills/hep-authoring/assets/review-lenses.json, "
              "skills/hep-authoring/assets/review-hosts.json, contracts/review.py). Files in a host shared directory that "
              "existed before your attempt started are also forbidden; tool outputs the host saved during your attempt "
              "may be read, but copy them into `work/` before you cite them.",
              "- List every local file you read in `paths_read` with the sha256 of the whole file (`sha256sum FILE`).",
              ""]
    if kind == "arbiter":
        lines += ["## Your task", "",
                  "items.json lists the arbitration items. For a conflict, it gives both verdicts in full (first, then "
                  "second); for a decline, the finding and the author's reason. Decide each item from evidence and write "
                  "exactly one entry in `resolves` per item.", ""]
    else:
        lines += ["## Your task", "", lens_info.get("task", ""), "",
                  "- **Skim**: mark every unit in `skim_units` of scope.json as `ok`, `issue` or `n/a`; every `issue` "
                  "maps to a finding.",
                  "- **Deep**: cover every unit in `deep_units` and `focus_units` with claims (1 to "
                  f"{max_units} contiguous units each), give each claim exactly one verdict with evidence and "
                  "refutation attempts, and write a finding for every problem.",
                  "- **Findings**: `value` gives the text you challenge, copied exactly from the units' text in "
                  "units.json; `correction` gives what you believe is right.", ""]
        if scope.get("carry_forward"):
            lines += ["- **Re-review**: scope.json lists `carry_forward` items from the previous round, each with its "
                      "units and earlier text. Mark each one `confirmed` (with evidence ids) or `reopened`.", ""]
    lines += ["## Output: review_record.json", "",
              "Write the record as JSON to `review_record.json.tmp` in your attempt folder, check it with",
              "", "```", f"python3 {plugin / 'contracts' / 'review.py'} check --record-only review_record.json.tmp "
              f"--role {role} --max-units-per-claim {max_units}", "```", "",
              "and rename it to `review_record.json` only after the check passes. Fields marked self-reported cannot be "
              "verified by the script.", ""]
    req = set(schema["required"])
    props = {k: v for k, v in schema["properties"].items()
             if not (role == "arbiter" and k in ("skim", "claims", "verdicts", "findings", "carry_forward"))
             and not (role == "reviewer" and k == "resolves")}
    lines += ["### Fields", ""] + _fields_table({"properties": props}, req, ROLE_REQUIRED[role]) + [""]
    for sub in ("reviewer", "isolation"):
        lines += [f"### `{sub}`", ""] + _fields_table(schema["properties"][sub], schema["properties"][sub]["required"]) + [""]
    for name in SUBTABLES[role]:
        d = schema["$defs"][name]
        lines += [f"### `{name}` entries", ""] + _fields_table(d, d.get("required", [])) + [""]
    lines += ["### Evidence bases", "",
              "Each evidence item has an `id`, a `basis` and that basis's required fields:", ""] + basis_table() + [""]
    lines += ["## Quality rules for this slot", ""] + _rules(kind, lens, scope) + [""]
    ex = example if example is not None else example_record(kind, scope["slot_id"])
    lines += [EXAMPLE_HEAD, "", "Unit ids, paths and hashes below are placeholders; use the ones of your packet.", "",
              "```json", json.dumps(ex, indent=1, ensure_ascii=False), "```", ""]
    return "\n".join(lines)


def extract_example(text: str):
    """The JSON example after the output-example heading of an instructions.md."""
    part = text.split(EXAMPLE_HEAD, 1)
    if len(part) != 2:
        raise ValueError("no output example heading")
    m = re.search(r"```json\n(.*?)\n```", part[1], re.S)
    if not m:
        raise ValueError("no JSON block after the output example heading")
    return json.loads(m.group(1))


def validate_written_example(path: Path, role: str, max_units: int) -> None:
    """Build-time check of the example in the instructions.md actually written; raises ReviewError on failure."""
    try:
        ex = extract_example(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ReviewError(f"generated instructions: the output example cannot be read ({exc})") from exc
    probs = record_rules(ex, role, max_units)
    if probs:
        raise ReviewError(f"generated instructions: the output example fails check --record-only: {probs[0]}")


def write_packet(pdir: Path, *, slot_id: str, document: str, units: list[dict], scope: dict, items: list | None,
                 instructions: str) -> dict:
    """Write the packet files and manifest.json; return {packet_sha256, instructions_sha256}."""
    pdir.mkdir(parents=True, exist_ok=True)
    files = {"document.md": document, "units.json": dumps({"slot_id": slot_id, "units": units}),
             "scope.json": dumps(scope), "instructions.md": instructions}
    if items is not None:
        files["items.json"] = dumps({"items": items})
    entries = []
    for name in sorted(files):
        data = files[name].encode("utf-8")
        (pdir / name).write_bytes(data)
        entries.append({"name": name, "size": len(data), "sha256": sha256_bytes(data)})
    man = dumps({"manifest_version": "1.0.0", "slot_id": slot_id, "files": entries}).encode("utf-8")
    (pdir / "manifest.json").write_bytes(man)
    return {"packet_sha256": sha256_bytes(man), "instructions_sha256": sha256_bytes(files["instructions.md"].encode("utf-8"))}


def packet_document(text: str, slot_id: str) -> str:
    """The slot's copy of the document, with a header line, so its hash never equals the delivered document's."""
    return f"<!-- review packet copy for slot {slot_id}; units are listed in units.json -->\n\n{text}"


def packet_units(units: list[dict], lens: str | None, texts: dict, roles: dict) -> list[dict]:
    """units.json entries restricted to the allow-list (spec 5.2): no hashes, scope for this slot's lens only."""
    return [{"id": u["id"], "section": u["section"], "kind": u["kind"], "text": texts.get(u["id"], u["text"]),
             "substantive": u["substantive"], "in_scope": bool(u["in_scope"].get(lens, False)) if lens else False,
             "role": roles.get(u["id"])} for u in units]


def dispatch_message(nonce: str, instructions_path: Path, sha: str) -> str:
    return ("Read and follow the instruction file below exactly.\n"
            f"REVIEW-DISPATCH nonce={nonce} instructions={instructions_path} sha256={sha}")
