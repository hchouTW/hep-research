#!/usr/bin/env python3
"""Write the M2 redistribution outcome back into plugins/hep-research/docs/migration-map.csv.

For every row whose source_path has a record in tasks/hep-research/m2/redistribution/<legacy>.csv, the
destination becomes the recorded one and the disposition maps as: move -> reuse, move+path-edit -> adapt,
port -> adapt, retain-outside -> retain-outside, retire -> retire, deferred -> keeps the planned disposition.
The rationale gets an "M2: <record disposition>" prefix (idempotent). Rows without a record are unchanged.
Usage: python3 tasks/hep-research/scripts/apply_redistribution_records.py [--check]
"""
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAP = ROOT / "plugins/hep-research/docs/migration-map.csv"
REC = ROOT / "tasks/hep-research/m2/redistribution"
DISP = {"move": "reuse", "move+path-edit": "adapt", "port": "adapt", "retain-outside": "retain-outside", "retire": "retire"}


def main(argv):
    records = {}
    for f in sorted(REC.glob("*.csv")):
        if f.name in ("plan.csv", "legacy-name-edits.csv"):
            continue
        for r in csv.DictReader(f.open(encoding="utf-8")):
            records[r["source_path"]] = r
    text = MAP.open(encoding="utf-8", newline="").read()
    rows = list(csv.DictReader(io.StringIO(text)))
    fields = list(rows[0].keys())
    changed = 0
    for row in rows:
        r = records.get(row["source_path"])
        if not r:
            continue
        before = dict(row)
        if r["disposition"] != "deferred":
            row["disposition"] = DISP[r["disposition"]]
        if r["destination"] and r["disposition"] not in ("retire",):
            row["destination"] = r["destination"]
        tag = f"M2: {r['disposition']}"
        if not row["rationale"].startswith("M2: "):
            row["rationale"] = f"{tag}; {row['rationale']}" if row["rationale"] else tag
        changed += row != before
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fields, lineterminator="\r\n" if "\r\n" in text else "\n")
    w.writeheader()
    w.writerows(rows)
    print(f"records {len(records)}, rows changed {changed}")
    if "--check" in argv:
        return 0 if out.getvalue() == text else 1
    MAP.open("w", encoding="utf-8", newline="").write(out.getvalue())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
