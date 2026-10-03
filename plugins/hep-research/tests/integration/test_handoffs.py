"""Section 11 handoff tests for M4: detector -> statistics (T07), ML (T16), analysis changes (T19), failure
propagation (T20), private local profile (T27), Bayesian vs frequentist (T28), and the communication handoff.

All inputs are SYNTHETIC test fixtures."""
import copy
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
for s in ("physics-ml", "hep-analysis"):
    sys.path.insert(0, str(PLUGIN / "skills" / s / "scripts"))
import check_split_integrity  # noqa: E402
import check_surrogate_domain  # noqa: E402
import review_analysis_change  # noqa: E402
from contracts.comparison.gate import gate  # noqa: E402
from contracts.project import load_project  # noqa: E402
from contracts.validate import required_statuses, validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

VALID = PLUGIN / "contracts" / "fixtures" / "artifacts" / "valid"
INVALID = PLUGIN / "contracts" / "fixtures" / "artifacts" / "invalid"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def codes(rep):
    return {f.code for f in rep.findings}


def envelope(atype, ext, status=("synthetic",), inputs=(), producer="hep-statistics"):
    return {"contract_version": "1.0.0", "artifact_id": f"fx-{atype}", "artifact_type": atype, "objective": "synthetic test",
            "provenance": {"producer_skill": producer, "created": "2026-10-02"}, "status": list(status),
            "bindings": {"experiments": [], "theory": []}, "versions": {"plugin": "0.1.0", "contracts": "1.0.0", "profiles": {}},
            "inputs": list(inputs), "outputs": [], "unresolved_inputs": [], "extension": ext}


class DetectorToStatisticsT07(unittest.TestCase):
    def test_response_with_inefficiency_and_separate_efficiency_rejected(self):
        self.assertIn("response.double_counted", codes(validate_artifact(load(INVALID / "response_double_counted.json"))))
        self.assertTrue(validate_artifact(load(VALID / "response.json")).ok)

    def test_fold_with_efficiency_inside_and_outside_rejected(self):
        o = {"quantity": "event-count", "variables": [{"name": "x", "unit": "1", "edges": [0.0, 1.0, 2.0]}], "level": "parton",
             "normalization": {"kind": "integrated-luminosity"}, "bin_semantics": "bin-integrated", "unit": "1"}
        t = [{"kind": "apply-correction", "owner": "detector-response", "effect": "efficiency", "justification": "test"},
             {"kind": "forward-fold", "owner": "hep-statistics", "truth_edges": [0.0, 1.0, 2.0], "reco_edges": [0.0, 1.0, 2.0],
              "truth_level": "parton", "includes": ["efficiency", "migration"]}]
        r = gate({"observable": o, "parameter_point": {}, "allowed_transformations": None, "status": []},
                 {"observable": dict(o, level="detector"), "status": [], "corrections": []}, t, [], {})
        self.assertFalse(r["comparable"])
        self.assertIn("efficiency", r["mismatches"][0]["reason"])


class MachineLearningT16(unittest.TestCase):
    def test_group_leakage_detected(self):
        rep = check_split_integrity.check({"train": ["e1", "e2", "e3"], "test": ["e4", "e5"],
                                           "groups": {"e1": "run1", "e2": "run2", "e3": "run3", "e4": "run3", "e5": "run4"}})
        self.assertFalse(rep["passed"])
        self.assertEqual(rep["group_leakage"], {"run3": ["test", "train"]})

    def test_surrogate_extrapolation_reported(self):
        grid = [[x / 4, y / 4] for x in range(5) for y in range(5) if not (1 <= x <= 3 and 1 <= y <= 3)]  # hole in the middle
        rep = check_surrogate_domain.check({"features": ["a", "b"], "training": grid, "queries": [[0.1, 0.9], [1.4, 0.5], [0.5, 0.5]]}, 1.5)
        self.assertEqual([q["status"] for q in rep["queries"]], ["inside", "outside", "sparse"])
        self.assertEqual(rep["queries"][1]["outside_features"], ["a"])
        self.assertFalse(rep["passed"])

    def test_auc_alone_insufficient(self):
        ml = load(VALID / "ml_artifact.json")
        ml["extension"]["downstream_validation"] = [{"metric": "ROC AUC", "value": 0.93}]
        self.assertIn("ml.auc_only", codes(validate_artifact(ml)))
        ml["extension"]["downstream_validation"].append({"metric": "signal efficiency at 1% background, per run period"})
        self.assertTrue(validate_artifact(ml).ok)
        ml["extension"]["downstream_validation"] = []
        self.assertIn("ml.no_downstream_validation", codes(validate_artifact(ml)))

    def test_surrogate_needs_training_domain(self):
        ml = load(VALID / "ml_artifact.json")
        ml["extension"].update(task="surrogate", training_domain={})
        self.assertIn("ml.no_training_domain", codes(validate_artifact(ml)))


class AnalysisChangesT19(unittest.TestCase):
    def test_legitimate_calibration_accepted_with_provenance(self):
        r = review_analysis_change.review({"id": "c1", "parameter": "energy scale", "motivation": "new calibration from Z->ee control sample",
                                           "evidence": {"control_sample": "dielectron control sample (synthetic)", "independent_of_signal_region": True},
                                           "looked_at": ["control-region data", "simulation"]})
        self.assertEqual(r["decision"], "accept")

    def test_outcome_driven_tuning_flagged_not_refused(self):
        r = review_analysis_change.review({"id": "c2", "parameter": "selection cut", "motivation": "tighten to remove the excess",
                                           "evidence": {}, "looked_at": ["signal-region data"], "after_unblinding": True})
        self.assertEqual(r["decision"], "flag")
        self.assertTrue(r["reasons"])
        self.assertIn("separate, documented variation", r["action"])

    def test_missing_provenance_asked_for(self):
        r = review_analysis_change.review({"id": "c3", "parameter": "binning", "motivation": "finer bins", "evidence": {}, "looked_at": ["simulation"]})
        self.assertEqual(r["decision"], "needs-provenance")


class FailurePropagationT20(unittest.TestCase):
    def missing_tool_run(self):
        tool = "hep-research-nonexistent-tool"
        found = shutil.which(tool) is not None or importlib.util.find_spec(tool.replace("-", "_")) is not None
        self.assertFalse(found)
        return envelope("computational-run", {"input_manifest": [], "tools": [{"name": tool, "version": "unavailable"}],
                                              "commands": [f"{tool} fit"], "environment": {}, "seeds": {}, "tolerances": {},
                                              "exit_status": 127, "output_hashes": {}}, status=["failed", "synthetic"], producer="hep-computing")

    def test_missing_tool_must_be_labeled_failed(self):
        run = self.missing_tool_run()
        self.assertTrue(validate_artifact(run).ok)
        unlabeled = copy.deepcopy(run)
        unlabeled["status"] = ["synthetic"]
        self.assertIn("status.failed_unlabeled", codes(validate_artifact(unlabeled)))

    def test_failed_status_reaches_the_result_and_the_report(self):
        ins = [{"ref": "run.json", "artifact_type": "computational-run", "status": ["failed", "synthetic"]}]
        self.assertEqual(required_statuses(ins), ["failed", "synthetic"])
        stat = envelope("statistical-result", {"paradigm": "frequentist", "likelihood": {"form": "not built"}, "parameters_of_interest": ["mu"],
                                               "nuisances": [], "test_statistic": "q(mu)", "construction": "asymptotic", "coverage": {"method": "not run"},
                                               "fit_status": "not-run"}, status=["synthetic"], inputs=ins)
        self.assertIn("status.not_propagated", codes(validate_artifact(stat)))
        stat["status"] = ["failed", "synthetic"]
        self.assertTrue(validate_artifact(stat).ok)
        comm_in = [{"ref": "result.json", "artifact_type": "statistical-result", "status": ["failed", "synthetic"]}]
        comm = envelope("communication", {"claims": [{"text": "mu = 1.02", "result_ref": "result.json", "status": ["synthetic"]}],
                                          "sources_read": [], "limitations": []}, status=["failed", "synthetic"], inputs=comm_in,
                        producer="research-communication")
        self.assertIn("communication.status_upgraded", codes(validate_artifact(comm)))
        comm["extension"]["claims"][0]["status"] = ["failed", "synthetic"]
        self.assertTrue(validate_artifact(comm).ok)

    def test_solver_failure_recorded(self):
        from scipy import optimize
        try:
            optimize.brentq(lambda x: x * x + 1.0, -1.0, 1.0)  # no root: the solver must fail
            status, fit = ["synthetic"], "converged"
        except ValueError:
            status, fit = ["failed", "synthetic"], "failed"
        stat = envelope("statistical-result", {"paradigm": "frequentist", "likelihood": {"form": "x"}, "parameters_of_interest": ["mu"],
                                               "nuisances": [], "test_statistic": "q", "construction": "asymptotic",
                                               "coverage": {"method": "none"}, "fit_status": fit}, status=status)
        self.assertEqual(fit, "failed")
        self.assertTrue(validate_artifact(stat).ok)
        stat["status"] = ["synthetic"]
        self.assertIn("status.failed_unlabeled", codes(validate_artifact(stat)))

    def test_synthetic_result_cannot_be_communicated_as_observed(self):
        ins = [{"ref": "r.json", "artifact_type": "statistical-result", "status": ["synthetic"]}]
        comm = envelope("communication", {"claims": [{"text": "x", "result_ref": "r.json", "status": ["observed", "synthetic"]}],
                                          "sources_read": [], "limitations": []}, inputs=ins, producer="research-communication")
        self.assertIn("communication.status_upgraded", codes(validate_artifact(comm)))


class PrivateLocalProfileT27(unittest.TestCase):
    def test_local_profile_validated_usable_and_absent_from_plugin(self):
        src = PLUGIN / "contracts" / "fixtures" / "projects" / "local_profile"
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td) / "my analysis"  # outside the plugin, path with a space
            shutil.copytree(src, proj)
            pj = proj / "local-profiles" / "exp-local" / "profile.json"
            prof = load(pj)
            prof.update(id="experiment:private-lab-synthetic", vocabulary_namespaces=["privlab"],
                        vocabulary_extensions={"levels": ["privlab:trigger-level"], "conventions": ["privlab:calibration_tag"]})
            pj.write_text(json.dumps(prof))
            cfg = load(proj / "hep-research.project.json")
            cfg["experiments"] = [{"profile": "experiment:private-lab-synthetic", "version": "1.0.0"}]
            cfg["overrides"] = []
            (proj / "hep-research.project.json").write_text(json.dumps(cfg))
            p = load_project(proj)
            self.assertTrue(p.report.ok, [f.as_dict() for f in p.report.findings])
            self.assertEqual([x["id"] for x in p.profiles], ["experiment:private-lab-synthetic"])
            vocab = Vocabulary.with_profiles(p.profiles)
            self.assertTrue(vocab.has("levels", "privlab:trigger-level"))
            self.assertFalse(Vocabulary().has("levels", "privlab:trigger-level"))
        hits = [f for f in PLUGIN.rglob("*") if f.is_file() and f.suffix in (".json", ".md", ".py")
                and f.resolve() != Path(__file__).resolve() and "privlab" in f.read_text(encoding="utf-8", errors="replace")]
        self.assertEqual(hits, [], "the private profile must not appear in the plugin")


class ParadigmsT28(unittest.TestCase):
    def test_bayesian_and_frequentist_requirements(self):
        self.assertTrue(validate_artifact(load(VALID / "statres_bayesian.json")).ok)
        self.assertTrue(validate_artifact(load(VALID / "statres_frequentist.json")).ok)
        self.assertIn("stats.paradigm_incomplete", codes(validate_artifact(load(INVALID / "statres_bayesian_no_priors.json"))))
        self.assertIn("stats.paradigm_mislabeled", codes(validate_artifact(load(INVALID / "statres_frequentist_with_priors.json"))))

    def test_bayesian_labeled_as_frequentist_rejected(self):
        b = load(VALID / "statres_bayesian.json")
        b["extension"]["paradigm"] = "frequentist"
        c = codes(validate_artifact(b))
        self.assertTrue({"stats.paradigm_incomplete", "stats.paradigm_mislabeled"} <= c, c)


if __name__ == "__main__":
    unittest.main()
