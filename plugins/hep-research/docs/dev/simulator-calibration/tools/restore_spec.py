#!/usr/bin/env python3
"""Restore the single-file specification from Part B and Appendix E and check its SHA-256.
Usage: python3 -I tools/restore_spec.py [OUT.md]   (run from the package root)"""
import hashlib, sys
EXPECTED = "eb56a985f25f360f23b32ef64cdb2d7ef1942ceffdf85d2e5cc57fe046d46eb9"
HEAD = "## Appendix E: Changes in the English primary edition\n"
partb = open("simulator-calibration-v7.37.4-clean-en.md", encoding="utf-8").read()
appx = open("simulator-calibration-v7.37.4-clean-en.appendix-E.md", encoding="utf-8").read()
cut = partb.index("\n" + HEAD) + 1
text = partb[:cut] + appx
got = hashlib.sha256(text.encode("utf-8")).hexdigest()
print("restored sha256", got, "OK" if got == EXPECTED else "MISMATCH")
if len(sys.argv) > 1:
    open(sys.argv[1], "w", encoding="utf-8").write(text)
sys.exit(0 if got == EXPECTED else 1)
