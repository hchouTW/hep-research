#!/usr/bin/env python3
"""Check a built event-display bundle without a browser: integrity, structure, and payloads against sidecars.

Usage: python3 check_bundle.py BUNDLE_DIR [--spec bundle-spec.json]
Checks:
  1. bundle.json has schema event-display-bundle/1 and every field the page needs;
  2. every object it lists exists and its name equals the sha256 of its content; no unlisted object exists;
  3. index.html loads only relative paths;
  4. every payload agrees with its sidecar (runs export_histogram.py --verify-payload from this folder);
     with --spec, also every sidecar against a fresh read of the panel's "source" in the spec (a result the
     project changed after export fails here); a panel without "source" is listed in "unchecked_sources";
  5. reports event-bound coverage gaps. Status stays "ok" with gaps: the hand-off must name every gap.
Prints JSON {"status": "ok"|"failed", "problems": [...], "coverage": {...}}; exit 0 ok, 1 failed, 2 bad input.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    spec_path = None
    if len(argv) == 3 and argv[1] == "--spec":
        spec_path = Path(argv[2]).resolve()
    elif len(argv) != 1:
        print(json.dumps({"status": "rejected", "reason": "usage: check_bundle.py BUNDLE_DIR [--spec SPEC]"}))
        return 2
    root = Path(argv[0])
    try:
        b = json.loads((root / "bundle.json").read_text())
        sources = {p["id"]: p.get("source") for p in json.loads(spec_path.read_text())["panels"]} if spec_path else {}
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "rejected", "reason": f"bundle.json or spec unreadable: {exc}"}))
        return 2
    problems = []
    if b.get("schema") != "event-display-bundle/1":
        problems.append(f"schema is {b.get('schema')!r}")
    for k in ("title", "events", "default_event", "geometry", "panels"):
        if k not in b:
            problems.append(f"bundle.json lacks '{k}'")

    listed = {}
    for e in b.get("events", []):
        listed[e["scene"]] = e["sha256"]
    for g in b.get("geometry", []):
        listed[g["object"]] = g["sha256"]
    for p in b.get("panels", []):
        if p.get("binding") == "event":
            for entry in p.get("per_event", {}).values():
                listed[entry["payload"]] = entry["sha256"]
        else:
            listed[p["payload"]] = p["sha256"]
    for v in b.get("verification", []):
        listed.setdefault(v["sidecar"], v["sidecar"].split("/")[1].split(".")[0])
    for rel, digest in listed.items():
        f = root / rel
        if not f.is_file():
            problems.append(f"missing object {rel}")
            continue
        actual = hashlib.sha256(f.read_bytes()).hexdigest()
        if actual != digest or not f.name.startswith(actual):
            problems.append(f"integrity failure: {rel} (sha256 {actual[:12]}…)")
    for f in sorted((root / "objects").iterdir()) if (root / "objects").is_dir() else []:
        if f"objects/{f.name}" not in listed:
            problems.append(f"unlisted object objects/{f.name}")

    html = (root / "index.html").read_text() if (root / "index.html").is_file() else ""
    for url in re.findall(r'(?:src|href)="([^"]+)"', html):
        if re.match(r"^(?:[a-z]+:)?//", url) or url.startswith("/"):
            problems.append(f"index.html loads a non-relative URL: {url}")

    unchecked = set()
    for v in b.get("verification", []):
        source_args = []
        src = sources.get(v["panel"])
        if src:
            base = spec_path.parent
            if "root" in src:
                source_args = ["--root", str(base / src["root"]), "--object", src["object"]]
            else:
                source_args = ["--json", str(base / src["json"].format(key=v.get("event", "")))]
        elif spec_path:
            unchecked.add(v["panel"])
        r = subprocess.run([sys.executable, "-I", str(HERE / "export_histogram.py"),
                            "--verify-payload", str(root / v["payload"]), "--sidecar", str(root / v["sidecar"]),
                            *source_args], capture_output=True, text=True)
        if r.returncode != 0:
            where = v["panel"] + (f" event {v['event']}" if "event" in v else "")
            problems.append(f"payload check failed for {where}: {r.stdout.strip() or r.stderr.strip()}")

    status = "failed" if problems else "ok"
    print(json.dumps({"status": status, "problems": problems, "objects": len(listed),
                      "sources_checked": bool(spec_path), "unchecked_sources": sorted(unchecked),
                      "coverage": b.get("coverage", {})}, indent=1))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
