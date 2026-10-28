#!/usr/bin/env python3
"""Multi-dataset propagation fit through a cr-provider/1 provider (cr-propagation C2). Needs NumPy and SciPy.

One fit of cosmic-ray transport parameters to several datasets at once. Predictions come only from a provider listed
in the registry the caller passes in (core/provider; --provider-registry), evaluated as a subprocess and cached; the fit
never computes a propagation itself. Every dataset is a dataset-record artifact: its values, bins and uncertainty
components are read from it, its covariance is assembled from the components (covariance_fit.data_covariance; a
dataset without one stops the fit with status incomplete, exit 3, never a diagonal matrix, R7), and the provider's
prediction at the start point is gated against it (contracts/comparison/gate.py) before anything is fitted (R5);
the parameters sent to the provider are passed to the gate as conditions, and every other parameter_point key (for
example a cross-section set) must be stated in gate_plan.measurement_conditions.

Bin semantics are checked first, explicitly, on both sides: a ratio is the P2 quantity (ratio of the bin-integrated
numerator and denominator) when declared bin-integrated, or bin-averaged with a convention stating the ratio of
bin-integrated fluxes (as the USINE provider does), and has no binning convention of its own; otherwise its
bin_semantics and every binning convention (a convention key containing "bin") must be the same on both sides. A
provider that returns bin averages of the ratio (for example averaged in ln(E/n) under a profile convention) is never
fitted to P2 data, nor a P2 provider to such data: refused (exit 1), because a ratio-only provider has no primary
spectra to convert with. Parameter_point keys that only record how the provider ran a point (run_record_keys, for
example a run name and the code's substitutions) are kept in the gate record and not compared.

Model (one shared LIS for all datasets; the provider's components carry the cross-section structure):
  mu_d(theta, nu) = sum_c m_c(nu) comp_{d,c}(theta),
theta the transport parameters (canonical names of the provider domain, fitted in ln p on a log axis or p), comp the
provider's components of dataset d (one per production channel for a decomposable provider), m_c a multiplier acting
on channel c: a production-cross-section norm (P15, kind production-norm, prior about 10%) or a parent source
abundance (P14, kind parent-abundance, free or with a prior). At most one multiplier per channel (two would be exactly
degenerate). Norm-type changes are applied after propagation, as P5 allows; an inelastic norm or energy scale and a
production slope need a provider parameter or energy-basis components and are refused for a provider without them.
-2 ln L = sum_d r_d^T C_d^-1 r_d + sum_n ((nu_n - aux_n) / sigma_n)^2, r_d = y_d - mu_d. The multipliers enter
linearly, so they are profiled exactly (linear least squares, bounded to NU_BOUNDS) at every theta. A provider that
is not decomposable (for example one USINE run per point) gives one pseudo-component, its prediction; multipliers are
then refused (reason not-decomposable). A transport block (contracts ext_theory_spec transport) given under
"transport" is sent with every request, so every family shares it.
A provider with numerical noise (for example tables printed with 6 significant digits) needs difference steps well
above it: parameters.<name>.step is the step in the fit coordinate used for the Jacobian, the Fisher matrix and the
convergence verdict (default: the optimizer's own steps and 1e-4 x max(1, |t|)).
Solar modulation: a dataset with a "period" asks for phi_<period>_gv, applied per isotope through the force-field tool
contract before ratios are formed (P4); a provider that returns only ratios cannot be modulated, so such a dataset is
refused (exit 1, reason modulation-needs-isotopic-lis).

Model families are declarative: {"name", "free": [...], "fixed": {...}}. A family whose parameters are outside the
provider's domain (for example BIG or SLIM with V_A_kms or R_break_gv for a closed form without them) is listed as not
expressible, with the names, never dropped. Each expressible family is fitted (scipy least_squares in the fit
coordinates, bounded by the provider domain); convergence is judged by core/stats/fit_diagnostics.py (newton_fit
verdict on the profiled -ln L; a coordinate on a domain bound is checked with boundary_kkt instead); an unconverged fit
is restarted from a perturbed start at most 5 times (reason restart-cap). Exactly flat directions (Fisher screen of
degeneracy.py) are held at their best fit for the verdict: a position along them is not a measurement. Degeneracies:
Fisher screen and, on request, profile scans by degeneracy.py (object form; only profile-scan entries carry a
valid_range and go to the fit-derived theory-spec).

Toys, family calibration and posteriors would need far more provider evaluations than the campaign budget allows, so
they use a response model: a tensor Chebyshev interpolation of the provider components (in ln of the component when
it is positive) on a box of +-k sigma around the expansion point, built from provider evaluations at the nodes (1 to
3 coordinates), or with kind "polynomial" a total-degree Chebyshev polynomial fitted to provider evaluations at
scrambled Sobol design points (1 to 6 coordinates, at least twice as many points as terms), and refused unless its largest error at random provider points in the box is below tolerance_sigma of the data sigma in
every bin. Its per-bin error enters the toy and posterior covariance as an uncorrelated component (P10); a fit that
leaves the box is a failed toy, a chain step outside it is rejected and counted. The reported fits never use it.
Kind "provider" uses no response model: toys and families evaluate the provider itself (meant for a provider that is
already a validated emulator, whose error the caller adds to the data covariance, P10); a point it refuses as out of
its domain fails that toy. For the family calibration, layout "union" (default) builds one model on the box spanning every family's best fit
+- k sigma; layout "joint" the same box with k times the largest sigma of any family around every best fit (so a
family's fit to another's null, which sits near that family's best fit, has its margin without a rebuild); layout
"per-center" builds one model per best fit (+- k times the largest sigma), each validated on its own, and fits each
family to a null family's toys with the model whose box holds that family's fit to the null (the error component
recorded is the largest of the models'). Per-center boxes suit families whose fits to each other's toys stay near
their best fits; a parameter that is not identifiable under another family's null (V_A near 0 under SLIM toys) spreads
those fits beyond the box, which then fail as toys.
- toys: declared with core/stats/toy_ensemble.py (EnsembleSpec, toy_seed, coverage); plug-in at a true point, the
  auxiliary values of the priors redrawn per toy; covered when the profile delta chi2 at the true value is <= 1
  (Wilks); for a parameter on a bound the critical value is calibrated with the toys (its 68.27% quantile), as in
  covariance_fit.py break-scan. Tested quantities: parameters and "flattest", the Fisher eigen-direction with the
  smallest eigenvalue in the fit coordinates. An unconverged toy is failed; the study stops once more than 2% of the
  toys failed (status failed). Coverage tolerance: z_m sqrt(p(1-p)/n), z_m = Phi^-1(1 - 0.0027/(2m)) for m tested
  quantities (Bonferroni at the familywise 3-sigma level); the uncorrected 3-sigma verdict is reported too.
- families: delta chi2 of each family against the best one, calibrated with toys generated from that family's best
  fit (no Wilks: families need not be nested, and a parameter undefined under the null is the Davies case); a family
  survives when the toy p-value is >= alpha.
- posterior: random-walk Metropolis in the fit coordinates (flat priors in the box, Gaussian priors of the
  multipliers), at most 2e5 steps per chain; bayes_diagnostics.py diagnose; no interval unless R-hat <= 1.01 and bulk
  and tail ESS >= 400 (status unvalidated).
- covariance alternatives (P9): the covariance of one dataset rebuilt by build_covariance.py's build with one source's
  correlation length set to each value of "lengths"; each is a separate fit, reported side by side, never combined.

Input (fit --input CONFIG.json; relative paths are read from the config's folder):
 {"provider": {"id", "version"},
  "datasets": [{"name", "measurement": "record.json" | {dataset-record}, "observable": "B/C", "period": optional}],
  "gate_plan": {"measurement_conditions", "mappings", "transformations"} (optional, contracts/comparison/gate.py),
  "parameters": {name: {"start": x, "scale": "log" | "linear", "step": optional}}, "fixed": {name: value},
  "nuisances": [{"name", "kind": "production-norm" | "parent-abundance", "channel": "C->B" | "parent": "O",
                 "prior_sigma": 0.1 | null, "aux": 1.0}],
  "families": [{"name", "free": [...], "fixed": {...}}]   (default: one family, every parameter free),
  "optimizer": {"max_iterations": 100, "max_restarts": 5, "seed": 0},
  "degeneracy_scan": {"family", <degeneracy.py scan keys>}, "theory_spec": "base-theory-spec.json",
  "intervals": [names]   (profile delta chi2 = 1 intervals with the provider; an end on a domain bound is kind "bound"),
  "covariance_alternatives": {"family", "dataset", "model": {build_covariance sources}, "source", "lengths": [...]},
  "response_model": {"kind": "tensor" | "polynomial" | "provider", "nodes": 7, "degree": 4, "design_points": 128,
                     "half_width_sigma": 5, "validation_points": 12, "tolerance_sigma": 0.02,
                     "layout": "union" | "joint" | "per-center"},
  "provider_requests": "per-dataset" (default) | "per-point" (one request and one provider run per point for every
                       dataset; distinct observable ids, a provider that is not decomposable),
  "transport": {transport block} | "transport.json", "run_record_keys": [parameter_point keys],
  "computational_runs": "folder holding the provider's computational-run artifacts" (optional),
  "toys": {"family", "n", "seed", "truth": {name: value}, "test": [names | "flattest"]},
  "family_toys": {"n", "seed", "alpha": 0.05}, "posterior": {"family", "chains": 4, "steps", "seed"}}
Output: one JSON object on stdout (status, fits, families, degeneracies, toys and family toys with their per-toy rows,
posterior, provider_evaluations with the provider's evaluation record of every result used and, with
computational_runs, each computational-run reference resolved with the tool versions it names, ...);
with --out DIR also result.json, statistical-result.json and, when a base theory-spec is given, theory-spec.json (both
validated with contracts/validate.py; the toy seeds are in extension.seeds and coverage.seed). Labels of the data and of the provider (synthetic, unvalidated, user-supplied,
outside-validated-range) carry to the result.

Usage:
  python3 propagation_fit.py fit --input CONFIG.json --provider-registry REGISTRY.json [--cache-dir DIR]
      [--out DIR] [--max-evaluations 2000] [--allow-outside-validated-range]
The registry comes from tools/provider_registry.py --write; the cache (core/provider) keeps provider results between
runs; --max-evaluations caps the provider point evaluations of the run (status failed, reason evaluation-budget).
Exit codes: 0 done; 1 refused or failed (gate, bin semantics, out-of-domain start, restart cap, toy-failure threshold,
response model above tolerance, evaluation budget, modulation without isotopic LIS); 2 bad input or NumPy/SciPy
missing; 3 incomplete (a dataset covariance is missing). Output JSON labelled [General method].
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
import warnings
from datetime import date
from pathlib import Path

try:  # --help works without them; main() refuses to run without them
    import numpy as np
    from scipy import optimize
    from scipy.stats import chi2 as chi2_dist
    from scipy.stats import norm as norm_dist
except ImportError:  # pragma: no cover
    np = optimize = chi2_dist = norm_dist = None  # type: ignore[assignment]

sys.dont_write_bytecode = True
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(Path(__file__).resolve().parent))

LABEL = "[General method]"
MAX_RESTARTS = 5            # restarts per optimization (r3 C2 loop limit)
TOY_FAILURE_LIMIT = 0.02    # stop a toy study once more than this fraction of its toys failed
MAX_CHAIN_STEPS = 200_000   # steps per chain
RHAT_MAX, ESS_MIN = 1.01, 400
MAX_OUTSIDE_FRACTION = 1e-3  # proposals outside the response box above which a posterior is not reported
MARGIN_TOL = 0.02           # joint and per-center layouts: a margin short by this fraction of a half-width still holds
FAMILYWISE_ALPHA = 0.0027   # two-sided 3-sigma
NOMINAL = 0.6827
EXACT_FLAT = 1e-8           # eigenvalue ratio of an exactly flat direction (held for the convergence verdict)
NU_BOUNDS = (1e-3, 10.0)    # multipliers of components
AXES = {"kinetic_energy_per_nucleon": ("ekn", "GeV/n"), "rigidity": ("rigidity", "GV")}
SUPPORTED_NUISANCES = ("production-norm", "parent-abundance")
REFUSED_NUISANCES = {"inelastic-norm": "an inelastic cross-section change needs a new propagation (P5)",
                     "inelastic-scale": "an inelastic cross-section change needs a new propagation (P5)",
                     "production-slope": "an energy-dependent production change needs energy-basis components or a "
                                         "new propagation (P5)"}
CONFIG_KEYS = {"provider", "datasets", "gate_plan", "parameters", "fixed", "nuisances", "families", "optimizer",
               "degeneracy_scan", "theory_spec", "covariance_alternatives", "response_model", "toys", "family_toys",
               "posterior", "intervals", "transport", "computational_runs", "run_record_keys", "provider_requests"}
TOTAL_COMPONENT = "total"   # the one pseudo-component of a provider that is not decomposable
# a ratio declared bin-averaged whose conventions state the ratio of bin-integrated fluxes is the P2 quantity
P2_STATEMENT = re.compile(r"ratio of (the )?bin-integrated", re.IGNORECASE)


class FitInputError(ValueError):
    """Unusable input (exit 2)."""


class FitRefused(RuntimeError):
    """A negative verdict (exit 1): the input or a result is refused, with a reason code."""

    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


class FitIncomplete(RuntimeError):
    """A needed input is missing (exit 3)."""

    def __init__(self, detail: str, missing):
        super().__init__(detail)
        self.missing = missing


# --------------------------------------------------------------------------- small helpers
def _num(x, what) -> float:
    if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x):
        raise FitInputError(f"{what} must be a finite number")
    return float(x)


def _int(x, what, lo, hi) -> int:
    if not isinstance(x, int) or isinstance(x, bool) or not lo <= x <= hi:
        raise FitInputError(f"{what} must be an integer in [{lo}, {hi}]")
    return x


def _keys(doc, allowed, what) -> dict:
    if not isinstance(doc, dict):
        raise FitInputError(f"{what} must be a JSON object")
    extra = sorted(set(doc) - set(allowed))
    if extra:
        raise FitInputError(f"{what}: unknown keys {extra}; allowed {sorted(allowed)}")
    return doc


def _load(ref, base: Path, what: str):
    if isinstance(ref, dict):
        return ref
    if not isinstance(ref, str):
        raise FitInputError(f"{what} must be a JSON object or a path")
    path = Path(ref) if Path(ref).is_absolute() else base / ref
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FitInputError(f"cannot read {what} {path}: {exc}") from None


def _to_fit(value: float, scale: str) -> float:
    return math.log(value) if scale == "log" else float(value)


def _natural(t: float, scale: str) -> float:
    return float(math.exp(t)) if scale == "log" else float(t)


def _r(x):
    return None if x is None else float(f"{float(x):.10g}")


# --------------------------------------------------------------------------- datasets
class Dataset:
    def __init__(self, name, record, observable, base: Path, period=None):
        from covariance_fit import CovFitIncomplete, CovFitInputError, data_covariance
        self.name, self.record, self.observable, self.period = name, record, observable, period
        if not isinstance(record, dict) or record.get("artifact_type") != "dataset-record":
            raise FitInputError(f"dataset {name}: the measurement must be a dataset-record artifact")
        ext = record.get("extension") or {}
        values = (ext.get("data") or {}).get("values")
        edges = (ext.get("data") or {}).get("edges")
        obs = ext.get("observable") or {}
        variables = obs.get("variables") or []
        if not isinstance(values, list) or not isinstance(edges, list) or len(edges) != len(values) + 1 or not values:
            raise FitInputError(f"dataset {name}: data.values and data.edges (one more edge than values) are required")
        if len(variables) != 1 or variables[0].get("name") not in AXES:
            raise FitInputError(f"dataset {name}: one binned variable, one of {sorted(AXES)}")
        self.axis, self.unit = AXES[variables[0]["name"]]
        if variables[0].get("unit") != self.unit:
            raise FitInputError(f"dataset {name}: variable unit {variables[0].get('unit')!r}, expected {self.unit}")
        self.y = np.asarray(values, dtype=float)
        self.edges = [float(e) for e in edges]
        if not np.all(np.isfinite(self.y)) or any(b <= a for a, b in zip(self.edges, self.edges[1:])):
            raise FitInputError(f"dataset {name}: finite values and increasing edges")
        self.bin_semantics = obs.get("bin_semantics")
        self.conventions = obs.get("conventions") or {}
        self.labels = [s for s in (record.get("status") or []) if isinstance(s, str)]
        try:
            cov, self.cov_info = data_covariance(ext, base, len(self.y))
        except CovFitIncomplete as exc:
            raise FitIncomplete(f"dataset {name}: {exc}", [dict(m, dataset=name) for m in exc.missing]) from None
        except CovFitInputError as exc:
            raise FitInputError(f"dataset {name}: {exc}") from None
        self.set_covariance(cov)

    def set_covariance(self, cov) -> None:
        cov = np.asarray(cov, dtype=float)
        try:
            self.chol = np.linalg.cholesky(cov)
        except np.linalg.LinAlgError:
            raise FitRefused("covariance-not-positive-definite", f"dataset {self.name}: the covariance is not positive "
                             "definite; nothing is regularized") from None
        self.cov = cov
        self.sigma = np.sqrt(np.diag(cov))

    def observable_request(self) -> dict:
        return {"id": self.observable, "axis": self.axis, "unit": self.unit,
                "bins": [[a, b] for a, b in zip(self.edges, self.edges[1:])]}


# --------------------------------------------------------------------------- provider evaluations
class Evaluator:
    """Components per dataset at one transport point, through core/provider (memo plus the runner's disk cache)."""

    def __init__(self, runner, provider_id, version, datasets, fixed, max_evaluations, decomposable=True,
                 transport=None, per_point=False):
        self.runner, self.provider_id, self.version = runner, provider_id, version
        self.datasets, self.fixed, self.max_evaluations = datasets, dict(fixed), int(max_evaluations)
        self.decomposable, self.transport = bool(decomposable), transport
        # provider_requests "per-point": one request names every dataset's observable (distinct ids), one run per point
        self.groups = [list(datasets)] if per_point else [[ds] for ds in datasets]
        self.memo: dict = {}
        self.labels: set = set()
        self.channels: list[str] | None = None
        self.first_predictions: dict = {}
        self.records: list = []   # one per provider result (point x dataset): its evaluation record

    @property
    def points_sent(self) -> int:
        return int(self.runner.stats["points_sent"])

    def point(self, values: dict) -> dict:
        out = dict(self.fixed)
        out.update({k: float(v) for k, v in values.items()})
        return out

    def components(self, values: dict) -> dict:
        """{dataset name: array (channels x bins)} at the point fixed + values; FitRefused on any provider failure."""
        pt = self.point(values)
        key = tuple(sorted((k, repr(float(v))) for k, v in pt.items()))
        if key in self.memo:
            return self.memo[key]
        out = {}
        for group in self.groups:
            if self.points_sent >= self.max_evaluations:
                raise FitRefused("evaluation-budget", f"the run reached --max-evaluations {self.max_evaluations} "
                                 "provider point evaluations (decision D7 budget); nothing more is evaluated")
            req = {"protocol": "cr-provider/1", "provider": self.provider_id, "provider_version": self.version,
                   "points": [pt], "observables": [ds.observable_request() for ds in group],
                   "want": ["lis", "components"] if self.decomposable else ["lis"], "seed": None}
            if self.transport is not None:
                req["transport"] = self.transport
            resp = self.runner.evaluate(req)
            res_all = (resp.get("results") or [None])[0]
            if resp.get("status") != "ok" or not isinstance(res_all, dict) or res_all.get("status") != "ok":
                reason = (res_all or {}).get("reason") or resp.get("reason") or "provider-failed"
                detail = (res_all or {}).get("detail") or resp.get("detail") or ""
                raise FitRefused(reason, f"provider {self.provider_id} at {pt}: {reason} {detail}".strip())
            preds = res_all.get("predictions") or []
            if len(preds) != len(group) or any(
                    not np.allclose(p["values"].get("edges", ds.edges), ds.edges, rtol=1e-9, atol=0)
                    for p, ds in zip(preds, group)):
                raise FitRefused("invalid-response", f"provider {self.provider_id} at {pt}: the predictions do not "
                                 f"match the requested observables {[ds.observable for ds in group]} in order")
            self.labels.update(res_all.get("labels") or [])
            evaluation = res_all.get("evaluation") or {}
            self.records.append({**({"dataset": group[0].name} if len(group) == 1 else
                                    {"datasets": [ds.name for ds in group]}),
                                 "point": dict(pt), "input_hash": evaluation.get("input_hash"),
                                 "computational_run_ref": evaluation.get("computational_run_ref"),
                                 "labels": sorted(res_all.get("labels") or [])})
            for ds, pred in zip(group, preds):
                out[ds.name] = self._components_of(ds, res_all, pred)
        self.memo[key] = out
        return out

    def _components_of(self, ds, res, pred):
        """(channels x bins) of one dataset's prediction; FitRefused when they cannot carry the multipliers."""
        if not self.decomposable:   # one pseudo-component, the prediction itself; it carries no multiplier
            res = dict(res, components=[{"id": TOTAL_COMPONENT, "values": pred["values"]["values"]}])
        comps = sorted(res.get("components") or [], key=lambda c: c["id"])
        names = [c["id"] for c in comps]
        if not names:
            raise FitRefused("not-decomposable", f"provider {self.provider_id} returned no components")
        if self.channels is None:
            self.channels = names
        elif names != self.channels:
            raise FitRefused("invalid-response", f"components changed between points: {names} vs {self.channels}")
        arr = np.array([c["values"] for c in comps], dtype=float)
        total = np.asarray(pred["values"]["values"], dtype=float)
        tol = 10 * float(res["evaluation"].get("numerical_tolerance") or 1e-9) + 1e-12
        if not np.allclose(arr.sum(axis=0), total, rtol=tol, atol=0):
            raise FitRefused("components-do-not-add-up", f"dataset {ds.name}: the components do not add up to the "
                             "prediction; they cannot carry the cross-section multipliers")
        if ds.name not in self.first_predictions:
            self.first_predictions[ds.name] = (pred, sorted(res.get("labels") or []))
        return arr


def binning_meaning(observable: dict):
    """What a binned value means, for the bin-semantics guard. A ratio is the P2 quantity (ratio of the bin-integrated
    numerator and denominator, equal to the ratio of their bin averages) when it is declared bin-integrated, or
    bin-averaged with a convention that states the ratio of bin-integrated fluxes, and carries no binning convention
    of its own (a convention key containing 'bin', such as a ratio averaged in ln(E/n)). Anything else is its
    bin_semantics together with its binning conventions, matched exactly."""
    sem = observable.get("bin_semantics")
    conv = observable.get("conventions") or {}
    own = {k: v for k, v in conv.items() if "bin" in k}
    stated = any(isinstance(v, str) and P2_STATEMENT.search(v) for v in conv.values())
    if observable.get("quantity") == "ratio" and not own and (
            sem == "bin-integrated" or (sem == "bin-averaged" and stated)):
        return "ratio of bin integrals (P2)", {}
    return sem, own


def _gate(ds: Dataset, pred: dict, labels, plan: dict, registry_entry, point_keys, run_record_keys=()) -> dict:
    """Explicit bin-semantics check (P2), then contracts/comparison/gate.py, on the provider's prediction."""
    from contracts import CONTRACTS_VERSION
    from contracts.comparison.gate import check as gate_check
    obs = pred.get("observable") or {}
    p_sem, p_own = binning_meaning(obs)
    d_sem, d_own = binning_meaning(ds.record["extension"].get("observable") or {})
    if p_sem != d_sem:
        raise FitRefused("bin-semantics-mismatch",
                         f"dataset {ds.name} is declared {ds.bin_semantics!r} ({d_sem}), provider "
                         f"{registry_entry.provider_id} returns {obs.get('bin_semantics')!r} values ({p_sem}); a ratio "
                         "of bin integrals (P2) and a bin-averaged ratio are different quantities, and a ratio-only "
                         "provider has no spectra to convert one into the other")
    missing = sorted(k for k in set(p_own) | set(d_own) if p_own.get(k) != d_own.get(k))
    if missing:
        raise FitRefused("bin-semantics-mismatch", f"dataset {ds.name} and provider {registry_entry.provider_id} do "
                         f"not declare the binning convention(s) {missing} with the same meaning")
    aligned = None
    if p_sem == "ratio of bin integrals (P2)" and obs.get("bin_semantics") != ds.bin_semantics:
        # the same P2 quantity under two labels (bin-averaged fluxes or bin-integrated fluxes, the ratio is the same):
        # the gate compares labels, so it sees the data's label; recorded in the gate record
        aligned = {"from": obs.get("bin_semantics"), "to": ds.bin_semantics, "meaning": p_sem}
        pred = dict(pred, observable=dict(obs, bin_semantics=ds.bin_semantics))
    comp = registry_entry.component
    bindings = {"experiments": [], "theory": []}
    if comp.startswith("theory:"):
        bindings["theory"] = [{"profile": comp, "version": registry_entry.version}]
    doc = {"contract_version": CONTRACTS_VERSION, "artifact_id": f"provider-{registry_entry.provider_id}-{ds.name}",
           "artifact_type": "prediction", "objective": f"prediction of provider {registry_entry.provider_id} for "
           f"dataset {ds.name} at the start point of a propagation fit", "bindings": bindings,
           "versions": {"plugin": "", "contracts": CONTRACTS_VERSION, "profiles": {}},
           "provenance": {"producer_skill": "hep-statistics", "created": date.today().isoformat(), "evidence_ids": []},
           "inputs": [], "outputs": [], "status": list(labels), "unresolved_inputs": [], "extension": pred}
    pp = pred.get("parameter_point") or {}
    cond = dict((plan or {}).get("measurement_conditions") or {})
    # the parameters sent to the provider (and its echo of them in its own units) are what is fitted or fixed, so they
    # are passed as conditions equal to the point's values; every other parameter_point key (for example a
    # cross-section set) must be stated in gate_plan.measurement_conditions and match
    for key in set(point_keys) | {"model_parameters"}:
        if key in pp:
            cond[key] = pp[key]
    # run_record_keys: parameter_point keys that record how the provider ran this point (a run name made from the
    # point hash, the substitutions the code made for this point), not conditions of the measurement; their values
    # are kept in the gate record, not compared
    for key in run_record_keys:
        if key in pp:
            cond[key] = pp[key]
    res = gate_check(doc, ds.record, dict(plan or {}, measurement_conditions=cond))
    if not res.get("comparable"):
        raise FitRefused("not-comparable", f"dataset {ds.name}: the comparison gate refused the prediction: " + json.dumps(
            [{k: m.get(k) for k in ("field", "reason")} for m in res.get("mismatches", [])][:5] + res.get("findings", [])[:3]))
    return {"dataset": ds.name, "comparable": True, "status": res.get("status"),
            "carried_statuses": res.get("carried_statuses") or [],
            "run_record_not_compared": {k: pp[k] for k in run_record_keys if k in pp},
            **({"bin_semantics_aligned": aligned} if aligned else {})}


# --------------------------------------------------------------------------- the model
class Model:
    """Datasets, parameters, multipliers: chi2 with the multipliers profiled at every transport point."""

    def __init__(self, cfg, datasets, evaluator, domain):
        self.datasets, self.ev, self.domain = datasets, evaluator, domain
        params = _keys(cfg.get("parameters") or {}, list(cfg.get("parameters") or {}), "parameters")
        if not params:
            raise FitInputError("parameters must name at least one transport parameter with its start value")
        self.params = {}
        for name, spec in params.items():
            spec = _keys(spec, {"start", "scale", "step"}, f"parameters.{name}")
            scale = spec.get("scale", "linear")
            if scale not in ("log", "linear"):
                raise FitInputError(f"parameters.{name}.scale must be 'log' or 'linear'")
            start = _num(spec.get("start"), f"parameters.{name}.start")
            if scale == "log" and start <= 0:
                raise FitInputError(f"parameters.{name}.start must be > 0 on a log axis")
            step = spec.get("step")
            if step is not None and _num(step, f"parameters.{name}.step") <= 0:
                raise FitInputError(f"parameters.{name}.step must be > 0 (a difference step in the fit coordinate)")
            self.params[name] = {"start": start, "scale": scale, "step": None if step is None else float(step)}
        self.nuisances = []
        for k, n in enumerate(cfg.get("nuisances") or []):
            n = _keys(n, {"name", "kind", "channel", "parent", "prior_sigma", "aux"}, f"nuisances[{k}]")
            if not isinstance(n.get("name"), str) or not n["name"]:
                raise FitInputError(f"nuisances[{k}].name is required")
            if n.get("kind") in REFUSED_NUISANCES:
                raise FitRefused("nuisance-not-supported", f"nuisance {n['name']} ({n['kind']}): "
                                 f"{REFUSED_NUISANCES[n['kind']]}; provider {evaluator.provider_id} offers neither")
            if n.get("kind") not in SUPPORTED_NUISANCES:
                raise FitInputError(f"nuisances[{k}].kind must be one of {list(SUPPORTED_NUISANCES) + list(REFUSED_NUISANCES)}")
            sig = n.get("prior_sigma")
            if sig is not None and _num(sig, f"nuisances[{k}].prior_sigma") <= 0:
                raise FitInputError(f"nuisances[{k}].prior_sigma must be > 0 or null (free)")
            self.nuisances.append({"name": n["name"], "kind": n["kind"], "channel": n.get("channel"),
                                   "parent": n.get("parent"), "prior_sigma": None if sig is None else float(sig),
                                   "aux": _num(n.get("aux", 1.0), f"nuisances[{k}].aux")})
        self.mult_of_channel: dict = {}
        self.channels: list = []

    def bind_channels(self, channels) -> None:
        """Map each multiplier to its channel(s) once the provider's components are known."""
        self.channels = list(channels)
        owner: dict = {}
        for j, n in enumerate(self.nuisances):
            if n["kind"] == "production-norm":
                hit = [c for c in channels if c == n["channel"]]
            else:
                hit = [c for c in channels if c.split("->")[0] == n["parent"]]
            if not hit:
                raise FitInputError(f"nuisance {n['name']}: no provider component matches "
                                    f"{n['channel'] or n['parent']!r}; components: {channels}")
            for c in hit:
                if c in owner:
                    raise FitInputError(f"nuisances {owner[c]} and {n['name']} both multiply component {c}: they are "
                                        "exactly degenerate; declare one")
                owner[c] = n["name"]
                self.mult_of_channel[c] = j
        self.n_nu = len(self.nuisances)
        # design: A[c, j] = 1 when multiplier j acts on channel c
        self.assign = np.zeros((len(channels), self.n_nu))
        for i, c in enumerate(channels):
            if c in self.mult_of_channel:
                self.assign[i, self.mult_of_channel[c]] = 1.0

    # ---- fit coordinates
    def coords(self, free):
        names = [n for n in self.params if n in free]
        scales = [self.params[n]["scale"] for n in names]
        bounds = []
        for n, s in zip(names, scales):
            d = self.domain[n]
            lo, hi = d["min"], d["max"]
            if s == "log" and lo <= 0:
                raise FitInputError(f"parameter {n}: a log axis needs a positive domain, the provider gives min {lo}")
            bounds.append((_to_fit(lo, s), _to_fit(hi, s)))
        return names, scales, bounds

    def steps(self, names):
        """Difference steps in the fit coordinates of names, or None when no parameter states one (then the
        optimizer's own steps and 1e-4 x max(1, |t|) are used, as for a provider without numerical noise)."""
        given = [self.params[n]["step"] for n in names]
        if all(g is None for g in given):
            return None
        return [g for g in given]

    def values(self, names, scales, t, fixed) -> dict:
        """Natural values at fit coordinates t; a value that leaves the domain only by the rounding of exp(ln p) is set
        to the domain edge (a point really outside is left for the provider to refuse)."""
        out = dict(fixed)
        for n, s, x in zip(names, scales, t):
            v = _natural(x, s)
            d = self.domain.get(n)
            if d is not None:
                for edge in (d["min"], d["max"]):
                    if abs(v - edge) <= 1e-12 * max(abs(edge), 1e-300):
                        v = float(edge)
            out[n] = v
        return out

    # ---- chi2 with the multipliers profiled
    def pieces(self, comps_by_ds, ys=None, aux=None, extra_cov=None):
        """Whitened design for the linear multipliers: returns (b, A, chol per dataset, prior rows)."""
        bs, As = [], []
        for ds in self.datasets:
            arr = comps_by_ds[ds.name]                       # channels x bins
            y = ds.y if ys is None else ys[ds.name]
            chol = ds.chol if extra_cov is None else extra_cov[ds.name]
            unassigned = arr[self.assign.sum(axis=1) == 0].sum(axis=0) if self.n_nu else arr.sum(axis=0)
            bs.append(np.linalg.solve(chol, y - unassigned))
            if self.n_nu:
                As.append(np.linalg.solve(chol, arr.T @ self.assign))
        b = np.concatenate(bs)
        A = np.vstack(As) if self.n_nu else np.zeros((len(b), 0))
        aux = [n["aux"] for n in self.nuisances] if aux is None else aux
        rows_b, rows_a = [], []
        for j, n in enumerate(self.nuisances):
            if n["prior_sigma"] is not None:
                e = np.zeros(self.n_nu)
                e[j] = 1.0 / n["prior_sigma"]
                rows_a.append(e)
                rows_b.append(aux[j] / n["prior_sigma"])
        if rows_a:
            A = np.vstack([A, np.array(rows_a)])
            b = np.concatenate([b, np.array(rows_b)])
        return b, A

    def profiled(self, comps_by_ds, ys=None, aux=None, extra_cov=None):
        """(residual vector, nu_hat): the multipliers at their exact conditional minimum (linear least squares)."""
        b, A = self.pieces(comps_by_ds, ys, aux, extra_cov)
        if self.n_nu == 0:
            return b, np.zeros(0)
        nu, *_ = np.linalg.lstsq(A, b, rcond=None)
        if np.any(nu < NU_BOUNDS[0]) or np.any(nu > NU_BOUNDS[1]):
            # outside the multiplier bounds (a negative norm or abundance is unphysical): the bounded solution
            nu = optimize.lsq_linear(A, b, bounds=NU_BOUNDS, method="bvls").x
        return b - A @ nu, nu

    def residual_at(self, comps_by_ds, nu, ys=None, aux=None, extra_cov=None):
        b, A = self.pieces(comps_by_ds, ys, aux, extra_cov)
        return b - A @ np.asarray(nu, dtype=float)

    def n_points(self) -> int:
        return int(sum(len(ds.y) for ds in self.datasets))


# --------------------------------------------------------------------------- one fit
def _verdict(nll_abs, x_abs, bounds_abs, held, steps=None):
    """fit_diagnostics verdict on the interior, non-held coordinates; boundary_kkt on the coordinates at a bound.
    Judged in offsets from the best fit, so the verdict's difference steps are 1e-4 in every fit coordinate whatever
    its value (newton_fit steps 1e-4 x max(1, |x|), which for ln D0 ~ 66 would be a sizeable fraction of sigma).
    With steps (a provider with numerical noise, parameters.<name>.step) the offsets are measured in units of
    step / 1e-4, so the Hessian's difference step is the stated step and boundary_kkt's is 1e-2 of it."""
    from core.stats.fit_diagnostics import boundary_kkt, newton_fit
    x0 = [float(v) for v in x_abs]
    unit = [1.0 if steps is None or steps[i] is None else steps[i] / 1e-4 for i in range(len(x0))]
    kkt_scale = 1.0 if steps is None else 1e-2

    def nll(d):
        return nll_abs([a + b * u for a, b, u in zip(x0, d, unit)])
    x = [0.0] * len(x0)
    bounds = [((lo - c) / u, (hi - c) / u) for (lo, hi), c, u in zip(bounds_abs, x0, unit)]
    at_bound, kkt = [], []
    for i, (lo, hi) in enumerate(bounds):
        if i in held:
            continue
        span = hi - lo
        if x[i] <= lo + 1e-9 * span:
            ok, d = boundary_kkt(nll, x, i, lo, scale=kkt_scale)
            at_bound.append(i)
            kkt.append({"index": i, "bound": "lower", "ok": bool(ok), "derivative": _r(d)})
        elif x[i] >= hi - 1e-9 * span:
            def flipped(z, i=i):
                w = list(z)
                w[i] = -w[i]
                return nll(w)
            z = list(x)
            z[i] = -z[i]
            ok, d = boundary_kkt(flipped, z, i, -hi, scale=kkt_scale)
            at_bound.append(i)
            kkt.append({"index": i, "bound": "upper", "ok": bool(ok), "derivative": _r(d)})
    judged = [i for i in range(len(x)) if i not in held and i not in at_bound]

    def reduced(z):
        w = list(x)
        for i, v in zip(judged, z):
            w[i] = v
        return nll(w)
    res = newton_fit(reduced, [x[i] for i in judged], max_iter=0)
    ok = res.ok and all(k["ok"] for k in kkt)
    reasons = list(res.reasons) + [f"kkt_{k['bound']}_{k['index']}" for k in kkt if not k["ok"]]
    return {"status": "converged" if ok else "failed", "reasons": reasons, "edm": _r(res.edm),
            "judged": judged, "held": sorted(held), "at_bound": at_bound, "kkt": kkt}


def _fisher_full(model, names, scales, t, fixed, nu, step=1e-4, bounds=None):
    """Fisher matrix in (transport fit coordinates, multipliers) at (t, nu) with the multiplier priors, by central
    differences of the provider components (2 evaluations per transport coordinate; one-sided at a domain bound, so
    the provider is never asked outside its domain). The difference step is parameters.<name>.step when stated."""
    k = len(names)
    bounds = bounds or model.coords(names)[2]
    stated = model.steps(names) or [None] * k
    comps0 = model.ev.components(model.values(names, scales, t, fixed))
    mult = _multipliers(model, nu)
    cols = []
    for i in range(k):
        h = stated[i] if stated[i] is not None else step * max(1.0, abs(t[i]))
        tp, tm = list(t), list(t)
        tp[i] = min(t[i] + h, bounds[i][1])
        tm[i] = max(t[i] - h, bounds[i][0])
        cp = model.ev.components(model.values(names, scales, tp, fixed))
        cm = model.ev.components(model.values(names, scales, tm, fixed))
        col = []
        for ds in model.datasets:
            d = ((cp[ds.name] - cm[ds.name]) / (tp[i] - tm[i])).T @ mult
            col.append(np.linalg.solve(ds.chol, d))
        cols.append(np.concatenate(col))
    for j in range(model.n_nu):
        col = []
        for ds in model.datasets:
            d = comps0[ds.name].T @ model.assign[:, j]
            col.append(np.linalg.solve(ds.chol, d))
        cols.append(np.concatenate(col))
    J = np.array(cols).T if cols else np.zeros((model.n_points(), 0))
    F = J.T @ J
    for j, n in enumerate(model.nuisances):
        if n["prior_sigma"] is not None:
            F[k + j, k + j] += 1.0 / n["prior_sigma"] ** 2
    return F


def _difference_jacobian(fun, steps, lo, hi):
    """Forward-difference Jacobian of fun with the stated steps (backward at an upper bound, so no point leaves the
    box), for least_squares; "2-point" (scipy's own relative steps) when no step is stated. The point itself is
    evaluated again, which the evaluator's memo answers without a provider call."""
    if steps is None:
        return "2-point"
    lo, hi = np.asarray(lo, dtype=float), np.asarray(hi, dtype=float)

    def jac(t):
        t = np.asarray(t, dtype=float)
        f0 = fun(t)
        cols = []
        for i, h in enumerate(steps):
            h = h if h is not None else 1e-4 * max(1.0, abs(t[i]))
            if t[i] + h > hi[i]:
                h = -h
            tp = t.copy()
            tp[i] += h
            cols.append((fun(tp) - f0) / h)
        return np.array(cols).T
    return jac


def _snap_to_bounds(nll, t, steps, lo, hi):
    """A bounded optimizer stops strictly inside the box; a coordinate within one stated difference step of a bound
    would make the verdict's differences straddle the bound. Such a coordinate is set on the bound when that does not
    raise -ln L by more than the noise allowance 1e-6, so the bound is judged by boundary_kkt instead."""
    t = np.asarray(t, dtype=float).copy()
    base = nll(t)
    for i, h in enumerate(steps):
        if h is None:
            continue
        for edge in (lo[i], hi[i]):
            if 0 < abs(t[i] - edge) < h:
                trial = t.copy()
                trial[i] = edge
                value = nll(trial)
                if value <= base + 1e-6:
                    t, base = trial, value
    return t


def _multipliers(model, nu):
    m = np.ones(len(model.channels))
    for c, j in model.mult_of_channel.items():
        m[model.channels.index(c)] = nu[j]
    return m


def fit_family(model, family, opt, fixed_global, start=None, ys=None, aux=None):
    """Fit one family with the provider; returns the fit record (FitRefused on a provider failure)."""
    from degeneracy import fisher_screen, screen_objects
    names, scales, bounds = model.coords(family["free"])
    fixed = dict(fixed_global)
    fixed.update(family.get("fixed") or {})
    lo = np.array([b[0] for b in bounds])
    hi = np.array([b[1] for b in bounds])
    steps = model.steps(names)
    t0 = np.array([_to_fit(model.params[n]["start"] if start is None else start[n], s) for n, s in zip(names, scales)])
    for n, s, v, a, b in zip(names, scales, t0, lo, hi):
        if not a <= v <= b:
            raise FitRefused("out-of-domain", f"start {n} = {_natural(v, s):.6g} is outside the provider domain "
                             f"[{_natural(a, s):.6g}, {_natural(b, s):.6g}]; the fit starts only inside it")

    def resid(t):
        return model.profiled(model.ev.components(model.values(names, scales, t, fixed)), ys, aux)[0]

    def nll(t):
        t = np.clip(np.asarray(t, dtype=float), lo, hi)
        return 0.5 * float(resid(t) @ resid(t))
    rng = np.random.default_rng(int(opt["seed"]))
    attempts, best = [], None
    t_start = t0.copy()
    for attempt in range(opt["max_restarts"] + 1):
        if not names:
            t_hat = t0
            jac = np.zeros((len(resid(t0)), 0))
            stop = "no free parameter"
        else:
            res = optimize.least_squares(resid, t_start, jac=_difference_jacobian(resid, steps, lo, hi),
                                         bounds=(lo, hi), method="trf", x_scale="jac",
                                         max_nfev=opt["max_iterations"], xtol=1e-12, ftol=1e-12,
                                         gtol=1e-10)
            t_hat, jac, stop = res.x, res.jac, str(res.message)
            if steps is not None:
                t_hat = _snap_to_bounds(nll, t_hat, steps, lo, hi)
        F = jac.T @ jac
        span = hi - lo
        held: set = set()
        degenerate = []
        if names:
            cond, eig, degenerate, keep = fisher_screen(F, names, span)
            held = _exactly_flat(F)
        verdict = _verdict(nll, t_hat, bounds, held, steps) if names else {"status": "converged", "reasons": [],
                                                                    "judged": [], "held": [], "at_bound": [], "kkt": []}
        attempts.append({"attempt": attempt, "status": verdict["status"], "reasons": verdict["reasons"],
                         "optimizer": stop})
        if best is None or nll(t_hat) < best[1]:
            best = (t_hat, nll(t_hat), verdict, F, degenerate)
        if verdict["status"] == "converged":
            best = (t_hat, nll(t_hat), verdict, F, degenerate)
            break
        if attempt < opt["max_restarts"]:
            t_start = np.clip(t0 + rng.uniform(-0.1, 0.1, len(t0)) * span, lo, hi)
    t_hat, half_chi2, verdict, F, degenerate = best
    converged = verdict["status"] == "converged"
    comps = model.ev.components(model.values(names, scales, t_hat, fixed))
    r, nu = model.profiled(comps, ys, aux)
    chi2 = float(r @ r)
    out = {"family": family["name"], "free": names, "fixed": fixed, "status": "converged" if converged else "failed",
           "restarts": len(attempts) - 1, "attempts": attempts, "convergence": verdict,
           "chi2": chi2, "best_fit_coordinates": [float(x) for x in t_hat]}
    if not converged:
        out["reason"] = "restart-cap" if len(attempts) - 1 >= opt["max_restarts"] else "not-converged"
    k = len(names)
    Ffull = _fisher_full(model, names, scales, list(t_hat), fixed, nu) if (k or model.n_nu) else np.zeros((0, 0))
    cov_full, flat_mask = _pinv_kept(Ffull)
    n_free_nu = model.n_nu
    n_constrained = k + n_free_nu - int(flat_mask.sum())
    dof = model.n_points() + sum(1 for n in model.nuisances if n["prior_sigma"] is not None) - n_constrained
    out["dof"] = int(dof)
    out["p_value"] = float(chi2_dist.sf(chi2, dof)) if dof > 0 else None
    params = []
    for i, (n, s) in enumerate(zip(names, scales)):
        constrained = i not in verdict["held"] and not _along_flat(i, degenerate)
        sig = float(math.sqrt(max(cov_full[i, i], 0.0))) if constrained else None
        params.append({"name": n, "scale": s, "fit_coordinate": f"ln({n})" if s == "log" else n,
                       "best_fit": _natural(t_hat[i], s), "best_fit_coordinate": float(t_hat[i]),
                       "sigma_coordinate": sig, "constrained": constrained,
                       "at_bound": i in verdict["at_bound"]})
    out["parameters"] = params
    out["nuisances"] = [{"name": n["name"], "kind": n["kind"], "value": float(nu[j]),
                         "sigma": float(math.sqrt(max(cov_full[k + j, k + j], 0.0))),
                         "prior_sigma": n["prior_sigma"], "aux": (n["aux"] if aux is None else float(aux[j])),
                         "pull": None if n["prior_sigma"] is None else
                         float((nu[j] - (n["aux"] if aux is None else aux[j])) / n["prior_sigma"])}
                        for j, n in enumerate(model.nuisances)]
    if k:
        cond, eig, degenerate, keep = fisher_screen(F, names, hi - lo)
        out["fisher"] = {"coordinates": [p["fit_coordinate"] for p in params], "matrix": F.tolist(),
                         "condition_number": cond, "eigen": eig,
                         "method": "J^T C^-1 J of the residuals with the multipliers profiled (least_squares Jacobian)"}
        out["degenerate_directions"] = screen_objects(degenerate, names, scales)
    else:
        out["degenerate_directions"] = []
    out["fisher_full"] = {"coordinates": [p["fit_coordinate"] for p in params] + [n["name"] for n in model.nuisances],
                          "matrix": Ffull.tolist()}
    out["_internal"] = {"names": names, "scales": scales, "bounds": bounds, "t_hat": t_hat, "nu": nu, "fixed": fixed,
                        "degenerate": degenerate, "cov_full": cov_full, "nll": nll, "Ffull": Ffull}
    return out


def profile_interval(model, fit, name, opt):
    """Profile delta chi2 = 1 interval of one free parameter with the provider (the other coordinates profiled by
    least_squares, the multipliers exactly). An end on a domain bound is reported as such (kind "bound"); the width on
    each side is the one-sided interval width used at a boundary."""
    fi = fit["_internal"]
    names, scales, bounds, t_hat = fi["names"], fi["scales"], fi["bounds"], np.asarray(fi["t_hat"], dtype=float)
    i = names.index(name)
    others = [j for j in range(len(names)) if j != i]
    lo = np.array([bounds[j][0] for j in others])
    hi = np.array([bounds[j][1] for j in others])
    chi2_min = fit["chi2"]
    stated = model.steps(names)
    steps = None if stated is None else [stated[j] for j in others]

    def delta(x):
        def resid(w):
            t = t_hat.copy()
            t[i] = x
            t[others] = w
            return model.profiled(model.ev.components(model.values(names, scales, t, fi["fixed"])))[0]
        if others:
            res = optimize.least_squares(resid, np.clip(t_hat[others], lo, hi), bounds=(lo, hi), method="trf",
                                         jac=_difference_jacobian(resid, steps, lo, hi),
                                         x_scale="jac", max_nfev=opt["max_iterations"],
                                         xtol=1e-12, ftol=1e-12, gtol=1e-10)
            r = res.fun
        else:
            r = resid(np.zeros(0))
        return float(r @ r) - chi2_min
    sig = fit["parameters"][i]["sigma_coordinate"] or 0.05 * (bounds[i][1] - bounds[i][0])
    ends = {}
    for side, key in ((-1, "lower"), (1, "upper")):
        edge = bounds[i][0] if side < 0 else bounds[i][1]
        if abs(t_hat[i] - edge) <= 1e-9 * (bounds[i][1] - bounds[i][0]):
            ends[key] = {"value": _natural(edge, scales[i]), "kind": "bound", "width_coordinate": 0.0}
            continue
        step, x_in, x_out = sig, float(t_hat[i]), None
        for _ in range(12):
            x = float(np.clip(t_hat[i] + side * step, bounds[i][0], bounds[i][1]))
            if delta(x) >= 1.0:
                x_out = x
                break
            x_in = x
            if x == edge:
                break
            step *= 2.0
        if x_out is None:
            ends[key] = {"value": _natural(edge, scales[i]), "kind": "bound-without-crossing",
                         "width_coordinate": abs(edge - float(t_hat[i]))}
            continue
        x = optimize.brentq(lambda z: delta(z) - 1.0, min(x_in, x_out), max(x_in, x_out),
                            xtol=(1e-6 if stated is None else 1e-3) * sig)
        ends[key] = {"value": _natural(x, scales[i]), "kind": "crossing", "width_coordinate": abs(x - float(t_hat[i]))}
    return {"parameter": name, "coordinate": fit["parameters"][i]["fit_coordinate"], "threshold": 1.0, **ends}


def _exactly_flat(F, ratio=EXACT_FLAT) -> set:
    """Coordinates held for the verdict: for each eigen-direction with eigenvalue below ratio x the largest (an exact
    degeneracy, not a weakly constrained one), the coordinate with the largest component not yet held."""
    ev, vec = np.linalg.eigh(0.5 * (F + F.T))
    lam_max = max(float(ev[-1]), 1e-300)
    held: set = set()
    for lam, v in zip(ev, vec.T):
        if lam <= ratio * lam_max:
            order = [int(i) for i in np.argsort(-np.abs(v)) if int(i) not in held]
            if order:
                held.add(order[0])
    return held


def _along_flat(i, degenerate) -> bool:
    return any(abs(v[i]) > 0.1 for _, v, _ in degenerate)


def _pinv_kept(F):
    """Inverse over the constrained directions (eigenvalues above 1e-10 of the largest); mask of flat directions."""
    if F.size == 0:
        return F, np.zeros(0, dtype=bool)
    ev, vec = np.linalg.eigh(0.5 * (F + F.T))
    lam_max = max(float(ev[-1]), 1e-300)
    flat = ev <= 1e-10 * lam_max
    cov = sum((np.outer(v, v) / lam for lam, v, f in zip(ev, vec.T, flat) if not f), np.zeros_like(F))
    return cov, flat


# --------------------------------------------------------------------------- response model
class ResponseModel:
    """Tensor Chebyshev interpolation of the provider components on a box in fit coordinates (module docstring)."""

    def __init__(self, model, names, scales, lo, hi, fixed, nodes):
        self.model, self.names, self.scales, self.fixed = model, list(names), list(scales), dict(fixed)
        self.lo, self.hi, self.nodes = np.asarray(lo, dtype=float), np.asarray(hi, dtype=float), int(nodes)
        d = len(names)
        if not 1 <= d <= 3:
            raise FitRefused("response-model-dimension", f"a response model spans 1 to 3 transport coordinates, got {d}")
        k = np.arange(self.nodes)
        self.u_nodes = np.cos(np.pi * (k + 0.5) / self.nodes)[::-1]    # Chebyshev points in (-1, 1)
        grids = np.meshgrid(*([self.u_nodes] * d), indexing="ij")
        pts = np.stack([g.ravel() for g in grids], axis=1)
        tables = {}
        for u in pts:
            t = self._t(u)
            comps = model.ev.components(model.values(self.names, self.scales, t, self.fixed))
            for ds in model.datasets:
                tables.setdefault(ds.name, []).append(comps[ds.name])
        vinv = np.linalg.inv(np.polynomial.chebyshev.chebvander(self.u_nodes, self.nodes - 1))
        self.coef, self.logged = {}, {}
        for name, rows in tables.items():
            arr = np.array(rows).reshape([self.nodes] * d + list(rows[0].shape))
            logged = bool(np.all(arr > 0))
            vals = np.log(arr) if logged else arr
            for axis in range(d):
                vals = np.moveaxis(np.tensordot(vinv, np.moveaxis(vals, axis, 0), axes=(1, 0)), 0, axis)
            self.coef[name], self.logged[name] = vals, logged
        self.evaluations = len(pts) * len(model.datasets)
        self.error = {ds.name: np.zeros(len(ds.y)) for ds in model.datasets}
        self.validation: dict = {}

    def _t(self, u):
        return self.lo + 0.5 * (np.asarray(u) + 1.0) * (self.hi - self.lo)

    def _u(self, t):
        return 2.0 * (np.asarray(t, dtype=float) - self.lo) / (self.hi - self.lo) - 1.0

    def inside(self, t, tol=1e-9) -> bool:
        u = self._u(t)
        return bool(np.all(u >= -1 - tol) and np.all(u <= 1 + tol))

    def components(self, t) -> dict:
        u = np.clip(self._u(t), -1.0, 1.0)
        rows = [np.polynomial.chebyshev.chebvander(np.array([x]), self.nodes - 1)[0] for x in u]
        out = {}
        for name, c in self.coef.items():
            v = c
            for row in rows:
                v = np.tensordot(row, v, axes=(0, 0))
            out[name] = np.exp(v) if self.logged[name] else v
        return out

    def validate(self, n_points, tolerance, seed) -> dict:
        rng = np.random.default_rng(seed)
        worst = 0.0
        for _ in range(n_points):
            t = self.lo + rng.uniform(0, 1, len(self.names)) * (self.hi - self.lo)
            exact = self.model.ev.components(self.model.values(self.names, self.scales, t, self.fixed))
            approx = self.components(t)
            for ds in self.model.datasets:
                diff = np.abs(exact[ds.name].sum(axis=0) - approx[ds.name].sum(axis=0))
                self.error[ds.name] = np.maximum(self.error[ds.name], diff)
                worst = max(worst, float(np.max(diff / ds.sigma)))
        self.evaluations += n_points * len(self.model.datasets)
        self.validation = {"points": n_points, "seed": seed, "max_error_over_sigma": worst, "tolerance": tolerance,
                           "passed": worst <= tolerance}
        return self.validation

    def chol_with_error(self) -> dict:
        """Data covariance plus the response-model error as an uncorrelated component (P10), Cholesky factors."""
        return {ds.name: np.linalg.cholesky(ds.cov + np.diag(self.error[ds.name] ** 2)) for ds in self.model.datasets}

    def record(self) -> dict:
        return {"kind": "tensor Chebyshev",
                "coordinates": [f"ln({n})" if s == "log" else n for n, s in zip(self.names, self.scales)],
                "box": [[_natural(a, s), _natural(b, s)] for a, b, s in zip(self.lo, self.hi, self.scales)],
                "fixed": self.fixed, "nodes_per_axis": self.nodes, "provider_evaluations": self.evaluations,
                "validation": self.validation,
                "error_component": {k: [float(x) for x in v] for k, v in self.error.items()}}


class PolynomialResponseModel(ResponseModel):
    """Total-degree Chebyshev polynomial (in ln of the component when it is positive) fitted by least squares to
    provider evaluations at the points of a scrambled Sobol design in the box: far fewer evaluations than a tensor
    grid in 4 to 6 coordinates (a total degree p in d coordinates has C(d + p, p) terms). Validated like the tensor
    model; its error enters the covariance the same way (P10)."""

    def __init__(self, model, names, scales, lo, hi, fixed, degree, design_points, seed):
        from itertools import product

        from scipy.stats import qmc
        self.model, self.names, self.scales, self.fixed = model, list(names), list(scales), dict(fixed)
        self.lo, self.hi = np.asarray(lo, dtype=float), np.asarray(hi, dtype=float)
        d = len(names)
        if not 1 <= d <= 6:
            raise FitRefused("response-model-dimension", f"a polynomial response model spans 1 to 6 transport "
                             f"coordinates, got {d}")
        self.degree, self.nodes = int(degree), None
        self.terms = [m for m in product(range(self.degree + 1), repeat=d) if sum(m) <= self.degree]
        if design_points < 2 * len(self.terms):
            raise FitInputError(f"response_model.design_points {design_points} must be at least twice the "
                                f"{len(self.terms)} terms of total degree {self.degree} in {d} coordinates")
        with warnings.catch_warnings():   # a count that is not a power of 2 loses only Sobol's balance property
            warnings.simplefilter("ignore", UserWarning)
            u = 2.0 * qmc.Sobol(d, scramble=True, seed=int(seed)).random(int(design_points)) - 1.0
        tables: dict = {}
        for row in u:
            comps = model.ev.components(model.values(self.names, self.scales, self._t(row), self.fixed))
            for ds in model.datasets:
                tables.setdefault(ds.name, []).append(comps[ds.name])
        basis = self._basis(u)
        self.coef, self.logged = {}, {}
        for name, rows in tables.items():
            arr = np.array(rows)                                   # points x channels x bins
            logged = bool(np.all(arr > 0))
            vals = (np.log(arr) if logged else arr).reshape(len(u), -1)
            coef, *_ = np.linalg.lstsq(basis, vals, rcond=None)
            self.coef[name], self.logged[name] = (coef, arr.shape[1:]), logged
        self.evaluations = len(u) * len(model.datasets)
        self.design = {"kind": "scrambled Sobol", "points": int(design_points), "seed": int(seed)}
        self.error = {ds.name: np.zeros(len(ds.y)) for ds in model.datasets}
        self.validation: dict = {}

    def _basis(self, u):
        u = np.atleast_2d(u)
        cheb = [np.polynomial.chebyshev.chebvander(u[:, j], self.degree) for j in range(u.shape[1])]
        return np.array([[np.prod([cheb[j][r, m[j]] for j in range(u.shape[1])]) for m in self.terms]
                         for r in range(u.shape[0])])

    def components(self, t) -> dict:
        b = self._basis(np.clip(self._u(t), -1.0, 1.0))[0]
        out = {}
        for name, (coef, shape) in self.coef.items():
            v = (b @ coef).reshape(shape)
            out[name] = np.exp(v) if self.logged[name] else v
        return out

    def record(self) -> dict:
        rec = super().record()
        rec.pop("nodes_per_axis", None)
        rec.update(kind="total-degree polynomial", degree=self.degree, terms=len(self.terms), design=self.design)
        return rec


class ProviderResponse(ResponseModel):
    """kind "provider": no response model; the toys and families evaluate the provider itself (for a provider that is
    already a validated emulator, whose error enters the data covariance outside this script, P10). The box only
    bounds the toy fits; the error component is zero because nothing is approximated here."""

    def __init__(self, model, names, scales, lo, hi, fixed):
        self.model, self.names, self.scales, self.fixed = model, list(names), list(scales), dict(fixed)
        self.lo, self.hi, self.nodes = np.asarray(lo, dtype=float), np.asarray(hi, dtype=float), None
        self.evaluations = 0
        self.error = {ds.name: np.zeros(len(ds.y)) for ds in model.datasets}
        self.validation: dict = {}

    def components(self, t) -> dict:
        return self.model.ev.components(self.model.values(self.names, self.scales, np.asarray(t, dtype=float),
                                                          self.fixed))

    def validate(self, n_points, tolerance, seed) -> dict:
        self.validation = {"points": 0, "seed": seed, "max_error_over_sigma": 0.0, "tolerance": tolerance,
                           "passed": True, "note": "no response model: the provider itself is evaluated"}
        return self.validation

    def record(self) -> dict:
        rec = super().record()
        rec.pop("nodes_per_axis", None)
        rec["kind"] = "provider (no response model)"
        return rec


def build_response_model(model, names, scales, centers, sigmas, fixed, rm_cfg, bounds, seed):
    """Box = union over centers of +-k sigma, clipped to the provider domain; validated; FitRefused above tolerance."""
    k = rm_cfg["half_width_sigma"]
    lo = np.min([c - k * s for c, s in zip(centers, sigmas)], axis=0)
    hi = np.max([c + k * s for c, s in zip(centers, sigmas)], axis=0)
    lo = np.maximum(lo, [b[0] for b in bounds])
    hi = np.minimum(hi, [b[1] for b in bounds])
    if rm_cfg["kind"] == "provider":
        rm = ProviderResponse(model, names, scales, lo, hi, fixed)
    elif rm_cfg["kind"] == "polynomial":
        rm = PolynomialResponseModel(model, names, scales, lo, hi, fixed, rm_cfg["degree"], rm_cfg["design_points"],
                                     seed + 1)
    else:
        rm = ResponseModel(model, names, scales, lo, hi, fixed, rm_cfg["nodes"])
    val = rm.validate(rm_cfg["validation_points"], rm_cfg["tolerance_sigma"], seed)
    if not val["passed"]:
        raise FitRefused("response-model-above-tolerance",
                         f"the response model's largest error is {val['max_error_over_sigma']:.3g} of the data sigma, "
                         f"above the tolerance {val['tolerance']}; toys and posteriors are not run on it")
    return rm


# --------------------------------------------------------------------------- fits on the response model
class SurrogateFit:
    """Fits in (transport fit coordinates, multipliers) on a response model, for toys, families and posteriors."""

    def __init__(self, model, rm, names, scales, fixed_t: dict, domain_bounds):
        self.model, self.rm = model, rm
        self.idx = [rm.names.index(n) for n in names]
        self.fixed_t = dict(fixed_t)   # response-model coordinate name -> fixed fit-coordinate value
        self.names, self.scales = list(names), list(scales)
        self.k = len(names)
        self.chol = rm.chol_with_error()
        lo = np.array([rm.lo[i] for i in self.idx])
        hi = np.array([rm.hi[i] for i in self.idx])
        self.lo = np.concatenate([lo, np.full(model.n_nu, NU_BOUNDS[0])])
        self.hi = np.concatenate([hi, np.full(model.n_nu, NU_BOUNDS[1])])
        dom = {n: b for n, b in zip(*domain_bounds)}
        self.domain_edge = [(abs(self.lo[i] - dom[n][0]) < 1e-9 * (dom[n][1] - dom[n][0]),
                             abs(self.hi[i] - dom[n][1]) < 1e-9 * (dom[n][1] - dom[n][0])) for i, n in enumerate(names)]

    def full_t(self, z):
        t = np.zeros(len(self.rm.names))
        for n, v in self.fixed_t.items():
            t[self.rm.names.index(n)] = v
        for j, i in enumerate(self.idx):
            t[i] = z[j]
        return t

    def resid(self, z, ys, aux):
        comps = self.rm.components(self.full_t(z[:self.k]))
        return self.model.residual_at(comps, z[self.k:], ys, aux, self.chol)

    def chi2(self, z, ys, aux) -> float:
        r = self.resid(z, ys, aux)
        return float(r @ r)

    def fit(self, ys, aux, start, opt, constraint=None):
        """Minimize; constraint = ("index", i, value) or ("direction", v, z_ref). Returns (chi2, z, ok, reason).
        A provider evaluated directly (kind "provider") that refuses a point out of its domain fails the fit."""
        try:
            return self._fit(ys, aux, start, opt, constraint)
        except FitRefused as exc:
            if exc.reason != "out-of-domain":
                raise
            return float("nan"), np.asarray(start, dtype=float), False, "provider-out-of-domain"

    def _fit(self, ys, aux, start, opt, constraint=None):
        start = np.clip(np.asarray(start, dtype=float), self.lo, self.hi)
        to_z, w0, lo, hi = _constrained_map(constraint, start, self.lo, self.hi)
        rng = np.random.default_rng(opt["seed"])
        last = None
        for attempt in range(opt["max_restarts"] + 1):
            if lo is None:
                def fun(w):
                    z = to_z(w)
                    c = np.clip(z, self.lo, self.hi)
                    pen = 1e3 * (z - c) / (self.hi - self.lo)
                    return np.concatenate([self.resid(c, ys, aux), pen])
                res = optimize.least_squares(fun, w0, method="lm" if len(w0) <= len(fun(w0)) else "trf",
                                             max_nfev=opt["max_iterations"] * (len(w0) + 1) * 4, xtol=1e-12,
                                             ftol=1e-12, gtol=1e-10)
            else:
                res = optimize.least_squares(lambda w: self.resid(to_z(w), ys, aux), w0, bounds=(lo, hi),
                                             method="trf", max_nfev=opt["max_iterations"],
                                             xtol=1e-12, ftol=1e-12, gtol=1e-10)
            z = to_z(res.x)
            ok, reason = self._judge(z, res, ys, aux, to_z, lo, hi)
            last = (self.chi2(np.clip(z, self.lo, self.hi), ys, aux), z, ok, reason)
            if ok:
                return last
            if reason == "left-response-box":
                return last
            if attempt < opt["max_restarts"]:
                w0 = res.x + rng.normal(0, 0.05, len(res.x)) * (1.0 if lo is None else (hi - lo))
                if lo is not None:
                    w0 = np.clip(w0, lo, hi)
        return last[0], last[1], False, "restart-cap"

    def _judge(self, z, res, ys, aux, to_z, lo, hi):
        if res.status <= 0:
            return False, "not-converged"
        for j in range(self.k):
            span = self.hi[j] - self.lo[j]
            if z[j] <= self.lo[j] + 1e-7 * span and not self.domain_edge[j][0]:
                return False, "left-response-box"
            if z[j] >= self.hi[j] - 1e-7 * span and not self.domain_edge[j][1]:
                return False, "left-response-box"
        if not np.all(np.isfinite(z)):
            return False, "not-converged"
        w = res.x
        bounds = list(zip(lo, hi)) if lo is not None else [(-np.inf, np.inf)] * len(w)
        v = _verdict(lambda q: 0.5 * float(np.sum(res_fun(self, to_z, q, ys, aux) ** 2)), w, bounds, set())
        return v["status"] == "converged", ("ok" if v["status"] == "converged" else "not-converged")


def _constrained_map(constraint, start, lo_all, hi_all):
    """(map from free coordinates w to the full vector z, w at the start, bounds of w or None): no constraint; one
    coordinate fixed ("index", i, value); or a fixed projection on a unit direction ("direction", v, z_ref), w then
    spanning its orthogonal complement (unbounded; the caller keeps the box with a penalty)."""
    if constraint is None:
        return (lambda w: w), start, lo_all, hi_all
    if constraint[0] == "index":
        i, val = constraint[1], constraint[2]
        keep = [j for j in range(len(start)) if j != i]

        def insert(w):
            z = np.empty(len(start))
            z[keep] = w
            z[i] = val
            return z
        return insert, start[keep], lo_all[keep], hi_all[keep]
    v, z_ref = constraint[1], constraint[2]
    comp = np.linalg.svd(v.reshape(1, -1))[2][1:].T
    return (lambda w: z_ref + comp @ w), comp.T @ (start - z_ref), None, None


def res_fun(sf, to_z, w, ys, aux):
    z = to_z(np.asarray(w, dtype=float))
    return sf.resid(np.clip(z, sf.lo, sf.hi), ys, aux)


def _toy_data(model, mu_true, aux_true, rng):
    ys = {}
    for ds in model.datasets:
        ys[ds.name] = mu_true[ds.name] + ds.chol @ rng.normal(size=len(ds.y))
    aux = [a + (n["prior_sigma"] * rng.normal() if n["prior_sigma"] is not None else 0.0)
           for a, n in zip(aux_true, model.nuisances)]
    return ys, aux


def _mu_exact(model, names, scales, t, fixed, nu):
    comps = model.ev.components(model.values(names, scales, t, fixed))
    m = _multipliers(model, nu)
    return {ds.name: comps[ds.name].T @ m for ds in model.datasets}


def coverage_band(n, m):
    z_m = float(norm_dist.ppf(1 - FAMILYWISE_ALPHA / (2 * m)))
    se = math.sqrt(NOMINAL * (1 - NOMINAL) / n)
    return z_m, se


def run_toys(model, family, truth, tcfg, rm_cfg, opt, fixed_global):
    """Plug-in coverage toys at a true point (module docstring)."""
    from core.stats.toy_ensemble import EnsembleSpec, coverage, toy_seed
    names, scales, bounds = model.coords(family["free"])
    fixed = dict(fixed_global)
    fixed.update(family.get("fixed") or {})
    unknown = sorted(set(truth) - set(names) - {n["name"] for n in model.nuisances})
    if unknown:
        raise FitInputError(f"toys.truth: {unknown} are neither free parameters of family {family['name']} nor nuisances")
    t_true = np.array([_to_fit(truth.get(n, model.params[n]["start"]), s) for n, s in zip(names, scales)])
    for n, s, v, (a, b) in zip(names, scales, t_true, bounds):
        if not a - 1e-12 <= v <= b + 1e-12:
            raise FitRefused("out-of-domain", f"toys.truth {n} = {_natural(v, s):.6g} is outside the provider domain")
    nu_true = np.array([float(truth.get(n["name"], n["aux"])) for n in model.nuisances])
    aux_true = list(nu_true)
    F = _fisher_full(model, names, scales, list(t_true), fixed, nu_true)
    cov, flat = _pinv_kept(F)
    if flat.any():
        raise FitRefused("flat-direction-in-toys", f"family {family['name']} has an exactly flat direction at the truth; "
                         "coverage of a parameter along it is undefined: fix it or add data that break it")
    sig_t = np.sqrt(np.diag(cov))[:len(names)]
    rm = build_response_model(model, names, scales, [t_true], [sig_t], fixed, rm_cfg, bounds, tcfg["seed"] + 7)
    sf = SurrogateFit(model, rm, names, scales, {}, (names, bounds))
    mu_true = _mu_exact(model, names, scales, list(t_true), fixed, nu_true)
    z_true = np.concatenate([t_true, nu_true])
    ev, vec = np.linalg.eigh(0.5 * (F + F.T))
    flattest = vec[:, 0] * (1 if vec[np.argmax(np.abs(vec[:, 0])), 0] > 0 else -1)
    coords = [f"ln({n})" if s == "log" else n for n, s in zip(names, scales)] + [n["name"] for n in model.nuisances]
    tests = []
    for q in tcfg["test"]:
        if q == "flattest":
            tests.append(("flattest", ("direction", flattest, z_true)))
        elif q in names:
            i = names.index(q)
            tests.append((q, ("index", i, float(t_true[i]))))
        elif q in [n["name"] for n in model.nuisances]:
            j = len(names) + [n["name"] for n in model.nuisances].index(q)
            tests.append((q, ("index", j, float(nu_true[j - len(names)]))))
        else:
            raise FitInputError(f"toys.test: {q!r} is not a free parameter, a nuisance or 'flattest'")
    on_bound = {}
    for name, c in tests:
        if c[0] == "index" and c[1] < len(names):
            a, b = bounds[c[1]]
            on_bound[name] = abs(c[2] - a) < 1e-9 * (b - a) or abs(c[2] - b) < 1e-9 * (b - a)
        else:
            on_bound[name] = False
    spec = EnsembleSpec(kind="plug-in", seed=int(tcfg["seed"]), n_toys=int(tcfg["n"]),
                        notes={"truth": truth, "aux": "redrawn per toy from the prior around the true multipliers"})
    rows, failures, stopped = [], 0, False
    limit = TOY_FAILURE_LIMIT * spec.n_toys
    topt = dict(opt, max_iterations=tcfg.get("max_iterations", opt["max_iterations"]))
    for i in spec.indices:
        rng = np.random.default_rng(toy_seed(spec.seed, i))
        ys, aux = _toy_data(model, mu_true, aux_true, rng)
        c0, z0, ok, reason = sf.fit(ys, aux, z_true, dict(topt, seed=i))
        if not ok:
            rows.append((i, "fit_failed", None))
            failures += 1
        else:
            qs = {}
            for name, c in tests:
                cc, _, okc, _ = sf.fit(ys, aux, z0, dict(topt, seed=i), constraint=c)
                if not okc:
                    qs = None
                    break
                qs[name] = max(cc - c0, 0.0)
            if qs is None:
                rows.append((i, "fit_failed", None))
                failures += 1
            else:
                rows.append((i, "ok", qs))
        if failures > limit:
            stopped = True
            break
    result = {"ensemble": spec.record(), "generated": len(rows),
              "outcomes": {o: sum(1 for r in rows if r[1] == o) for o in ("ok", "fit_failed", "invalid_data",
                                                                            "empty_data", "timeout", "error")},
              "rows": rows}
    out = {"family": family["name"], "truth": truth, "ensemble": spec.record(), "generated": len(rows),
           "failed": failures, "failure_limit": TOY_FAILURE_LIMIT, "response_model": rm.record(),
           "fisher_eigenvalues": [float(x) for x in ev], "eigenvalue_ratio_min_max": float(ev[0] / ev[-1]),
           "flattest_direction": {c: float(x) for c, x in zip(coords, flattest)}, "tests": {},
           "rows": [{"toy": int(i), "outcome": o, "delta_chi2": q} for i, o, q in rows]}
    if stopped:
        out.update(status="failed", reason="toy-failure-threshold",
                   detail=f"{failures} of {len(rows)} toys failed, more than {TOY_FAILURE_LIMIT:.0%} of {spec.n_toys}: "
                          "the study is stopped and no coverage is reported")
        return out
    m = len(tests)
    z_m, se = coverage_band(spec.n_toys, m)
    all_pass = True
    for name, _ in tests:
        ok_q = [v[name] for _, o, v in rows if o == "ok"]
        crit_toys = float(np.quantile(ok_q, NOMINAL)) if ok_q else None
        cov_w = coverage(result, lambda v, name=name: v[name] <= 1.0, NOMINAL)
        value = cov_w["headline"]["value"]
        entry = {"coverage_wilks": cov_w, "critical_value_toys": crit_toys, "on_bound": on_bound[name],
                 "deviation": value - NOMINAL, "band_bonferroni": z_m * se, "z_bonferroni": z_m, "band_3sigma": 3 * se,
                 "pass_bonferroni": abs(value - NOMINAL) <= z_m * se, "pass_3sigma": abs(value - NOMINAL) <= 3 * se}
        if on_bound[name]:
            entry["note"] = ("the true value lies on a bound: Wilks does not hold (Chernoff); the toy 68.27% quantile "
                             "of the profile delta chi2 is the calibrated critical value")
            entry["coverage_calibrated"] = coverage(result, lambda v, name=name, c=crit_toys: v[name] <= c, NOMINAL)
        else:
            all_pass = all_pass and entry["pass_bonferroni"]
        out["tests"][name] = entry
    out["status"] = "ok"
    out["coverage_pass"] = all_pass
    return out


# --------------------------------------------------------------------------- families
def classify_families(cfg_families, model, domain):
    expressible, refused = [], []
    for k, f in enumerate(cfg_families):
        f = _keys(f, {"name", "free", "fixed"}, f"families[{k}]")
        if not isinstance(f.get("name"), str) or not isinstance(f.get("free"), list):
            raise FitInputError(f"families[{k}] needs a name and a list free")
        fixed = f.get("fixed") or {}
        unknown = sorted((set(f["free"]) | set(fixed)) - set(domain))
        if unknown:
            refused.append({"family": f["name"], "status": "not-expressible", "free": f["free"], "fixed": fixed,
                            "reason": f"parameters {unknown} are not in the domain of provider "
                                      f"{model.ev.provider_id} ({sorted(domain)})"})
            continue
        missing = [n for n in f["free"] if n not in model.params]
        if missing:
            raise FitInputError(f"family {f['name']}: free parameters {missing} need a start value under parameters")
        unset = sorted(set(model.params) - set(f["free"]) - set(fixed) - set(model.ev.fixed))
        if unset:
            raise FitInputError(f"family {f['name']}: parameters {unset} are neither free nor fixed; state them")
        for n, v in fixed.items():
            _num(v, f"families[{k}].fixed.{n}")
            if not domain[n]["min"] <= v <= domain[n]["max"]:
                raise FitRefused("out-of-domain", f"family {f['name']} fixes {n} = {v} outside the provider domain")
        expressible.append({"name": f["name"], "free": list(f["free"]), "fixed": dict(fixed)})
    return expressible, refused


def calibrate_families(model, fits, fam_cfg, rm_cfg, opt, fixed_global):
    """Toy-calibrated delta chi2 of every converged family (module docstring)."""
    from core.stats.tail_estimation import toy_tail
    from core.stats.toy_ensemble import toy_seed
    usable = [f for f in fits if f["status"] == "converged"]
    if not usable:
        return {"status": "failed", "reason": "no converged family"}
    union = [n for n in model.params if any(n in f["free"] for f in usable)]
    names, scales, bounds = model.coords(union)
    centers, sigmas = [], []
    for f in usable:
        c, s = [], []
        for n, sc in zip(names, scales):
            if n in f["free"]:
                j = f["free"].index(n)
                c.append(f["best_fit_coordinates"][j])
                sig = f["parameters"][j]["sigma_coordinate"]
                s.append(sig if sig is not None else 0.0)
            else:
                c.append(_to_fit(f["fixed"][n], sc))
                s.append(0.0)
        centers.append(np.array(c))
        sigmas.append(np.array(s))
    # a coordinate free in no fitted family near its value still needs a width: use the largest sigma seen
    width = np.max(sigmas, axis=0)
    sigmas = [np.where(s > 0, s, width) for s in sigmas]
    common_fixed = {n: v for n, v in usable[0]["fixed"].items() if n not in union}
    for f in usable:
        if {n: v for n, v in f["fixed"].items() if n not in union} != common_fixed:
            return {"status": "failed", "reason": "families fix parameters outside the shared response space "
                                                  "differently; calibrate them separately"}
    starts = {f["family"]: np.concatenate([f["best_fit_coordinates"], [n["value"] for n in f["nuisances"]]])
              for f in usable}
    nulls = {}
    for f in usable:
        fi = f["_internal"]
        nulls[f["family"]] = (_mu_exact(model, fi["names"], fi["scales"], list(fi["t_hat"]), fi["fixed"], fi["nu"]),
                              list(fi["nu"]))
    width = np.max(sigmas, axis=0)
    if rm_cfg["layout"] == "per-center":
        sfs_by_null, rm_record, rm = _per_center_models(model, usable, names, scales, bounds, centers, width,
                                                        common_fixed, rm_cfg, fam_cfg, opt, nulls, starts)
    else:
        joint = rm_cfg["layout"] == "joint"
        sfs, rm_record, rm = _union_model(model, usable, names, scales, bounds, centers,
                                          [width] * len(centers) if joint else sigmas, width, common_fixed, rm_cfg,
                                          fam_cfg, opt, nulls, starts, MARGIN_TOL if joint else 1e-9)
        rm_record["layout"] = rm_cfg["layout"]
        sfs_by_null = {f["family"]: sfs for f in usable}
    chi2_obs = {f["family"]: f["chi2"] for f in usable}
    best = min(chi2_obs.values())
    out = {"status": "ok", "alpha": fam_cfg["alpha"], "n_toys": fam_cfg["n"], "seed": fam_cfg["seed"],
           "response_model": rm_record, "families": [], "_rm": rm}
    for f in usable:
        sfs = sfs_by_null[f["family"]]
        d_obs = chi2_obs[f["family"]] - best
        fi = f["_internal"]
        mu = _mu_exact(model, fi["names"], fi["scales"], list(fi["t_hat"]), fi["fixed"], fi["nu"])
        exceed, failed, done = 0, 0, 0
        why: dict = {}
        toy_rows = []
        for i in range(fam_cfg["n"]):
            rng = np.random.default_rng(toy_seed(fam_cfg["seed"], i))
            ys, aux = _toy_data(model, mu, list(fi["nu"]), rng)
            vals = {}
            for g, sf in sfs.items():
                c, _, ok, reason = sf.fit(ys, aux, starts[g], dict(opt, seed=i))
                if not ok:
                    why[f"{g}: {reason}"] = why.get(f"{g}: {reason}", 0) + 1
                    toy_rows.append({"toy": i, "outcome": "fit_failed", "family": g, "reason": reason})
                    vals = None
                    break
                vals[g] = c
            done += 1
            if vals is not None:
                toy_rows.append({"toy": i, "outcome": "ok", "chi2": dict(vals),
                                 "delta_chi2": vals[f["family"]] - min(vals.values())})
            if vals is None:
                failed += 1
                if failed > TOY_FAILURE_LIMIT * fam_cfg["n"]:
                    break
                continue
            if vals[f["family"]] - min(vals.values()) >= d_obs - 1e-12:
                exceed += 1
        entry = {"family": f["family"], "chi2": f["chi2"], "delta_chi2": d_obs, "toys": done, "failed": failed,
                 "failure_reasons": why, "toy_seed": fam_cfg["seed"], "rows": toy_rows}
        if failed > TOY_FAILURE_LIMIT * fam_cfg["n"]:
            entry.update(status="failed", reason="toy-failure-threshold", surviving=None)
        else:
            tail = toy_tail(exceed, done - failed)
            entry["p_toys"] = tail
            if tail["estimate"] is not None:
                entry["surviving"] = tail["estimate"] >= fam_cfg["alpha"]
            else:
                entry["surviving"] = False if tail["upper_bound"]["value"] < fam_cfg["alpha"] else None
            entry["status"] = "ok"
        out["families"].append(entry)
    out["surviving"] = [e["family"] for e in out["families"] if e.get("surviving")]
    if any(e["status"] != "ok" for e in out["families"]):
        out["status"] = "failed"
        out["reason"] = "toy-failure-threshold"
    return out


def _union_model(model, usable, names, scales, bounds, centers, sigmas, width, common_fixed, rm_cfg, fam_cfg, opt,
                 nulls, starts, margin_tol=1e-9):
    """layout "union": one response model on the box spanning every center +- k sigma (layout "joint": +- k times the
    largest sigma of any family, every center). The box must also hold each family's fit to every other family's
    null prediction: grow it (at most 3 passes) where such a fit stops on a box edge that is not a domain edge, or
    where its margin of k width is short by more than margin_tol of the box half-width. Returns
    ({family: SurrogateFit}, record, model)."""
    passes = []
    for _ in range(3):
        rm = build_response_model(model, names, scales, centers, sigmas, common_fixed, rm_cfg, bounds,
                                  fam_cfg["seed"] + 11)
        sfs = {}
        for f in usable:
            fixed_t = {n: _to_fit(f["fixed"][n], sc) for n, sc in zip(names, scales) if n not in f["free"]}
            f_names = [n for n in names if n in f["free"]]
            f_scales = [model.params[n]["scale"] for n in f_names]
            sfs[f["family"]] = SurrogateFit(model, rm, f_names, f_scales, fixed_t, (names, bounds))
        grow, inner = [], []
        for null, (mu, nu) in nulls.items():
            for g, sf in sfs.items():
                if g == null:
                    continue
                _, z, ok, reason = sf.fit(mu, nu, starts[g], opt)
                t = sf.full_t(z[:sf.k])
                if reason == "left-response-box":
                    half = 0.5 * (rm.hi - rm.lo)
                    push = np.where(t <= rm.lo + 1e-7 * (rm.hi - rm.lo), -half,
                                    np.where(t >= rm.hi - 1e-7 * (rm.hi - rm.lo), half, 0.0))
                    grow.append(t + push)
                else:
                    k_w = rm_cfg["half_width_sigma"] * width
                    lo_d, hi_d = [b[0] for b in bounds], [b[1] for b in bounds]
                    if not (rm.inside(np.maximum(t - k_w, lo_d), margin_tol)
                            and rm.inside(np.minimum(t + k_w, hi_d), margin_tol)):
                        inner.append(t)
        passes.append({"box": rm.record()["box"], "fits_on_box_edge": len(grow), "centers_added": len(grow) + len(inner)})
        if not grow and not inner:
            break
        centers = centers + grow + inner
        sigmas = sigmas + [width] * (len(grow) + len(inner))
    return sfs, dict(rm.record(), box_passes=passes), rm


def _per_center_models(model, usable, names, scales, bounds, centers, width, common_fixed, rm_cfg, fam_cfg, opt,
                       nulls, starts):
    """layout "per-center": one response model per center, on center +- k width (width: the largest sigma of any
    family in each coordinate), each validated on its own; the fits to the toys of a null family use the model whose
    box holds the fitted family's fit to that null with a margin of k width (up to MARGIN_TOL of the half-width). A
    union box spanning distant centers holds corners that no fit visits and where the provider is least polynomial
    (strong reacceleration at low diffusion); separate boxes avoid them. A fit to a null that no box holds adds a
    center there (at most 3 passes). Returns ({null: {family: SurrogateFit}}, record, None)."""
    k = rm_cfg["half_width_sigma"]
    lo_d, hi_d = np.array([b[0] for b in bounds]), np.array([b[1] for b in bounds])
    subs, owners = [], []

    def add(center, owner):
        rm = build_response_model(model, names, scales, [center], [width], common_fixed, rm_cfg, bounds,
                                  fam_cfg["seed"] + 11 + 101 * len(subs))
        subs.append(rm)
        owners.append(owner)

    def surrogate(rm, f):
        fixed_t = {n: _to_fit(f["fixed"][n], sc) for n, sc in zip(names, scales) if n not in f["free"]}
        f_names = [n for n in names if n in f["free"]]
        return SurrogateFit(model, rm, f_names, [model.params[n]["scale"] for n in f_names], fixed_t, (names, bounds))

    def holds(rm, t):
        return (rm.inside(np.maximum(t - k * width, lo_d), MARGIN_TOL)
                and rm.inside(np.minimum(t + k * width, hi_d), MARGIN_TOL))
    for f, c in zip(usable, centers):
        add(c, f["family"])
    assignment, passes = {}, []
    for _ in range(3):
        missing = []
        for null, (mu, nu) in nulls.items():
            for g in usable:
                key = (null, g["family"])
                if key in assignment:
                    continue
                if g["family"] == null:
                    assignment[key] = owners.index(null)
                    continue
                landed = None
                for j, rm in enumerate(subs):
                    sf = surrogate(rm, g)
                    _, z, ok, reason = sf.fit(mu, nu, starts[g["family"]], opt)
                    t = sf.full_t(z[:sf.k])
                    if ok and holds(rm, t):
                        assignment[key] = j
                        break
                    if landed is None and reason in ("ok", "left-response-box"):
                        landed = t
                if key not in assignment and landed is not None:
                    missing.append((key, landed))
        passes.append({"sub_models": len(subs), "fits_without_a_box": len(missing)})
        if not missing:
            break
        for key, t in missing:
            add(np.clip(t, lo_d, hi_d), f"{key[1]} fitted to the null of {key[0]}")
    for null in nulls:
        for g in usable:
            assignment.setdefault((null, g["family"]), owners.index(g["family"]))
    by_name = {f["family"]: f for f in usable}
    sfs_by_null = {null: {g: surrogate(subs[assignment[(null, g)]], by_name[g]) for g in by_name} for null in nulls}
    records = [dict(rm.record(), center_of=owner) for rm, owner in zip(subs, owners)]
    error = {name: [float(max(r["error_component"][name][i] for r in records))
                    for i in range(len(records[0]["error_component"][name]))] for name in records[0]["error_component"]}
    record = {"layout": "per-center", "kind": records[0]["kind"], "half_width_sigma": k,
              "sub_models": records, "box_passes": passes,
              "assignment": [{"null": n, "family": g, "sub_model": j} for (n, g), j in sorted(assignment.items())],
              "provider_evaluations": sum(r["provider_evaluations"] for r in records),
              "validation": {"points": sum(r["validation"]["points"] for r in records),
                             "max_error_over_sigma": max(r["validation"]["max_error_over_sigma"] for r in records),
                             "tolerance": records[0]["validation"]["tolerance"],
                             "passed": all(r["validation"]["passed"] for r in records)},
              "error_component": error}
    return sfs_by_null, record, None


# --------------------------------------------------------------------------- posterior
def _covers(rm, names, fixed, t_hat, sig, k_sigma, bounds) -> bool:
    """True when a response model can be reused: same coordinates, its fixed values among ours, and its box holds
    t_hat +- k sigma (clipped to the domain)."""
    if rm is None or rm.names != list(names) or any(fixed.get(n) != v for n, v in rm.fixed.items()):
        return False
    lo = np.maximum(t_hat - k_sigma * sig, [b[0] for b in bounds])
    hi = np.minimum(t_hat + k_sigma * sig, [b[1] for b in bounds])
    return rm.inside(lo) and rm.inside(hi)


def run_posterior(model, fit, pcfg, rm_cfg, opt, rm=None):
    from bayes_diagnostics import diagnose
    fi = fit["_internal"]
    names, scales, bounds = fi["names"], fi["scales"], fi["bounds"]
    if _exactly_flat(fi["Ffull"]):
        raise FitRefused("flat-direction-in-posterior", f"family {fit['family']} has an exactly flat direction; its "
                         "posterior along it is the prior")
    k = len(names)
    sig = np.sqrt(np.diag(fi["cov_full"]))
    reused = _covers(rm, names, fi["fixed"], np.asarray(fi["t_hat"]), sig[:k], rm_cfg["half_width_sigma"], bounds)
    if not reused:
        rm = build_response_model(model, names, scales, [fi["t_hat"]], [sig[:k]], fi["fixed"], rm_cfg, bounds,
                                  pcfg["seed"] + 13)
    sf = SurrogateFit(model, rm, names, scales, {}, (names, bounds))
    aux = [n["aux"] for n in model.nuisances]
    z_hat = np.concatenate([fi["t_hat"], fi["nu"]])
    prop = (2.38 ** 2 / len(z_hat)) * fi["cov_full"] + 1e-12 * np.eye(len(z_hat))
    L = np.linalg.cholesky(prop)
    chains_n, steps = pcfg["chains"], pcfg["steps"]
    burn = int(steps * pcfg.get("burn_fraction", 0.5))
    rng = np.random.default_rng(pcfg["seed"])
    draws = np.zeros((chains_n, steps - burn, len(z_hat)))
    outside, accepted = 0, 0
    for c in range(chains_n):
        z = np.clip(z_hat + 2.0 * L @ rng.normal(size=len(z_hat)) / 2.38, sf.lo, sf.hi)
        lp = -0.5 * sf.chi2(z, None, aux)
        for s in range(steps):
            prop_z = z + L @ rng.normal(size=len(z))
            if np.any(prop_z < sf.lo) or np.any(prop_z > sf.hi):
                outside += 1
            else:
                lp_new = -0.5 * sf.chi2(prop_z, None, aux)
                if math.log(rng.uniform()) < lp_new - lp:
                    z, lp = prop_z, lp_new
                    accepted += 1
            if s >= burn:
                draws[c, s - burn] = z
    coords = [f"ln({n})" if s == "log" else n for n, s in zip(names, scales)] + [n["name"] for n in model.nuisances]
    diag = diagnose({c: draws[:, :, j].tolist() for j, c in enumerate(coords)}, (0.16, 0.5, 0.84), RHAT_MAX,
                    math.ceil(ESS_MIN / chains_n))
    out = {"family": fit["family"], "sampler": {"name": "random-walk Metropolis (Gaussian proposal from the inverse "
                                                         "Fisher matrix, scale 2.38^2/d)", "chains": chains_n,
                                                 "steps": steps, "burn_in": burn, "seed": pcfg["seed"]},
           "priors": {**{c: "uniform in the response box" for c in coords[:k]},
                      **{n["name"]: (f"normal(aux {n['aux']}, sigma {n['prior_sigma']})" if n["prior_sigma"] else
                                     "uniform in the multiplier bounds") for n in model.nuisances}},
           "acceptance": accepted / (chains_n * steps), "proposals_outside_box": outside,
           "response_model": dict(rm.record(), reused_from_family_calibration=reused), "diagnostics": diag}
    rhats = [p["rhat"] for p in diag["parameters"].values()]
    ess = [min(p["ess_bulk"], p["ess_tail"]) for p in diag["parameters"].values()]
    out["rhat_max_seen"], out["ess_min_seen"] = float(max(rhats)), float(min(ess))
    out["fraction_outside_box"] = outside / (chains_n * steps)
    if out["fraction_outside_box"] > MAX_OUTSIDE_FRACTION:
        out["status"] = "unvalidated"
        out["reason"] = (f"{outside} proposals ({out['fraction_outside_box']:.2%}) left the response box: the posterior "
                         "would be truncated by the box, so no interval is reported")
    elif diag["status"] == "converged" and max(rhats) <= RHAT_MAX and min(ess) >= ESS_MIN:
        out["status"] = "ok"
        out["intervals_68"] = {c: {"q16": float(np.quantile(draws[:, :, j], 0.16)),
                                   "median": float(np.quantile(draws[:, :, j], 0.5)),
                                   "q84": float(np.quantile(draws[:, :, j], 0.84))} for j, c in enumerate(coords)}
    else:
        out["status"] = "unvalidated"
        out["reason"] = (f"R-hat {max(rhats):.4g} (limit {RHAT_MAX}) or ESS {min(ess):.4g} (limit {ESS_MIN}): no "
                         "posterior interval is reported")
    return out


# --------------------------------------------------------------------------- artifacts
def theory_spec_artifact(base_spec: dict, entries: list, labels, cfg_ref: str) -> dict:
    from contracts import CONTRACTS_VERSION
    doc = copy.deepcopy(base_spec)
    doc["contract_version"] = CONTRACTS_VERSION
    doc["artifact_id"] = f"{base_spec.get('artifact_id', 'theory-spec')}-propagation-fit"
    doc["objective"] = ("Theory spec with the degenerate directions found by a propagation fit (profile-likelihood "
                        "scans, object form, with the range where each holds); the rest is copied from "
                        f"{base_spec.get('artifact_id')}")
    doc.setdefault("versions", {})["contracts"] = CONTRACTS_VERSION
    doc["provenance"] = dict(doc.get("provenance") or {}, producer_skill="hep-statistics",
                             created=date.today().isoformat())
    doc["inputs"] = [{"ref": cfg_ref, "artifact_type": "theory-spec", "artifact_id": base_spec.get("artifact_id"),
                      "status": list(base_spec.get("status") or [])}]
    doc["status"] = sorted(set(doc.get("status") or []) | set(labels))
    doc["extension"]["degenerate_directions"] = entries
    return doc


def statistical_result_artifact(result: dict, labels) -> dict:
    from contracts import CONTRACTS_VERSION, trace
    from contracts.identity import plugin_release
    fits = [f for f in result["fits"] if f.get("status") == "converged"]
    results = {"provider_point_evaluations": result["provider_evaluations"]["points_sent"]}
    for f in fits:
        results[f"chi2_{f['family']}"] = f["chi2"]
        results[f"dof_{f['family']}"] = f["dof"]
        for p in f["parameters"]:
            results[f"{p['name']}_{f['family']}"] = p["best_fit"]
            if p["sigma_coordinate"] is not None:
                results[f"sigma_{p['fit_coordinate']}_{f['family']}"] = p["sigma_coordinate"]
    toys = result.get("toys") or {}
    cov = {"check": "not-checked", "method": "not run"}
    seeds = {}
    if toys.get("ensemble"):
        seeds["coverage_toys"] = toys["ensemble"]["seed"]
    if (result.get("family_calibration") or {}).get("seed") is not None:
        seeds["family_toys"] = result["family_calibration"]["seed"]
    if (result.get("posterior") or {}).get("sampler"):
        seeds["posterior"] = result["posterior"]["sampler"]["seed"]
    if toys.get("status") == "ok":
        first = next(iter(toys["tests"].values()))
        cov = {"check": "toys", "method": "plug-in toys at a true point; profile delta chi2 <= 1 at the true value",
               "n_toys": toys["generated"], "coverage": first["coverage_wilks"]["headline"]["value"],
               "seed": toys["ensemble"]["seed"]}
    status = result["status"]
    fit_status = {"ok": "converged", "failed": "failed"}.get(status, "converged-with-warnings")
    lab = sorted(set(labels) | ({"failed"} if status == "failed" else set()))
    prov = trace.provenance()
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": "propagation-fit-result",
            "artifact_type": "statistical-result",
            "objective": "Multi-dataset propagation fit through a cr-provider/1 provider",
            "bindings": {"experiments": [], "theory": []},
            "versions": {"plugin": json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"],
                         "contracts": CONTRACTS_VERSION, "plugin_release": plugin_release(), "profiles": {}},
            "provenance": {"producer_skill": "hep-statistics", **prov, "created": date.today().isoformat(),
                           "evidence_ids": []},
            "inputs": [], "outputs": [], "status": lab, "unresolved_inputs": [],
            "required_capabilities": ["stats:result-semantics"],
            "extension": {"paradigm": "frequentist",
                          "likelihood": {"form": "Gaussian with the full data covariance per dataset, Gaussian priors "
                                                 "of the component multipliers profiled exactly",
                                         "backend": "skills/hep-statistics/scripts/propagation_fit.py"},
                          "parameters_of_interest": [p["name"] for f in fits[:1] for p in f["parameters"]],
                          "nuisances": [n["name"] for f in fits[:1] for n in f["nuisances"]],
                          "fit_status": fit_status, "test_statistic": "profile delta chi2",
                          "construction": "profile-likelihood-wilks", "coverage": cov, "results": results,
                          **({"seeds": seeds} if seeds else {})}}


# --------------------------------------------------------------------------- driver
def _opt_cfg(cfg) -> dict:
    o = _keys(cfg.get("optimizer") or {}, {"max_iterations", "max_restarts", "seed"}, "optimizer")
    return {"max_iterations": _int(o.get("max_iterations", 100), "optimizer.max_iterations", 1, 10000),
            "max_restarts": _int(o.get("max_restarts", MAX_RESTARTS), "optimizer.max_restarts", 0, MAX_RESTARTS),
            "seed": _int(o.get("seed", 0), "optimizer.seed", 0, 2 ** 31)}


def _rm_cfg(cfg) -> dict:
    r = _keys(cfg.get("response_model") or {}, {"kind", "nodes", "degree", "design_points", "half_width_sigma",
                                                 "validation_points", "tolerance_sigma", "layout"}, "response_model")
    if r.get("layout", "union") not in ("union", "joint", "per-center"):
        raise FitInputError("response_model.layout must be 'union', 'joint' or 'per-center'")
    kind = r.get("kind", "tensor")
    if kind not in ("tensor", "polynomial", "provider"):
        raise FitInputError("response_model.kind must be 'tensor', 'polynomial' or 'provider'")
    return {"kind": kind, "degree": _int(r.get("degree", 4), "response_model.degree", 1, 8),
            "design_points": _int(r.get("design_points", 128), "response_model.design_points", 4, 4096),
            "nodes": _int(r.get("nodes", 7), "response_model.nodes", 3, 15),
            "half_width_sigma": _num(r.get("half_width_sigma", 5.0), "response_model.half_width_sigma"),
            "validation_points": _int(r.get("validation_points", 12), "response_model.validation_points", 4, 1000),
            "tolerance_sigma": _num(r.get("tolerance_sigma", 0.02), "response_model.tolerance_sigma"),
            "layout": r.get("layout", "union")}


def _per_point_requests(cfg, datasets, decomposable) -> bool:
    """provider_requests: "per-dataset" (default; one request per point and dataset) or "per-point" (one request per
    point naming every dataset's observable, so one provider run serves all datasets; the observable ids must differ,
    and only a provider that is not decomposable is supported, since its prediction is the one component)."""
    mode = cfg.get("provider_requests", "per-dataset")
    if mode not in ("per-dataset", "per-point"):
        raise FitInputError("provider_requests must be 'per-dataset' or 'per-point'")
    if mode == "per-point":
        ids = [ds.observable for ds in datasets]
        if len(set(ids)) != len(ids):
            raise FitInputError(f"provider_requests 'per-point' needs distinct observable ids, got {ids}: two "
                                "observables with the same id in one request make the predictions ambiguous")
        if decomposable:
            raise FitInputError("provider_requests 'per-point' is supported only for a provider that is not "
                                "decomposable (its components per observable are not defined in one request)")
    return mode == "per-point"


def _family(fams, name, what):
    for f in fams:
        if f["name"] == name:
            return f
    raise FitInputError(f"{what}: family {name!r} is not an expressible declared family")


def run(cfg: dict, base: Path, registry, cache_dir=None, max_evaluations=2000, allow_outside=False,
        out_dir: Path | None = None, cfg_ref="config") -> dict:
    from core.provider.registry import RegistryError, load_registry, parse_registry
    from core.provider.runner import ProviderRunner
    _keys(cfg, CONFIG_KEYS, "the configuration")
    steps = (cfg.get("posterior") or {}).get("steps") if isinstance(cfg.get("posterior"), dict) else None
    if isinstance(steps, int) and not isinstance(steps, bool) and steps > MAX_CHAIN_STEPS:
        raise FitRefused("chain-step-cap", f"posterior.steps {steps} exceeds the cap of {MAX_CHAIN_STEPS} steps per "
                         "chain (r3 C2 loop limit); nothing is run")
    prov = _keys(cfg.get("provider"), {"id", "version"}, "provider")
    try:
        entries = parse_registry(registry) if isinstance(registry, dict) else load_registry(registry)
    except RegistryError as exc:
        raise FitInputError(str(exc)) from None
    entry = entries.get(prov.get("id"))
    if entry is None:
        raise FitRefused("unregistered-provider", f"provider {prov.get('id')!r} is not in the registry the caller passed "
                         f"in (registered: {sorted(entries)})")
    if prov.get("version") != entry.version:
        raise FitRefused("provider-version-mismatch", f"the registry lists {entry.provider_id} version "
                         f"{entry.version!r}, the configuration names {prov.get('version')!r}")
    domain = entry.declaration["domain"]
    ds_cfg = cfg.get("datasets")
    if not isinstance(ds_cfg, list) or not ds_cfg:
        raise FitInputError("datasets must be a non-empty list")
    datasets = []
    for k, d in enumerate(ds_cfg):
        d = _keys(d, {"name", "measurement", "observable", "period"}, f"datasets[{k}]")
        if not isinstance(d.get("name"), str) or not isinstance(d.get("observable"), str):
            raise FitInputError(f"datasets[{k}] needs a name and an observable id")
        datasets.append(Dataset(d["name"], _load(d.get("measurement"), base, f"datasets[{k}].measurement"),
                                d["observable"], base, d.get("period")))
    if len({ds.name for ds in datasets}) != len(datasets):
        raise FitInputError("dataset names must be unique")
    periods = sorted({ds.period for ds in datasets if ds.period})
    if periods:
        raise FitRefused("modulation-needs-isotopic-lis",
                         f"datasets with periods {periods} need phi_<period>_gv ({[f'phi_{p}_gv' for p in periods]}) "
                         "applied per isotope before ratios are formed (P4); provider "
                         f"{entry.provider_id} returns only {entry.declaration['observables']}, no isotopic LIS")
    fixed_global = {k: _num(v, f"fixed.{k}") for k, v in _keys(cfg.get("fixed") or {}, list(domain), "fixed").items()}
    transport = None
    if cfg.get("transport") is not None:
        transport = _load(cfg["transport"], base, "transport")
        if not isinstance(transport, dict):
            raise FitInputError("transport must be a JSON object (contracts ext_theory_spec transport block) or a path")
    opt = _opt_cfg(cfg)
    rm_cfg = _rm_cfg(cfg)
    warnings = []
    labels = set()
    for ds in datasets:
        labels.update(ds.labels)
    with ProviderRunner(registry, cache_dir=cache_dir, allow_outside=allow_outside, session="serve") as runner:
        decomposable = bool(entry.declaration.get("decomposable"))
        ev = Evaluator(runner, entry.provider_id, entry.version, datasets, fixed_global, max_evaluations,
                       decomposable=decomposable, transport=transport,
                       per_point=_per_point_requests(cfg, datasets, decomposable))
        model = Model(cfg, datasets, ev, domain)
        if model.nuisances and not decomposable:
            raise FitRefused("not-decomposable", f"provider {entry.provider_id} declares decomposable: false, so its "
                             "predictions have no channel components for the multipliers "
                             f"{[n['name'] for n in model.nuisances]}; a cross-section change needs a provider "
                             "parameter or a separate run (a model alternative, R8)")
        bad = sorted(set(model.params) - set(domain))
        if bad:
            raise FitRefused("unknown-parameter", f"parameters {bad} are not in the domain of provider "
                             f"{entry.provider_id} ({sorted(domain)})")
        fams_cfg = cfg.get("families") or [{"name": "all-free", "free": list(model.params), "fixed": {}}]
        stated = set(model.params) | set(fixed_global)
        for f in fams_cfg:
            stated |= set((f or {}).get("fixed") or {}) if isinstance(f, dict) else set()
        defaulted = sorted(set(domain) - stated)
        if defaulted:
            warnings.append(f"provider parameters {defaulted} are neither fitted nor fixed: they keep the provider's own "
                            "default values; state them under fixed to make the choice explicit")
        families, not_expressible = classify_families(fams_cfg, model, domain)
        if not families:
            raise FitRefused("no-expressible-family", "no declared family can be expressed by provider "
                             f"{entry.provider_id}: " + "; ".join(f["reason"] for f in not_expressible))
        # first evaluation at the start of the first family: bin semantics and the gate, before any fit
        f0 = families[0]
        names0, scales0, bounds0 = model.coords(f0["free"])
        start_vals = {n: model.params[n]["start"] for n in names0}
        for n, v in start_vals.items():
            if not domain[n]["min"] <= v <= domain[n]["max"]:
                raise FitRefused("out-of-domain", f"start {n} = {v:.6g} is outside the provider domain "
                                 f"[{domain[n]['min']:.6g}, {domain[n]['max']:.6g}]; the fit starts only inside it")
        start_fixed = dict(f0.get("fixed") or {})
        ev.components({**start_fixed, **start_vals})
        model.bind_channels(ev.channels)
        point_keys = ev.point({**start_fixed, **start_vals})
        run_ids = cfg.get("run_record_keys") or []
        if not isinstance(run_ids, list) or not all(isinstance(k, str) for k in run_ids):
            raise FitInputError("run_record_keys must be a list of parameter_point keys")
        gates = [_gate(ds, *ev.first_predictions[ds.name], cfg.get("gate_plan") or {}, entry, point_keys, run_ids)
                 for ds in datasets]
        fits = []
        for fam in families:
            fits.append(fit_family(model, fam, opt, fixed_global))
        wanted = cfg.get("intervals") or []
        if not isinstance(wanted, list) or not all(isinstance(w, str) for w in wanted):
            raise FitInputError("intervals must be a list of parameter names")
        for f in fits:
            todo = [w for w in wanted if w in f["free"] and f["status"] == "converged"
                    and f["parameters"][f["free"].index(w)]["constrained"]]
            if todo:
                f["profile_intervals"] = [profile_interval(model, f, w, opt) for w in todo]
        status = "ok" if all(f["status"] == "converged" for f in fits) else "failed"
        result = {"label": LABEL, "provider": {"id": entry.provider_id, "version": entry.version,
                                               "component": entry.component, "user_supplied": entry.user_supplied,
                                               "decomposable": decomposable, "transport": transport},
                  "datasets": [{"name": ds.name, "observable": ds.observable, "axis": ds.axis, "bins": len(ds.y),
                                "bin_semantics": ds.bin_semantics, "covariance": ds.cov_info} for ds in datasets],
                  "gate": gates, "channels": ev.channels, "families_not_expressible": not_expressible,
                  "fits": fits, "warnings": warnings,
                  "loop_limits": {"max_restarts": MAX_RESTARTS, "toy_failure_limit": TOY_FAILURE_LIMIT,
                                  "max_chain_steps": MAX_CHAIN_STEPS, "rhat_max": RHAT_MAX, "ess_min": ESS_MIN}}
        by_name = {f["family"]: f for f in fits}
        # degeneracies (A3): screen entries per fit; profile scan on request
        scan_cfg = cfg.get("degeneracy_scan")
        degeneracies, scans = [], []
        if scan_cfg is not None:
            from degeneracy import ScanInputError, parse_scan, profile_scan
            scan_cfg = dict(scan_cfg)
            fam = _family(families, scan_cfg.pop("family", families[0]["name"]), "degeneracy_scan")
            fit = by_name[fam["name"]]
            fi = fit["_internal"]
            try:
                scan = parse_scan(scan_cfg, fi["names"])
            except ScanInputError as exc:
                raise FitInputError(str(exc)) from None

            def m2ll(q, fi=fi):
                comps = model.ev.components(model.values(fi["names"], fi["scales"], q, fi["fixed"]))
                r, _ = model.profiled(comps)
                return float(r @ r)
            level2, scans, scan_warn = profile_scan(m2ll, np.asarray(fi["t_hat"]), fi["bounds"], fi["names"],
                                                    fi["scales"], scan, fit["chi2"], fi["degenerate"])
            degeneracies = level2
            warnings.extend(scan_warn)
            result["degeneracy_scan_family"] = fam["name"]
        result["degeneracies"] = [d for f in fits for d in f["degenerate_directions"]] + degeneracies
        result["profile_scans"] = scans
        # covariance alternatives (P9)
        alt = cfg.get("covariance_alternatives")
        if alt is not None:
            result["covariance_alternatives"] = covariance_alternatives(model, families, alt, opt, fixed_global)
        if cfg.get("family_toys") is not None and len(fits) > 1:
            ft = _keys(cfg["family_toys"], {"n", "seed", "alpha"}, "family_toys")
            fcfg = {"n": _int(ft.get("n", 200), "family_toys.n", 20, 100000),
                    "seed": _int(ft.get("seed", 1), "family_toys.seed", 0, 2 ** 31),
                    "alpha": _num(ft.get("alpha", 0.05), "family_toys.alpha")}
            try:
                result["family_calibration"] = calibrate_families(model, fits, fcfg, rm_cfg, opt, fixed_global)
            except FitRefused as exc:   # the fits stay reported; the calibration is failed with its reason
                result["family_calibration"] = {"status": "failed", "reason": exc.reason, "detail": exc.detail,
                                                "alpha": fcfg["alpha"], "n_toys": fcfg["n"], "seed": fcfg["seed"]}
            if result["family_calibration"].get("status") != "ok":
                status = "failed"
        result["families"] = {"declared": [f["name"] for f in families] + [f["family"] for f in not_expressible],
                              "expressible": [f["name"] for f in families],
                              "not_expressible": [f["family"] for f in not_expressible],
                              "surviving": (result.get("family_calibration") or {}).get("surviving")}
        if cfg.get("toys") is not None:
            tc = _keys(cfg["toys"], {"family", "n", "seed", "truth", "test", "max_iterations"}, "toys")
            tcfg = {"n": _int(tc.get("n", 1000), "toys.n", 10, 1_000_000),
                    "seed": _int(tc.get("seed", 1), "toys.seed", 0, 2 ** 31), "truth": dict(tc.get("truth") or {}),
                    "test": list(tc.get("test") or [])}
            if "max_iterations" in tc:
                tcfg["max_iterations"] = _int(tc["max_iterations"], "toys.max_iterations", 1, 10000)
            if not tcfg["test"]:
                raise FitInputError("toys.test must name at least one quantity")
            fam = _family(families, tc.get("family", families[0]["name"]), "toys")
            result["toys"] = run_toys(model, fam, tcfg["truth"], tcfg, rm_cfg, opt, fixed_global)
            if result["toys"]["status"] != "ok":
                status = "failed"
        if cfg.get("posterior") is not None:
            pc = _keys(cfg["posterior"], {"family", "chains", "steps", "seed", "burn_fraction"}, "posterior")
            steps = pc.get("steps", 20000)
            pcfg = {"chains": _int(pc.get("chains", 4), "posterior.chains", 2, 64),
                    "steps": _int(steps, "posterior.steps", 100, MAX_CHAIN_STEPS),
                    "seed": _int(pc.get("seed", 1), "posterior.seed", 0, 2 ** 31),
                    "burn_fraction": _num(pc.get("burn_fraction", 0.5), "posterior.burn_fraction")}
            fam = _family(families, pc.get("family", families[0]["name"]), "posterior")
            if by_name[fam["name"]]["status"] != "converged":
                raise FitRefused("not-converged", f"family {fam['name']} did not converge; no posterior is sampled")
            shared = (result.get("family_calibration") or {}).get("_rm")
            result["posterior"] = run_posterior(model, by_name[fam["name"]], pcfg, rm_cfg, opt, shared)
            if result["posterior"]["status"] != "ok":
                labels.add("unvalidated")
        labels.update(ev.labels)
        result["provider_evaluations"] = dict(runner.stats, points_sent=ev.points_sent,
                                              max_evaluations=max_evaluations,
                                              **evaluation_records(ev.records, cfg.get("computational_runs"), base))
    result["status"] = status
    if status == "failed":
        reasons = [f.get("reason") for f in fits if f.get("reason")]
        for key in ("toys", "family_calibration"):
            if (result.get(key) or {}).get("reason"):
                reasons.append(result[key]["reason"])
        result["reason"] = reasons[0] if reasons else "failed"
    result["status_label"] = sorted(labels)
    for f in fits:
        f.pop("_internal", None)
    (result.get("family_calibration") or {}).pop("_rm", None)
    if out_dir is not None:
        write_outputs(result, cfg, base, out_dir, sorted(labels), cfg_ref)
    return result


def evaluation_records(records, runs_ref, base: Path) -> dict:
    """The provider's evaluation record of every result the fit used (one per point and dataset, cache hits included,
    since a cached result keeps the record of the run that made it) and, when the configuration names the folder that
    holds the provider's computational-run artifacts (computational_runs), each reference resolved there with the
    tools and versions those artifacts name."""
    out = {"records": records,
           "records_with_computational_run": sum(1 for r in records if r.get("computational_run_ref"))}
    if runs_ref is None:
        return out
    folder = Path(runs_ref) if Path(runs_ref).is_absolute() else base / runs_ref
    if not folder.is_dir():
        raise FitInputError(f"computational_runs: {folder} is not a folder")
    wanted = {r["computational_run_ref"] for r in records if r.get("computational_run_ref")}
    found: dict = {}
    for path in folder.rglob("*.computational-run.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(doc, dict) and doc.get("artifact_id") in wanted and doc.get("artifact_type") == "computational-run":
            found[doc["artifact_id"]] = doc
    tools: dict = {}
    for r in records:
        doc = found.get(r.get("computational_run_ref"))
        r["computational_run_resolved"] = doc is not None
        for t in ((doc or {}).get("extension") or {}).get("tools") or []:
            if isinstance(t, dict):
                tools[(t.get("name"), t.get("version"))] = {"name": t.get("name"), "version": t.get("version")}
    out["computational_runs"] = {"resolved": sum(1 for r in records if r["computational_run_resolved"]),
                                 "unresolved_refs": sorted(wanted - set(found)),
                                 "tools": sorted(tools.values(), key=lambda t: (str(t["name"]), str(t["version"])))}
    return out


def covariance_alternatives(model, families, alt, opt, fixed_global):
    import build_covariance
    alt = _keys(alt, {"family", "dataset", "model", "source", "lengths"}, "covariance_alternatives")
    fam = _family(families, alt.get("family", families[0]["name"]), "covariance_alternatives")
    ds = next((d for d in model.datasets if d.name == alt.get("dataset")), None)
    if ds is None:
        raise FitInputError("covariance_alternatives.dataset must name a dataset")
    lengths = alt.get("lengths")
    if not isinstance(lengths, list) or len(lengths) < 2:
        raise FitInputError("covariance_alternatives.lengths must list at least two correlation lengths")
    doc = dict(_keys(alt.get("model"), {"sources", "units"}, "covariance_alternatives.model"))
    doc["values"] = ds.y.tolist()
    doc["x"] = [math.sqrt(a * b) for a, b in zip(ds.edges, ds.edges[1:])]
    nominal = ds.cov
    rows = []
    try:
        for length in lengths:
            built = build_covariance.build(doc, {"name": alt.get("source"), "value": _num(length, "lengths")})
            if not (all(c["psd"] for c in built["checks"].values()) and built["total_check"]["psd"]):
                raise FitRefused("covariance-not-positive-definite", f"length {length}: the built covariance is not PSD")
            ds.set_covariance(built["total"])
            f = fit_family(model, fam, opt, fixed_global)
            rows.append({"length": float(length), "status": f["status"], "chi2": f["chi2"], "dof": f["dof"],
                         "parameters": {p["name"]: {"best_fit": p["best_fit"], "sigma_coordinate": p["sigma_coordinate"]}
                                        for p in f["parameters"]}})
    except build_covariance.InputError as exc:
        raise FitInputError(f"covariance_alternatives.model: {exc}") from None
    finally:
        ds.set_covariance(nominal)
    return {"family": fam["name"], "dataset": ds.name, "source": alt.get("source"), "alternatives": rows,
            "note": "model alternatives of the correlation model (P9): fitted one by one, never combined; the spread "
                    "of the best fits is the sensitivity to the assumption"}


def write_outputs(result, cfg, base, out_dir: Path, labels, cfg_ref):
    from contracts.validate import validate_artifact
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    written = {"result": "result.json"}
    sr = statistical_result_artifact(result, labels)
    rep = validate_artifact(sr)
    if not rep.ok:
        raise FitRefused("artifact-invalid", "statistical-result does not validate: " + json.dumps(rep.as_dict())[:800])
    (out_dir / "statistical-result.json").write_text(json.dumps(sr, indent=1) + "\n", encoding="utf-8")
    written["statistical_result"] = "statistical-result.json"
    if cfg.get("theory_spec") is not None:
        base_spec = _load(cfg["theory_spec"], base, "theory_spec")
        entries = [d for d in result["degeneracies"] if d.get("evidence") == "profile-scan" and d.get("valid_range")]
        if not entries:
            result["warnings"].append("no profile-scan degeneracy: the theory-spec is not written (a fisher-screen entry "
                                      "has no valid_range)")
        else:
            spec = theory_spec_artifact(base_spec, entries, labels,
                                        cfg["theory_spec"] if isinstance(cfg["theory_spec"], str) else "theory-spec")
            rep = validate_artifact(spec)
            if not rep.ok:
                raise FitRefused("artifact-invalid", "theory-spec does not validate: " + json.dumps(rep.as_dict())[:800])
            (out_dir / "theory-spec.json").write_text(json.dumps(spec, indent=1) + "\n", encoding="utf-8")
            written["theory_spec"] = "theory-spec.json"
    result["written"] = written
    (out_dir / "result.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")


def _jsonable(x):
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if np is not None and isinstance(x, np.ndarray):
        return _jsonable(x.tolist())
    if np is not None and isinstance(x, np.generic):
        return x.item()
    if isinstance(x, float) and not math.isfinite(x):
        return None
    return x


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fit", help="fit a configuration (see the module docstring)")
    f.add_argument("--input", required=True, help="configuration JSON")
    f.add_argument("--provider-registry", required=True, help="registry from tools/provider_registry.py --write")
    f.add_argument("--cache-dir", help="provider cache folder (core/provider)")
    f.add_argument("--out", help="folder for result.json, statistical-result.json, theory-spec.json")
    f.add_argument("--max-evaluations", type=int, default=2000, help="cap on provider point evaluations (default 2000)")
    f.add_argument("--allow-outside-validated-range", action="store_true",
                   help="evaluate outside the provider domain; results labelled outside-validated-range")
    args = ap.parse_args(argv)
    if np is None or optimize is None:
        print(json.dumps({"status": "rejected", "error": "propagation_fit.py needs NumPy and SciPy"}))
        return 2
    path = Path(args.input)
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "error": f"cannot read {path}: {exc}"}))
        return 2
    try:
        result = run(cfg, path.resolve().parent, args.provider_registry, cache_dir=args.cache_dir,
                     max_evaluations=args.max_evaluations, allow_outside=args.allow_outside_validated_range,
                     out_dir=Path(args.out) if args.out else None, cfg_ref=path.name)
    except FitInputError as exc:
        print(json.dumps({"status": "rejected", "error": str(exc), "label": LABEL}))
        return 2
    except FitIncomplete as exc:
        print(json.dumps({"status": "incomplete", "error": str(exc), "missing": exc.missing, "label": LABEL}))
        return 3
    except FitRefused as exc:
        print(json.dumps({"status": "failed", "reason": exc.reason, "detail": exc.detail, "label": LABEL}))
        return 1
    print(json.dumps(_jsonable(result), indent=1))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
