"""Release B, P5.2/P5.1/P5.3: analysis-level bundles, formal-use permits and the recipe-use review. A changed spec,
recipe, calibration or plugin release changes the bundle digest and leaves a permit without effect; a missing, expired,
not-yet-valid, replayed, wrong-scope, wrong-subject, wrong-use, revoked or session-writable permit is refused; formal
use needs an attestation that accepts the recipe for the required roles and covers the use; the HEPData export runs in
protected mode only with a valid permit. Synthetic data only; custodian files are modeled as in tests/protected_fixture.py.
"""
from __future__ import annotations

import contextlib
import copy
import datetime
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import analysis_bundle as ab  # noqa: E402
from contracts import permit as pm  # noqa: E402
from contracts.release_manifest import canonical_sha256  # noqa: E402
from core.protected.guard import establish  # noqa: E402
from tests.protected_fixture import PLUGIN, ProtectedProject, ts  # noqa: E402

RECIPE = json.loads((ROOT / "contracts" / "semantics" / "recipes" / "flux_from_counts.json").read_text())
TABLE = json.loads((ROOT / "contracts" / "semantics" / "tables" / "differential_flux.json").read_text())
DATASET = json.loads((ROOT / "contracts" / "fixtures" / "artifacts" / "valid" / "dataset_record.json").read_text())
SPEC = json.loads((ROOT / "contracts" / "fixtures" / "artifacts" / "valid" / "measurement_v26.json").read_text())
ITEMS = [{"role": "measurement-spec", "id": "spec", "ref": "spec/measurement.json"},
         {"role": "recipe", "id": RECIPE["recipe_id"], "ref": "recipes/flux.json"},
         {"role": "semantics-table", "id": "differential-flux", "ref": "tables/differential_flux.json"},
         {"role": "calibration", "id": "synthetic-efficiency", "ref": "calib/efficiency.txt"},
         {"role": "environment-lock", "id": "env", "ref": "env/requirements.lock"}]


class Analysis:
    """A synthetic protected analysis: bundle, attestation, nonce ledger and a permit for one published artifact."""

    def __init__(self, tmp: Path):
        self.pp = ProtectedProject(tmp, policy_extra={})
        self.pp.policy["protected_inputs"]["nonce_ledger"] = str(self.pp.cust / "nonces.jsonl")
        self.pp.write_all()
        self.ledger = self.pp.cust / "nonces.jsonl"
        self.pp._write(self.ledger, b"")
        self.proj = self.pp.project
        for rel, doc in (("spec/measurement.json", SPEC), ("recipes/flux.json", RECIPE), ("tables/differential_flux.json", TABLE)):
            self.pp.artifact(rel, doc)
        (self.proj / "calib").mkdir()
        (self.proj / "calib" / "efficiency.txt").write_text("0.91 0.92 0.93\n")
        (self.proj / "env").mkdir()
        (self.proj / "env" / "requirements.lock").write_text("numpy==2.5.3\n")
        (self.proj / "evidence").mkdir()
        (self.proj / "evidence" / "closure.json").write_text('{"closure": "synthetic toy closure within 1%"}')
        self.art = self.pp.artifact("results/dataset.json", DATASET)
        self.patches = [mock.patch("contracts.analysis_bundle.plugin_release", lambda: dict(PLUGIN))]

    def start(self):
        self.pp.start()
        for p in self.patches:
            p.start()
        self.freeze()
        self.write_attestation()
        self.write_permit()
        return self

    def stop(self):
        for p in reversed(self.patches):
            p.stop()
        self.pp.stop()
        self.pp.cleanup_modes()

    def freeze(self):
        self.bundle = ab.freeze(self.proj, "synthetic-analysis", ITEMS)
        self.pp.artifact("bundles/analysis.json", self.bundle)

    def write_attestation(self, purposes=("validation", "formal-analysis"), conclusion="accepted", **lifecycle):
        scope = {"observable": "synthetic differential flux", "data": ["synthetic-release-001"],
                 "recipe": {"recipe_id": RECIPE["recipe_id"], "sha256": canonical_sha256(RECIPE)},
                 "calibrations": [{"id": "synthetic-efficiency", "sha256": "4" * 64}], "assumptions": ["isotropic flux"],
                 "purposes": list(purposes)}
        ev = (self.proj / "evidence" / "closure.json").read_bytes()
        review = {"reviewer": "synthetic reviewer", "role": "analysis-reviewer", "date": ts(-3600)[:10],
                  "bundle_sha256": self.bundle["bundle_digest"], "scope_sha256": canonical_sha256(scope),
                  "evidence": [{"ref": "evidence/closure.json", "sha256": hashlib.sha256(ev).hexdigest()}],
                  "conclusion": conclusion, "record_ref": "review-record-001"}
        lc = {"state": "active", "effective": ts(-86400), "expires": ts(86400 * 30), "revocation_ref": "rev-att-1",
              "status_source": "custodian:synthetic-revocations", "max_status_age_s": 3600}
        lc.update(lifecycle)
        self.att = {"attestation_version": "1.0.0", "attestation_id": "att-1",
                    "subject": {"bundle_sha256": self.bundle["bundle_digest"], "scope": scope},
                    "capability": {"required_capabilities": ["core:data-exposure"]},
                    "review": {"reviews": [review]}, "lifecycle": lc}
        self.att_path = self.pp.cust / "attestation.json"
        self.pp._write(self.att_path, json.dumps(self.att).encode())

    def write_permit(self, **over):
        p = {"permit_version": "1.0.0", "permit_id": "permit-1", "scope": "formal-use",
             "subject": {"analysis_bundle_sha256": self.bundle["bundle_digest"],
                         "analysis_bundle_ref": "bundles/analysis.json",
                         "artifacts": [hashlib.sha256(self.art.read_bytes()).hexdigest()]},
             "use": {"purpose": "formal-analysis", "description": "synthetic HEPData export"},
             "actor": "synthetic analyst", "budget": {"uses": 1}, "not_before": ts(-600), "expires": ts(3600),
             "nonce": "ab" * 16, "issued_by": "synthetic gate",
             "review": {"attestation_ref": str(self.att_path), "attestation_sha256": canonical_sha256(self.att),
                        "required_roles": ["analysis-reviewer"]}}
        for k, v in over.items():
            if v is None:
                p.pop(k, None)
            else:
                p[k] = v
        self.permit = p
        self.permit_path = self.pp.cust / "permit.json"
        self.pp._write(self.permit_path, json.dumps(p).encode())

    def codes(self, inputs=None, **kw):
        ctx = establish([self.art], project=self.proj)
        assert ctx.protected and not ctx.refusals, ctx.refusals
        return {r["code"] for r in pm.verify(self.permit_path, ctx, inputs=[self.art] if inputs is None else inputs, **kw)}


class AnalysisBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.a = Analysis(Path(self.tmp.name))
        for p in self.a.patches:
            p.start()
        self.a.freeze()

    def tearDown(self):
        for p in reversed(self.a.patches):
            p.stop()
        self.tmp.cleanup()

    def test_frozen_bundle_verifies(self):
        rep = ab.verify(self.a.bundle, self.a.proj, check_plugin=True)
        self.assertEqual(rep["status"], "identical", rep)
        self.assertEqual([it["digest_kind"] for it in self.a.bundle["items"] if it["role"] == "calibration"], ["bytes"])
        recipe = [it for it in self.a.bundle["items"] if it["role"] == "recipe"][0]
        self.assertEqual(recipe["sha256"], canonical_sha256(RECIPE))  # the digest an attestation scope uses

    def test_any_change_changes_the_digest(self):
        base = self.a.bundle["bundle_digest"]
        changes = {"spec/measurement.json": lambda p: p.write_text(json.dumps(dict(SPEC, objective="edited"))),
                   "recipes/flux.json": lambda p: p.write_text(json.dumps(dict(RECIPE, not_applied=[]))),
                   "calib/efficiency.txt": lambda p: p.write_text("0.5\n"),
                   "env/requirements.lock": lambda p: p.write_text("numpy==2.6.0\n")}
        for rel, edit in changes.items():
            with self.subTest(item=rel):
                path = self.a.proj / rel
                before = path.read_bytes()
                edit(path)
                self.assertEqual(ab.verify(self.a.bundle, self.a.proj)["differences"], [{"ref": rel, "change": "changed"}])
                self.assertNotEqual(ab.freeze(self.a.proj, "synthetic-analysis", ITEMS)["bundle_digest"], base)
                path.write_bytes(before)
        other = ab.freeze(self.a.proj, "synthetic-analysis", ITEMS, identity={"release": "9.9.9", "digest": "9" * 64})
        self.assertNotEqual(other["bundle_digest"], base)
        self.assertIn({"ref": "$plugin_release", "change": "changed"},
                      ab.verify(other, self.a.proj, check_plugin=True)["differences"])
        # reformatting a JSON item keeps the canonical digest
        (self.a.proj / "recipes" / "flux.json").write_text(json.dumps(RECIPE, indent=4))
        self.assertEqual(ab.verify(self.a.bundle, self.a.proj)["status"], "identical")

    def test_refusals(self):
        with self.assertRaises(ab.BundleRefused):
            ab.freeze(self.a.proj, "x", ITEMS + [dict(ITEMS[1])])  # listed twice
        with self.assertRaises(ab.BundleRefused):
            ab.freeze(self.a.proj, "x", [it for it in ITEMS if it["role"] != "environment-lock"])
        with self.assertRaises(ab.BundleRefused):
            ab.freeze(self.a.proj, "x", ITEMS + [{"role": "review", "id": "r", "ref": "../outside.json"}])
        (self.a.proj / "linked.txt").symlink_to(self.a.proj / "calib" / "efficiency.txt")
        with self.assertRaises(ab.BundleRefused):
            ab.freeze(self.a.proj, "x", ITEMS + [{"role": "review", "id": "r", "ref": "linked.txt"}])
        tampered = dict(self.a.bundle, analysis="other")
        self.assertIn({"ref": "$", "change": "digest"}, ab.verify(tampered, self.a.proj)["differences"])

    def test_attestation_takes_the_analysis_bundle_as_subject(self):
        from contracts.attestation import evaluate
        self.a.pp.start()
        self.addCleanup(self.a.pp.stop)
        self.a.write_attestation()
        out = evaluate(self.a.att, bundle=self.a.bundle, recipe=RECIPE, evidence_root=self.a.proj,
                       roles=["analysis-reviewer"])
        self.assertTrue(out["evaluated"], out["findings"])
        self.assertEqual(out["axes"]["review"]["state"], "accepted-as-recorded")
        changed = dict(self.a.bundle, analysis="other")
        changed["bundle_digest"] = ab.digest_of(changed)
        self.assertFalse(evaluate(self.a.att, bundle=changed, recipe=RECIPE)["evaluated"])


class PermitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.a = Analysis(Path(self.tmp.name)).start()

    def tearDown(self):
        self.a.stop()
        self.tmp.cleanup()

    def test_valid_permit_has_no_refusal(self):
        self.assertEqual(self.a.codes(), set())

    def test_permit_refusals(self):
        cases = {
            "permit.missing": lambda a: os.unlink(a.permit_path),
            "permit.malformed": lambda a: a.write_permit(nonce="short"),
            "permit.wrong_scope": lambda a: a.write_permit(scope="s3-execution"),
            "permit.expired": lambda a: a.write_permit(expires=ts(-1)),
            "permit.not_yet_valid": lambda a: a.write_permit(not_before=ts(600)),
            "permit.wrong_use": lambda a: a.write_permit(use={"purpose": "validation", "description": "x"}),
            "permit.wrong_subject": lambda a: a.write_permit(subject=dict(a.permit["subject"], artifacts=["e" * 64])),
            "permit.replayed": lambda a: a.pp._write(a.ledger, json.dumps({"nonce": "ab" * 16, "permit_id": "permit-1",
                                                                          "time": ts(-60)}).encode() + b"\n"),
            "source.writable_by_account": lambda a: os.chmod(a.permit_path, 0o666),
            "permit.revoked": lambda a: a.pp.revoke("permit", ref="permit-1"),
            "permit.review_missing": lambda a: a.write_permit(review=None),
        }
        for code, breaker in cases.items():
            with self.subTest(code=code):
                self.tearDown()
                self.setUp()
                breaker(self.a)
                got = self.a.codes() if code != "permit.missing" else {
                    r["code"] for r in pm.verify(None, establish([self.a.art], project=self.a.proj), inputs=[self.a.art])}
                self.assertIn(code, got)

    def test_budget_counts_uses(self):
        self.a.write_permit(budget={"uses": 2})
        line = json.dumps({"nonce": "ab" * 16, "permit_id": "permit-1", "time": ts(-60)}).encode() + b"\n"
        self.a.pp._write(self.a.ledger, line)
        self.assertEqual(self.a.codes(), set())
        self.a.pp._write(self.a.ledger, line * 2)
        self.assertIn("permit.replayed", self.a.codes())

    def test_ledger_must_be_a_protected_input(self):
        os.chmod(self.a.ledger, 0o666)
        self.assertIn("permit.ledger_missing", self.a.codes())

    def test_changed_bundle_invalidates_the_permit(self):
        (self.a.proj / "calib" / "efficiency.txt").write_text("0.1\n")
        self.assertIn("permit.bundle_changed", self.a.codes())
        self.tearDown()
        self.setUp()
        with mock.patch("contracts.analysis_bundle.plugin_release", lambda: {"release": "9.9.9", "digest": "9" * 64}):
            self.assertIn("permit.bundle_changed", self.a.codes())  # another plugin release

    def test_recipe_use_review(self):
        """P5.3: the review must accept the recipe for the required roles, cover formal analysis, and be active."""
        a = self.a
        for code, kw in (("permit.review_out_of_scope", {"purposes": ("validation",)}),
                         ("permit.review_not_accepted", {"conclusion": "changes-requested"}),
                         ("permit.attestation_inactive", {"state": "withdrawn"})):
            with self.subTest(code=code):
                self.tearDown()
                self.setUp()
                self.a.write_attestation(**kw)
                self.a.write_permit()  # the gate bound the attestation as it is
                self.assertIn(code, self.a.codes())
        self.tearDown()
        self.setUp()
        a = self.a
        a.write_permit(review=dict(a.permit["review"], required_roles=["analysis-reviewer", "statistics-reviewer"]))
        self.assertIn("permit.review_not_accepted", a.codes())
        a.write_permit(review=dict(a.permit["review"], attestation_sha256="0" * 64))
        self.assertIn("permit.attestation_mismatch", a.codes())
        a.write_permit()
        a.pp.revoke("attestation", ref="att-1")
        self.assertIn("permit.attestation_inactive", a.codes())


class FormalEntryPointTests(unittest.TestCase):
    """At the formal-use entry points (HEPData export: command line and build_tables) a valid permit lifts the refusal."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.a = Analysis(Path(self.tmp.name)).start()
        self.hx = __import__("tests.contracts.test_protected_entry_points", fromlist=["x"]).load_script(
            "adapters/hepdata/assets/hepdata_export.py")
        self.cwd = os.getcwd()
        os.chdir(self.a.proj)

    def tearDown(self):
        os.chdir(self.cwd)
        self.a.stop()
        self.tmp.cleanup()

    def run_export(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = self.hx.main(["--artifact", str(self.a.art), "--out", str(self.a.proj / "hepdata"), *extra])
        text = out.getvalue()
        refused = code == 3 and '"entry_point"' in text
        return code, (json.loads(text[text.index("{"):]) if refused else None)

    def test_command_line(self):
        code, rep = self.run_export()
        self.assertEqual({r["code"] for r in rep["refusals"]}, {"protected.formal_use_unavailable"})
        code, rep = self.run_export("--permit", str(self.a.permit_path))
        self.assertIsNone(rep, rep)
        self.assertEqual(code, 0)
        self.a.write_permit(expires=ts(-1))
        code, rep = self.run_export("--permit", str(self.a.permit_path))
        self.assertIn("permit.expired", {r["code"] for r in rep["refusals"]})

    def test_direct_call(self):
        from core.protected.guard import ProtectedUseRefused
        with self.assertRaises(ProtectedUseRefused):
            self.hx.build_tables(DATASET, self.a.proj / "results", "t", "d")
        self.hx.build_tables(DATASET, self.a.proj / "results", "t", "d", self.a.permit_path, [self.a.art])
        other = self.a.pp.artifact("results/other.json", dict(DATASET, objective="not covered"))
        with self.assertRaises(ProtectedUseRefused) as cm:
            self.hx.build_tables(DATASET, self.a.proj / "results", "t", "d", self.a.permit_path, [other])
        self.assertIn("permit.wrong_subject", {r["code"] for r in cm.exception.refusals})


if __name__ == "__main__":
    unittest.main()
