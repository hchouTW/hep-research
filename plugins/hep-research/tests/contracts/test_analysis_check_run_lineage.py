"""v6.3 D05d/D08 run (M2c, suite run-lineage/v1): post-execution evidence through a result binding on RUN-CHAIN,
RUN-STATUS, RUN-LINEAGE, RUN-CAMPAIGN and a blinded variant (tests/contracts/analysis_check_runs.py). V20, V33, V38, V53, V54,
V55, V56, V61, V62, V63, V70, plus V32 and the post-execution part of V60 (D10). Synthetic only: the campaign is a
core.partition campaign with LocalExecutor in a temporary folder; no record outside it is touched."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import analysis_check_cases as cases  # noqa: E402
import analysis_check_runs as runs  # noqa: E402

R = runs.ROOT_ID


def states(rep):
    return {o["obligation_id"]: (o["state"], o["reason"]) for o in rep["obligations"]}


def run_state(rep, rule):
    return states(rep)[f"{rule}:{R}"]


class Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.n = 0

    def root(self) -> Path:
        self.n += 1
        return Path(self.td.name) / f"r{self.n}"


class RunChain(Base):
    def test_pre_execution(self):
        post = runs.run_chain(self.root())
        rep = post.check(binding=False)
        for rule in ("r-run.binding", "r-run.status", "r-run.closure", "r-run.campaign", "r-run.blinding"):
            self.assertEqual(run_state(rep, rule), ("unverified", "check.not_executed"), rule)
        self.assertIn("not checked", str(rep["execution_evidence_level"]))

    def test_v53_v56_positive_declared_level(self):
        # V53: run B uses run A's product through a provenance binding; V56: self-reported manifests stay declared
        # (a 1.1.0 context: complete needs the counting-chain rules this checker runs, release R2)
        post = runs.run_chain(self.root(), spec_variant=cases.context_1_1)
        rep = post.check()
        self.assertEqual(rep["phase"], "post-execution")
        self.assertEqual(run_state(rep, "r-run.closure"), ("satisfied", "check.closure_complete"))
        self.assertEqual(run_state(rep, "r-run.status"), ("satisfied", "check.producer_succeeded"))
        self.assertEqual(run_state(rep, "r-run.binding"), ("satisfied", "check.result_bound"))
        self.assertEqual(run_state(rep, "r-run.campaign"), ("not_applicable", "check.no_campaign"))
        # the AMS example's spec is blinded (a synthetic result is permitted); the AMS-optional fallback spec is not
        blinded = (json.loads((post.root / "spec.json").read_text()).get("extension") or {}).get("blinding", {}).get("blinded")
        self.assertEqual(run_state(rep, "r-run.blinding"), ("satisfied", "check.blinding_permitted") if blinded
                         else ("not_applicable", "check.not_blinded"))
        self.assertEqual(rep["execution_evidence_level"], {R: "declared"})
        self.assertEqual(rep["status"], "complete")
        binding = next(o for o in rep["obligations"] if o["rule_id"] == "r-run.binding")
        self.assertTrue(binding["declaration_based"])  # the agent wrote the attribution (C12)
        self.assertEqual(rep["formal_use_view"]["coverage"]["value"], "partial")

    def test_v20_results_after_execution(self):
        # V20: the bundle is unchanged, the binding names no digest of itself, result identity and scope are verified
        from contracts import analysis_check as ac
        post = runs.run_chain(self.root())
        before = post.bundle_path.read_bytes()
        rep = post.check()
        self.assertEqual(post.bundle_path.read_bytes(), before)
        self.assertEqual(ac.verify(json.loads(before), post.root)["status"], "identical")
        self.assertNotIn("post/result-binding.json", {i["ref"] for i in post.bundle["items"]})
        self.assertEqual(rep["subject_digest"], post.bundle["bundle_digest"])
        for field, value, reason in (("unit", "1/(m2 s)", "check.result_identity"),
                                     ("scope", "species:proton/period:synthetic-period-2", "check.result_identity")):
            p = runs.run_chain(self.root())
            p.binding["results"][0][field] = value
            self.assertEqual(run_state(p.check(), "r-run.binding"), ("violated", reason), field)
        p = runs.run_chain(self.root())
        p.write("results/flux.json", runs.result_artifact(("synthetic",), "edited"))
        self.assertEqual(run_state(p.check(), "r-run.binding"), ("violated", "check.result_digest"))
        p = runs.run_chain(self.root())
        p.binding["analysis_bundle_sha256"] = "e" * 64
        self.assertEqual(run_state(p.check(), "r-run.binding"), ("violated", "check.binding_wrong_subject"))
        p = runs.run_chain(self.root())
        p.binding["results"] = []
        self.assertEqual(run_state(p.check(), "r-run.binding"), ("unverified", "check.result_unbound"))

    def test_v33_input_neither_frozen_nor_produced(self):
        def extra(post):
            post.write("scratch/notes.json", {"note": "an input nothing froze or produced"})
            post.rewrite_run("run-b", lambda d: d["extension"]["input_manifest"].append(
                {"path": "scratch/notes.json", "sha256": runs.sha_file(post.root / "scratch/notes.json")}))
        rep = runs.run_chain(self.root(), extra).check()
        self.assertEqual(run_state(rep, "r-run.closure"), ("violated", "check.closure_open"))

    def test_mapped_input_with_other_bytes(self):
        def other(post):
            post.write("copies/spec.json", {"not": "the frozen spec"})
            post.rewrite_run("run-a", lambda d: d["extension"]["input_manifest"].__setitem__(
                0, {"path": "copies/spec.json", "sha256": runs.sha_file(post.root / "copies/spec.json")}))
            post.binding["runs"][0]["inputs"][0]["path"] = "copies/spec.json"
        rep = runs.run_chain(self.root(), other).check()
        self.assertEqual(run_state(rep, "r-run.closure"), ("violated", "check.closure_mismatch"))

    def test_v38_json_inside_the_bundle(self):
        # V38: bytes and canonical digests are each verified; a re-serialized copy is a derived input
        def copy_of(serialize):
            def v(post):
                spec = (post.root / "spec.json").read_bytes()
                data = spec if serialize is None else serialize(json.loads(spec)).encode()
                post.write("copies/spec.json", data)
                post.rewrite_run("run-a", lambda d: d["extension"]["input_manifest"].__setitem__(
                    0, {"path": "copies/spec.json", "sha256": runs.sha_bytes(data)}))
                post.binding["runs"][0]["inputs"][0]["path"] = "copies/spec.json"
            return v
        rep = runs.run_chain(self.root(), copy_of(None)).check()
        self.assertEqual(run_state(rep, "r-run.closure"), ("satisfied", "check.closure_complete"))
        rep = runs.run_chain(self.root(), copy_of(lambda d: json.dumps(d, indent=4, sort_keys=True))).check()
        self.assertEqual(run_state(rep, "r-run.closure"), ("unverified", "check.closure_reserialized"))

    def test_v54_failed_run_and_retries(self):
        # V54: a failed execution that left output is not promoted; the binding names the adopted retry
        def failed(post):
            post.rewrite_run("run-b", lambda d: d["extension"].update(exit_status=1))
        rep = runs.run_chain(self.root(), failed).check()
        self.assertEqual(run_state(rep, "r-run.status"), ("violated", "check.failed_promoted"))

        def retries(adopt):
            def v(post):
                post.rewrite_run("run-b", lambda d: d["extension"].update(exit_status=1))
                src = [{"path": "work/counts.json", "source": {"product": {"run": "run-a", "output": "work/counts.json"}}}]
                post.add_run("run-b-retry", src, {"results/flux-retry.json": runs.result_artifact()})
                file = "results/flux.json" if adopt == "run-b" else "results/flux-retry.json"
                post.result(file, {"run": adopt})
            return v
        self.assertEqual(run_state(runs.run_chain(self.root(), retries("run-b-retry")).check(), "r-run.status"),
                         ("satisfied", "check.producer_succeeded"))
        self.assertEqual(run_state(runs.run_chain(self.root(), retries("run-b")).check(), "r-run.status"),
                         ("violated", "check.failed_promoted"))

    def test_failure_propagates_downstream(self):
        rep = runs.run_chain(self.root(), lambda p: p.rewrite_run("run-a", lambda d: d["extension"].update(exit_status=1))).check()
        self.assertEqual(run_state(rep, "r-run.status"), ("violated", "check.failed_upstream"))

    def test_v55_ambiguous_producer_cycle_and_role(self):
        # V55: rejected, or an explicit binding required
        def cycle(post):
            post.rewrite_run("run-a", lambda d: d["extension"]["input_manifest"].append(
                {"path": "results/flux.json", "sha256": runs.sha_file(post.root / "results/flux.json")}))
            post.binding["runs"][0]["inputs"].append(
                {"path": "results/flux.json", "source": {"product": {"run": "run-b", "output": "results/flux.json"}}})
        self.assertEqual(run_state(runs.run_chain(self.root(), cycle).check(), "r-run.status"), ("violated", "check.run_cycle"))

        def twice(post):
            post.binding["runs"].append(copy.deepcopy(post.binding["runs"][1]))
        self.assertEqual(run_state(runs.run_chain(self.root(), twice).check(), "r-run.status"),
                         ("violated", "check.producer_ambiguous"))

        def same_bytes(post):
            data = (post.root / "spec.json").read_bytes()
            post.write("dup/spec.json", data)
            post.rewrite_run("run-b", lambda d: d["extension"]["input_manifest"].append(
                {"path": "dup/spec.json", "sha256": runs.sha_bytes(data)}))
        self.assertEqual(run_state(runs.run_chain(self.root(), same_bytes).check(), "r-run.closure"),
                         ("unverified", "check.closure_unbound"))

    def test_v32_lock_drift(self):
        # V32: a lock in the binding that is not the bundle's is semantic drift; newly installed definitions with the
        # old snapshot available are not
        def other_lock(post):
            post.binding["semantic_lock_sha256"] = "f" * 64
        self.assertEqual(run_state(runs.run_chain(self.root(), other_lock).check(), "r-run.binding"),
                         ("violated", "check.semantic_drift"))
        from test_analysis_check_snapshots import install_new_definitions
        store = Path(self.td.name) / "snapshots"
        post = runs.run_chain(self.root(), snapshots=store)
        rep = post.check(snapshots=store, view_edit=install_new_definitions)
        self.assertEqual(rep["semantics_source"], "snapshot")
        self.assertEqual(run_state(rep, "r-run.binding"), ("satisfied", "check.result_bound"))


class RunCampaign(Base):
    def test_campaign_recorded(self):
        rep = runs.run_campaign(self.root()).check()
        self.assertEqual(run_state(rep, "r-run.campaign"), ("satisfied", "check.campaign_recorded"))
        self.assertEqual(run_state(rep, "r-run.closure"), ("satisfied", "check.closure_complete"))
        self.assertEqual(run_state(rep, "r-run.status"), ("satisfied", "check.producer_succeeded"))
        self.assertEqual(rep["execution_evidence_level"], {R: "campaign-recorded"})
        self.assertIn("agent-writable", next(o for o in rep["obligations"] if o["rule_id"] == "r-run.campaign")["message"])

    def test_v61_only_the_collected_output_is_adopted(self):
        # V61: a duplicate swapped into the chunk file is not the collected output
        def swap(post, cdir):
            (cdir / "chunks" / "c0001.json").write_text(json.dumps({"n": 4, "sum": 999}))
            runs.edit_state(cdir, lambda s: s["duplicates"].append(
                {"chunk": "c0001", "file": "outputs/c0001/c0001-a01.rerun-1.json", "kept": "c0001-a01", "identical_result": False}))
        rep = runs.run_campaign(self.root(), after=swap).check()
        self.assertEqual(run_state(rep, "r-run.campaign"), ("violated", "check.chunk_digest_conflict"))

    def test_v62_digest_conflict_uncollected_and_orphan(self):
        def conflict(post, cdir):
            ref = post.root / "runs/campaign.computational-run.json"
            art = json.loads(ref.read_text())
            art["extension"]["output_hashes"]["chunks/c0000.json"] = "0" * 64
            post.binding["campaigns"][0]["run_sha256"] = post.write("runs/campaign.computational-run.json", art)
        self.assertEqual(run_state(runs.run_campaign(self.root(), after=conflict).check(), "r-run.campaign"),
                         ("violated", "check.chunk_digest_conflict"))
        rep = runs.run_campaign(self.root(), after=lambda p, c: runs.edit_state(c, lambda s: s.pop("collected"))).check()
        self.assertEqual(run_state(rep, "r-run.campaign"), ("unverified", "check.campaign_uncollected"))
        self.assertEqual(rep["execution_evidence_level"], {R: "declared"})

        def orphan(s):
            s["submissions"][1]["status"] = "abandoned"
        rep = runs.run_campaign(self.root(), after=lambda p, c: runs.edit_state(c, orphan)).check()
        self.assertEqual(run_state(rep, "r-run.campaign"), ("unverified", "check.campaign_orphan"))
        self.assertEqual(rep["execution_evidence_level"], {R: "declared"})

    def test_v63_submission_bundle_digests(self):
        def null(s):
            s["submissions"][1]["bundle_digest"] = None
        rep = runs.run_campaign(self.root(), after=lambda p, c: runs.edit_state(c, null)).check()
        self.assertEqual(run_state(rep, "r-run.campaign"), ("unverified", "check.campaign_bundle_unrecorded"))
        self.assertEqual(rep["execution_evidence_level"], {R: "declared"})

        def differ(s):
            s["submissions"][1]["bundle_digest"] = "e" * 64
        rep = runs.run_campaign(self.root(), after=lambda p, c: runs.edit_state(c, differ)).check()
        self.assertEqual(run_state(rep, "r-run.campaign"), ("unverified", "check.campaign_bundle_unrecorded"))

        def binding_other(post, cdir):
            post.binding["campaigns"][0]["execution_bundle_sha256"] = "e" * 64
        self.assertEqual(run_state(runs.run_campaign(self.root(), after=binding_other).check(), "r-run.campaign"),
                         ("violated", "check.execution_bundle_mismatch"))

        def same_name(post, cdir):
            post.binding["campaigns"][0]["campaign_uid"] = "0123456789abcdef"
            post.binding["results"][0]["producer"] = {"campaign": "0123456789abcdef"}
        self.assertEqual(run_state(runs.run_campaign(self.root(), after=same_name).check(), "r-run.campaign"),
                         ("violated", "check.campaign_mismatch"))

    def test_merge_cross_check(self):
        def other_result(post, cdir):
            post.write("results/merged.json", {"n": 12, "sum": 67})
            post.result("results/merged.json", post.binding["results"][0]["producer"])
        self.assertEqual(run_state(runs.run_campaign(self.root(), after=other_result).check(), "r-run.campaign"),
                         ("violated", "check.merge_mismatch"))


def blinded(c):
    c.doc("spec").setdefault("extension", {})["blinding"] = {"blinded": True, "mask": {"regions": ["signal-window"]}}


class Blinding(Base):
    """V70: a blinded spec's binding cites only permitted derivatives; reports carry no result values. r-run.blinding
    1.1.0 (DR-7) judges by lineage: an 'observed' result here reads a real (published) dataset record, a synthetic one a
    synthetic record; the result's own status label is not read."""

    def check(self, status, allowed=None, data_status=None):
        data_status = data_status or ("published" if "observed" in status else "synthetic")
        post = runs.run_chain(self.root(), spec_variant=blinded, status=status, data_status=data_status)
        project = None if allowed is None else {"blinded": ["flux"], "allowed_outputs": allowed}
        rep = post.check(project=project)
        from contracts import analysis_check as ac
        text = json.dumps(rep) + json.dumps(ac.summary_page(rep))
        self.assertNotIn("123.45", text)
        return rep

    def test_v70(self):
        self.assertEqual(run_state(self.check(("observed",), []), "r-run.blinding"), ("violated", "check.blinded_result_cited"))
        self.assertEqual(run_state(self.check(("synthetic",), []), "r-run.blinding"), ("satisfied", "check.blinding_permitted"))
        rep = self.check(("observed",), ["path:results/flux.json"])
        o = next(x for x in rep["obligations"] if x["rule_id"] == "r-run.blinding")
        self.assertEqual((o["state"], o["reason"], o["declaration_based"]), ("satisfied", "check.blinding_permitted", True))
        self.assertEqual(run_state(self.check(("observed",), ["artifact:flux-proton-p1-result"]), "r-run.blinding"),
                         ("satisfied", "check.blinding_permitted"))
        self.assertEqual(run_state(self.check(("observed",), ["results/flux.json"]), "r-run.blinding"),
                         ("unverified", "check.allowed_output_ambiguous"))
        self.assertEqual(run_state(self.check(("observed",), None), "r-run.blinding"),
                         ("unverified", "check.blinding_policy_unknown"))
        # the label is not evidence either way: the lineage decides (G7)
        self.assertEqual(run_state(self.check(("synthetic",), [], data_status="published"), "r-run.blinding"),
                         ("violated", "check.blinded_result_cited"))
        self.assertEqual(run_state(self.check(("observed",), [], data_status="simulated"), "r-run.blinding"),
                         ("satisfied", "check.blinding_permitted"))


class PostExecutionPermit(Base):
    """The post-execution part of V60 (D10): the permit's artifacts list the cited results, and its execution bundle
    is the binding's; the purpose policy's evidence floor (O15); model-only bundles (O13)."""

    def scaffold(self, post, rep, policy_extra=None):
        """codes(permit) -> refusal codes of permit.report_check for this report under an accepted synthetic review."""
        import datetime
        import hashlib

        from contracts.permit import report_check
        from contracts.release_manifest import canonical_sha256
        recipe = json.loads((post.root / "recipe.json").read_text())
        ev = post.root / "evidence"
        ev.mkdir(exist_ok=True)
        (ev / "report.json").write_text(json.dumps(rep))
        scope = {"observable": "synthetic flux", "data": ["synthetic"],
                 "recipe": {"recipe_id": recipe["recipe_id"], "sha256": canonical_sha256(recipe)},
                 "calibrations": [], "assumptions": ["synthetic"], "purposes": ["formal-analysis"]}
        review = {"reviewer": "synthetic reviewer", "role": "analysis-reviewer", "date": "2026-10-15",
                  "bundle_sha256": post.bundle["bundle_digest"], "scope_sha256": canonical_sha256(scope),
                  "evidence": [{"ref": "evidence/report.json", "sha256": hashlib.sha256((ev / "report.json").read_bytes()).hexdigest()}],
                  "conclusion": "accepted", "record_ref": "review-record-1"}
        att = {"attestation_version": "1.0.0", "attestation_id": "att-v63-post",
               "subject": {"bundle_sha256": post.bundle["bundle_digest"], "scope": scope},
               "capability": {"required_capabilities": []}, "review": {"reviews": [review]},
               "lifecycle": {"state": "active", "effective": "2026-10-15T00:00:00Z", "expires": "2026-11-15T00:00:00Z",
                             "revocation_ref": "rev-att", "status_source": "synthetic-gate", "max_status_age_s": 3600}}
        policy = {"policy_version": "1.0.0", "purposes": {"formal-analysis": dict({
            "suites": [{"id": "counting-chain", "version": "1.0.0"}, {"id": "run-lineage", "version": "1.0.0"}],
            "checker_digests": [rep["assessment"]["checker"]], "accept_pre_execution_only": False}, **(policy_extra or {}))}}

        def codes(permit):
            out = report_check(att, post.bundle, post.root, post.root, policy, "formal-analysis", permit=permit,
                               now=datetime.datetime(2026, 10, 16, 12, tzinfo=datetime.UTC),
                               revocations={"as_of": "2026-10-16T11:30:00Z", "source": "synthetic-gate", "revoked": []},
                               roles=["analysis-reviewer"])
            return {r["code"] for r in out}
        return codes

    def permit(self, post, **over):
        return {"subject": dict({"analysis_bundle_sha256": post.bundle["bundle_digest"], "analysis_bundle_ref": "bundle.json",
                                 "artifacts": [post.binding["results"][0]["sha256"]]}, **over)}

    def test_v60_post_execution_bindings(self):
        post = runs.run_campaign(self.root())
        codes = self.scaffold(post, post.check())
        good = self.permit(post, execution_bundle_sha256=post.exec_digest)
        self.assertFalse({"permit.report_result_unlisted", "permit.report_execution_bundle_mismatch",
                          "permit.report_pre_execution_only", "permit.report_inconsistent"} & codes(good))
        self.assertIn("permit.report_result_unlisted", codes(self.permit(post, execution_bundle_sha256=post.exec_digest,
                                                                         artifacts=["0" * 64])))
        self.assertIn("permit.report_execution_bundle_mismatch", codes(self.permit(post, execution_bundle_sha256="e" * 64)))

    def test_evidence_floor_by_purpose(self):
        # O15: the purpose policy, not the checker, says which evidence level a root needs
        floor = {"min_evidence_level": "campaign-recorded"}
        camp = runs.run_campaign(self.root())
        self.assertNotIn("permit.report_evidence_level",
                         self.scaffold(camp, camp.check(), floor)(self.permit(camp, execution_bundle_sha256=camp.exec_digest)))
        chain = runs.run_chain(self.root())
        self.assertIn("permit.report_evidence_level", self.scaffold(chain, chain.check(), floor)(self.permit(chain)))
        self.assertNotIn("permit.report_evidence_level",
                         self.scaffold(chain, chain.check(), {"min_evidence_level": "declared"})(self.permit(chain)))

    def test_hand_raised_evidence_level_is_inconsistent(self):
        # a level that does not follow from the r-run.campaign outcomes is a hand edit (V60)
        chain = runs.run_chain(self.root())
        rep = chain.check()
        forged = dict(rep, execution_evidence_level={runs.ROOT_ID: "campaign-recorded"})
        self.assertIn("permit.report_inconsistent",
                      self.scaffold(chain, forged, {"min_evidence_level": "campaign-recorded"})(self.permit(chain)))

    def test_model_only_bundle_is_diagnostics_only(self):
        # O13: a model-only bundle never counts toward formal use
        import analysis_check_cases as cases
        from contracts.permit import report_check
        root = self.root()
        bundle = json.loads(cases.model_case(root).read_text())
        out = report_check({}, bundle, root, root, {"purposes": {}}, "formal-analysis",
                           permit={"subject": {"analysis_bundle_sha256": bundle["bundle_digest"]}})
        self.assertIn("permit.report_model_only", {r["code"] for r in out})


if __name__ == "__main__":
    unittest.main()
