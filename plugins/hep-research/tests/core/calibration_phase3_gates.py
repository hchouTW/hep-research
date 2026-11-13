"""The registered gate run of phase 3 of the simulator calibration workflow and its G8 calibrations (task card
`docs/dev/simulator-calibration/simcal-tasks/phase-3.md`, "Thresholds and test designs"; wave 3, WP-H). Not a unit test
module.

  python3 calibration_phase3_gates.py --list                        the task table (JSON: index, family, key, kwargs)
  python3 calibration_phase3_gates.py --task K --out DIR            one Slurm array task (seeds from the task's own keys)
  python3 calibration_phase3_gates.py --merge DIR --out FILE        merge, decide each item against its registered rule
  python3 calibration_phase3_gates.py --local --out FILE            the code path at tiny sizes (`smoke`, not evidence)

Families (one task each unless stated; every task a few minutes):
- `units`: the section 17 gate parts carried by existing unit tests, run as gate items (each test's outcome recorded;
  a negative test passes only when its negative is caught and its positive control passes): the P6 negative tests; the
  g4sim positive tests on the synthetic ZDC fixture (section 15.2); the response-layer parameters and phi tests.
- `zdc_fit`: the response-layer parameters of the ZDC (light yield and RESOLUTIONSCALE, re-digitization with the coupled
  default) fitted on truth-MC pseudo-data (D6) with sigma_noise from 5 independent batches (section 8.1).
- `phi_resim`: a resimulation-level phi on the toy detector: shift mode when section 5.5 holds (P8, G9), otherwise the
  surrogate model (P6) with phi profiled.
- `g8_3m` (+ `g8_3m_spot`): G8 at the full level for the three-method combination (reweighting, rerun, resimulation by
  the surrogate model) with the section 19-5 reading of A12: surrogate pseudo-data for the bulk, a full-simulation spot
  check at the injection points with independent seeds (decided by P6's rule, A16 (i)).
- `toy_g8`: the toy-detector G8 rows carried from phase 2 (calibrations 1, 6, 10, 12) at exposure 8000 per run, and
  `toy_g8_mm` the G8 item of calibration 15 on the bimodal variant.

Seeds: `default_rng([cal_seed(c, r), ...])` with c the family's calibration code below and r the repetition; every
output records the commit and the SHA-256 of the files that decide it. Everything is `synthetic`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import unittest
import warnings
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (str(ROOT), str(HERE), str(ROOT / "adapters" / "geant4" / "assets")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import calibration_phase2_cals as CA  # noqa: E402
import calibration_phase2_cals_c as CC  # noqa: E402
import calibration_phase2_gates as G  # noqa: E402
import calibration_phase3_g4 as P3  # noqa: E402

from core.calibration import closure as C  # noqa: E402
from core.calibration import emulator as EM  # noqa: E402
from core.calibration import fit as F  # noqa: E402
from core.calibration import identify  # noqa: E402
from core.calibration import interval as IV  # noqa: E402
from core.calibration import io  # noqa: E402
from core.calibration import likelihood as L  # noqa: E402
from core.calibration import shift as Sh  # noqa: E402
from core.calibration import toy  # noqa: E402
from core.calibration import toy_problem as TP  # noqa: E402

warnings.filterwarnings("ignore", message="The balance properties of Sobol")
LABEL = "synthetic"
SEED = 20261300
FILES = ["core/calibration/" + f for f in ("closure.py", "emulator.py", "evaluator_problem.py", "fit.py", "interval.py",
                                            "likelihood.py", "shift.py", "toy.py", "toy_problem.py")] + \
    ["adapters/geant4/assets/g4sim_calib_eval.py", "tests/core/calibration_zdc_fixture.py",
     "tests/core/calibration_phase3_g4.py",
     "tests/core/calibration_phase3_gates.py", "docs/dev/simulator-calibration/simcal-tasks/phase-3.md"]


def cal_seed(c: int, r: int) -> int:
    return int(np.random.SeedSequence([SEED, int(c), int(r)]).generate_state(1)[0])


def _rng(*parts) -> np.random.Generator:
    return np.random.default_rng([int(p) for p in parts])


def provenance() -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                                check=True, timeout=60).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", *FILES], cwd=ROOT, capture_output=True,
                                    text=True, timeout=60).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    return {"commit": commit, "dirty": dirty, "python": sys.version.split()[0], "numpy": np.__version__,
            "sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES if (ROOT / f).exists()}}


class _Problem(TP.ToyProblem):
    """The toy problem with bounded caches (each cached evaluation holds per-event influence arrays; the surrogate's
    design-point cache too), and V_MC multiplied by `fit_scale` in the fit (calibration 12's detection curve)."""

    fit_scale = 1.0
    CACHE_MAX = 64

    def _predict(self, params, seeds=None):
        if len(self._cache) > self.CACHE_MAX:
            self._cache.clear()
        if len(getattr(self.ev, "_design_cache", ())) > 8 * self.CACHE_MAX:
            self.ev._design_cache.clear()
        r = super()._predict(params, seeds)
        if self.fit_scale == 1.0:
            return r
        return {**r, "V_MC": np.asarray(r["V_MC"], float) * self.fit_scale}


# ================================================================== units: gate parts carried by unit tests
# kind: "negative" (the test asserts the negative's finding and its positive control), "positive"
EMULATOR_TESTS = "test_calibration_emulator."
PROBLEM_TESTS = "test_calibration_evaluator_problem."
EVALUATOR_TESTS = "test_calibration_g4sim_eval."
COUPLING_TESTS = "test_calibration_g4sim_eval_coupling."
KERNEL_TESTS = "test_calibration_kernel_check."
MAP_TESTS = "test_calibration_map."
PDE_TESTS = "test_calibration_pde_split."
UNIT_ITEMS = {
    "p6_negatives": {
        "part": "P6 negative tests",
        "tests": {EMULATOR_TESTS + "P6Arrays.test_delta_m_fails_on_a_large_difference": "negative",
                  EMULATOR_TESTS + "P6Arrays.test_pull_chi2_catches_an_understated_v_emu": "negative",
                  EMULATOR_TESTS + "P6Arrays.test_no_held_out_points_is_rejected": "negative",
                  EMULATOR_TESTS + "P6Arrays.test_twenty_held_out_points_decide_only_delta_m": "negative",
                  EMULATOR_TESTS + "P6Arrays.test_bonferroni_z": "positive",
                  EMULATOR_TESTS + "P6Arrays.test_from_input_with_bootstrap_replicas": "negative",
                  EMULATOR_TESTS + "P6Toy.test_too_few_design_points": "negative",
                  EMULATOR_TESTS + "P6Toy.test_spot_checks_are_held_back_and_mandatory": "negative",
                  EMULATOR_TESTS + "FinalMethod.test_surrogate_tier_decided_by_p6": "negative",
                  EMULATOR_TESTS + "SurrogateModel.test_query_outside_the_domain_is_rejected": "negative",
                  EMULATOR_TESTS + "G8Hook.test_spot_check_seeds_independent_of_training": "negative",
                  EMULATOR_TESTS + "P6JointReference.test_correlated_points_plain_reference_is_oversized_joint_is_not":
                      "negative",
                  EMULATOR_TESTS + "P6JointReference.test_joint_reference_catches_an_understated_covariance_on_"
                                   "correlated_points": "negative",
                  EMULATOR_TESTS + "P6JointReference.test_independent_points_both_references_agree": "positive"}},
    "g4sim_zdc_positive": {
        "part": "g4sim positive tests on the synthetic ZDC fixture (section 15.2)",
        "env": {P3.PRODUCTS_ENV: str(P3.OUT_ROOT)},     # the Geant4 products of campaign p3-g4 (unset: they skip)
        "tests": {PROBLEM_TESTS + "ResponseParametersP0": "positive",
                  PROBLEM_TESTS + "BirksRerunAgainstResimulation": "positive",
                  PROBLEM_TESTS + "CalorimeterProblem": "positive",
                  PROBLEM_TESTS + "Production": "positive",
                  EVALUATOR_TESTS + "Birks": "positive",
                  EVALUATOR_TESTS + "Redigitization": "positive",
                  EVALUATOR_TESTS + "NodeZero": "positive",
                  COUPLING_TESTS + "Coupling": "positive",
                  KERNEL_TESTS + "BirksSpotChecks": "positive",
                  KERNEL_TESTS + "SpotCheckApplicability": "positive"}},
    "response_phi": {
        "part": "the response-layer parameters of ZDC Phase 3 and phi at the resimulation level",
        "tests": {COUPLING_TESTS + "ScaleBinding": "positive",
                  EMULATOR_TESTS + "Combination": "positive",
                  MAP_TESTS + "TestMapTerm": "positive",
                  MAP_TESTS + "TestSection152FixedMap": "positive",
                  MAP_TESTS + "TestThetaNoise": "positive",
                  PDE_TESTS + "Routes": "positive",
                  PDE_TESTS + "SplitCheck": "positive",
                  PDE_TESTS + "Evaluator": "positive"}},
}
UNIT_RULE = ("every listed test passes; a test skipped with a reason starting 'requires Geant4' is recorded as "
             "`requires-geant4` (not judged, listed as open); any other skip, failure or error fails the item")
GEANT4_SKIP = "requires Geant4"


def _ids(suite) -> list:
    out = []
    for t in suite:
        out += _ids(t) if isinstance(t, unittest.TestSuite) else [t.id()]
    return out


def run_tests(ids: list) -> dict:
    """{test id: outcome} of the given test names (module.Class or module.Class.test), run in this process with the
    standard result (a name that does not load is an error)."""
    loader = unittest.TestLoader()
    outcomes: dict = {}
    for name in ids:
        try:
            suite = loader.loadTestsFromName(name)
        except Exception as exc:                          # noqa: BLE001 (a missing test is a failed gate item)
            outcomes[name] = {"outcome": "error", "detail": f"not loadable: {exc}"}
            continue
        names = _ids(suite)
        res = unittest.TestResult()
        suite.run(res)
        got = {t: {"outcome": "passed"} for t in names}
        for kind, rows in (("failed", res.failures), ("error", res.errors)):
            for tc, tb in rows:
                got[tc.id()] = {"outcome": kind, "detail": tb[-2000:]}
        for tc, reason in res.skipped:
            got[tc.id()] = {"outcome": "skipped", "reason": reason}
        for tc in [x for x, _ in res.expectedFailures] + list(res.unexpectedSuccesses):
            got[tc.id()] = {"outcome": "failed", "detail": "an expected-failure marker"}
        for t in [t for t in got if t.startswith("unittest.loader._FailedTest")]:
            got[name] = {**got.pop(t), "outcome": "error"}
        outcomes.update(got or {name: {"outcome": "error", "detail": "no test ran"}})
    return outcomes


def judge_units(item: str, outcomes: dict, names=None) -> dict:
    """The registered rule of a unit-test gate item (UNIT_RULE) on the recorded outcomes; `names` restricts the
    required tests (the `--local` smoke run only)."""
    spec = UNIT_ITEMS[item]
    kinds = {n: k for n, k in spec["tests"].items() if names is None or n in names}
    rows, ok, caught, open_g4 = [], True, [], []
    for tid, out in sorted(outcomes.items()):
        kind = next((k for n, k in kinds.items() if tid == n or tid.startswith(n + ".")), "positive")
        o = out["outcome"]
        if o == "skipped" and str(out.get("reason", "")).startswith(GEANT4_SKIP):
            status = "requires-geant4"
            open_g4.append(tid)
        elif o == "passed":
            status = "caught" if kind == "negative" else "passed"
            if kind == "negative":
                caught.append(tid)
        else:
            status = o
            ok = False
        rows.append({"test": tid, "kind": kind, "status": status, **{k: v for k, v in out.items() if k != "outcome"}})
    named = [n for n in kinds if not any(t == n or t.startswith(n + ".") for t in outcomes)]
    if named:
        ok = False
    return {"item": item, "part": spec["part"], "rule": UNIT_RULE, "tests": rows, "negatives_caught": caught,
            "requires_geant4": open_g4, "not_run": named, "passed": bool(ok and outcomes)}


def units_block(item: str) -> dict:
    """The item's tests run with its `env` set for the run (a value already in the environment wins: a gate run may
    name another products root), restored after; the products root and its tell.json SHA-256 recorded."""
    env = {k: os.environ.get(k) or v for k, v in UNIT_ITEMS[item].get("env", {}).items()}
    saved = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        rec = {"outcomes": run_tests(list(UNIT_ITEMS[item]["tests"]))}
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    if env:
        tells = {k: Path(v) / "tell.json" for k, v in env.items()}
        rec["env"] = env
        rec["tell_sha256"] = {k: hashlib.sha256(t.read_bytes()).hexdigest() if t.is_file() else None
                              for k, t in tells.items()}
    return rec


# ================================================================== zdc_fit: the ZDC response-layer parameters
CALO_THETA = ("light_yield", "resolution")
CALO_OBS = ("pe_mean", "pe_std")
CALO_TRUTH = {"light_yield": 205.0, "resolution": 0.6}
CALO_MC, CALO_EXPOSURE, CALO_TRUTH_MC = 2500, 500, 10_000      # V_MC / V_data ~ 0.2; the truth sample 20 x the data
CALO_REPS = 40                                           # part D (A19): 40 fresh repetitions, 4 per task
CALO_PER_TASK, CALO_R0 = 4, 1000                         # repetitions per task; seed offset (part C used r = 0-9)
CALO_RULE = ("each repetition: P3 passes at the prior centre, the fit converges, G1 passes with sigma_noise from 5 "
            "independent batches (section 8.1), |theta-hat_i - truth_i| <= 4 sigma_tot,i; the item passes when every "
            "repetition does and, for each theta_i, the pull chi2 over the repetitions (sum of pull_i^2) is at most the "
            "0.99 quantile of chi2 with that many degrees of freedom (tightened by A19, review F1)")
CALO_G4_RULE = ("CALO_RULE on the p3-g4 Geant4 products by re-digitization (A19, review F1): theta = light yield (the "
                "resolution scale is not identifiable there: P3 fails for both, recorded), 40 repetitions")


def calo_fit_block(r0: int, reps: int, n_mc: int = CALO_MC, exposure: int = CALO_EXPOSURE,
                  n_truth: int = CALO_TRUTH_MC) -> list:
    """Repetition r: the fixture's nominal batch (n_mc events), a truth batch (n_truth events, the G8 truth of D6),
    five sigma-noise batches; theta = (light yield, RESOLUTIONSCALE) by re-digitization (the evaluator's coupled
    default); pseudo-data of `exposure` events resampled from the truth batch; the fit from the prior centre."""
    import calibration_zdc_fixture as Z
    import g4sim_calib_eval  # noqa: F401  (registers the g4sim evaluator)

    from core.calibration import evaluator
    from core.calibration import evaluator_problem as EP
    rows = []
    for r in range(r0, r0 + reps):
        s = cal_seed(40, r) % 2 ** 31
        bs = {"nominal": Z.batch(s, 0, n_mc, use="fit"), "truth": Z.batch(s + 1, 0, n_truth, use="G8-truth")}
        bs.update({f"s{k}": Z.batch(s + 2 + k, 0, n_mc, use="sigma-noise", set=k) for k in range(5)})
        c = Z.contract(thetas=CALO_THETA, observables=CALO_OBS, exposure=exposure)
        ev = evaluator.make(Z.plan(bs, nominal="nominal", observables=CALO_OBS), c)
        pr = EP.EvaluatorProblem(ev, c, seeds={"batch": "nominal"})
        events = Z.truth_events(ev, CALO_TRUTH, "truth")
        q = pr.with_data(pr.pseudo_data(events, {"kind": "fixed", "events": exposure}, _rng(cal_seed(40, r), 1)))
        tv = np.array([CALO_TRUTH[t] for t in CALO_THETA])
        q.sigma_noise = EP.estimate_sigma_noise(q, tv, [f"s{k}" for k in range(5)])
        centre = np.array([0.5 * sum(Z.PRIORS[t]) for t in CALO_THETA])
        lk = L.Likelihood(q.layout, q.observed, q.reference(centre, None))
        b0 = lk.initial_beta(dict(zip(CALO_THETA, centre)))
        p3 = identify.p3(q, b0)["status"]
        f = F.iterate(q, b0)
        row = {"r": r, "p3": p3, "converged": bool(f.converged), "coupling": ev.coupling,
               "sigma_noise": float(q.sigma_noise)}
        if f.converged:
            row.update(g1=F.g1(f, q)["status"], pull=((f.beta[:2] - tv) / f.sigma_tot[:2]).tolist(),
                       sigma_tot=f.sigma_tot[:2].tolist())
        rows.append(row)
    return rows


def calo_fit_judge(rows: list, reps: int = CALO_REPS, item: str = "zdc_fit", rule: str = CALO_RULE,
                   label: str = f"{LABEL}; ZDC transport stand-in") -> dict:
    from scipy import stats
    ok_rows = [x for x in rows if x["p3"] == "passed" and x["converged"] and x.get("g1") == "passed"
               and max(abs(v) for v in x["pull"]) <= 4.0]
    pulls = np.array([x["pull"] for x in rows if x.get("pull")], float)
    chi2 = (pulls ** 2).sum(0).tolist() if pulls.size else []
    limit = float(stats.chi2.ppf(0.99, len(pulls))) if pulls.size else None
    chi2_ok = bool(pulls.size) and all(c <= limit for c in chi2)
    return {"item": item, "part": "the response-layer parameters of ZDC Phase 3", "rule": rule,
            "reps": len(rows), "passing": len(ok_rows), "pull_chi2": chi2, "pull_chi2_limit": limit,
            "pull_rms": np.sqrt((pulls ** 2).mean(0)).tolist() if pulls.size else [],
            "rows": rows, "label": label,
            "passed": bool(len(rows) == reps and len(ok_rows) == reps and chi2_ok)}


CALO_G4_THETA = ("light_yield",)
CALO_G4_BLOCK, CALO_G4_BLOCKS = 2500, 8                  # the fit MC size of the stand-in; 8 blocks of the 20,000 nominal


def sub_batch(b: dict, first: int, n: int) -> dict:
    """Events first..first+n-1 of a told g4sim batch (its cells and primaries), as a batch of its own."""
    lo, hi = first, first + n
    out = {k: v for k, v in b.items() if k not in ("cells", "primaries")}
    out.update(first_event=lo, events=n, cells=[r for r in b["cells"] if lo <= int(r[0]) < hi],
               primaries=[p for p in b.get("primaries", []) if lo <= int(p[0]) < hi])
    return out


def calo_fit_g4_block(r0: int, reps: int, exposure: int = CALO_EXPOSURE, root: Path | None = None,
                      thetas=CALO_G4_THETA) -> list:
    """The response-layer item on the p3-g4 Geant4 products by re-digitization (review F1; A19): repetition r fits with
    nominal block r mod 8 (2500 events) as the MC, the next five blocks as the sigma-noise sets, and pseudo-data of
    `exposure` events resampled from the independent `reference` run (20,000 Geant4 events) digitized at the truth;
    theta = `thetas` (the light yield: RESOLUTIONSCALE is not identifiable on these products, whose pe_std is shower-
    dominated; P3 fails for both, recorded); the fit from the prior centre. Blocks are shared across repetitions."""
    import calibration_zdc_fixture as Z
    import g4sim_calib_eval  # noqa: F401  (registers the g4sim evaluator)

    from core.calibration import evaluator
    from core.calibration import evaluator_problem as EP
    root = Path(root or os.environ.get(P3.PRODUCTS_ENV) or P3.OUT_ROOT)
    nom = P3.told_batch(root, P3.CALO, "nominal")
    ref = P3.told_batch(root, P3.CALO, "reference")
    for b in (nom, ref):
        b.pop("point", None)
    rows = []
    for r in range(r0, r0 + reps):
        ks = [(r + j) % CALO_G4_BLOCKS for j in range(6)]
        bs = {"nominal": {**sub_batch(nom, ks[0] * CALO_G4_BLOCK, CALO_G4_BLOCK), "use": "fit", "set": "s"},
              "truth": {**ref, "use": "G8-truth"}}
        bs.update({f"s{j}": {**sub_batch(nom, k * CALO_G4_BLOCK, CALO_G4_BLOCK), "use": "sigma-noise", "set": j}
                   for j, k in enumerate(ks[1:])})
        c = Z.contract(thetas=tuple(thetas), observables=CALO_OBS, exposure=exposure)
        p = P3.calo_plan(bs, observables=CALO_OBS)
        p["evaluator"]["nominal"] = "nominal"
        ev = evaluator.make(p, c)
        pr = EP.EvaluatorProblem(ev, c, seeds={"batch": "nominal"})
        events = Z.truth_events(ev, CALO_TRUTH, "truth")
        q = pr.with_data(pr.pseudo_data(events, {"kind": "fixed", "events": exposure}, _rng(cal_seed(42, r), 1)))
        tv = np.array([CALO_TRUTH[t] for t in thetas])
        q.sigma_noise = EP.estimate_sigma_noise(q, tv, [f"s{j}" for j in range(5)])
        centre = np.array([0.5 * sum(Z.PRIORS[t]) for t in thetas])
        lk = L.Likelihood(q.layout, q.observed, q.reference(centre, None))
        b0 = lk.initial_beta(dict(zip(thetas, centre)))
        p3 = identify.p3(q, b0)["status"]
        f = F.iterate(q, b0)
        row = {"r": r, "thetas": list(thetas), "blocks": ks, "p3": p3, "converged": bool(f.converged), "coupling": ev.coupling,
               "sigma_noise": float(q.sigma_noise)}
        if f.converged:
            d = len(thetas)
            row.update(g1=F.g1(f, q)["status"], pull=((f.beta[:d] - tv) / f.sigma_tot[:d]).tolist(),
                       sigma_tot=f.sigma_tot[:d].tolist())
        else:
            row["reason"] = f.reason
        rows.append(row)
    return rows


# ================================================================== phi_resim: a resimulation-level phi (section 5.5)
PHI_RUNS = ("light", "spe", "beam4")
PHI_NAMES = ["beam4_e_mean", "light_e_mean", "light_e_width", "spe_e_mean", "spe_e_width"]
PHI_THETA = {"pde": {"bounds": (0.2125, 0.2875), "prior": (0.2425, 0.2575)},
             "gain": {"bounds": (8.5, 11.5), "prior": (9.7, 10.3)}}
PHI_CASES = {"small": 0.002, "large": 0.1}              # the constraint sigma of the thickness phi
PHI_BOX = 4.0                                            # the surrogate's box: +- 4 sigma_phi
PHI_RULE = ("each case (sigma_phi 0.002 and 0.1) follows section 5.5: shift mode when P8 passes and G9 passes at "
            "theta-hat (the refits by resimulation with common random numbers), otherwise the surrogate model over "
            "phi +- 4 sigma (regression mode) with phi profiled; the case passes when the mode it reaches passes its "
            "gates (shift: P8, G9; surrogate: P6, and the profile fit converges and passes G1 with sigma_noise from "
            "K = 5 MC sets), the route and the reason recorded; the item passes when both cases do")


def _phi_build(n):
    return toy.build_toy(n, "full", runs_subset=PHI_RUNS)


PHI_EXPOSURE, PHI_MC, PHI_SEED_ROUND = 4000, 40_000, 1   # part E (A20): identified fits (pilot 7647759: sigma_tot /
#   sigma_prior 0.47-0.50 at 4000, 0.67-0.71 at 2000, 1.2-1.4 at part C/D's 500); fresh seeds (round 1; the pilot used 0)


def phi_resim_block(case: str, exposure: int = PHI_EXPOSURE, mc: int = PHI_MC, n_design: int = 12, held_back: int = 8,
                    seed_round: int = PHI_SEED_ROUND) -> dict:
    """The material thickness phi resimulated with common random numbers (not the light-yield equivalence)."""
    sig = PHI_CASES[case]
    truth = np.array([0.25, 10.0])
    base = cal_seed(41, list(PHI_CASES).index(case) + 100 * seed_round)
    sp = _Problem(_phi_build, PHI_NAMES, PHI_THETA, exposure, mc, mc_seed=(base, 1), boot_seed=(base, 2),
                       shift={"material_thickness": (1.0, sig)})
    b = np.r_[truth, np.zeros(sp.layout.n_beta - 2)]
    sp.observed = sp.simulate(b, _rng(base, 3), nominal=False)
    p8 = Sh.p8(sp, sp.initial_beta())
    out = {"case": case, "sigma_phi": sig, "p8": {k: p8.get(k) for k in ("status", "lambda_max", "c", "finding")}}
    if p8["status"] == "passed":
        f = F.iterate(sp, sp.initial_beta())
        g9 = Sh.g9(sp, f, p8, seed=(base, 4)) if f.converged else {"status": "not-run", "finding": f.reason}
        out.update(shift_converged=bool(f.converged),
                   g9={k: g9.get(k) for k in ("status", "finding", "findings", "Delta")})
        if g9.get("status") == "passed":
            out.update(route="shift", ok=True)
            return out
        out["reason"] = f"G9 {g9.get('status')}: section 5.5 does not hold, the surrogate model"
    else:
        out["reason"] = f"P8 {p8['status']}: section 5.5 is not shown to hold, the surrogate model"
    lo, hi = 1.0 - PHI_BOX * sig, 1.0 + PHI_BOX * sig
    plan = {"methods": {"material_thickness": "surrogate-model"},
            "design": {"surrogate": {"n_design": n_design, "held_back": held_back, "seed": base % 2 ** 31,
                                     "mode": "regression"}}}         # CRN staircases of a resimulated phi: smoothed
    contract = {"parameters": [{"name": "material_thickness", "role": "phi", "sampling_bounds": [lo, hi]}],
                "observables": [{"name": n} for n in PHI_NAMES], "exposure": {r: exposure for r in PHI_RUNS}}
    pp = _Problem(_phi_build, PHI_NAMES, PHI_THETA, exposure, mc, mc_seed=(base, 1), boot_seed=(base, 2),
                       phi_P={"material_thickness": (1.0, sig)}, plan=plan)
    p6 = EM.p6_from_evaluator(pp.ev, contract, plan, parameters=["material_thickness"], names=PHI_NAMES)
    tr = EM.training_set(pp.ev, contract, plan, parameters=["material_thickness"], names=PHI_NAMES)
    pp.ev.attach_surrogate(tr["surrogate"])
    pp._cache.clear()
    pp.observed = sp.observed
    phi_obs = L.Observations(y_gauss=sp.observed.y_gauss, phi0=np.array([1.0]), phi_cov=pp.phi_cov())
    pp.observed = phi_obs
    try:
        pp.sigma_noise = TP.estimate_sigma_noise(pp, pp.initial_beta(), seed=(base, 5))     # section 8.1, K = 5
        f = F.iterate(pp, pp.initial_beta())
        conv, g1 = bool(f.converged), (F.g1(f, pp)["status"] if f.converged else f.reason)
    except EM.OutsideDomain as exc:
        conv, g1 = False, f"outside the surrogate domain: {exc}"
    out.update(p6={k: p6.get(k) for k in ("status", "findings")}, converged=conv, g1=g1,
               sigma_noise=float(pp.sigma_noise))
    out.update(route="surrogate", ok=bool(p6.get("status") == "passed" and conv and g1 == "passed"))
    return out


def phi_resim_judge(cases: list) -> dict:
    by = {c["case"]: c for c in cases}
    return {"item": "phi_resim", "part": "phi at the resimulation level (section 5.5, otherwise the surrogate model)",
            "rule": PHI_RULE, "cases": cases, "label": LABEL,
            "passed": bool(set(by) == set(PHI_CASES) and all(c["ok"] for c in cases))}


# ================================================================== g8_3m: G8 for the three-method combination
M3_RUNS = ("spe", "beam1", "beam3")
M3_NAMES = ["spe_e_mean", "spe_e_width", "spe_efficiency", "beam1_ratio_mean", "beam3_ratio_mean", "beam1_e_mean",
            "beam3_e_mean"]
M3_THETA = {"gain": {"bounds": (8.5, 11.5), "prior": (9.7, 10.3)},
            "relative_gain_b": {"bounds": (0.85, 1.15), "prior": (0.97, 1.03)},
            "threshold": {"bounds": (2.5, 7.5), "prior": (4.5, 5.5)}}
M3_METHODS = {"gain": "analytic-reweighting", "relative_gain_b": "rerun", "threshold": "surrogate-model"}
M3_BOX = {"threshold": (4.0, 6.0)}          # the surrogate's design box (domain)
M3_TRUTH = np.array([10.0, 1.0, 5.0])
M3_WHICH = 1                                 # the boundary point: relative_gain_b 0.5 sigma inside 0.85
M3 = {"exposure": 2000, "mc": 20_000, "truth_batches": 20, "truth_batch_factor": 5, "n_design": 12,
      "per_point": 540, "chunk": 10}
M3_RULE = ("G8 at the full level (section 8.4; d = 3, N_c = 518 per point, Holm over 5d = 15 tests, alpha_G8 = 0.05, "
           "the bias rule and the summed ratio test) on surrogate pseudo-data (A12, section 19-5): passes when "
           "closure.g8 passes and the full-simulation spot check passes, the spot check decided by P6's rule on its "
           "P6-form statistics (A16 (i)); a spot check not complete makes the item incomplete")


def _m3_build(n):
    return toy.build_toy(n, "full", runs_subset=M3_RUNS)


def _m3_contract():
    return {"parameters": [{"name": n, "role": "theta", "sampling_bounds": list(M3_BOX.get(n, v["prior"]))}
                           for n, v in M3_THETA.items()]}


def _m3_plan(n_design, seed):
    return {"methods": dict(M3_METHODS),
            "design": {"surrogate": {"n_design": int(n_design), "held_back": 0, "seed": int(seed) % 2 ** 31,
                                     "mode": "interpolate"}}}


def m3_problem(mc_seed, boot_seed, mc: int, sizes: dict, train_seed: int):
    """The fit problem of one pseudo-data set: its own nominal MC, bootstrap and surrogate (rebuilt on its own
    design-point MC, section 8.4 "same size"); the gain reweighted and relative_gain_b rerun inside each design point
    (section 6.5, outside to inside)."""
    plan = _m3_plan(sizes["n_design"], train_seed)
    p = _Problem(_m3_build, M3_NAMES, M3_THETA, exposure=sizes["exposure"], mc_events=mc, mc_seed=mc_seed,
                      boot_seed=boot_seed, plan=plan)
    tr = EM.training_set(p.ev, _m3_contract(), plan, names=M3_NAMES)
    if tr["status"] != "ok":
        raise RuntimeError(f"surrogate training incomplete: {tr.get('reason')}")
    p.ev.attach_surrogate(tr["surrogate"])
    p._cache.clear()
    return p, tr


_M3_CACHE: dict = {}


def m3_design(sizes: dict) -> dict:
    """sigma_tot^design (an Asimov fit of the nominal problem at the truth), the injection points, and the pseudo-data
    centres and data covariances there (link space). The truth (section 8.4: >= 100 x the nominal MC) is the mean of
    `truth_batches` truth surrogates, each trained on its own MC of `truth_batch_factor` x the nominal size (so the
    centre's MC noise is V_MC / (batches x factor), and the memory that of one batch). Deterministic: every task
    recomputes the same values (the merge checks sigma_design)."""
    key = json.dumps(sizes, sort_keys=True)
    if key in _M3_CACHE:
        return _M3_CACHE[key]
    p0, _ = m3_problem((cal_seed(30, 0), 1), (cal_seed(30, 0), 2), sizes["mc"], sizes, cal_seed(30, 0))
    b = np.r_[M3_TRUTH, np.zeros(p0.layout.n_beta - 3)]
    p0.observed = p0.asimov(b)
    sd = F.iterate(p0, p0.initial_beta()).sigma_tot[:3]
    interior, boundary = C.injection_points([v["prior"] for v in M3_THETA.values()],
                                            [v["bounds"] for v in M3_THETA.values()], sd, M3_TRUTH, which=M3_WHICH)
    inj = {"interior": dict(zip(M3_THETA, map(float, interior))), "boundary": dict(zip(M3_THETA, map(float, boundary)))}
    preds: dict = {n: [] for n in inj}
    states = []
    for t in range(int(sizes["truth_batches"])):
        pt, trt = m3_problem((cal_seed(30, 10 + t), 1), (cal_seed(30, 1), 2), sizes["truth_batch_factor"] * sizes["mc"],
                             sizes, cal_seed(30, 10 + t))
        st = trt["state"]                     # kept for the spot check's seed check, without the raw results
        states.append({**{k: v for k, v in st.items() if k != "entries"},
                       "entries": [{k: e[k] for k in ("run_id", "point", "theta", "seeds", "status")}
                                   for e in st["entries"]]})
        for n, x in inj.items():
            r = pt.ev.evaluate(x, names=M3_NAMES)
            preds[n].append({k: np.asarray(r[k], float) for k in ("pred", "V_MC", "V_emu")})
        if t == 0:
            vdata = {n: pt.bootstrap_vhat(x, (cal_seed(30, 2), n == "boundary")) for n, x in inj.items()}
            names = trt["surrogate"].names
        del pt, trt, st
    pts = {}
    for n, x in (("interior", interior), ("boundary", boundary)):
        K = len(preds[n])
        mean = {k: sum(r[k] for r in preds[n]) / K for k in ("pred", "V_MC", "V_emu")}
        mean["V_MC"], mean["V_emu"] = mean["V_MC"] / K, mean["V_emu"] / K      # the variance of a mean of K
        pts[n] = {"theta": x, "centre": p0._to_link(mean["pred"]), "V_data": vdata[n], "truth": mean}
    d = {"sigma_design": sd, "points": pts, "truth_states": states, "names": names}
    _M3_CACHE[key] = d
    return d


def g8_3m_block(point: str, start: int, n: int, sizes: dict | None = None) -> dict:
    """Pseudo-data start..start+n-1 of `point`: y ~ N(link mu-hat_truth(theta_inj), V_data) (A12), each fitted with its
    own MC, bootstrap and surrogate; Gaussian intervals theta-hat_i +- z sigma_tot,i (the plan's interval procedure)."""
    sz = {**M3, **(sizes or {})}
    d = m3_design(sz)
    k = ("interior", "boundary").index(point)
    pt = d["points"][point]
    Y = EM.surrogate_pseudo_data(pt["centre"], pt["V_data"], sz["per_point"], seed=(cal_seed(31, k), 0))
    rows = []
    for s in range(start, start + n):
        t0 = time.time()
        row = {"s": s}
        try:
            p, _ = m3_problem((cal_seed(32, k), s, 1), (cal_seed(32, k), s, 2), sz["mc"], sz, cal_seed(33, 1000 * k + s))
            p.observed = L.Observations(y_gauss=np.asarray(Y[s], float))
            f = F.iterate(p, p.initial_beta())
            row["converged"] = bool(f.converged)
            if f.converged:
                row.update(error=(f.beta[:3] - pt["theta"]).tolist(), sigma_tot=f.sigma_tot[:3].tolist())
            else:
                row["reason"] = f.reason
        except (EM.OutsideDomain, F.FitError, np.linalg.LinAlgError) as exc:
            row.update(converged=False, reason=f"{type(exc).__name__}: {exc}")
        row["seconds"] = time.time() - t0
        rows.append(row)
    return {"point": point, "rows": rows, "sigma_design": d["sigma_design"], "theta": pt["theta"]}


def g8_3m_spot(sizes: dict | None = None) -> dict:
    """The full-simulation spot check (A12): the threshold resimulated at each injection point with a truth-batch-size
    MC and its own seed, independent of every truth surrogate's training seed (emulator.spot_check_plan checks each
    training state), compared with the pseudo-data centre (the mean truth surrogate combined with the inner methods);
    decided by P6's rule on the P6-form statistics (A16 (i))."""
    sz = {**M3, **(sizes or {})}
    d = m3_design(sz)
    inj = [dict(zip(M3_THETA, map(float, d["points"][n]["theta"]))) for n in ("interior", "boundary")]
    seeds = [{"nominal": cal_seed(34, 0)}, {"nominal": cal_seed(34, 1)}]
    for st in d["truth_states"]:
        plan = EM.spot_check_plan(inj, st, seeds, names=M3_NAMES)
    full = _Problem(_m3_build, M3_NAMES, M3_THETA, exposure=sz["exposure"],
                         mc_events=sz["truth_batch_factor"] * sz["mc"], mc_seed=(cal_seed(34, 2), 1),
                         boot_seed=(cal_seed(34, 2), 2), plan={"methods": dict(M3_METHODS)})
    EM.drive(full.ev, plan)
    by = {json.dumps(sorted(x.items())): d["points"][n]["truth"] for x, n in zip(inj, ("interior", "boundary"))}

    def predict(x):
        return by[json.dumps(sorted({k: float(v) for k, v in x.items() if k in M3_THETA}.items()))]
    contract = {"observables": [{"name": n} for n in M3_NAMES], "exposure": {r: sz["exposure"] for r in M3_RUNS}}
    holder = type("S", (), {"names": d["names"]})()
    rec = EM.spot_check_record(plan, holder, contract, predict=predict)   # V_data per point from its full result
    return {"spot_check": rec}


def _take(rows: list, n: int):
    """The first n converged pseudo-data in seed order (non-converged ones replaced, section 7.3) and the X incurred
    up to the n-th; None when the rows run out."""
    rows = sorted(rows, key=lambda x: x["s"])
    got, X = [], 0
    for x in rows:
        if len(got) == n:
            break
        if not x["converged"]:
            X += 1
            continue
        got.append(x)
    return (got, X) if len(got) == n else (None, X)


def _ensemble(got: list, X: int, scale: dict | None = None) -> dict:
    sc = {0.68: 1.0, 0.95: 1.0, **(scale or {})}
    e = np.array([x["error"] for x in got], float)
    s = np.array([x["sigma_tot"] for x in got], float)
    return {"errors": e, "cover68": np.abs(e) <= sc[0.68] * s, "cover95": np.abs(e) <= 1.96 * sc[0.95] * s,
            "nontruth_basin": np.zeros(len(got), bool), "X": X, "interval_toys": {"X": 0, "n": 0}}


def g8_3m_judge(blocks: list, spot: dict | None, d: int = 3) -> dict:
    names = list(M3_THETA)
    sds = {json.dumps(np.round(np.asarray(b["sigma_design"], float), 12).tolist()) for b in blocks}
    sd = np.asarray(blocks[0]["sigma_design"], float)
    out = {"item": "g8_3m", "part": "G8 passes for the three-method combination", "rule": M3_RULE,
           "methods": M3_METHODS, "sigma_design": sd, "label": f"{LABEL}; provisional-thresholds",
           "design_consistent": len(sds) == 1}
    res = {}
    for level in ("standard", "full"):
        N = C.n_c(d, level)["N_c"]
        pts = {}
        for name in ("interior", "boundary"):
            got, X = _take([x for b in blocks if b["point"] == name for x in b["rows"]], N)
            pts[name] = None if got is None else _ensemble(got, X)
        if None in pts.values():
            res[level] = {"status": "incomplete", "N_c": N}
            continue
        g = C.g8(level, names, sd, pts["interior"], pts["boundary"])
        res[level] = {"N_c": N, **{k: g.get(k) for k in ("status", "finding", "fails", "b_bar", "family", "X")},
                      "coverage68": {n: pts[n]["cover68"].mean(0).tolist() for n in pts},
                      "coverage95": {n: pts[n]["cover95"].mean(0).tolist() for n in pts},
                      "bias_over_sigma": (pts["interior"]["errors"].mean(0) / sd).tolist()}
    out["g8"] = res
    out["spot_check"] = (spot or {}).get("spot_check") or {"status": "missing"}
    sp = out["spot_check_status"] = out["spot_check"].get("status", "missing")
    g = res["full"]["status"]
    if not out["design_consistent"] or g == "failed" or sp == "failed":
        out["status"] = "failed"
    elif g == "passed" and sp == "passed":
        out["status"] = "passed"
    else:
        out["status"] = "incomplete"
    out["passed"] = out["status"] == "passed"
    return out


# ================================================================== toy_g8: the toy-detector G8 rows from phase 2
TOY_EXPOSURE = 8000
# the track configuration of phase 2's research run (its observables, truth and prior box) with the toy design's
# momentum-scale physical bound declared at 0.999 (lower), so the boundary point (0.5 sigma inside it) lies ~10 sigma
# from the fits' start at the prior centre (with the bound at 0.95 the fits from the centre failed: pilot 2026-11-12)
TOY_THETA = {"momentum_scale": {"bounds": (0.999, 1.05), "prior": (0.98, 1.02)},
             "sum_term_a": {"bounds": (0.2, 3.0), "prior": (0.8, 1.2)}}
TOY_CONFIGS = {
    # name: calibration, row, MC / exposure, truth, V_MC factor in the fit, G8 replicates, judged
    "cal1": {"cal": 1, "row": 2000, "mcr": 20, "truth": "analytic", "fit_scale": 1.0, "reps": 1000, "judged": True,
             "power": True, "inject": True},
    # calibration 12 folded into calibration 6 (the user's reduction of 2026-11-12, registered before any run): one
    # configuration at MC 10x with the shared truth MC, judged for rows 2006 and 2015
    "cal6": {"cal": 6, "row": 2006, "rows": [2006, 2015], "mcr": 10, "truth": "shared-mc", "fit_scale": 1.0,
             "reps": 1000, "judged": True,
             "power": True, "inject": False},
    "cal12_vmc2_r10": {"cal": 12, "row": 2015, "mcr": 10, "truth": "analytic", "fit_scale": 0.5, "reps": 200,
                       "judged": False, "power": False, "inject": False},
    "cal12_vmc2_r33": {"cal": 12, "row": 2015, "mcr": 33, "truth": "analytic", "fit_scale": 0.5, "reps": 200,
                       "judged": False, "power": False, "inject": False},
    # the second registration of rows 2006 and 2015 (2026-11-13, approval A15; the first, cal6, failed and stands as
    # recorded): the shared truth MC at 100 x the fit MC (1000 x the exposure at MC 10x), fresh replicates (offset
    # 10^6), one task per replicate and point so the truth is generated once; its tasks follow every earlier task
    "cal6b": {"cal": 6, "row": 2006, "rows": [2006, 2015], "mcr": 10, "truth": "shared-mc", "truth_factor": 1000,
              "chunk": 500, "r_offset": 1_000_000, "second": True, "fit_scale": 1.0, "reps": 1000, "judged": True,
              "power": True, "inject": False},
}
TOY_PER_POINT, TOY_CHUNK = 500, 100           # N_full(d = 2) = 483 plus 17 spare for replacement and injection
TOY_TRUTH_FACTOR = 100                        # the shared truth MC of calibration 12: 100 x the exposure (section 8.4)
INJECT = [(m, e) for m in ("independent", "covered", "not-covered") for e in (0.005, 0.01)]
BIAS_LIMIT = 0.02                             # the card: the toy's finite-sample sum-term-a bias below 0.02 sigma
TOY_RULE = ("each judged configuration: false alarms <= 62 of 1000 G8 replicates at the standard and at the full "
            "level (closure.g8; d = 2, N_c = 93 standard and 483 full per point); calibration 1 and 6 power: with the interval "
            "scaled to the coverage p1 (standard 68% 0.50, full 68% 0.58, full 95% 0.90) detections >= 775 of 1000; "
            "calibration 10 (from calibration 1's fits, six injection modes): false alarms <= 62 of 1000 at both "
            "levels; the V_MC-underestimated configurations reported (no threshold, note 4). Validity condition "
            "(card, carried from phase 2): the interior mean error of sum_term_a over all replicates, in sigma_design, "
            "is within 0.02 in absolute value (else the configuration is reported `exposure-condition-not-met`, not "
            "evidence)")


def _toy_problem(cfg, mc_seed, boot_seed, exposure):
    p = _Problem(G.track_build, G.TRACK_CAL, TOY_THETA, exposure=exposure, mc_events=cfg["mcr"] * exposure,
                   mc_seed=mc_seed, boot_seed=boot_seed)
    p.fit_scale = float(cfg["fit_scale"])
    return p


_TOY_SD: dict = {}


def toy_design(name: str, exposure: int = TOY_EXPOSURE) -> tuple:
    """sigma_tot^design (an Asimov fit with the configuration's MC size, a fixed seed) and the injection points."""
    key = (name, exposure)
    if key not in _TOY_SD:
        cfg = TOY_CONFIGS[name]
        p0 = _toy_problem({**cfg, "fit_scale": 1.0}, (cal_seed(50, 0), 1), (cal_seed(50, 0), 2), exposure)
        p0.observed = p0.asimov(np.r_[G.TRACK_TRUTH, np.zeros(p0.layout.n_beta - 2)])
        sd = F.iterate(p0, p0.initial_beta()).sigma_tot[:2]
        th = list(TOY_THETA.values())
        _TOY_SD[key] = (sd, C.injection_points([v["prior"] for v in th], [v["bounds"] for v in th], sd, G.TRACK_TRUTH))
    return _TOY_SD[key]


TOY_TRUTH_BATCHES = 20                        # the shared truth MC generated in batches (memory of one batch)


def toy_chunk(cfg: dict) -> int:
    return int(cfg.get("chunk", TOY_CHUNK))


def toy_truth_factor(cfg: dict) -> int:
    return int(cfg.get("truth_factor", TOY_TRUTH_FACTOR))


def toy_truth_batches(cfg: dict) -> int:
    """The batch count of the shared truth MC: TOY_TRUTH_BATCHES at 100 x the exposure, and the same batch size for a
    larger truth (so the memory stays that of one batch)."""
    return TOY_TRUTH_BATCHES * toy_truth_factor(cfg) // TOY_TRUTH_FACTOR


def _truth_pseudo_data(p, params: dict, n_total: int, exposure: int, seed, draws: dict,
                       n_batches: int = TOY_TRUTH_BATCHES) -> dict:
    """Pseudo-data resampled with replacement from one shared truth MC of n_total events per run at `params`
    (section 8.4), generated in TOY_TRUTH_BATCHES batches with seeds (seed, batch): draws {s: {run: event indices in
    [0, n_total)}}; returns {s: Observations}."""
    nb = int(n_batches)
    per = n_total // nb
    m = G.track_build(per)
    ev = toy.ChainEvaluator(m, {"seeds": {"nominal": 1}})
    picked: dict = {s: {} for s in draws}
    for b in range(nb):
        gen = ev.generate(TP._seed_int((*seed, b)), params={**m.nominal, **params})
        for s, by_run in draws.items():
            for rid, idx in by_run.items():
                sel = idx[(idx >= b * per) & (idx < (b + 1) * per)] - b * per
                evs = gen["runs"][rid]["events"]
                picked[s].setdefault(rid, []).append({nd: {k: np.asarray(v)[sel] for k, v in outs.items()}
                                                      for nd, outs in evs.items()})
        del gen
    out = {}
    for s, runs in picked.items():
        ev_s = {rid: {nd: {k: np.concatenate([part[nd][k] for part in parts]) for k in parts[0][nd]}
                      for nd in parts[0]} for rid, parts in runs.items()}
        o = toy.observe(m, ev_s, {r: np.ones(exposure) for r in ev_s}, p.names)
        out[s] = L.Observations(y_gauss=p._to_link(o["pred"]))
    return out


def toy_g8_block(config: str, r: int, point: str, start: int, n: int, exposure: int = TOY_EXPOSURE) -> dict:
    """Pseudo-data start..start+n-1 of replicate r at `point`: fresh events at the point (analytic truth) or resampled
    from the replicate's shared truth MC (100 x the exposure per run); each fitted with its own nominal MC and
    bootstrap."""
    cfg = TOY_CONFIGS[config]
    j = list(TOY_CONFIGS).index(config)
    k = ("interior", "boundary").index(point)
    sd, pts = toy_design(config, exposure)
    truth = np.asarray(pts[k], float)
    base = (cal_seed(cfg["cal"], r + int(cfg.get("r_offset", 0))), j, k)
    shared = None
    if cfg["truth"] == "shared-mc":
        p0 = _toy_problem(cfg, (*base, start, 1), (*base, start, 2), exposure)
        runs = sorted({o.run for o in p0.model.observables if o.name in p0.names})
        n_total = toy_truth_factor(cfg) * exposure
        draws = {s: {rid: _rng(*base, s, 3, jr).integers(n_total, size=exposure) for jr, rid in enumerate(runs)}
                 for s in range(start, start + n)}
        shared = _truth_pseudo_data(p0, dict(zip(TOY_THETA, map(float, truth))), n_total, exposure, (*base, 999),
                                    draws, toy_truth_batches(cfg))
    rows = []
    for s in range(start, start + n):
        p = _toy_problem(cfg, (*base, s, 1), (*base, s, 2), exposure)
        b = np.r_[truth, np.zeros(p.layout.n_beta - 2)]
        p.observed = p.simulate(b, _rng(*base, s, 3), nominal=False) if shared is None else shared.pop(s)
        f = F.iterate(p, p.initial_beta())
        row = {"s": s, "converged": bool(f.converged)}
        if f.converged:
            row.update(error=(f.beta[:2] - truth).tolist(), sigma_tot=f.sigma_tot[:2].tolist())
        rows.append(row)
    return {"config": config, "r": r, "point": point, "rows": rows, "sigma_design": sd}


def _inject_take(rows, n, mode, eps, rng):
    """calibration 10 on calibration 1's fits: walking the fits in seed order, each converged fit is declared
    non-converged with probability eps (independent), eps / p68 if covered at 68% for theta_0, eps / (1 - p68) if
    not (the phase-2 modes), and replaced by the next."""
    from scipy import stats
    p68 = 2 * stats.norm.cdf(1) - 1
    got, X, inj = [], 0, 0
    for x in sorted(rows, key=lambda y: y["s"]):
        if len(got) == n:
            break
        if not x["converged"]:
            X += 1
            continue
        cov = abs(x["error"][0]) <= x["sigma_tot"][0]
        pd = {"independent": eps, "covered": eps / p68 if cov else 0.0,
              "not-covered": eps / (1 - p68) if not cov else 0.0}[mode]
        if rng.random() < pd:
            X += 1
            inj += 1
            continue
        got.append(x)
    return (got if len(got) == n else None), X, inj


def toy_g8_replicate(name: str, r: int, blocks: list, sd: np.ndarray) -> dict:
    """The decisions of one replicate: G8 at both levels; the power cases; calibration 10's injection modes."""
    cfg = TOY_CONFIGS[name]
    names = list(TOY_THETA)
    out = {"r": r}
    rows = {pt: [x for b in blocks if b["point"] == pt for x in b["rows"]] for pt in ("interior", "boundary")}
    for level in ("standard", "full"):
        N = C.n_c(2, level)["N_c"]
        took = {pt: _take(rows[pt], N) for pt in rows}
        if any(t[0] is None for t in took.values()):
            out[level] = "short"
            continue
        ens = {pt: _ensemble(*took[pt]) for pt in took}
        out[level] = C.g8(level, names, sd, ens["interior"], ens["boundary"])["status"]
        if level == "full":
            out["bias_over_sigma"] = (ens["interior"]["errors"].mean(0) / sd).tolist()
        if cfg["power"]:
            for key, (lv, c) in CC.POWER.items():
                if lv != level:
                    continue
                sc = {pt: _ensemble(*took[pt], scale={c: CC._scale_for(C.P1[(lv, c)], c)}) for pt in took}
                out[f"power|{key}"] = C.g8(level, names, sd, sc["interior"], sc["boundary"])["status"] == "failed"
        if cfg["inject"]:
            for mi, (mode, eps) in enumerate(INJECT):
                rng = _rng(cal_seed(10, r), mi, level == "full")
                t2 = {pt: _inject_take(rows[pt], N, mode, eps, rng) for pt in rows}
                key = f"inject|{mode}|{eps}|{level}"
                if any(t[0] is None for t in t2.values()):
                    out[key] = "short"
                    continue
                ens2 = {pt: _ensemble(t2[pt][0], t2[pt][1]) for pt in t2}
                out[key] = C.g8(level, names, sd, ens2["interior"], ens2["boundary"])["status"]
                out[key + "|injected"] = sum(t[2] for t in t2.values())
    return out


def toy_g8_judge(name: str, reps_rows: list, reps: int | None = None) -> dict:
    """The registered rule of one configuration over its replicate decisions."""
    cfg = TOY_CONFIGS[name]
    n_req = reps if reps is not None else cfg["reps"]
    n = len(reps_rows)
    short = sum(any(v == "short" for v in x.values()) for x in reps_rows)
    rec = {"configuration": name, "calibration": cfg["cal"], "row": cfg["row"], "mc_over_exposure": cfg["mcr"],
           "truth": cfg["truth"], "fit_V_MC_factor": cfg["fit_scale"], "replicates": n, "short": short,
           "false_alarms_standard": int(sum(x.get("standard") == "failed" for x in reps_rows)),
           "false_alarms_full": int(sum(x.get("full") == "failed" for x in reps_rows))}
    bias = [x["bias_over_sigma"] for x in reps_rows if "bias_over_sigma" in x]
    rec["mean_bias_over_sigma"] = np.mean(bias, 0).tolist() if bias else None
    rec["condition_bias_below_0.02"] = bool(bias and abs(rec["mean_bias_over_sigma"][1]) < BIAS_LIMIT)
    lim = 62 * n_req / 1000
    if not cfg["judged"]:
        rec.update(detection_standard=rec["false_alarms_standard"] / max(n, 1),
                   detection_full=rec["false_alarms_full"] / max(n, 1), status="reported", passed=None)
        return rec
    if n < n_req or short:
        rec.update(status="incomplete", passed=False)
        return rec
    ok = rec["false_alarms_standard"] <= lim and rec["false_alarms_full"] <= lim
    if cfg["power"]:
        rec["power"] = {k: int(sum(bool(x.get(f"power|{k}")) for x in reps_rows)) for k in CC.POWER}
        ok = ok and all(v >= 775 * n_req / 1000 for v in rec["power"].values())
    if cfg["inject"]:
        inj = {}
        for mode, eps in INJECT:
            for level in ("standard", "full"):
                key = f"inject|{mode}|{eps}|{level}"
                inj[key] = {"false_alarms": int(sum(x.get(key) == "failed" for x in reps_rows)),
                            "injected_fraction": float(sum(x.get(key + "|injected", 0) for x in reps_rows)
                                                       / max(2 * n * C.n_c(2, level)["N_c"], 1))}
        rec["calibration_10"] = inj
        rec["calibration_10_passed"] = all(v["false_alarms"] <= lim for v in inj.values())
        ok = ok and rec["calibration_10_passed"]
    if not rec["condition_bias_below_0.02"]:
        rec.update(status="exposure-condition-not-met", passed=False)
        return rec
    rec.update(status="passed" if ok else "failed", passed=bool(ok))
    return rec


# ------------------------------------------------------------------ toy_g8_mm: calibration 15's G8 item on the toy
MM_TRUTH = np.array([1.0, 0.6])               # the exact-degeneracy variant (Beta(2, 2)): mirror basin at (0.6, 1.0)
MM = {"exposure": 2000, "mc": 8000, "toys": 100, "per_point": 520, "chunk": 1}   # 100 toys: the user's reduction
MM_RULE = ("closure.decide at the full level (d = 2, N_c = 483 per point, the first 483 pseudo-data whose fit converged "
           "and whose toy-calibrated intervals were formed) on the toy-calibrated intervals (100 toys at the truth "
           "scan point; covered when p > 0.32 at 68%, p > 0.05 at 95%) of section 7.4 fits of the bimodal toy; the "
           "error taken to the nearer of the truth and its mirror point")


def _mm_problem(seed, sz):
    return _Problem(lambda n: toy.build_bimodal(n, 2.0, 2.0), CA.CAL15_NAMES, CA.CAL15_THETA,
                         exposure=sz["exposure"], mc_events=sz["mc"], mc_seed=(*seed, 1), boot_seed=(*seed, 2),
                         links={"sum_mean": "identity", "sum_m3": "identity"})


_MM_SD: dict = {}


def mm_design(sz) -> tuple:
    key = json.dumps(sz, sort_keys=True)
    if key not in _MM_SD:
        p0 = _mm_problem((cal_seed(51, 0),), sz)
        p0.observed = p0.asimov(np.r_[MM_TRUTH, np.zeros(p0.layout.n_beta - 2)])
        sd = F.find_extremum(p0, (cal_seed(51, 0), 3), p0.initial_beta()).sigma_tot[:2]
        th = list(CA.CAL15_THETA.values())
        _MM_SD[key] = (sd, C.injection_points([v["prior"] for v in th], [v["bounds"] for v in th], sd, MM_TRUTH,
                                              which=1))
    return _MM_SD[key]


def toy_g8_mm_block(point: str, start: int, n: int, sizes: dict | None = None) -> dict:
    sz = {**MM, **(sizes or {})}
    sd, pts = mm_design(sz)
    k = ("interior", "boundary").index(point)
    truth = np.asarray(pts[k], float)
    mirror = truth[::-1]
    rows = []
    for s in range(start, start + n):
        base = (cal_seed(15, s), 900 + k)
        p = _mm_problem(base, sz)
        p.observed = p.simulate(np.r_[truth, np.zeros(p.layout.n_beta - 2)], _rng(*base, 3), nominal=False)
        f = F.find_extremum(p, (*base, 4), p.initial_beta())
        row = {"s": s, "converged": bool(f.converged), "multimodal": "multimodal" in f.flags}
        if f.converged:
            th = f.beta[:2]
            row["basin_truth"] = bool(np.linalg.norm(th - truth) <= np.linalg.norm(th - mirror))
            row["error"] = ((th - truth) if row["basin_truth"] else (th - mirror)).tolist()
            pv = []
            for i in range(2):
                iv = IV.toy_calibrated(p, f, i, [float(truth[i])], sz["toys"], (*base, 5, i), 0.68)
                pv.append(iv["p"][0] if iv.get("status") == "ok" and iv.get("p") else None)
            row["toy_p"] = pv
            row["converged"] = None not in pv
        rows.append(row)
    return {"point": point, "rows": rows, "sigma_design": sd}


def toy_g8_mm_judge(blocks: list) -> dict:
    sd = np.asarray(blocks[0]["sigma_design"], float)
    N = C.n_c(2, "full")["N_c"]
    res = {}
    for name in ("interior", "boundary"):
        got, X = _take([x for b in blocks if b["point"] == name for x in b["rows"]], N)
        if got is None:
            return {"item": "toy_g8_mm", "status": "incomplete", "passed": False, "rule": MM_RULE}
        pv = np.array([x["toy_p"] for x in got], float)
        res[name] = {"errors": np.array([x["error"] for x in got]), "cover68": pv > 0.32, "cover95": pv > 0.05,
                     "nontruth_basin": np.array([not x["basin_truth"] for x in got]), "X": X,
                     "interval_toys": {"X": 0, "n": 0}}
    g = C.decide("full", list(CA.CAL15_THETA), res["interior"], res["boundary"], sd)
    return {"item": "toy_g8_mm", "calibration": 15, "row": 2018, "rule": MM_RULE, "status": g["status"],
            "fails": g.get("fails"), "b_bar": g.get("b_bar"),
            "coverage": {n: {"68": res[n]["cover68"].mean(0).tolist(), "95": res[n]["cover95"].mean(0).tolist()}
                         for n in res},
            "nontruth_basin_fraction": float(np.mean(res["interior"]["nontruth_basin"])),
            "passed": g["status"] == "passed", "label": f"{LABEL}; provisional-thresholds"}


# ================================================================== the task table, tasks, merge
def _tasks() -> list:
    t = [("units", {"item": k}) for k in UNIT_ITEMS]
    t += [("zdc_fit", {"r0": CALO_R0 + CALO_PER_TASK * i, "reps": CALO_PER_TASK})
          for i in range(CALO_REPS // CALO_PER_TASK)]                  # indices 3-12 as before
    t += [("phi_resim", {"case": c}) for c in PHI_CASES]
    for pt in ("interior", "boundary"):
        t += [("g8_3m", {"point": pt, "start": s, "n": M3["chunk"]}) for s in range(0, M3["per_point"], M3["chunk"])]
    t.append(("g8_3m_spot", {}))
    def toy(second: bool) -> list:
        out = []
        for name, cfg in TOY_CONFIGS.items():
            if bool(cfg.get("second")) != second:
                continue
            for r in range(cfg["reps"]):
                for pt in ("interior", "boundary"):
                    out += [("toy_g8", {"config": name, "r": r, "point": pt, "start": s, "n": toy_chunk(cfg)})
                            for s in range(0, TOY_PER_POINT, toy_chunk(cfg))]
        return out
    t += toy(False)
    for pt in ("interior", "boundary"):
        t += [("toy_g8_mm", {"point": pt, "start": s, "n": MM["chunk"]}) for s in range(0, MM["per_point"], MM["chunk"])]
    t += toy(True)                             # second registrations, after every earlier task (indices unchanged)
    t += [("zdc_fit_g4", {"r0": CALO_PER_TASK * i, "reps": CALO_PER_TASK})
          for i in range(CALO_REPS // CALO_PER_TASK)]                  # part D (A19): after every earlier task
    return t


TASKS = _tasks()
BLOCKS = {"units": units_block, "zdc_fit": calo_fit_block, "phi_resim": phi_resim_block, "g8_3m": g8_3m_block,
          "g8_3m_spot": g8_3m_spot, "toy_g8": toy_g8_block, "toy_g8_mm": toy_g8_mm_block,
          "zdc_fit_g4": calo_fit_g4_block}


def family_counts(tasks=None) -> dict:
    out: dict = {}
    for fam, kw in (tasks or TASKS):
        key = fam if fam != "toy_g8" else f"toy_g8|{kw['config']}"
        out[key] = out.get(key, 0) + 1
    return out


def run_task(i: int, out_dir: Path) -> dict:
    fam, kw = TASKS[i]
    t0 = time.time()
    res = BLOCKS[fam](**kw)
    rec = {"task": i, "family": fam, "kwargs": kw, "result": res, "seconds": time.time() - t0,
           "provenance": provenance(), "label": LABEL}
    out_dir.mkdir(parents=True, exist_ok=True)
    io.write_json(str(out_dir / f"task_{i:05d}.json"), io.jsonable(rec))
    return rec


def decide_all(recs: dict, tasks=None, toy_reps: dict | None = None) -> dict:
    """Every item from its task records ({index: record}; missing indices are None), each judged by its rule."""
    tasks = tasks or TASKS
    by: dict = {}
    for i, (fam, kw) in enumerate(tasks):
        by.setdefault(fam, []).append((kw, (recs.get(i) or {}).get("result")))
    items = {}
    for kw, res in by.get("units", []):
        items[f"units|{kw['item']}"] = judge_units(kw["item"], res["outcomes"]) if res else \
            {"item": kw["item"], "passed": False, "status": "missing"}
    if "zdc_fit" in by:
        rows = [x for _, res in by["zdc_fit"] if res for x in res]
        items["zdc_fit"] = calo_fit_judge(rows, reps=sum(kw["reps"] for kw, _ in by["zdc_fit"]))
    if "zdc_fit_g4" in by:
        rows = [x for _, res in by["zdc_fit_g4"] if res for x in res]
        items["zdc_fit_g4"] = calo_fit_judge(rows, reps=sum(kw["reps"] for kw, _ in by["zdc_fit_g4"]),
                                             item="zdc_fit_g4", rule=CALO_G4_RULE,
                                             label=f"{LABEL}; p3-g4 Geant4 products, re-digitization")
    if "phi_resim" in by:
        items["phi_resim"] = phi_resim_judge([res for _, res in by["phi_resim"] if res])
    if "g8_3m" in by:
        blocks = [res for _, res in by["g8_3m"] if res]
        spot = next((res for _, res in by.get("g8_3m_spot", []) if res), None)
        items["g8_3m"] = g8_3m_judge(blocks, spot) if blocks else {"item": "g8_3m", "passed": False,
                                                                   "status": "missing"}
        if blocks:                             # the non-converged pseudo-data and their reasons (review F7)
            nc: dict = {}
            for b in blocks:
                for x in b["rows"]:
                    if not x.get("converged"):
                        e = nc.setdefault(b["point"], {"n": 0, "reasons": {}})
                        e["n"] += 1
                        key = str(x.get("reason", ""))[:80]
                        e["reasons"][key] = e["reasons"].get(key, 0) + 1
            items["g8_3m"]["non_converged"] = nc
    toy: dict = {}
    for kw, res in by.get("toy_g8", []):
        if res:
            toy.setdefault(kw["config"], {}).setdefault(kw["r"], []).append(res)
    for name, reps in toy.items():
        sd = np.asarray(next(iter(reps.values()))[0]["sigma_design"], float)
        dec = [toy_g8_replicate(name, r, bl, sd) for r, bl in sorted(reps.items())]
        n_req = (toy_reps or {}).get(name)
        items[f"toy_g8|{name}"] = toy_g8_judge(name, dec, n_req)
    if "toy_g8_mm" in by:
        blocks = [res for _, res in by["toy_g8_mm"] if res]
        items["toy_g8_mm"] = toy_g8_mm_judge(blocks) if blocks else {"item": "toy_g8_mm", "passed": False}
    return items


GATE_ITEMS = ("units|p6_negatives", "units|g4sim_zdc_positive", "units|response_phi", "zdc_fit", "zdc_fit_g4",
              "phi_resim", "g8_3m")


def _products_record() -> dict:
    """The Geant4 products the units and zdc_fit_g4 items read: their root and the tell state's SHA-256 (review F7)."""
    root = Path(os.environ.get(P3.PRODUCTS_ENV) or P3.OUT_ROOT)
    tell = root / "tell.json"
    return {"root": str(root), "tell_sha256": hashlib.sha256(tell.read_bytes()).hexdigest() if tell.is_file() else None}


def merge(out_dir: Path, out: Path) -> dict:
    recs = {}
    for i in range(len(TASKS)):
        f = out_dir / f"task_{i:05d}.json"
        recs[i] = json.loads(f.read_text()) if f.exists() else None
    missing = [i for i, r in recs.items() if r is None]
    by_family: dict = {}                       # each family from one clean commit (the arrays may be registered apart)
    for i, r in recs.items():
        if r:
            fam = family_counts([TASKS[i]]).popitem()[0]
            f = by_family.setdefault(fam, {"commits": set(), "dirty": False})
            f["commits"].add(r["provenance"]["commit"])
            f["dirty"] = f["dirty"] or bool(r["provenance"].get("dirty"))
    commits = {c for f in by_family.values() for c in f["commits"]}
    dirty = any(f["dirty"] for f in by_family.values())
    items = decide_all(recs)
    for k, v in items.items():
        fams = [f for f in by_family if f == k.split("|")[0] or f == k or (k == "g8_3m" and f == "g8_3m_spot")]
        clean = all(len(by_family[f]["commits"]) == 1 and not by_family[f]["dirty"] for f in fams)
        if not clean and v.get("passed"):
            v.update(passed=False, status="not-from-one-clean-commit")
    gate = [k for k in GATE_ITEMS if k in items]
    gate_fams = ("units", "zdc_fit", "zdc_fit_g4", "phi_resim", "g8_3m", "g8_3m_spot")
    gate_commits = {c for f in gate_fams if f in by_family for c in by_family[f]["commits"]}
    gate_ok = len(gate_commits) == 1 and len(gate) == len(GATE_ITEMS) and all(items[k].get("passed") for k in gate)
    rep = {"gate": "phase 3 (section 17): P6 negative tests; G8 for the three-method combination; g4sim positive tests "
                   "on the synthetic ZDC fixture; the response-layer parameters and phi at the resimulation level",
           "gate_status": "passed" if gate_ok else "failed", "missing_tasks_by_family": family_counts(
               [TASKS[i] for i in missing]), "commits": sorted(commits), "dirty": dirty,
           "commits_by_family": {f: sorted(v["commits"]) for f, v in by_family.items()},
           "items": {k: v for k, v in items.items() if k in GATE_ITEMS},
           "passed": {k: v.get("passed") for k, v in items.items() if k in GATE_ITEMS},
           "other_items": {k: v for k, v in items.items() if k not in GATE_ITEMS},
           "other_items_note": "not gate items: the toy calibration rows, judged in their own campaigns (review F7)",
           "products": _products_record(),
           "not_judged": [],
           "task_seconds": {i: r["seconds"] for i, r in recs.items() if r}, "provenance": provenance(),
           "label": LABEL}
    io.write_json(str(out), io.jsonable(rep))
    return rep


# ------------------------------------------------------------------ --local: every family at tiny sizes
LOCAL_M3 = {"exposure": 400, "mc": 2000, "truth_batches": 2, "truth_batch_factor": 2, "n_design": 6,
            "per_point": 2, "chunk": 1}


def local(out: Path) -> dict:
    """Each family's code path at tiny sizes (`smoke`, not evidence): one unit item (a small test class), one
    ZDC repetition (small batches), the three-method G8 (one pseudo-data per point, small MC; the spot check), one
    toy-G8 chunk per point (exposure 400, 2 fits), and the judges on what they produced."""
    t0 = time.time()
    res: dict = {}
    few = [EMULATOR_TESTS + "P6Arrays.test_bonferroni_z", EMULATOR_TESTS + "P6Arrays.test_delta_m_fails_on_a_large_difference"]
    res["units"] = judge_units("p6_negatives", run_tests(few), names=few)
    res["zdc_fit"] = calo_fit_judge(calo_fit_block(900000, 1, n_mc=300, exposure=200, n_truth=1200), reps=1)
    blocks = [g8_3m_block(pt, 0, 1, LOCAL_M3) for pt in ("interior", "boundary")]
    res["g8_3m_rows"] = blocks
    res["g8_3m_spot"] = g8_3m_spot(LOCAL_M3)["spot_check"]["status"]
    tb = [toy_g8_block("cal1", 900000, pt, 0, 2, exposure=400) for pt in ("interior", "boundary")]
    res["toy_g8_rows"] = tb
    rec = {"label": "smoke (not evidence)", "results": res, "seconds": time.time() - t0, "provenance": provenance()}
    io.write_json(str(out), io.jsonable(rec))
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--task", type=int)
    ap.add_argument("--merge")
    ap.add_argument("--local", action="store_true", dest="smoke_run")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.list:
        print(json.dumps({"tasks": len(TASKS), "families": family_counts(),
                          "table": [{"index": i, "family": f, "kwargs": kw} for i, (f, kw) in enumerate(TASKS)]}))
        return 0
    if not a.out:
        ap.error("--out is required")
    if a.task is not None:
        r = run_task(a.task, Path(a.out))
        print(json.dumps({"task": r["task"], "family": r["family"], "seconds": r["seconds"]}))
        return 0
    if a.merge:
        r = merge(Path(a.merge), Path(a.out))
        print(json.dumps({"gate_status": r["gate_status"], "passed": r["passed"],
                          "missing": r["missing_tasks_by_family"]}))
        return 0 if r["gate_status"] == "passed" else 1
    if a.smoke_run:
        r = local(Path(a.out))
        print(json.dumps({"label": r["label"], "seconds": r["seconds"]}))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
