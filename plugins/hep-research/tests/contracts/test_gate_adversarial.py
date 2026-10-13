"""Adversarial inputs the statistical gates must refuse (hep-statistics hardening STH-T1, audit on 0.6.15).

Every case below passed the gate it targets on main c1d375c (contracts 2.5.0): each statistical-result mutation gave
strict validation ok and publication gate 'passed', the comparison gate called a relabelled axis comparable, the
combination planner combined a dataset with itself, the covariance validator only warned on a matrix that is not
positive semidefinite after scaling, the contour scan reported out-of-domain probes as failed fits, and
result_artifact.py wrote a converged fit from an output without a status. Each case now names the component that owns
the check, the expected verdict and its reason code. The statistical-result mutations start from the published sbottom
likelihood artifact relabelled 'observed' with an analytic coverage justification (so the unmutated base passes the
gate), as evidence/probes_t1.py of the hardening order does. All inputs are SYNTHETIC placeholders."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts.comparison.combination import plan_combination  # noqa: E402
from contracts.comparison.gate import gate  # noqa: E402
from contracts.comparison.model_set import envelope  # noqa: E402
from contracts.validate import publication_gate  # noqa: E402

SBOTTOM = ROOT / "examples/stats-benchmarks/published-likelihood-sbottom/output/artifacts/statistical_result.json"


def _base() -> dict:
    d = json.loads(SBOTTOM.read_text(encoding="utf-8"))
    d["status"] = ["observed"]
    d["extension"]["coverage"] = {"check": "analytic", "method": "CLs over-covers by construction (probe base)"}
    return d


def _bayes_base() -> dict:
    d = _base()
    ext = d["extension"]
    for k in ("coverage", "expected", "test_statistic", "construction"):
        ext.pop(k, None)
    ext.update(paradigm="bayesian", parameters_of_interest=["S"], priors=[{"parameter": "S", "form": "uniform(0, 50)"}],
               sampler={"name": "metropolis", "chains": 4, "draws": 4000},
               convergence={"rhat": 1.001, "ess_bulk": 4000, "ess_tail": 3500})
    return d


def _mut(base_fn, fn):
    d = base_fn()
    fn(d["extension"], d)
    return d


def _set(**kw):
    return lambda e, d: e.update(**kw)


# name: (mutation of the extension (and document), expected gate status, reason codes that must appear)
STAT_CASES = {
    "1a_status_synthetic": (lambda e, d: d.update(status=["synthetic"], inputs=[]), "failed", ["gate.not_observed_data"]),
    "1b_status_asimov": (lambda e, d: d.update(status=["asimov"], inputs=[]), "failed", ["gate.not_observed_data"]),
    "2_toys_n1": (_set(coverage={"check": "toys", "n_toys": 1, "coverage": 0.95, "cl": 0.95}),
                  "unresolved", ["stats.coverage_toys_too_few"]),
    "3_cov_cl_mismatch": (_set(coverage={"check": "toys", "n_toys": 10000, "coverage": 0.68, "cl": 0.68}),
                          "failed", ["stats.coverage_cl_mismatch"]),
    "4_undercov_wide_interval": (_set(coverage={"check": "toys", "n_toys": 10, "coverage": 0.90, "cl": 0.95, "interval": [0.0, 0.99]}),
                                 "failed", ["stats.coverage_interval_inconsistent"]),
    "5_local_p_zero_no_bound": (_set(significance={"local_p": 0.0, "local_z": 8.0, "method": "toys"}),
                                "failed", ["stats.p_zero_without_bound"]),
    "6a_expected_deleted": (lambda e, d: e.pop("expected"), "unresolved", ["stats.expected_bands_missing"]),
    "6b_expected_median_only": (_set(expected={"median": 5.1, "method": "asimov"}), "unresolved", ["stats.expected_bands_missing"]),
    "7_p0_out_of_range": (lambda e, d: e["results"].update(p0=1.7), "failed", ["stats.p_out_of_range"]),
    "8a_z_p_inconsistent": (_set(significance={"local_z": 5.0, "local_p": 0.5}), "failed", ["stats.z_p_inconsistent"]),
    "8b_global_z_negative": (_set(significance={"local_z": 1.0, "local_p": 0.16, "global_z": -3}),
                             "unresolved", ["stats.global_z_without_p"]),
    "8c_global_z_above_local": (_set(significance={"local_z": 1.0, "local_p": 0.158655, "global_z": 2.0, "global_p": 0.02275,
                                                   "trials_method": "toys", "global_n_toys": 1000}, seeds={"toys": 1}),
                                "failed", ["stats.global_z_above_local"]),
    "9a_neyman_with_cls_results": (_set(construction="neyman"), "failed", ["stats.construction_statistic_mismatch"]),
    "9b_fc_with_q0": (_set(construction="feldman-cousins", test_statistic="q0"), "failed", ["stats.construction_statistic_mismatch"]),
    "10_toy_construction_no_seed": (_set(construction="toy-calibrated-profile"), "unresolved", ["stats.seed_missing"]),
    "11a_bad_sha": (lambda e, d: e["likelihood"].update(model_sha256="abc"), "failed", ["stats.model_sha256_malformed"]),
    "11b_blank_backend": (lambda e, d: e["likelihood"].update(backend=" "), "unresolved", ["gate.model_provenance_missing"]),
    "12_gof_p0_toys_no_ntoys": (_set(goodness_of_fit={"statistic": "saturated", "p_value": 0.0, "calibration": "toys"}),
                                "failed", ["stats.gof_toys_missing", "stats.p_zero_without_bound"]),
}

BAYES_CASES = {
    "B1_uniform_0_inf": (_set(priors=[{"parameter": "S", "form": "uniform(0, inf)"}]), "unresolved", ["stats.improper_prior"]),
    "B2_propriety_yes": (_set(priors=[{"parameter": "S", "form": "flat", "propriety": "yes"}]), "unresolved", ["stats.propriety_unsupported"]),
    "B3_prior_on_nuisance_only": (_set(priors=[{"parameter": "bkg_norm", "form": "lognormal(0,0.1)"}]), "unresolved", ["stats.poi_prior_missing"]),
    "B4_ess_bulk_3": (_set(convergence={"rhat": 1.0, "ess_bulk": 3}), "unresolved", ["stats.ess_too_low"]),
    "B5_stan_no_metadata": (_set(sampler={"name": "stan"}), "unresolved", ["stats.sampler_metadata_missing"]),
}


def _codes(g) -> set:
    return {r["code"] for r in g["reasons"]}


class BasesPass(unittest.TestCase):
    def test_unmutated_bases_pass_the_gate(self):
        for fn in (_base, _bayes_base):
            g = publication_gate(fn())
            self.assertEqual(g["status"], "passed", (fn.__name__, g["reasons"]))


class StatisticalResultMutations(unittest.TestCase):
    """STH-T1.1: each mutation is failed or unresolved at the publication gate with its own code."""

    def test_each_mutation_is_refused_with_its_code(self):
        for name, (fn, status, want) in STAT_CASES.items():
            with self.subTest(name):
                g = publication_gate(_mut(_base, fn))
                self.assertEqual(g["status"], status, g["reasons"])
                self.assertTrue(set(want) <= _codes(g), (sorted(_codes(g)), want))


class BayesianMutations(unittest.TestCase):
    """STH-T1.2: improper priors, propriety claims, POI priors, ESS floor, gradient samplers."""

    def test_each_mutation_is_refused_with_its_code(self):
        for name, (fn, status, want) in BAYES_CASES.items():
            with self.subTest(name):
                g = publication_gate(_mut(_bayes_base, fn))
                self.assertEqual(g["status"], status, g["reasons"])
                self.assertTrue(set(want) <= _codes(g), (sorted(_codes(g)), want))


def _obs(var, unit, edges, q_unit="m^-2 sr^-1 s^-1 GV^-1"):
    return {"quantity": "differential-flux", "variables": [{"name": var, "unit": unit, "edges": list(edges)}],
            "phase_space": {"definition": "full sky", "fiducial": False}, "level": "unfolded", "frame": "lab",
            "normalization": {"kind": "exposure", "value": "not-applicable"}, "bin_semantics": "bin-averaged",
            "unit": q_unit, "conventions": {}}


def _pred(obs):
    return {"observable": obs, "parameter_point": {}, "status": [], "uncertainties": [], "allowed_transformations": None}


def _meas(obs):
    return {"observable": obs, "status": [], "uncertainties": [], "covariance": "present", "corrections": []}


class ComparisonGate(unittest.TestCase):
    """STH-T1.3: variable-change needs a declared edge map and Jacobian; unit-conversion a finite factor > 0."""

    def test_relabel_of_kinetic_energy_per_nucleon_as_rigidity_is_not_comparable(self):
        pred = _pred(_obs("ekin_per_nucleon", "GeV/n", [1, 2, 5, 10], "m^-2 sr^-1 s^-1 (GeV/n)^-1"))
        meas = _meas(_obs("rigidity", "GV", [1, 2, 5, 10]))
        plan = [{"kind": "variable-change", "owner": "hep-theory", "justification": "probe", "from": "ekin_per_nucleon",
                 "to": "rigidity", "unit": "GV", "jacobian": "yes"},
                {"kind": "unit-conversion", "owner": "hep-theory", "justification": "probe",
                 "from": "m^-2 sr^-1 s^-1 (GeV/n)^-1", "to": "m^-2 sr^-1 s^-1 GV^-1", "factor": 1}]
        g = gate(pred, meas, plan, [], {})
        self.assertFalse(g["comparable"])
        self.assertIn(g["status"], ("unresolved", "not-comparable"))

    def test_variable_change_cannot_overwrite_edges(self):
        pred = _pred(_obs("rigidity", "GV", [1, 1.5, 2, 5, 10]))
        meas = _meas(_obs("rigidity", "GV", [1, 3, 7, 10]))
        plan = [{"kind": "variable-change", "owner": "hep-theory", "justification": "probe", "from": "rigidity",
                 "to": "rigidity", "unit": "GV", "jacobian": "identity", "edges": [1, 3, 7, 10]}]
        g = gate(pred, meas, plan, [], {})
        self.assertEqual(g["status"], "not-comparable")

    def test_unit_conversion_factor_must_be_finite_and_positive(self):
        for f in (-3, 0, math.nan, math.inf):
            with self.subTest(factor=f):
                pu = _pred(_obs("rigidity", "GV", [1, 1.5, 2, 5, 10], "cm^-2 sr^-1 s^-1 GV^-1"))
                mu = _meas(_obs("rigidity", "GV", [1, 1.5, 2, 5, 10]))
                g = gate(pu, mu, [{"kind": "unit-conversion", "owner": "hep-theory", "justification": "probe",
                                   "from": "cm^-2 sr^-1 s^-1 GV^-1", "to": "m^-2 sr^-1 s^-1 GV^-1", "factor": f}], [], {})
                self.assertFalse(g["comparable"])


class CombinationAndEnvelope(unittest.TestCase):
    """STH-T1.4: duplicate dataset ids and envelope rows of unequal length."""

    def test_duplicate_dataset_id_is_not_combinable(self):
        o = _obs("rigidity", "GV", [1, 2, 5, 10])
        ds = {"id": "alpha:A", "observable": o, "covariance": "present", "auxiliary": [], "uncertainties": []}
        r = plan_combination([dict(ds), dict(ds)], [{"between": ["alpha:A", "alpha:A"], "independent": True,
                                                    "assumption": {"justification": "probe", "scope": "probe"}}])
        self.assertFalse(r["combinable"])
        self.assertEqual(r["treatment"], "comparison-only")

    def test_envelope_refuses_unequal_rows(self):
        ms = {"ok": True, "alternatives": [{"id": "a"}, {"id": "b"}]}
        env = envelope(ms, {"a": [1, 2, 3, 4], "b": [1, 2]}, {"kind": "min-max", "owner": "hep-theory", "justification": "probe"})
        self.assertFalse(env["ok"])


def _run(args, doc=None):
    with tempfile.TemporaryDirectory() as td:
        if doc is not None:
            p = Path(td) / "in.json"
            p.write_text(json.dumps(doc))
            args = [str(p) if a == "@IN" else a for a in args]
        cp = subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=td, timeout=600)
    try:
        js = json.loads(cp.stdout)
    except ValueError:
        js = {}
    return cp, js


def _cov_codes(js):
    return {x.get("code") for x in js.get("errors", []) + js.get("warnings", []) if isinstance(x, dict)}


class CovarianceScaleInvariance(unittest.TestCase):
    """STH-T1.5: PSD and rank checks on the correlation matrix, not on the raw scale."""
    VC = str(ROOT / "core/stats/validate_covariance.py")

    def test_scaled_non_psd_matrix_fails(self):
        rho = [[1, 0.9, 0.9, 0], [0.9, 1, -0.9, 0], [0.9, -0.9, 1, 0], [0, 0, 0, 1]]
        sig = [0.01, 0.01, 0.01, 100]
        c = [[rho[i][j] * sig[i] * sig[j] for j in range(4)] for i in range(4)]
        cp, js = _run([self.VC, "@IN"], {"labels": ["a", "b", "c", "d"], "matrix": c, "kind": "absolute"})
        self.assertEqual(cp.returncode, 1, cp.stdout[-400:])
        self.assertIn("not_psd", _cov_codes(js))

    def test_diagonal_of_disparate_scales_is_fine(self):
        cp, js = _run([self.VC, "@IN"], {"labels": ["a", "b"], "matrix": [[1e-20, 0], [0, 1e20]], "kind": "absolute"})
        self.assertFalse({"rank_deficient", "ill_conditioned"} & _cov_codes(js), js)


class ContourDomain(unittest.TestCase):
    """STH-T1.6: probes where a bin mean is <= 0 are outside the domain, not failed fits."""

    def test_three_bin_contour_is_ok(self):
        two = {"bins": [{"n": 20, "b": 10, "s1": 5, "s2": 1}, {"n": 15, "b": 10, "s1": 1, "s2": 5},
                        {"n": 12, "b": 10, "s1": 2, "s2": 2}]}
        cp, js = _run([str(ROOT / "core/stats/likelihood_limits.py"), "contour", "--input", "@IN"], two)
        self.assertEqual(cp.returncode, 0, cp.stdout[-600:])
        self.assertEqual(js.get("status"), "ok")


class ResultArtifactRefusals(unittest.TestCase):
    """STH-T1.7: an output without a status is not a converged fit; not-checked coverage carries no value."""
    RA = str(ROOT / "skills/hep-statistics/scripts/result_artifact.py")
    LM = str(ROOT / "skills/hep-statistics/scripts/li_ma_significance.py")

    def _li_ma(self, td, status=None):
        cp = subprocess.run([sys.executable, self.LM, "--on", "30", "--off", "100", "--alpha", "0.1"],
                            capture_output=True, text=True, timeout=120)
        out = json.loads(cp.stdout)
        if status is not None:
            out["status"] = status
        p = Path(td) / "lm.json"
        p.write_text(json.dumps(out))
        return p

    def _ra(self, td, *extra, status=None):
        p = self._li_ma(td, status)
        return subprocess.run([sys.executable, self.RA, "--cli-output", str(p), "--poi", "s", "--construction", "asymptotic",
                               "--test-statistic", "li-ma", "--label", "observed", "--artifact-id", "probe",
                               "--out", str(Path(td) / "r.json"), *extra], capture_output=True, text=True, timeout=120)

    def test_missing_status_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            cp = self._ra(td)
            self.assertEqual(cp.returncode, 2, cp.stdout + cp.stderr)
            self.assertFalse((Path(td) / "r.json").exists())

    def test_not_checked_with_a_coverage_value_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            cp = self._ra(td, "--coverage-check", "not-checked", "--coverage-value", "0.95", status="ok")
            self.assertEqual(cp.returncode, 2, cp.stdout + cp.stderr)


if __name__ == "__main__":
    unittest.main()
