#!/usr/bin/env python3
"""Sourced detector atlas: validate, render, query and audit (D13).

Purpose: answer questions about large experiments' detectors only from sourced ledger claims, never from memory. An
atlas is an evidence ledger (evidence/sources.json, evidence/claims.json) whose claims carry an `atlas` block:
experiment, subsystem, quantity, value (as written in the source), unit, kind (design, achieved or operating),
valid_for (the configuration) and conditions. The plugin atlas is the reference profile in
<plugin root>/profiles/reference/detector-atlas/; a user atlas is any folder with the same evidence files. See
"Detector design principles" in <plugin root>/skills/hep-detector/references/detector-design-principles.md.

Subcommands:
  validate [--atlas DIR] [--release] [--today YYYY-MM-DD]
      core/evidence/ledger.py on the atlas, then the atlas block of every claim. --release also fails on the ledger's
      warnings and on its stale-date notes (stale.source, stale.claim), which the ledger reports as notes only.
  render [--atlas DIR] [--experiment NAME] [--out FILE]
      Markdown pages per experiment and subsystem: every number in a row carries its claim id.
  query [--project DIR] [--user-atlas DIR ...] [--atlas DIR] [--experiment] [--subsystem] [--quantity] [--kind]
        [--text] [--page N]
      Matching claims in order: the experiment profiles a project binds (claims with an atlas block), then the user
      atlases (labelled user-supplied), then the plugin atlas. Filters match whole words, case-insensitively. Pages hold at
      most 20 rows and 16 KiB, like core/evidence/query.py. No match: answer "unknown" (with the profile to read when
      the experiment has its own profile, from the atlas's evidence/links.json); never a value from memory.
  audit FILE [--strict]
      Numbers with a unit in a text file that carry no atlas claim id on the same line; --strict fails on any.
Every subcommand takes --status LABEL (default unvalidated), echoed as status_label.
Output JSON: status (ok, failed, rejected), status_label, inputs, defaults_used and the results.
Exit codes: 0 ok; 1 validation failed (or unsourced numbers with --strict); 2 unreadable input or bad arguments.
Standard library only.
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))  # the plugin root
from core.evidence import ledger as vel  # noqa: E402
from core.status import add_status_argument, exit_code  # noqa: E402

PLUGIN_ATLAS = PLUGIN / "profiles" / "reference" / "detector-atlas"
FIELDS = ("experiment", "subsystem", "quantity", "value", "unit", "kind", "valid_for", "conditions")
KINDS = ("design", "achieved", "operating")
PAGE_ROWS, PAGE_BYTES = 20, 16384  # as core/evidence/query.py
UNIT_NUMBER = re.compile(r"(?<![\w.:-])(\d+(?:\.\d+)?(?:\s*[x×]\s*10\^?-?\d+)?)\s?(%|um|µm|mm|cm|m|km|ns|ps|us|µs|s|"
                         r"T|Tm|T m|GeV|MeV|keV|TeV|kHz|MHz|GHz|Hz|kt|t|X0|sr|deg|degrees?)(?![\w])")
CLAIM_ID = re.compile(r"\b[a-z][a-z0-9-]*:C\d{2,}\b")


class InputError(ValueError):
    """Unreadable input or bad arguments (status rejected, exit 2)."""


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"status": "rejected", "error": message}, indent=2))
        self.print_usage(sys.stderr)
        self.exit(exit_code("rejected"), f"{self.prog}: error: {message}\n")


def load_atlas(folder):
    folder = Path(folder)
    try:
        sources = json.loads((folder / "evidence" / "sources.json").read_text(encoding="utf-8"))
        claims = json.loads((folder / "evidence" / "claims.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read the atlas ledger in {folder}: {exc}") from None
    namespace = None
    pj = folder / "profile.json"
    if pj.is_file():
        try:
            namespace = json.loads(pj.read_text(encoding="utf-8")).get("evidence_namespace")
        except ValueError:
            namespace = None
    links_file = folder / "evidence" / "links.json"
    links = json.loads(links_file.read_text(encoding="utf-8")).get("links", []) if links_file.is_file() else []
    return {"dir": folder, "sources": sources, "claims": claims, "namespace": namespace, "links": links}


def atlas_errors(claims):
    out = []
    for c in claims:
        cid = c.get("id", "?")
        a = c.get("atlas")
        if not isinstance(a, dict):
            out.append({"claim": cid, "problem": "no atlas block"})
            continue
        missing = [k for k in FIELDS if k not in a]
        if missing:
            out.append({"claim": cid, "problem": f"atlas block lacks {missing}"})
        for k in ("experiment", "subsystem", "quantity", "value", "unit", "valid_for"):
            if k in a and not (isinstance(a[k], str) and a[k].strip()):
                out.append({"claim": cid, "problem": f"atlas.{k} must be a non-empty string"})
        if "kind" in a and a["kind"] not in KINDS:
            out.append({"claim": cid, "problem": f"atlas.kind {a['kind']!r} is not one of {list(KINDS)}"})
    return out


def _today(args):
    try:
        return date.fromisoformat(args.today) if args.today else date.today()
    except ValueError:
        raise InputError(f"--today {args.today!r} is not YYYY-MM-DD") from None


def validate(args, defaults):
    atlas = load_atlas(args.atlas or PLUGIN_ATLAS)
    if not args.atlas:
        defaults.append("atlas: the plugin atlas")
    if not args.today:
        defaults.append("today: the current date")
    rep = vel.check_ledger(atlas["sources"], atlas["claims"], _today(args), 365, atlas["namespace"])
    aerr = atlas_errors(atlas["claims"])
    blockers = (rep["warnings"] + [n for n in rep["notes"] if n["code"].startswith("stale.")]) if args.release else []
    ok = not rep["errors"] and not aerr and not blockers
    return ("ok" if ok else "failed"), {"claims": len(atlas["claims"]), "sources": len(atlas["sources"]),
                                         "ledger": {k: rep[k] for k in ("status", "errors", "warnings", "notes")},
                                         "atlas_errors": aerr, "release": bool(args.release),
                                         "release_blockers": blockers}


def _rows(atlas, origin, label):
    titles = {s["id"]: s for s in atlas["sources"]}
    out = []
    for c in atlas["claims"]:
        a = c.get("atlas")
        if not isinstance(a, dict):
            continue
        src = [titles.get(s, {}) for s in c.get("source_ids", [])]
        out.append({"claim_id": c["id"], **{k: a.get(k) for k in FIELDS}, "claim": c.get("claim"),
                    "location": c.get("location"), "source": "; ".join(s.get("title", "?") for s in src),
                    "source_ids": c.get("source_ids", []),
                    "read_level": c.get("verification_strength"), "origin": origin, "status_label": label})
    return out


def render(args, defaults):
    atlas = load_atlas(args.atlas or PLUGIN_ATLAS)
    rows = [r for r in _rows(atlas, "atlas", None)
            if not args.experiment or args.experiment.lower() in r["experiment"].lower()]
    lines, current = [], None
    for r in sorted(rows, key=lambda r: (r["experiment"], r["subsystem"], r["claim_id"])):
        if r["experiment"] != current:
            current = r["experiment"]
            lines += ["", f"## {current}", "", "| Subsystem | Quantity | Value | Unit | Kind | Valid for | Claim |",
                      "|---|---|---|---|---|---|---|"]
        cells = [r["subsystem"], r["quantity"], r["value"], r["unit"], r["kind"], r["valid_for"], r["claim_id"]]
        lines.append("| " + " | ".join(str(x).replace("|", "/") for x in cells) + " |")
    md = "# Detector atlas\n\nEvery value is a sourced claim; quote its claim id.\n" + "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    return "ok", {"rows": len(rows), "markdown": md if not args.out else None, "out": args.out}


def _bound_profile_dirs(project):
    from contracts.registry import load_registry  # imported here: only the query of a project needs it
    project = Path(project)
    try:
        cfg = json.loads((project / "hep-research.project.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read the project config in {project}: {exc}") from None
    local = [(project / p) for p in cfg.get("local_profile_paths", [])]
    loaded = load_registry(local_dirs=local).every_profile
    return [Path(loaded[b["profile"]]["_dir"]) for b in cfg.get("experiments", []) if b.get("profile") in loaded]


def _match(r, args):
    for key, want in (("experiment", args.experiment), ("subsystem", args.subsystem), ("quantity", args.quantity)):
        if want and not re.search(r"(?<![a-z0-9])" + re.escape(want.lower()) + r"(?![a-z0-9])", str(r[key]).lower()):
            return False
    if args.kind and r["kind"] != args.kind:
        return False
    if args.text and args.text.lower() not in json.dumps(r).lower():
        return False
    return True


def query(args, defaults):
    rows = []
    for d in (_bound_profile_dirs(args.project) if args.project else []):
        if (d / "evidence" / "claims.json").is_file():
            rows += _rows(load_atlas(d), "bound experiment profile", "public profile claim")
    for d in args.user_atlas or []:
        rows += _rows(load_atlas(d), "user atlas", "user-supplied")
    plugin = load_atlas(args.atlas or PLUGIN_ATLAS)
    rows += _rows(plugin, "plugin atlas", "sourced public fact")
    hits = [r for r in rows if _match(r, args)]
    if args.page < 0:
        raise InputError("--page must be >= 0")
    start = args.page * PAGE_ROWS
    page = hits[start:start + PAGE_ROWS]
    while page and len(json.dumps(page).encode()) > PAGE_BYTES - 2048:
        page = page[:-1]
    nxt = args.page + 1 if start + len(page) < len(hits) and page else None
    out = {"total": len(hits), "page": args.page, "rows": page, "next_page": nxt,
           "order": ["bound experiment profile", "user atlas", "plugin atlas"]}
    if not hits:
        out["answer"] = "unknown"
        out["note"] = "no sourced claim matches: do not fill the value from memory; ask for a source or a profile"
        if args.experiment:
            for link in plugin["links"]:
                names = [link["experiment"], *link.get("aliases", [])]
                if any(args.experiment.lower() == n.lower() for n in names):
                    out["see_profile"] = link["profile"]
    return "ok", out


def audit(args, defaults):
    try:
        text = Path(args.file).read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read {args.file}: {exc}") from None
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        if CLAIM_ID.search(line):
            continue
        for m in UNIT_NUMBER.finditer(line):
            found.append({"line": n, "text": m.group(0).strip()})
    status = "failed" if (args.strict and found) else "ok"
    return status, {"file": str(args.file), "unsourced": found, "strict": bool(args.strict),
                    "rule": "a number with a unit and no claim id on its line is unsourced"}


def main(argv=None):
    ap = JsonArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="ledger plus atlas-block check")
    v.add_argument("--atlas")
    v.add_argument("--release", action="store_true")
    v.add_argument("--today")
    r = sub.add_parser("render", help="markdown pages with claim ids")
    r.add_argument("--atlas")
    r.add_argument("--experiment")
    r.add_argument("--out")
    q = sub.add_parser("query", help="sourced claims matching the filters")
    q.add_argument("--project")
    q.add_argument("--user-atlas", action="append")
    q.add_argument("--atlas")
    for f in ("--experiment", "--subsystem", "--quantity", "--text"):
        q.add_argument(f)
    q.add_argument("--kind", choices=KINDS)
    q.add_argument("--page", type=int, default=0)
    a = sub.add_parser("audit", help="numbers without a claim id in a text file")
    a.add_argument("file")
    a.add_argument("--strict", action="store_true")
    for sp in (v, r, q, a):
        add_status_argument(sp)
    args = ap.parse_args(argv)
    given = {x.split("=")[0] for x in (sys.argv[1:] if argv is None else argv) if x.startswith("--")}
    defaults = ["status"] if "--status" not in given else []
    inputs = {k: v for k, v in vars(args).items() if k != "status"}
    try:
        status, res = {"validate": validate, "render": render, "query": query, "audit": audit}[args.command](args, defaults)
        out = {"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults, **res}
    except InputError as exc:
        out = {"status": "rejected", "status_label": args.status, "inputs": inputs, "error": str(exc)}
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return exit_code(out["status"])


if __name__ == "__main__":
    raise SystemExit(main())
