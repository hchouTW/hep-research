"""The section 8.7 calibrations of phase 3 (task card `docs/dev/simulator-calibration/simcal-tasks/phase-3.md`,
"Thresholds and test designs"), run as Slurm job arrays: each task writes the raw per-repetition records of one block
of one configuration; the merge concatenates them and applies the registered rule (failures are reported, never
retuned). Not a unit test module.

  python3 calibration_phase3_cals.py --list                        the task table (JSON)
  python3 calibration_phase3_cals.py --task K --out DIR            one task of the array
  python3 calibration_phase3_cals.py --merge DIR --out FILE        merge and judge (exit 0 passed, 1 failed/incomplete)
  python3 calibration_phase3_cals.py --local --out FILE            every family at tiny sizes (`smoke`, not evidence)

Families (calibration index c of the seeds):
  1 `p6`    row 2004, P6 part: the false-alarm rate of P6 with a correct (known-error) surrogate on the toy detector.
  2 `theta` row 2008: the theta-noise bounds of P5 in the mode where the map varies with theta; the pull width of
            theta-hat and G8 at the full level of section 8.4, with the exact map covariance of the scan.
  3 `pde`   row 2009: the PDE split's false-rejection rate under an exact split, its power against a reflectance tied
            to the PDE, and the route-3 replica covariance against the multinomial covariance over grid sizes.

Seeds: repetition r of calibration c and configuration j draws from default_rng([cal_seed(c, r), j, ...]) (no stream
shared between calibrations, configurations or repetitions); cal_seed(c, r) = 20261312 + 100000 c + r. Every record is
labelled `synthetic` (the toy detector, and synthetic optics with g4sim's map and replica laws: Geant4 not run) and
`provisional-thresholds` until the author writes the calibrated values back into section 8.7.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import subprocess
import sys
import time
import warnings
from pathlib import Path

import numpy as np
from scipy import linalg, optimize, stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import calibration_pde_fixtures as PF  # noqa: E402
import calibration_phase1 as H1  # noqa: E402

from core.calibration import closure as C  # noqa: E402
from core.calibration import design_map as DM  # noqa: E402
from core.calibration import emulator as EM  # noqa: E402
from core.calibration import evaluator as E  # noqa: E402
from core.calibration import io  # noqa: E402
from core.calibration import map_basis as MB  # noqa: E402
from core.calibration import map_term as MT  # noqa: E402
from core.calibration import pde_split as S  # noqa: E402
from core.simulation import efficiency_map as em  # noqa: E402

warnings.filterwarnings("ignore", message="The balance properties of Sobol")

FLAGS = ["synthetic", "provisional-thresholds"]
FILES = ["core/calibration/" + f for f in ("emulator.py", "evaluator.py", "toy.py", "design.py", "design_map.py",
                                            "map_term.py", "map_basis.py", "closure.py", "pde_split.py",
                                            "data/toy_detector_design.json")] + \
    ["core/simulation/efficiency_map.py", "tests/core/calibration_phase3_cals.py",
     "tests/core/calibration_pde_fixtures.py", "tests/core/calibration_phase1.py",
     "docs/dev/simulator-calibration/simcal-tasks/phase-3.md"]
SEED0 = 20261312


def cal_seed(c: int, r: int) -> int:
    return SEED0 + 100_000 * c + r


def _rng(c, r, j, *more):
    return np.random.default_rng([cal_seed(c, r), j, *more])


def _int(c, r, j, *more) -> int:
    return int(np.random.SeedSequence([cal_seed(c, r), j, *more]).generate_state(1)[0] % (2 ** 31 - 1)) + 1


def provenance() -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True,
                                timeout=60).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", *FILES], cwd=ROOT, capture_output=True,
                                    text=True, timeout=60).stdout.strip())
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        commit, dirty = None, None
    return {"commit": commit, "dirty": dirty, "python": sys.version.split()[0], "numpy": np.__version__,
            "sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES}}


def clopper_pearson(x: int, n: int, level: float = 0.95) -> list:
    a = 1 - level
    lo = 0.0 if x == 0 else float(stats.beta.ppf(a / 2, x, n - x + 1))
    hi = 1.0 if x == n else float(stats.beta.ppf(1 - a / 2, x + 1, n - x))
    return [lo, hi]


def max_false_alarms(n: int, rate: float, pass_probability: float = 0.97) -> int:
    """The smallest count c with P(Binomial(n, rate) <= c) >= pass_probability (the phase-1 form of the row-2004 rule:
    <= 16 of 1000 at rate 0.01 passes with probability 0.97)."""
    return int(stats.binom.ppf(pass_probability, n, rate))


# ====================================================================== 1. row 2004, P6 part
P6_ALPHA = EM.ALPHA_P6
P6_H = (8, 20, 40)                       # held-out points (x 3 observables); the pull chi2 needs >= 30 points
P6_VEMU = (0.0, 1.0)                     # V_emu = v * cov_delta at each point (v = 0: no interpolation error)
P6_REPS = 2000
P6_BLOCK = {8: 50, 20: 50, 40: 50}
P6_MAX_FALSE_ALARMS = max_false_alarms(P6_REPS, P6_ALPHA)   # 29 of 2000 (pass probability 0.979 at rate alpha)
P6_DESIGN_SEED = 20261313
_P6_CACHE: dict = {}


def _p6_case(H: int):
    """The toy detector of section 15.1 with the threshold (resimulation level) evaluated by a surrogate, the three
    single-photoelectron observables (as WP-A's toy_case), and H held-back points from calib_design's Sobol set."""
    if H not in _P6_CACHE:
        d = copy.deepcopy(H1.toy_design())
        c, p = d["contract"], d["plan"]
        for q in c["parameters"]:
            if q["name"] == "threshold":
                q["sampling_bounds"] = [1.0, 16.0]
        c["observables"] = [o for o in c["observables"] if o["name"] in ("spe_e_mean", "spe_e_width",
                                                                          "spe_efficiency")]
        p["methods"]["threshold"] = "surrogate-model"
        p["design"]["surrogate"] = {"n_design": 8, "held_back": H, "seed": P6_DESIGN_SEED, "mode": "interpolate"}
        cfg = EM.settings(c, p)
        held = EM.design(cfg)["held_back"]
        _P6_CACHE[H] = (c, p, E.make(p, c), cfg, held, EM._names(c, None))
    return _P6_CACHE[H]


def _p6_eval(ev, held, theta_ref, names, seed):
    st = EM.new_state(held, "held-back", theta_ref, {"nominal": int(seed)}, names)
    run = EM.drive(ev, st)
    if run["status"] != "ok":
        raise RuntimeError("toy evaluations outstanding")
    return [e["_raw"] for e in st["entries"]]


def _sqrt_psd(M: np.ndarray) -> np.ndarray:
    lam, Q = np.linalg.eigh(0.5 * (M + M.T))
    return Q * np.sqrt(np.clip(lam, 0.0, None))


# second registration of row 2004 (2026-11-12): fresh seeds, because the first run's repetitions 0-499 at H = 40 were
# used by the research that validated the joint-covariance reference
P6_R_OFFSET = 1_000_000


def p6_rep(H: int, r: int) -> dict:
    """One repetition: full simulation at the H held-back points (seed s_full) against a known-error toy surrogate
    (section 8.7 note 4): its prediction is an independent design-point MC at the same point (seed s_sur, weight 1)
    plus an interpolation error e ~ N(0, V_emu) with V_emu = v cov_delta reported exactly. sigma_Delta is the
    event-bootstrap covariance of the difference with independent seeds (emulator.delta_covariance, paired=False)."""
    j = P6_H.index(H)
    c, _, ev, cfg, held, names = _p6_case(H)
    full = _p6_eval(ev, held, cfg["theta_ref"], names, _int(1, r + P6_R_OFFSET, j, 1))
    sur = _p6_eval(ev, held, cfg["theta_ref"], names, _int(1, r + P6_R_OFFSET, j, 2))
    ev._other.clear()                    # the toy keeps every seeded sample: free them (memory per task stays flat)
    k = len(names)
    dm = np.array([np.asarray(s["pred"], float) - np.asarray(f["pred"], float) for f, s in zip(full, sur)])
    cd = np.array([EM.delta_covariance(f, [s], np.array([1.0]), k, paired=False) for f, s in zip(full, sur)])
    # the joint covariance over the held-out points: each side shares its events across points (one seed per side)
    cj = EM.joint_delta_covariance(full, sur, np.eye(H), k, paired=False) if H >= EM.MIN_PULL_POINTS else None
    vd = np.array([EM.v_data_unc(c, f) for f in full])
    g = _rng(1, r + P6_R_OFFSET, j, 3)
    z = g.standard_normal((H, k))
    out = {"r": r}
    for v in P6_VEMU:
        ve = v * cd
        e = np.array([_sqrt_psd(ve[h]) @ z[h] if v else np.zeros(k) for h in range(H)])
        res = EM.p6(dm + e, cd, ve, vd, cov_joint=cj)
        sig = np.sqrt(np.einsum("hkk->hk", cd))
        zonly = bool(np.any(np.abs(dm + e) > EM.bonferroni_z(H * k) * sig))
        pc = res["parts"]["pull_chi2"]
        out[str(v)] = {"failed": res["status"] == "failed", "delta_m_failed": res["parts"]["delta_m"]["status"] ==
                       "failed", "z_only_failed": zonly, "max_ratio": res["parts"]["delta_m"]["max_ratio"],
                       "chi2": pc.get("chi2"), "dof": pc.get("dof"),
                       "chi2_failed": pc["status"] == "failed" if pc["status"] != "not-executed" else None}
    out["data_term_over_sigma_delta"] = float(np.median(0.3 * np.sqrt(vd) / np.sqrt(np.einsum("hkk->hk", cd))))
    return out


def p6_block(H: int, r0: int, reps: int) -> list:
    return [p6_rep(H, r) for r in range(r0, r0 + reps)]


def p6_judge(rows_by: dict, reps: int = P6_REPS, max_false_alarms: int = P6_MAX_FALSE_ALARMS) -> dict:
    out, ok = {}, True
    for key, rows in sorted(rows_by.items()):
        H, v = key.split("|")
        sub = [x[v] for x in rows]
        n = len(sub)
        fa = sum(x["failed"] for x in sub)
        rec = {"H": int(H), "v_emu": float(v), "reps": n, "false_alarms": fa, "rate": fa / max(n, 1),
               "rate_cp95": clopper_pearson(fa, n), "delta_m_rate": sum(x["delta_m_failed"] for x in sub) / max(n, 1),
               "z_only_rate": sum(x["z_only_failed"] for x in sub) / max(n, 1),
               "max_ratio_median": float(np.median([x["max_ratio"] for x in sub])) if n else None,
               "data_term_over_sigma_delta_median": float(np.median([x["data_term_over_sigma_delta"]
                                                                     for x in rows])) if n else None}
        chi = [x for x in sub if x["chi2_failed"] is not None]
        if chi:
            rec["pull_chi2_size"] = sum(x["chi2_failed"] for x in chi) / len(chi)
            rec["pull_chi2_size_cp95"] = clopper_pearson(sum(x["chi2_failed"] for x in chi), len(chi))
            rec["v_emu_scale"] = float(np.mean([x["chi2"] / x["dof"] for x in chi]))   # mean chi2/dof: 1 if correct
        # judged: the correct surrogate (v = 0, no error beyond MC noise; the user's decision of 2026-11-12); v = 1
        # (an error drawn at V_emu) is P6's sensitivity to an emulation error, reported
        rec["judged"] = float(v) == 0.0
        rec["passed"] = bool(n >= reps and fa <= max_false_alarms) if rec["judged"] else None
        ok = ok and (rec["passed"] is not False)
        out[key] = rec
    ok = ok and any(r.get("judged") for r in out.values())          # at least one judged configuration
    return {"calibration": "p6", "row": 2004, "configurations": out, "passed": bool(ok), "flags": FLAGS,
            "rule": f"per configuration (H held-out points x 3 observables, V_emu scale v), P6 fails (either part) in "
                    f"<= {max_false_alarms} of {reps} repetitions with a correct surrogate (the phase-1 form of this "
                    "row's rule: "
                    f"pass probability >= 0.97 at a true false-alarm rate alpha = {P6_ALPHA}); the pull-chi2 size, the "
                    "z-only rate and the V_emu scale (mean chi2/dof) are reported; judged at v = 0 only (the user's decision of "
                    "2026-11-12), v = 1 reported; the pull chi2 referenced to its exact null distribution under the "
                    "joint covariance of the held-out points (emulator.p6 cov_joint)"}


# ====================================================================== 2. row 2008, theta-noise bounds of P5
TH_BINS = 8
TH_P = np.linspace(0.05, 0.09, TH_BINS)            # efficiency per bin at theta = 1
TH_C = np.linspace(-0.3, 0.3, TH_BINS)             # curvature per bin (eps increasing in theta over [0.5, 1.5])
TH_OBS_REL = 0.085                                 # observation noise sd relative to eps_b(1): sigma_tot ~ 0.03
TH_J = 6
TH_PHOTONS = (1_000_000, 10_000_000)
TH_SPACING = (0.1, 0.2)
TH_SEEDING = ("shared", "independent", "nested")   # shared: joint-pattern coupling, divergence = spacing per step
TH_REPS = 2000                                     # interior injection point (pull width, G8 interior)
TH_CLOSURE_COUNT = C.n_c(1, "full")["N_c"]                    # 412: G8 at the full level, d = 1 (section 8.4)
TH_BLOCK = 1000
TH_PULL_WIDTH_MAX = 1.05


def th_configs() -> list:
    return [(n, s, m) for n in TH_PHOTONS for s in TH_SPACING for m in TH_SEEDING]


def th_key(n, s, m) -> str:
    return f"{n:.0e}|{s}|{m}"


def eps_true(theta) -> np.ndarray:
    t = np.asarray(theta, float)[..., None]
    return TH_P * t * (1.0 + TH_C * (t - 1.0))


def eps_slope(theta: float) -> np.ndarray:
    return TH_P * (1.0 + TH_C * (2.0 * theta - 1.0))


def th_points(spacing: float) -> np.ndarray:
    return 1.0 + spacing * (np.arange(TH_J) - 0.5 * (TH_J - 1))


def th_divergence(spacing: float, seeding: str) -> float:
    return {"shared": spacing, "independent": 1.0, "nested": 0.0}[seeding]


def map_covariance(eps_pts: np.ndarray, n_b: float, divergence: float) -> np.ndarray:
    """The exact covariance of the mapping-run estimates eps-hat_jb = k_jb / n_b of a scan (J x J x B x B): bins
    independent; per photon a uniform u kept between design points with probability 1 - divergence (redrawn
    otherwise), detected at j when u < eps_jb, so Cov = (1 - divergence)^|j - l| (min(eps_j, eps_l) - eps_j eps_l)."""
    J, B = eps_pts.shape
    S_ = np.zeros((J, J, B, B))
    for j in range(J):
        for m in range(J):
            f = (1.0 - divergence) ** abs(j - m) if divergence < 1.0 else float(j == m)
            S_[j, m] = np.diag(f * (np.minimum(eps_pts[j], eps_pts[m]) - eps_pts[j] * eps_pts[m]) / n_b)
    return S_


def sample_maps(eps_pts: np.ndarray, n_b: int, divergence: float, g) -> np.ndarray:
    """Exact draws of eps-hat (J x B) under the coupling of map_covariance: per bin the photons' cells between the
    sorted thresholds form a Markov chain over the design points (stay with probability 1 - divergence, else redrawn
    from the cell probabilities)."""
    J, B = eps_pts.shape
    out = np.zeros((J, B))
    for b in range(B):
        e = eps_pts[:, b]
        if np.any(np.diff(e) <= 0):
            raise ValueError("eps must increase along the scan")
        pi = np.diff(np.r_[0.0, e, 1.0])
        m = g.multinomial(n_b, pi)
        for j in range(J):
            if j:
                moved = g.binomial(m, divergence) if divergence > 0 else np.zeros_like(m)
                m = m - moved + (g.multinomial(int(moved.sum()), pi) if moved.sum() else 0)
            out[j, b] = m[:j + 1].sum() / n_b
    return out


class ThetaFit:
    """The fit of one repetition: the regression-mode surrogate over the J noisy maps, the map term U(theta) phi_map
    from the exact scan covariance (shared: joint U_j; independent: per-point blocks), phi_map profiled with theta
    (closed form: the profiled deviance is r^T (V + U U^T)^-1 r, as fit.minimize gives for this linear Gaussian term,
    WP-D's test_fixed_map_profile_equals_marginal_gls), and profile intervals at 68% and 95% within the design box."""

    def __init__(self, eps_hat, points, Sig, seeding, v_obs):
        self.lo, self.hi = float(points[0]), float(points[-1])
        pts = [{"t": float(x)} for x in points]
        self.sur = EM.Surrogate(["t"], {"t": [self.lo, self.hi]}, pts, eps_hat, mode="regression")
        J, B = eps_hat.shape
        if seeding == "independent":
            U = [linalg.cholesky(Sig[j, j], lower=True) for j in range(J)]
            mode = "independent"
        else:
            big = np.block([[Sig[j, m] for m in range(J)] for j in range(J)])
            U = MB.u_analytic([np.eye(B)] * J, big)
            mode = "shared"
        self.term = MT.MapTerm(U, list(range(B)), B, mode, surrogate=self.sur, theta_names=["t"])
        self.V = np.diag(v_obs)
        self.Sig, self.seeding = Sig, seeding

    def q(self, t: float, y) -> float:
        th = {"t": float(t)}
        r = y - self.sur.weights(th) @ self.sur.values
        Cm = self.V + self.term.covariance(th)
        return float(r @ linalg.solve(Cm, r, assume_a="pos"))

    def sigma(self, t: float) -> float:
        th = {"t": float(t)}
        d1, _ = self.sur.weight_derivatives(th, "t")
        dmu = d1 @ self.sur.values
        Cm = self.V + self.term.covariance(th)
        return float(1.0 / math.sqrt(dmu @ linalg.solve(Cm, dmu, assume_a="pos")))

    def fit(self, y) -> dict:
        grid = np.linspace(self.lo, self.hi, 61)
        qs = np.array([self.q(t, y) for t in grid])
        i = int(np.argmin(qs))
        a, b = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
        res = optimize.minimize_scalar(lambda t: self.q(t, y), bounds=(a, b), method="bounded",
                                       options={"xatol": 1e-7 * (self.hi - self.lo)})
        th, qmin = (float(res.x), float(res.fun)) if res.fun <= qs[i] else (float(grid[i]), float(qs[i]))
        out = {"theta_hat": th, "q_min": qmin, "sigma_hat": self.sigma(th)}
        for name, lev in (("68", 1.0), ("95", float(stats.chi2.ppf(0.95, 1)))):
            f = lambda t: self.q(t, y) - qmin - lev     # noqa: E731
            lo = self.lo if f(self.lo) <= 0 else optimize.brentq(f, self.lo, th, xtol=1e-9) if th > self.lo else th
            hi = self.hi if f(self.hi) <= 0 else optimize.brentq(f, th, self.hi, xtol=1e-9) if th < self.hi else th
            out[f"interval{name}"] = [float(lo), float(hi)]
        return out


def th_design(n: int, spacing: float, seeding: str) -> dict:
    """The configuration's fixed quantities: design points, exact covariance, observation noise, sigma_tot^design at
    the box centre, and the injection points (closure.injection_points; the design box is the physical range)."""
    pts = th_points(spacing)
    eps_pts = eps_true(pts)
    n_b = n // TH_BINS
    div = th_divergence(spacing, seeding)
    Sig = map_covariance(eps_pts, n_b, div)
    v_obs = (TH_OBS_REL * eps_true(1.0)) ** 2

    def sig_design(t):
        e = eps_true(t)
        Cm = np.diag(v_obs + e * (1 - e) / n_b)
        d = eps_slope(t)
        return float(1.0 / math.sqrt(d @ np.linalg.solve(Cm, d)))
    sd = np.array([sig_design(1.0)])
    interior, boundary = C.injection_points([(pts[0], pts[-1])], [(pts[0], pts[-1])], sd, np.array([1.0]))
    return {"points": pts, "eps_points": eps_pts, "n_b": n_b, "divergence": div, "Sigma": Sig, "v_obs": v_obs,
            "sigma_design": {"interior": sig_design(float(interior[0])), "boundary": sig_design(float(boundary[0]))},
            "interior": float(interior[0]), "boundary": float(boundary[0])}


def th_rep(n: int, spacing: float, seeding: str, where: str, r: int, design: dict | None = None) -> dict:
    j = th_configs().index((n, spacing, seeding))
    d = design or th_design(n, spacing, seeding)
    g = _rng(2, r, j, 0 if where == "interior" else 1)
    eps_hat = sample_maps(d["eps_points"], d["n_b"], d["divergence"], g)
    truth = d[where]
    y = eps_true(truth) + g.standard_normal(TH_BINS) * np.sqrt(d["v_obs"])
    fit = ThetaFit(eps_hat, d["points"], d["Sigma"], "independent" if seeding == "independent" else "shared",
                   d["v_obs"])
    f = fit.fit(y)
    sdes = d["sigma_design"][where]
    tn = DM.theta_noise(fit.sur, [{"theta": {"t": x}, "V_G": fit.V} for x in (d["interior"], d["boundary"])],
                        {"t": d["sigma_design"]["interior"]}, Sigma=d["Sigma"],
                        seeding="independent" if seeding == "independent" else "shared")
    pp = tn["per_parameter"]["t"]
    return {"r": r, "where": where, "converged": True, "error": f["theta_hat"] - truth,
            "pull": (f["theta_hat"] - truth) / f["sigma_hat"], "pull_design": (f["theta_hat"] - truth) / sdes,
            "sigma_hat": f["sigma_hat"], "cover68": bool(f["interval68"][0] <= truth <= f["interval68"][1]),
            "cover95": bool(f["interval95"][0] <= truth <= f["interval95"][1]), "s": pp["s"], "kappa": pp["kappa"],
            "p5_passed": bool(tn["passed"]), "nugget": float(fit.sur.nugget)}


def th_block(n: int, spacing: float, seeding: str, where: str, r0: int, reps: int) -> list:
    d = th_design(n, spacing, seeding)
    return [th_rep(n, spacing, seeding, where, r, d) for r in range(r0, r0 + reps)]


def _sd_ci(x: np.ndarray) -> list:
    n = len(x)
    s = float(np.std(x, ddof=1))
    return [s * math.sqrt((n - 1) / stats.chi2.ppf(0.975, n - 1)), s * math.sqrt((n - 1) / stats.chi2.ppf(0.025,
                                                                                                         n - 1))]


def th_judge(rows_by: dict, reps: int = TH_REPS, closure_count: int = TH_CLOSURE_COUNT) -> dict:
    """Per configuration: within the bounds (median over repetitions of the worst-point s <= 0.25 and kappa <= 0.05,
    section 8.2 note 3 fifth item) the pull sd of theta-hat over the interior repetitions is <= 1.05, and G8 at the
    full level (closure.decide on the first N_c interior and N_c boundary repetitions) passes. Configurations outside
    the bounds are reported, not judged."""
    out, ok = {}, True
    for key, rows in sorted(rows_by.items()):
        inner = [x for x in rows if x["where"] == "interior"]
        bnd = [x for x in rows if x["where"] == "boundary"]
        inner.sort(key=lambda x: x["r"])
        bnd.sort(key=lambda x: x["r"])
        n = len(inner)
        pull = np.array([x["pull"] for x in inner])
        s_med = float(np.median([x["s"] for x in inner])) if n else None
        k_med = float(np.median([x["kappa"] for x in inner])) if n else None
        within = bool(n and s_med <= DM.S_BOUND and k_med <= DM.KAPPA_BOUND)
        rec = {"reps": n, "boundary_reps": len(bnd), "s_median": s_med, "kappa_median": k_med,
               "s_q90": float(np.quantile([x["s"] for x in inner], 0.9)) if n else None,
               "kappa_q90": float(np.quantile([x["kappa"] for x in inner], 0.9)) if n else None,
               "within_bounds": within, "p5_pass_fraction": float(np.mean([x["p5_passed"] for x in inner])) if n
               else None}
        if n > 1:
            rec.update(pull_mean=float(pull.mean()), pull_sd=float(pull.std(ddof=1)), pull_sd_ci95=_sd_ci(pull),
                       pull_design_sd=float(np.std([x["pull_design"] for x in inner], ddof=1)),
                       cover68=float(np.mean([x["cover68"] for x in inner])),
                       cover95=float(np.mean([x["cover95"] for x in inner])))
            p5 = np.array([x["pull"] for x in inner if x["p5_passed"]])
            rec["pull_sd_where_p5_passes"] = float(p5.std(ddof=1)) if len(p5) > 1 else None
        g8 = None
        if len(inner) >= closure_count and len(bnd) >= closure_count:
            def pt(xs):
                return {"errors": np.array([[x["error"]] for x in xs[:closure_count]]),
                        "cover68": np.array([[x["cover68"]] for x in xs[:closure_count]]),
                        "cover95": np.array([[x["cover95"]] for x in xs[:closure_count]]),
                        "nontruth_basin": np.zeros(closure_count, bool)}
            sd = float(np.median([x["error"] / x["pull_design"] for x in inner if x["pull_design"]]))
            g8 = C.decide("full", ["t"], pt(inner), pt(bnd), np.array([sd]))
            rec["g8"] = {k: g8[k] for k in ("status", "fails", "p", "b_bar", "family")}
        complete = n >= reps and g8 is not None
        rec["complete"] = complete
        if within:
            rec["passed"] = bool(complete and rec["pull_sd"] <= TH_PULL_WIDTH_MAX and g8["status"] == "passed")
            ok = ok and rec["passed"]
        else:
            rec["passed"] = None
            ok = ok and complete
        out[key] = rec
    return {"calibration": "theta", "row": 2008, "configurations": out, "passed": bool(ok), "flags": FLAGS,
            "rule": f"within the bounds (median worst-point s <= {DM.S_BOUND}, kappa <= {DM.KAPPA_BOUND}) the pull sd "
                    f"of theta-hat over {reps} repetitions is <= {TH_PULL_WIDTH_MAX} and G8 passes at the full level "
                    "of "
                    f"section 8.4 (N_c = {closure_count} at each injection point); configurations outside the bounds "
                    "are reported"}


# ====================================================================== 3. row 2009, PDE split
PDE_PHOTONS = 20000
PDE_P0 = 0.4
PDE_EXACT = ("scale", "table")           # route 2_1 (p0) and route 3 (PDE(E)) nominal PDE
PDE_EXACT_REPS = 2000
PDE_PASS_MIN = 0.94
PDE_RHO = (0.05, 0.1, 0.25, 0.5)
PDE_POWER_REPS = 500
PDE_GRIDS = (1, 3, 6, 12, 24)            # energy cells of the route-3 grid
PDE_MAPS = 200
PDE_R = 1000
PDE_VAR_MIN = S.VARIANCE_RATIO           # 0.98
PDE_BLOCK = {"exact": 250, "power": 250, "replicas": 25}
GEANT4_NOT_RUN = ("the same three items on the ZDC fixture with optics, the nested pair from G4OpBoundaryProcess "
                  "(Geant4 transport, g4sim S7 mapping runs at efficiency 1 and at the nominal PDE with one "
                  "logical_run_seed and event interval): not run (Part B section 15.2: confirm with Geant4)")


def _nominal(kind: str) -> dict:
    return {"p": PDE_P0} if kind == "scale" else {"table": PF.pde_table()}


def _pair(seed: int, efficiency, rho: float = 0.0):
    ph1, pr, emitted, detected = PF.run(PDE_PHOTONS, seed=seed, efficiency=1.0)
    php, _, _, _ = PF.run(PDE_PHOTONS, seed=seed, efficiency=efficiency, rho=rho)
    m = PF.build_map(emitted, detected)
    prim = S.read_primaries(pr)
    r1 = S.binned(m, S.read_photons(ph1), prim, PF.CENTRE)
    rp = S.binned(m, S.read_photons(php), prim, PF.CENTRE)
    return m, r1, rp, (S.read_photons(ph1), S.read_photons(php))


def pde_propagation(m: dict, r1: dict, nominal: dict) -> dict:
    """theta = a scale of the PDE, observed through the total detected fraction: d theta = d(sum eps)/sum eps(p0); the
    pair sized exactly at the rule, sd(d theta) = 0.1 sigma_tot^design/(2 + z_{1 - 0.025}) (sigma_tot^design set from
    the efficiency-1 run's thinning variance, as a plan sizes the pair from it)."""
    q = S._q(r1["detections"], nominal)
    nb = {r["bin"]: r["emitted"] for r in m["form"]["bins"]}
    tot = float(sum(qi / nb[d[0]] for d, qi in zip(r1["detections"], q)))
    var = float(sum(qi * (1 - qi) / nb[d[0]] ** 2 for d, qi in zip(r1["detections"], q)))
    sd = math.sqrt(var) / tot
    z = float(stats.norm.ppf(1 - S.PAIR_ALPHA))
    cells = len(m["form"]["bins"]) * len(m["channels"])
    return {"J": [[1.0] * cells], "A": [[1.0 / tot]], "sigma_tot_design": [(1 + 1e-9) * sd * (S.SPREAD_MULTIPLIER + z) /
                                                                          S.DTHETA_FRACTION]}


def _codes(res) -> list:
    return sorted({f["code"] for f in res["findings"]})


def pde_exact_rep(kind: str, r: int) -> dict:
    j = PDE_EXACT.index(kind)
    seed = _int(3, r, j, 1)
    nominal = _nominal(kind)
    m, r1, rp, lines = _pair(seed, PDE_P0 if kind == "scale" else PF.pde_table())
    res = S.split_check(m, r1, rp, nominal, lines, pde_propagation(m, r1, nominal))
    return {"r": r, "passed": res["status"] == "passed", "codes": _codes(res), "p_value": res["p_value"],
            "dof": res["dof"], "dtheta_over_sd": res["dtheta"][0] / res["sd"][0] if res["sd"][0] else None,
            "sized": res["sizing"]["sized"]}


def pde_power_rep(rho: float, r: int) -> dict:
    j = 10 + PDE_RHO.index(rho)
    seed = _int(3, r, j, 1)
    nominal = _nominal("scale")
    m, r1, rp, lines = _pair(seed, PDE_P0, rho)
    prop = pde_propagation(m, r1, nominal)
    res = S.split_check(m, r1, rp, nominal, lines, prop)
    no_rows = S.split_check(m, r1, rp, nominal, None, prop)          # the chi2 and d theta parts without the rows
    return {"r": r, "rejected": res["status"] == "failed", "codes": _codes(res),
            "rejected_without_rows": no_rows["status"] == "failed", "codes_without_rows": _codes(no_rows),
            "chi2_p": no_rows["p_value"], "dtheta_over_bound": abs(no_rows["dtheta"][0]) / no_rows["bound"][0]}


def _grid(K: int) -> list:
    return [float(x) for x in np.linspace(2.0, 3.5, K + 1)]


def pde_replica_rep(r: int, R: int = PDE_R) -> dict:
    """One efficiency-1 mapping run (new seed) and, per grid size, R route-3 replicas: per bin the replica variance
    of sum_c eps_bc and the channel variances against the plug-in multinomial covariance and the analytic Dirichlet;
    the grid check's decision for the grid; the route-3 centre (for the between-map variance)."""
    seed = _int(3, r, 20, 1)
    ph, pr, emitted, detected = PF.run(PDE_PHOTONS, seed=seed, efficiency=1.0)
    m = PF.build_map(emitted, detected)
    run = S.binned(m, S.read_photons(ph), S.read_primaries(pr), PF.CENTRE)
    table = PF.pde_table()
    msha, psha = em.map_sha256(m), S.photons_sha256(ph.encode())
    out = {"r": r, "grids": {}}
    for K in PDE_GRIDS:
        grid = _grid(K)
        cat = S.route3_categories(m, run, table, grid)
        chk = S.grid_check(m, run, [table], grid)
        draws = [S.route3_replica(cat, S.replica_key(msha, psha, 1, i)) for i in range(1, R + 1)]
        per = []
        for b in sorted(cat["bins"]):
            x = np.array([dd[str(b)] for dd in draws])
            emp = np.atleast_2d(np.cov(x.T))
            mult = S.multinomial_covariance(cat, b)
            dirc = S.dirichlet_covariance(cat, b)
            one = np.ones(len(cat["channels"]))
            per.append({"bin": int(b), "sum_emp_over_mult": float(one @ emp @ one / (one @ mult @ one)),
                        "sum_emp_over_dirichlet": float(one @ emp @ one / (one @ dirc @ one)),
                        "sum_dirichlet_over_mult": float(S.variance_ratio(cat, b)),
                        "chan_emp_over_mult": (np.diag(emp) / np.diag(mult)).tolist(),
                        "corr_emp": float(emp[0, 1] / math.sqrt(emp[0, 0] * emp[1, 1])),
                        "corr_mult": float(mult[0, 1] / math.sqrt(mult[0, 0] * mult[1, 1]))})
        out["grids"][str(K)] = {"grid_check": chk["status"], "bins": per}
    out["centre"] = S.route3(m, run, table)["efficiencies"]
    return out


def pde_block(part: str, arg, r0: int, reps: int) -> list:
    f = {"exact": pde_exact_rep, "power": pde_power_rep}.get(part)
    if f:
        return [f(arg, r) for r in range(r0, r0 + reps)]
    return [pde_replica_rep(r) for r in range(r0, r0 + reps)]


def pde_judge(rows_by: dict, exact_reps: int = PDE_EXACT_REPS, power_reps: int = PDE_POWER_REPS,
              maps: int = PDE_MAPS) -> dict:
    out, ok = {"exact": {}, "power": {}, "replicas": {}}, True
    for key, rows in sorted(rows_by.items()):
        part, arg = key.split("|")
        n = len(rows)
        if part == "exact":
            k = sum(x["passed"] for x in rows)
            codes: dict = {}
            for x in rows:
                for c in x["codes"]:
                    codes[c] = codes.get(c, 0) + 1
            rec = {"reps": n, "pass_rate": k / max(n, 1), "pass_rate_cp95": clopper_pearson(k, n),
                   "failures_by_code": codes, "sized_fraction": float(np.mean([x["sized"] for x in rows])) if n
                   else None, "chi2_size": float(np.mean([x["p_value"] < S.CHI2_ALPHA for x in rows])) if n else None}
            rec["passed"] = bool(n >= exact_reps and k / n >= PDE_PASS_MIN)
            ok = ok and rec["passed"]
            out["exact"][arg] = rec
        elif part == "power":
            out["power"][arg] = {"reps": n, "power": float(np.mean([x["rejected"] for x in rows])) if n else None,
                                 "power_without_rows": float(np.mean([x["rejected_without_rows"] for x in rows]))
                                 if n else None,
                                 "chi2_power": float(np.mean([x["chi2_p"] < S.CHI2_ALPHA for x in rows])) if n
                                 else None,
                                 "dtheta_power": float(np.mean(["pde_split.dtheta" in x["codes_without_rows"]
                                                                for x in rows])) if n else None,
                                 "complete": n >= power_reps}
            ok = ok and n >= power_reps
        else:
            for K in PDE_GRIDS:
                recs = [x["grids"][str(K)] for x in rows]
                passing = [g for g in recs if g["grid_check"] == "passed"]
                vals = np.array([b["sum_emp_over_mult"] for g in passing for b in g["bins"]])
                allv = np.array([b["sum_emp_over_mult"] for g in recs for b in g["bins"]])
                dv = np.array([b["sum_emp_over_dirichlet"] for g in recs for b in g["bins"]])
                chan = np.array([c for g in recs for b in g["bins"] for c in b["chan_emp_over_mult"]])
                rec = {"maps": len(recs), "grid_check_pass_fraction": len(passing) / max(len(recs), 1),
                       "emp_over_mult_mean_where_grid_passes": float(vals.mean()) if vals.size else None,
                       "emp_over_mult_mean_all": float(allv.mean()) if allv.size else None,
                       "emp_over_dirichlet_mean": float(dv.mean()) if dv.size else None,
                       "emp_over_dirichlet_se": float(dv.std(ddof=1) / math.sqrt(dv.size)) if dv.size > 1 else None,
                       "chan_emp_over_mult_mean": float(chan.mean()) if chan.size else None,
                       "corr_difference_rms": float(np.sqrt(np.mean([(b["corr_emp"] - b["corr_mult"]) ** 2
                                                                     for g in recs for b in g["bins"]])))
                       if recs else None}
                rec["passed"] = bool(len(recs) >= maps and (not vals.size or vals.mean() >= PDE_VAR_MIN))
                rec["grid_check_consistent"] = bool(allv.size and (allv.mean() >= PDE_VAR_MIN) ==
                                                    (rec["grid_check_pass_fraction"] > 0.5))
                ok = ok and rec["passed"]
                out["replicas"][str(K)] = rec
            cen = np.array([[c for b in sorted(x["centre"], key=int) for c in x["centre"][b]] for x in rows])
            if len(cen) > 1:
                out["replicas"]["between_map_sd_relative"] = (cen.std(0, ddof=1) / cen.mean(0)).tolist()
    return {"calibration": "pde", "row": 2009, **out, "passed": bool(ok), "flags": FLAGS,
            "geant4": GEANT4_NOT_RUN,
            "rule": f"(a) under an exact split the split check passes in >= {PDE_PASS_MIN} of {exact_reps} nested "
                    "pairs "
                    "sized by the rule, for route 2_1 (scale) and route 3 (PDE(E) table); (b) power against a "
                    "reflectance tied to the PDE reported (no threshold); (c) for each grid size whose grid check "
                    f"passes, the mean route-3 replica variance (R = {PDE_R}) of sum_c eps_bc over the plug-in "
                    f"multinomial variance is >= {PDE_VAR_MIN} over {maps} maps"}


# ====================================================================== the task table, tasks and merge
def _tasks() -> list:
    t = []
    for H in P6_H:
        b = P6_BLOCK[H]
        t += [("p6", {"H": H, "r0": i, "reps": b}) for i in range(0, P6_REPS, b)]
    for n, s, m in th_configs():
        t += [("theta", {"n": n, "spacing": s, "seeding": m, "where": "interior", "r0": i, "reps": TH_BLOCK})
              for i in range(0, TH_REPS, TH_BLOCK)]
        t += [("theta", {"n": n, "spacing": s, "seeding": m, "where": "boundary", "r0": i,
                         "reps": min(TH_BLOCK, TH_CLOSURE_COUNT - i)}) for i in range(0, TH_CLOSURE_COUNT, TH_BLOCK)]
    for kind in PDE_EXACT:
        t += [("pde", {"part": "exact", "arg": kind, "r0": i, "reps": PDE_BLOCK["exact"]})
              for i in range(0, PDE_EXACT_REPS, PDE_BLOCK["exact"])]
    for rho in PDE_RHO:
        t += [("pde", {"part": "power", "arg": rho, "r0": i, "reps": PDE_BLOCK["power"]})
              for i in range(0, PDE_POWER_REPS, PDE_BLOCK["power"])]
    t += [("pde", {"part": "replicas", "arg": None, "r0": i, "reps": PDE_BLOCK["replicas"]})
          for i in range(0, PDE_MAPS, PDE_BLOCK["replicas"])]
    return t


TASKS = _tasks()


def _key(name: str, kw: dict) -> str:
    if name == "p6":
        return str(kw["H"])
    if name == "theta":
        return th_key(kw["n"], kw["spacing"], kw["seeding"])
    return f"{kw['part']}|{kw['arg']}"


def run_block(name: str, kw: dict) -> list:
    if name == "p6":
        return p6_block(kw["H"], kw["r0"], kw["reps"])
    if name == "theta":
        return th_block(kw["n"], kw["spacing"], kw["seeding"], kw["where"], kw["r0"], kw["reps"])
    return pde_block(kw["part"], kw["arg"], kw["r0"], kw["reps"])


def run_task(i: int, out_dir: Path, sizes: dict | None = None) -> dict:
    name, kw = TASKS[i]
    kw = {**kw, **(sizes or {})}
    t0 = time.time()
    rows = run_block(name, kw)
    rec = {"task": i, "family": name, "kwargs": kw, "key": _key(name, kw), "rows": rows,
           "seconds": time.time() - t0, "provenance": provenance(), "flags": FLAGS}
    out_dir.mkdir(parents=True, exist_ok=True)
    io.write_json(str(out_dir / f"task_{i:04d}.json"), io.jsonable(rec))
    return rec


def judge(by: dict, sizes: dict | None = None) -> dict:
    """The decisions from the rows grouped by family and key (sizes: the smoke sizes, else the registered ones)."""
    z = sizes or {}
    res = {}
    if "p6" in by:
        p6 = {}
        for H, rows in by["p6"].items():
            for v in P6_VEMU:
                p6[f"{H}|{v}"] = rows
        res["p6"] = p6_judge(p6, z.get("p6_reps", P6_REPS),
                             z.get("p6_max_false_alarms", P6_MAX_FALSE_ALARMS))
    if "theta" in by:
        res["theta"] = th_judge(by["theta"], z.get("th_reps", TH_REPS),
                                z.get("th_closure_count", TH_CLOSURE_COUNT))
    if "pde" in by:
        res["pde"] = pde_judge(by["pde"], z.get("pde_exact_reps", PDE_EXACT_REPS),
                               z.get("pde_power_reps", PDE_POWER_REPS), z.get("pde_maps", PDE_MAPS))
    return res


def merge(out_dir: Path, out: Path) -> dict:
    recs = {}
    for i in range(len(TASKS)):
        f = out_dir / f"task_{i:04d}.json"
        recs[i] = json.loads(f.read_text()) if f.exists() else None
    missing = [i for i, r in recs.items() if r is None]
    commits = {r["provenance"]["commit"] for r in recs.values() if r}
    dirty = any(r["provenance"].get("dirty") for r in recs.values() if r)
    by: dict = {}
    for r in recs.values():
        if r:
            by.setdefault(r["family"], {}).setdefault(r["key"], []).extend(r["rows"])
    results = judge(by)
    complete = not missing and len(commits) == 1 and not dirty
    rep = {"array": "phase-3 section 8.7 calibrations (rows 2004 P6, 2008, 2009)", "complete": complete,
           "missing_tasks": missing, "commits": sorted(c for c in commits if c), "dirty": dirty, "results": results,
           "passed": {k: v["passed"] for k, v in results.items()}, "provenance": provenance(), "flags": FLAGS,
           "seconds": {k: float(sum(r["seconds"] for r in recs.values() if r and r["family"] == k)) for k in by}}
    io.write_json(str(out), io.jsonable(rep))
    return rep


SMOKE = [("p6", {"H": 8, "r0": 900000, "reps": 2}),
         ("theta", {"n": 1_000_000, "spacing": 0.1, "seeding": "shared", "where": "interior", "r0": 900000,
                    "reps": 3}),
         ("theta", {"n": 1_000_000, "spacing": 0.1, "seeding": "shared", "where": "boundary", "r0": 900000,
                    "reps": 3}),
         ("pde", {"part": "exact", "arg": "scale", "r0": 900000, "reps": 2}),
         ("pde", {"part": "power", "arg": 0.25, "r0": 900000, "reps": 1})]
SMOKE_SIZES = {"p6_reps": 2, "p6_max_false_alarms": 0, "th_reps": 3, "th_closure_count": 3, "pde_exact_reps": 2,
               "pde_power_reps": 1,
               "pde_maps": 1}


def local(out: Path) -> dict:
    """Every family's code path at tiny sizes (the replica part with R = 20 on one map): label `smoke`, not evidence."""
    t0 = time.time()
    by: dict = {}
    for name, kw in SMOKE:
        by.setdefault(name, {}).setdefault(_key(name, kw), []).extend(run_block(name, kw))
    by["pde"]["replicas|None"] = [pde_replica_rep(900000, R=20)]
    rep = {"label": "smoke", "results": judge(by, SMOKE_SIZES), "seconds": time.time() - t0, "flags": FLAGS}
    io.write_json(str(out), io.jsonable(rep))
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--task", type=int)
    ap.add_argument("--merge")
    ap.add_argument("--local", dest="smoke", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    if args.list:
        print(json.dumps([{"task": i, "family": n, "key": _key(n, kw), **kw} for i, (n, kw) in enumerate(TASKS)]))
        return 0
    if not args.out:
        ap.error("--out is required with --task, --merge and --local")
    if args.task is not None:
        r = run_task(args.task, Path(args.out))
        print(json.dumps({"task": r["task"], "family": r["family"], "key": r["key"], "seconds": r["seconds"]}))
        return 0
    if args.merge:
        r = merge(Path(args.merge), Path(args.out))
        print(json.dumps({"complete": r["complete"], "passed": r["passed"], "missing": len(r["missing_tasks"])}))
        return 0 if r["complete"] and all(r["passed"].values()) else 1
    if args.smoke:
        r = local(Path(args.out))
        print(json.dumps({"label": "smoke", "seconds": r["seconds"],
                          "passed": {k: v["passed"] for k, v in r["results"].items()}}))
        return 0
    ap.error("one of --list, --task, --merge, --local")
    return 2


if __name__ == "__main__":
    sys.exit(main())
