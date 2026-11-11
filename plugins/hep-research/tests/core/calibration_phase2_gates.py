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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--gate", choices=("segmented", "shift"))
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
