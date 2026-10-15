"""covariance_fit.py tabulated-grid model (ams02-skill-upgrade WP1): fits of grid parameters to a measurement from one
gated prediction artifact per grid node. SYNTHETIC grids and data only. Criteria fixed before the runs:
- recovery: an Asimov fit recovers every parameter within 0.1 of its error (the interpolation bias); 200 seeded toys
  give a mean pull within 4 standard errors of 0 and a pull width within 0.15 of 1;
- degeneracy: a model that depends on D0/L only reports one degenerate direction within 0.05 (cosine distance) of
  (1, 1)/sqrt(2) in (ln D0, ln L), matched to the theory spec's 'D0/L', and recovers D0/L within 2% (Asimov);
  a missing or wrong theory-spec entry is a warning, not a refusal;
- refusals: no measurement (ungated) and a gate-failing prediction exit 1; a component without a covariance exits 3
  with status 'incomplete' and the component under 'missing'; a truth outside the grid exits 1, and so does an
  interpolation or start outside it."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-statistics" / "scripts"))

import covariance_fit as cf  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

SCRIPT = ROOT / "skills" / "hep-statistics" / "scripts" / "covariance_fit.py"
EDGES = [2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0]
R = np.sqrt(np.array(EDGES[:-1]) * np.array(EDGES[1:]))          # bin centres (geometric)


def _observable():
    return {"quantity": "ratio", "process": "synthetic secondary-to-primary ratio",
            "variables": [{"name": "rigidity", "unit": "GV", "edges": EDGES}],
            "phase_space": {"definition": "synthetic", "fiducial": False}, "level": "unfolded",
            "normalization": {"kind": "shape-only"}, "bin_semantics": "bin-averaged", "unit": "1",
            "validity_range": {"rigidity": [1.0, 1000.0]}}


def _envelope(aid, atype, status):
    return {"contract_version": "2.8.0", "artifact_id": aid, "artifact_type": atype,
            "objective": "SYNTHETIC grid-fit test input", "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": "0.10.1", "contracts": "2.8.0", "profiles": {}},
            "provenance": {"producer_skill": "hep-theory" if atype == "prediction" else "hep-analysis",
                           "created": "2026-10-15", "evidence_ids": []},
            "inputs": [], "outputs": [], "status": status, "unresolved_inputs": []}


def prediction(point, values, spec="theory-spec-a.json", edges=EDGES):
    aid = "synthetic-grid-" + "-".join(f"{k}{v}" for k, v in point.items())
    doc = _envelope(aid, "prediction", ["synthetic", "unvalidated"])
    obs = _observable()
    obs["variables"][0]["edges"] = edges
    doc["extension"] = {"observable": obs, "theory_spec_ref": spec, "derivation_status": "numerical-evidence",
                        "parameter_point": dict(point), "representation": "grid",
                        "values": {"edges": edges, "values": [float(v) for v in values], "unit": "1"},
                        "uncertainties": [], "allowed_transformations": []}
    return doc


def measurement(y, components):
    doc = _envelope("synthetic-grid-data", "dataset-record", ["synthetic", "unvalidated"])
    doc["extension"] = {"dataset_id": "synthetic:grid-data-synthetic", "source_evidence_ids": [],
                        "observable": _observable(),
                        "data": {"edges": EDGES, "values": [float(v) for v in y], "unit": "1",
                                 "uncertainties": components},
                        "covariance": {"status": "absent"}, "status": "synthetic"}
    return doc


def components(y, stat=0.02, corr=0.01):
    y = np.asarray(y)
    return [{"name": "stat", "kind": "statistical", "correlation": "uncorrelated", "values": (stat * y).tolist()},
            {"name": "scale", "kind": "systematic", "correlation": "fully-correlated", "values": (corr * y).tolist()}]


def cov_of(y, stat=0.02, corr=0.01):
    y = np.asarray(y)
    return np.diag((stat * y) ** 2) + np.outer(corr * y, corr * y)


def theory_spec(directions):
    doc = json.loads((ROOT / "contracts/fixtures/artifacts/valid/theory_spec_v26_propagation.json").read_text())
    doc["extension"]["degenerate_directions"] = directions
    return doc


# --- model 1: two independently constrained parameters, a (linear axis) and b (log axis)
A_NODES = np.linspace(0.5, 1.5, 11)
B_NODES = np.exp(np.linspace(math.log(0.01), math.log(1.0), 41))
TRUTH_AB = {"a": 1.0, "b": 0.3}
X1 = np.log(R)


def model_ab(a, b):
    return a * np.exp(-b * X1)


# --- model 2: a weighted-slab-like ratio that depends on L / D0 only (B/C-like: lambda / (1 + lambda))
D0_NODES = np.exp(np.linspace(0.0, math.log(10.0), 11))
L_NODES = np.exp(np.linspace(math.log(2.0), math.log(20.0), 11))
TRUTH_DL = {"D0": 4.0, "L": 8.0}


def model_dl(d0, length, scale=1.0):
    lam = 2.0 * (length / d0) * (R / 2.0) ** -0.5
    return scale * lam / (1.0 + lam)


def grid_ab():
    return [prediction({"a": float(a), "b": float(b)}, model_ab(a, b)) for a in A_NODES for b in B_NODES]


def grid_dl(scale=1.0, alt=None, spec="theory-spec-a.json"):
    out = []
    for d in D0_NODES:
        for length in L_NODES:
            pt = {"D0": float(d), "L": float(length)}
            if alt is not None:
                pt["xs_set"] = alt
            doc = prediction(pt, model_dl(d, length, scale), spec)
            out.append(doc)
    return out


AB_GRID = {"parameters": [{"name": "a", "scale": "linear"}, {"name": "b", "scale": "log"}]}
DL_GRID = {"parameters": [{"name": "D0", "scale": "log"}, {"name": "L", "scale": "log"}]}


def run_cli(doc, extra_files=None):
    with tempfile.TemporaryDirectory() as td:
        for name, content in (extra_files or {}).items():
            (Path(td) / name).write_text(json.dumps(content))
        p = Path(td) / "input.json"
        p.write_text(json.dumps(doc))
        res = subprocess.run([sys.executable, "-I", str(SCRIPT), "fit", "--input", str(p)], capture_output=True,
                             text=True, timeout=300)
    return res.returncode, json.loads(res.stdout)


class SyntheticInputsAreValidArtifacts(unittest.TestCase):
    def test_artifacts_validate(self):
        y = model_ab(**TRUTH_AB)
        for doc in (prediction({"a": 1.0, "b": 0.3}, y), measurement(y, components(y)), theory_spec(["D0/L"])):
            with self.subTest(doc["artifact_type"]):
                self.assertEqual([f.code for f in validate_artifact(doc).errors], [])


class GridRecovery(unittest.TestCase):
    """Recovery of known parameters within a stated tolerance (Asimov: 0.1 sigma; toys: pulls)."""

    @classmethod
    def setUpClass(cls):
        y = model_ab(**TRUTH_AB)
        cls.y = y
        cls.out = cf.grid_fit({"model": "tabulated-grid", "measurement": measurement(y, components(y)),
                               "predictions": grid_ab(), "grid": AB_GRID})

    def test_asimov_recovers_the_truth(self):
        f = self.out["fits"][0]
        pars = {p["name"]: p for p in f["parameters"]}
        self.assertTrue(pars["a"]["constrained"] and pars["b"]["constrained"])
        self.assertLess(abs(pars["a"]["best_fit"] - 1.0) / pars["a"]["error_coordinate"], 0.1)
        self.assertLess(abs(pars["b"]["best_fit_coordinate"] - math.log(0.3)) / pars["b"]["error_coordinate"], 0.1)
        self.assertLess(f["chi2"], 0.05)
        self.assertEqual(f["dof"], len(EDGES) - 1 - 2)
        self.assertEqual(f["degenerate_directions"], [])
        self.assertEqual(self.out["cross_section_uncertainty"]["mode"], "none")
        self.assertIn("synthetic", self.out["carried_statuses"])
        self.assertEqual(self.out["gate"], {"predictions_gated": len(A_NODES) * len(B_NODES), "comparable": len(A_NODES) * len(B_NODES)})

    def test_toy_pulls(self):
        rows = {}
        for node in grid_ab():
            pp = node["extension"]["parameter_point"]
            rows[(pp["a"], math.log(pp["b"]))] = node["extension"]["values"]["values"]
        V = np.array([[rows[(a, math.log(b))] for b in B_NODES] for a in A_NODES])
        grid = cf._Grid([A_NODES, np.log(B_NODES)], V)
        cov = cov_of(self.y)
        rng = np.random.default_rng(20261015)
        pulls = []
        for _ in range(200):
            yt = rng.multivariate_normal(self.y, cov)
            r = cf._grid_one(grid, ["a", "b"], ["linear", "log"], yt, cov, None, None, {}, [])
            pa, pb = r["parameters"]
            pulls.append([(pa["best_fit"] - 1.0) / pa["error_coordinate"],
                          (pb["best_fit_coordinate"] - math.log(0.3)) / pb["error_coordinate"]])
        pulls = np.array(pulls)
        se = 4 / math.sqrt(len(pulls))
        for j in range(2):
            self.assertLess(abs(pulls[:, j].mean()), se, pulls[:, j].mean())
            self.assertLess(abs(pulls[:, j].std(ddof=1) - 1), 0.15, pulls[:, j].std(ddof=1))


class GridDegeneracy(unittest.TestCase):
    """A ratio that depends on L / D0 only: the degenerate direction is reported with its eigenvector and the
    condition number and compared with the theory spec."""

    def fit(self, spec_dirs, combos=None, preds=None):
        y = model_dl(**{"d0": TRUTH_DL["D0"], "length": TRUTH_DL["L"]})
        doc = {"model": "tabulated-grid", "measurement": measurement(y, components(y)),
               "predictions": preds or grid_dl(), "grid": DL_GRID}
        if spec_dirs is not None:
            doc["theory_spec"] = theory_spec(spec_dirs)
        if combos:
            doc["combinations"] = combos
        return cf.grid_fit(doc)

    def test_degenerate_direction_matches_the_theory_spec(self):
        out = self.fit(["D0/L"])
        f = out["fits"][0]
        self.assertEqual(len(f["degenerate_directions"]), 1, f["fisher"]["eigen"])
        d = f["degenerate_directions"][0]
        v = np.array([d["eigenvector"]["D0"], d["eigenvector"]["L"]])
        self.assertGreater(abs(v @ np.array([1.0, 1.0]) / math.sqrt(2)), 0.95, v)
        self.assertEqual(d["matches_theory_spec"], "D0/L")
        self.assertIn("condition_number", d)
        self.assertTrue(d["condition_number"] is None or d["condition_number"] > 1e3, d["condition_number"])
        self.assertFalse(any("degenerate" in w for w in out["warnings"]), out["warnings"])
        combo = {c["name"]: c for c in f["combinations"]}["D0/L"]
        self.assertTrue(combo["constrained"])
        self.assertLess(abs(combo["value"] - 0.5) / 0.5, 0.02, combo)
        self.assertIsNotNone(combo["sigma_ln"])
        self.assertTrue(all(p["error_coordinate"] is None and not p["constrained"] for p in f["parameters"]))

    def test_mismatch_is_a_warning(self):
        out = self.fit([])                          # spec lists no degenerate direction
        self.assertTrue(any("theory spec lists none" in w for w in out["warnings"]), out["warnings"])
        out = self.fit(["D0*L"])                    # spec lists the wrong combination
        self.assertTrue(any("not among the theory spec" in w for w in out["warnings"]), out["warnings"])
        self.assertTrue(any("data constrain" in w for w in out["warnings"]), out["warnings"])
        out = self.fit(None, combos=["D0/L"])        # no spec: reported, not compared
        self.assertTrue(any("not compared" in w for w in out["warnings"]), out["warnings"])
        self.assertEqual(len(out["fits"][0]["degenerate_directions"]), 1)

    def test_declared_degeneracy_absent_in_a_constraining_fit_is_a_warning(self):
        y = model_ab(**TRUTH_AB)
        out = cf.grid_fit({"model": "tabulated-grid", "measurement": measurement(y, components(y)),
                           "predictions": grid_ab(), "grid": AB_GRID, "theory_spec": theory_spec(["a/b"])})
        self.assertTrue(any("data constrain" in w for w in out["warnings"]), out["warnings"])


class GridCrossSections(unittest.TestCase):
    def test_nuisance_mode(self):
        y = 1.05 * model_ab(**TRUTH_AB)                 # a 5% common normalization offset
        rel = (0.05 ** 2 * np.ones((7, 7))).tolist()
        out = cf.grid_fit({"model": "tabulated-grid", "measurement": measurement(y, components(y, corr=0.001)),
                           "predictions": grid_ab(), "grid": AB_GRID,
                           "multiplicative": {"relative_cov": rel, "mode": "nuisance"}})
        self.assertEqual(out["cross_section_uncertainty"]["mode"], "nuisance")
        f = out["fits"][0]
        self.assertIn("normalization_nuisance", f)
        b = f["parameters"][1]
        self.assertLess(abs(b["best_fit_coordinate"] - math.log(0.3)) / b["error_coordinate"], 0.2)
        with self.assertRaises(cf.CovFitInputError):
            cf.grid_fit({"model": "tabulated-grid", "measurement": measurement(y, components(y)), "predictions": grid_ab(),
                         "grid": AB_GRID, "multiplicative": {"relative_cov": rel, "mode": "data"}})

    def test_model_set_mode_with_envelope(self):
        y = model_dl(TRUTH_DL["D0"], TRUTH_DL["L"])
        preds = grid_dl(1.0, "set-a", "theory-spec-a.json") + grid_dl(1.1, "set-b", "theory-spec-b.json")
        prescription = {"kind": "min-max", "owner": "hep-theory", "justification": "synthetic cross-section sets"}
        out = cf.grid_fit({"model": "tabulated-grid", "measurement": measurement(y, components(y)),
                           "predictions": preds, "grid": DL_GRID, "combinations": ["D0/L"],
                           "model_set": {"alternative_key": "xs_set", "prescription": prescription}})
        self.assertEqual(out["cross_section_uncertainty"]["mode"], "model-set")
        self.assertEqual(len(out["fits"]), 2)
        env = out["envelope"]
        self.assertEqual(env["kind"], "model-alternative")
        self.assertFalse(env["gaussian"])
        j = env["columns"].index("D0/L")
        self.assertLess(env["lower"][j], env["upper"][j])
        with self.assertRaises(cf.CovFitInputError):        # no hep-theory prescription: no envelope
            cf.grid_fit({"model": "tabulated-grid", "measurement": measurement(y, components(y)), "predictions": preds,
                         "grid": DL_GRID, "model_set": {"alternative_key": "xs_set"}})


class GridRefusals(unittest.TestCase):
    def setUp(self):
        self.y = model_ab(**TRUTH_AB)
        self.base = {"model": "tabulated-grid", "measurement": measurement(self.y, components(self.y)),
                     "predictions": grid_ab(), "grid": AB_GRID}

    def test_ungated_prediction_is_refused_exit_1(self):
        doc = dict(self.base)
        del doc["measurement"]
        code, out = run_cli(doc)
        self.assertEqual(code, 1, out)
        self.assertEqual(out["status"], "refused")
        self.assertIn("ungated", out["error"])

    def test_gate_failing_prediction_is_refused_exit_1(self):
        preds = grid_ab()
        bad = prediction(preds[5]["extension"]["parameter_point"], preds[5]["extension"]["values"]["values"],
                         edges=[1.0] + EDGES[1:])
        preds[5] = bad
        code, out = run_cli(dict(self.base, predictions=preds))
        self.assertEqual(code, 1, out)
        self.assertIn("comparison gate", out["error"])
        # a parameter the measurement conditions do not state also fails the gate
        preds = grid_ab()
        for p in preds:
            p["extension"]["parameter_point"]["phi"] = 0.5
        with self.assertRaisesRegex(cf.CovFitError, "comparison gate"):
            cf.grid_fit(dict(self.base, predictions=preds))
        out = cf.grid_fit(dict(self.base, predictions=preds, gate_plan={"measurement_conditions": {"phi": 0.5}}))
        self.assertEqual(out["gate"]["comparable"], len(preds))

    def test_missing_covariance_is_incomplete_exit_3(self):
        comps = components(self.y) + [{"name": "acceptance", "kind": "systematic", "correlation": "unknown",
                                       "values": (0.01 * self.y).tolist()}]
        code, out = run_cli(dict(self.base, measurement=measurement(self.y, comps)))
        self.assertEqual(code, 3, out)
        self.assertEqual(out["status"], "incomplete")
        self.assertEqual([m["component"] for m in out["missing"]], ["acceptance"])
        meas = measurement(self.y, [])
        with self.assertRaises(cf.CovFitIncomplete) as ctx:
            cf.grid_fit(dict(self.base, measurement=meas))
        self.assertEqual(ctx.exception.missing[0]["component"], "dataset covariance")

    def test_covariance_ref_component_is_used(self):
        cov = cov_of(self.y)
        comps = [{"name": "total", "kind": "systematic", "correlation": "covariance", "covariance_ref": "cov.json"}]
        code, out = run_cli(dict(self.base, measurement="data.json", predictions=self.base["predictions"]),
                            {"data.json": measurement(self.y, comps), "cov.json": {"matrix": cov.tolist()}})
        self.assertEqual(code, 0, out)
        self.assertEqual(out["fits"][0]["covariance"]["components"][0]["ref"], "cov.json")

    def test_no_extrapolation_outside_the_grid(self):
        y = model_ab(1.7, 0.3)                             # a = 1.7 is above the grid (0.5 - 1.5)
        code, out = run_cli(dict(self.base, measurement=measurement(y, components(y))))
        self.assertEqual(code, 1, out)
        self.assertIn("outside the grid", out["error"])
        grid = cf._Grid([A_NODES, np.log(B_NODES)], np.zeros((len(A_NODES), len(B_NODES), 7)))
        with self.assertRaisesRegex(cf.CovFitError, "not extrapolated"):
            grid(np.array([1.6, math.log(0.3)]))
        with self.assertRaisesRegex(cf.CovFitError, "outside the grid"):
            cf.grid_fit(dict(self.base, start={"a": 1.0, "b": 2.0}))

    def test_incomplete_grid_is_bad_input(self):
        with self.assertRaisesRegex(cf.CovFitInputError, "full grid"):
            cf.grid_fit(dict(self.base, predictions=grid_ab()[:-1]))


if __name__ == "__main__":
    unittest.main()
