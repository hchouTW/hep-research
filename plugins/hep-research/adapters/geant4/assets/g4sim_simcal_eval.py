#!/usr/bin/env python3
"""The g4sim evaluator of the simulator calibration workflow (Part B sections 6.3, 6.6, 7.1, 11.4; phase 3, WP-B): the
section 7.1 interface for g4sim-backed problems, over the products of g4sim runs (`cells.csv`, `primaries.csv`) and the
three g4sim specifications with `response-pipeline/1`. No Geant4 runs here: resimulation is requested (run cards) through
ask/tell and the products are told back.

  g4sim_calib_eval.py evaluate --plan PLAN.json --theta THETA.json [--batch NAME]
  g4sim_calib_eval.py ask      --plan PLAN.json --points POINTS.json --state STATE.json --series S --study S
                               --events N [--use design] [--ensemble surrogate] [--out DIR]
  g4sim_calib_eval.py tell     --state STATE.json --point ID --run-id RUN_ID --parts BATCH.json [BATCH.json ...]
Output: one JSON object with a status key; exit 0 ok, 2 rejected (bad input), 3 incomplete (a resimulation is needed).

Methods (derived from the binding of each theta, section 11.4 Table 2; outside to inside, section 6.5):
- source of the request (node 0): analytic reweighting with `source-density/1`, w = p_theta(E) / q(E) of the primary;
- Birks k_B of a detector-spec material: deterministic rerun from `edep_by_dedx_class` (no event weights, D75), each
  class's deposit times 1 / (1 + k_B x_c), with `g4sim_simulate.reweighting_bound` reported; with downstream
  scintillation, E^L and E^S of `edep_visible_ly_split` scale by the volume's visible-energy ratio (the split stays the
  nominal k_B's, the section 5.4 approximation: `kB-split-nominal`, P0 at the k_B extremes);
- response-pipeline/1 and condition-snapshot/1 values: re-digitization through `core/simulation/digitize.py` on the
  `g4sim-digi-job/1` path (job built by `design_g4sim.job_from_documents`, run_seed = logical_run_seed, replica = 0), the
  same Geant4 events and Philox keys at every theta (common random numbers, section 6.6);
- a PDE under the split of section 6.7 (spec `pde`: {parameter, route 2_1 | 1, component, nominal}): the job's
  efficiencies p eps_c of the efficiency-1 map (route 2_1), or the per-photon thinning nested in p (route 1); route 3
  ({route 3, photons, primaries (the efficiency-1 mapping run's CSV files), centre_mm, table, parameter and pointer
  /pde/table/value/<k> when a table value is theta}): sum_i PDE(E_i)/n_b and the PDE-weighted transit; all by
  `core/calibration/pde_split.py`;
- any other detector-spec, run-card or request field: resimulation (`g4sim_run`), requested by ask.
The detector-spec Birks constant stays nominal (g4sim_run refuses a read-back difference, section 11.4)."""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
for folder in (str(ROOT), str(Path(__file__).resolve().parent)):
    if folder not in sys.path:
        sys.path.insert(0, folder)

try:  # NumPy (and the engine, which needs it) is reported by main() as a missing dependency (exit 3)
    import numpy as np

    import g4sim_simulate as simulate
    from core.calibration import design_g4sim as DG
    from core.calibration import evaluator as engine_evaluator
    from core.calibration import pde_split
    from core.calibration import io as calib_io
    from core.calibration import reweight, toy
    from core.canonical import canonical_sha256
    from core.simulation import conditions, digitize, response, rng, source_density
    from scipy import stats
    MISSING = None
except ImportError as _exc:
    MISSING = _exc.name or "numpy"

KIND = "g4sim"
STATE_SCHEMA = "g4sim-calib-eval-state/1"
QUANTITIES = ("primary_energy", "edep_visible", "photoelectrons", "charge", "code", "photon_hits", "cherenkov_angle",
              "ring_radius")
PHOTON_QUANTITIES = ("photon_hits", "cherenkov_angle", "ring_radius")
COUPLINGS = ("quantile", "g4sim")
DIGITIZED = ("photoelectrons", "charge", "code")
RESIMULATION_DOCUMENTS = ("detector", "run", "request")


class ResimulationRequired(LookupError):
    """theta needs a Geant4 run that has not been told: the caller asks (exit 3, incomplete)."""

    def __init__(self, message: str, parameters=()):
        super().__init__(message)
        self.parameters = list(parameters)


def method_of(binding: dict) -> str:
    """The method a binding implies (section 11.4 Table 2)."""
    doc, ptr = binding["document"], binding["pointer"]
    if doc == "request" and ptr.startswith("/source/"):
        return "analytic-reweighting"
    if doc == "detector" and ptr.endswith("/birks_mm_per_MeV"):
        return "rerun"
    if doc in ("pipeline", "conditions"):
        return "re-digitization"
    if doc in RESIMULATION_DOCUMENTS:
        return "resimulation"
    raise DG.CheckError("binding.document", f"unknown document {doc!r}")


# ------------------------------------------------------------------ products of a g4sim run
def batch_tables(batch: dict, scorers: dict) -> dict:
    """Per-event tables of one batch (one interval of Geant4 events): primaries {event: E}, dedx {(event, volume): [(class,
    E)]}, split rows (event, volume, bin, E^L, E^S, n^L) from cells.csv (bin 2b holds E^L_b with n^L_b summands, 2b + 1
    holds E^S_b; bin -1 is the direct sum)."""
    first, n = int(batch["first_event"]), int(batch["events"])
    prim = {int(r[0]): float(r[1]) for r in batch.get("primaries", [])}
    direction = {int(r[0]): np.array([float(x) for x in r[5:8]]) for r in batch.get("primaries", []) if len(r) >= 8}
    photons: dict = {}
    for r in batch.get("photons", []):       # photons.csv (S7): event, scorer, volume, arrival, transit, energy eV,
        event = int(r[0])                    # emission point (3), arrival direction (3), parent track
        if not first <= event < first + n:
            raise DG.CheckError("batch.event", f"photon of event {event} is outside the batch [{first}, +{n})")
        photons.setdefault(event, []).append((str(r[1]), int(r[2]), np.array([float(x) for x in r[9:12]])))
    dedx: dict = {}
    split: dict = {}
    for r in batch.get("cells", []):
        event, scorer, volume, b = int(r[0]), str(r[1]), int(r[2]), int(r[3])
        if not first <= event < first + n:
            raise DG.CheckError("batch.event", f"event {event} is outside the batch [{first}, +{n})")
        if b < 0:
            continue
        if scorer == scorers.get("dedx"):
            dedx.setdefault((event, volume), []).append((b, float(r[4])))
        elif scorer == scorers.get("split"):
            row = split.setdefault((event, volume, b // 2), [0.0, 0.0, 0])
            if b % 2 == 0:
                row[0], row[2] = float(r[4]), int(r[5])
            else:
                row[1] = float(r[4])
    return {"first": first, "n": n, "primaries": prim, "directions": direction, "photons": photons, "dedx": dedx,
            "split": [(e, v, b, L, S, k) for (e, v, b), (L, S, k) in sorted(split.items())]}


def merge_parts(parts: list) -> dict:
    """One member from runs on disjoint first_event ranges (array tasks, section 7.1): one logical_run_seed, ranges that
    are disjoint and contiguous; rows are per event, so the merge is their union."""
    if not parts:
        raise DG.CheckError("batch.parts", "no parts")
    seed = {int(p["logical_run_seed"]) for p in parts}
    if len(seed) != 1:
        raise DG.CheckError("batch.parts", f"parts of one member share one logical_run_seed, not {sorted(seed)}")
    ps = sorted(parts, key=lambda p: int(p["first_event"]))
    for a, b in zip(ps, ps[1:]):
        if int(a["first_event"]) + int(a["events"]) != int(b["first_event"]):
            raise DG.CheckError("batch.parts", "the parts' event ranges must be disjoint and contiguous")
    photons = [r for p in ps for r in p.get("photons", [])]        # photons.csv (S7) of optical runs, kept
    return {"logical_run_seed": seed.pop(), "first_event": int(ps[0]["first_event"]),
            "events": sum(int(p["events"]) for p in ps), "cells": [r for p in ps for r in p.get("cells", [])],
            "primaries": [r for p in ps for r in p.get("primaries", [])], **({"photons": photons} if photons else {}),
            **({"point": ps[0]["point"]} if "point" in ps[0] else {})}


def read_csv_rows(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as fh:
        return [row for row in csv.reader(fh) if row and not row[0].startswith("#") and row[0] != "event"]


def photon_values(o: dict, tab: dict, events) -> np.ndarray:
    """Per-event values from photons.csv (g4sim S7, full optical tracking), the detected photons of the observable's
    scorer (o['scorer']) and volumes: `photon_hits`, their number; `cherenkov_angle`, the mean angle between each
    photon's arrival direction and the axis (o['axis'], else the event's primary direction from primaries.csv);
    `ring_radius`, the mean of expansion_mm x tan(angle), the radius on a detection plane at distance o['expansion_mm']
    from the emission (a direct ring: photons no surface turned; o['max_angle_rad'] drops wider ones, e.g. reflected).
    An event without a photon has no angle or radius (NaN: it does not enter the functional)."""
    q = o["quantity"]
    vols = set(o["volumes"]) if o.get("volumes") is not None else None
    scorer = o.get("scorer")
    cut = float(o.get("max_angle_rad", np.pi))
    if q == "ring_radius" and not float(o.get("expansion_mm", 0.0)) > 0:
        raise DG.CheckError("evaluator.observable", f"{o['name']}: ring_radius needs a positive expansion_mm")
    out = np.full(len(events), np.nan if q != "photon_hits" else 0.0)
    fixed = np.asarray(o["axis"], float) if o.get("axis") is not None else None
    for i, e in enumerate(events):
        hits = [d for s, v, d in tab["photons"].get(int(e), []) if (scorer is None or s == scorer)
                and (vols is None or v in vols)]
        if q == "photon_hits":
            out[i] = len(hits)
            continue
        if not hits:
            continue
        axis = fixed if fixed is not None else tab["directions"].get(int(e))
        if axis is None:
            raise DG.CheckError("evaluator.observable", f"{o['name']}: event {e} has no primary direction or axis")
        axis = axis / np.linalg.norm(axis)
        ang = [float(np.arccos(np.clip(d @ axis / np.linalg.norm(d), -1.0, 1.0))) for d in hits]
        ang = [a for a in ang if a <= cut]
        if q == "cherenkov_angle" and ang:
            out[i] = float(np.mean(ang))
        elif q == "ring_radius":
            ang = [a for a in ang if a < np.pi / 2]
            if ang:
                out[i] = float(np.mean(float(o["expansion_mm"]) * np.tan(ang)))
    return out


# ------------------------------------------------------------------ re-digitization coupled across theta
def coupled_digitize(job: dict, rows: list) -> list:
    """The channel rows of digitize.digitize (event, volume, channel index, photoelectrons, charge, code) with the
    multinomial of each bin drawn by a quantile coupling, so that every draw is monotone in theta for fixed uniforms
    and one more photon moves at most a few channel counts (common random numbers that vary smoothly, section 11.4
    "Re-digitization and common random numbers"); the marginal law is g4sim's exactly.

    Per (event, volume, bin), on g4sim's own sub-stream (the scintillation stage's volume key, counter (event, volume
    ID, bin)), the same for every theta: N_b = response.bin_photons (the same draw as g4sim's: inverse transform below
    a mean of 10, the rounded Gaussian of one Box-Muller group above, both monotone in the mean); then one output group
    per channel c, whose first variate u_c gives k_c = F^-1_Binomial(u_c; N_b - sum_{c'<c} k_c', eps_c / (1 - sum_{c'<c}
    eps_c')), the conditional binomials of a multinomial by their quantile functions. The yield factor, the sensor and
    the electronics stages (with conditions) are g4sim's draws on g4sim's streams (continuous in their parameters).
    g4sim's own multinomial (inverse transform or BTPE, rejection with a theta-dependent number of variates) cannot be
    reproduced by a monotone coupling, so the channel split is not g4sim's realization, only its law. Timing (one time
    per detected photon) is not coupled: a job with timing is refused."""
    digitize.check_job(job)
    if job.get("timing"):
        raise DG.CheckError("evaluator.coupling_timing", "the quantile coupling draws no photon times; use coupling "
                            "g4sim for a job with timing")
    stage, sensor, electronics = job["stage"], job["sensor"], job["electronics"]
    document = {"run_seed": job["run_seed"], "replica": job["replica"]}
    count = len(job["channels"])
    key = rng.volume_key(job["run_seed"], stage["name"], job["replica"])
    grouped: dict = {}
    for event, volume, b, large, small, steps in rows:
        bins = grouped.setdefault((int(event), int(volume)), {})
        if b in bins:
            raise digitize.DigiError("bin-twice", f"event {event}, volume {volume}: bin {b} appears twice")
        bins[b] = (large, small, steps)
    owners, totals, uniforms, effs = [], [], [], []
    for (event, volume), bins in sorted(grouped.items()):
        factor = response.yield_factor(document, event, volume, stage.get("yield_relative_width", 0.0))
        for b in sorted(bins):
            eff = job["efficiencies"].get(str(b))
            if eff is None:
                raise digitize.DigiError("efficiencies", f"bin {b} has no efficiencies")
            stream = rng.SubStream(key, event, volume, b)
            large, small, steps = bins[b]
            totals.append(response.bin_photons(stream, stage["light_yield_per_MeV"], stage["resolution_scale"], large,
                                               small, steps, factor))
            uniforms.append([stream.group()[0] for _ in range(count)])
            effs.append(eff)
            owners.append((event, volume))
    pe: dict = {k: np.zeros(count, dtype=np.int64) for k in grouped}
    if totals:
        left = np.asarray(totals, dtype=np.int64)
        U, P = np.asarray(uniforms, float), np.asarray(effs, float)
        rest = np.ones(len(left))
        K = np.zeros((len(left), count), dtype=np.int64)
        for c in range(count):
            q = np.clip(np.divide(P[:, c], rest, out=np.zeros_like(rest), where=rest > 0), 0.0, 1.0)
            k = np.where((left > 0) & (q > 0), stats.binom.ppf(U[:, c], left, q), 0.0)
            K[:, c] = np.minimum(np.nan_to_num(k, nan=0.0).astype(np.int64), left)
            left = left - K[:, c]
            rest = rest - P[:, c]
        for i, o in enumerate(owners):
            pe[o] += K[i]
    sensor_key = rng.channel_key(job["run_seed"], job["readout"], sensor["name"], job["replica"])
    electronics_key = rng.channel_key(job["run_seed"], job["readout"], electronics["name"], job["replica"])
    out = []
    for (event, volume) in sorted(grouped):
        for at in range(count):
            cell = volume * count + at
            state = {"gain_factor": 1.0, "dead": False}
            if "conditions" in job:
                time = job["event_time_ns"].get(str(event))
                if time is None:
                    raise digitize.DigiError("event-time", f"event {event} has no time")
                state = conditions.at(job["conditions"], time, {"volume": volume, "channel": at})
            n_pe = int(pe[(event, volume)][at])
            charge = response.sensor_response(rng.SubStream(sensor_key, event, cell), n_pe,
                                              sensor["gain"] * state["gain_factor"], sensor["excess_noise"],
                                              sensor["dark_rate_per_ns"], sensor["gate_ns"])
            code = response.electronics_response(rng.SubStream(electronics_key, event, cell), charge,
                                                 electronics["noise_sigma"], state.get("threshold",
                                                                                       electronics["threshold"]),
                                                 electronics["lsb"], electronics["bits"])
            out.append((event, volume, at, n_pe, charge, None if state["dead"] else code))
    return out


# ------------------------------------------------------------------ the evaluator
class G4simEvaluator:
    """Section 7.1 over g4sim products. spec (plan['evaluator']): documents {detector, request, run, pipeline, maps:
    {name: map}, conditions}, readout, map (a name of maps), scorers {split, dedx}, birks_material, batches {name: batch},
    nominal (batch name), reference (an independent batch for P0), observables [{name, quantity, functional, volumes,
    channels, threshold}], run (the label of the observables' exposure, default g4sim)."""

    def __init__(self, spec: dict, plan: dict):
        plan = DG.resolve(plan, spec.get("contract"))    # the contract's locked bindings (section 5.1)
        self.spec, self.plan = spec, plan
        self.documents = spec["documents"]
        self.readout = spec.get("readout")
        self.scorers = spec.get("scorers") or {}
        self.run = spec.get("run", KIND)
        self.bindings = DG.bindings(plan)
        self.parameters = list(self.bindings)
        self.methods = {p: method_of(b) for p, b in self.bindings.items()}
        self.pde = spec.get("pde")       # the PDE split of section 6.7 (see the module docstring)
        if self.pde and self.pde.get("route", "2_1") not in ("2_1", "1", "3"):
            raise DG.CheckError("evaluator.pde_route", "the PDE-split routes are 2_1, 1 and 3")
        if self.pde and self.pde.get("route") == "3":    # the efficiency-1 mapping run's photons.csv (section 6.7)
            self.pde_run = pde_split.binned(self.documents["maps"][spec["map"]],
                                            pde_split.read_photons(self.pde["photons"]),
                                            pde_split.read_primaries(self.pde["primaries"]), self.pde["centre_mm"])
            self.pde_index = int(str(self.pde.get("pointer", "/pde/table/value/0")).rsplit("/", 1)[1])
        if self.pde and self.pde.get("parameter"):
            self.bindings[self.pde["parameter"]] = {"document": "evaluator", "pointer": "/pde"}
            self.parameters.append(self.pde["parameter"])
            self.methods[self.pde["parameter"]] = "re-digitization"
        self.light_yield_density = spec.get("light_yield_density", "poisson")       # section 15.3.19 (A24): "normal" only in its test
        if self.light_yield_density not in ("poisson", "normal"):
            raise DG.CheckError("evaluator.light_yield_density", "the photon-count density is poisson (or normal, a test)")
        for p, m in (plan.get("methods") or {}).items():
            if p in self.methods and m == "analytic-reweighting" and self.methods[p] == "re-digitization" \
                    and self._is_ly(p):        # section 11.4 Table 2: LY only, Poisson interval only (A24)
                self.methods[p] = m
                continue
            if p in self.methods and m != self.methods[p] and not (m == "surrogate-model"
                                                                   and self.methods[p] == "resimulation"):
                raise DG.CheckError("evaluator.method", f"{p}: the plan's method {m} is not the one its binding allows "
                                    f"({self.methods[p]}, section 11.4 Table 2)")
        src = (self.documents.get("request") or {}).get("source") or {}
        if src.get("density") != "analytic" and any(b["document"] == "request" for b in self.bindings.values()):
            raise DG.CheckError("evaluator.source_density", "node 0 is reweighted only with an analytic source "
                                "(source-density/1); an external source is rejected (section 5.2)")
        self.nominal_theta = {p: DG.nominal_value(self.documents, b)
                              for p, b in self.bindings.items() if b["document"] != "evaluator"}
        if self.pde and self.pde.get("parameter"):
            self.nominal_theta[self.pde["parameter"]] = float(self.pde["table"]["value"][self.pde_index]) \
                if self.pde.get("route") == "3" else float(self.pde.get("nominal", 1.0))
        self.coupling = spec.get("coupling", "quantile")   # re-digitization coupled across theta (default), or g4sim's
        if self.coupling not in COUPLINGS:              # own stream exactly (digitize.digitize)
            raise DG.CheckError("evaluator.coupling", f"coupling {self.coupling!r} is one of {COUPLINGS}")
        self.digitization_path = "job-coupled" if self.coupling == "quantile" else "job"
        self.observable_specs = list(spec.get("observables") or [])
        for o in self.observable_specs:
            if o["quantity"] not in QUANTITIES:
                raise DG.CheckError("evaluator.observable", f"{o['name']}: quantity {o['quantity']!r}")
        self.observables = [o["name"] for o in self.observable_specs]
        self.batches = dict(spec.get("batches") or {})
        self.nominal_batch = spec.get("nominal", "nominal")
        self.state_path = spec.get("state")
        self._check_batches()

    # ---- common random numbers and independence (section 6.6)
    def _check_batches(self):
        """Batches are independent sets of Geant4 events: pairwise non-overlapping (logical_run_seed, interval) unless
        declared the same set; checked by calib_design's implementation of the section 6.6 check."""
        evs = [{"run_id": name, "use": b.get("use", "evaluation"), "set": b.get("set", name),
                "logical_run_seed": b["logical_run_seed"], "first_event": b["first_event"], "events": b["events"],
                "run_seed": b["logical_run_seed"], "replica": 0} for name, b in self.batches.items()]
        r = DG.interval_findings({"evaluations": evs})
        if r["findings"]:
            raise DG.CheckError("evaluator.batches", "; ".join(f["message"] for f in r["findings"]))

    def default_method(self, par: str) -> str:
        return self.methods[par]

    def _is_ly(self, par: str) -> bool:
        b = self.bindings.get(par) or {}
        return b.get("document") == "pipeline" and str(b.get("pointer", "")).endswith("/light_yield_per_MeV/value")

    def _ly_weights(self, par, value, tab, events, batch):
        """Section 11.4 Table 2, LY by analytic reweighting when only LY changes and only the Poisson interval is used:
        per (event, volume, bin) the photon count N_b of g4sim's own draw at the nominal LY (the scintillation stage's
        sub-stream, response.bin_photons: Poisson below a mean of 10) weighted by p(N_b; mu_b LY'/LY0) / p(N_b; mu_b),
        p the registered density (`light_yield_density`: Poisson; normal only for the section 15.3.19 negative test). A bin whose
        mean at LY0 or LY' exceeds the Poisson interval is refused (re-digitization is then the method)."""
        docs = self.documents
        job = DG.job_from_documents(docs["pipeline"], docs["maps"][self.spec["map"]], self.readout,
                                    sorted({r[2] for r in tab["split"]}) or [0], int(batch["logical_run_seed"]))
        stage = job["stage"]
        ly0, ly1 = float(stage["light_yield_per_MeV"]), float(value)
        document = {"run_seed": job["run_seed"], "replica": job["replica"]}
        key = rng.volume_key(job["run_seed"], stage["name"], job["replica"])
        idx = {int(e): i for i, e in enumerate(events)}
        logw = np.zeros(len(events))
        for e, v, b, large, small, steps in tab["split"]:
            factor = response.yield_factor(document, int(e), int(v), stage.get("yield_relative_width", 0.0))
            m0 = ly0 * (large + small) * factor
            m1 = ly1 * (large + small) * factor
            if max(m0, m1) > response.POISSON_LIMIT:
                raise DG.CheckError("evaluator.poisson_interval", f"{par}: event {e}, volume {v}, bin {b} has a mean "
                                    f"of {max(m0, m1):.3g} photons > {response.POISSON_LIMIT} (Table 2: analytic "
                                    "reweighting of LY only in the Poisson interval; re-digitize)")
            n = response.bin_photons(rng.SubStream(key, int(e), int(v), int(b)), ly0, stage["resolution_scale"],
                                     large, small, steps, factor)
            if self.light_yield_density == "normal":
                lp = stats.norm.logpdf(n, m1, math.sqrt(max(m1, 1e-300))) - stats.norm.logpdf(n, m0, math.sqrt(max(m0, 1e-300)))
            else:
                lp = stats.poisson.logpmf(n, m1) - stats.poisson.logpmf(n, m0)
            logw[idx[int(e)]] += lp
        return np.exp(logw)

    def _batch(self, seeds: dict | None, theta: dict):
        name = (seeds or {}).get("batch", self.nominal_batch)
        resim = [p for p in theta if self.methods.get(p) == "resimulation" and not _same(theta[p], self.nominal_theta[p])]
        if resim:
            name = self._told_batch({p: theta[p] for p in resim})
            if name is None:
                raise ResimulationRequired(f"{resim} at {theta} need a g4sim_run that has not been told (ask)", resim)
        if name not in self.batches:
            raise DG.CheckError("evaluator.batch", f"no batch {name!r}")
        return name, self.batches[name]

    def _told_batch(self, point: dict):
        for name, b in self.batches.items():
            pt = b.get("point") or {}
            if pt and all(p in pt and _same(pt[p], v) for p, v in point.items()):
                return name
        for pid, rec in (_load_state(self.state_path).get("points") or {}).items() if self.state_path else ():
            if rec.get("status") == "told" and all(_same(rec["theta"].get(p), v) for p, v in point.items()):
                self.batches[f"point:{pid}"] = rec["batch"]
                return f"point:{pid}"
        return None

    # ---- section 7.1 interface
    def evaluate(self, theta: dict, phi: dict | None = None, psi: dict | None = None, model: str = "nominal",
                 effects_off=(), seeds: dict | None = None, names=None) -> dict:
        """The prediction at theta (phi and psi bound like theta): reweighting of node 0, the Birks rerun and the
        re-digitization on the batch `seeds['batch']` (default: the nominal batch), so every theta uses the same
        Geant4 events and Philox keys; resimulation-level theta read the batch told for that point. effects_off
        ({effect: {parameter: value after removal}}, section 10.5) sets those parameters last, with the same methods."""
        if model != "nominal":
            raise DG.CheckError("evaluator.model", "enumerated models are separate g4sim specifications (phase 4)")
        try:                                                       # section 10.5: the declared values after removal
            removal = engine_evaluator.removal_values(effects_off)
        except ValueError as exc:
            raise DG.CheckError("evaluator.effects_off", str(exc)) from exc
        unknown = sorted(set(removal) - set(self.nominal_theta))
        if unknown:
            raise DG.CheckError("evaluator.effects_off", f"effects_off removes parameters {unknown} that this "
                                "evaluator does not evaluate")
        values = {**self.nominal_theta, **(psi or {}), **(phi or {}), **(theta or {}), **removal}
        bname, batch = self._batch(seeds, values)
        return self._observe(values, bname, batch, names)

    def birks_parameter(self):
        """The k_B parameter evaluated by the deterministic rerun (section 5.4), or None."""
        kb_pars = [p for p, m in self.methods.items() if m == "rerun"]
        return kb_pars[0] if kb_pars else None

    def birks_bound_shift(self, theta: dict, sign: int, names=None, seeds: dict | None = None) -> dict:
        """The prediction at theta with every (event, volume) visible energy moved by sign x its class-discretization
        bound (g4sim_simulate.reweighting_bound at theta's k_B; section 5.4), carried into the scintillation bins
        the same way as the rerun itself; the P5 feasibility item of section 5.4 compares it with the plain one."""
        if sign not in (-1, 1):
            raise DG.CheckError("evaluator.birks_bound", "sign is +1 or -1")
        self._bound_sign = int(sign)
        try:
            return self.evaluate(theta, seeds=seeds, names=names)
        finally:
            self._bound_sign = 0

    def _kb_visible(self, rows, kb):
        """edep_visible of one (event, volume) at k_B, moved by the bound when birks_bound_shift asks for it (the
        downward move stops at 0: a visible energy is never negative)."""
        v = simulate.reweighted(rows, kb)
        s = getattr(self, "_bound_sign", 0)
        return max(v + s * simulate.reweighting_bound(rows, kb), 0.0) if s else v

    def _observe(self, values: dict, bname: str, batch: dict, names=None, given=None) -> dict:
        tab = batch_tables(batch, self.scorers)
        events = np.arange(tab["first"], tab["first"] + tab["n"])
        changed = {p: v for p, v in values.items() if p in self.methods and not _same(v, self.nominal_theta[p])}
        flags = []
        w, missing, diag = self._weights(values, changed, tab, events, batch)
        kb, kb0 = self._birks(values, batch)
        vis, bound = self._visible(tab, events, kb) if kb is not None else (None, None)
        need_digi = any(o["quantity"] in DIGITIZED for o in self.observable_specs)
        rows = None
        if need_digi:
            rows = given if given is not None else self._digitize(values, tab, batch, kb, kb0)
            if kb is not None and not _same(kb, kb0):
                flags.append("kB-split-nominal")
        per = {}
        for o in self.observable_specs:
            per[o["name"]] = self._values(o, tab, events, vis, rows)
        specs = [o for o in self.observable_specs if names is None or o["name"] in names]
        obs = [toy.Observable(o["name"], self.run, (lambda ev, n=o["name"]: ev["values"][n]),
                              o.get("functional", "mean"),
                              (lambda ev, n=o["name"]: np.isfinite(ev["values"][n]))) for o in specs]
        holder = type("M", (), {"observables": obs})()
        out = toy.observe(holder, {self.run: {"values": per}}, {self.run: w}, [o.name for o in obs])
        if bound is not None:                       # the mean over events of each event's bound (section 5.4)
            out["birks_bound_MeV"] = {o["name"]: float(np.mean(self._values({**o, "functional": "mean"}, tab, events,
                                      bound, rows))) for o in specs if o["quantity"] == "edep_visible"}
        out.update({"V_emu": None, "V_learn": None, "node_diag": diag, "theta": values, "batch": bname,
                    "methods": {p: self.methods[p] for p in changed}, "missing_support_runs": missing,
                    "flags": flags, "digitization": self.digitization_path if need_digi else None, "seeds": {"logical_run_seed": int(batch["logical_run_seed"]),
                                              "first_event": tab["first"], "events": tab["n"]}})
        return out

    def _weights(self, values, changed, tab, events, batch=None):
        w = np.ones(len(events))
        diag: dict = {}
        for p in [p for p in changed if self.methods[p] == "analytic-reweighting" and self._is_ly(p)
                  and not getattr(self, "_reference", False)]:   # the reference (P0) re-digitizes LY at theta
            if any(self.methods[q] == "rerun" for q in changed):
                raise DG.CheckError("evaluator.poisson_interval", "LY is reweighted only when LY alone changes in the "
                                    "scintillation stage (Table 2); a k_B change re-digitizes")
            w = w * self._ly_weights(p, values[p], tab, events, batch)
            diag["photon_generation"] = {"n_eff": reweight.kish(w), "pareto_k": reweight.pareto_k(w),
                                         "max_weight_fraction": float(w.max() / w.sum()) if w.sum() > 0 else None}
        src = [p for p in changed if self.methods[p] == "analytic-reweighting" and not self._is_ly(p)]
        if not src:
            return w, [], diag
        request = self.documents["request"]
        target = DG.apply_theta({"request": request}, self.plan, {p: values[p] for p in src})["request"]
        q = source_density.density(request["source"])
        p = source_density.density(target["source"])
        missing = []
        for i, e in enumerate(events):
            E = tab["primaries"].get(int(e))
            if E is None:
                raise DG.CheckError("evaluator.primaries", f"event {e} has no primary (primaries.csv)")
            qe = source_density.energy_density(q, E)
            if qe <= 0:
                missing.append(self.run)
                w[i] = 0.0
                continue
            w[i] *= source_density.energy_density(p, E) / qe
        node = {"n_eff": reweight.kish(w), "pareto_k": reweight.pareto_k(w),
                "max_weight_fraction": float(w.max() / w.sum()) if w.sum() > 0 else None}
        return w, sorted(set(missing)), {**diag, "source": node}

    def _birks(self, values, batch=None):
        """(k_B at theta, k_B the batch's split was scored at): the nominal k_B, or the k_B of a run told at a k_B
        point (a full g4sim_run at k_B', whose split is already k_B''s and is not scaled again)."""
        kb_pars = [p for p, m in self.methods.items() if m == "rerun"]
        if not kb_pars:
            return None, None
        p = kb_pars[0]
        own = ((batch or {}).get("point") or {}).get(p)
        return float(values[p]), float(self.nominal_theta[p] if own is None else own)

    def _visible(self, tab, events, kb):
        """edep_visible per (event, volume) from edep_by_dedx_class at k_B, with the section 5.4 discretization bound."""
        vis, bound = {}, {}
        for key, rows in tab["dedx"].items():
            vis[key] = self._kb_visible(rows, kb)
            bound[key] = simulate.reweighting_bound(rows, kb)
        return vis, bound

    def _digitize(self, values, tab, batch, kb, kb0):
        pde = (self.pde or {}).get("parameter")
        redigi = ("re-digitization",) + (("analytic-reweighting",) if getattr(self, "_reference", False) else ())
        docs = DG.apply_theta(self.documents, self.plan, {p: v for p, v in values.items() if p != pde and (
            self.methods.get(p) == "re-digitization" or (self.methods.get(p) in redigi and self._is_ly(p)))})
        rows = tab["split"]
        if kb is not None and (not _same(kb, kb0) or getattr(self, "_bound_sign", 0)):
            scaled = []
            for e, v, b, L, S, k in rows:
                d = tab["dedx"].get((e, v))
                if d is None:
                    raise DG.CheckError("evaluator.birks", f"event {e}, volume {v}: no edep_by_dedx_class rows to carry "
                                        "a k_B change into the scintillation bins")
                r0 = simulate.reweighted(d, kb0)
                f = self._kb_visible(d, kb) / r0 if r0 > 0 else 1.0
                scaled.append((e, v, b, L * f, S * f, k))
            rows = scaled
        snapshot = docs.get("conditions")
        job = DG.job_from_documents(docs["pipeline"], docs["maps"][self.spec["map"]], self.readout,
                                    sorted({r[2] for r in rows}) or [0], int(batch["logical_run_seed"]),
                                    conditions=snapshot, event_time=self.plan.get("event_time"),
                                    interval=(tab["first"], tab["n"]) if snapshot is not None else None)
        if self.pde and self.pde.get("route") == "3":   # sum_i PDE(E_i)/n_b and the PDE-weighted transit
            table = {"energy_eV": list(self.pde["table"]["energy_eV"]), "value": list(self.pde["table"]["value"])}
            if pde:
                table["value"][self.pde_index] = float(values.get(pde, self.nominal_theta[pde]))
            job = pde_split.route3_job(job, pde_split.route3(docs["maps"][self.spec["map"]], self.pde_run, table))
        elif pde:                        # job efficiencies p eps (route 2_1) or the nested thinning (route 1)
            p = float(values.get(pde, self.nominal_theta[pde]))
            if self.pde.get("route", "2_1") == "1":
                return pde_split.digitize_route1(job, rows, p, int(self.pde.get("component", 1)))[0]
            job = pde_split.route21_job(job, p)
        if self.coupling == "quantile":
            return coupled_digitize(job, rows)
        channel_rows, _ = digitize.digitize(job, rows)
        return channel_rows

    def _values(self, o, tab, events, vis, rows):
        q = o["quantity"]
        idx = {int(e): i for i, e in enumerate(events)}
        x = np.zeros(len(events))
        vols = set(o["volumes"]) if o.get("volumes") is not None else None
        if q == "primary_energy":
            return np.array([tab["primaries"].get(int(e), np.nan) for e in events])
        if q in PHOTON_QUANTITIES:
            x = photon_values(o, tab, events)
            return (x >= float(o.get("threshold", 0.0))).astype(float) if o.get("functional") == "fraction" else x
        if q == "edep_visible":
            if vis is None:
                raise DG.CheckError("evaluator.observable", f"{o['name']}: edep_visible needs a k_B binding and "
                                    "edep_by_dedx_class")
            for (e, v), val in vis.items():
                if vols is None or v in vols:
                    x[idx[e]] += val
        else:
            col = {"photoelectrons": 3, "charge": 4, "code": 5}[q]
            chans = set(o["channels"]) if o.get("channels") is not None else None
            for r in rows:
                if (vols is None or r[1] in vols) and (chans is None or r[2] in chans):
                    x[idx[r[0]]] += 0.0 if r[col] is None else float(r[col])
        if o.get("functional") == "fraction":
            x = (x >= float(o.get("threshold", 0.0))).astype(float)
        return x

    def resample(self, node: str, theta: dict, phi: dict | None, psi: dict | None, model: str, inputs,
                 seeds: dict) -> object:
        """Direct sampling of a node (section 7.1): node 1 (transport) is a g4sim_run, read from the batch told at
        theta; a response stage is the digitization of the batch `seeds['batch']` (new Geant4 events, its own keys)
        at theta, recomputed as a whole segment from the stored scorer quantities (no stage 2 -> 3 hand-off)."""
        values = {**self.nominal_theta, **(psi or {}), **(phi or {}), **(theta or {})}
        self._reference = True                    # the direct sampling: LY re-digitized, never reweighted (P0's reference)
        try:
            return self._resample(node, values, seeds, theta)
        finally:
            self._reference = False

    def _resample(self, node, values, seeds, theta):
        if node == "transport":                   # the run told at theta (every parameter off nominal, e.g. a light-yield
            name = self._told_batch({p: values[p] for p in self.methods  # spot check, section 5.4)
                                     if self.methods[p] in ("rerun", "resimulation")
                                     or not _same(values[p], self.nominal_theta[p])})
            if name is None:
                raise ResimulationRequired(f"node {node} at {theta} is a g4sim_run that has not been told (ask)")
            return {"batch": name}
        bname, batch = self._batch(seeds, values)
        tab = batch_tables(batch, self.scorers)
        kb, kb0 = self._birks(values, batch)
        return {"batch": bname, "channel_rows": self._digitize(values, tab, batch, kb, kb0)}

    def evaluate_from(self, node: str, samples, theta: dict, phi: dict | None, psi: dict | None, model: str,
                      seeds: dict, names=None) -> dict:
        """The observables from a node's output (for P0): the batch of the samples, with the given channel rows."""
        values = {**self.nominal_theta, **(psi or {}), **(phi or {}), **(theta or {})}
        batch = self.batches[samples["batch"]]
        self._reference = True                    # P0's reference: LY re-digitized at theta, not reweighted
        try:
            out = self._observe(values, samples["batch"], batch, names, given=samples.get("channel_rows"))
        finally:
            self._reference = False
        out["independent_runs"] = [] if self._same_set(samples["batch"], self.nominal_batch) else [self.run]
        return out

    def _same_set(self, a: str, b: str) -> bool:
        """Two batches are one set of Geant4 events (paired, section 6.6) when they are the same batch, or declare the same
        `set` on the same logical_run_seed and interval (a rerun of those events at another k_B: without optical photons
        k_B draws no random number in transport)."""
        if a == b:
            return True
        x, y = self.batches[a], self.batches[b]
        key = ("logical_run_seed", "first_event", "events")
        return "set" in x and x.get("set") == y.get("set") and all(x[k] == y[k] for k in key)

    def learned_closure(self, fold):
        raise NotImplementedError("learned density ratios are not g4sim's (phase 5)")

    # ---- ask/tell (section 7.1): resimulation requests and their products
    def ask(self, points: list, state_path: str, *, series: str, study: str, events: int, use: str = "design",
            ensemble: str = "surrogate", registered=()) -> list:
        """One g4sim_run request per design point (section 6.4: only the fields holding theta change), all on one seed
        block and one event interval (common random numbers across the design, section 6.6); the state file records
        each point's request and, after tell, its run_id."""
        seed, t = DG.block_seed(series, study, use, ensemble, 0, registered)
        first, n = DG.member_interval(0, int(events), 1)
        state = _load_state(state_path)
        out = []
        for i, theta in enumerate(points):
            unknown = [p for p in theta if p not in self.methods]
            if unknown:
                raise DG.CheckError("evaluator.parameter", f"point {i}: no binding for {unknown}")
            docs = DG.apply_theta(self.documents, self.plan, theta)
            card = json.loads(json.dumps(docs["run"]))
            card.setdefault("run", {}).update(logical_run_seed=seed, first_event=first, events=n)
            pid = f"{i}"
            req = {"point_id": pid, "theta": dict(theta), "logical_run_seed": seed, "seed_t": t, "first_event": first,
                   "events": n, "run": card, "detector": docs["detector"], "request": docs["request"],
                   "run_sha256": canonical_sha256(card), "detector_sha256": canonical_sha256(docs["detector"]),
                   "request_sha256": canonical_sha256(docs["request"])}
            state.setdefault("points", {})[pid] = {"theta": dict(theta), "status": "asked", "run_id": None,
                                                    "run_sha256": req["run_sha256"],
                                                    "detector_sha256": req["detector_sha256"],
                                                    "logical_run_seed": seed, "first_event": first, "events": n}
            out.append(req)
        state["schema"] = STATE_SCHEMA
        calib_io.write_json(state_path, state)
        return out

    @staticmethod
    def tell(state_path: str, point_id: str, run_id: str, parts: list) -> dict:
        """Record a point's run_id and its products (parts on disjoint first_event ranges, merged); the merged member
        must be the asked seed and interval."""
        state = _load_state(state_path)
        rec = (state.get("points") or {}).get(point_id)
        if rec is None:
            raise DG.CheckError("tell.point", f"no asked point {point_id!r}")
        batch = merge_parts(parts)
        if (batch["logical_run_seed"], batch["first_event"], batch["events"]) != (rec["logical_run_seed"],
                                                                                  rec["first_event"], rec["events"]):
            raise DG.CheckError("tell.interval", f"point {point_id}: the products are not the asked seed and interval")
        batch["point"] = rec["theta"]
        rec.update(status="told", run_id=run_id, batch=batch)
        calib_io.write_json(state_path, state)
        return rec


def _same(a, b) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) <= 1e-15 * max(1.0, abs(float(b)))


def _load_state(path) -> dict:
    if not path or not Path(path).is_file():
        return {"schema": STATE_SCHEMA, "points": {}}
    return calib_io.load(str(path))


def build(spec: dict, plan: dict) -> G4simEvaluator:
    """The builder registered with core/calibration/evaluator.py under the plan's evaluator kind `g4sim`."""
    return G4simEvaluator(spec, plan)


if MISSING is None:
    engine_evaluator.register(KIND, build)


# ------------------------------------------------------------------ CLI
def _resolve(plan: dict, base: Path) -> dict:
    """The plan's evaluator spec with document and product paths read (relative to the plan's folder)."""
    spec = json.loads(json.dumps(plan.get("evaluator") or {}))
    docs = spec.get("documents") or {}
    for k, v in list(docs.items()):
        if k == "maps":
            docs[k] = {m: calib_io.load(str(base / p)) if isinstance(p, str) else p for m, p in v.items()}
        elif isinstance(v, str):
            docs[k] = calib_io.load(str(base / v))
    for b in (spec.get("batches") or {}).values():
        for key in ("cells", "primaries", "photons"):
            if isinstance(b.get(key), str):
                b[key] = read_csv_rows(base / b[key])
    for key in ("photons", "primaries"):          # route 3 of the PDE split: the mapping run's CSV files as text
        if isinstance((spec.get("pde") or {}).get(key), str):
            spec["pde"][key] = (base / spec["pde"][key]).read_text(encoding="utf-8")
    if isinstance(spec.get("state"), str):
        spec["state"] = str(base / spec["state"])
    return spec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--plan", required=True)
    ev.add_argument("--theta", required=True)
    ev.add_argument("--batch")
    ak = sub.add_parser("ask")
    for a in ("--plan", "--points", "--state", "--series", "--study"):
        ak.add_argument(a, required=True)
    ak.add_argument("--events", type=int, required=True)
    ak.add_argument("--use", default="design")
    ak.add_argument("--ensemble", default="surrogate")
    tl = sub.add_parser("tell")
    for a in ("--state", "--point", "--run-id"):
        tl.add_argument(a, required=True)
    tl.add_argument("--parts", nargs="+", required=True)
    args = ap.parse_args(argv)
    if MISSING:  # exit 3, a missing dependency (hep-computing script contract)
        print(json.dumps({"status": "missing-dependency", "reason": f"{MISSING} is not installed: pip install numpy"}))
        return 3

    def go():
        try:
            if args.cmd == "tell":
                rec = G4simEvaluator.tell(args.state, args.point, args.run_id, [calib_io.load(p) for p in args.parts])
                return {"status": "ok", "point": args.point, "run_id": rec["run_id"]}
            plan = calib_io.load_object(args.plan, ("evaluator",))
            spec = _resolve(plan, Path(args.plan).resolve().parent)
            if spec.get("kind") != KIND:
                raise calib_io.InputError(f"the plan's evaluator kind is {spec.get('kind')!r}, not {KIND}")
            e = engine_evaluator.make({**plan, "evaluator": spec})
            if args.cmd == "evaluate":
                theta = calib_io.load_object(args.theta)
                r = e.evaluate(theta, seeds={"batch": args.batch} if args.batch else None)
                return {"status": "ok", "names": r["names"], "pred": r["pred"], "V_MC": r["V_MC"], "n_eff": r["n_eff"],
                        "node_diag": r["node_diag"], "methods": r["methods"], "batch": r["batch"], "seeds": r["seeds"],
                        "flags": r["flags"], **({"birks_bound_MeV": r["birks_bound_MeV"]}
                                                                    if "birks_bound_MeV" in r else {})}
            reqs = e.ask(calib_io.load(args.points), args.state, series=args.series, study=args.study,
                         events=args.events, use=args.use, ensemble=args.ensemble)
            return {"status": "ok", "requests": reqs}
        except ResimulationRequired as exc:
            return {"status": "incomplete", "reason": str(exc), "parameters": exc.parameters}
        except (DG.CheckError, digitize.DigiError, source_density.SourceError) as exc:
            return {"status": "rejected", "code": getattr(exc, "code", None), "error": str(exc)}
    return calib_io.run(lambda: calib_io.jsonable(go()))


if __name__ == "__main__":
    sys.exit(main())
