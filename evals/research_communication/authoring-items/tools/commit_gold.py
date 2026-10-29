#!/usr/bin/env python3
"""Salted commitments for gold files: SHA-256(nonce || gold bytes).
Usage: commit_gold.py GOLD_DIR NONCE_DIR OUT_JSON
Writes one 32-byte nonce per gold file into NONCE_DIR (keep it where test runs and the developer cannot read it)
and the commitments (no nonces) into OUT_JSON (commit this file)."""
import hashlib, json, secrets, sys
from pathlib import Path
gold_dir, nonce_dir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
nonce_dir.mkdir(parents=True, exist_ok=True)
commitments = {}
for f in sorted(p for p in gold_dir.rglob("*") if p.is_file()):
    rel = f.relative_to(gold_dir).as_posix()
    nonce = secrets.token_bytes(32)
    (nonce_dir / (rel.replace("/", "__") + ".nonce")).write_bytes(nonce)
    commitments[rel] = hashlib.sha256(nonce + f.read_bytes()).hexdigest()
out.write_text(json.dumps({"scheme": "sha256(nonce||gold)", "commitments": commitments}, indent=1) + "\n")
print(f"{len(commitments)} commitments written to {out}")
