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
    data = joint.simulate(truth, rng)
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
    sp, Cp, _ = seg2_fit(pkg["G_xi"], pkg["G_zeta"], np.zeros(2) + np.array([0.0, 1.0]), np.diag([1.0, 0.05 ** 2]),
                         1)
    res["counterexample_prior"] = agree(sp, Cp, bj, Cj)
    Gm = P.marginal_regressions(f1.Sigma_beta, i_th, [i_z[0]], [i_z[1]])
    D = np.diag(np.diag(f1.Sigma_beta)[i_z])
    sm, Cm, _ = seg2_fit(pkg["G_xi"], Gm, pkg["zeta_hat"], D, 2)
    res["counterexample_marginal"] = agree(sm, Cm, bj, Cj)
    passed = res["joint_posterior"]["agree"] and not res["counterexample_prior"]["agree"] and \
        not res["counterexample_marginal"]["agree"] and fj.converged and f1.converged and f2.converged
    rep = {"gate": "segmented calibration and the joint fit agree", "status": "passed" if passed else "failed",
           "smoke": smoke, "probe": probe, "label": "smoke (not evidence)" if smoke else ("probe (not evidence)" if probe else "synthetic"), "results": res,
           "converged": {"joint": fj.converged, "segment1": f1.converged, "segment2": f2.converged},
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


CALS = {"chat": cal13_chat, "lambda-bound": cal14_lower_bound, "lambda": cal3_lambda, "g7": cal5_g7, "bj": cal7_bj}


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
            rng = np.random.default_rng([seed, hash(label) % 2 ** 31, r])
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--gate", choices=("segmented", "shift", "negatives"))
    ap.add_argument("--calibration", choices=sorted(CALS))
    ap.add_argument("--reps", type=int)
    ap.add_argument("--out", required=True)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args(argv)
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
