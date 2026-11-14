"""The deferred section 8.7 calibrations of phase 2 (task card `docs/dev/simulator-calibration/simcal-tasks/phase-2.md`,
"Calibrations of this phase"), run as Slurm job arrays: each task writes the raw per-repetition records of one block
of one configuration, the merge concatenates them and applies the registered rule. Not a unit test module.

  python3 calibration_phase2_cals.py --task N --out DIR          one task of the array
  python3 calibration_phase2_cals.py --merge DIR --out FILE      merge and judge (exit 0 passed, 1 failed)
  python3 calibration_phase2_cals.py --local NAME --out FILE     a calibration light enough to run locally
  python3 calibration_phase2_cals.py --smoke NAME --out FILE     the code path at tiny sizes (not evidence)

Seeds: a repetition r of calibration c and configuration j draws from default_rng([cal_seed(c, r), j, ...]) (no
stream shared between calibrations, configurations or repetitions). The G8-based items wait (the user's decision of
2026-11-12, "Run the rest, G8 rows wait").
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import calibration_phase2_gates as G  # noqa: E402

from core.calibration import fit as F  # noqa: E402
from core.calibration import interval as IV  # noqa: E402
from core.calibration import io  # noqa: E402
from core.calibration import likelihood as L  # noqa: E402
from core.calibration import shift as Sh  # noqa: E402
from core.calibration import toy  # noqa: E402
from core.calibration import toy_problem as TP  # noqa: E402
from core.calibration import toys_linear as T  # noqa: E402
from core.calibration import validate as V  # noqa: E402

cal_seed = G.cal_seed
Z68 = 1.0                                   # +-1 sigma: nominal 0.6827
Z95 = float(stats.norm.ppf(0.975))
NOM68 = float(stats.norm.cdf(1) - stats.norm.cdf(-1))


def _rng(c, r, j, *more):
    return np.random.default_rng([cal_seed(c, r), j, *more])


def _int(c, r, j, *more):
    return int(np.random.SeedSequence([cal_seed(c, r), j, *more]).generate_state(1)[0])


def _within3se(rate, n, p0):
    return n > 0 and abs(rate - p0) <= 3 * math.sqrt(p0 * (1 - p0) / n)


# ------------------------------------------------------------------ calibration 2: allowed fraction of the linearity check
CAL2_TRUTH = np.array([0.5, -0.3, 1.0])
CAL2_Q = {"linear": 0.0, "near-linear": 0.10, "nonlinear": 0.40}      # quadratic scale q (card re-registration)
CAL2_TOYS = 500
CAL2_ALPHA = 0.01


def _cal2_config(q):
    cfg = T.linear_config(n=20, d=3, seed=11, mc_ratio=0.1)
    if q:
        cfg.quad = q * np.random.default_rng(12).normal(size=(20, 3, 3))
    return cfg


def cal2_block(config: str, r0: int, reps: int) -> list:
    """G6 with locally linear toys and with full toys on the same data, and the profile interval of theta_0."""
    j = list(CAL2_Q).index(config)
    cfg = _cal2_config(CAL2_Q[config])
    rows = []
    for r in range(r0, r0 + reps):
        p = T.make(cfg, CAL2_TRUTH, data_seed=_int(2, r, j, 1), mc_seed=_int(2, r, j, 2))
        f = F.iterate(p, T.initial_beta(p))
        if not f.converged:
            rows.append({"r": r, "converged": False})
            continue
        g = F.g6(p, f, F.null_toys(p, f, CAL2_TOYS, (cal_seed(2, r), j, 3)), alpha=CAL2_ALPHA)
        gf = F.g6_full(p, f, CAL2_TOYS, (cal_seed(2, r), j, 4), alpha=CAL2_ALPHA)
        cov = {}
        for lev in (0.68, 0.95):
            iv = IV.profile_interval(p, f, 0, lev, seed=(cal_seed(2, r), j, 5))
            lo, hi = iv.get("lo", iv.get("lower")), iv.get("hi", iv.get("upper"))
            cov[str(lev)] = None if lo is None or hi is None else bool(lo <= CAL2_TRUTH[0] <= hi)
        rows.append({"r": r, "converged": True, "p_lin": g["p"], "X_lin": g["X"], "lin_fraction": g["linearity_fraction"],
                     "lin_ok": g["linearity_ok"], "p_full": gf["p"], "X_full": gf["X"], "cover_theta0": cov})
    return rows


def cal2_judge(rows_by: dict) -> dict:
    out, ok = {}, True
    for cfg, rows in rows_by.items():
        conv = [x for x in rows if x["converged"]]
        chk = [x for x in conv if x["lin_ok"]]
        pl = np.array([x["p_lin"] for x in chk])
        pf = np.array([x["p_full"] for x in chk])
        rate_lin = float(np.mean(pl <= CAL2_ALPHA)) if len(pl) else None
        rate_full = float(np.mean(pf <= CAL2_ALPHA)) if len(pf) else None
        ks = float(stats.ks_2samp(pl, pf).pvalue) if len(pl) > 1 else None
        allp_l = np.array([x["p_lin"] for x in conv])
        allp_f = np.array([x["p_full"] for x in conv])
        rec = {"reps": len(rows), "converged": len(conv), "check_passes": len(chk),
               "check_pass_fraction": len(chk) / max(len(conv), 1), "rate_lin_where_check_passes": rate_lin,
               "rate_full_where_check_passes": rate_full, "ks_p_where_check_passes": ks,
               "rate_lin_all": float(np.mean(allp_l <= CAL2_ALPHA)) if len(conv) else None,
               "rate_full_all": float(np.mean(allp_f <= CAL2_ALPHA)) if len(conv) else None,
               "mean_abs_p_difference": float(np.mean(np.abs(allp_l - allp_f))) if len(conv) else None,
               "coverage_theta0": {lev: float(np.mean([x["cover_theta0"][lev] for x in conv
                                                        if x["cover_theta0"][lev] is not None]))
                                   for lev in ("0.68", "0.95")} if conv else None}
        judged = cfg != "nonlinear"          # the linear and near-linear configurations, on the repetitions
                                            # where the check passes; the nonlinear one is reported
        if judged:
            rec["passed"] = bool(rate_lin is not None and rate_lin <= 1.5 * CAL2_ALPHA and ks is not None and ks >= 0.01)
            ok = ok and rec["passed"]
        else:
            rec["passed"] = None                             # the check fails: the difference is reported
        out[cfg] = rec
    return {"calibration": 2, "row": 2001, "configurations": out, "passed": bool(ok),
            "rule": "where the check passes: G6 rejection with locally linear toys <= 1.5 alpha and KS p >= 0.01 "
                    "against full toys; where it fails, reported"}


# ------------------------------------------------------------------ calibration 4: c and t_lin of shift mode
CAL4_CAL = ["track5_p_mean", "track5_dx_width", "track2_dx_width"]
CAL4_SIGMA = {"0.03": 0.01212, "0.1": 0.02214, "0.3": 0.03834}          # sigma of sum_term_b giving P8 lambda
CAL4_RESP = {"linear": (0.0, 0.0), "quadratic": (0.15, 0.0), "cubic": (0.0, 0.05)}    # g = phi + k2 phi^2 + k3 phi^3
CAL4_NOISE = (0.0, 0.01)
CAL4_EXPOSURE, CAL4_MC = 2000, 16000


def _cal4_cfg_index(lam, resp):
    return list(CAL4_SIGMA).index(lam) * len(CAL4_RESP) + list(CAL4_RESP).index(resp)


def _cal4_problem(r, j, sigma, resp=None):
    kw = dict(exposure=CAL4_EXPOSURE, mc_events=CAL4_MC, mc_seed=(cal_seed(4, r), j, 1),
              boot_seed=(cal_seed(4, r), j, 2))
    if resp is None:                                        # profile mode: sum_term_b a constrained parameter
        return TP.ToyProblem(G.track_build, CAL4_CAL, G.TRACK_THETA, phi_P={"sum_term_b": (0.5, sigma)}, **kw)
    return TP.ToyProblem(G.track_build, CAL4_CAL, G.TRACK_THETA, shift={"sum_term_b": (0.5, sigma)},
                         shift_response={"sum_term_b": CAL4_RESP[resp]}, **kw)


def cal4_lambda(lam: str, j: int = 0) -> float:
    p = _cal4_problem(0, j, CAL4_SIGMA[lam], "linear")
    b = np.r_[G.TRACK_TRUTH, np.zeros(p.layout.n_beta - 2)]
    p.observed = L.Observations(y_gauss=p.h(b[:2]))
    return float(Sh.p8(p, b)["lambda_max"])


def cal4_block(lam: str, resp: str, r0: int, reps: int) -> list:
    j = _cal4_cfg_index(lam, resp)
    sig = CAL4_SIGMA[lam]
    th_true = np.asarray(G.TRACK_TRUTH, float)
    rows = []
    for r in range(r0, r0 + reps):
        rng = _rng(4, r, j)
        phi = float(rng.normal())
        p = _cal4_problem(r, j, sig, resp)
        truth = np.r_[th_true, np.zeros(p.layout.n_beta - 2)]
        p.observed = p.simulate(truth, rng, np.array([phi]), nominal=False)
        f = F.iterate(p, p.initial_beta())
        row = {"r": r, "phi": phi, "converged": bool(f.converged)}
        if not f.converged:
            rows.append(row)
            continue
        rf = Sh.refits(p, f, multistart=False)
        row["refits_converged"] = {f"{k[1]}": bool(v["converged"]) for k, v in rf.items()}
        th = f.beta[:2]
        D = {k: v["theta"] - th for k, v in rf.items()}
        lin0 = Sh.linearity(D, f.sigma_tot, 1)
        s0 = np.asarray(lin0["s"])
        lam_hat = float(np.linalg.eigvalsh(Sh.conditional_information(p, f.beta, f.ref)).max())
        row.update(theta=th.tolist(), sigma_tot=f.sigma_tot.tolist(), a=np.asarray(lin0["a"])[:, 0].tolist(),
                   lambda_at_fit=lam_hat)
        nrng = _rng(4, r, j, 7)
        z = {k: nrng.normal(size=2) for k in D}
        per = {}
        for nz in CAL4_NOISE:
            Dn = {k: D[k] + nz * s0 * z[k] for k in D}
            lin = Sh.linearity(Dn, f.sigma_tot, 1)
            w = np.maximum(np.abs(Dn[(0, 1)]), np.abs(Dn[(0, -1)]))
            s = np.sqrt(f.sigma_tot ** 2 + w ** 2)
            allconv = all(v["converged"] for v in rf.values())
            g9 = bool(allconv and max(lin["Delta"]) <= Sh.T_LIN and lam_hat <= 1.5 * Sh.C_INFO)
            per[str(nz)] = {"Delta": list(map(float, lin["Delta"])), "s": s.tolist(), "g9": g9,
                            "cover68": (np.abs(th - th_true) <= Z68 * s).tolist(),
                            "cover95": (np.abs(th - th_true) <= Z95 * s).tolist()}
        row["noise"] = per
        pp = _cal4_problem(r, j, sig)                       # profile mode on the same data and the same MC
        pp.observed = L.Observations(y_gauss=p.observed.y_gauss, phi0=np.array([0.5]), phi_cov=pp.phi_cov())
        fp = F.iterate(pp, pp.initial_beta())
        row["profile"] = {"converged": bool(fp.converged)}
        if fp.converged:
            tp = fp.beta[:2]
            row["profile"].update(theta=tp.tolist(), sigma_tot=fp.sigma_tot.tolist(),
                                  cover68=(np.abs(tp - th_true) <= Z68 * fp.sigma_tot).tolist(),
                                  cover95=(np.abs(tp - th_true) <= Z95 * fp.sigma_tot).tolist(),
                                  diff=(th - tp).tolist())
        rows.append(row)
    return rows


def cal4_judge(rows_by: dict, lambdas: dict) -> dict:
    out, ok = {}, True
    for key, rows in rows_by.items():
        lam, resp = key.split("|")
        p8 = lambdas[key] <= Sh.C_INFO
        conv = [x for x in rows if x["converged"]]
        for nz in map(str, CAL4_NOISE):
            pas = [x for x in conv if x["noise"][nz]["g9"]]
            n = len(pas)
            c68 = np.mean([x["noise"][nz]["cover68"] for x in pas], axis=0) if n else np.full(2, np.nan)
            c95 = np.mean([x["noise"][nz]["cover95"] for x in pas], axis=0) if n else np.full(2, np.nan)
            prof = [x["profile"] for x in conv if x["profile"]["converged"]]
            rec = {"lambda_P8": lambdas[key], "P8": "passed" if p8 else "failed", "reps": len(rows),
                   "converged": len(conv), "g9_passes": n, "shift_cover68": c68.tolist(), "shift_cover95": c95.tolist(),
                   "profile_cover68": np.mean([x["cover68"] for x in prof], axis=0).tolist() if prof else None,
                   "profile_cover95": np.mean([x["cover95"] for x in prof], axis=0).tolist() if prof else None,
                   "r_mean": np.mean([np.abs(x["a"]) / np.asarray(x["sigma_tot"]) for x in conv], axis=0).tolist()
                   if conv else None}
            if p8 and n:
                rec["coverage_ok"] = bool(all(_within3se(c68[i], n, NOM68) and _within3se(c95[i], n, 0.95)
                                              for i in range(2)))
                ok = ok and rec["coverage_ok"]
            if lam == "0.1" and resp == "linear":
                both = [x for x in conv if x["profile"]["converged"]]
                rms_d = np.sqrt(np.mean([np.square(x["profile"]["diff"]) for x in both], axis=0))
                rms_a = np.sqrt(np.mean([np.square(x["a"]) for x in both], axis=0))
                pred = math.sqrt(lambdas[key] / (1 + lambdas[key])) * rms_a
                judged = [i for i in range(2) if rec["r_mean"][i] >= 0.1]
                rec.update(rms_difference=rms_d.tolist(), predicted=pred.tolist(), judged_parameters=judged,
                           rms_ok=bool(judged and all(abs(rms_d[i] / pred[i] - 1) <= 0.10 for i in judged)))
                ok = ok and rec["rms_ok"]
            out[f"{key}|noise={nz}"] = rec
    return {"calibration": 4, "row": 2003, "configurations": out, "passed": bool(ok),
            "rule": "where P8 and G9 pass: shift-mode 68% and 95% coverage within 3 binomial se of nominal; at "
                    "lambda = c = 0.1 (linear response) rms(shift - profile) within 10% of sqrt(c/(1+c)) |a| for "
                    "the parameters with mean r >= 0.1"}


# ------------------------------------------------------------------ calibration 8: tau_num (local)
def cal8_tau_num() -> dict:
    """The four confirmations of section 8.7 note 1 on the toy detector: a track fit (exposure 400) and the track-2
    momentum shape (K = 5) of a separate sample conditioned on its total, whose residuals sum to 0 by construction."""
    seed = cal_seed(8, 0)
    p = G.track_problem(0, G.TRACK_CAL, [], seed=seed)
    rng = np.random.default_rng([seed, 1])
    truth = np.r_[G.TRACK_TRUTH, np.zeros(p.layout.n_beta - 2)]
    p.observed = p.simulate(truth, rng, nominal=False)
    f = F.iterate(p, p.initial_beta())
    shape = {"p2_shape": {"source": "track2_p_mean", "edges": G.P2_EDGES, "kind": "shape"}}
    vp = TP.ToyProblem(G.track_build, [], G.TRACK_THETA, exposure=1000, mc_events=400_000, mc_seed=(seed, 2),
                       boot_seed=(seed, 3), counts=shape)

    def pshape(tp):
        mu = vp.counts_pred(vp.params_of(tp)[0])["p2_shape"]["mu"]
        return mu / mu.sum()
    th = f.beta[:2]
    steps = np.array([1e-5, 1e-3])
    Gm = np.stack([(pshape(th + e) - pshape(th - e)) / (2 * s) for e, s in zip(np.diag(steps), steps)], 1)
    Gb = np.zeros((Gm.shape[0], f.cov_beta.shape[0]))
    Gb[:, :2] = Gm
    Nobs = 1500
    p0 = pshape(th)
    n_exp = Nobs * p0
    pc = V.shape_holdout_pieces(n_exp, p0, Gb, f.cov_beta)
    C, s, cons = pc["C_r"], pc["s"], pc["constraints"]
    # toy residuals of the conditioned shape: multinomial counts minus N p, no rounding
    toys = np.array([rng.multinomial(Nobs, p0) - n_exp for _ in range(2000)])
    e_nom = Nobs * pshape(np.asarray(G.TRACK_TRUTH, float)) - n_exp     # the nominal model's residual expectation
    a = V.declaration_check(C, s, cons, expectations=[e_nom], toy_residuals=toys)
    item1 = {"block_norm": a.get("block_norm"), "max_expectation": a.get("max_expectation"),
             "analytic_block_norm": V.declaration_check(C, s, cons)["block_norm"],
             "ok": bool(a.get("block_norm", 1) < 1e-14 and a.get("max_expectation", 1) < 1e-7)}
    K = C.shape[0]
    # (2) a wrongly declared direction with standardized sd 1e-3: an extra row r1 + r2 + e, sd(e) = 1e-3 sd(row)
    T2 = np.vstack([np.eye(K), np.r_[1.0, 1.0, np.zeros(K - 2)]])
    C2 = T2 @ C @ T2.T
    C2[K, K] += (1e-3) ** 2 * C2[K, K]
    s2 = np.sqrt(np.diag(C2))
    wrong = np.r_[1.0, 1.0, np.zeros(K - 2), -1.0]
    b = V.declaration_check(C2, s2, [np.r_[v, 0.0] for v in cons] + [wrong])
    item2 = {"failures": b["failures"], "ok": "validate.declared_direction_has_variance" in b["failures"]}
    # (3) two observables with correlation 1 - 1e-7 undeclared: a copy of row 1 with that correlation
    c = 1 - 1e-7
    T3 = np.vstack([np.eye(K), np.r_[1.0, np.zeros(K - 1)]])
    C3 = T3 @ C @ T3.T
    v1 = C3[0, 0]
    C3[K, K] = v1
    C3[K, :K] = C3[0, :K] * c
    C3[:K, K] = C3[K, :K]
    C3[K, 0] = C3[0, K] = c * v1
    s3 = np.sqrt(np.diag(C3))
    d3 = V.declaration_check(C3, s3, [np.r_[v, 0.0] for v in cons])
    item3 = {"lambda_min": d3.get("lambda_min"), "failures": d3["failures"], "ok": d3["status"] == "passed"}
    # (4) the conditioned shape's C_r rescaled to diag(100, ..., 1e-6) scales and its correlation matrix
    D = np.diag(np.r_[10.0, np.ones(K - 2), 1e-3])
    C4 = D @ C @ D
    s4 = np.sqrt(np.diag(C4))
    cons4 = [np.linalg.solve(D, np.asarray(v)) for v in cons]      # n.y = 0 becomes (D^-1 n).(D y) = 0
    corr = C4 / np.outer(s4, s4)
    d4a = V.declaration_check(C4, s4, cons4)
    d4b = V.declaration_check(corr, np.ones(K), [np.asarray(v) * s4 for v in cons4])
    r = rng.normal(size=K)
    tv_a = V.t_v(r * s4, V.c_r_plus(C4, s4, cons4)[0])
    tv_b = V.t_v(r, V.c_r_plus(corr, np.ones(K), [np.asarray(v) * s4 for v in cons4])[0])
    item4 = {"status": [d4a["status"], d4b["status"]], "T_v": [tv_a, tv_b],
             "ok": d4a["status"] == d4b["status"] and abs(tv_a - tv_b) <= 1e-8 * max(1.0, abs(tv_a))}
    items = {"exact_constraint": item1, "wrong_declaration": item2, "near_collinear": item3, "scale": item4}
    return {"calibration": 8, "row": 2011, "fit_converged": bool(f.converged), "items": items,
            "passed": bool(f.converged and all(v["ok"] for v in items.values())),
            "rule": "all four confirmations of note 1 hold on the toy detector"}


# ------------------------------------------------------------------ calibration 11: G5 failures in cross-validation toys
CAL11_SIGMA_POST = 0.66              # theta_1 from fold 0's training rows: sigma_post / sigma_prior = 0.3996 (P3 0.4)
CAL11_THETA1 = ("0.0", "0.2", "0.4", "0.6", "0.8", "1.2")      # scan of the theta-hat position toward the box edge 3
CAL11_FOLDS = [list(range(6)), list(range(6, 12))]
CAL11_ALPHA = 0.05
CAL11_NCHAT, CAL11_NREF = 500, 500


def _cal11_config():
    rng = np.random.default_rng(31)
    J = rng.normal(size=(12, 2))
    Q, _ = np.linalg.qr(rng.normal(size=(6, 2)))
    J[6:, 0] = Q[:, 0] / 0.2                         # fold 0's training rows: theta_0 well measured,
    J[6:, 1] = Q[:, 1] / CAL11_SIGMA_POST            # theta_1 just passing P3 (orthogonal columns)
    return T.Config(J, np.full(12, 10.0), np.eye(12), np.eye(12) * 0.1, [(-10.0, 10.0)] * 2, [(-3.0, 3.0)] * 2)


def _g5(sub, f):
    from core.calibration import identify as I
    return I.g5(sub, f, seed=None)


def _cv_ensemble(p, truth, n_req, base, replacement):
    """A cross-validation toy ensemble with G5 conditioning (failing toys renewed with the next seed, not counted in
    the ratio test) and without the 20% stop, so that the size can be measured on both sides of 20%."""
    vals, X, g5f, decided, i = [], 0, 0, 0, 0
    while len(vals) < n_req and i < 50 * n_req:
        st, res = V.cv_toy(p, CAL11_FOLDS, truth, np.random.default_rng([*base, i]), (*base, i), 0, _g5)
        i += 1
        if st == "not-converged":
            X += 1
            if not replacement:
                vals.append(None)
            continue
        decided += 1
        if st == "g5-failed":
            g5f += 1
            continue
        vals.append(res)
    return {"values": [v for v in vals if v is not None], "X": X, "g5_failed": g5f, "decided": decided,
            "complete": len(vals) >= n_req}


def cal11_block(theta1: str, r0: int, reps: int) -> list:
    j = CAL11_THETA1.index(theta1)
    cfg = _cal11_config()
    truth = np.array([0.3, float(theta1)])
    rows = []
    for r in range(r0, r0 + reps):
        p = T.make(cfg, truth, data_seed=_int(11, r, j, 1), mc_seed=_int(11, r, j, 2))
        row = {"r": r}
        data_ok = True
        for fi, frows in enumerate(CAL11_FOLDS):          # conditioning: every fold passes G5 on the actual data
            sub, f = V.fold_fit(p, frows, (cal_seed(11, r), j, 3, fi), n_start=0)
            if not f.converged or _g5(sub, f)["status"] != "passed":
                data_ok = False
                break
        row["data_folds_pass"] = data_ok
        if not data_ok:
            rows.append(row)
            continue
        _, f0 = V.fold_fit(p, np.arange(0), (cal_seed(11, r), j, 4), n_start=0)
        est = _cv_ensemble(p, f0.beta, CAL11_NCHAT, (cal_seed(11, r), j, 5), True)
        ref = _cv_ensemble(p, f0.beta, CAL11_NREF, (cal_seed(11, r), j, 6), False)
        row.update(chat={k: est[k] for k in ("X", "g5_failed", "decided", "complete")},
                   ref={k: ref[k] for k in ("X", "g5_failed", "decided", "complete")})
        if not (est["complete"] and ref["complete"]):
            rows.append(row)
            continue
        Cplus, factors = {}, {}
        for fi, frows in enumerate(CAL11_FOLDS):
            R = np.array([v[fi] for v in est["values"]])
            Cf = np.cov(R, rowvar=False).reshape(len(frows), len(frows))
            Cplus[fi], kf = V.c_r_plus(Cf, np.sqrt(np.clip(np.diag(Cf), 1e-300, None)), [])
            factors[fi] = V.chat_factor(R.shape[0], kf)
        obs = V.cv_statistic(p, CAL11_FOLDS, (cal_seed(11, r), j, 7), Cplus, factors, 0, _g5)
        if obs["status"] != "ok":
            row["observed"] = obs.get("finding")
            rows.append(row)
            continue
        Tr = [sum(float(v[fi] @ Cplus[fi] @ v[fi]) * factors[fi] for fi in range(len(CAL11_FOLDS)))
              for v in ref["values"]]
        row.update(T_cv=obs["T_cv"], p=F.testing_pvalue(obs["T_cv"], Tr, ref["X"]))
        rows.append(row)
    return rows


def cal11_judge(rows_by: dict) -> dict:
    out, ok = {}, True
    for key, rows in rows_by.items():
        dec = [x for x in rows if "p" in x]
        g5f = sum(x[e]["g5_failed"] for x in rows if "chat" in x for e in ("chat", "ref"))
        decided = sum(x[e]["decided"] for x in rows if "chat" in x for e in ("chat", "ref"))
        prop = g5f / max(decided, 1)
        size = float(np.mean([x["p"] <= CAL11_ALPHA for x in dec])) if dec else None
        rec = {"theta1": float(key), "reps": len(rows), "data_folds_pass": sum(bool(x["data_folds_pass"]) for x in rows),
               "decided": len(dec), "g5_proportion": prop, "size": size,
               "size_bias": None if size is None else size / CAL11_ALPHA - 1}
        if prop < 0.20:
            rec["passed"] = bool(size is not None and abs(size - CAL11_ALPHA) <= 0.25 * CAL11_ALPHA)
            ok = ok and rec["passed"]
        else:
            rec["passed"] = None
            rec["bias_exceeds_25pct"] = None if size is None else bool(abs(size - CAL11_ALPHA) > 0.25 * CAL11_ALPHA)
        out[key] = rec
    return {"calibration": 11, "row": 2014, "configurations": out, "passed": bool(ok),
            "rule": "below 20% G5 failures in the cross-validation toys: size within alpha +- 25% (alpha = 0.05); above "
                    "20% the size bias reported (Part B's 'no longer negligible' confirmed if > 25%)"}


# ------------------------------------------------------------------ calibration 15: basins
CAL15_VARIANTS = {"exact": (2.0, 2.0, (1.0, 0.6)), "broken": (2.0, 2.3, (1.0, 0.6)),
                  "bifurcation": (2.0, 2.0, (0.82, 0.78))}
CAL15_MODES = ("zero", "crn", "independent")
CAL15_THETA = {"a": {"bounds": (0.0, 2.0), "prior": (0.3, 1.3)}, "b": {"bounds": (0.0, 2.0), "prior": (0.3, 1.3)}}
CAL15_NAMES = ["sum_mean", "sum_width", "sum_m3"]
CAL15_RESEEDS = 10
CAL15_EXPOSURE, CAL15_MC = 2000, 8000
CAL15_MATCH = 3.0          # basins matched by position: max_i |d theta_i| / sigma_tot,i < 3 (the mirror basins are
                           # ~80 sigma apart; independent MC samples move a basin by ~0.5 sigma)


def _cal15_problem(variant, r, j, k=0):
    al, be, _ = CAL15_VARIANTS[variant]
    return TP.ToyProblem(lambda n, al=al, be=be: toy.build_bimodal(n, al, be), CAL15_NAMES, CAL15_THETA,
                         exposure=CAL15_EXPOSURE, mc_events=CAL15_MC, mc_seed=(cal_seed(15, r), j, 1, k),
                         boot_seed=(cal_seed(15, r), j, 2), links={"sum_mean": "identity", "sum_m3": "identity"})


def _signature(f) -> dict | None:
    if not f.converged:
        return None
    basins = sorted(([b["theta"], b["sigma_tot"]] for b in getattr(f, "basins", []) if b["converged"]),
                    key=lambda x: tuple(x[0]))
    return {"theta_hat": f.beta[:2].tolist(), "sigma_tot": f.sigma_tot.tolist(), "basins": basins,
            "tie": "tie" in f.flags, "multimodal": "multimodal" in f.flags}


def _same(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if len(a["basins"]) != len(b["basins"]) or a["tie"] != b["tie"]:
        return False

    def close(x, y, s):
        return float(np.max(np.abs(np.asarray(x) - np.asarray(y)) / np.asarray(s))) < CAL15_MATCH
    for (x, s), (y, _) in zip(a["basins"], b["basins"]):
        if not close(x, y, s):
            return False
    return close(a["theta_hat"], b["theta_hat"], a["sigma_tot"])


def cal15_block(variant: str, mode: str, r0: int, reps: int) -> list:
    j = list(CAL15_VARIANTS).index(variant) * len(CAL15_MODES) + CAL15_MODES.index(mode)
    truth = np.asarray(CAL15_VARIANTS[variant][2], float)
    rows = []
    for r in range(r0, r0 + reps):
        p = _cal15_problem(variant, r, j)
        b = np.r_[truth, np.zeros(p.layout.n_beta - 2)]
        p.observed = p.simulate(b, _rng(15, r, j), nominal=False)
        if mode != "zero":                                # sigma_noise at the theta-hat of a preliminary fit
            f0 = F.find_extremum(p, (cal_seed(15, r), j, 4), p.initial_beta())
            p.sigma_noise = TP.estimate_sigma_noise(p, f0.beta if f0.converged else p.initial_beta(),
                                                    seed=(cal_seed(15, r), j, 5))
        sigs, extra = [], {}
        for k in range(CAL15_RESEEDS + 1):
            q = p
            if mode == "independent" and k:
                q = _cal15_problem(variant, r, j, k)          # an independent MC sample for this reseeding
                q.observed, q.sigma_noise = p.observed, p.sigma_noise
            f = F.find_extremum(q, (cal_seed(15, r), j, 3, k), q.initial_beta())
            sigs.append(_signature(f))
            if k == 0:
                sp = np.asarray(F.sigma_prior(q))
                extra = {"admitted_ratio": [list(np.asarray(bb["sigma_tot"]) / sp) for bb in getattr(f, "basins", [])],
                         "nonadmitted_ratio": [x["sigma_ratio"] for x in getattr(f, "nonidentified", [])],
                         "flags": list(f.flags)}
        stable = all(_same(sigs[0], s) for s in sigs[1:])
        th = sigs[0]["theta_hat"] if sigs[0] else None
        outside = None
        if th is not None:
            mirror = truth[::-1]
            outside = bool(np.linalg.norm(np.asarray(th) - mirror) < np.linalg.norm(np.asarray(th) - truth))
        rows.append({"r": r, "sigma_noise": float(p.sigma_noise), "stable": bool(stable), "signature": sigs[0],
                     "n_unstable": int(sum(not _same(sigs[0], s) for s in sigs[1:])), "outside_truth_basin": outside,
                     **extra})
    return rows


def cal15_judge(rows_by: dict) -> dict:
    out, ok = {}, True
    for key, rows in rows_by.items():
        n = len(rows)
        st = float(np.mean([x["stable"] for x in rows])) if n else None
        adm = np.array([v for x in rows for rr in x.get("admitted_ratio", []) for v in rr])
        non = np.array([v for x in rows for rr in x.get("nonadmitted_ratio", []) for v in rr])
        rec = {"toys": n, "stable_fraction": st, "passed": bool(n and st >= 0.99),
               "admitted_ratio_max": float(adm.max()) if adm.size else None,
               "nonadmitted_ratio_min": float(non.min()) if non.size else None,
               "admitted_in_band_1.00_1.02": int(np.sum((adm > 1.0) & (adm < 1.02))),
               "nonadmitted_in_band_1.00_1.02": int(np.sum((non > 1.0) & (non < 1.02))),
               "outside_truth_basin": float(np.mean([x["outside_truth_basin"] for x in rows
                                                     if x["outside_truth_basin"] is not None])) if n else None,
               "multimodal_fraction": float(np.mean([bool(x["signature"] and x["signature"]["multimodal"])
                                                     for x in rows])) if n else None,
               "sigma_noise_median": float(np.median([x["sigma_noise"] for x in rows])) if n else None}
        ok = ok and rec["passed"]
        out[key] = rec
    return {"calibration": 15, "row": 2018, "configurations": out, "passed": bool(ok),
            "rule": "the classification unchanged under 10 reseedings in >= 99% of toys (each variant and noise "
                    "mode); sigma_tot / sigma_prior of admitted and non-admitted endpoints reported; G8 items wait"}


# ------------------------------------------------------------------ the task table, tasks and merge
def _tasks() -> list:
    t = []
    for c in CAL2_Q:
        t += [("cal2", {"config": c, "r0": 250 * i, "reps": 250}) for i in range(8)]
    for lam in CAL4_SIGMA:
        for resp in CAL4_RESP:
            t += [("cal4", {"lam": lam, "resp": resp, "r0": 250 * i, "reps": 250}) for i in range(4)]
    for th in CAL11_THETA1:
        t += [("cal11", {"theta1": th, "r0": 100 * i, "reps": 100}) for i in range(20)]
    for v in CAL15_VARIANTS:
        for m in CAL15_MODES:
            t += [("cal15", {"variant": v, "mode": m, "r0": 10 * i, "reps": 10}) for i in range(100)]
    return t


TASKS = _tasks()
BLOCKS = {"cal2": cal2_block, "cal4": cal4_block, "cal11": cal11_block, "cal15": cal15_block}


def _key(name, kw):
    if name == "cal2":
        return kw["config"]
    if name == "cal4":
        return f"{kw['lam']}|{kw['resp']}"
    if name == "cal11":
        return kw["theta1"]
    return f"{kw['variant']}|{kw['mode']}"


def run_task(i: int, out_dir: Path, sizes: dict | None = None) -> dict:
    name, kw = TASKS[i]
    kw = {**kw, **(sizes or {})}
    t0 = time.time()
    rows = BLOCKS[name](**kw)
    extra = {}
    if name == "cal4" and kw["r0"] == 0:
        extra["lambda_P8"] = cal4_lambda(kw["lam"], _cal4_cfg_index(kw["lam"], kw["resp"]))
    rec = {"task": i, "calibration": name, "kwargs": kw, "key": _key(name, kw), "rows": rows, **extra,
           "seconds": time.time() - t0, "provenance": G.provenance(), "label": "synthetic"}
    out_dir.mkdir(parents=True, exist_ok=True)
    io.write_json(str(out_dir / f"task_{i:04d}.json"), io.jsonable(rec))
    return rec


def merge(out_dir: Path, out: Path) -> dict:
    recs = {}
    for i in range(len(TASKS)):
        f = out_dir / f"task_{i:04d}.json"
        recs[i] = json.loads(f.read_text()) if f.exists() else None
    missing = [i for i, r in recs.items() if r is None]
    commits = {r["provenance"]["commit"] for r in recs.values() if r}
    dirty = any(r["provenance"].get("dirty") for r in recs.values() if r)
    by = {}
    lambdas = {}
    for r in recs.values():
        if r:
            by.setdefault(r["calibration"], {}).setdefault(r["key"], []).extend(r["rows"])
            if "lambda_P8" in r:
                lambdas[r["key"]] = r["lambda_P8"]
    results = {}
    if "cal2" in by:
        results["cal2"] = cal2_judge(by["cal2"])
    if "cal4" in by:
        results["cal4"] = cal4_judge(by["cal4"], lambdas)
    if "cal11" in by:
        results["cal11"] = cal11_judge(by["cal11"])
    if "cal15" in by:
        results["cal15"] = cal15_judge(by["cal15"])
    complete = not missing and len(commits) == 1 and not dirty
    rep = {"array": "deferred section 8.7 calibrations, batch A", "complete": complete, "missing_tasks": missing,
           "commits": sorted(commits), "dirty": dirty, "results": results,
           "passed": {k: v["passed"] for k, v in results.items()}, "provenance": G.provenance(), "label": "synthetic"}
    io.write_json(str(out), io.jsonable(rep))
    return rep


LOCAL = {"cal8": cal8_tau_num}
SMOKE = {"cal2": ("cal2", {"config": "near-linear", "r0": 900000, "reps": 2}),
         "cal4": ("cal4", {"lam": "0.1", "resp": "cubic", "r0": 900000, "reps": 2}),
         "cal11": ("cal11", {"theta1": "0.8", "r0": 900000, "reps": 2}),
         "cal15": ("cal15", {"variant": "broken", "mode": "independent", "r0": 900000, "reps": 1})}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--task", type=int)
    ap.add_argument("--merge")
    ap.add_argument("--local", dest="item", choices=sorted(LOCAL))
    ap.add_argument("--smoke", choices=sorted(SMOKE))
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.task is not None:
        r = run_task(a.task, Path(a.out))
        print(json.dumps({"task": r["task"], "calibration": r["calibration"], "key": r["key"], "seconds": r["seconds"]}))
        return 0
    if a.merge:
        r = merge(Path(a.merge), Path(a.out))
        print(json.dumps({"complete": r["complete"], "passed": r["passed"], "missing": len(r["missing_tasks"])}))
        return 0 if r["complete"] and all(r["passed"].values()) else 1
    if a.item:
        t0 = time.time()
        r = LOCAL[a.item]()
        r.update(seconds=time.time() - t0, provenance=G.provenance(), label="synthetic")
        io.write_json(a.out, io.jsonable(r))
        print(json.dumps({"calibration": r["calibration"], "passed": r["passed"], "seconds": r["seconds"]}))
        return 0 if r["passed"] else 1
    if a.smoke:
        name, kw = SMOKE[a.smoke]
        t0 = time.time()
        rows = BLOCKS[name](**kw)
        rec = {"calibration": name, "kwargs": kw, "rows": rows, "seconds": time.time() - t0, "label": "smoke"}
        io.write_json(a.out, io.jsonable(rec))
        print(json.dumps({"calibration": name, "seconds": rec["seconds"], "rows": len(rows)}))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
