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
- any other detector-spec, run-card or request field: resimulation (`g4sim_run`), requested by ask.
The detector-spec Birks constant stays nominal (g4sim_run refuses a read-back difference, section 11.4)."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
for folder in (str(ROOT), str(Path(__file__).resolve().parent)):
    if folder not in sys.path:
        sys.path.insert(0, folder)

import numpy as np  # noqa: E402

import g4sim_simulate as simulate  # noqa: E402
from core.calibration import design_g4sim as DG  # noqa: E402
from core.calibration import evaluator as engine_evaluator  # noqa: E402
from core.calibration import io as calib_io  # noqa: E402
from core.calibration import reweight, toy  # noqa: E402
from core.canonical import canonical_sha256  # noqa: E402
from core.simulation import digitize, source_density  # noqa: E402

KIND = "g4sim"
STATE_SCHEMA = "g4sim-calib-eval-state/1"
QUANTITIES = ("primary_energy", "edep_visible", "photoelectrons", "charge", "code")
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
    return {"first": first, "n": n, "primaries": prim, "dedx": dedx,
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
    return {"logical_run_seed": seed.pop(), "first_event": int(ps[0]["first_event"]),
            "events": sum(int(p["events"]) for p in ps), "cells": [r for p in ps for r in p.get("cells", [])],
            "primaries": [r for p in ps for r in p.get("primaries", [])], **({"point": ps[0]["point"]}
                                                                           if "point" in ps[0] else {})}


def read_csv_rows(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as fh:
        return [row for row in csv.reader(fh) if row and not row[0].startswith("#") and row[0] != "event"]


# ------------------------------------------------------------------ the evaluator
class G4simEvaluator:
    """Section 7.1 over g4sim products. spec (plan['evaluator']): documents {detector, request, run, pipeline, maps:
    {name: map}, conditions}, readout, map (a name of maps), scorers {split, dedx}, birks_material, batches {name: batch},
    nominal (batch name), reference (an independent batch for P0), observables [{name, quantity, functional, volumes,
    channels, threshold}], run (the label of the observables' exposure, default g4sim)."""

    def __init__(self, spec: dict, plan: dict):
        self.spec, self.plan = spec, plan
        self.documents = spec["documents"]
        self.readout = spec.get("readout")
        self.scorers = spec.get("scorers") or {}
        self.run = spec.get("run", KIND)
        self.bindings = DG.bindings(plan)
        self.parameters = list(self.bindings)
        self.methods = {p: method_of(b) for p, b in self.bindings.items()}
        for p, m in (plan.get("methods") or {}).items():
            if p in self.methods and m != self.methods[p] and not (m == "surrogate-model"
                                                                   and self.methods[p] == "resimulation"):
                raise DG.CheckError("evaluator.method", f"{p}: the plan's method {m} is not the one its binding allows "
                                    f"({self.methods[p]}, section 11.4 Table 2)")
        src = (self.documents.get("request") or {}).get("source") or {}
        if src.get("density") != "analytic" and any(b["document"] == "request" for b in self.bindings.values()):
            raise DG.CheckError("evaluator.source_density", "node 0 is reweighted only with an analytic source "
                                "(source-density/1); an external source is rejected (section 5.2)")
        self.nominal_theta = {p: float(DG.pointer_get(self.documents[b["document"]], b["pointer"]))
                              for p, b in self.bindings.items()}
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
        Geant4 events and Philox keys; resimulation-level theta read the batch told for that point."""
        if model != "nominal":
            raise DG.CheckError("evaluator.model", "enumerated models are separate g4sim specifications (phase 4)")
        if effects_off:
            raise DG.CheckError("evaluator.effects_off", "effects_off (section 10.5) is phase 4")
        values = {**self.nominal_theta, **(psi or {}), **(phi or {}), **(theta or {})}
        bname, batch = self._batch(seeds, values)
        return self._observe(values, bname, batch, names)

    def _observe(self, values: dict, bname: str, batch: dict, names=None, given=None) -> dict:
        tab = batch_tables(batch, self.scorers)
        events = np.arange(tab["first"], tab["first"] + tab["n"])
        changed = {p: v for p, v in values.items() if p in self.methods and not _same(v, self.nominal_theta[p])}
        flags = []
        w, missing, diag = self._weights(values, changed, tab, events)
        kb, kb0 = self._birks(values)
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
                    "flags": flags, "seeds": {"logical_run_seed": int(batch["logical_run_seed"]),
                                              "first_event": tab["first"], "events": tab["n"]}})
        return out

    def _weights(self, values, changed, tab, events):
        w = np.ones(len(events))
        src = [p for p in changed if self.methods[p] == "analytic-reweighting"]
        if not src:
            return w, [], {}
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
            w[i] = source_density.energy_density(p, E) / qe
        node = {"n_eff": reweight.kish(w), "pareto_k": reweight.pareto_k(w),
                "max_weight_fraction": float(w.max() / w.sum()) if w.sum() > 0 else None}
        return w, sorted(set(missing)), {"source": node}

    def _birks(self, values):
        kb_pars = [p for p, m in self.methods.items() if m == "rerun"]
        if not kb_pars:
            return None, None
        p = kb_pars[0]
        return float(values[p]), float(self.nominal_theta[p])

    def _visible(self, tab, events, kb):
        """edep_visible per (event, volume) from edep_by_dedx_class at k_B, with the section 5.4 discretization bound."""
        vis, bound = {}, {}
        for key, rows in tab["dedx"].items():
            vis[key] = simulate.reweighted(rows, kb)
            bound[key] = simulate.reweighting_bound(rows, kb)
        return vis, bound

    def _digitize(self, values, tab, batch, kb, kb0):
        docs = DG.apply_theta(self.documents, self.plan, {p: v for p, v in values.items()
                                                          if self.methods.get(p) == "re-digitization"})
        rows = tab["split"]
        if kb is not None and not _same(kb, kb0):
            scaled = []
            for e, v, b, L, S, k in rows:
                d = tab["dedx"].get((e, v))
                if d is None:
                    raise DG.CheckError("evaluator.birks", f"event {e}, volume {v}: no edep_by_dedx_class rows to carry "
                                        "a k_B change into the scintillation bins")
                r0 = simulate.reweighted(d, kb0)
                f = simulate.reweighted(d, kb) / r0 if r0 > 0 else 1.0
                scaled.append((e, v, b, L * f, S * f, k))
            rows = scaled
        snapshot = docs.get("conditions")
        job = DG.job_from_documents(docs["pipeline"], docs["maps"][self.spec["map"]], self.readout,
                                    sorted({r[2] for r in rows}) or [0], int(batch["logical_run_seed"]),
                                    conditions=snapshot, event_time=self.plan.get("event_time"),
                                    interval=(tab["first"], tab["n"]) if snapshot is not None else None)
        channel_rows, _ = digitize.digitize(job, rows)
        return channel_rows

    def _values(self, o, tab, events, vis, rows):
        q = o["quantity"]
        idx = {int(e): i for i, e in enumerate(events)}
        x = np.zeros(len(events))
        vols = set(o["volumes"]) if o.get("volumes") is not None else None
        if q == "primary_energy":
            return np.array([tab["primaries"].get(int(e), np.nan) for e in events])
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
        if node == "transport":
            name = self._told_batch({p: values[p] for p in self.methods if self.methods[p] in ("rerun", "resimulation")})
            if name is None:
                raise ResimulationRequired(f"node {node} at {theta} is a g4sim_run that has not been told (ask)")
            return {"batch": name}
        bname, batch = self._batch(seeds, values)
        tab = batch_tables(batch, self.scorers)
        kb, kb0 = self._birks(values)
        return {"batch": bname, "channel_rows": self._digitize(values, tab, batch, kb, kb0)}

    def evaluate_from(self, node: str, samples, theta: dict, phi: dict | None, psi: dict | None, model: str,
                      seeds: dict, names=None) -> dict:
        """The observables from a node's output (for P0): the batch of the samples, with the given channel rows."""
        values = {**self.nominal_theta, **(psi or {}), **(phi or {}), **(theta or {})}
        batch = self.batches[samples["batch"]]
        out = self._observe(values, samples["batch"], batch, names, given=samples.get("channel_rows"))
        out["independent_runs"] = [self.run] if samples["batch"] != self.nominal_batch else []
        return out

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
        for key in ("cells", "primaries"):
            if isinstance(b.get(key), str):
                b[key] = read_csv_rows(base / b[key])
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
