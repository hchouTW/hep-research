"""--strict-versions (validate.py, dependencies.py): the stricter version policy alone, as --protected meant before
protected mode (0.8.0). A newer minor contract is an error with it and a warning without it; it never switches protected
mode on, so it needs no protected inputs and is never refused for their absence; --protected keeps its meaning."""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import CONTRACTS_VERSION, dependencies, validate  # noqa: E402

FIXTURE = json.loads((ROOT / "contracts" / "fixtures" / "artifacts" / "valid" / "computational_run.json").read_text())


_MAJOR, _MINOR, _ = CONTRACTS_VERSION.split(".")
NEWER_MINOR = f"{_MAJOR}.{int(_MINOR) + 1}.0"  # one minor above the reader, whatever the current version is


def newer(doc):
    d = json.loads(json.dumps(doc))
    d["contract_version"] = NEWER_MINOR
    if isinstance(d.get("versions"), dict) and "contracts" in d["versions"]:
        d["versions"]["contracts"] = NEWER_MINOR
    return d


def codes(rep, severity):
    return {f.code for f in rep.findings if f.severity == severity}


class StrictVersionsTests(unittest.TestCase):
    def test_validate_artifact(self):
        doc = newer(FIXTURE)
        self.assertIn("contract.newer_minor", codes(validate.validate_artifact(doc), "warning"))
        rep = validate.validate_artifact(doc, strict_versions=True)
        self.assertIn("contract.newer_minor", codes(rep, "error"))
        self.assertFalse({f.code for f in rep.findings if f.code.startswith(("protected.", "source.", "revocation."))})
        self.assertTrue(validate.validate_artifact(FIXTURE, strict_versions=True).ok)  # the current version passes

    def run_main(self, main, argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(argv)
        return code, out.getvalue()

    def test_command_lines(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            up = root / "up.json"
            up.write_text(json.dumps(newer(dict(FIXTURE, artifact_id="up"))))
            down = root / "down.json"
            down.write_text(json.dumps(dict(FIXTURE, artifact_id="down", inputs=[
                {"ref": "up.json", "sha256": hashlib.sha256(up.read_bytes()).hexdigest(),
                 "status": FIXTURE.get("status", [])}])))
            code, text = self.run_main(validate.main, [str(up), "--strict-versions"])
            self.assertEqual(code, 1, text)
            self.assertIn("contract.newer_minor", text)
            self.assertNotIn('"refused"', text)
            code, text = self.run_main(validate.main, [str(up)])
            self.assertEqual(code, 0, text)
            rep = dependencies.validate_dependencies(down, root, strict_versions=True)
            self.assertIn("dependency.source_invalid", {f["code"] for f in rep["findings"]})
            rep = dependencies.validate_dependencies(down, root)
            self.assertIn("dependency.source_newer_minor", {f["code"] for f in rep["findings"]})
            code, text = self.run_main(dependencies.main, [str(down), "--root", str(root), "--strict-versions"])
            self.assertEqual(code, 1, text)
            code, text = self.run_main(validate.main, [str(up), "--protected"])  # protected mode, no project: refused
            self.assertEqual(code, 3, text)
            self.assertIn("protected.policy_missing", text)


if __name__ == "__main__":
    unittest.main()
