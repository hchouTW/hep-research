"""T4.5: attestations with separate capability, review and lifecycle axes. Each axis is reported on its own; a review
binds the bundle, the scope and its evidence, so a changed bundle, scope, recipe or evidence file leaves it unbound;
revocation and expiry come from a fresh status source; no output field combines the axes. Synthetic values only."""
import copy
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import attestation as at  # noqa: E402
from contracts.release_manifest import canonical_sha256  # noqa: E402
from core.partition.bundle import digest_of  # noqa: E402

NOW = datetime.datetime(2026, 10, 9, 12, 0, 0, tzinfo=datetime.UTC)
RECIPE = json.loads((ROOT / "contracts" / "semantics" / "recipes" / "flux_from_counts.json").read_text(encoding="utf-8"))
EVIDENCE = b'{"closure": "synthetic toy closure within 1%"}'


def bundle_doc():
    doc = {"format": "hep-research-bundle/1", "campaign_uid": "synthetic-uid", "manifest_hash": "3" * 64,
           "container_image": None, "data_exposure": {"state": "unexposed", "basis": "structured-record"},
           "roots": {}, "files": [], "named": {}}
    doc["bundle_digest"] = digest_of(doc)
    return doc


def axes(out):
    return {k: v["state"] for k, v in out["axes"].items()}


class AttestationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "evidence").mkdir()
        (self.root / "evidence" / "closure.json").write_bytes(EVIDENCE)
        self.bundle = bundle_doc()
        scope = {"observable": "synthetic differential flux, 10 bins", "data": ["synthetic-release-001"],
                 "recipe": {"recipe_id": RECIPE["recipe_id"], "sha256": canonical_sha256(RECIPE)},
                 "calibrations": [{"id": "synthetic-efficiency-map", "sha256": "4" * 64}],
                 "assumptions": ["isotropic flux"], "purposes": ["fixed-execution", "validation"]}
        review = {"reviewer": "synthetic reviewer", "role": "analysis-reviewer", "date": "2026-10-08",
                  "bundle_sha256": self.bundle["bundle_digest"], "scope_sha256": canonical_sha256(scope),
                  "evidence": [{"ref": "evidence/closure.json", "sha256": hashlib.sha256(EVIDENCE).hexdigest()}],
                  "conclusion": "accepted", "record_ref": "review-record-001"}
        self.att = {"attestation_version": "1.0.0", "attestation_id": "att-001",
                    "subject": {"bundle_sha256": self.bundle["bundle_digest"], "scope": scope},
                    "capability": {"required_capabilities": ["core:data-exposure"]},
                    "review": {"reviews": [review]},
                    "lifecycle": {"state": "active", "effective": "2026-10-08T00:00:00Z", "expires": "2026-11-08T00:00:00Z",
                                  "revocation_ref": "rev-att-001", "status_source": "synthetic-gate", "max_status_age_s": 3600}}
        self.rev = {"as_of": "2026-10-09T11:30:00Z", "source": "synthetic-gate", "revoked": []}

    def tearDown(self):
        self.tmp.cleanup()

    def run_eval(self, att=None, **kw):
        args = dict(bundle=self.bundle, recipe=RECIPE, evidence_root=self.root, revocations=self.rev,
                    roles=["analysis-reviewer"], use=None, now=NOW)
        args.update(kw)
        return at.evaluate(self.att if att is None else att, **args)

    def test_all_axes_in_good_state(self):
        out = self.run_eval()
        self.assertTrue(out["evaluated"], out["findings"])
        self.assertEqual(axes(out), {"capability": "supported", "review": "accepted-as-recorded", "lifecycle": "active"})

    def test_no_combined_verdict(self):
        out = self.run_eval()
        self.assertEqual(out["clock"], "given")
        self.assertEqual(out["evaluated_at"], "2026-10-09T12:00:00Z")
        self.assertEqual(set(out), {"attestation_id", "evaluated_at", "clock", "subject_sha256", "scope_sha256", "axes", "evaluated", "findings", "note"})
        for name, fn in {"approved": lambda a: a.update(approved=True),
                         "authorized axis": lambda a: a["review"].update(authorized=True),
                         "status": lambda a: a.update(status="pass")}.items():
            with self.subTest(name):
                a = copy.deepcopy(self.att)
                fn(a)
                self.assertFalse(self.run_eval(a)["evaluated"])

    def test_axes_are_independent(self):
        a = copy.deepcopy(self.att)
        a["capability"]["required_capabilities"].append("core:future-capability")
        self.assertEqual(axes(self.run_eval(a)), {"capability": "unsupported", "review": "accepted-as-recorded", "lifecycle": "active"})
        self.rev["revoked"] = [{"ref": "rev-att-001"}]
        self.assertEqual(axes(self.run_eval()), {"capability": "supported", "review": "accepted-as-recorded", "lifecycle": "revoked"})

    # review axis: binding to bundle, scope and evidence (C15 review-axes part)
    def test_mismatch_reports_no_axes(self):
        other = bundle_doc()
        other["campaign_uid"] = "another"
        other["bundle_digest"] = digest_of(other)
        r = copy.deepcopy(RECIPE)
        r["steps"].pop()
        for kw in (dict(bundle=other), dict(recipe=r)):
            out = self.run_eval(**kw)
            self.assertFalse(out["evaluated"])
            self.assertIsNone(out["axes"])

    def test_bindings_unchecked_without_bundle_or_recipe(self):
        for kw in (dict(bundle=None), dict(recipe=None)):
            with self.subTest(kw=list(kw)):
                self.assertEqual(axes(self.run_eval(**kw))["review"], "bindings-unchecked")

    def test_status_age_is_capped(self):
        a = copy.deepcopy(self.att)
        a["lifecycle"]["max_status_age_s"] = 10 ** 12
        out = self.run_eval(a)
        self.assertFalse(out["evaluated"])
        self.assertIn("attestation.status_age_too_long", [f["code"] for f in out["findings"]])

    def test_linked_evidence_root_refused_in_library(self):
        link = Path(self.tmp.name + "-link")
        os.symlink(self.root, link)
        try:
            self.assertEqual(axes(self.run_eval(evidence_root=link))["review"], "evidence-unverified")
        finally:
            link.unlink()

    def test_changed_bundle_unbinds_review(self):
        a = copy.deepcopy(self.att)
        a["subject"]["bundle_sha256"] = "5" * 64
        out = self.run_eval(a, bundle=None)
        self.assertEqual(axes(out)["review"], "unbound")

    def test_bundle_document_checks(self):
        other = bundle_doc()
        other["campaign_uid"] = "another"
        other["bundle_digest"] = digest_of(other)
        self.assertIn("attestation.bundle_other", [f["code"] for f in self.run_eval(bundle=other)["findings"]])
        tampered = dict(self.bundle, manifest_hash="6" * 64)
        out = self.run_eval(bundle=tampered)
        self.assertFalse(out["evaluated"])
        self.assertIn("attestation.bundle_changed", [f["code"] for f in out["findings"]])

    def test_widened_scope_unbinds_review(self):
        a = copy.deepcopy(self.att)
        a["subject"]["scope"]["purposes"].append("formal-analysis")
        self.assertEqual(axes(self.run_eval(a))["review"], "unbound")
        a = copy.deepcopy(self.att)
        a["subject"]["scope"]["data"].append("synthetic-release-002")
        self.assertEqual(axes(self.run_eval(a))["review"], "unbound")

    def test_changed_recipe(self):
        r = copy.deepcopy(RECIPE)
        r["steps"].pop()
        out = self.run_eval(recipe=r)
        self.assertIn("attestation.recipe_changed", [f["code"] for f in out["findings"]])
        self.assertFalse(out["evaluated"])

    def test_changed_evidence(self):
        (self.root / "evidence" / "closure.json").write_bytes(EVIDENCE + b" ")
        self.assertEqual(axes(self.run_eval())["review"], "evidence-unverified")

    def test_evidence_link_refused(self):
        real = self.root / "real"
        real.mkdir()
        (real / "closure.json").write_bytes(EVIDENCE)
        (self.root / "evidence" / "closure.json").unlink()
        (self.root / "evidence").rmdir()
        os.symlink(real, self.root / "evidence")
        self.assertEqual(axes(self.run_eval())["review"], "evidence-unverified")

    def test_evidence_unchecked_without_root(self):
        self.assertEqual(axes(self.run_eval(evidence_root=None))["review"], "evidence-unverified")

    def test_rejection_and_absence(self):
        a = copy.deepcopy(self.att)
        second = dict(a["review"]["reviews"][0], reviewer="second", role="statistics-reviewer", conclusion="changes-requested")
        a["review"]["reviews"].append(second)
        self.assertEqual(axes(self.run_eval(a))["review"], "rejected")
        a["review"]["reviews"] = []
        self.assertEqual(axes(self.run_eval(a))["review"], "absent")

    def test_roles(self):
        self.assertEqual(axes(self.run_eval(roles=None))["review"], "roles-unchecked")
        self.assertEqual(axes(self.run_eval(roles=["analysis-reviewer", "statistics-reviewer"]))["review"], "roles-incomplete")
        self.assertFalse(self.run_eval(roles="analysis-reviewer")["evaluated"])
        self.assertFalse(self.run_eval(roles=[])["evaluated"])

    def test_use_scope(self):
        scope = self.att["subject"]["scope"]
        ok = dict(copy.deepcopy(scope), purposes=["validation"])
        self.assertEqual(axes(self.run_eval(use=ok))["review"], "accepted-as-recorded")
        for name, use in {"unreviewed purpose": dict(copy.deepcopy(scope), purposes=["formal-analysis"]),
                          "two purposes": copy.deepcopy(scope),
                          "other observable": dict(copy.deepcopy(scope), observable="other", purposes=["validation"]),
                          "other calibration": dict(copy.deepcopy(scope), calibrations=[], purposes=["validation"])}.items():
            with self.subTest(name):
                self.assertEqual(axes(self.run_eval(use=use))["review"], "out-of-scope")

    # lifecycle axis
    def test_lifecycle_states(self):
        cases = {"unknown": dict(revocations=None),
                 "expired": dict(now=datetime.datetime(2026, 12, 1, tzinfo=datetime.UTC)),
                 "not-yet-effective": dict(now=datetime.datetime(2026, 10, 7, 23, 0, tzinfo=datetime.UTC))}
        for state, kw in cases.items():
            with self.subTest(state):
                if "now" in kw:
                    self.rev["as_of"] = kw["now"].strftime("%Y-%m-%dT%H:%M:%SZ")
                self.assertEqual(axes(self.run_eval(**kw))["lifecycle"], state)

    def test_status_source_freshness(self):
        for name, rev in {"stale": dict(self.rev, as_of="2026-10-09T10:00:00Z"),
                          "future": dict(self.rev, as_of="2026-10-09T13:00:00Z"),
                          "other source": dict(self.rev, source="elsewhere"),
                          "no list": {"as_of": self.rev["as_of"], "source": "synthetic-gate"},
                          "malformed entry": dict(self.rev, revoked=["rev-att-001"])}.items():
            with self.subTest(name):
                self.assertEqual(axes(self.run_eval(revocations=rev))["lifecycle"], "unknown")

    def test_revoked_by_id_and_declared_states(self):
        self.rev["revoked"] = [{"ref": "att-001"}]
        self.assertEqual(axes(self.run_eval())["lifecycle"], "revoked")
        self.rev["revoked"] = []
        for state in ("draft", "withdrawn"):
            a = copy.deepcopy(self.att)
            a["lifecycle"]["state"] = state
            self.assertEqual(axes(self.run_eval(a))["lifecycle"], state)
        a = copy.deepcopy(self.att)
        a["lifecycle"]["state"] = "superseded"
        self.assertFalse(self.run_eval(a)["evaluated"])
        a["lifecycle"]["superseded_by"] = "att-002"
        self.assertEqual(axes(self.run_eval(a))["lifecycle"], "superseded")

    def test_future_review_not_counted(self):
        a = copy.deepcopy(self.att)
        a["review"]["reviews"][0]["date"] = "2099-01-01"
        self.assertEqual(axes(self.run_eval(a))["review"], "unbound")

    def test_one_reviewer_two_roles_is_flagged(self):
        a = copy.deepcopy(self.att)
        a["review"]["reviews"].append(dict(a["review"]["reviews"][0], role="statistics-reviewer"))
        out = self.run_eval(a, roles=["analysis-reviewer", "statistics-reviewer"])
        self.assertIn("attestation.roles_one_reviewer", [f["code"] for f in out["findings"]])

    def test_superseded_by_only_when_superseded(self):
        a = copy.deepcopy(self.att)
        a["lifecycle"]["superseded_by"] = "att-002"
        self.assertFalse(self.run_eval(a)["evaluated"])

    def test_bad_times(self):
        a = copy.deepcopy(self.att)
        a["lifecycle"]["expires"] = a["lifecycle"]["effective"]
        self.assertFalse(self.run_eval(a)["evaluated"])

    def test_cli(self):
        files = {}
        for name, doc in {"att": self.att, "bundle": self.bundle, "recipe": RECIPE, "rev": self.rev,
                          "roles": ["analysis-reviewer"]}.items():
            files[name] = self.root / f"{name}.json"
            files[name].write_text(json.dumps(doc))
        cmd = [sys.executable, "-B", str(ROOT / "contracts" / "attestation.py"), str(files["att"]), "--bundle", str(files["bundle"]),
               "--recipe", str(files["recipe"]), "--revocations", str(files["rev"]), "--required-roles", str(files["roles"]),
               "--evidence-root", str(self.root), "--now", "2026-10-09T12:00:00Z"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(axes(json.loads(p.stdout)), {"capability": "supported", "review": "accepted-as-recorded", "lifecycle": "active"})
        self.rev["revoked"] = [{"ref": "rev-att-001"}]
        files["rev"].write_text(json.dumps(self.rev))
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0)  # evaluated; the revocation is an axis state, not an exit status
        self.assertEqual(axes(json.loads(p.stdout))["lifecycle"], "revoked")
        files["att"].write_text("{")
        self.assertEqual(subprocess.run(cmd, capture_output=True, text=True, timeout=60).returncode, 2)
        files["att"].write_text(json.dumps({"attestation_version": "1.0.0"}))
        self.assertEqual(subprocess.run(cmd, capture_output=True, text=True, timeout=60).returncode, 1)
        p = subprocess.run(cmd[:3] + ["--now", "yesterday"], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 2)
        files["att"].write_text(json.dumps(self.att))
        null = self.root / "null.json"
        null.write_text("null")
        p = subprocess.run(cmd + ["--use", str(null)], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 1)
        self.assertIn("attestation.use_malformed", p.stdout)


if __name__ == "__main__":
    unittest.main()
