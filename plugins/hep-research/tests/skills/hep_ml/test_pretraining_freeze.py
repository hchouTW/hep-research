"""Pre-training freeze (ml-analysis.md, "Training on data and blinding"): the shipped example decision record binds
its exposure record (contracts/lineage.py decision exits 0, exposure at decision time unexposed) and names the split
manifest by its file SHA-256 in both `artifacts` and the `decision` text. Tampered copies fail: an edited exposure
history, an understated `seen`, a decision dated before what it counts as seen (lineage.py, exit 1), and a changed
split manifest or a hash that disagrees between `artifacts` and the text (the file-hash comparison the reference asks
for, since lineage.py does not open artifacts). Synthetic values only."""
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
ASSETS = PLUGIN / "skills" / "hep-ml" / "assets"
DECISION = ASSETS / "pretraining-decision.example.json"
EXPOSURE = ASSETS / "pretraining-exposure.example.json"
SPLIT = ASSETS / "pretraining-split.example.json"
LINEAGE = PLUGIN / "contracts" / "lineage.py"


def lineage(decision: Path, exposure: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(LINEAGE), "decision", str(decision), "--exposure", str(exposure)],
                          capture_output=True, text=True, timeout=120)


def freeze_findings(decision: dict, base: Path) -> list[str]:
    """The artifact check lineage.py leaves to the analyst: each artifact's file hash matches `artifacts`, and every
    SHA-256 the decision text names is one of the artifacts' hashes, with the split manifest named."""
    out = []
    hashes = set()
    for art in decision["artifacts"]:
        path = base / art["ref"]
        if not path.is_file():
            out.append(f"missing artifact {art['ref']}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != art["sha256"]:
            out.append(f"{art['ref']}: file SHA-256 {actual} differs from the record")
        hashes.add(art["sha256"])
    named = set(re.findall(r"\b[0-9a-f]{64}\b", decision["decision"]))
    if not named:
        out.append("the decision text names no SHA-256")
    elif named - hashes:
        out.append("the decision text names a SHA-256 that is not an artifact's")
    return out


class PretrainingFreezeTests(unittest.TestCase):
    def setUp(self):
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.exposure = json.loads(EXPOSURE.read_text(encoding="utf-8"))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def write(self, name, doc) -> Path:
        path = self.tmp / name
        path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        return path

    def assert_lineage_fails(self, decision, exposure, code):
        res = lineage(self.write("d.json", decision), self.write("e.json", exposure))
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn(code, {f["code"] for f in json.loads(res.stdout)["findings"]})

    def test_shipped_example_checks(self):
        res = lineage(DECISION, EXPOSURE)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        out = json.loads(res.stdout)
        self.assertEqual(out["status"], "valid")
        self.assertEqual(out["exposure_at_decision"]["state"], "unexposed")
        self.assertEqual(freeze_findings(self.decision, ASSETS), [])

    def test_record_states_what_the_reference_requires(self):
        d = self.decision
        self.assertEqual(d["category"], "other")
        self.assertEqual([a["ref"] for a in d["artifacts"]], [SPLIT.name])
        text = d["decision"].lower()
        for word in ("labels", "features", "training domain", "split manifest", d["artifacts"][0]["sha256"]):
            self.assertIn(word, text)
        # the record is later than what it saw and the exposure record went on (an append) after it
        self.assertLess(d["seen"]["through_seq"], len(self.exposure["entries"]))

    def test_split_manifest_passes_the_integrity_check(self):
        res = subprocess.run([sys.executable, str(PLUGIN / "skills/hep-ml/scripts/check_split_integrity.py"),
                              str(SPLIT)], capture_output=True, text=True, timeout=120)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_edited_exposure_history_fails(self):
        exp = copy.deepcopy(self.exposure)
        exp["entries"][1]["seen"] = ["sideband", "signal-region"]
        self.assert_lineage_fails(self.decision, exp, "lineage.seen_mismatch")

    def test_understated_seen_fails(self):
        dec = copy.deepcopy(self.decision)
        dec["time"] = "2026-10-10T12:00:00Z"   # after entry 3, which the decision does not count
        self.assert_lineage_fails(dec, self.exposure, "lineage.seen_understated")

    def test_decision_dated_before_what_it_saw_fails(self):
        dec = copy.deepcopy(self.decision)
        dec["time"] = "2026-10-01T12:00:00Z"   # before entry 2
        self.assert_lineage_fails(dec, self.exposure, "lineage.seen_after_decision")

    def test_changed_split_manifest_fails(self):
        manifest = json.loads(SPLIT.read_text(encoding="utf-8"))
        manifest["train"].append(manifest["test"].pop())
        (self.tmp / SPLIT.name).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        found = freeze_findings(self.decision, self.tmp)
        self.assertTrue(any("differs from the record" in f for f in found), found)

    def test_hash_in_text_and_artifacts_disagree_fails(self):
        dec = copy.deepcopy(self.decision)
        dec["artifacts"][0]["sha256"] = "0" * 64
        # still schema-valid lineage (lineage.py does not open artifacts) ...
        res = lineage(self.write("d.json", dec), EXPOSURE)
        self.assertEqual(res.returncode, 0, res.stdout)
        # ... so the freeze check is what catches it
        found = freeze_findings(dec, ASSETS)
        self.assertTrue(any("differs from the record" in f for f in found), found)
        self.assertTrue(any("not an artifact's" in f for f in found), found)


if __name__ == "__main__":
    unittest.main()
