"""The PDE split of Part B section 6.7 (decided by the author 2026-11-10, section 19-g4c; phase 3, WP-E): a SiPM PDE as a
response parameter (theta or phi) applied in the digitization job to an efficiency map built with every sensor surface's
`efficiency` = 1, allowed only when the PDE model is exactly the sensor surface's EFFICIENCY(E) (a scale p of it, or a
table PDE(E) that replaces it). Otherwise, or by the plan's choice, the PDE stays an optical property (route 0,
resimulation), which is always allowed.

Routes: 2_1 (default, wavelength-independent p: the job's efficiencies are p eps_c(b) of the efficiency-1 map); 3
(PDE(E): the efficiencies are sum_i PDE(E_i)/n_b over the detections of the efficiency-1 mapping run's photons.csv, the
transit histogram PDE-weighted and integerised to 10^6; route-3 replicas Dirichlet(k + 1/2) over (channel, energy cell)
categories); 1 (p theta, a readout system with an observable not linear in eps: each detected photon kept with
probability p from its own volume stream `<stage>/pde/<component>`, nested in p, before the sensor stages).

Checks: the contract rules (calib_contract.py: the PDE acts only as the sensor `efficiency`, no angle dependence, the
efficiency-1 map's sensor surfaces at 1 and its `surfaces_sha256` g4sim's hash of the production surfaces with the sensor
efficiencies set to 1, no PDE(E) as a constant scale, the `EFFICIENCY > 0` condition); the plan rules (calib_design.py,
remedy level plan: route 1 where p is theta and an observable is not linear in eps, the route-1 position and stream, key
distinctness, the `EFFICIENCY > 0` condition over the prior range, route 3's photons.csv against the map, the energy
grid, the surfaces hash of a theta scan's maps, and the split check with its nested pair of mapping runs). The bounds
are design values of section 8.7 (row 2009): results carry `provisional-thresholds`.

Inputs are loaded documents: photons.csv rows (event, scorer, volume, arrival time, transit, energy eV, emission point,
direction, parent; channel = "scorer/volume" as g4sim_efficiency_map.py names it), primaries.csv rows (event, ..., x, y,
z in columns 2-4) and the mapping template's world centre (a mapping template is a box of the world placed with no
rotation, so local = world - centre). Pure computation; NumPy and SciPy."""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import math
import re

import numpy as np
from scipy import stats

from core.canonical import canonical_sha256, load_spec_json
from core.geometry import expand
from core.simulation import conditions, digitize, efficiency_map, response, rng

FLAG = "provisional-thresholds"
CHI2_ALPHA = 0.01                 # section 8.7 row 2009: the split check's chi-square level
DTHETA_FRACTION = 0.1             # |d theta_i| + 2 sd(d theta_i) <= 0.1 sigma_tot,i^design
SPREAD_MULTIPLIER = 2.0
PAIR_ALPHA = 0.025                # the pair is sized with z_{1 - 0.025/d} (joint pass probability >= 0.94)
PSEUDO_MASS_FRACTION = 0.01       # route-3 grid: K_cat/2 <= 0.01 n_b per bin
VARIANCE_RATIO = 0.98             # route-3 grid: analytic Dirichlet variance >= 0.98 of the multinomial variance
TRANSIT_TOTAL = 10 ** 6           # route-3 transit histogram scaled to 10^6 and rounded (D83 (22))
PDE_REPLICA_KEY = "calib-map-pde/1"
JOINT_REPLICA_KEY = "calib-map-joint/1"
ROUTES = ("0", "2_1", "3", "1")
MODELS = ("scale", "table")
# surface types whose absorption branch tests EFFICIENCY > 0 (G4OpBoundaryProcess DielectricLUTDAVIS and
# CoatedDielectricDielectric; not configurable in g4sim 0.65.0)
EFFICIENCY_TEST_TYPES = ("dielectric_LUTDAVIS", "coated")
ROUTE1_POSITIONS = ("before-sensor",)
ROUTE1_APPLIES_TO = ("detected-photons",)
MAP_STREAM = re.compile(r"^efficiency_map/\d+$")
SAMPLER_VERSION = "core.simulation.rng Philox4x32-10, SubStream.gamma, efficiency_map._gamma boost"


class SplitError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _f(code: str, message: str, path: str = "$", **extra) -> dict:
    return {"code": "pde_split." + code, "path": path, "message": message, **extra}


def _plan_f(code: str, message: str, **extra) -> dict:
    return {"code": "pde_split." + code, "message": message, "remedy": "plan", **extra}


# ------------------------------------------------------------------ the PDE model
def table_arrays(table: dict) -> tuple[np.ndarray, np.ndarray]:
    """(energies eV, values) of a PDE(E) table {energy_eV, value}: increasing energies, values in [0, 1]."""
    try:
        e = np.array([float(x) for x in table["energy_eV"]], float)
        v = np.array([float(x) for x in table["value"]], float)
    except (KeyError, TypeError, ValueError) as exc:
        raise SplitError("table", f"a PDE(E) table is {{energy_eV, value}} of numbers ({exc!r})") from None
    if len(e) < 1 or len(e) != len(v) or np.any(np.diff(e) <= 0) or np.any((v < 0) | (v > 1)):
        raise SplitError("table", "a PDE(E) table has increasing energies and values in [0, 1]")
    return e, v


def pde_at(table: dict, energies) -> np.ndarray:
    """PDE(E) interpolated as Geant4 interpolates a surface's EFFICIENCY vector: linearly, with the edge values outside
    the table (G4PhysicsFreeVector::Value)."""
    e, v = table_arrays(table)
    return np.interp(np.asarray(energies, float), e, v)


def cell_mean(table: dict, low: float, high: float) -> float:
    """The mean of PDE(E) over [low, high], uniform in E (exact for the piecewise-linear interpolation)."""
    if high <= low:
        return float(pde_at(table, [low])[0])
    e, _ = table_arrays(table)
    knots = np.unique(np.concatenate([[low, high], e[(e > low) & (e < high)]]))
    vals = pde_at(table, knots)
    return float(np.sum(0.5 * (vals[1:] + vals[:-1]) * np.diff(knots)) / (high - low))


def zero_in_range(table: dict, low: float, high: float) -> bool:
    """Whether the interpolated PDE(E) reaches 0 on [low, high] (its minimum lies at a knot or an end)."""
    e, _ = table_arrays(table)
    pts = np.concatenate([[low, high], e[(e >= low) & (e <= high)]])
    return bool(np.any(pde_at(table, pts) <= 0.0))


def emission_range(map_document: dict) -> tuple[float, float]:
    """The energies the mapping run's emission spectrum reaches (its support: values > 0)."""
    s = (map_document.get("form") or {}).get("emission_spectrum") or {}
    e = [float(x) for x in s.get("energy_eV", [])]
    v = [float(x) for x in s.get("value", [])]
    if not e or len(e) != len(v):
        raise SplitError("emission", "the map has no emission spectrum")
    on = [x for i, x in enumerate(e) if v[i] > 0 or (i > 0 and v[i - 1] > 0) or (i + 1 < len(v) and v[i + 1] > 0)]
    return (min(on), max(on)) if on else (e[0], e[0])


# ------------------------------------------------------------------ photons.csv and primaries.csv
def read_photons(text: str) -> list[dict]:
    """The rows of a photons.csv (g4sim S7, NewScorers.hh PhotonDetected); `line` keeps the row's text as written for
    the byte-level nesting check of the split-check pair."""
    out = []
    for raw in text.splitlines():
        if not raw.strip() or raw.startswith("#") or raw.startswith("event"):
            continue
        row = next(csv.reader(io.StringIO(raw)))
        if len(row) < 6:
            raise SplitError("photons", f"a photons.csv row has {len(row)} columns: {raw[:80]!r}")
        out.append({"event": int(row[0]), "channel": f"{row[1]}/{row[2]}", "transit_ns": float(row[4]),
                    "energy_eV": float(row[5]), "line": raw.rstrip("\r")})
    return out


def read_primaries(text: str) -> dict:
    """{event: world emission point} of a primaries.csv (columns 2-4, as g4sim_efficiency_map.py reads them)."""
    out = {}
    for row in csv.reader(io.StringIO(text)):
        if not row or row[0] == "event" or row[0].startswith("#"):
            continue
        out[int(row[0])] = [float(x) for x in row[2:5]]
    return out


def photons_sha256(content: bytes) -> str:
    """photons_sha256: the SHA-256 of the file's bytes as g4sim wrote them (section 6.7)."""
    return hashlib.sha256(content).hexdigest()


def binned(map_document: dict, photons: list, primaries: dict, centre_mm) -> dict:
    """The mapping run binned by emission point in the map's (production) segmentation: {emitted: {bin: n_b},
    detections: [(bin, channel, transit_ns, energy_eV, event)]}."""
    form = map_document["form"]
    seg, half = form["segmentation"], form["half_mm"]
    centre = [float(x) for x in centre_mm]
    where: dict = {}
    emitted: dict = {}
    for event, point in primaries.items():
        b = efficiency_map.bin_of(seg, half, [p - c for p, c in zip(point, centre)])
        where[event] = b
        emitted[b] = emitted.get(b, 0) + 1
    dets = []
    for r in photons:
        if r["event"] not in where:
            raise SplitError("photons", f"a detection in event {r['event']}, which emitted no photon")
        dets.append((where[r["event"]], r["channel"], r["transit_ns"], r["energy_eV"], r["event"]))
    return {"emitted": emitted, "detections": dets}


def _transit_cell(edges: list, t: float) -> int:
    return min(int(t / edges[-1] * efficiency_map.TRANSIT_BINS), efficiency_map.TRANSIT_BINS - 1)


def photons_findings(map_document: dict, run: dict) -> list[dict]:
    """Route 3 (remedy level plan): the detections of the photons.csv, binned by emission point in the production
    segmentation, equal the map's emitted and `detected` counts per (bin, channel) and its transit counts."""
    out = []
    chans = list(map_document["channels"])
    edges = map_document["form"]["transit_edges_ns"]
    det: dict = {}
    tr: dict = {}
    for b, c, t, _, _ in run["detections"]:
        if c not in chans:
            out.append(_plan_f("photons_counts", f"photons.csv detects in channel {c!r}, which the map does not list"))
            continue
        det.setdefault(b, [0] * len(chans))[chans.index(c)] += 1
        tr.setdefault(b, [0] * efficiency_map.TRANSIT_BINS)[_transit_cell(edges, t)] += 1
    for row in map_document["form"]["bins"]:
        b = row["bin"]
        if run["emitted"].get(b, 0) != row["emitted"]:
            out.append(_plan_f("photons_counts", f"bin {b}: primaries.csv emits {run['emitted'].get(b, 0)}, the map "
                               f"{row['emitted']}"))
        if det.get(b, [0] * len(chans)) != list(row["detected"]):
            out.append(_plan_f("photons_counts", f"bin {b}: photons.csv detects {det.get(b, [0] * len(chans))}, the "
                               f"map {row['detected']} (not the mapping run of this map)"))
        if tr.get(b, [0] * efficiency_map.TRANSIT_BINS) != list(row["transit_counts"]):
            out.append(_plan_f("photons_counts", f"bin {b}: the transit counts of photons.csv differ from the map's"))
    return out


# ------------------------------------------------------------------ route 2_1 and route 3 (nominal)
def route21_efficiencies(efficiencies: dict, p: float) -> dict:
    """Route 2_1: p eps_c(b) for every bin, eps of the efficiency-1 map (nominal k/n, a g4sim replica, a joint-pattern
    replica or eps_0 + B_map phi_map). No random stream is added."""
    if not 0.0 <= float(p) <= 1.0:
        raise SplitError("p_range", f"a PDE p of {p} is outside [0, 1]")
    return {str(b): [float(p) * float(x) for x in v] for b, v in efficiencies.items()}


def map_efficiencies(map_document: dict, replica: int = 0) -> dict:
    return {str(r["bin"]): efficiency_map.efficiencies(map_document, r["bin"], replica)
            for r in map_document["form"]["bins"]}


def integerise(weights) -> tuple[list, float]:
    """A weighted histogram scaled to TRANSIT_TOTAL and rounded: (integer counts, the largest rounding error as a
    fraction of the total; <= 5e-7 per cell)."""
    w = np.asarray(weights, float)
    total = float(w.sum())
    if total <= 0:
        return [0] * len(w), 0.0
    scaled = w / total * TRANSIT_TOTAL
    counts = np.rint(scaled).astype(int)
    return [int(x) for x in counts], float(np.max(np.abs(counts - scaled)) / TRANSIT_TOTAL)


def route3(map_document: dict, run: dict, table: dict) -> dict:
    """Route 3: eps_bc = sum_i PDE(E_i)/n_b over the detections i of channel c in bin b of the efficiency-1 mapping run,
    and the transit histogram weighted by PDE(E_i) (on the map's transit edges), integerised to 10^6. Returns
    {efficiencies, transit (the job's mapped transit), rounding (largest error / total)}."""
    chans = list(map_document["channels"])
    edges = map_document["form"]["transit_edges_ns"]
    bins = [r["bin"] for r in map_document["form"]["bins"]]
    n = {r["bin"]: r["emitted"] for r in map_document["form"]["bins"]}
    eff = {b: np.zeros(len(chans)) for b in bins}
    tw = {b: np.zeros(efficiency_map.TRANSIT_BINS) for b in bins}
    q = pde_at(table, [d[3] for d in run["detections"]]) if run["detections"] else np.zeros(0)
    for (b, c, t, _, _), qi in zip(run["detections"], q):
        eff[b][chans.index(c)] += qi
        tw[b][_transit_cell(edges, t)] += qi
    counts, worst = {}, 0.0
    for b in bins:
        counts[str(b)], err = integerise(tw[b])
        worst = max(worst, err)
    return {"efficiencies": {str(b): [float(x) / n[b] for x in eff[b]] for b in bins},
            "transit": {"kind": "mapped", "edges_ns": list(edges), "counts": counts}, "rounding": worst}


# ------------------------------------------------------------------ route-3 replicas and the energy grid
def default_grid(table: dict) -> list[float]:
    """The default energy grid: the knots of the PDE(E) table (cells between consecutive knots)."""
    e, _ = table_arrays(table)
    if len(e) < 2:
        raise SplitError("grid", "a one-point PDE(E) table gives no energy cell: declare the grid")
    return [float(x) for x in e]


def categories(map_document: dict, run: dict, table: dict, grid: list) -> dict:
    """Per bin the route-3 categories: "not absorbed at a sensor" (u = 0), then the cells (channel, energy cell) in
    sorted order (channel name, cell); counts k_bu and weights w_u (0 for "not absorbed"; the mean PDE(E_i) over the
    detections of a cell, or for a cell with none the mean of PDE(E) over the cell, uniform in E).
    Returns {channels, cells, bins: {b: {n, k, w, q (per-detection PDE values)}}}."""
    g = np.asarray(grid, float)
    if len(g) < 2 or np.any(np.diff(g) <= 0):
        raise SplitError("grid", "an energy grid is at least two increasing edges")
    chans = list(map_document["channels"])
    ncell = len(g) - 1
    cells = sorted((c, e) for c in chans for e in range(ncell))
    index = {ce: 1 + i for i, ce in enumerate(cells)}
    out = {}
    empty_mean = [cell_mean(table, float(g[e]), float(g[e + 1])) for e in range(ncell)]
    per_bin: dict = {r["bin"]: [] for r in map_document["form"]["bins"]}
    for b, c, _, en, _ in run["detections"]:
        per_bin[b].append((c, en))
    for row in map_document["form"]["bins"]:
        b, n = row["bin"], row["emitted"]
        dets = per_bin[b]
        k = np.zeros(1 + len(cells))
        qsum = np.zeros(1 + len(cells))
        q = pde_at(table, [en for _, en in dets]) if dets else np.zeros(0)
        for (c, en), qi in zip(dets, q):
            e = int(min(max(np.searchsorted(g, en, side="right") - 1, 0), ncell - 1))
            u = index[(c, e)]
            k[u] += 1
            qsum[u] += qi
        k[0] = n - len(dets)
        w = np.zeros(1 + len(cells))
        for (_, e), u in index.items():
            w[u] = qsum[u] / k[u] if k[u] else empty_mean[e]
        chan_of = np.array([-1] + [chans.index(c) for c, _ in cells])
        out[b] = {"n": n, "k": k, "w": w, "q": q, "chan": chan_of}
    return {"channels": chans, "cells": cells, "bins": out}


def dirichlet_covariance(cat: dict, b) -> np.ndarray:
    """The analytic covariance of eps_b (channels) under Dirichlet(k + 1/2): W Cov(pi) W^T."""
    x = cat["bins"][b]
    a = x["k"] + 0.5
    a0 = a.sum()
    m = a / a0
    cov_pi = (np.diag(m) - np.outer(m, m)) / (a0 + 1.0)
    W = np.zeros((len(cat["channels"]), len(a)))
    for u in range(1, len(a)):
        W[x["chan"][u], u] = x["w"][u]
    return W @ cov_pi @ W.T


def multinomial_covariance(cat: dict, b) -> np.ndarray:
    """The plug-in multinomial covariance of the per-photon weighting eps_bc = sum_i q_i/n_b (channels)."""
    x = cat["bins"][b]
    C = len(cat["channels"])
    n = x["n"]
    s, s2 = np.zeros(C), np.zeros(C)
    # recover each detection's channel from the cell order: q holds the detections in photons order
    chans = x.get("det_chan")
    if chans is None:
        raise SplitError("internal", "multinomial_covariance needs det_chan")
    for c, qi in zip(chans, x["q"]):
        s[c] += qi
        s2[c] += qi * qi
    return (np.diag(s2) / n - np.outer(s, s) / n ** 2) / n


def _attach_channels(cat: dict, run: dict) -> dict:
    chans = cat["channels"]
    for b in cat["bins"]:
        cat["bins"][b]["det_chan"] = []
    for b, c, _, _, _ in run["detections"]:
        cat["bins"][b]["det_chan"].append(chans.index(c))
    return cat


def variance_ratio(cat: dict, b) -> float:
    """Var(sum_c eps_bc) under the Dirichlet (analytic, from its parameters) over the multinomial variance of
    sum_i PDE(E_i)/n_b, the plug-in (sum q_i^2 - (sum q_i)^2/n_b)/n_b^2."""
    x = cat["bins"][b]
    a = x["k"] + 0.5
    a0 = a.sum()
    m = a / a0
    vd = (np.sum(x["w"] ** 2 * m) - np.sum(x["w"] * m) ** 2) / (a0 + 1.0)
    n, q = x["n"], x["q"]
    vm = (np.sum(q ** 2) - np.sum(q) ** 2 / n) / n ** 2
    return float(vd / vm) if vm > 0 else math.inf


def grid_check(map_document: dict, run: dict, tables: list, grid: list | None = None) -> dict:
    """The route-3 energy grid (calib_design.py, remedy level plan): per bin the pseudo-mass K_cat/2 <= 0.01 n_b, and the
    analytic Dirichlet variance of sum_c eps_bc >= 0.98 of the multinomial variance, for every PDE(E) of `tables` (the
    nominal one, or the tables spanning the prior or design range when the PDE holds theta). Otherwise the grid is
    changed; if no grid meets both, the bin is merged or the map photon number increased."""
    if not tables:
        raise SplitError("tables", "the grid check needs at least one PDE(E) table")
    grid = grid or default_grid(tables[0])
    out, per = [], []
    for t in tables:
        cat = categories(map_document, run, t, grid)
        kcat = 1 + len(cat["cells"])
        for b, x in cat["bins"].items():
            ratio = variance_ratio(cat, b)
            mass_ok = kcat / 2.0 <= PSEUDO_MASS_FRACTION * x["n"]
            per.append({"bin": b, "K_cat": kcat, "n_b": x["n"], "pseudo_mass_ok": mass_ok, "variance_ratio": ratio})
            if not mass_ok:
                out.append(_plan_f("grid_pseudo_mass", f"bin {b}: K_cat/2 = {kcat / 2} > {PSEUDO_MASS_FRACTION} n_b = "
                                   f"{PSEUDO_MASS_FRACTION * x['n']:.4g}: coarsen the grid, merge the bin or add photons"))
            if ratio < VARIANCE_RATIO:
                out.append(_plan_f("grid_variance", f"bin {b}: the Dirichlet variance is {ratio:.4f} of the "
                                   f"multinomial variance (< {VARIANCE_RATIO}): refine the grid"))
    return {"status": "failed" if out else "passed", "findings": out, "grid": list(grid), "bins": per,
            "flags": [FLAG]}


def replica_key(map_sha256: str, photons_sha: str, component: int, r: int) -> tuple:
    """rng._key("calib-map-pde/1", map_sha256, photons_sha256, component, r), as g4sim forms its keys."""
    return rng._key(PDE_REPLICA_KEY, map_sha256, photons_sha, int(component), int(r))


def route3_replica(cat: dict, key: tuple) -> dict:
    """Route-3 replica r (fixed-map mode): per bin g_bu ~ Gamma(k_bu + 1/2) from SubStream(key, b, u) (the boost of
    efficiency_map._gamma below shape 1), normalized per bin; eps_bc = sum_e w_ce pi_bce. Returns {bin: [eps_c]}."""
    out = {}
    C = len(cat["channels"])
    for b, x in cat["bins"].items():
        g = np.array([efficiency_map._gamma(rng.SubStream(key, int(b), u), float(k) + 0.5)
                      for u, k in enumerate(x["k"])])
        pi = g / math.fsum(g)
        eps = np.zeros(C)
        for u in range(1, len(pi)):
            eps[x["chan"][u]] += x["w"][u] * pi[u]
        out[str(b)] = [float(v) for v in eps]
    return out


def registration_key(map_sha256: str, photons_sha: str, component: int, cat: dict, R: int, grid: list) -> dict:
    """The registration key of the route-3 replicas (fixed-map mode)."""
    centre = {str(b): [float(np.sum(x["q"][np.array(x["det_chan"], int) == c])) / x["n"] if len(x["q"]) else 0.0
                       for c in range(len(cat["channels"]))] for b, x in cat["bins"].items()} \
        if all("det_chan" in x for x in cat["bins"].values()) else None
    return {"key": PDE_REPLICA_KEY, "map_sha256": map_sha256, "photons_sha256": photons_sha,
            "component": int(component), "coordinates": [list(ce) for ce in cat["cells"]], "centre": centre,
            "R": int(R), "sampler": SAMPLER_VERSION, "grid": [float(x) for x in grid]}


def route3_categories(map_document: dict, run: dict, table: dict, grid: list | None = None) -> dict:
    """categories() with each detection's channel attached (for the multinomial covariance and the centre)."""
    return _attach_channels(categories(map_document, run, table, grid or default_grid(table)), run)


# ------------------------------------------------------------------ route 1: per-photon thinning nested in p
def route1_stream(stage: str, component: int) -> str:
    return f"{stage}/pde/{component}"


def route1_key(run_seed: int, stage: str, component: int) -> tuple:
    """Key ("g4sim-rng/1\\0volume", run_seed, <stage>/pde/<component>, 0): a volume stream of g4sim's form."""
    return rng.volume_key(int(run_seed), route1_stream(stage, component), 0)


def digitize_route1(job: dict, rows: list, p: float, component: int) -> tuple[list, list]:
    """Route 1: digitize the job at the efficiency-1 map's efficiencies (the job's), then keep each detected photon with
    probability p from the volume stream route1_key, counter (global event, volume ID, bin, output group = the index of
    the detected photon in the order the job draws them: channel order), before g4sim's sensor and electronics stages
    (job keys and channel counter volume ID x C + c). Never after dark counts, cross-talk or saturation, never on charge
    or codes. The kept set is nested in p: a photon kept at p is kept at every p' > p. Same output as
    digitize.digitize."""
    digitize.check_job(job)
    if not 0.0 <= float(p) <= 1.0:
        raise SplitError("p_range", f"a PDE p of {p} is outside [0, 1]")
    stage, sensor, electronics = job["stage"], job["sensor"], job["electronics"]
    document = {"run_seed": job["run_seed"], "replica": job["replica"]}
    count = len(job["channels"])
    timing = job.get("timing")
    transit_document = digitize._transit_document(job) if timing else None
    sensor_key = rng.channel_key(job["run_seed"], job["readout"], sensor["name"], job["replica"])
    electronics_key = rng.channel_key(job["run_seed"], job["readout"], electronics["name"], job["replica"])
    thin_key = route1_key(job["run_seed"], stage["name"], component)
    key = rng.volume_key(job["run_seed"], stage["name"], job["replica"])
    grouped: dict = {}
    for event, volume, bin_index, large, small, steps in rows:
        bins = grouped.setdefault((event, volume), {})
        if bin_index in bins:
            raise digitize.DigiError("bin-twice", f"event {event}, volume {volume}: bin {bin_index} appears twice")
        bins[bin_index] = (large, small, steps)
    channel_rows, time_rows = [], []
    for (event, volume), bins in sorted(grouped.items()):
        factor = response.yield_factor(document, event, volume, stage.get("yield_relative_width", 0.0))
        photoelectrons = [0] * count
        for bin_index in sorted(bins):
            large, small, steps = bins[bin_index]
            efficiencies = job["efficiencies"].get(str(bin_index))
            if efficiencies is None:
                raise digitize.DigiError("efficiencies", f"bin {bin_index} has no efficiencies")
            stream = rng.SubStream(key, event, volume, bin_index)
            photons = response.bin_photons(stream, stage["light_yield_per_MeV"], stage["resolution_scale"], large,
                                           small, steps, factor)
            counts = stream.multinomial(photons, efficiencies)[:count]
            times = None
            if timing and sum(counts):
                times = response.photon_times(document, stage["name"], event, volume, bin_index, sum(counts),
                                              timing["decay_ns"], timing["transit"].get("transit_ns", 0.0),
                                              transit_document, timing.get("rise_ns", 0.0))
            thin = rng.SubStream(thin_key, event, volume, bin_index)
            start = 0
            for at, drawn in enumerate(counts):
                kept = [j for j in range(start, start + drawn) if thin.group()[0] < p]
                photoelectrons[at] += len(kept)
                if times is not None:
                    time_rows += [(event, volume, bin_index, at, times[j]) for j in kept]
                start += drawn
        for at in range(count):
            cell = volume * count + at
            state = {"gain_factor": 1.0, "dead": False}
            if "conditions" in job:
                state = conditions.at(job["conditions"], job["event_time_ns"][str(event)],
                                      {"volume": volume, "channel": at})
            charge = response.sensor_response(rng.SubStream(sensor_key, event, cell), photoelectrons[at],
                                              sensor["gain"] * state["gain_factor"], sensor["excess_noise"],
                                              sensor["dark_rate_per_ns"], sensor["gate_ns"])
            code = response.electronics_response(rng.SubStream(electronics_key, event, cell), charge,
                                                 electronics["noise_sigma"],
                                                 state.get("threshold", electronics["threshold"]), electronics["lsb"],
                                                 electronics["bits"])
            if state["dead"]:
                code = None
            channel_rows.append((event, volume, at, photoelectrons[at], charge, code))
    time_rows.sort(key=lambda row: row[:4])
    return channel_rows, time_rows


def route1_findings(route1: dict) -> list[dict]:
    """Route 1's placement and stream (calib_design.py, remedy level plan): the thinning sits before the sensor stages
    (never after dark counts, cross-talk or saturation), applies to the detected photons (never as a scale of charge or
    codes), and its stream is <stage>/pde/<component>, never efficiency_map/<k>."""
    out = []
    if route1.get("position", "before-sensor") not in ROUTE1_POSITIONS:
        out.append(_plan_f("route1_position", f"route 1 thins at {route1.get('position')!r}: the thinning is never "
                           "applied after dark counts, cross-talk or saturation (before the sensor stages only)"))
    if route1.get("applies_to", "detected-photons") not in ROUTE1_APPLIES_TO:
        out.append(_plan_f("route1_scale", f"route 1 applied to {route1.get('applies_to')!r}: never as a scale of "
                           "charge or of codes (section 11.4 Table 2)"))
    stream = route1.get("stream", route1_stream(route1.get("stage", ""), route1.get("component", 0)))
    if MAP_STREAM.match(str(stream)):
        out.append(_plan_f("route1_stream", f"the route-1 stream {stream!r} is named like g4sim's map replica stream "
                           "efficiency_map/<k>"))
    elif stream != route1_stream(route1.get("stage", ""), route1.get("component", 0)):
        out.append(_plan_f("route1_stream", f"the route-1 stream is <stage>/pde/<component>, not {stream!r}"))
    return out


# ------------------------------------------------------------------ the contract rules (calib_contract.py)
def declaration(contract: dict) -> dict | None:
    return contract.get("pde_split") if isinstance(contract.get("pde_split"), dict) else None


def _pde_bound(par: dict) -> bool:
    return any(b.get("document") == "evaluator" for b in par.get("bindings") or [])


def contract_findings(contract: dict) -> list[dict]:
    """The declaration-level rules of section 6.7 "Rejected" (contract error): every parameter bound to the evaluator is
    a declared PDE-split parameter; the declared PDE parameter acts only as the sensor `efficiency` (bound to the
    evaluator's /pde fields only, no tie to a reflectance, transmittance, refractive index, window or coating); no angle
    dependence; a PDE(E) is never applied as a constant scale of the efficiency-1 map; a nominal PDE(E) table is valid.
    contract.pde_split = {parameters: [names], model: scale | table, applied_as: scale | weighting (table),
    table: {energy_eV, value} (nominal PDE(E)), angle_dependent, ties: [optical properties tied to the PDE],
    sensor_surfaces: [names of the sensor optical surfaces set to 1 for the map], map_mode: fixed | varies-with-theta}."""
    out: list[dict] = []
    if contract.get("simulator") != "g4sim":
        return out
    decl = declaration(contract)
    pars = {p.get("name"): (i, p) for i, p in enumerate(contract.get("parameters", []))}
    bound = [n for n, (_, p) in pars.items() if _pde_bound(p)]
    if decl is None:
        for n in bound:
            out.append(_f("undeclared", f"{n!r} is bound to the evaluator (a PDE split) but the contract declares no "
                          "pde_split (section 6.7)", f"$.parameters[{pars[n][0]}]"))
        return out
    names = decl.get("parameters") or []
    if not names:
        out.append(_f("declaration", "pde_split names its PDE parameters", "$.pde_split.parameters"))
    for n in bound:
        if n not in names:
            out.append(_f("undeclared", f"{n!r} is bound to the evaluator but is not a pde_split parameter",
                          f"$.parameters[{pars[n][0]}]"))
    for n in names:
        if n not in pars:
            out.append(_f("declaration", f"pde_split parameter {n!r} is not a contract parameter", "$.pde_split"))
            continue
        i, p = pars[n]
        other = [b for b in p.get("bindings") or [] if b.get("document") != "evaluator"
                 or not str(b.get("pointer", "")).startswith("/pde")]
        if other or not _pde_bound(p):
            out.append(_f("tied_property", f"PDE parameter {n!r} is bound to {other or 'no evaluator field'}: under "
                          "the split it acts only as the sensor efficiency, through the evaluator's /pde fields; a PDE "
                          "that also changes another optical property stays an optical property (route 0)",
                          f"$.parameters[{i}].bindings"))
    if decl.get("model") not in MODELS:
        out.append(_f("declaration", f"pde_split.model is scale or table, not {decl.get('model')!r}",
                      "$.pde_split.model"))
    if decl.get("ties"):
        out.append(_f("tied_property", f"the PDE is tied to {decl['ties']} (e.g. reflectivity = 1 - PDE): the split "
                      "is exact only when the PDE acts only as the sensor EFFICIENCY; the PDE stays an optical property "
                      "(route 0)", "$.pde_split.ties"))
    if decl.get("angle_dependent"):
        out.append(_f("angle_dependent", "a PDE that depends on the angle of incidence cannot be expressed by g4sim's "
                      "efficiency: it stays an optical property (route 0)", "$.pde_split.angle_dependent"))
    if decl.get("model") == "table":
        if decl.get("applied_as", "weighting") != "weighting":
            out.append(_f("table_as_scale", "a PDE(E) is never a constant scale of the efficiency-1 map (nor a scale "
                          "of a map built at a nominal PDE(E)): route 3 weights each detection by PDE(E_i)",
                          "$.pde_split.applied_as"))
        try:
            table_arrays(decl.get("table") or {})
        except SplitError as err:
            out.append(_f("declaration", str(err), "$.pde_split.table"))
    if not decl.get("sensor_surfaces"):
        out.append(_f("declaration", "pde_split names the sensor surfaces set to efficiency 1 for the map",
                      "$.pde_split.sensor_surfaces"))
    return out


def mapping_surfaces(spec_text, spec_field_types: dict, sensors: list) -> tuple[dict, dict]:
    """(production optical_surfaces, the mapping run's optical_surfaces): the IR's physical.optical_surfaces of the
    production detector-spec/1 and of the same spec with every sensor surface's efficiency values set to 1 (read by
    g4sim's procedure, so the spelling of 1 is the IR's)."""
    spec = load_spec_json(spec_text, spec_field_types)
    prod = (expand.expand(spec)["physical"].get("optical_surfaces") or {})
    raw = load_spec_json(spec_text, spec_field_types)
    surfaces = raw.get("optical_surfaces") or {}
    for s in sensors:
        if s not in surfaces or "efficiency" not in surfaces[s]:
            raise SplitError("sensor_surface", f"sensor surface {s!r} is not an optical surface with an efficiency")
        surfaces[s]["efficiency"]["value"] = ["1"] * len(surfaces[s]["efficiency"]["value"])
    one = load_spec_json(json.dumps(raw), spec_field_types)
    return prod, (expand.expand(one)["physical"].get("optical_surfaces") or {})


def surfaces_findings(map_document: dict, production: dict, sensors: list, mapping: dict,
                      path: str = "$.pde_split") -> list[dict]:
    """The efficiency-1 map's surfaces: every sensor surface of the mapping run at efficiency 1, every other optical
    property equal to production, and the map's surfaces_sha256 g4sim's hash (canonical_sha256 of the IR's
    optical_surfaces) of that specification. g4sim's map-stale compares only materials_sha256 (v0.65.0), so this
    workflow checks the surfaces itself. `mapping`: the mapping run's IR surfaces (mapping_surfaces)."""
    out = []
    want = copy.deepcopy(production)
    for s in sensors:
        if s not in production or "efficiency" not in production[s]:
            out.append(_f("sensor_surface", f"sensor surface {s!r} is not an optical surface with an efficiency", path))
            return out
    for s in sensors:
        vals = (mapping.get(s) or {}).get("efficiency", {}).get("value", [])
        if not vals or any(float(v) != 1.0 for v in vals):
            out.append(_f("sensor_not_one", f"sensor surface {s!r} of the efficiency-1 map has efficiency {vals}, "
                          "not 1", path))
    a = dict(mapping)
    for s in sensors:
        if s in a and s in want:
            a[s] = {k: v for k, v in a[s].items() if k != "efficiency"}
            want[s] = {k: v for k, v in want[s].items() if k != "efficiency"}
    if a != want:
        out.append(_f("surfaces_differ", "the mapping run's optical surfaces differ from production in more than the "
                      "sensor efficiency entries", path))
    got = ((map_document.get("form") or {}).get("hashes") or {}).get("surfaces_sha256")
    if got != canonical_sha256(mapping):
        out.append(_f("surfaces_hash", f"the map's surfaces_sha256 {str(got)[:12]}... is not g4sim's hash of the "
                      "production surfaces with the sensor efficiency entries set to 1", path))
    return out


def efficiency_test_findings(decl: dict, surfaces: dict, low: float, high: float, prior: list | None = None,
                             design: bool = False) -> list[dict]:
    """On a surface model whose absorption branch tests EFFICIENCY > 0, a PDE that is 0 at an energy the emission
    spectrum reaches changes the photon history (section 6.7): rejected. Contract: the declared PDE(E). Design
    (remedy plan): over the prior or design range, p = 0 included (prior: [low, high] of p, or a list of PDE(E)
    tables)."""
    tested = [s for s in decl.get("sensor_surfaces") or [] if (surfaces.get(s) or {}).get("type")
              in EFFICIENCY_TEST_TYPES or (surfaces.get(s) or {}).get("model") == "DAVIS"]
    if not tested:
        return []
    mk = _plan_f if design else (lambda code, msg: _f(code, msg, "$.pde_split"))
    out = []
    if not design and decl.get("model") == "table" and decl.get("table") \
            and zero_in_range(decl["table"], low, high):
        out.append(mk("efficiency_zero", f"surfaces {tested} test EFFICIENCY > 0 and the declared PDE(E) is 0 at an "
                      f"emitted energy in [{low}, {high}] eV: an efficiency of 0 changes the photon history"))
    if design and prior is not None:
        if decl.get("model") == "scale" and len(prior) == 2 and not isinstance(prior[0], dict) \
                and float(min(prior)) <= 0.0:
            out.append(mk("efficiency_zero", f"surfaces {tested} test EFFICIENCY > 0 and the prior range {prior} of p "
                          "reaches 0"))
        for t in prior:
            if isinstance(t, dict) and zero_in_range(t, low, high):
                out.append(mk("efficiency_zero", f"surfaces {tested} test EFFICIENCY > 0 and a PDE(E) of the prior "
                              f"range is 0 at an emitted energy in [{low}, {high}] eV"))
                break
    return out


def document_findings(contract: dict, spec_text, spec_field_types: dict, map_document: dict | None) -> list[dict]:
    """calib_contract.py with the model documents (fixed map): the efficiency-1 map's surfaces and the EFFICIENCY > 0
    condition for the declared PDE(E)."""
    decl = declaration(contract)
    if decl is None or contract.get("simulator") != "g4sim":
        return []
    sensors = list(decl.get("sensor_surfaces") or [])
    try:
        prod, one = mapping_surfaces(spec_text, spec_field_types, sensors)
    except SplitError as err:
        return [_f(err.code, str(err), "$.pde_split.sensor_surfaces")]
    out = []
    if map_document is not None and decl.get("map_mode", "fixed") == "fixed":
        out += surfaces_findings(map_document, prod, sensors, one)
    if map_document is not None:
        low, high = emission_range(map_document)
        out += efficiency_test_findings(decl, prod, low, high)
    return out


# ------------------------------------------------------------------ the model identity (section 5.1)
def identity_part(pde, masked: bool = False):
    """The PDE(E) part of item 4 (model_identity.response_hash(..., pde_part=)): for route 3 the photons.csv hash of
    the efficiency-1 mapping run and the PDE(E) table (masked when it holds theta or phi: a derived value); for routes
    2_1 and 1, p is a theta/phi of the evaluator's job builder, so there is no part (None)."""
    if pde is None:
        return None
    if not isinstance(pde, dict) or pde.get("route") not in ROUTES:
        raise SplitError("identity", "the model's pde is {route, photons_sha256 and table for route 3}")
    if pde["route"] != "3":
        return None
    if not re.fullmatch(r"[0-9a-f]{64}", str(pde.get("photons_sha256", ""))):
        raise SplitError("identity", "route 3 needs the mapping run's photons.csv (photons_sha256, 64 hex)")
    e, v = table_arrays(pde.get("table") or {})
    table = "calib-masked/1" if masked else {"energy_eV": [float(x) for x in e], "value": [float(x) for x in v]}
    return {"route": "3", "photons_sha256": pde["photons_sha256"], "table": table}


# ------------------------------------------------------------------ candidate methods (section 11.4 Table 2)
def candidates(par: dict, contract: dict, plan: dict, stored: set, recorded: bool) -> tuple[list, list]:
    """The Table 2 row "PDE under the split of section 6.7" of a parameter bound to the evaluator: re-digitization
    (rerun, medium) through g4sim-digi-job/1 with route 2_1 (p eps_c), route 3 (sum_i PDE(E_i)/n_b) or, when p is
    theta, route 1 for readout systems with an observable not linear in eps; analytic for observables linear in eps.
    Returns (candidates [(method, form, preconditions)], excluded [{method, reason}])."""
    decl = declaration(contract)
    if decl is None or par.get("name") not in (decl.get("parameters") or []):
        return [], [{"method": "rerun", "reason": "bound to the evaluator without a pde_split declaration"}]
    if any(f["code"] in ("pde_split.tied_property", "pde_split.angle_dependent", "pde_split.table_as_scale")
           for f in contract_findings(contract)):
        return [], [{"method": "rerun", "reason": "the PDE model is not exactly the sensor surface's EFFICIENCY(E): "
                     "route 0 (bind the PDE to the sensor surface's efficiency, resimulation)"}]
    route0 = {"method": "resimulation", "reason": "route 0 (always allowed): bind the PDE to the sensor surface's "
              "efficiency (detector-spec optical row) instead of the evaluator"}
    if not recorded or "edep_visible_ly_split" not in stored:
        return [], [{"method": "rerun", "reason": "re-digitization needs edep_visible_ly_split recorded as column or "
                     "event_file (section 6.1)"}, route0]
    pre = ["the PDE acts in Geant4 only as the sensor EFFICIENCY (no reflectance, transmittance, refractive index, "
           "window or angle dependence tied to it)", "the split check of section 6.7 passed (calib_design.py "
           "pde-split)", "the efficiency map is built with every sensor surface's efficiency = 1",
           "never as a thinning of charge or of codes, never after dark counts, cross-talk or saturation"]
    if decl.get("model") == "table":
        form = ("re-digitization through g4sim-digi-job/1, route 3: efficiencies sum_i PDE(E_i)/n_b and the "
                "PDE-weighted transit (integerised to 10^6) from the efficiency-1 mapping run's photons.csv")
        pre = pre + ["the mapping run's photons.csv kept, hashed and equal to the map's counts"]
    else:
        form = ("re-digitization through g4sim-digi-job/1, route 2_1 (efficiencies p eps_c); route 1 (per-photon "
                "thinning nested in p) for every readout system with an observable not linear in eps when p is "
                "theta; analytic mu_0 + p (mu(1) - mu_0) for observables linear in eps")
    return [("rerun", form, pre)], [route0]


# ------------------------------------------------------------------ the plan rules (calib_design.py)
def p_is_theta(par: dict) -> bool:
    """p moves with the fit: a theta, or a phi in profile mode (section 6.7 route 1)."""
    return par.get("role") == "theta" or (par.get("role") == "phi" and par.get("mode", "profile") == "profile")


def route_findings(contract: dict, plan_split: dict) -> list[dict]:
    """Routes per readout system (remedy level plan). plan.pde_split.readouts = {readout: {route, observables:
    {name: linear_in_eps (bool)}}}. When p is theta, a readout system with an observable not linear in eps uses route 1
    for all its observables; one whose observables are all linear in eps uses route 2_1. Route 3 is for a PDE(E),
    routes 2_1 and 1 for a scale p. Route 3 needs the mapping run's photons.csv."""
    decl = declaration(contract) or {}
    out = []
    pars = {p["name"]: p for p in contract.get("parameters", [])}
    theta = any(p_is_theta(pars[n]) for n in decl.get("parameters") or [] if n in pars)
    model = decl.get("model")
    for ro, r in sorted((plan_split.get("readouts") or {}).items()):
        route = r.get("route")
        if route not in ROUTES:
            out.append(_plan_f("route", f"readout {ro}: route {route!r} is not one of {ROUTES}"))
            continue
        nonlinear = sorted(o for o, lin in (r.get("observables") or {}).items() if not lin)
        if model == "scale" and route == "3":
            out.append(_plan_f("route_model", f"readout {ro}: route 3 is for a PDE(E) table, the PDE is a scale p"))
        if model == "table" and route in ("2_1", "1"):
            out.append(_plan_f("route_model", f"readout {ro}: a PDE(E) uses route 3 (or route 0), not route {route}"))
        if model == "scale" and theta and nonlinear and route == "2_1":
            out.append(_plan_f("route_nonlinear", f"readout {ro}: p is theta and {nonlinear} are not linear in eps: "
                               "route 1 (per-photon thinning nested in p) for all its observables, not route 2_1 "
                               "(digitizing at p eps re-maps the uniforms when p moves)"))
        if model == "scale" and theta and not nonlinear and route == "1":
            out.append(_plan_f("route_linear", f"readout {ro}: all observables are linear in eps, which use route 2_1"))
        if route == "3" and not plan_split.get("photons"):
            out.append(_plan_f("route3_photons", f"readout {ro}: route 3 without the mapping run's photons.csv "
                               "(efficiency-map/1 stores no photon energies)"))
    return out


def key_findings(labelled: dict, pipelines: list) -> list[dict]:
    """Key distinctness (section 6.6, remedy plan): the workflow's keys (calib-map-joint/1, calib-map-pde/1, route-1
    <stage>/pde/<component>) pairwise distinct and distinct from response.study_keys of every pipeline used.
    labelled: {label: key}; pipelines: [(response-pipeline/1, [readouts])]."""
    out = []
    seen: dict = {}
    for doc, readouts in pipelines:
        for k in response.study_keys(doc, readouts):
            seen.setdefault(tuple(k), f"response.study_keys (run_seed {doc['run_seed']})")
    for label, k in labelled.items():
        k = tuple(k)
        if k in seen:
            out.append(_plan_f("key_collision", f"key {label} equals the key of {seen[k]}"))
        else:
            seen[k] = label
    return out


def pair_findings(plan: dict) -> list[dict]:
    """The split-check pair records (plan.evaluations, use "pde-split-pair"): two runs per pair, one with
    efficiency_one, sharing logical_run_seed and event interval (the sharing section 6.6 allows only for this pair;
    the overlap check itself is design_g4sim.interval_findings)."""
    out = []
    pairs: dict = {}
    for e in plan.get("evaluations") or []:
        if e.get("use") == "pde-split-pair":
            pairs.setdefault(e.get("pair"), []).append(e)
    for name, runs in sorted(pairs.items(), key=lambda x: str(x[0])):
        ones = [e for e in runs if e.get("efficiency_one")]
        if len(runs) != 2 or len(ones) != 1:
            out.append(_plan_f("pair_form", f"split-check pair {name!r}: two mapping runs, one at efficiency 1 and one "
                               f"at the nominal PDE (found {len(runs)} runs, {len(ones)} at efficiency 1)"))
            continue
        a, b = runs
        same = all(int(a[k]) == int(b[k]) for k in ("logical_run_seed", "first_event", "events"))
        if not same:
            out.append(_plan_f("pair_seeding", f"split-check pair {name!r}: the two mapping runs differ in seed or "
                               "event interval; they share one (logical_run_seed, interval), so that the detections "
                               "at the nominal PDE are a subset of those at efficiency 1"))
    return out


def nesting(lines_one: list, lines_p: list) -> dict:
    """Event by event, the detections at the nominal PDE are a subset of those at efficiency 1 with byte-identical
    photons.csv rows. Returns {nested, first_event (the first event that breaks it, or None), extra (rows)}."""
    by_one: dict = {}
    for r in lines_one:
        by_one.setdefault(r["event"], []).append(r["line"])
    by_p: dict = {}
    for r in lines_p:
        by_p.setdefault(r["event"], []).append(r["line"])
    bad = []
    for ev in sorted(by_p):
        pool = list(by_one.get(ev, []))
        for ln in by_p[ev]:
            if ln in pool:
                pool.remove(ln)
            else:
                bad.append(ev)
                break
    return {"nested": not bad, "first_event": bad[0] if bad else None, "events_not_nested": len(bad)}


def _q(detections, nominal: dict) -> np.ndarray:
    if "table" in nominal:
        return pde_at(nominal["table"], [d[3] for d in detections]) if detections else np.zeros(0)
    p0 = float(nominal["p"])
    if not 0.0 < p0 < 1.0:
        raise SplitError("p_range", f"the split check needs a nominal PDE in (0, 1), not {p0}")
    return np.full(len(detections), p0)


def split_check(map_one: dict, run_one: dict, run_p: dict, nominal: dict, lines: tuple | None = None,
                propagation: dict | None = None) -> dict:
    """The split check of section 6.7 (calib_design.py, remedy level plan) on a nested pair of mapping runs (efficiency 1
    and the nominal PDE p0 or PDE(E), same materials, surfaces, logical_run_seed and event interval).
    1. Nesting (when `lines` = (photons rows at 1, rows at p0) are given): a pair that is not nested fails, and the
       first event that breaks it is recorded.
    2. Per bin and channel, and on the transit means per bin, the detections at p0 against the binomial thinning by
       q_i (p0, or PDE(E_i)) of those at efficiency 1: z = (K_q - sum q_i)/sqrt(sum q_i (1 - q_i)) (the r/sd(r) of
       section 6.7), and for the transit S = sum_kept (t_i - tbar_q), Var S = sum q_i (1 - q_i)(t_i - tbar_q)^2; the
       chi-square of the z^2 passes at alpha = 0.01.
    3. With propagation = {A (d x n_obs), sigma_tot_design (d), and J (n_obs x n_cells, cells (bin, channel) in map
       order) or delta_mu with cov_delta_mu}: d theta = A J d eps, d eps_bc = (K_q - sum q_i)/n_b with variance
       sum q_i (1 - q_i)/n_b^2; |d theta_i| + 2 sd(d theta_i) <= 0.1 sigma_tot,i^design for every theta_i. The pair is
       sized by sd(d theta_i) <= 0.1 sigma_tot,i^design/(2 + z_{1 - 0.025/d}).
    Returns {status passed | failed, findings, chi2, dof, p_value, nesting, dtheta, sd, bound, sizing, remedy, flags}.
    remedy: "larger-pair" when the check fails only through 2 sd(d theta_i) (one larger pair, on a new interval and
    sized by the rule, may replace it), else "route-0"."""
    chans = list(map_one["channels"])
    rows = map_one["form"]["bins"]
    n = {r["bin"]: r["emitted"] for r in rows}
    findings: list = []
    nest = None
    if lines is not None:
        nest = nesting(*lines)
        if not nest["nested"]:
            findings.append(_plan_f("not_nested", f"the detections at the nominal PDE are not a subset of those at "
                                    f"efficiency 1 (first event {nest['first_event']}): something other than the "
                                    "sensor efficiency changed the photon histories, or a number is drawn on Detection"))
    q = _q(run_one["detections"], nominal)
    cells = [(r["bin"], c) for r in rows for c in range(len(chans))]
    ci = {cell: i for i, cell in enumerate(cells)}
    sum_q, var_q = np.zeros(len(cells)), np.zeros(len(cells))
    for d, qi in zip(run_one["detections"], q):
        i = ci[(d[0], chans.index(d[1]))]
        sum_q[i] += qi
        var_q[i] += qi * (1 - qi)
    k_p = np.zeros(len(cells))
    for d in run_p["detections"]:
        if d[1] not in chans:
            findings.append(_plan_f("not_nested", f"a detection at the nominal PDE in channel {d[1]!r}, which "
                                    "detected nothing at efficiency 1"))
            continue
        k_p[ci[(d[0], chans.index(d[1]))]] += 1
    z2 = []
    use = var_q > 0
    z2 += list(((k_p[use] - sum_q[use]) ** 2) / var_q[use])
    # transit means per bin
    t_one: dict = {}
    for d, qi in zip(run_one["detections"], q):
        t_one.setdefault(d[0], []).append((d[2], qi))
    t_p: dict = {}
    for d in run_p["detections"]:
        t_p.setdefault(d[0], []).append(d[2])
    for b, tq in t_one.items():
        t = np.array([x for x, _ in tq])
        qq = np.array([y for _, y in tq])
        if len(t) < 2 or qq.sum() <= 0:
            continue
        tbar = float(np.sum(qq * t) / qq.sum())
        v = float(np.sum(qq * (1 - qq) * (t - tbar) ** 2))
        if v > 0:
            s = float(np.sum(np.array(t_p.get(b, [])) - tbar))
            z2.append(s * s / v)
    chi2 = float(np.sum(z2))
    dof = len(z2)
    pval = float(stats.chi2.sf(chi2, dof)) if dof else 1.0
    chi_ok = pval >= CHI2_ALPHA
    if not chi_ok:
        findings.append(_plan_f("chi2", f"the detections at the nominal PDE are not the binomial thinning of those at "
                                f"efficiency 1: chi2 = {chi2:.1f} on {dof} (p = {pval:.2e} < {CHI2_ALPHA})"))
    res: dict = {"chi2": chi2, "dof": dof, "p_value": pval, "nesting": nest, "flags": [FLAG]}
    only_sd = False
    if propagation is not None:
        A = np.atleast_2d(np.asarray(propagation["A"], float))
        sig = np.asarray(propagation["sigma_tot_design"], float)
        if "J" in propagation:
            J = np.atleast_2d(np.asarray(propagation["J"], float))
            nb = np.array([n[b] for b, _ in cells], float)
            deps = (k_p - sum_q) / nb
            veps = var_q / nb ** 2
            dmu, cov = J @ deps, (J * veps) @ J.T
        else:
            dmu = np.asarray(propagation["delta_mu"], float)
            cov = np.atleast_2d(np.asarray(propagation["cov_delta_mu"], float))
        dth = A @ dmu
        sd = np.sqrt(np.clip(np.diag(A @ cov @ A.T), 0, None))
        d = len(dth)
        bound = DTHETA_FRACTION * sig
        z = float(stats.norm.ppf(1 - PAIR_ALPHA / d))
        target = bound / (SPREAD_MULTIPLIER + z)
        ok = np.abs(dth) + SPREAD_MULTIPLIER * sd <= bound
        bias_ok = np.abs(dth) <= bound
        res.update(dtheta=dth.tolist(), sd=sd.tolist(), bound=bound.tolist(),
                   sizing={"sd_target": target.tolist(), "sized": bool(np.all(sd <= target)), "z": z,
                           "photon_factor": float(np.max((sd / target) ** 2))})
        for i in (int(x) for x in np.flatnonzero(~ok)):
            findings.append(_plan_f("dtheta", f"theta_{i}: |d theta| + 2 sd = {abs(dth[i]) + 2 * sd[i]:.4g} > "
                                    f"0.1 sigma_tot^design = {bound[i]:.4g}"))
        only_sd = bool(np.any(~ok)) and bool(np.all(bias_ok)) and chi_ok and (nest is None or nest["nested"])
    res.update(status="failed" if findings else "passed", findings=findings,
               remedy=None if not findings else ("larger-pair" if only_sd else "route-0"))
    return res


def nominal_job(job_one: dict, map_one: dict, run_p: dict) -> dict:
    """The job of the mapping run at the nominal PDE, in the efficiency-1 map's segmentation and transit edges: per
    bin the efficiencies K_p,bc/n_b and the integer transit counts of the nominal run's detections (the second map of
    the pair, digitized with the same run_seed, rows and stages as the split job)."""
    chans = list(map_one["channels"])
    edges = map_one["form"]["transit_edges_ns"]
    n = {str(r["bin"]): r["emitted"] for r in map_one["form"]["bins"]}
    k = {b: [0] * len(chans) for b in n}
    tr = {b: [0] * efficiency_map.TRANSIT_BINS for b in n}
    for b, c, t, _, _ in run_p["detections"]:
        k[str(b)][chans.index(c)] += 1
        tr[str(b)][_transit_cell(edges, t)] += 1
    out = {**job_one, "efficiencies": {b: [x / n[b] for x in k[b]] for b in job_one["efficiencies"]}}
    if job_one.get("timing") and job_one["timing"]["transit"]["kind"] == "mapped":
        out["timing"] = {**job_one["timing"], "transit": {"kind": "mapped", "edges_ns": list(edges), "counts": {
            b: tr[b] for b in job_one["timing"]["transit"]["counts"]}}}
    return out


def split_job(job_one: dict, map_one: dict, run_one: dict, nominal: dict) -> dict:
    """The split's job at the nominal PDE: route 2_1 (p0 eps(1)) or route 3 (the PDE(E) weighting of the efficiency-1
    run)."""
    if "table" in nominal:
        return route3_job(job_one, route3(map_one, run_one, nominal["table"]))
    return route21_job(job_one, float(nominal["p"]))


def _per_event(channel_rows: list, events: list, quantity: str, channels) -> np.ndarray:
    col = {"photoelectrons": 3, "charge": 4, "code": 5}[quantity]
    at = {e: i for i, e in enumerate(events)}
    x = np.zeros(len(events))
    for r in channel_rows:
        if channels is None or r[2] in channels:
            x[at[r[0]]] += 0.0 if r[col] is None else float(r[col])
    return x


def digitized_propagation(map_one: dict, run_one: dict, run_p: dict, nominal: dict, job_one: dict, rows: list,
                          observables: list, A, sigma_tot_design, J=None) -> dict:
    """The split check's delta mu with both maps digitized with one run_seed (section 6.7): the nominal-PDE map
    (nominal_job) and the split (split_job) on the same rows, stages and keys; delta mu_k = the mean over events of the
    paired difference of observable k (observables: [{quantity photoelectrons | charge | code, channels}], per-event
    sums, functional mean). Its covariance is the digitization noise (the paired differences' covariance / N) plus the
    thinning noise J diag(Var d eps) J^T, J (n_obs x cells in map (bin, channel) order) given or, for photoelectrons and
    charge (linear in eps in expectation), the mean photon number per (event, bin) times the sensor gain for charge.
    Returns the `propagation` of split_check ({delta_mu, cov_delta_mu, A, sigma_tot_design})."""
    events = sorted({r[0] for r in rows})
    a = digitize.digitize(nominal_job(job_one, map_one, run_p), rows)[0]
    b = digitize.digitize(split_job(job_one, map_one, run_one, nominal), rows)[0]
    diff = np.array([_per_event(a, events, o["quantity"], o.get("channels")) -
                     _per_event(b, events, o["quantity"], o.get("channels")) for o in observables])
    cov = np.atleast_2d(np.cov(diff)) / len(events)
    chans = list(map_one["channels"])
    cells = [(r["bin"], c) for r in map_one["form"]["bins"] for c in range(len(chans))]
    n = {r["bin"]: r["emitted"] for r in map_one["form"]["bins"]}
    q = _q(run_one["detections"], nominal)
    var = np.zeros(len(cells))
    ci = {cell: i for i, cell in enumerate(cells)}
    for d, qi in zip(run_one["detections"], q):
        var[ci[(d[0], chans.index(d[1]))]] += qi * (1 - qi)
    var /= np.array([n[bb] for bb, _ in cells], float) ** 2
    if J is None:
        stage = job_one["stage"]
        photons: dict = {}
        for _e, _, bb, large, small, _ in rows:
            photons[bb] = photons.get(bb, 0.0) + stage["light_yield_per_MeV"] * (large + small)
        J = np.zeros((len(observables), len(cells)))
        for k, o in enumerate(observables):
            if o["quantity"] == "code":
                raise SplitError("propagation", f"observable {k} is a code: give J (not linear in eps)")
            g = job_one["sensor"]["gain"] if o["quantity"] == "charge" else 1.0
            for i, (bb, c) in enumerate(cells):
                if o.get("channels") is None or c in o["channels"]:
                    J[k, i] = g * photons.get(bb, 0.0) / len(events)
    J = np.atleast_2d(np.asarray(J, float))
    return {"delta_mu": diff.mean(axis=1).tolist(), "cov_delta_mu": (cov + (J * var) @ J.T).tolist(),
            "A": A, "sigma_tot_design": sigma_tot_design, "digitization_cov": cov.tolist()}


def pair_size_total(p0: float, b: float, d: int = 1) -> float:
    """The detections at efficiency 1 for an exact split to pass jointly with probability >= 0.94 on a total (section
    6.7): K_1 >= (2 + z_{1-0.025/d})^2 (1 - p0)/(p0 b^2), b = 0.1 sigma_tot/p0 the bound relative to p0."""
    z = float(stats.norm.ppf(1 - PAIR_ALPHA / d))
    return (SPREAD_MULTIPLIER + z) ** 2 * (1 - p0) / (p0 * b * b)


def record_findings(record: dict | None, geant4_version: str | None, map_document: dict) -> list[dict]:
    """The split check is redone after any change of the Geant4 version or of the sensor materials or surfaces: the
    plan's split-check record {status, geant4_version, materials_sha256, surfaces_sha256} must be a passed check of the
    current build and map."""
    if record is None:
        return [_plan_f("check_missing", "the PDE split has no split-check record (section 6.7: mandatory)")]
    h = (map_document.get("form") or {}).get("hashes") or {}
    out = []
    if record.get("status") != "passed":
        out.append(_plan_f("check_failed", f"the recorded split check is {record.get('status')!r}"))
    for k, now in (("geant4_version", geant4_version), ("materials_sha256", h.get("materials_sha256")),
                   ("surfaces_sha256", h.get("surfaces_sha256"))):
        if now is not None and record.get(k) != now:
            out.append(_plan_f("check_stale", f"the split check was run at {k} {record.get(k)!r}, now {now!r}: redo "
                               "it"))
    return out


def design_findings(contract: dict, plan: dict, docs: dict, spec_field_types: dict | None = None) -> dict:
    """calib_design.py pde-split: every plan rule of section 6.7 for the PDE split (remedy level plan).
    plan.pde_split = {readouts (route_findings), route1 {stage, component, position, applies_to, stream}, photons
    (name of the efficiency-1 mapping run's photons in docs), map (name of the efficiency-1 map), centre_mm, grid
    (energy edges), prior (p range [lo, hi] or PDE(E) tables), replicas R, joint_keys {label: [hi, lo]},
    scan [{map, detector}] (theta-scan maps), record (the split-check record), split_check {nominal: {p} | {table},
    one, p (photon-file names), propagation | digitize {rows, readout, observables, A, sigma_tot_design, J,
    pipeline}}}. docs: maps {name: map}, photons {name: text}, primaries {name: text},
    detector (spec text), detectors {name: spec text}, pipelines [response-pipeline/1], rows {name: rows}, readouts,
    build_environment."""
    decl = declaration(contract)
    ps = plan.get("pde_split") or {}
    if decl is None:
        raise SplitError("declaration", "the contract declares no pde_split")
    findings: list = []
    out: dict = {"flags": [FLAG]}
    findings += route_findings(contract, ps)
    if ps.get("route1") is not None:
        findings += route1_findings(ps["route1"])
    findings += pair_findings(plan)
    maps = docs.get("maps") or {}
    mp = maps.get(ps.get("map")) if ps.get("map") else None
    sensors = list(decl.get("sensor_surfaces") or [])
    prod_surfaces = None
    if docs.get("detector") is not None and spec_field_types is not None:
        prod_surfaces, _ = mapping_surfaces(docs["detector"], spec_field_types, sensors)
    if mp is not None and prod_surfaces is not None:
        low, high = emission_range(mp)
        prior = ps.get("prior")
        if prior is None and decl.get("model") == "scale":
            par: dict = next((p for p in contract.get("parameters", []) if p["name"] in (decl.get("parameters") or [])), {})
            prior = par.get("sampling_bounds") or par.get("physical_bounds")
        findings += efficiency_test_findings(decl, prod_surfaces, low, high, prior, design=True)
    for i, pt in enumerate(ps.get("scan") or []):
        if spec_field_types is None:
            break
        prod, one = mapping_surfaces(docs["detectors"][pt["detector"]], spec_field_types, sensors)
        for f in surfaces_findings(maps[pt["map"]], prod, sensors, one, path=f"$.plan.pde_split.scan[{i}]"):
            findings.append({**f, "remedy": "plan"})
    run_one = None
    if mp is not None and ps.get("photons"):
        ph = read_photons(docs["photons"][ps["photons"]])
        prim = read_primaries(docs["primaries"][ps.get("primaries", ps["photons"])])
        run_one = binned(mp, ph, prim, ps.get("centre_mm", [0, 0, 0]))
        if decl.get("model") == "table":
            findings += photons_findings(mp, run_one)
            tables = [t for t in (ps.get("prior") or []) if isinstance(t, dict)] or [decl["table"]]
            g = grid_check(mp, run_one, tables, ps.get("grid"))
            out["grid"] = {k: g[k] for k in ("status", "grid")}
            findings += g["findings"]
    labelled: dict = {}
    seeds_used = sorted({int(p["run_seed"]) for p in docs.get("pipelines") or []})
    r1 = ps.get("route1")
    if r1 is not None:
        for s in seeds_used:
            labelled[f"route-1 {route1_stream(r1.get('stage', ''), r1.get('component', 0))} run_seed {s}"] = \
                route1_key(s, r1.get("stage", ""), r1.get("component", 0))
    if mp is not None and decl.get("model") == "table" and ps.get("photons"):
        psha = photons_sha256(docs["photons"][ps["photons"]].encode("utf-8"))
        msha = efficiency_map.map_sha256(mp)
        for r in range(1, int(ps.get("replicas", efficiency_map.MINIMUM_REPLICAS)) + 1):
            labelled[f"calib-map-pde/1 r={r}"] = replica_key(msha, psha, mp["form"]["component"], r)
    for label, k in (ps.get("joint_keys") or {}).items():
        labelled[f"calib-map-joint/1 {label}"] = tuple(k)
    readouts = docs.get("readouts") or []
    findings += key_findings(labelled, [(p, readouts) for p in docs.get("pipelines") or []])
    if mp is not None:
        findings += record_findings(ps.get("record"), (docs.get("build_environment") or {}).get("geant4_version"), mp)
    sc = ps.get("split_check")
    if sc is not None and mp is not None:
        lp = read_photons(docs["photons"][sc["p"]])
        lo = read_photons(docs["photons"][sc["one"]])
        prim = read_primaries(docs["primaries"][sc.get("primaries", sc["one"])])
        r_one = binned(mp, lo, prim, ps.get("centre_mm", [0, 0, 0]))
        r_p = binned(mp, lp, prim, ps.get("centre_mm", [0, 0, 0]))
        prop = sc.get("propagation")
        dg = sc.get("digitize")          # delta mu from both maps digitized with one run_seed
        if dg is not None:
            from core.calibration import design_g4sim
            pipe = docs["pipelines"][int(dg.get("pipeline", 0))]
            rows = [tuple(r) for r in docs["rows"][dg["rows"]]]
            job = design_g4sim.job_from_documents(pipe, mp, dg["readout"], sorted({r[2] for r in rows}),
                                                  int(pipe["run_seed"]))
            prop = digitized_propagation(mp, r_one, r_p, sc["nominal"], job, rows, dg["observables"], dg["A"],
                                         dg["sigma_tot_design"], dg.get("J"))
        chk = split_check(mp, r_one, r_p, sc["nominal"], (lo, lp), prop)
        out["split_check"] = {k: v for k, v in chk.items() if k != "findings"}
        findings += chk["findings"]
    out.update(status="failed" if findings else "passed", findings=findings)
    return out


# ------------------------------------------------------------------ the jobs the evaluator sends (routes 2_1 and 3)
def route21_job(job: dict, p: float) -> dict:
    """The g4sim-digi-job/1 of route 2_1: the efficiency-1 job with efficiencies p eps_c(b) and the efficiency-1 map's
    transit histogram; run_seed, replica 0 and keys rules unchanged (no random stream added)."""
    return {**job, "efficiencies": route21_efficiencies(job["efficiencies"], p)}


def route3_job(job: dict, r3: dict) -> dict:
    """The g4sim-digi-job/1 of route 3 from route3(): its efficiencies and, with timing, its PDE-weighted transit."""
    out = {**job, "efficiencies": {b: r3["efficiencies"][b] for b in job["efficiencies"]}}
    if job.get("timing") and job["timing"]["transit"]["kind"] == "mapped":
        out["timing"] = {**job["timing"], "transit": {**r3["transit"], "counts": {
            b: r3["transit"]["counts"][b] for b in job["timing"]["transit"]["counts"]}}}
    return out


def table_masked(contract: dict) -> bool:
    """Whether a theta or phi binds the PDE(E) table (pointer /pde/table...): the table is then a derived value."""
    return any(b.get("document") == "evaluator" and str(b.get("pointer", "")).startswith("/pde/table")
               for p in contract.get("parameters", []) if p.get("role") in ("theta", "phi")
               for b in p.get("bindings") or [])
