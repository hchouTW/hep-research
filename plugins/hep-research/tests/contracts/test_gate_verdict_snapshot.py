"""Verdict snapshot of every committed artifact (hep-statistics hardening STH-T1.0).

For every JSON artifact under examples/ and contracts/fixtures/artifacts/ the snapshot records the default-validator
outcome (ok), the strict outcome (strict_ok) and, for a statistical-result, the publication-gate status. A rule change
that moves any of them fails this test unless the change is listed in ALLOWED_CHANGES with its reason, so new contract
rules cannot silently change what a committed artifact promised.

Regenerate the snapshot only when a change is intended and listed:
    python3 tests/contracts/test_gate_verdict_snapshot.py --write
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts.validate import publication_gate, validate_artifact  # noqa: E402

SNAPSHOT = Path(__file__).with_name("gate_verdicts.json")
BASES = ("examples", "contracts/fixtures/artifacts")

# path -> (field -> new value, reason). Recorded against the snapshot taken on main c1d375c (contracts 2.5.0).
_Q3 = ("contracts 2.6.0 (STH-T1.1, order question Q3): a 'synthetic' or 'asimov' statistical-result fails the "
       "publication gate (gate.not_observed_data); the artifact stays valid under the validator, default and strict")
_Q3_UNRESOLVED_TO_FAILED = (
    "contracts/fixtures/artifacts/unresolved/statres_scan_no_global.json",
    "contracts/fixtures/artifacts/valid/statres_bayesian.json",
    "contracts/fixtures/artifacts/valid/statres_bayesian_rhat_warning.json",
    "contracts/fixtures/artifacts/valid/statres_frequentist.json",
    "contracts/fixtures/artifacts/valid/statres_scan_global.json",
    "examples/ams-flux-ratio/output/artifacts/ratio_result.json",
    "examples/collider-angular/output/artifacts/result.json",
    "examples/detector-resolution/output/artifacts/width_fit.json",
    "examples/published-comparison/output/artifacts/result.json",
    "examples/recasting/output/artifacts/result.json",
    "examples/theory-comparison/output/artifacts/result.json",
)
ALLOWED_CHANGES: dict[str, tuple[dict, str]] = {
    # J9 (physics-ml example, status ["synthetic"]) was the one committed artifact that passed: the intended true
    # positive of the audit's mutation 1a (order question Q6).
    "examples/ml-classifier-to-inference/output/artifacts/statistical_result.json": ({"gate": "failed"}, _Q3 + " (Q6: J9)"),
    **{p: ({"gate": "failed"}, _Q3) for p in _Q3_UNRESOLVED_TO_FAILED},
}


def collect() -> dict:
    rows = {}
    for base in BASES:
        for p in sorted((ROOT / base).rglob("*.json")):
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if not isinstance(doc, dict) or "artifact_type" not in doc:
                continue
            row = {"ok": validate_artifact(doc).ok, "strict_ok": validate_artifact(doc, strict=True).ok}
            if doc.get("artifact_type") == "statistical-result":
                row["gate"] = publication_gate(doc)["status"]
            rows[p.relative_to(ROOT).as_posix()] = row
    return rows


class VerdictSnapshot(unittest.TestCase):
    def test_no_unlisted_verdict_change(self):
        recorded = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        now = collect()
        problems = []
        for path in sorted(set(recorded) | set(now)):
            if path not in now:
                problems.append(f"{path}: in the snapshot but no longer committed")
                continue
            if path not in recorded:
                problems.append(f"{path}: new artifact, not in the snapshot (rerun with --write)")
                continue
            expected = dict(recorded[path])
            expected.update(ALLOWED_CHANGES.get(path, ({}, ""))[0])
            if now[path] != expected:
                problems.append(f"{path}: {expected} -> {now[path]}")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_allowed_changes_are_real_changes(self):
        recorded = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        for path, (change, reason) in ALLOWED_CHANGES.items():
            with self.subTest(path):
                self.assertTrue(reason)
                self.assertIn(path, recorded)
                self.assertTrue(any(recorded[path].get(k) != v for k, v in change.items()), "allow-list entry changes nothing")


def main() -> None:
    rows = collect()
    for path, (change, _reason) in ALLOWED_CHANGES.items():
        # the snapshot keeps the c1d375c baseline; the allow-list carries the intended change on top of it
        for k in change:
            if path in rows:
                rows[path][k] = json.loads(SNAPSHOT.read_text(encoding="utf-8")).get(path, {}).get(k, rows[path][k])
    SNAPSHOT.write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{len(rows)} artifacts written to {SNAPSHOT.name}")


if __name__ == "__main__":
    if "--write" in sys.argv[1:]:
        main()
    else:
        unittest.main()
