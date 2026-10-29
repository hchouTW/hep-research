#!/usr/bin/env python3
"""Verify gold files against commitments after nonces are revealed.
Usage: verify_gold.py GOLD_DIR NONCE_DIR COMMITMENTS_JSON  (exit 0 all match, 1 otherwise)"""
import hashlib, json, sys
from pathlib import Path
gold_dir, nonce_dir, cfile = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
bad = 0
for rel, digest in json.loads(cfile.read_text())["commitments"].items():
    nonce = (nonce_dir / (rel.replace("/", "__") + ".nonce")).read_bytes()
    ok = hashlib.sha256(nonce + (gold_dir / rel).read_bytes()).hexdigest() == digest
    bad += not ok
    print(("ok   " if ok else "FAIL ") + rel)
sys.exit(1 if bad else 0)
