"""The registered gate runs and section 8.7 calibrations of phase 2 of the simulator calibration workflow (task card
`docs/dev/simulator-calibration/simcal-tasks/phase-2.md`, "Thresholds and test designs"). Not a unit test module.

  python3 calibration_phase2_gates.py --gate segmented --out FILE [--smoke]     gate 2 on the toy detector

`--smoke` runs the same code path with tiny sizes to check it; its output is labeled `smoke` and is not evidence.
Every output records the commit and the SHA-256 of the files that decide it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from core.calibration import fit as F  # noqa: E402
from core.calibration import io  # noqa: E402
from core.calibration import likelihood as L  # noqa: E402
from core.calibration import propagate as P  # noqa: E402
from core.calibration import toy  # noqa: E402
from core.calibration import toy_problem as TP  # noqa: E402
from core.calibration import validate as V  # noqa: E402
from scipy import stats  # noqa: E402

FILES = ["core/calibration/" + f for f in ("likelihood.py", "fit.py", "propagate.py", "toy_problem.py", "toy.py",
                                            "reweight.py", "data/toy_detector_design.json")] + \
    ["tests/core/calibration_phase2_gates.py", "docs/dev/simulator-calibration/simcal-tasks/phase-2.md"]

# gate 2 (card): the calorimeter segment and the track / E-p segment of the toy detector
# the beam means measure exp(-t/lambda)(1 + eta) (pde and gain from the light-source and single-photoelectron runs), so
# the data determine the eta-phi correlation; the momentum scale is measured only through E/p (the track widths measure
# its product with the sum term), so theta2 depends on zeta and the regression choice of the export matters
CAL = [f"beam{e}_e_mean" for e in (1, 2, 3, 4)] + ["light_e_mean", "light_e_width", "spe_e_mean", "spe_e_width"]
TRK = ["track5_p_width", "track2_p_width", "eop_mean"]
THETA1 = ("pde", "gain")      # the light yield is not calibrated here: it would absorb the thickness exactly
THETA2 = ("momentum_scale", "sum_term_a")
PHI = {"material_thickness": (1.0, 0.05)}
ETA_R = 0.005                      # the fixture's common energy scale (relative), on the calorimeter energies and E/p
SEED_GATE2 = 20261140


def provenance() -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                                check=True, timeout=60).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", *FILES], cwd=ROOT, capture_output=True,
                                    text=True, timeout=60).stdout.strip())
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    return {"commit": commit, "dirty": dirty, "python": sys.version.split()[0], "numpy": np.__version__,
            "sha256": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES}}


def bounds_from_fixture():
    fx = json.loads((ROOT / "core/calibration/data/toy_detector_design.json").read_text())
    out = {}
    for p in fx["contract"]["parameters"]:
        if p["role"] == "theta":
            out[p["name"]] = {"bounds": tuple(p["physical_bounds"]), "prior": tuple(p["sampling_bounds"])}
    return out


def build(n):
    return toy.build_toy(n, "full")


def eta_spec(names):
    """The common energy scale of the beam measurement: on the beam energy means and E/p (not on the light-source and
    single-photoelectron charges, nor on the widths' photon statistics); with the thickness acting on the same means,
    the data determine the eta-phi posterior correlation (section 15.1)."""
    energy = [n for n in names if (n.startswith("beam") and n.endswith("_e_mean")) or n == "eop_mean"]
    return [{"relative": {n: ETA_R for n in energy}}]


def agree(a, Ca, b, Cb):
    """The gate-2 criteria (card): |delta theta_i| <= 0.1 sigma_i, |sigma ratio - 1| <= 0.1, correlations within 0.1."""
    sa, sb = np.sqrt(np.diag(Ca)), np.sqrt(np.diag(Cb))
    ra, rb = Ca / np.outer(sa, sa), Cb / np.outer(sb, sb)
    d = {"max_dtheta_over_sigma": float(np.max(np.abs(a - b) / sb)), "max_sigma_ratio_dev": float(np.max(np.abs(sa / sb - 1))),
         "max_corr_dev": float(np.max(np.abs(ra - rb)))}
    d["agree"] = d["max_dtheta_over_sigma"] <= 0.1 and d["max_sigma_ratio_dev"] <= 0.1 and d["max_corr_dev"] <= 0.1
    return d


class Segment2:
    """Segment 2 with theta1 = theta1-hat + G_xi xi + G_zeta (zeta - zeta-hat): xi and zeta as constrained phi_P (xi ~ N(0, I);
    zeta = (eta, phi) ~ the exported joint posterior N(zeta-hat, Sigma_zeta), the zeta prior not added again)."""

    def __init__(self, pkg, Gx, Gz, zmean, Sz, theta2_spec, exposure, mc, seeds, B):
        self.pkg = dict(theta_hat=pkg["theta_hat"], Gx=Gx, Gz=Gz, zmean=zmean)
        nx = Gx.shape[1]
        phi = {f"xi{i}": (0.0, 1.0) for i in range(nx)}
        phi["zeta_eta"] = (float(zmean[0]), float(np.sqrt(Sz[0, 0])))
        phi["zeta_phi"] = (float(zmean[1]), float(np.sqrt(Sz[1, 1])))
        self.nx = nx
        eta_rel = np.array([ETA_R if (n == "eop_mean") else 0.0 for n in TRK])
        th1 = list(THETA1)

        def map_params(d):
            xi = np.array([d[f"xi{i}"] for i in range(nx)])
            z = np.array([d["zeta_eta"], d["zeta_phi"]])
            t1 = self.pkg["theta_hat"] + Gx @ xi + Gz @ (z - zmean)
            params = {k: v for k, v in d.items() if k in THETA2}
            params.update(dict(zip(th1, t1)))
            params["material_thickness"] = z[1]
            return params, eta_rel * z[0]                      # log links: a relative shift r eta is r eta in link space
        self.problem = TP.ToyProblem(build, TRK, theta2_spec, exposure, mc, seeds[0], phi, None, None, B, seeds[1],
                                     map_params=map_params, thickness_by_yield=True)
        cov = np.zeros((nx + 2, nx + 2))
        cov[:nx, :nx] = np.eye(nx)
        cov[nx:, nx:] = Sz
        self.problem.phi_cov = lambda _c=cov: _c


def gate_segmented(out: Path, smoke: bool, probe: bool = False):
    """probe: the registered sizes with another seed (20262140), to design the configuration without the gate's data;
    labeled `probe`, not evidence."""
    t0 = time.time()
    exposure, mc, B = (400, 2000, 500) if smoke else (2000, 20000, 500)
    SEED = SEED_GATE2 + 1000 if probe else SEED_GATE2
    spec = bounds_from_fixture()
    th1 = {k: spec[k] for k in THETA1}
    th2 = {k: spec[k] for k in THETA2}
    seeds = (SEED, SEED + 1)
    joint = TP.ToyProblem(build, CAL + TRK, {**th1, **th2}, exposure, mc, seeds[0], PHI, eta_spec(CAL + TRK), None, B,
                          seeds[1], thickness_by_yield=True)
    truth = joint.initial_beta({**{k: toy.TOY_NOMINAL[k] for k in THETA1}, **{k: toy.TOY_NOMINAL[k] for k in THETA2}})
    rng = np.random.default_rng(SEED + 2)
    data = joint.simulate(truth, rng, nominal=False)          # the actual data: the analytic truth
    joint.data = data
    joint.sigma_noise = TP.estimate_sigma_noise(joint, truth)
    fj = F.find_extremum(joint, (SEED, 0), joint.initial_beta())
    # joint: theta order th1 + th2, then phi, then eta
    ij = list(range(len(THETA1) + len(THETA2)))
    bj, Cj = fj.beta[ij], fj.Sigma_beta[np.ix_(ij, ij)]
    # segment 1
    rows1 = [joint.names.index(n) for n in CAL]
    seg1 = TP.ToyProblem(build, CAL, th1, exposure, mc, seeds[0], PHI, eta_spec(CAL), None, B, seeds[1],
                         thickness_by_yield=True)
    seg1.data = L.Data(y_gauss=data.y_gauss[rows1], phi0=data.phi0, phi_cov=seg1.phi_cov(), eta0=data.eta0)
    seg1.sigma_noise = TP.estimate_sigma_noise(seg1, seg1.initial_beta())
    f1 = F.find_extremum(seg1, (SEED, 1), seg1.initial_beta())
    # beta of seg1: theta1, phi (1), eta (1): zeta = (eta, phi)
    n1 = len(THETA1)
    i_th, i_z = list(range(n1)), [n1 + 1, n1]
    pkg = P.export(f1.beta[i_th], f1.beta[i_z], f1.Sigma_beta, i_th, i_z, zeta_keys=["eta:energy_scale",
                                                                                     "phi:material_thickness"])
    rows2 = [joint.names.index(n) for n in TRK]

    def seg2_fit(Gx, Gz, zmean, Sz, label):
        s2 = Segment2(pkg, Gx, Gz, zmean, Sz, th2, exposure, mc, seeds, B)
        p2 = s2.problem
        p2.data = L.Data(y_gauss=data.y_gauss[rows2], phi0=np.r_[np.zeros(s2.nx), zmean], phi_cov=p2.phi_cov())
        p2.sigma_noise = TP.estimate_sigma_noise(p2, p2.initial_beta())
        f2 = F.find_extremum(p2, (SEED, 2, label), p2.initial_beta())
        nx = s2.nx
        # (theta2 (2), xi (nx), zeta (2)) -> (theta1, theta2)
        idx = list(range(2 + nx + 2))
        S = f2.Sigma_beta[np.ix_(idx, idx)]
        n1 = len(THETA1)
        T = np.zeros((n1 + 2, 2 + nx + 2))
        T[:n1, 2:2 + nx] = Gx
        T[:n1, 2 + nx:] = Gz
        T[n1, 0] = T[n1 + 1, 1] = 1.0
        xi = f2.beta[2:2 + nx]
        z = f2.beta[2 + nx:2 + nx + 2]
        t1 = pkg["theta_hat"] + Gx @ xi + Gz @ (z - zmean)
        return np.r_[t1, f2.beta[:2]], T @ S @ T.T, f2
    seg, Cs, f2 = seg2_fit(pkg["G_xi"], pkg["G_zeta"], pkg["zeta_hat"], pkg["Sigma_zeta"], 0)
    res = {"joint_posterior": agree(seg, Cs, bj, Cj)}
    sp, Cp, fp = seg2_fit(pkg["G_xi"], pkg["G_zeta"], np.zeros(2) + np.array([0.0, 1.0]), np.diag([1.0, 0.05 ** 2]),
                         1)
    res["counterexample_prior"] = agree(sp, Cp, bj, Cj)
    Gm = P.marginal_regressions(f1.Sigma_beta, i_th, [i_z[0]], [i_z[1]])
    D = np.diag(np.diag(f1.Sigma_beta)[i_z])
    sm, Cm, fm = seg2_fit(pkg["G_xi"], Gm, pkg["zeta_hat"], D, 2)
    res["counterexample_marginal"] = agree(sm, Cm, bj, Cj)
    passed = res["joint_posterior"]["agree"] and not res["counterexample_prior"]["agree"] and \
        not res["counterexample_marginal"]["agree"] and fj.converged and f1.converged and f2.converged and \
        fp.converged and fm.converged            # a counterexample violates only through a converged fit (F12)
    rep = {"gate": "segmented calibration and the joint fit agree", "status": "passed" if passed else "failed",
           "smoke": smoke, "probe": probe, "label": "smoke (not evidence)" if smoke else ("probe (not evidence)" if probe else "synthetic"), "results": res,
           "converged": {"joint": fj.converged, "segment1": f1.converged, "segment2": f2.converged,
                         "counterexample_prior": fp.converged, "counterexample_marginal": fm.converged},
           "joint": {"theta": bj.tolist(), "cov": Cj.tolist()}, "segmented": {"theta": seg.tolist(), "cov": Cs.tolist()},
           "sizes": {"exposure": exposure, "mc_events": mc, "B": B}, "seed": SEED,
           "eta_phi_correlation": float(pkg["Sigma_zeta"][0, 1] / np.sqrt(pkg["Sigma_zeta"][0, 0] *
                                                                          pkg["Sigma_zeta"][1, 1])),
           "seconds": time.time() - t0, "provenance": provenance()}
    io.write_json(str(out), io.jsonable(rep))
    return rep


# ------------------------------------------------------------------ section 8.7 calibrations (card, calibrations 1-15)
def cal_seed(c: int, r: int) -> int:
    """Seeds 20261120 + 1e5 c + r (card): no stream shared between calibrations or repetitions."""
    return 20261120 + 100_000 * c + r


def _spd(k, rng):
    A = rng.normal(size=(k, k))
    return A @ A.T / k + np.eye(k)


def cal13_chat(reps: int = 2000) -> dict:
    """Calibration 13: n = max(500, 10k) toys for C-hat_r, k in {5, 20, 60}; the median over repetitions of
    e^T C-hat^+ e (n - k - 2)/(n - 1) / e^T C^+ e within 1 +- 10%."""
    from core.calibration import validate as V
    out = {}
    for k in (5, 20, 60):
        rng0 = np.random.default_rng(cal_seed(13, k))
        C = _spd(k, rng0)
        s = np.sqrt(np.diag(C))
        e = rng0.normal(size=k)
        ref = float(e @ np.linalg.solve(C, e))
        n = V.chat_min_toys(k)
        L_ = np.linalg.cholesky(C)
        ratios = []
        for r in range(reps):
            rng = np.random.default_rng([cal_seed(13, k), r])
            R = rng.normal(size=(n, k)) @ L_.T
            est = V.estimate_c_r(R, s, [])
            ratios.append(float(e @ est["C_plus"] @ e) * est["factor"] / ref)
        med = float(np.median(ratios))
        out[str(k)] = {"n": n, "median": med, "passed": abs(med - 1) <= 0.10, "mean": float(np.mean(ratios))}
    return {"calibration": 13, "row": 2016, "results": out, "passed": all(v["passed"] for v in out.values()),
            "reps": reps}


def cal14_lower_bound(reps: int = 2000, R: int = 50) -> dict:
    """Calibration 14: known lambda_a in {5, 12.8, 30}, V_Delta / C_r in {0.03, 0.1, 0.3, 1}, R = 50 MC repetitions
    per bound, normal-approximation quantile; levels 1 - alpha_P/(2m) and 1 - alpha_P/m for m = 1, 2; the bound lies
    below the true lambda with frequency >= level - 3 binomial standard errors."""
    from core.calibration import validate as V
    k = 5
    levels = sorted({1 - 0.05 / (2 * m) for m in (1, 2)} | {1 - 0.05 / m for m in (1, 2)})
    out = {}
    for lam in (5.0, 12.8, 30.0):
        for vr in (0.03, 0.1, 0.3, 1.0):
            e = np.zeros(k)
            e[0] = np.sqrt(lam)
            Cp = np.eye(k)
            sd = np.sqrt(vr)
            below = {lv: 0 for lv in levels}
            for r in range(reps):
                rng = np.random.default_rng([cal_seed(14, int(lam * 10)), int(vr * 100), r])
                e1 = e + rng.normal(size=(R, k)) * sd
                e2 = e + rng.normal(size=(R, k)) * sd
                cr = np.einsum("ri,ij,rj->r", e1, Cp, e2)
                for lv in levels:
                    below[lv] += V.lambda_lower_bound(cr, lv) < lam
            for lv in levels:
                f = below[lv] / reps
                se = np.sqrt(lv * (1 - lv) / reps)
                out[f"lambda={lam},VD={vr},level={lv:.4f}"] = {"frequency": f, "passed": f >= lv - 3 * se}
    return {"calibration": 14, "row": 2017, "results": out, "passed": all(v["passed"] for v in out.values()),
            "reps": reps, "R": R}


def cal3_lambda(reps: int = 2000) -> dict:
    """Calibration 3: lambda_a in {5, 12.8, 30}, k = 5, V_Delta / C_r in {0.03, 0.1, 0.3}: the cross product's mean
    within lambda +- 2% or 3 standard errors (the larger); the single-set estimate biased high by tr(C^+ V_Delta) within
    3 standard errors; single set minus the trace reported."""
    from core.calibration import validate as V
    k = 5
    out = {}
    for lam in (5.0, 12.8, 30.0):
        for vr in (0.03, 0.1, 0.3):
            e = np.zeros(k)
            e[0] = np.sqrt(lam)
            Cp, VD = np.eye(k), np.eye(k) * vr
            rng = np.random.default_rng([cal_seed(3, int(lam * 10)), int(vr * 100)])
            e1 = e + rng.normal(size=(reps, k)) * np.sqrt(vr)
            e2 = e + rng.normal(size=(reps, k)) * np.sqrt(vr)
            cr = np.array([V.cross_lambda(a, b, Cp) for a, b in zip(e1, e2)])
            sg = np.array([V.single_lambda(a, Cp) for a in e1])
            sc = np.array([V.single_lambda(a, Cp, VD) for a in e1])
            tol = max(0.02 * lam, 3 * cr.std(ddof=1) / np.sqrt(reps))
            bias, tb = sg.mean() - lam, float(np.trace(Cp @ VD))
            out[f"lambda={lam},VD={vr}"] = {
                "cross_mean": float(cr.mean()), "cross_ok": bool(abs(cr.mean() - lam) <= tol),
                "single_bias": float(bias), "trace": tb,
                "single_ok": bool(abs(bias - tb) <= 3 * sg.std(ddof=1) / np.sqrt(reps)),
                "single_minus_trace_mean": float(sc.mean())}
    return {"calibration": 3, "row": 2002, "results": out,
            "passed": all(v["cross_ok"] and v["single_ok"] for v in out.values()), "reps": reps}


def cal5_g7(reps: int = 1000) -> dict:
    """Calibration 5: d = 3, K = 10 and 5, V_MC correct, underestimated by 2 and by 3; false-alarm rate with a
    correct V_MC <= 2 alpha (<= 34 of 1000 at alpha = 0.01, using 2 alpha + 3 se as the card's count); detection at
    K = 10, factor 3, >= 0.9; the others reported."""
    from core.calibration import toys_linear as T
    cfg = T.linear_config(n=20, d=3, mc_ratio=0.1, seed=cal_seed(5, 0) % 2 ** 31)
    out = {}
    for K in (10, 5):
        for factor in (1.0, 2.0, 3.0):
            det = 0
            for r in range(reps):
                p0 = T.make(cfg, [0.5, -0.3, 1.0], data_seed=cal_seed(5, 1) + r, mc_seed=cal_seed(5, 2) + r)
                f0 = F.iterate(p0, T.initial_beta(p0), lndet=False)
                th = []
                for k in range(K):
                    p = T.LinearProblem(cfg, mc_seed=cal_seed(5, 3) + 100 * r + k, data=p0.data)
                    th.append(F.iterate(p, T.initial_beta(p), lndet=False).beta[:3])
                det += F.g7(np.array(th), F.sigma_mc(p0, f0, cfg.V_MC / factor))["status"] == "failed"
            out[f"K={K},factor={factor}"] = det / reps
    ok = out["K=10,factor=1.0"] <= 0.034 and out["K=5,factor=1.0"] <= 0.034 and out["K=10,factor=3.0"] >= 0.9
    return {"calibration": 5, "row": 2005, "rates": out, "passed": ok, "reps": reps}


def cal7_bj(reps: int = 10_000) -> dict:
    """Calibration 7: the linear Gaussian configuration with MC noise varying with theta (e = e0 (1 + g theta)),
    scaled so that max_i |b_J,i| / sigma_tot,i = 0.05, 0.10, 0.15, 0.25; >= 10^4 repetitions per point; the extra
    68% and 95% undercoverage of the interval +-z sigma_tot relative to the same configuration with K_l = 0 is <= 0.01
    at and below the bound (0.10 by approval A9)."""
    from core.calibration import design_noise as DN
    from core.calibration import toys_linear as T
    rng0 = np.random.default_rng(cal_seed(7, 0))
    base = T.linear_config(n=20, d=2, mc_ratio=0.1, seed=int(cal_seed(7, 1) % 2 ** 31))
    g0 = rng0.normal(size=(20, 2))
    truth = np.array([0.5, -0.3])
    W = np.linalg.inv(base.V_data + base.V_MC)
    st = np.sqrt(np.diag(np.linalg.inv(base.J.T @ W @ base.J)))

    def bj_ratio(scale):                     # with V_MC at the truth (the toy recomputes it at theta_ref, e19bfc76)
        g = g0 * scale
        Dg = 1 + g @ truth
        Wt = np.linalg.inv(base.V_data + base.V_MC * np.outer(Dg, Dg))
        stt = np.sqrt(np.diag(np.linalg.inv(base.J.T @ Wt @ base.J)))
        Ks = [np.diag(g[:, l]) @ base.V_MC @ np.diag(Dg) for l in range(2)]
        return float(np.max(np.abs(DN.b_J(base.J, Wt, Ks)) / stt))

    def coverage(scale, label):
        cfg = T.linear_config(n=20, d=2, mc_ratio=0.1, seed=int(cal_seed(7, 1) % 2 ** 31))
        cfg.e_scale = g0 * scale if scale else None
        c68 = c95 = 0
        for r in range(reps):
            p = T.make(cfg, truth, data_seed=cal_seed(7, 2) + r, mc_seed=cal_seed(7, 3) + r)
            f = F.iterate(p, T.initial_beta(p), lndet=False)
            z = np.abs(f.beta[:2] - truth) / f.sigma_tot
            c68 += np.mean(z <= 1.0)
            c95 += np.mean(z <= 1.96)
        return c68 / reps, c95 / reps
    from scipy import optimize
    c0 = coverage(0.0, "K0")
    out = {"K_l=0": {"cover68": c0[0], "cover95": c0[1]}}
    ok = True
    for target in (0.05, 0.10, 0.15, 0.25):
        sc = optimize.brentq(lambda s: bj_ratio(s) - target, 1e-6, 50.0)
        cv = coverage(sc, str(target))
        d68, d95 = c0[0] - cv[0], c0[1] - cv[1]
        out[f"bJ={target}"] = {"scale": sc, "cover68": cv[0], "cover95": cv[1], "extra_under68": d68,
                              "extra_under95": d95}
        if target <= DN.BJ_BOUND + 1e-12 and (d68 > 0.01 or d95 > 0.01):
            ok = False
    return {"calibration": 7, "row": 2007, "results": out, "passed": ok, "reps": reps}


def cal9_rounding(reps: int = 10_000) -> dict:
    """Calibration 9 (section 8.7 note 2): validation pairs with correlation |c| = 1 - 25 r^2 (both signs) for
    r = rho / sigma in {0.02, 0.05, 0.1, 0.15, 0.2}, the release rounding the data to its grid with the true values
    uniform on the grid, C_r = C + diag(rho^2 / 12), T_v against chi2_2: size within alpha +- 25%; and a single observable
    with sigma / rho from 0.1 to 10: sizes reported, judged where the condition holds (sigma / rho >= 5). The
    deterministic items of note 2 are unit tests (test_calibration_data_checks.Rounding)."""
    from core.calibration import validate as V
    alpha = 0.05
    out, ok = {}, True
    crit2, crit1 = stats.chi2.ppf(1 - alpha, 2), stats.chi2.ppf(1 - alpha, 1)
    for r in (0.02, 0.05, 0.1, 0.15, 0.2):
        for sgn in (1, -1):
            c = sgn * (1 - 25 * r * r)
            C = np.array([[1.0, c], [c, 1.0]])
            rho = r
            Cr = C + np.eye(2) * rho * rho / 12
            Cp, _ = V.c_r_plus(Cr, np.ones(2), [])
            rng = np.random.default_rng([cal_seed(9, 1), int(r * 1000), sgn + 1])
            mu = rng.uniform(0, rho, size=(reps, 2))                 # true values uniform on the grid
            y = mu + rng.multivariate_normal(np.zeros(2), C, size=reps)
            yr = np.round(y / rho) * rho
            res = yr - mu
            size = float(np.mean(np.einsum("ni,ij,nj->n", res, Cp, res) > crit2))
            good = abs(size - alpha) <= 0.25 * alpha
            ok &= good
            out[f"pair r={r},c={c:+.4f}"] = {"size": size, "ok": good}
    for ratio in (0.1, 0.3, 1.0, 3.0, 5.0, 10.0):
        rho = 1.0 / ratio
        rng = np.random.default_rng([cal_seed(9, 2), int(ratio * 100)])
        mu = rng.uniform(0, rho, reps)
        y = np.round((mu + rng.normal(size=reps)) / rho) * rho
        size = float(np.mean((y - mu) ** 2 / (1 + rho * rho / 12) > crit1))
        holds = rho <= 0.2 + 1e-12
        good = (abs(size - alpha) <= 0.25 * alpha) if holds else None
        if holds:
            ok &= good
        out[f"single sigma/rho={ratio}"] = {"size": size, "condition_holds": holds, "ok": good}
    return {"calibration": 9, "row": 2012, "results": out, "passed": bool(ok), "reps": reps}


def cal12_replica(reps: int = 10_000, n_ref: int = 20_000) -> dict:
    """Calibration 12 (section 8.7 note 4, size of T_v): holdout on the linear toy, V_MC / V_data in {0.03, 0.1, 0.3, 1},
    k in {5, 20}, d = 2, the truth without MC noise; T_v with the analytic C_r (V_vv incl. V_MC, propagation) calibrated
    by replica-difference toys (truth = the nominal MC prediction at the fit point, the toy's own replica difference
    (m_a - m_b)/sqrt(2) on both predictions). In the linear Gaussian configuration the toy residual's law does not
    depend on the data or on e_nom, so one reference of n_ref toys per configuration is used for every repetition
    (equivalent in law to regenerating 500 per repetition). Rule: size within alpha +- 25%. Negative control: nominal as
    truth with a single replica as prediction (size too small, about 0.025)."""
    from core.calibration import toys_linear as T
    from core.calibration import validate as V
    alpha = 0.05
    out, ok = {}, True
    for k in (5, 20):
        for ratio in (0.03, 0.1, 0.3, 1.0):
            rng0 = np.random.default_rng([cal_seed(12, 0), k, int(ratio * 100)])
            n, d = 12, 2
            J = rng0.normal(size=(n, d))
            Jv = rng0.normal(size=(k, d))
            Vd, Vdv = np.eye(n), np.eye(k)
            Vm, Vmv = Vd * ratio, Vdv * ratio
            W = np.linalg.inv(Vd + Vm)
            Sig = np.linalg.inv(J.T @ W @ J)
            A = Sig @ J.T @ W
            Cr = Vdv + Vmv + Jv @ Sig @ Jv.T
            Cp, _ = V.c_r_plus(Cr, np.sqrt(np.diag(Vdv)), [])

            def residual(rng, single=False):
                # data from the truth (toys: the nominal MC prediction at the truth point); prediction = nominal + pert
                e_c = rng.multivariate_normal(np.zeros(n), Vm)
                e_v = rng.multivariate_normal(np.zeros(k), Vmv)
                yc = rng.multivariate_normal(np.zeros(n), Vd)
                yv = rng.multivariate_normal(np.zeros(k), Vdv)
                return yc, yv, e_c, e_v

            def tv(rv):
                return float(rv @ Cp @ rv)
            # reference: replica-difference toys (true value m_nom, prediction m_nom + (m_a - m_b)/sqrt 2)
            ref, ref_single = [], []
            rng = np.random.default_rng([cal_seed(12, 1), k, int(ratio * 100)])
            for _ in range(n_ref):
                yc, yv, _, _ = residual(rng)
                pc = (rng.multivariate_normal(np.zeros(n), Vm) - rng.multivariate_normal(np.zeros(n), Vm)) / np.sqrt(2)
                pv = (rng.multivariate_normal(np.zeros(k), Vmv) - rng.multivariate_normal(np.zeros(k), Vmv)) / np.sqrt(2)
                th = A @ (yc - pc)
                ref.append(tv(yv - pv - Jv @ th))
                sc = rng.multivariate_normal(np.zeros(n), Vm)        # single replica as prediction, nominal as truth
                sv = rng.multivariate_normal(np.zeros(k), Vmv)
                en_c = rng.multivariate_normal(np.zeros(n), Vm)
                en_v = rng.multivariate_normal(np.zeros(k), Vmv)
                th2 = A @ (yc + en_c - sc)
                ref_single.append(tv(yv + en_v - sv - Jv @ th2))
            ref, ref_single = np.sort(ref), np.sort(ref_single)
            rej = rej_s = 0
            rng = np.random.default_rng([cal_seed(12, 2), k, int(ratio * 100)])
            for _ in range(reps):
                yc, yv, e_c, e_v = residual(rng)            # actual data: analytic truth; nominal MC noise e_nom
                th = A @ (yc - e_c)
                T_obs = tv(yv - e_v - Jv @ th)
                p = (np.sum(ref >= T_obs) + 1) / (ref.size + 1)
                ps = (np.sum(ref_single >= T_obs) + 1) / (ref_single.size + 1)
                rej += p <= alpha
                rej_s += ps <= alpha
            size, size_s = rej / reps, rej_s / reps
            good = abs(size - alpha) <= 0.25 * alpha
            ok &= good
            out[f"k={k},VMC/Vdata={ratio}"] = {"size": size, "ok": good, "control_single_replica": size_s}
    return {"calibration": 12, "row": 2015, "results": out, "passed": bool(ok), "reps": reps, "n_ref": n_ref}


CALS = {"rounding": cal9_rounding, "replica": cal12_replica, "chat": cal13_chat, "lambda-bound": cal14_lower_bound, "lambda": cal3_lambda, "g7": cal5_g7, "bj": cal7_bj}


# ------------------------------------------------------------------ gate 3: the negative tests of P8 and G9 (card)
SEED_GATE3 = 20261150


def gate_shift(out: Path) -> dict:
    """Gate 3 as registered: each case with seeds 20261150 + case index (data) and + 100 (MC); linear toy n = 20,
    d = 3, truth (0.5, -0.3, 1.0); the shift phi orthogonal to the theta columns with information as stated."""
    from core.calibration import shift as Sh
    from core.calibration import toys_linear as T
    truth = [0.5, -0.3, 1.0]

    def orth(J, seed):
        Q, _ = np.linalg.qr(np.c_[J, np.random.default_rng(seed).normal(size=(J.shape[0], 1))])
        return Q[:, J.shape[1]]

    def cfg(i, info, resp=None, dep=False):
        c = T.linear_config(n=20, d=3, seed=SEED_GATE3 + i)
        o = orth(c.J, SEED_GATE3 + 50 + i)
        c.phi_cols = (np.sqrt(info) * o)[:, None]
        if dep:
            c.phi_resp = lambda ph, tp, _o=o, _s=np.sqrt(info): _o * _s * 0.6 * tp[0] * ph[0]
        elif resp is not None:
            c.phi_resp = resp(c)
        return c

    def make(c, i, th=truth):
        return T.make(c, th, data_seed=SEED_GATE3 + i, mc_seed=SEED_GATE3 + 100 + i)

    cases = []
    for i, (info, want) in enumerate(((0.3, "failed"), (0.05, "passed"))):
        p = make(cfg(i, info), i)
        r = Sh.p8(p, T.initial_beta(p))
        cases.append({"case": f"P8 information {info}", "expected": want, "observed": r["status"],
                      "lambda_max": r["lambda_max"], "ok": r["status"] == want})

    def response(kind):
        def build(c):
            p0 = T.make(c, truth, data_seed=1, mc_seed=1)
            b = 2.0 * F.iterate(p0, T.initial_beta(p0)).sigma_tot[0]
            J0 = c.J[:, 0].copy()
            f = {"expansive": lambda ph: -J0 * b * (ph[0] + 0.3 * ph[0] ** 3 / 6),
                 "quadratic": lambda ph: -J0 * b * (ph[0] + 0.25 * ph[0] ** 2),
                 "compressive": lambda ph: -J0 * b * (ph[0] - 0.3 * ph[0] ** 3 / 6)}[kind]
            return f
        return build
    for j, (kind, want, code) in enumerate((("expansive", "failed", "g9.linearity"),
                                            ("quadratic", "failed", "g9.linearity"),
                                            ("compressive", "passed", None))):
        i = 2 + j
        p = make(cfg(i, 0.05, response(kind)), i)
        r = Sh.g9(p, F.iterate(p, T.initial_beta(p)), Sh.p8(p, T.initial_beta(p)), seed=SEED_GATE3 + i)
        cases.append({"case": f"G9 {kind} response", "expected": want, "observed": r["status"], "Delta": r.get("Delta"),
                      "ok": r["status"] == want and (code is None or code in r.get("findings", []))})
    i = 5
    p = make(cfg(i, 0.09, dep=True), i, [1.0, -0.3, 1.0])
    p8 = Sh.p8(p, T.initial_beta(p))
    r = Sh.g9(p, F.iterate(p, T.initial_beta(p)), p8, seed=SEED_GATE3 + i)
    cases.append({"case": "G9 condition 1 at theta-hat (1.5c)", "expected": "failed", "p8": p8["status"],
                  "observed": r["status"], "lambda_at_fit": r.get("lambda_max_at_fit"),
                  "ok": p8["status"] == "passed" and "g9.information" in r.get("findings", [])})
    i = 6
    q = make(cfg(i, 0.05), i)
    fq = F.iterate(q, T.initial_beta(q))
    base = q.h_shift
    q.h_shift = lambda tp, ph: base(tp, ph) if abs(ph[0]) < 1.5 else np.full_like(base(tp, ph), np.nan)
    r = Sh.g9(q, fq, Sh.p8(q, T.initial_beta(q)), seed=SEED_GATE3 + i)
    cases.append({"case": "G9 refit not converged", "expected": "failed", "observed": r["status"],
                  "ok": r.get("finding") == "g9.refit_not_converged"})
    p = make(cfg(0, 0.3), 0)
    r = Sh.g9(p, F.iterate(p, T.initial_beta(p)), Sh.p8(p, T.initial_beta(p)))
    cases.append({"case": "G9 not decided after P8 failed", "expected": "not-decided", "observed": r["status"],
                  "ok": r["status"] == "not-decided"})
    passed = all(c["ok"] for c in cases)
    rep = {"gate": "the negative tests of P8, G9", "status": "passed" if passed else "failed", "cases": cases,
           "provenance": provenance(), "label": "synthetic"}
    io.write_json(str(out), io.jsonable(rep))
    return rep


# ------------------------------------------------------------------ gate 1: toy-detector negatives (card item 1)
SEED_GATE1 = 20261130


def _toy_p3(names, theta_names, i, modes=None, exposure=2000, mc=20000):
    from core.calibration import identify as I
    spec = bounds_from_fixture()
    th = {k: spec[k] for k in theta_names}
    p = TP.ToyProblem(build, names, th, exposure, mc, SEED_GATE1 + i, None, None, None, None, SEED_GATE1 + 100 + i)
    p.degeneracy_modes = modes or []
    b = p.initial_beta()
    p.data = p.asimov(b)
    return I.p3(p, b)


def gate1_toy_p3() -> list:
    """P3 on the toy detector at Asimov data, prior centre (section 15.3.1, 15.2, 15.3.18)."""
    widths = [f"beam{e}_e_width" for e in (1, 2, 3, 4)]
    means = [f"beam{e}_e_mean" for e in (1, 2, 3, 4)]
    thin = [{"mode": "binomial thinning chain", "parameters": ["light_yield", "pde"],
             "signal": "inject a reference with a known photon count between photon generation and PDE"}]
    gain = [{"mode": "Poisson stage x subsequent gain", "parameters": ["light_yield", "gain", "enf"],
             "signal": "the single-photoelectron spectrum"}]
    common = [{"mode": "common mode of redundant measurements", "parameters": ["relative_gain_b", "gain"],
               "signal": "another reference acting on a single branch"}]
    out = []
    r = _toy_p3(widths + means, ("light_yield", "pde"), 1, thin)
    out.append({"case": "P3 yield x PDE, widths and means, no photon source", "expected": "failed", "observed": r["status"],
                "hint": [h["mode"] for h in r.get("hints", [])], "ok": r["status"] == "failed"})
    r = _toy_p3(widths + means + ["light_e_mean", "light_e_width"], ("light_yield", "pde"), 2, thin)
    out.append({"case": "P3 yield x PDE with the photon source", "expected": "passed", "observed": r["status"],
                "ok": r["status"] == "passed"})
    r = _toy_p3(widths + means, ("light_yield", "gain", "enf"), 3, gain)
    out.append({"case": "P3 Poisson x gain, free fluctuation (ENF), no single-photoelectron spectrum",
                "expected": "failed", "observed": r["status"], "hint": [h["mode"] for h in r.get("hints", [])],
                "ok": r["status"] == "failed"})
    r = _toy_p3(widths + means + ["spe_e_mean", "spe_e_width", "light_e_mean", "light_e_width"],
                ("light_yield", "gain", "enf"), 4, gain)
    out.append({"case": "P3 Poisson x gain with the single-photoelectron spectrum and the light source (the light source "
                        "fixes the gain to the precision of 400 photons; the spectrum alone measures it to ~1.4%, "
                        "leaving the yield-gain correlation near -0.99)", "expected": "passed",
                "observed": r["status"], "ok": r["status"] == "passed"})
    ratios = [f"beam{e}_ratio_mean" for e in (1, 2, 3, 4)]
    r = _toy_p3(ratios, ("relative_gain_b", "gain"), 5, common)
    out.append({"case": "P3 redundant modules: the energy ratio, common gain scale", "expected": "failed",
                "observed": r["status"], "hint": [h["mode"] for h in r.get("hints", [])],
                "ok": r["status"] == "failed" and any(h["mode"] == "common mode of redundant measurements"
                                                      for h in r.get("hints", []))})
    return out


# ------------------------------------------------------------------ gate 1: event samples conditioned on N_tot,s (item 11)
def _alr(counts):
    from core.calibration import likelihood as Lk
    return Lk.shape_summary(counts, Lk.logratio_matrix(len(counts), "alr"))


def _rate(pvals, alpha=0.05):
    return float(np.mean(np.asarray(pvals) <= alpha))


def gate1_event_samples(reps: int = 2000, B: int = 500, n_toys: int = 500, seed: int = SEED_GATE1 + 60) -> list:
    """The section 15.3.7 size cases with a bootstrap conditioned on N_tot,s; each with its negative control."""
    from core.calibration import validate as V
    out = []
    # (i) true normalization omega = 0.5: N_tot,s observed = 400 while N_decl = 800; K = 3 shape + efficiency
    P_BIN, EPS = np.array([0.5, 0.3, 0.2]), 0.7

    def gun(n, rng):
        N = int(sum(n))
        passed = rng.random(N) < EPS
        k = rng.multinomial(int(passed.sum()), P_BIN)
        return np.r_[_alr(k), passed.mean() if N else 0.0]

    def size_case(cond_n, data_n, label, reps_):
        pv = []
        for r in range(reps_):
            rng = np.random.default_rng([seed, zlib.crc32(label.encode()), r])   # deterministic per label (F9)
            y = gun(data_n(rng), rng)
            n_c = cond_n(y, rng)
            sets = V.conditioned_sets(gun, n_c, B, (seed, r, 1))
            toys = V.conditioned_sets(gun, n_c, n_toys, (seed, r, 2))
            pv.append(V.toy_calibrated_pvalue(y, sets.mean(0), np.cov(sets, rowvar=False), toys))
        return _rate(pv)
    ok_rate = size_case(lambda y, rng: [400], lambda rng: [400], "omega-ok", reps)
    # negative control: the bootstrap generated with N_decl = 800 events (omega = 1) while the toys follow the data
    pv = []
    for r in range(reps):
        rng = np.random.default_rng([seed, 7, r])
        y = gun([400], rng)
        sets = V.conditioned_sets(gun, [800], B, (seed, r, 3))
        toys = V.conditioned_sets(gun, [400], n_toys, (seed, r, 4))
        Ci = np.linalg.pinv(np.cov(sets, rowvar=False))
        c = sets.mean(0)
        T = lambda v: float((v - c) @ Ci @ (v - c))  # noqa: E731
        pv.append(float(stats.chi2.sf(T(y), 3)))      # the omega = 1 covariance used as if it were the data's
    out.append({"case": "omega = 0.5: bootstrap conditioned on N_tot,s", "size": ok_rate,
                "ok": abs(ok_rate - 0.05) <= 0.0125, "control_size_omega1": _rate(pv),
                "control_ok": _rate(pv) > 0.0625})

    # (ii) particle gun: the shape and the efficiency of the same events, conditioned on N_tot,s; the negative control
    # conditions the toys on the shape's own passing count N_pass (the efficiency direction then has no variance)
    def gun_npass(n_pass, n_tot):
        def f(_n, rng):
            k = rng.multinomial(n_pass, P_BIN)
            return np.r_[_alr(k), n_pass / n_tot]
        return f
    pv_ok, pv_np = [], []
    for r in range(reps):
        rng = np.random.default_rng([seed, 11, r])
        y = gun([400], rng)
        n_pass = int(round(y[-1] * 400))
        sets = V.conditioned_sets(gun, [400], B, (seed, r, 5))
        toys = V.conditioned_sets(gun, [400], n_toys, (seed, r, 6))
        pv_ok.append(V.toy_calibrated_pvalue(y, sets.mean(0), np.cov(sets, rowvar=False), toys))
        sets2 = V.conditioned_sets(gun_npass(n_pass, 400), [400], B, (seed, r, 7))[:, :-1]
        toys2 = V.conditioned_sets(gun_npass(n_pass, 400), [400], n_toys, (seed, r, 8))[:, :-1]
        pv_np.append(V.toy_calibrated_pvalue(y[:-1], sets2.mean(0), np.cov(sets2, rowvar=False), toys2))
    a = _rate(pv_ok)
    # power at an efficiency bias of 3.2 sigma (section 15.3.7: >= 0.6 conditioned on N_tot,s); conditioned on N_pass the
    # efficiency direction has no variance in the toys and drops out, so the bias is not seen (negative control)
    eps_b = EPS + 3.2 * np.sqrt(EPS * (1 - EPS) / 400)
    pw_ok, pw_np = [], []
    for r in range(reps):
        rng = np.random.default_rng([seed, 12, r])
        passed = rng.random(400) < eps_b
        y = np.r_[_alr(rng.multinomial(int(passed.sum()), P_BIN)), passed.mean()]
        n_pass = int(passed.sum())
        sets = V.conditioned_sets(gun, [400], B, (seed, r, 13))
        toys = V.conditioned_sets(gun, [400], n_toys, (seed, r, 14))
        pw_ok.append(V.toy_calibrated_pvalue(y, sets.mean(0), np.cov(sets, rowvar=False), toys))
        sets2 = V.conditioned_sets(gun_npass(n_pass, 400), [400], B, (seed, r, 15))[:, :-1]
        toys2 = V.conditioned_sets(gun_npass(n_pass, 400), [400], n_toys, (seed, r, 16))[:, :-1]
        pw_np.append(V.toy_calibrated_pvalue(y[:-1], sets2.mean(0), np.cov(sets2, rowvar=False), toys2))
    out.append({"case": "particle gun: K = 3 shape + efficiency conditioned on N_tot,s", "size": a,
                "power_at_3.2_sigma": _rate(pw_ok), "ok": abs(a - 0.05) <= 0.0125 and _rate(pw_ok) >= 0.6,
                "control_N_pass_size": _rate(pv_np), "control_N_pass_power": _rate(pw_np),
                "control_ok": _rate(pw_np) <= 0.10})          # no power beyond about 2 alpha

    # (iii) two run periods, model fraction 0.45, true 0.5, efficiencies 0.6 and 0.8: eps1, eps2 and the combined t
    E1, E2 = 0.6, 0.8

    def periods(n, rng):
        n1, n2 = int(n[0]), int(n[1])
        k1, k2 = rng.binomial(n1, E1), rng.binomial(n2, E2)
        return np.array([k1 / n1, k2 / n2, (k1 + k2) / (n1 + n2)])

    def periods_sum(n, rng):
        N = int(sum(n))
        n1 = rng.binomial(N, 0.45)
        return periods([n1, N - n1], rng)
    pv_c, pv_s = [], []
    for r in range(reps):
        rng = np.random.default_rng([seed, 13, r])
        n1 = rng.binomial(800, 0.5)
        y = periods([n1, 800 - n1], rng)
        sets = V.conditioned_sets(periods, [n1, 800 - n1], B, (seed, r, 9))
        toys = V.conditioned_sets(periods, [n1, 800 - n1], n_toys, (seed, r, 10))
        pv_c.append(V.toy_calibrated_pvalue(y, sets.mean(0), np.cov(sets, rowvar=False), toys))
        sets = V.conditioned_sets(periods_sum, [n1, 800 - n1], B, (seed, r, 11))
        toys = V.conditioned_sets(periods_sum, [n1, 800 - n1], n_toys, (seed, r, 12))
        pv_s.append(V.toy_calibrated_pvalue(y, sets.mean(0), np.cov(sets, rowvar=False), toys))
    a, b = _rate(pv_c), _rate(pv_s)
    out.append({"case": "two periods (model fraction 0.45, true 0.5): conditioned on (N1, N2)", "size": a,
                "ok": abs(a - 0.05) <= 0.0125, "control_conditioned_on_sum": b, "control_ok": b > 0.0625})
    return out


# ------------------------------------------------------------------ gate 1: the remaining heavy items (card items 2, 9-11)
def gate1_g7_bblite(reps: int = 40, seed: int = SEED_GATE1 + 70) -> dict:
    """G7 for a fit with only Poisson blocks and BB-lite: Sigma_MC from the auxiliary measurements (B_m of section 6.7)
    passes; A V_MC A^T alone (Sigma_MC = 0) diverges (section 15.3.1)."""
    from core.calibration import toys_linear as T
    rng = np.random.default_rng(seed)
    K = 12
    pois = {"a": rng.uniform(20, 80, K), "b": rng.normal(0, 0.4, K), "tau": np.full(K, 200.0)}
    cfg = T.linear_config(n=0, d=1, poisson=pois, prior=[(-1, 1)], bounds=[(-3, 3)])
    p = T.make(cfg, [0.2], data_seed=seed, mc_seed=seed + 1)
    f = F.iterate(p, T.initial_beta(p), lndet=False)
    S = F.sigma_mc(p, f, None)
    bb = zero = 0
    for r in range(reps):
        th = np.array([F.iterate(q, T.initial_beta(q), lndet=False).beta[:1] for q in
                       (T.LinearProblem(cfg, mc_seed=seed + 10_000 + 100 * r + k, data=p.data) for k in range(10))])
        bb += F.g7(th, S)["status"] == "failed"
        zero += F.g7(th, np.zeros((1, 1)), sigma_tot_ref=f.sigma_tot)["status"] == "failed"
    return {"case": "G7 Poisson-only with BB-lite", "fail_rate_bb": bb / reps, "fail_rate_zero": zero / reps,
            "ok": bb / reps <= 0.1 and zero / reps >= 0.9}


def gate1_g8_lndet(reps: int = 50, seed: int = SEED_GATE1 + 80) -> dict:
    """G8 detects a fitter that omits ln det while V changes with theta (bias ~0.5 sigma) with probability >= 0.8:
    >= 40 detections in 50 repetitions at the standard level; the correct fitter as the positive control."""
    from scipy import optimize
    from core.calibration import closure as C
    from core.calibration import likelihood as Lk
    from core.calibration import toys_linear as T
    cfg = T.linear_config(n=20, d=1, count_c=1.0, sd=0.5, bounds=[(-2.0, 10.0)], prior=[(-2.0, 3.0)])
    cfg.J[:, 0] = np.abs(cfg.J[:, 0]) + 0.5
    N = C.n_c(1, "standard")["N_c"]
    p0 = T.make(cfg, [0.5], 1, 2)
    sd = F.iterate(p0, T.initial_beta(p0)).sigma_tot
    interior, boundary = C.injection_points(cfg.prior, cfg.bounds, sd, np.array([0.5]))
    det = {"good": 0, "bad": 0}
    for r in range(reps):
        for kind in ("good", "bad"):
            def maker(truth, off):
                return lambda s: T.make(cfg, truth, data_seed=seed + 10 ** 6 * r + off + s, mc_seed=seed + 7 + s + 10 ** 6 * r)

            def fit_and_cover(p, s):
                f = F.iterate(p, T.initial_beta(p), lndet=False)
                th = f.beta[0]
                if kind == "bad":
                    def chi2(x):
                        rf = p.reference(np.array([x]), None)
                        return Lk.Likelihood(p.layout, p.data, rf).deviance(np.r_[x], p.h(np.array([x])))
                    th = optimize.minimize_scalar(chi2, bounds=(-2, 10), method="bounded").x
                err = np.array([th - p.truth[0]])
                return f.converged, err, np.abs(err) <= f.sigma_tot, np.abs(err) <= 1.96 * f.sigma_tot, {"n": 0, "X": 0}, True
            ri = C.run_point(maker(interior, 0), fit_and_cover, N, range(100_000))
            rb = C.run_point(maker(boundary, 500_000), fit_and_cover, N, range(100_000))
            det[kind] += C.g8("standard", ["t0"], sd, ri, rb)["status"] == "failed"
    return {"case": "G8 detects a fitter without ln det", "detections_bad": det["bad"], "false_alarms_good": det["good"],
            "reps": reps, "ok": det["bad"] >= 40}


def gate1_g8_counting(reps: int = 1000, seed: int = SEED_GATE1 + 90) -> dict:
    """Counting non-converged pseudo-data as not covered (negative control) over-rejects at the full level, d = 3,
    eps = 1% concentrated in covered pseudo-data, against replacement (section 7.3, 15.3.1, 15.3.9)."""
    from core.calibration import closure as C
    N = C.n_c(3, "full")["N_c"]
    fa = {"replace": 0, "count": 0}
    for r in range(reps):
        rng = np.random.default_rng([seed, r])
        pts = {}
        for kind in ("replace", "count"):
            res = {}
            for k, pt in enumerate(("interior", "boundary")):
                err = rng.normal(size=(N, 3)) if kind == "replace" else None
                if kind == "count":
                    err = rng.normal(size=(N, 3))
                    nc = rng.random(N) < 0.01
                c68 = np.abs(err) <= 1.0
                c95 = np.abs(err) <= 1.96
                if kind == "count":
                    c68[nc] = False
                    c95[nc] = False
                res[pt] = {"errors": err, "cover68": c68, "cover95": c95, "nontruth_basin": np.zeros(N, bool), "X": 0,
                           "interval_toys": {"X": 0, "n": 0}}
            fa[kind] += C.g8("full", ["a", "b", "c"], np.ones(3), res["interior"], res["boundary"])["status"] == "failed"
    return {"case": "G8: non-converged pseudo-data counted as not covered (negative control)", "false_alarms": fa,
            "reps": reps, "ok": fa["replace"] <= 62 and fa["count"] > 62}


def gate1_power_point_estimate(reps: int = 2000, seed: int = SEED_GATE1 + 100, k: int = 5, R: int = 50,
                               n_toys: int = 1000, MC_SD: float = 1.0) -> dict:
    """Power toys scaled by the point estimate of lambda-hat_cross while the true power is 0.75 claim a lower bound
    >= 0.8 in more than 5% of repetitions (negative control); with the one-sided lower bound and the Bonferroni split
    (m = 1: 0.975 each) in at most 5% (section 15.3.10)."""
    from scipy import optimize as so
    from core.calibration import validate as V
    crit = stats.chi2.ppf(0.95, k)
    lam = so.brentq(lambda x: stats.ncx2.sf(crit, k, x) - 0.75, 0.1, 100)
    e = np.zeros(k)
    e[0] = np.sqrt(lam)
    claims = {"point": 0, "lower": 0}
    for r in range(reps):
        rng = np.random.default_rng([seed, r])
        cr = np.einsum("ri,ri->r", e + rng.normal(size=(R, k)) * MC_SD, e + rng.normal(size=(R, k)) * MC_SD)
        # the point estimate: one cross product of two MC sets; the lower bound: over R independent repetitions
        for kind, lv in (("point", float(cr[0])), ("lower", V.lambda_lower_bound(cr, 0.975))):
            pw = stats.ncx2.sf(crit, k, max(lv, 1e-9))
            rej = rng.binomial(n_toys, pw)
            claims[kind] += V.clopper_pearson_lower(int(rej), n_toys, 0.975) >= 0.8
    return {"case": "P7: power toys scaled by the point estimate (negative control)", "claims": claims, "reps": reps,
            "true_power": 0.75, "ok": claims["point"] / reps > 0.05 and claims["lower"] / reps <= 0.05}


def gate1_shape_total(reps: int = 2000, seed: int = SEED_GATE1 + 110) -> dict:
    """A shape conditioned on its total (K = 5, calibration total 500): the size of T_v at N_obs = 300, 1200, 1500,
    3000 is alpha (within alpha +- 25%) with the multinomial and propagation terms scaled per section 2.1 (15.2)."""
    from core.calibration import likelihood as Lk
    from core.calibration import validate as V
    K = 5
    rng0 = np.random.default_rng(seed)
    A = rng0.normal(size=(K - 1, 2)) * 0.5
    Lm = Lk.logratio_matrix(K, "alr")
    a0 = np.log(np.array([0.3, 0.25, 0.2, 0.15]) / 0.1)

    class Shape:
        def __init__(s, counts):
            s.layout = Lk.build_layout([{"name": "c", "block": "poisson", "bins": K, "free_omega": True}], ["t0", "t1"],
                                       [], 0, 0)
            s.data = Lk.Data(y_gauss=np.zeros(0), counts={"c": counts})
            s.sigma_noise, s.edm_tol = 0.0, 0.01

        def h(s, tp):
            return a0 + A @ np.asarray(tp)[:2]

        def p(s, tp):
            return Lk.logratio_inverse(s.h(tp), Lm)

        def reference(s, tp, beta, frozen=None, bootstrap_frozen=False, bootstrap_seed=None):
            return Lk.Reference(V_G=np.zeros((0, 0)), V_std=np.zeros((0, 0)), U=np.zeros((K - 1, 0)),
                                S=np.zeros((K - 1, 0))).finalize()

        def bounds(s):
            return [(-10, 10)] * 2

        def prior_box(s):
            return [(-3, 3)] * 2

        def sigma_prior(s):
            return [6 / 12 ** 0.5] * 2
    truth = np.array([0.3, -0.2])
    p0 = Lk.logratio_inverse(a0 + A @ truth, Lm)
    sizes = {}
    for Nobs in (300, 1200, 1500, 3000):
        rej = 0
        for r in range(reps):
            rng = np.random.default_rng([seed, Nobs, r])
            sh = Shape(rng.multinomial(500, p0))
            lk = Lk.Likelihood(sh.layout, sh.data, sh.reference(None, None))
            f = F.iterate(sh, lk.initial_beta({"t0": 0, "t1": 0}), lndet=False)
            th = f.beta[:2]
            Gm = np.stack([(sh.p(th + e_) - sh.p(th - e_)) / 2e-5 for e_ in np.eye(2) * 1e-5], axis=1)
            Gb = np.zeros((K, f.Sigma_beta.shape[0]))
            Gb[:, :2] = Gm
            pc = V.shape_holdout_pieces(rng.multinomial(Nobs, p0), sh.p(th), Gb, f.Sigma_beta)
            Cp, kk = V.c_r_plus(pc["C_r"], pc["s"], pc["constraints"])
            rej += V.t_v(pc["r"], Cp) > stats.chi2.ppf(0.95, kk)
        sizes[Nobs] = rej / reps
    return {"case": "shape conditioned on its total (K = 5, calibration total 500)", "sizes": sizes, "reps": reps,
            "ok": all(abs(s - 0.05) <= 0.0125 for s in sizes.values())}


# ------------------------------------------------------------------ gate 1 assembly
# ------------------------------------------------------------------ gate 1 on the toy detector (review F1, F2)
TRACK_THETA = {"momentum_scale": {"bounds": (0.5, 1.5), "prior": (0.98, 1.02)},
               "sum_term_a": {"bounds": (0.2, 3.0), "prior": (0.8, 1.2)}}
TRACK_TRUTH = np.array([1.004, 1.05])          # inside the prior box, away from its centre (the fits start there)
SEED_T1 = 20261200


def track_build(n):
    return toy.build_toy(n, "full", 1.0, ["track5", "track2"])


def track_problem(r, cal, val, mc=4000, exposure=400, val_exposure=4000, shift=None, seed=SEED_T1):
    """The track branch of the toy detector as a fit problem (theta = momentum scale and sum term a; P3 at the prior
    centre passes with lambda_min 0.95), its validation observables from a separate sample of the same detector;
    repetition r has its own nominal MC, bootstrap and validation MC (the size is averaged over the MC noise)."""
    return TP.ToyProblem(track_build, cal, TRACK_THETA, exposure=exposure, mc_events=mc, mc_seed=(seed, r, 1),
                         boot_seed=(seed, r, 2), val_names=val, val_mc_seed=(seed, r, 3), val_exposure=val_exposure,
                         shift=shift)


def _size_judge(rate, alpha=0.05):
    return abs(rate - alpha) <= 0.25 * alpha


def t1_v_cross_terms(reps: int = 2000, seed: int = SEED_T1 + 10, r0: int = 0) -> dict:
    """Item 11 (V), on the toy detector: T_v with the analytic C_r (V_vv plus the propagation term J_v Sigma J_v^T)
    against chi2_k over `reps` repetitions of actual data (fresh calibration and validation events at the truth, a
    fresh nominal MC): rejection within alpha +- 25%; the formula omitting the propagation term rejects above
    alpha + 25%. Non-converged fits are counted and must stay <= 1%."""
    cal = ["track5_p_mean", "track5_p_width", "track2_p_mean", "track2_p_width"]
    val = ["track2_p_mean", "track5_p_width", "track2_p_width"]
    rej, rej0, X, n = 0, 0, 0, 0
    for r in range(r0, r0 + reps):
        p = track_problem(r, cal, val, seed=seed)
        rng = np.random.default_rng([seed, r])
        truth = np.r_[TRACK_TRUTH, np.zeros(p.layout.n_beta - 2)]
        p.data = p.simulate(truth, rng, nominal=False)
        yv = p.simulate_val(truth, rng, nominal=False)
        f = F.iterate(p, p.initial_beta())
        if not f.converged:
            X += 1
            continue
        n += 1
        p.set_val_point(f.beta[:2])
        pc = V.holdout_pieces(p, f, yv)
        Cp, k = V.c_r_plus(pc["C_r"], pc["s"], [])
        rej += V.t_v(pc["r"], Cp) > stats.chi2.ppf(0.95, k)
        pc0 = V.holdout_pieces(p, f, yv, omit=("propagation",))
        Cp0, k0 = V.c_r_plus(pc0["C_r"], pc0["s"], [])
        rej0 += V.t_v(pc0["r"], Cp0) > stats.chi2.ppf(0.95, k0)
    return _judge_cross({"item": "11 V cross terms (toy detector)", "rej": int(rej), "rej_omitted": int(rej0), "n": n,
                         "X": X, "reps": reps})


def _judge_cross(c):
    size, size0 = c["rej"] / max(c["n"], 1), c["rej_omitted"] / max(c["n"], 1)
    ok = _size_judge(size) and size0 > 0.0625 and c["X"] <= 0.01 * c["reps"]
    return {**c, "size_correct": size, "size_omitted": size0, "ok": bool(ok),
            "criterion": "correct within 0.05 +- 0.0125, omitted > 0.0625, X <= 1%"}


SHIFT_SIGMA = 0.07


def t1_v_shift(reps: int = 2000, seed: int = SEED_T1 + 20, r0: int = 0) -> dict:
    """Item 11 (V), shift-mode phi on the toy detector: sum_term_b in shift mode (centre 0.5, sigma 0.07; exposures 2000 and 16000 for validation, so that
    the phi-induced residual dominates C_r), its true
    value drawn from its prior in each repetition and fixed at nominal in the fit; C_r with sum d_l d_l^T (the
    symmetric +-1 sigma refits) gives a rejection rate within alpha +- 25%; only the indirect effect, and the refit
    derivative with a minus sign, give a rate outside alpha +- 25%."""
    from core.calibration import shift as Sh
    cal = ["track5_p_mean", "track5_p_width", "track2_p_width", "track5_dx_width"]
    val = ["track5_dx_width", "track2_dx_width", "track2_p_width"]
    res = {"ok": 0, "minus": 0, "indirect": 0}
    X, X2, n = 0, 0, 0
    for r in range(r0, r0 + reps):
        p = track_problem(r, cal, val, seed=seed, shift={"sum_term_b": (0.5, SHIFT_SIGMA)}, exposure=2000,
                          val_exposure=16000)
        rng = np.random.default_rng([seed, r])
        truth = np.r_[TRACK_TRUTH, np.zeros(p.layout.n_beta - 2)]
        phi = rng.normal(size=1)
        p.data = p.simulate(truth, rng, phi, nominal=False)
        yv = p.simulate_val(truth, rng, phi, nominal=False)
        f = F.iterate(p, p.initial_beta())
        if not f.converged:
            X += 1
            continue
        rf = Sh.refits(p, f, multistart=False)
        if not (rf[(0, 1)]["converged"] and rf[(0, -1)]["converged"]):     # the refits d_l uses (D52 (b))
            X += 1
            continue
        X2 += not (rf[(0, 2)]["converged"] and rf[(0, -2)]["converged"])  # G9's +-2 refits: recorded only
        n += 1
        p.set_val_point(f.beta[:2])

        def mu_v(beta, phis, p=p):
            return p.h_val(beta[:2], phis)
        for lab, kw in (("ok", {}), ("minus", {"sign": -1.0}), ("indirect", {"direct": False})):
            pc = V.holdout_pieces(p, f, yv, d_cols=Sh.d_columns(p, f, rf, mu_v, **kw))
            Cp, k = V.c_r_plus(pc["C_r"], pc["s"], [])
            res[lab] += int(V.t_v(pc["r"], Cp) > stats.chi2.ppf(0.95, k))
    return _judge_shift({"item": "11 V shift-mode phi (toy detector)", "rejections": res, "n": n, "X": X,
                         "X_pm2_refits": X2, "reps": reps})


def _judge_shift(c):
    rate = {k: v / max(c["n"], 1) for k, v in c["rejections"].items()}
    ok = _size_judge(rate["ok"]) and not _size_judge(rate["minus"]) and not _size_judge(rate["indirect"]) and \
        c["X"] <= 0.05 * c["reps"]  # repetitions whose +-1 sigma refits do not converge (G9 would fail) are excluded
    return {**c, "rates": rate, "ok": bool(ok),
            "criterion": "correct within 0.05 +- 0.0125; minus sign and indirect only outside; X <= 5% (+-1 refits)"}


TRACK_CAL = ["track5_p_mean", "track5_p_width", "track2_p_mean", "track2_p_width"]


def _track_fit(r, seed, cal=None, truth=TRACK_TRUTH, theta=None, links=None, data_params=None, **kw):
    """A toy-detector track fit on actual data at the truth (fresh events, `data_params` overriding simulator
    settings in the data only, i.e. an effect the simulation lacks)."""
    p = TP.ToyProblem(track_build, cal or TRACK_CAL, theta or TRACK_THETA, exposure=kw.get("exposure", 400),
                      mc_events=kw.get("mc", 4000), mc_seed=(seed, r, 1), boot_seed=(seed, r, 2), links=links)
    b = np.r_[truth, np.zeros(p.layout.n_beta - len(truth))]
    rng = np.random.default_rng([seed, r])
    if data_params:
        params, _ = p.params_of(b[:len(truth)])
        y = p.observe_at({**params, **data_params}, int(rng.integers(2 ** 62)))
        p.data = L.Data(y_gauss=y)
    else:
        p.data = p.simulate(b, rng, nominal=False)
    p.sigma_noise = TP.estimate_sigma_noise(p, p.initial_beta()) if kw.get("sigma_noise", True) else 0.0
    return p


def t1_g1(seed: int = SEED_T1 + 30) -> dict:
    """Item 3 (G1), toy detector: the iteration limit forced to 1 -> g1.not_converged; the limit 30 -> passes, with
    the EDM per basin below the G1 threshold."""
    p = _track_fit(0, seed)
    bad = F.g1(F.iterate(p, p.initial_beta(), limit=1), p)
    good_fit = F.find_extremum(p, (seed, 1), p.initial_beta())
    good = F.g1(good_fit, p)
    ok = bad.get("finding") == "g1.not_converged" and good["status"] == "passed"
    return {"item": "3 G1 (toy detector)", "forced": bad.get("finding"), "limit_30": good["status"], "ok": bool(ok)}


def t1_g2(seed: int = SEED_T1 + 40, n_toys: int = 500, tries: int = 10) -> dict:
    """Item 4 (G2), toy detector, lower bounds at 1.0: truth sum_term_a = 0.85 (about 5 sigma beyond) ->
    g2.boundary_significant; truth on the bound -> passes (with boundary-solution whenever the bound is active);
    truths 1 sigma beyond both bounds -> the first of up to `tries` repetitions with both bounds active uses the
    chi-bar^2 weights over j = 0, 1, 2 (locally linear toys, one bootstrap per toy)."""
    out = {}
    cases = (("beyond", [1.004, 0.85], {"sum_term_a": 1.0}), ("on", [1.004, 1.0], {"sum_term_a": 1.0}),
             ("two", [0.9996, 0.97], {"momentum_scale": 1.0, "sum_term_a": 1.0}))
    for lab, truth, lo in cases:
        th = {k: {"bounds": (lo.get(k, v["bounds"][0]), v["bounds"][1]),
                  "prior": (max(lo.get(k, -9.0), v["prior"][0]), v["prior"][1])} for k, v in TRACK_THETA.items()}
        for k in range(tries if lab == "two" else 1):
            r = hash_free(lab) + 1000 * k
            p = _track_fit(r, seed, truth=np.array(truth), theta=th)
            f = F.find_extremum(p, (seed, r), p.initial_beta())
            g = F.g2(p, f, F.null_toys(p, f, n_toys, (seed, r, 9)))
            if lab != "two" or len(g.get("active") or []) == 2:
                break
        out[lab] = {k_: g.get(k_) for k_ in ("status", "finding", "flags", "weights", "p", "active")}
        out[lab]["repetition"] = k
    on = out["on"]
    ok = out["beyond"]["finding"] == "g2.boundary_significant" and on["status"] == "passed" and \
        (not on["active"] or "boundary-solution" in on["flags"]) and len(out["two"]["weights"] or []) == 3 and \
        out["two"]["status"] in ("passed", "failed")
    return {"item": "4 G2 (toy detector)", "cases": out, "ok": bool(ok)}


def hash_free(label: str) -> int:
    return zlib.crc32(label.encode()) % 1000


def t1_g5(seed: int = SEED_T1 + 50) -> dict:
    """Item 7 (G5), toy detector: with only the momentum widths, momentum scale and sum term enter as the product
    a s (sigma_p = kappa a s p) -> g5.not_identifiable; with the momentum means added -> passes."""
    from core.calibration import identify as I
    res = {}
    for lab, cal in (("product", ["track5_p_width", "track2_p_width"]), ("means", TRACK_CAL)):
        p = _track_fit(hash_free(lab), seed, cal=cal)
        f = F.find_extremum(p, (seed, hash_free(lab)), p.initial_beta())
        res[lab] = I.g5(p, f, seed=(seed, 2))
    ok = res["product"].get("finding") == "g5.not_identifiable" and res["means"]["status"] == "passed"
    return {"item": "7 G5 (toy detector)", "product": res["product"].get("finding"),
            "product_lambda_min": res["product"].get("lambda_min"), "means": res["means"]["status"], "ok": bool(ok)}


def t1_g6(seed: int = SEED_T1 + 60, n_toys: int = 500) -> dict:
    """Item 8 (G6), toy detector: the track position offset of layer b (0.3, absent from the simulation) in the data
    with the position-difference mean among the observables -> g6.p_value; without it -> passes (linear and full
    toys). The missing effect also fails the linearity check of the locally linear toys, which switches to full toys
    (D56, D46); the full toys must then decide g6.p_value."""
    cal = TRACK_CAL + ["track5_dx_mean"]
    links = {"track5_dx_mean": "identity"}
    out = {}
    for lab, dp in (("correct", None), ("missing", {"layer_b_offset": 0.3})):
        p = _track_fit(hash_free(lab), seed, cal=cal, links=links, data_params=dp)
        f = F.find_extremum(p, (seed, hash_free(lab)), p.initial_beta())
        lin = F.g6(p, f, F.null_toys(p, f, n_toys, (seed, hash_free(lab), 1)))
        full = F.g6_full(p, f, n_toys, (seed, hash_free(lab), 2))
        out[lab] = {"linear": [lin["status"], lin.get("finding"), lin["p"], lin["linearity_ok"]],
                    "full": [full["status"], full.get("finding"), full["p"], full["X"]]}
    ok = out["correct"]["linear"][0] == "passed" and out["correct"]["full"][0] == "passed" and \
        out["missing"]["linear"][1] in ("g6.p_value", "g6.linearity_check_failed") and \
        out["missing"]["full"][1] == "g6.p_value"         # a failed linearity check switches to full toys (D56)
    return {"item": "8 G6 (toy detector)", "cases": out, "ok": bool(ok)}


def t1_g7(reps: int = 40, K: int = 10, seed: int = SEED_T1 + 70) -> dict:
    """Item 9 (G7), toy detector, d = 3 (momentum scale, sum terms a and b): K = 10 fits of the same data with independent nominal MC samples, Sigma_MC =
    A V_MC A^T from the first; with Sigma_MC as computed G7 fails in <= 10% of `reps` sets, with Sigma_MC / 3 (V_MC
    underestimated by 3) in >= 90%."""
    from scipy import linalg
    fails = {"correct": 0, "under3": 0}
    th3 = {**TRACK_THETA, "sum_term_b": {"bounds": (0.05, 2.0), "prior": (0.4, 0.6)}}
    cal = TRACK_CAL + ["track5_dx_width", "track2_dx_width"]
    for r in range(reps):
        p = _track_fit(r, seed, cal=cal, truth=np.r_[TRACK_TRUTH, 0.52], theta=th3, sigma_noise=False)
        th, Smc = [], None
        for k in range(K):
            q = p.with_data(p.data, mc_seed=(seed, r, 100 + k))
            f = F.iterate(q, q.initial_beta())
            if Smc is None:
                J = F.jacobian(q, f.beta[:3], F.fd_steps(q))
                W = linalg.inv(f.ref.V_G)
                S = linalg.inv(J.T @ W @ J)
                A = S @ J.T @ W
                Smc = A @ f.ref.V_MC @ A.T
            th.append(f.beta[:3])
        th = np.array(th)
        fails["correct"] += F.g7(th, Smc)["status"] == "failed"
        fails["under3"] += F.g7(th, Smc / 3.0)["status"] == "failed"
    ok = fails["correct"] <= 0.1 * reps and fails["under3"] >= 0.9 * reps
    return {"item": "9 G7 (toy detector)", "failures": fails, "reps": reps, "ok": bool(ok)}


# G8's injection points sit at the physical bounds (D55): the momentum scale is bounded at 0.995, close to the
# nominal MC, so that the boundary point stays within the reweighting range of the nominal sample
G8_THETA = {"momentum_scale": {"bounds": (0.995, 1.5), "prior": (0.995, 1.02)},
            "sum_term_a": {"bounds": (0.2, 3.0), "prior": (0.8, 1.2)}}
G8_CAL = ["track5_p_width", "track2_p_width", "track5_dx_width", "track2_dx_width", "track5_p_mean", "track2_p_mean"]
G8_LINKS = {n: "identity" for n in G8_CAL}


def _g8_problem(truth, seed_tuple, exposure=100, mc=100):
    """The G8 configuration: identity links (V of a width grows with theta), exposure 100, MC 100 per run, so that a
    fitter omitting ln det is biased by about 0.7 sigma in sum_term_a (pilot). Each pseudo-data set has its own
    nominal-size MC and its own bootstrap (section 8.4: misestimation of V_MC then enters G8's bias and coverage);
    the pseudo-data are fresh events at the injection point."""
    st = [TP._seed_int(x) for x in seed_tuple]
    p = TP.ToyProblem(track_build, G8_CAL, G8_THETA, exposure=exposure, mc_events=mc, mc_seed=(*st, 1),
                      boot_seed=(*st, 2), links=G8_LINKS)
    b = np.r_[truth, np.zeros(p.layout.n_beta - len(truth))]
    p.data = p.simulate(b, np.random.default_rng([*st, 3]), nominal=False)
    p.truth = b
    return p


def _nolndet_fit(p, start):
    """The negative-control fitter: -2 ln L minimized with V recomputed at every theta and no ln det term."""
    from scipy import optimize
    from core.calibration import likelihood as Lk

    def chi2(x):
        rf = p.reference(np.asarray(x), None)
        return Lk.Likelihood(p.layout, p.data, rf).deviance(np.asarray(x), p.h(np.asarray(x)))
    m = optimize.minimize(chi2, start, method="Nelder-Mead", options={"xatol": 1e-7, "fatol": 1e-7, "maxiter": 2000})
    return bool(m.success), m.x


def t1_g8_lndet(reps: int = 50, seed: int = SEED_T1 + 80, r0: int = 0) -> dict:
    """Item 10 (G8), toy detector, standard level, d = 2: the fitter omitting ln det is caught in >= 40 of `reps`
    repetitions; the correct fitter (section 7.3 iteration with the ln det diagnostic) as the positive control."""
    from core.calibration import closure as C
    N = C.n_c(2, "standard")["N_c"]
    p0 = _g8_problem(TRACK_TRUTH, (seed, 0))
    sd = F.iterate(p0, p0.initial_beta()).sigma_tot
    box = [v["prior"] for v in G8_THETA.values()]
    bounds = [v["bounds"] for v in G8_THETA.values()]
    interior, boundary = C.injection_points(box, bounds, sd, TRACK_TRUTH)
    det = {"good": 0, "bad": 0}
    for r in range(r0, r0 + reps):
        for kind in ("good", "bad"):
            def maker(truth, off, r=r):
                return lambda s: _g8_problem(truth, (seed, r, off, s))

            def fit_and_cover(p, s, kind=kind):
                f = F.iterate(p, p.initial_beta())
                th = f.beta[:2]
                ok = f.converged
                if kind == "bad":
                    ok2, th = _nolndet_fit(p, f.beta[:2])
                    ok = ok and ok2
                err = th - p.truth[:2]
                return ok, err, np.abs(err) <= f.sigma_tot, np.abs(err) <= 1.96 * f.sigma_tot, {"n": 0, "X": 0}, True
            ri = C.run_point(maker(interior, 0), fit_and_cover, N, range(100_000))
            rb = C.run_point(maker(boundary, 1), fit_and_cover, N, range(100_000))
            det[kind] += C.g8("standard", list(G8_THETA), sd, ri, rb)["status"] == "failed"
    return _judge_g8({"item": "10 G8 ln det (toy detector)", "detections_bad": det["bad"],
                      "false_alarms_good": det["good"], "reps": reps, "N_c": N})


def _judge_g8(c):
    return {**c, "ok": bool(c["detections_bad"] >= 0.8 * c["reps"])}


def t1_g8_counting(reps: int = 1000, pool: int = 3000, seed: int = SEED_T1 + 90, exposure: int = 400) -> dict:
    """Item 10 (G8 counting), toy detector, full level, d = 3: a pool of `pool` real pseudo-data fits per injection
    point, each with its own MC and bootstrap (coverage by the total Gaussian intervals); each repetition draws N_c with replacement from the pool; the
    eps = 1% non-convergence concentrated in covered pseudo-data: replacing them keeps false alarms <= 62 in 1000,
    counting them as not covered (negative control) gives > 62."""
    from core.calibration import closure as C
    # the third parameter enters linearly (the position-difference mean is the layer-b offset, identity link), so the
    # correct fits are unbiased at G8's full-level resolution (a b^2 term would leave a ~0.2 sigma nonlinear bias)
    th3 = {**G8_THETA, "layer_b_offset": {"bounds": (-1.0, 1.0), "prior": (-0.05, 0.05)}}
    cal = TRACK_CAL + ["track5_dx_mean", "track2_dx_mean"]
    links = {"track5_dx_mean": "identity", "track2_dx_mean": "identity"}
    truth3 = np.r_[TRACK_TRUTH, 0.01]
    p0 = _track_fit(0, seed, cal=cal, truth=truth3, theta=th3, sigma_noise=False, links=links, exposure=exposure,
                    mc=10 * exposure)
    sd = F.iterate(p0, p0.initial_beta()).sigma_tot
    interior, boundary = C.injection_points([v["prior"] for v in th3.values()], [v["bounds"] for v in th3.values()],
                                            sd, truth3)
    pools, Xpool = {}, {}
    for k, pt in enumerate((interior, boundary)):
        errs, c68, c95, X = [], [], [], 0
        for s in range(pool):                     # each pseudo-data set: its own MC and bootstrap (section 8.4)
            q = _track_fit(10 ** 5 * (k + 1) + s, seed, cal=cal, truth=pt, theta=th3, sigma_noise=False, links=links,
                           exposure=exposure, mc=10 * exposure)
            f = F.iterate(q, q.initial_beta())
            if not f.converged:
                X += 1
                continue
            e = f.beta[:3] - pt
            errs.append(e)
            c68.append(np.abs(e) <= f.sigma_tot)
            c95.append(np.abs(e) <= 1.96 * f.sigma_tot)
        pools[k] = (np.array(errs), np.array(c68), np.array(c95))
        Xpool[k] = X
    N = C.n_c(3, "full")["N_c"]
    fa = {"replace": 0, "count": 0}
    for r in range(reps):
        rng = np.random.default_rng([seed, r])
        for kind in fa:
            res = {}
            for k, name in enumerate(("interior", "boundary")):
                E, A68, A95 = pools[k]
                idx = rng.integers(len(E), size=N)
                e, c68, c95 = E[idx], A68[idx].copy(), A95[idx].copy()
                if kind == "count":                   # 1% non-converged, concentrated in covered pseudo-data
                    cov = np.flatnonzero(c68.all(1))
                    nc = rng.choice(cov, size=min(len(cov), int(round(0.01 * N))), replace=False)
                    c68[nc] = False
                    c95[nc] = False
                res[name] = {"errors": e, "cover68": c68, "cover95": c95, "nontruth_basin": np.zeros(N, bool),
                             "X": 0, "interval_toys": {"X": 0, "n": 0}}
            fa[kind] += C.g8("full", list(th3), sd, res["interior"], res["boundary"])["status"] == "failed"
    return {"item": "10 G8 counting (toy detector)", "false_alarms": fa, "reps": reps, "pool": pool,
            "pool_nonconverged": Xpool, "N_c": N, "ok": fa["replace"] <= 62 and fa["count"] > 62}


P7_VAL = ["track5_p_width", "track2_p_width", "track5_dx_width", "track2_dx_width", "track2_p_mean"]


def _p7_problem(mc=4000, seed=SEED_T1 + 100):
    """P7 on the toy detector: the track calibration, k = 5 validation observables from a separate sample; C_r^+ at
    the design stage (Asimov at the truth); the alternative a declared simulation setting the model does not contain
    (the layer-b sum term moved by delta: not theta, nu, eta or phi here)."""
    p = track_problem(0, TRACK_CAL, P7_VAL, mc=mc, seed=seed)
    b = np.r_[TRACK_TRUTH, np.zeros(p.layout.n_beta - 2)]
    p.data = p.asimov(b)
    f = F.iterate(p, b)
    p.set_val_point(f.beta[:2])
    pc = V.holdout_pieces(p, f, p.h_val(f.beta[:2]))
    Cp, k = V.c_r_plus(pc["C_r"], pc["s"], [])
    return p, f, Cp, k


def _alt_effect(p, f, delta, seed_pair):
    """e = h_v^alt - h_v^nom from one independent pair of validation MC samples (section 9.4: the difference of
    two predictions with their own MC noise); the calibration rows do not depend on the setting, so the refit
    absorbs nothing."""
    params, _ = p.params_of(f.beta[:2])
    s_alt, s_nom = (TP._seed_int(x) for x in seed_pair)
    out = []
    for s, extra in ((s_alt, {"sum_term_b": 0.5 + delta}), (s_nom, {})):
        r = p.val_ev.evaluate({**params, **extra}, names=p.val_names, seeds={"nominal": s})
        p.val_ev._other.pop(s, None)
        out.append(p._val_link(r["pred"]))
    return out[0] - out[1]


def _true_lambda(delta, Cp, mc_big=400_000, seed=SEED_T1 + 101):
    """lambda of the alternative from one very large MC sample (common random numbers for alt and nominal)."""
    q = track_problem(0, TRACK_CAL, P7_VAL, mc=mc_big, seed=seed)
    params, _ = q.params_of(TRACK_TRUTH)
    a = q._val_link(q.val_ev.evaluate({**params, "sum_term_b": 0.5 + delta}, names=q.val_names)["pred"])
    n = q._val_link(q.val_ev.evaluate(params, names=q.val_names)["pred"])
    e = a - n
    return float(e @ Cp @ e)


def _delta_for(lam_target, Cp, lo=0.005, hi=0.5):
    from scipy import optimize as so
    return float(so.brentq(lambda d: _true_lambda(d, Cp) - lam_target, lo, hi, xtol=1e-4))


def _cross_pool(p, f, Cp, delta, n_sets, seed):
    E = np.array([_alt_effect(p, f, delta, ((seed, i, 0), (seed, i, 1))) for i in range(n_sets)])
    return E


def t1_p7_cross(pool: int = 16000, seed: int = SEED_T1 + 102) -> dict:
    """Item 2 (P7), toy detector: at the delta whose true lambda is 12.8 (k = 5), the cross product of two
    independent MC sets is unbiased (pool mean within +-2% of the true lambda, the true value from 400000 events),
    while the single-set estimate is biased high (> +2%); with k = 1 (only the momentum mean of track 2, blind to the
    setting) P7 fails with p7.insufficient_power, with k = 5 at a delta of 4x the lambda-12.8 delta it passes."""
    from core.calibration import design_noise as DN
    p, f, Cp, k = _p7_problem()
    d128 = _delta_for(12.8, Cp)
    lam = _true_lambda(d128, Cp)
    E = _cross_pool(p, f, Cp, d128, pool, seed)
    cross = np.einsum("ri,ij,rj->r", E[0::2], Cp, E[1::2])
    single = np.einsum("ri,ij,rj->r", E, Cp, E)
    rel_c, rel_s = float(cross.mean() / lam - 1), float(single.mean() / lam - 1)
    # insufficient power: k = 1 blind to the alternative; sufficient: k = 5 at 4 delta_12.8, R = 50 repetitions
    E4 = _cross_pool(p, f, Cp, 4 * d128, 100, seed + 1)
    big = DN.p7("holdout", 5, {"a": np.einsum("ri,ij,rj->r", E4[0::2], Cp, E4[1::2])}, "analytic", 5)
    p1 = track_problem(0, TRACK_CAL, ["track2_p_mean"], seed=SEED_T1 + 100)
    b = np.r_[TRACK_TRUTH, np.zeros(p1.layout.n_beta - 2)]
    p1.data = p1.asimov(b)
    f1 = F.iterate(p1, b)
    p1.set_val_point(f1.beta[:2])
    pc1 = V.holdout_pieces(p1, f1, p1.h_val(f1.beta[:2]))
    Cp1, _ = V.c_r_plus(pc1["C_r"], pc1["s"], [])
    E1 = np.array([_alt_effect(p1, f1, 4 * d128, ((seed + 2, i, 0), (seed + 2, i, 1))) for i in range(100)])
    small = DN.p7("holdout", 1, {"a": np.einsum("ri,ij,rj->r", E1[0::2], Cp1, E1[1::2])}, "analytic", 1)
    ok = abs(rel_c) <= 0.02 and rel_s > 0.02 and small.get("finding") == "p7.insufficient_power" and \
        big["status"] == "passed"
    return {"item": "2 P7 cross product and power (toy detector)", "delta_12_8": d128, "true_lambda": lam,
            "cross_rel_bias": rel_c, "single_rel_bias": rel_s, "pool": pool, "k1": small.get("finding"),
            "k5_4delta": big["status"], "ok": bool(ok)}


def t1_p7_point_estimate(reps: int = 2000, pool: int = 4000, R: int = 50, n_toys: int = 1000,
                         seed: int = SEED_T1 + 103) -> dict:
    """Item 2 (P7), toy detector: at the delta whose true power is 0.75 (k = 5), cross products drawn from a pool of
    `pool` toy-detector MC pairs; the power from the point estimate (one cross product) claims a lower bound >= 0.8
    in > 5% of `reps` repetitions (negative control); the one-sided lower bound over R = 50 cross products with the
    Bonferroni split (0.975) in <= 5% (section 15.3.10)."""
    from scipy import optimize as so
    p, f, Cp, k = _p7_problem()
    crit = stats.chi2.ppf(0.95, k)
    lam75 = so.brentq(lambda x: stats.ncx2.sf(crit, k, x) - 0.75, 0.1, 100)
    d75 = _delta_for(lam75, Cp)
    E = _cross_pool(p, f, Cp, d75, pool, seed)
    cr_pool = np.einsum("ri,ij,rj->r", E[0::2], Cp, E[1::2])
    claims = {"point": 0, "lower": 0}
    for r in range(reps):
        rng = np.random.default_rng([seed, r])
        cr = cr_pool[rng.integers(cr_pool.size, size=R)]
        for kind, lv in (("point", float(cr[0])), ("lower", V.lambda_lower_bound(cr, 0.975))):
            pw = stats.ncx2.sf(crit, k, max(lv, 1e-9))
            rej = rng.binomial(n_toys, pw)
            claims[kind] += V.clopper_pearson_lower(int(rej), n_toys, 0.975) >= 0.8
    ok = claims["point"] / reps > 0.05 and claims["lower"] / reps <= 0.05
    return {"item": "2 P7 point estimate (toy detector)", "claims": claims, "reps": reps, "lambda_075": lam75,
            "delta_075": d75, "pool_pairs": int(cr_pool.size), "ok": bool(ok)}


def t1_cv(seed: int = SEED_T1 + 110, n_ref: int = 500) -> dict:
    """Item 11 (V, cross-validation) and item 1 (fold P3), toy detector: T_cv with C-hat_{r,f} from complete
    cross-validation toys (every fold refitted; the engine never uses locally linear toys for cross-validation, so a
    fold failing the linearity check is covered by construction, section 9.3, 8.5) and its toy reference gives a
    p-value on actual data at the truth; a split whose training fold keeps only the momentum widths (theta enters as
    a product there) is rejected by design.fold_p3, a split keeping a mean in every training fold passes."""
    from core.calibration import design_noise as DN
    cal = ["track5_p_mean", "track5_p_width", "track2_p_mean", "track2_p_width", "track5_dx_width",
           "track2_dx_width"]
    p = _track_fit(0, seed, cal=cal)
    folds = [[0, 1, 4], [2, 3, 5]]                       # each fold keeps a momentum mean in its training set
    ev = V.cv_evidence(p, folds, "k" * 64, 0.05, (seed, 1), n_ref=n_ref, n_start=0)
    b = p.initial_beta()
    asimov = p.with_data(p.asimov(b))
    bad = DN.fold_p3(asimov, [np.array([0, 2])], b)      # training rows: the widths only
    good = DN.fold_p3(asimov, [np.array(r) for r in folds], b)
    ok = ev["status"] == "ok" and ev["p"] is not None and [f["code"] for f in bad] == ["design.fold_p3"] and \
        good == []
    return {"item": "11 V cross-validation and 1 fold P3 (toy detector)", "T_cv": ev.get("T"), "k": ev.get("k"),
            "p": ev.get("p"), "status": ev["status"], "reference": ev.get("reference"),
            "fold_p3_bad": [f["code"] for f in bad], "fold_p3_good": good, "ok": bool(ok)}


def t1_propagation(seed: int = SEED_T1 + 120) -> dict:
    """Item 12 (propagation), toy detector: a joint track fit exports R1 (the momentum scale) and R2 (the sum term,
    with R1's theta as its central input zeta); combining the two packages as independent misstates Var(theta_1 +
    theta_2) against the joint value from Sigma (the parent-child counterexample on real fits); the package checks
    on these two results find the source overlap, and a theta/nu split export is rejected."""
    from core.calibration import deps
    p = _track_fit(0, seed, sigma_noise=False)
    f = F.iterate(p, p.initial_beta())
    S = f.Sigma_beta[:2, :2]
    th = f.beta[:2]
    p1 = P.export(th[[0]], np.zeros(0), S, [0], [])
    p2 = P.export(th[[1]], th[[0]], S, [1], [0])
    # scale to unit sigma so the variances are comparable
    D = np.diag(1 / np.sqrt(np.diag(S)))
    Sz = D @ S @ D
    joint = float(np.ones(2) @ Sz @ np.ones(2))
    q1 = P.export(np.zeros(1), np.zeros(0), Sz, [0], [])
    q2 = P.export(np.zeros(1), np.zeros(1), Sz, [1], [0])
    indep = float(P.variance(q1)[0, 0] + P.variance(q2)[0, 0])
    h1, h2 = (hashlib.sha256(f"toy-track-R{i}-{seed}".encode()).hexdigest() for i in (1, 2))
    ups = {h2: [{"result_sha256": h1, "usages": ["xi"]}]}
    pc = deps.check_packages([{"id": "R1", "upstream": h1}, {"id": "R2", "upstream": h2}], ups)
    split = deps.check_packages([{"id": "R1", "upstream": h1, "exports": ["theta", "nu"]}], {})
    rho = float(Sz[0, 1])
    ok = abs(indep - joint) > 0.1 and [x["code"] for x in pc] == ["deps.source_overlap"] and \
        [x["code"] for x in split] == ["deps.theta_nu_split"] and abs(P.variance(p1)[0, 0] - S[0, 0]) < 1e-15
    return {"item": "12 propagation (toy detector)", "correlation": rho, "var_sum_joint": joint,
            "var_sum_independent": indep, "package_findings": [x["code"] for x in pc],
            "split": [x["code"] for x in split], "ok": bool(ok)}


P5_EDGES = np.linspace(4.86, 5.14, 11)          # the momentum histogram of track 5: every bin populated (+-2.8 sigma)
P2_EDGES = np.linspace(1.944, 2.056, 6)          # the track-2 momentum shape, K = 5


def t1_g7_bblite(reps: int = 40, K: int = 10, seed: int = SEED_T1 + 130) -> dict:
    """Item 9 (G7), toy detector, a fit with only Poisson blocks and BB-lite: the track-5 momentum histogram (10 bins,
    absolute counts, exposure 2000, MC 20000); K = 10 fits of the same data with independent MC samples; Sigma_MC
    from the auxiliary measurements (B_m, section 6.7) fails G7 in <= 10% of `reps` sets, A V_MC A^T alone
    (Sigma_MC = 0: no Gaussian rows) in >= 90%."""
    counts = {"p5_hist": {"source": "track5_p_mean", "edges": P5_EDGES, "kind": "absolute", "bb": True}}
    fails = {"bb": 0, "zero": 0}
    for r in range(reps):
        p = TP.ToyProblem(track_build, [], TRACK_THETA, exposure=2000, mc_events=20000, mc_seed=(seed, r, 1),
                          boot_seed=(seed, r, 2), counts=counts)
        b = np.r_[TRACK_TRUTH, np.zeros(p.layout.n_beta - 2)]
        p.data = p.simulate(b, np.random.default_rng([seed, r]), nominal=False)
        th, S, st = [], None, None
        for k in range(K):
            q = p.with_data(p.data, mc_seed=(seed, r, 100 + k))
            f = F.iterate(q, q.initial_beta())
            if S is None:
                S = F.sigma_mc(q, f, None)[:2, :2]
                st = f.sigma_tot
            th.append(f.beta[:2])
        th = np.array(th)
        fails["bb"] += F.g7(th, S)["status"] == "failed"
        fails["zero"] += F.g7(th, np.zeros((2, 2)), sigma_tot_ref=st)["status"] == "failed"
    ok = fails["bb"] <= 0.1 * reps and fails["zero"] >= 0.9 * reps
    return {"item": "9 G7 BB-lite (toy detector)", "failures": fails, "reps": reps, "ok": bool(ok)}


def t1_shape_total(reps: int = 2000, seed: int = SEED_T1 + 140, nobs=(300, 1200, 1500, 3000)) -> dict:
    """Item 11 (V, a shape conditioned on its total), toy detector: the track calibration (exposure 400); the
    validation shape is the track-2 momentum histogram (K = 5) of a separate sample with N_obs events, conditioned on
    its observed total: r = n - N_obs p(beta-hat), C = N_obs (diag p - p p^T) + N_obs^2 G Sigma_beta G^T with p and
    G = dp/dbeta from a validation MC of 200000 events (its noise adds about N_obs / 200000 <= 1.5% to the variance);
    the size of T_v against chi2_(K-1) at N_obs in {300, 1200, 1500, 3000} within alpha +- 25%."""
    shape = {"p2_shape": {"source": "track2_p_mean", "edges": P2_EDGES, "kind": "shape"}}
    vp = TP.ToyProblem(track_build, [], TRACK_THETA, exposure=1000, mc_events=200_000, mc_seed=(seed, 1),
                       boot_seed=(seed, 2), counts=shape)

    def pshape(tp):
        mu = vp.counts_pred(vp.params_of(tp)[0])["p2_shape"]["mu"]
        return mu / mu.sum()
    data_model = track_build(4000)
    sizes = {}
    for Nobs in nobs:
        rej, X = 0, 0
        for r in range(reps):
            p = track_problem(0, TRACK_CAL, [], seed=seed + 1)
            rng = np.random.default_rng([seed, Nobs, r])
            truth = np.r_[TRACK_TRUTH, np.zeros(p.layout.n_beta - 2)]
            p.data = p.simulate(truth, rng, nominal=False)
            f = F.iterate(p, p.initial_beta())
            if not f.converged:
                X += 1
                continue
            th = f.beta[:2]
            ev = toy.ChainEvaluator(data_model, {"seeds": {"nominal": 1}})
            params, _ = p.params_of(truth[:2])
            gen = ev.generate(int(rng.integers(2 ** 62)), params={**data_model.nominal, **params})
            evs = {"track2": {nd: {k: np.asarray(v)[:Nobs] for k, v in o.items()}
                              for nd, o in gen["runs"]["track2"]["events"].items()}}
            n = vp._hist(data_model, evs, "p2_shape")[0]
            steps = np.array([1e-5, 1e-3])
            Gm = np.stack([(pshape(th + e) - pshape(th - e)) / (2 * s) for e, s in zip(np.diag(steps), steps)], 1)
            Gb = np.zeros((len(n), f.Sigma_beta.shape[0]))
            Gb[:, :2] = Gm
            pc = V.shape_holdout_pieces(n, pshape(th), Gb, f.Sigma_beta)
            Cp, kk = V.c_r_plus(pc["C_r"], pc["s"], pc["constraints"])
            rej += V.t_v(pc["r"], Cp) > stats.chi2.ppf(0.95, kk)
        sizes[str(Nobs)] = {"rej": int(rej), "X": X, "size": rej / max(reps - X, 1)}
    return _judge_shape({"item": "11 V shape conditioned on its total (toy detector)", "sizes": sizes, "reps": reps})


def _judge_shape(c):
    ok = all(_size_judge(v["size"]) and v["X"] <= 0.01 * c["reps"] for v in c["sizes"].values())
    return {**c, "ok": bool(ok)}


def _p_pool(run: str, n: int, seed) -> np.ndarray:
    """Reconstructed momenta of n toy-detector events of `run` generated at the truth (an event pool: the
    model's parametric bootstrap draws from it, the data from a pool of its own)."""
    m = track_build(n)
    ev = toy.ChainEvaluator(m, {"seeds": {"nominal": 1}})
    params = dict(zip(TRACK_THETA, TRACK_TRUTH))
    gen = ev.generate(TP._seed_int(seed), params={**m.nominal, **params})
    return np.asarray(gen["runs"][run]["events"]["momentum"]["p_rec"], float)


def t1_event_samples(reps: int = 2000, B: int = 500, n_toys: int = 500, seed: int = SEED_T1 + 150) -> list:
    """Item 11 (V, section 15.3.7 event samples), toy detector: event samples of the track runs with their summary
    statistics, the parametric bootstrap and the reference toys drawn by the engine's conditioned_sets (exactly
    n_j events per component) from toy-detector event pools generated at the truth; data from a separate pool.
    (i) particle gun (track 5, |p - 5| < 0.05, K = 3 shape of the selected momenta + efficiency), N_tot,s = 400 while
    N_decl = 800: conditioned on the observed 400, size within alpha +- 25%; the omega = 1 procedure (sets and toys
    conditioned on N_decl) > alpha + 25%. (ii) the gun's power at a 3.2 sigma efficiency loss (events lost at random,
    the shape unchanged) >= 0.6; conditioned on the shape's own N_pass the efficiency drops out: power <= 0.10.
    (iii) two periods (track 5 and track 2, efficiencies about 0.6 and 0.8; true fraction 0.5, model 0.45):
    conditioned on (N1, N2) size within alpha +- 25%; conditioned on N1 + N2 with the model fraction > alpha + 25%."""
    pool5, pool2 = _p_pool("track5", 200_000, (seed, 1)), _p_pool("track2", 200_000, (seed, 2))
    data5, data2 = _p_pool("track5", 200_000, (seed, 3)), _p_pool("track2", 200_000, (seed, 4))
    W5, W2 = 0.044, 0.0269
    edges = np.linspace(4.95, 5.05, 4)

    def gun_summary(p, keep=None):
        sel = np.abs(p - 5.0) < 0.05
        if keep is not None:
            sel &= keep
        k, _ = np.histogram(p[sel], edges)
        return np.r_[_alr(k), sel.mean() if p.size else 0.0]

    def draw(pool, n, rng):
        return pool[rng.integers(pool.size, size=n)]

    def gun(n, rng):
        return gun_summary(draw(pool5, int(sum(n)), rng))

    def pval(y, summary, n_c, r, tag, drop_last=False):
        sets = V.conditioned_sets(summary, n_c, B, (seed, tag, r, 1))
        toys = V.conditioned_sets(summary, n_c, n_toys, (seed, tag, r, 2))
        if drop_last:
            sets, toys, y = sets[:, :-1], toys[:, :-1], y[:-1]
        return V.toy_calibrated_pvalue(y, sets.mean(0), np.cov(sets, rowvar=False), toys)
    out = []
    pv_ok, pv_om = [], []
    for r in range(reps):
        rng = np.random.default_rng([seed, 10, r])
        y = gun_summary(draw(data5, 400, rng))
        pv_ok.append(pval(y, gun, [400], r, 11))
        pv_om.append(pval(y, gun, [800], r, 12))
    a, c = _rate(pv_ok), _rate(pv_om)
    out.append({"case": "particle gun, omega = 0.5: conditioned on N_tot,s = 400", "size": a, "ok": _size_judge(a),
                "control_omega1": c, "control_ok": c > 0.0625})
    eps = float(np.mean(np.abs(pool5 - 5.0) < 0.05))
    q = 3.2 * np.sqrt(eps * (1 - eps) / 400) / eps            # random loss giving a 3.2 sigma efficiency bias
    pw, pw_np = [], []
    for r in range(reps):
        rng = np.random.default_rng([seed, 20, r])
        pd = draw(data5, 400, rng)
        keep = rng.random(400) >= q
        y = gun_summary(pd, keep)
        pw.append(pval(y, gun, [400], r, 21))
        n_pass = int(round(y[-1] * 400))
        sel = np.abs(pool5 - 5.0) < 0.05
        P_in, P_out = pool5[sel], pool5[~sel]

        def gun_npass(n, rng, n_pass=n_pass):
            return gun_summary(np.r_[draw(P_in, n_pass, rng), draw(P_out, int(sum(n)) - n_pass, rng)])
        pw_np.append(pval(y, gun_npass, [400], r, 22, drop_last=True))
    a, c = _rate(pw), _rate(pw_np)
    out.append({"case": "particle gun power at a 3.2 sigma efficiency loss", "power": a, "ok": a >= 0.6,
                "control_N_pass_power": c, "control_ok": c <= 0.10, "efficiency": eps, "loss": q})

    def periods_summary(n, rng):
        a5, a2 = draw(pool5, int(n[0]), rng), draw(pool2, int(n[1]), rng)
        k1, k2 = int(np.sum(np.abs(a5 - 5.0) < W5)), int(np.sum(np.abs(a2 - 2.0) < W2))
        return np.array([k1 / max(n[0], 1), k2 / max(n[1], 1), (k1 + k2) / max(n[0] + n[1], 1)])

    def periods_sum(n, rng):
        N = int(sum(n))
        n1 = int(rng.binomial(N, 0.45))
        return periods_summary([n1, N - n1], rng)
    pv_c, pv_s = [], []
    for r in range(reps):
        rng = np.random.default_rng([seed, 30, r])
        n1 = int(rng.binomial(800, 0.5))
        a5, a2 = draw(data5, n1, rng), draw(data2, 800 - n1, rng)
        k1, k2 = int(np.sum(np.abs(a5 - 5.0) < W5)), int(np.sum(np.abs(a2 - 2.0) < W2))
        y = np.array([k1 / n1, k2 / (800 - n1), (k1 + k2) / 800])
        pv_c.append(pval(y, periods_summary, [n1, 800 - n1], r, 31))
        pv_s.append(pval(y, periods_sum, [n1, 800 - n1], r, 32))
    a, c = _rate(pv_c), _rate(pv_s)
    out.append({"case": "two periods: conditioned on (N1, N2)", "size": a, "ok": _size_judge(a),
                "control_conditioned_on_sum": c, "control_ok": c > 0.0625})
    return out


GATE1_EVIDENCE = {
    "1 P3": ["harness gate1_toy_p3 (toy detector)", "test_calibration_identify_shift_interval.Identifiability",
             "test_calibration_design_noise.Folds.test_fold_p3"],
    "2 P7": ["test_calibration_contract (validation.alternative_shift: nu_k = 2 rejected)",
             "test_calibration_design_noise.P7", "test_calibration_validate.Power",
             "test_calibration_validate.CrossValidation (power by toys: cv_ensemble)", "harness gate1_power_point_estimate"],
    "3 G1": ["test_calibration_fit.Iteration.test_g1_iteration_limit", "test_calibration_fit.Basins"],
    "4 G2": ["test_calibration_fit.G2G3 (beyond, on, two parameters with chi-bar^2)"],
    "5 G3": ["test_calibration_fit.G2G3.test_g3_isolation_mode"],
    "6 G4": ["test_calibration_g4"],
    "7 G5": ["test_calibration_identify_shift_interval.Identifiability (product; non-converged scan points: plan)"],
    "8 G6": ["test_calibration_fit.G6 (missing effect; cross-term nonlinearity -> full toys)"],
    "9 G7": ["test_calibration_fit.G7 (factor 3 detection, rank one, null space)", "harness gate1_g7_bblite"],
    "10 G8": ["test_calibration_closure", "harness gate1_g8_lndet (50 repetitions)", "harness gate1_g8_counting",
              "test_calibration_design_noise.Practices (pseudo-data sharing the fit MC rejected)"],
    "11 V": ["test_calibration_validate (NullSpace, Holdout, ShiftModeResidual, ToyPath, CrossValidation, Records)",
             "test_calibration_data_checks", "test_calibration_locking", "test_calibration_data (phase 0: reads, failure "
             "records)", "test_calibration_contract (phase 0 rules of sections 15.3.4-15.3.8)", "harness gate1_event_samples",
             "harness gate1_shape_total", "cross-validation toys are always complete toys, so a fold failing the "
             "linearity check uses full toys by construction"],
    "12 propagation": ["test_calibration_propagate"],
}


def gate_negatives(out: Path, smoke: bool = False) -> dict:
    """Gate 1 as registered: the calibration unit-test modules and the script tests at the commit, and the harness
    items at their registered sizes (smoke: tiny sizes, not evidence)."""
    t0 = time.time()
    mods = sorted(p.name for p in (ROOT / "tests" / "core").glob("test_calibration_*.py"))
    units = {}
    for m in mods:
        r = subprocess.run([sys.executable, "-I", str(ROOT / "tests" / "core" / m)], capture_output=True, text=True,
                           timeout=7200, cwd=ROOT)
        tail = (r.stderr or "").strip().splitlines()[-3:]
        units[m] = {"exit": r.returncode, "summary": tail}
    r = subprocess.run([sys.executable, "-m", "unittest", "tests.skills.test_calib_scripts"], capture_output=True,
                       text=True, timeout=7200, cwd=ROOT)
    units["tests.skills.test_calib_scripts"] = {"exit": r.returncode, "summary": (r.stderr or "").strip().splitlines()[-3:]}
    s = 0.1 if smoke else 1.0
    items = {"toy_p3": gate1_toy_p3(),
             "event_samples": gate1_event_samples(reps=int(2000 * s)),
             "g7_bblite": gate1_g7_bblite(reps=int(40 * s) or 2),
             "g8_lndet": gate1_g8_lndet(reps=int(50 * s) or 2),
             "g8_counting": gate1_g8_counting(reps=int(1000 * s)),
             "power_point_estimate": gate1_power_point_estimate(reps=int(2000 * s)),
             "shape_total": gate1_shape_total(reps=int(2000 * s))}
    def ok(x):
        if isinstance(x, list):
            return all(c.get("ok") and c.get("control_ok", True) for c in x)
        return bool(x.get("ok")) and x.get("control_ok", True)
    units_ok = all(u["exit"] == 0 for u in units.values())
    items_ok = {k: ok(v) for k, v in items.items()}
    passed = units_ok and all(items_ok.values())
    rep = {"gate": "the negative tests of P3, P7, G1-G8, V and propagation", "status": "passed" if passed else "failed",
           "smoke": smoke, "units": units, "items": items, "items_ok": items_ok, "evidence": GATE1_EVIDENCE,
           "seconds": time.time() - t0, "provenance": provenance(), "label": "smoke (not evidence)" if smoke else "synthetic"}
    io.write_json(str(out), io.jsonable(rep))
    return rep


# ------------------------------------------------------------------ gate 1 on the toy detector: array tasks and merge
def _units() -> dict:
    mods = sorted(p.name for p in (ROOT / "tests" / "core").glob("test_calibration_*.py"))
    units = {}
    for m in mods:
        r = subprocess.run([sys.executable, "-I", str(ROOT / "tests" / "core" / m)], capture_output=True, text=True,
                           timeout=10800, cwd=ROOT)
        units[m] = {"exit": r.returncode, "summary": (r.stderr or "").strip().splitlines()[-3:]}
    r = subprocess.run([sys.executable, "-m", "unittest", "tests.skills.test_calib_scripts"], capture_output=True,
                       text=True, timeout=10800, cwd=ROOT)
    units["tests.skills.test_calib_scripts"] = {"exit": r.returncode,
                                                "summary": (r.stderr or "").strip().splitlines()[-3:]}
    return {"item": "unit tests", "units": units, "ok": all(u["exit"] == 0 for u in units.values())}


GATE1T_TASKS = [("units", "_units", {}), ("toy_p3", "gate1_toy_p3", {}), ("g1", "t1_g1", {}), ("g2", "t1_g2", {}),
                ("g5", "t1_g5", {}), ("g6", "t1_g6", {}), ("g7", "t1_g7", {}), ("g7_bblite", "t1_g7_bblite", {}),
                ("cv", "t1_cv", {}), ("propagation", "t1_propagation", {}), ("p7_cross", "t1_p7_cross", {}),
                ("p7_point", "t1_p7_point_estimate", {}), ("g8_counting", "t1_g8_counting", {}),
                ("event_samples", "t1_event_samples", {})]
GATE1T_TASKS += [("v_cross", "t1_v_cross_terms", {"reps": 1000, "r0": 1000 * i}) for i in range(2)]
GATE1T_TASKS += [("v_shift", "t1_v_shift", {"reps": 200, "r0": 200 * i}) for i in range(10)]
GATE1T_TASKS += [("shape_total", "t1_shape_total", {"nobs": (n,)}) for n in (300, 1200, 1500, 3000)]
GATE1T_TASKS += [("g8_lndet", "t1_g8_lndet", {"reps": 5, "r0": 5 * i}) for i in range(10)]


def gate1_toy_task(i: int, out_dir: Path) -> dict:
    """One task of the gate-1 array on the toy detector (registered sizes; seeds fixed per item and repetition)."""
    key, fn, kw = GATE1T_TASKS[i]
    t0 = time.time()
    res = globals()[fn](**kw)
    rec = {"task": i, "item": key, "function": fn, "kwargs": kw, "result": res, "seconds": time.time() - t0,
           "provenance": provenance(), "label": "synthetic"}
    out_dir.mkdir(parents=True, exist_ok=True)
    io.write_json(str(out_dir / f"task_{i:02d}.json"), io.jsonable(rec))
    return rec


def _ok(x):
    if isinstance(x, list):
        return all(c.get("ok") and c.get("control_ok", True) for c in x)
    return bool(x.get("ok")) and x.get("control_ok", True)


def gate1_toy_merge(out_dir: Path, out: Path) -> dict:
    """Merge the array: every task present and from one clean commit; blocks summed per item, then judged."""
    recs = {}
    for i in range(len(GATE1T_TASKS)):
        f = out_dir / f"task_{i:02d}.json"
        recs[i] = json.loads(f.read_text()) if f.exists() else None
    missing = [i for i, r in recs.items() if r is None]
    commits = {r["provenance"]["commit"] for r in recs.values() if r}
    dirty = any(r["provenance"].get("dirty") for r in recs.values() if r)
    items = {}
    by = {}
    for i, r in recs.items():
        if r:
            by.setdefault(r["item"], []).append(r["result"])
    for key, rs in by.items():
        if key == "v_cross":
            items[key] = _judge_cross({"item": rs[0]["item"], **{k: sum(x[k] for x in rs) for k in
                                                                  ("rej", "rej_omitted", "n", "X", "reps")}})
        elif key == "v_shift":
            rej = {k: sum(x["rejections"][k] for x in rs) for k in rs[0]["rejections"]}
            items[key] = _judge_shift({"item": rs[0]["item"], "rejections": rej,
                                       **{k: sum(x[k] for x in rs) for k in ("n", "X", "X_pm2_refits", "reps")}})
        elif key == "g8_lndet":
            items[key] = _judge_g8({"item": rs[0]["item"], "N_c": rs[0]["N_c"],
                                    **{k: sum(x[k] for x in rs) for k in ("detections_bad", "false_alarms_good",
                                                                          "reps")}})
        elif key == "shape_total":
            items[key] = _judge_shape({"item": rs[0]["item"], "reps": rs[0]["reps"],
                                       "sizes": {k: v for x in rs for k, v in x["sizes"].items()}})
        else:
            items[key] = rs[0]
    items_ok = {k: _ok(v) for k, v in items.items()}
    passed = not missing and len(commits) == 1 and not dirty and all(items_ok.values())
    rep = {"gate": "the negative tests of P3, P7, G1-G8, V and propagation (on the toy detector)",
           "status": "passed" if passed else "failed", "missing_tasks": missing, "commits": sorted(commits),
           "dirty": dirty, "items": items, "items_ok": items_ok,
           "task_seconds": {i: r["seconds"] for i, r in recs.items() if r}, "provenance": provenance(),
           "label": "synthetic"}
    io.write_json(str(out), io.jsonable(rep))
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--gate", choices=("segmented", "shift", "negatives"))
    ap.add_argument("--calibration", choices=sorted(CALS))
    ap.add_argument("--reps", type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--gate1-toy-task", type=int, help="one task of the gate-1 array on the toy detector")
    ap.add_argument("--gate1-toy-merge", help="the folder of the array's task files")
    a = ap.parse_args(argv)
    if a.gate1_toy_task is not None:
        r = gate1_toy_task(a.gate1_toy_task, Path(a.out))
        print(json.dumps({"task": r["task"], "item": r["item"], "ok": _ok(r["result"]), "seconds": r["seconds"]}))
        return 0
    if a.gate1_toy_merge:
        r = gate1_toy_merge(Path(a.gate1_toy_merge), Path(a.out))
        print(json.dumps({"status": r["status"], "items_ok": r["items_ok"], "missing": r["missing_tasks"]}))
        return 0 if r["status"] == "passed" else 1
    if a.gate == "segmented":
        r = gate_segmented(Path(a.out), a.smoke, a.probe)
        print(json.dumps({"status": r["status"], "results": r["results"], "seconds": r["seconds"]}))
        return 0 if r["status"] == "passed" else 1
    if a.gate == "negatives":
        r = gate_negatives(Path(a.out), a.smoke)
        print(json.dumps({"status": r["status"], "items_ok": r["items_ok"],
                          "units_failed": [m for m, u in r["units"].items() if u["exit"] != 0]}))
        return 0 if r["status"] == "passed" else 1
    if a.gate == "shift":
        r = gate_shift(Path(a.out))
        print(json.dumps({"status": r["status"], "cases": [(c["case"], c["ok"]) for c in r["cases"]]}))
        return 0 if r["status"] == "passed" else 1
    if a.calibration:
        t0 = time.time()
        r = CALS[a.calibration](**({"reps": a.reps} if a.reps else {}))
        r.update(seconds=time.time() - t0, provenance=provenance(), label="synthetic")
        io.write_json(a.out, io.jsonable(r))
        print(json.dumps({"calibration": r["calibration"], "passed": r["passed"], "seconds": r["seconds"]}))
        return 0 if r["passed"] else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
