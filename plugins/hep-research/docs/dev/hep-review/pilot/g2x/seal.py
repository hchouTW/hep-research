#!/usr/bin/env python3
"""Seal or verify a Codex-authored held-out suite (g2x/frozen-protocol.md section 1). Domain-agnostic; reads no gold
content into its output. Run by the gold holder (the user), not by Claude, until the trials have ended.

  seal   --author DIR --out DIR   check the layout, run every oracle (pass counts only), copy public/instances to
                                  OUT/instances, write OUT/commitments.json (salted SHA-256 of every private file) and
                                  DIR/private/nonces.json
  verify --author DIR --commitments FILE   after the private folder is restored: check every commitment, rerun the
                                  oracles, report counts
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

ID = re.compile(r"^x[0-9a-f]{8}$")
PUBLIC_FILES = ("intent.json", "material/analysis.md", "material/data.json")
HINTS = re.compile(r"\b(defect|planted|gold|oracle|C0[1-4]|control instance|missing-input instance)\b", re.I)


def ids_of(author: Path) -> list[str]:
    return sorted(p.name for p in (author / "public" / "instances").iterdir() if p.is_dir())


def check_layout(author: Path) -> tuple[list[str], list[str]]:
    problems, warnings = [], []
    ids = ids_of(author)
    if len(ids) != 16:
        problems.append(f"{len(ids)} instances, expected 16")
    for iid in ids:
        if not ID.match(iid):
            problems.append(f"{iid}: id is not x + 8 hex digits")
        for rel in PUBLIC_FILES:
            f = author / "public" / "instances" / iid / rel
            if not f.is_file():
                problems.append(f"{iid}: missing {rel}")
            elif HINTS.search(f.read_text(encoding="utf-8")):
                warnings.append(f"{iid}: {rel} contains a word that may reveal the answer; read it before trials")
        for rel in (f"gold/{iid}.json", f"oracles/{iid}.py"):
            if not (author / "private" / rel).is_file():
                problems.append(f"{iid}: missing private/{rel}")
    for rel in ("calibration/items.json", "calibration/labels.json"):
        if not (author / "private" / rel).is_file():
            problems.append(f"missing private/{rel}")
    return problems, warnings


def run_oracles(author: Path) -> dict:
    passed, failed = 0, []
    for iid in ids_of(author):
        proc = subprocess.run([sys.executable, "-I", str(author / "private" / "oracles" / f"{iid}.py"),
                               str(author / "public" / "instances" / iid)], capture_output=True, timeout=300)
        if proc.returncode == 0:
            passed += 1
        else:
            failed.append(iid)
    return {"oracles_passed": passed, "oracles_failed": failed}


def private_files(author: Path) -> list[str]:
    root = author / "private"
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and p.name != "nonces.json")


def cmd_seal(author: Path, out: Path) -> dict:
    problems, warnings = check_layout(author)
    oracles = run_oracles(author)
    if problems or oracles["oracles_failed"]:
        return {"status": "refused", "problems": problems, "warnings": warnings, **oracles}
    if (out / "instances").exists():
        return {"status": "refused", "problems": [f"{out}/instances exists"]}
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(author / "public" / "instances", out / "instances")
    nonces, commitments = {}, {}
    for rel in private_files(author):
        nonce = secrets.token_bytes(32)
        nonces[rel] = nonce.hex()
        commitments[rel] = hashlib.sha256(nonce + (author / "private" / rel).read_bytes()).hexdigest()
    (author / "private" / "nonces.json").write_text(json.dumps(nonces, indent=1, sort_keys=True) + "\n")
    (out / "commitments.json").write_text(json.dumps({"algorithm": "sha256(nonce || file bytes), nonce 32 random bytes",
                                                      "commitments": commitments}, indent=1, sort_keys=True) + "\n")
    return {"status": "ok", "instances": len(ids_of(author)), "private_files_committed": len(commitments),
            "warnings": warnings, **oracles}


def cmd_verify(author: Path, commitments_file: Path) -> dict:
    record = json.loads(commitments_file.read_text())["commitments"]
    nonces = json.loads((author / "private" / "nonces.json").read_text())
    bad = [rel for rel, c in record.items()
           if not (author / "private" / rel).is_file() or not hmac.compare_digest(
               hashlib.sha256(bytes.fromhex(nonces[rel]) + (author / "private" / rel).read_bytes()).hexdigest(), c)]
    extra = sorted(set(private_files(author)) - set(record))
    return {"status": "ok" if not bad else "mismatch", "verified": len(record) - len(bad), "mismatched": bad,
            "uncommitted_extra_files": extra, **run_oracles(author)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seal")
    s.add_argument("--author", required=True)
    s.add_argument("--out", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--author", required=True)
    v.add_argument("--commitments", required=True)
    a = p.parse_args(argv)
    out = (cmd_seal(Path(a.author), Path(a.out)) if a.cmd == "seal"
           else cmd_verify(Path(a.author), Path(a.commitments)))
    print(json.dumps(out, indent=1))
    return 0 if out["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
