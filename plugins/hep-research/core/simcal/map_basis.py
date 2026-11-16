"""Efficiency-map bases of the simulator calibration workflow (Part B section 6.7 "Three layers of MC error", "Two
efficiency map modes", D28, D84; section 14 `calib_propagate.py`; section 15.3a; phase 3, WP-D).

- Native coordinates: (component, bin, channel), one mapped `efficiency-map/1` per scintillation component, its bins
  in order and its `channels` in order; "not detected" is implied. The centre is g4sim's nominal map eps_0 = k/n
  (replica 0), never the replica mean (accepted 2026-11-09, M1).
- Native basis (fixed map): delta_r = eps_r - mean over r of g4sim's Dirichlet replicas r = 1..R
  (`efficiency_map.efficiencies`, R >= 100 by `efficiency_map.replicas`); [delta_1 ... delta_R] / sqrt(R - 1) = W S V^T,
  B_map = W S; phi_map ~ N(0, I) on B_map. No truncation. The registration key holds the map hashes (the map part of
  the model identity, `model_identity.map_part`), R, the sampler's CORE_VERSION, the coordinate order, the centre and
  the basis version.
- U of a study: from predictions at the R replicas (digitized through `g4sim-digi-job/1` or `map_replica`), U = M V with
  M the replica differences of mu divided by sqrt(R - 1) (a secant for mu not linear in eps); or, for an observable
  the plan records as linear in eps, the linear construction U = J B_map (decided 2026-11-09; calib_design.py rejects
  it for any other observable).
- Joint-pattern replicas (map varies with theta, shared seed, D28): the pattern table of the scan (bin of the emission
  point and the category at every design point), the scan key, the draws G_rp ~ Gamma(m_p) from SubStream(key, p, 0)
  and g_rbc ~ Gamma(1/2) from SubStream(key, b, 1 + u) with key rng._key("calib-map-joint/1", scan_key, component, r),
  so that the marginal at every design point is g4sim's Dirichlet(k + 1/2); U_j = M_j / sqrt(R - 1) in replica
  coordinates. For observables linear in eps the analytic (linearized multinomial) covariance of the same table, with
  U_j the row blocks of one factor L of [Sigma_jl] = L L^T.
- Propagation into studies: the cross covariance of two studies of one map is U_a U_b^T in the shared native basis,
  whatever the observable order; joining separate per-study PCAs by component index is rejected (section 15.3a). Local
  dimension reduction (optional; all directions may always be kept): the smallest m with the per-observable 1% rule and
  s_perp = tr(V_G^-1 U_perp U_perp^T) <= 0.05 (settled by computation, en/compute-19-g9.md; to be confirmed).
"""
from __future__ import annotations

import hashlib
import math

import numpy as np

from core import CORE_VERSION
from core.canonical import canonical_json, canonical_sha256
from core.simulation import efficiency_map, rng

from . import model_identity

BASIS_VERSION = "calib-map-basis/1"
JOINT_PREFIX = "calib-map-joint/1"
REDUCTION_OBSERVABLE = 0.01        # condition 1: discarded variance <= 1% of each observable's map variance
REDUCTION_S_PERP = 0.05            # condition 2: s_perp <= 0.05 per study


class BasisError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _decimal(x: float) -> str:
    return repr(float(x))


def _maps(maps: dict) -> list:
    """[(component, document)] in component order; every document a mapped efficiency-map/1 of that component."""
    out = []
    for comp, doc in sorted(maps.items(), key=lambda kv: int(kv[0])):
        form = doc.get("form") or {}
        if form.get("kind") != efficiency_map.FORM:
            raise BasisError("basis.not_mapped", f"component {comp}: the basis is defined on a mapped map")
        if int(form.get("component", comp)) != int(comp):
            raise BasisError("basis.component", f"map of component {form.get('component')} given as component {comp}")
        out.append((int(comp), doc))
    if not out:
        raise BasisError("basis.no_map", "no efficiency map")
    return out


def coordinates(maps: dict) -> list:
    """The native coordinates [component, bin, channel] in order."""
    return [[c, int(row["bin"]), ch] for c, doc in _maps(maps) for row in doc["form"]["bins"] for ch in doc["channels"]]


def map_vector(maps: dict, replica: int = 0) -> np.ndarray:
    """eps in native coordinates: the nominal k/n (replica 0) or g4sim's replica r."""
    return np.array([e for _, doc in _maps(maps) for row in doc["form"]["bins"]
                     for e in efficiency_map.efficiencies(doc, int(row["bin"]), replica)], float)


def dirichlet_mean(maps: dict) -> np.ndarray:
    """The mean of g4sim's replicas, (k + 1/2) / (n + (C + 1) / 2) per bin and channel (the Jeffreys posterior mean;
    never the nominal map, section 6.7)."""
    out = []
    for _, doc in _maps(maps):
        C = len(doc["channels"])
        for row in doc["form"]["bins"]:
            out += [(k + 0.5) / (row["emitted"] + (C + 1) / 2) for k in row["detected"]]
    return np.array(out, float)


def _replica_numbers(maps: dict, R: int, first: int = 1) -> list:
    for _, doc in _maps(maps):
        try:
            efficiency_map.replicas(doc, R)
        except efficiency_map.MapError as exc:
            raise BasisError("basis.replicas", str(exc)) from None
    return list(range(first, first + R))


def native_basis(maps: dict, R: int) -> dict:
    """The native basis of a fixed map set from g4sim's replicas 1..R: B_map = W S, V (R x rank), eps_0 and the
    registration key."""
    numbers = _replica_numbers(maps, R)
    E = np.stack([map_vector(maps, r) for r in numbers])
    return basis_from_replicas(maps, E, numbers)


def basis_from_replicas(maps: dict, E: np.ndarray, numbers: list) -> dict:
    """The basis of replica vectors E (R x n_coords): delta = E - mean, SVD of delta^T / sqrt(R - 1)."""
    R = E.shape[0]
    X = (E - E.mean(axis=0)).T / math.sqrt(R - 1)
    W, S, Vt = np.linalg.svd(X, full_matrices=False)
    keep = S > 1e-12 * max(float(S[0]) if S.size else 0.0, 1e-300)
    coords = coordinates(maps)
    eps0 = map_vector(maps, 0)
    return {"coordinates": coords, "eps0": eps0, "B_map": W[:, keep] * S[keep], "V": Vt[keep].T, "R": R,
            "replicas": [int(numbers[0]), int(numbers[-1])], "key": registration_key(maps, R, coords, eps0)}


def registration_key(maps: dict, R: int, coords: list, eps0) -> dict:
    """The registration key of a native basis (section 6.7): map hashes as the map part of the model identity (the
    document exactly as built, D83 (1): never rewritten), R, the sampler's CORE_VERSION, coordinate order, centre and
    basis version; `id` is its SHA-256."""
    parts = {str(c): model_identity.map_part(doc) or {} for c, doc in _maps(maps)}
    key: dict = {"maps": {c: p["map_sha256"] for c, p in parts.items()}, "R": int(R),
           "sampler": f"core {CORE_VERSION}", "coordinates_sha256": canonical_sha256(coords),
           "centre_sha256": canonical_sha256([_decimal(x) for x in eps0]), "centre": "k/n",
           "basis_version": BASIS_VERSION}
    return {**key, "id": canonical_sha256(key)}


# ------------------------------------------------------------------ U of a study
def replica_differences(predictions) -> np.ndarray:
    """M (n_obs x R): column r the prediction at replica r minus the mean over the R replicas, divided by sqrt(R - 1)."""
    P = np.asarray(predictions, float)
    if P.ndim != 2 or P.shape[0] < 2:
        raise BasisError("basis.predictions", "predictions at the replicas are an (R x n_obs) array with R >= 2")
    return (P - P.mean(axis=0)).T / math.sqrt(P.shape[0] - 1)


def u_digitized(predictions, basis: dict) -> np.ndarray:
    """U = M V from the predictions at the basis's own replicas 1..R (digitized through g4sim-digi-job/1 or map_replica;
    the secant over the replica spread for mu not linear in eps)."""
    P = np.asarray(predictions, float)
    if P.shape[0] != basis["R"]:
        raise BasisError("basis.predictions", f"{P.shape[0]} predictions for a basis of R = {basis['R']} replicas")
    return replica_differences(P) @ basis["V"]


def u_linear(J_eps, basis: dict) -> np.ndarray:
    """U = J B_map with J = d mu / d eps at eps_0 (n_obs x n_coords): only for observables recorded as linear in eps
    (calib_design.py `u_construction_findings`)."""
    J = np.atleast_2d(np.asarray(J_eps, float))
    if J.shape[1] != basis["B_map"].shape[0]:
        raise BasisError("basis.jacobian", f"J has {J.shape[1]} columns, the basis {basis['B_map'].shape[0]} coordinates")
    return J @ basis["B_map"]


# ------------------------------------------------------------------ joint-pattern replicas (D28)
def pattern_table(bins: dict, detections: list, channels: list) -> list:
    """The pattern table of a shared-seed scan: bins {event: bin of the emission point} (common to the scan, its
    primaries agree), detections[j] {event: detecting channel} of design point j (plan order), channels[j] map j's
    `channels`. Rows [b, c_1, ..., c_J, m_p] in lexicographic order of (b; c_1..c_J), c_j = 0 not detected, 1..C_j
    the channel in map j's order."""
    if len(detections) != len(channels) or not detections:
        raise BasisError("joint.points", "one detection map and one channel list per design point")
    counts: dict = {}
    for event, b in bins.items():
        codes = []
        for j, (det, chans) in enumerate(zip(detections, channels)):
            ch = det.get(event)
            if ch is None:
                codes.append(0)
            elif ch in chans:
                codes.append(1 + list(chans).index(ch))
            else:
                raise BasisError("joint.channel", f"event {event}: channel {ch!r} is not among map {j}'s channels")
        key = (int(b), *codes)
        counts[key] = counts.get(key, 0) + 1
    extra = [e for det in detections for e in det if e not in bins]
    if extra:
        raise BasisError("joint.events", f"detections in events with no emission point, e.g. {extra[0]}")
    return [[*k, m] for k, m in sorted(counts.items())]


def pattern_sha256(table: list) -> str:
    return hashlib.sha256(canonical_json([[int(x) for x in row] for row in table]).encode("utf-8")).hexdigest()


def scan_key(map_shas: list, logical_run_seed: int, first_event: int, n_map: int) -> str:
    """SHA-256 hex of the canonical JSON of [[sorted map_sha256], logical_run_seed, first event, N_map]."""
    return hashlib.sha256(canonical_json([sorted(map_shas), int(logical_run_seed), int(first_event), int(n_map)])
                          .encode("utf-8")).hexdigest()


def pattern_findings(table: list, maps: list) -> list:
    """The pattern table against the maps of the scan (plan order): per bin the emitted photons, per (bin, channel)
    the detections of map j. A disagreement means the table is not that of these mapping runs."""
    out: list = []
    J = len(maps)
    for j, doc in enumerate(maps):
        rows = {int(r["bin"]): r for r in doc["form"]["bins"]}
        C = len(doc["channels"])
        n: dict = {}
        k: dict = {}
        for row in table:
            b, c, m = row[0], row[1 + j], row[-1]
            n[b] = n.get(b, 0) + m
            if c:
                k[(b, c)] = k.get((b, c), 0) + m
        if len(table) and len(table[0]) != J + 2:
            out.append({"code": "joint.table_width", "message": f"rows have {len(table[0]) - 2} design points, not {J}"})
            break
        for b, r in rows.items():
            if n.get(b, 0) != r["emitted"] or any(k.get((b, c + 1), 0) != r["detected"][c] for c in range(C)):
                out.append({"code": "joint.counts", "message": f"design point {j}, bin {b}: the pattern table's counts "
                            "are not the map's emitted and detected counts", "point": j, "bin": b})
        if set(n) - set(rows):
            out.append({"code": "joint.counts", "message": f"design point {j}: the table has bins the map has not"})
    return out


def _union(channels: list) -> list:
    return sorted({c for chans in channels for c in chans})


def joint_key(scan: str, component: int, r: int) -> tuple:
    return rng._key(JOINT_PREFIX, scan, int(component), int(r))


def joint_replica(table: list, channels: list, scan: str, component: int, r: int) -> list:
    """Joint-pattern replica r >= 1 of every design point: [ {bin: [eps_jbc for c in map j's channels]} for j ]."""
    if r < 1:
        raise BasisError("joint.replica", "replica 0 is the nominal k_j/n and is not drawn")
    key = joint_key(scan, component, r)
    union = _union(channels)
    G = [rng.SubStream(key, p, 0).gamma(float(row[-1])) for p, row in enumerate(table)]
    small: dict = {}

    def g(b, u):
        if (b, u) not in small:
            small[(b, u)] = efficiency_map._gamma(rng.SubStream(key, b, 1 + u), 0.5)
        return small[(b, u)]

    out = []
    for j, chans in enumerate(channels):
        codes = [0] + [1 + union.index(c) for c in chans]
        tot: dict = {}
        for Gp, row in zip(G, table):
            b, c = row[0], row[1 + j]
            tot.setdefault(b, [0.0] * len(codes))[c] += Gp
        point = {}
        for b in sorted(tot):
            vals = [tot[b][c] + g(b, codes[c]) for c in range(len(codes))]
            s = math.fsum(vals)
            point[b] = [v / s for v in vals[1:]]
        out.append(point)
    return out


def joint_replicas(table: list, channels: list, scan: str, component: int, R: int) -> list:
    """R joint-pattern replicas: per design point an (R x n_coords_j) array in map j's native coordinates (bins in
    order, channels in map j's order). R >= 100 (as for g4sim's replicas; D84)."""
    if R < efficiency_map.MINIMUM_REPLICAS:
        raise BasisError("basis.replicas", f"{R} replicas; at least {efficiency_map.MINIMUM_REPLICAS} (D84)")
    rows: list = [[] for _ in channels]
    for r in range(1, R + 1):
        for j, point in enumerate(joint_replica(table, channels, scan, component, r)):
            rows[j].append([e for b in sorted(point) for e in point[b]])
    return [np.array(x, float) for x in rows]


def nominal_points(table: list, channels: list) -> list:
    """eps_0 = k_j / n per design point from the table (the centre of every design point, section 6.7)."""
    out = []
    for j, chans in enumerate(channels):
        n: dict = {}
        k: dict = {}
        for row in table:
            b, c, m = row[0], row[1 + j], row[-1]
            n[b] = n.get(b, 0) + m
            if c:
                k[(b, c)] = k.get((b, c), 0) + m
        out.append(np.array([k.get((b, c), 0) / n[b] for b in sorted(n) for c in range(1, len(chans) + 1)], float))
    return out


def analytic_covariance(table: list, channels: list) -> np.ndarray:
    """The linearized multinomial covariance of the stacked [eps_1; ...; eps_J] from the pattern table (per bin,
    Cov = (sum_p f_p a_p a_p^T - a-bar a-bar^T) / n_b with a_p the pattern's category indicators); no finite-R noise
    (D84). For observables linear in eps only."""
    sizes: list = []
    offsets: list = []
    bins = sorted({row[0] for row in table})
    for chans in channels:
        offsets.append(sum(sizes))
        sizes.append(len(bins) * len(chans))
    N = sum(sizes)
    Sigma = np.zeros((N, N))
    for bi, b in enumerate(bins):
        rows = [row for row in table if row[0] == b]
        n_b = sum(row[-1] for row in rows)
        A = np.zeros((len(rows), N))
        for p, row in enumerate(rows):
            for j, chans in enumerate(channels):
                c = row[1 + j]
                if c:
                    A[p, offsets[j] + bi * len(chans) + c - 1] = 1.0
        f = np.array([row[-1] for row in rows], float) / n_b
        abar = f @ A
        Sigma += ((A.T * f) @ A - np.outer(abar, abar)) / n_b
    return Sigma


def joint_registration_key(scan: str, component: int, table: list, channels: list, R: int) -> dict:
    """The registration key of the joint-pattern replicas of one scan and component (section 6.7)."""
    centre = nominal_points(table, channels)
    key = {"scan_key": scan, "component": int(component), "pattern_table_sha256": pattern_sha256(table),
           "coordinates": [list(c) for c in channels], "centre": "k_j/n",
           "centre_sha256": canonical_sha256([[_decimal(x) for x in e] for e in centre]), "R": int(R),
           "sampler": f"core {CORE_VERSION}", "prefix": JOINT_PREFIX}
    return {**key, "id": canonical_sha256(key)}


def u_joint(predictions: list) -> list:
    """U_j = M_j / sqrt(R - 1) (columns r, replica coordinates) from each design point's predictions at its
    joint-pattern replicas (R x n_obs); no SVD per design point (its signs and order are arbitrary)."""
    U = [replica_differences(P) for P in predictions]
    if len({u.shape[1] for u in U}) != 1:
        raise BasisError("joint.replicas", "every design point needs the same R replicas")
    return U


def u_analytic(J_points: list, Sigma: np.ndarray) -> list:
    """U_j for observables linear in eps from the analytic covariance: the observable covariance [J_j Sigma_jl J_l^T]
    = L L^T (eigendecomposition), U_j the row block j of L, so U(theta) U(theta)^T = sum_jl w_j w_l Sigma_obs,jl."""
    Js = [np.atleast_2d(np.asarray(J, float)) for J in J_points]
    off = np.cumsum([0] + [J.shape[1] for J in Js])
    if off[-1] != Sigma.shape[0]:
        raise BasisError("joint.jacobian", "the Jacobians do not cover the stacked coordinates of the covariance")
    n = Js[0].shape[0]
    Big = np.zeros((n * len(Js), Sigma.shape[0]))
    for j, J in enumerate(Js):
        Big[j * n:(j + 1) * n, off[j]:off[j + 1]] = J
    S = Big @ Sigma @ Big.T
    lam, E = np.linalg.eigh(0.5 * (S + S.T))
    keep = lam > 1e-14 * max(float(lam.max()), 1e-300)
    L = E[:, keep] * np.sqrt(lam[keep])
    return [L[j * n:(j + 1) * n] for j in range(len(Js))]


# ------------------------------------------------------------------ propagation into studies (section 15.3a)
def study(basis_key: str, observables: list, U, local: dict | None = None) -> dict:
    """A study's map term on a registered basis: U (n_obs x k) on the native coefficients phi_map, or, after a local
    reduction, U_loc on phi_loc = Q_m^T phi_map with the export map Q_m."""
    rec = {"kind": "native-basis", "basis": basis_key, "observables": list(observables), "U": np.asarray(U, float)}
    if local is not None:
        rec["Q_m"] = np.asarray(local["Q_m"], float)
    return rec


def native_u(rec: dict) -> np.ndarray:
    """U in the native coefficients: U, or U_loc Q_m^T after a local reduction (the explicit linear map, section 6.7)."""
    return rec["U"] @ rec["Q_m"].T if "Q_m" in rec else rec["U"]


def cross_covariance(a: dict, b: dict) -> dict:
    """The map-induced cross covariance of two studies (observables of a x observables of b), U_a U_b^T in the native
    basis. Rejected: studies on different bases, and a study whose shared variables are its own observable-space PCA
    joined to another's by component index (section 6.7, 15.3a)."""
    for rec in (a, b):
        if rec.get("kind") == "study-pca":
            raise BasisError("propagate.pca_by_index", "separate PCAs in each study's observable space joined by the "
                             "same component index are not shared variables (section 6.7, 15.3a); use the native basis")
        if rec.get("kind") != "native-basis":
            raise BasisError("propagate.basis_kind", f"unknown study kind {rec.get('kind')!r}")
    if a["basis"] != b["basis"]:
        raise BasisError("propagate.different_basis", "the two studies use different registered bases")
    return {"rows": a["observables"], "columns": b["observables"], "cov": native_u(a) @ native_u(b).T}


def study_pca(observables: list, U) -> dict:
    """The rejected construction (section 6.7): a PCA of U U^T in the study's own observable space; its k-th component
    is not the same variable as another study's k-th component."""
    U = np.asarray(U, float)
    lam, E = np.linalg.eigh(U @ U.T)
    order = np.argsort(lam)[::-1]
    return {"kind": "study-pca", "observables": list(observables),
            "U": E[:, order] * np.sqrt(np.clip(lam[order], 0.0, None))}


def _discarded(U, Q):
    return U - U @ Q @ Q.T


def local_reduction(U, V_G, rows_gaussian=None, nongaussian_rows=(), tau_num: float = 1e-10) -> dict:
    """The smallest m with, for every observable, var(U_perp) <= 1% of its map variance and s_perp = tr(V_G^-1 U_perp
    U_perp^T) <= 0.05 (V_G over the Gaussian rows, without nu, eta, phi_map). A Poisson or binomial row (no V_G) with
    a discarded variance above tau_num keeps every direction (D43). Returns m, s_perp, Q_m, U_loc = U Q_m and the
    local covariance U_perp U_perp^T (not shareable)."""
    U = np.asarray(U, float)
    _, lam, Qt = np.linalg.svd(U, full_matrices=False)
    Q_all = Qt.T
    k = int(np.sum(lam > 1e-12 * max(float(lam[0]) if lam.size else 0.0, 1e-300)))
    total = np.sum(U ** 2, axis=1)
    g = np.arange(U.shape[0]) if rows_gaussian is None else np.asarray(rows_gaussian, int)
    Vinv = np.linalg.inv(np.asarray(V_G, float))
    for m in range(0, k + 1):
        Q = Q_all[:, :m]
        Up = _discarded(U, Q)
        var = np.sum(Up ** 2, axis=1)
        s_perp = float(np.trace(Vinv @ Up[g] @ Up[g].T))
        c1 = bool(np.all(var <= REDUCTION_OBSERVABLE * total + 1e-300))
        ng = [i for i in nongaussian_rows if var[i] > tau_num]
        if (c1 and s_perp <= REDUCTION_S_PERP and not ng) or m == k:
            return {"m": m, "kept_all": m == k, "s_perp": s_perp, "Q_m": Q, "U_loc": U @ Q,
                    "U_perp_cov": Up @ Up.T, "shareable_part": "U_loc", "note": "U_perp U_perp^T enters V_G per block, "
                    "not shareable"}
    raise AssertionError("unreachable")


def local_reduction_scan(U_points: list, weights_points: list, V_G_points: list, rows_gaussian=None) -> dict:
    """Joint-pattern replicas: one rotation Q from the SVD of [U_1; ...; U_J] (rows stacked), with the two conditions
    applied to U(theta) = sum_j w_j(theta) U_j at every given point (design points and the Sobol points of P5; the
    regression weights can be negative). Returns the smallest m that holds at every point."""
    stacked = np.vstack([np.asarray(u, float) for u in U_points])
    _, lam, Qt = np.linalg.svd(stacked, full_matrices=False)
    k = int(np.sum(lam > 1e-12 * max(float(lam[0]) if lam.size else 0.0, 1e-300)))
    Ust = [np.asarray(u, float) for u in U_points]
    for m in range(0, k + 1):
        Q = Qt.T[:, :m]
        ok, worst = True, 0.0
        for w, V in zip(weights_points, V_G_points):
            Ut = np.sum([float(wj) * u for wj, u in zip(w, Ust)], axis=0)
            Up = _discarded(Ut, Q)
            g = np.arange(Ut.shape[0]) if rows_gaussian is None else np.asarray(rows_gaussian, int)
            s = float(np.trace(np.linalg.inv(np.asarray(V, float)) @ Up[g] @ Up[g].T))
            worst = max(worst, s)
            if not (np.all(np.sum(Up ** 2, 1) <= REDUCTION_OBSERVABLE * np.sum(Ut ** 2, 1) + 1e-300)
                    and s <= REDUCTION_S_PERP):
                ok = False
                break
        if ok or m == k:
            return {"m": m, "kept_all": m == k, "s_perp_worst": worst, "Q_m": Q}
    raise AssertionError("unreachable")
