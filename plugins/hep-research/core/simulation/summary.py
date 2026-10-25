"""Run summaries of simulation runs (format simulation-summary/1; schema contracts/schemas/simulation_summary.json,
validated by the callers through contracts.schema, since core imports only core).

A summary holds, per block of a logical run (event i, counted from the run's first event, belongs to block
floor(i / B); events with i >= K B are ignored and counted) and per declared observable (simulation-observables/1:
name, source_column, selection, bins {lo, hi, width}, thresholds), the accumulators: integers n (selected events),
per-bin histogram counts with separate underflow and overflow, count_if[] (x > threshold, strictly greater), and
floating sum, sum of squares (Neumaier-compensated), min and max; also the number of events per block. Summaries of
several jobs of one logical run merge by block number with the rule of each accumulator (MERGE). From Geant4 program
C2.1 an observable may declare values: true (optional values_max, default VALUES_MAX): each block then also keeps
its raw selected values in event order, so quantiles can be empirical (core.stats.batch_means.empirical_quantile);
when any block holds more than values_max values the observable keeps none and says so (values_omitted), and merged
blocks concatenate their values (merge rule concat; the caller passes the jobs in event order). Standard library
only."""
from __future__ import annotations

import json
import math
from pathlib import Path

SUMMARY_VERSION = "simulation-summary/1"
OBSERVABLES_VERSION = "simulation-observables/1"
VALUES_MAX = 10_000
QUANTILE_METHOD = "hyndman-fan-7"
MERGE = {"events": "sum", "n": "sum", "hist": "hist", "underflow": "sum", "overflow": "sum", "count_if": "sum",
         "sum": "sum", "sumsq": "sum", "min": "min", "max": "max"}
OPS = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b, "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
       ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
       "contains": lambda a, b: str(b) in str(a), "!contains": lambda a, b: str(b) not in str(a)}


class SummaryError(ValueError):
    """Unusable summary input."""


class Neumaier:
    """Compensated running sum (Neumaier's variant of Kahan summation)."""

    __slots__ = ("s", "c")

    def __init__(self, s: float = 0.0, c: float = 0.0):
        self.s, self.c = s, c

    def add(self, x: float) -> None:
        t = self.s + x
        self.c += (self.s - t) + x if abs(self.s) >= abs(x) else (x - t) + self.s
        self.s = t

    @property
    def value(self) -> float:
        return self.s + self.c


def selected(row: dict, selection) -> bool:
    """A declarative filter: every condition {column, op, value} holds (AND); an empty selection keeps every event."""
    for cond in selection or []:
        v = row.get(cond["column"])
        if v is None:
            return False
        try:
            if not OPS[cond["op"]](v, cond["value"]):
                return False
        except TypeError:
            return False
    return True


def _nbins(bins: dict) -> int:
    n = (bins["hi"] - bins["lo"]) / bins["width"]
    k = int(round(n))
    if k < 1 or abs(n - k) > 1e-9 * max(1.0, n):
        raise SummaryError(f"bins {bins}: (hi - lo) / width must be a positive integer")
    return k


def _empty_block(index: int, obs: dict) -> dict:
    return {"block": index, "events": 0, "n": 0, "hist": [0] * _nbins(obs["bins"]), "underflow": 0, "overflow": 0,
            "count_if": [0] * len(obs.get("thresholds") or []), "sum": 0.0, "sumsq": 0.0, "min": None, "max": None}


def build(rows, observables: list[dict], block_size: int, blocks: int, first_event: int = 0, run: dict | None = None,
          producer: dict | None = None) -> dict:
    """A simulation-summary/1 from per-event rows (dicts with an 'event' column) of one logical run."""
    if not (isinstance(block_size, int) and block_size >= 1 and isinstance(blocks, int) and blocks >= 1):
        raise SummaryError("block size B and block count K must be positive integers")
    acc = {o["name"]: [_empty_block(b, o) for b in range(blocks)] for o in observables}
    vals: dict[str, list[list[tuple[int, float]]]] = {o["name"]: [[] for _ in range(blocks)] for o in observables
                                                      if o.get("values")}
    sums = {o["name"]: [[Neumaier(), Neumaier()] for _ in range(blocks)] for o in observables}
    events, ignored = [0] * blocks, 0
    for row in rows:
        i = int(row["event"]) - first_event
        if i < 0:
            raise SummaryError(f"event {row['event']} is before the logical run's first event {first_event}")
        b = i // block_size
        if b >= blocks:
            ignored += 1
            continue
        events[b] += 1
        for o in observables:
            if not selected(row, o.get("selection")):
                continue
            x = row.get(o["source_column"])
            if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x):
                raise SummaryError(f"event {row['event']}: column {o['source_column']!r} is not a finite number")
            blk, (s, s2) = acc[o["name"]][b], sums[o["name"]][b]
            blk["n"] += 1
            if o["name"] in vals:
                vals[o["name"]][b].append((int(row["event"]), x))
            s.add(x)
            s2.add(x * x)
            blk["min"] = x if blk["min"] is None else min(blk["min"], x)
            blk["max"] = x if blk["max"] is None else max(blk["max"], x)
            bins = o["bins"]
            j = math.floor((x - bins["lo"]) / bins["width"])
            if j < 0:
                blk["underflow"] += 1
            elif j >= len(blk["hist"]):
                blk["overflow"] += 1
            else:
                blk["hist"][j] += 1
            for t, thr in enumerate(o.get("thresholds") or []):
                blk["count_if"][t] += x > thr
    out_obs = []
    for o in observables:
        for b, blk in enumerate(acc[o["name"]]):
            blk["events"] = events[b]
            blk["sum"], blk["sumsq"] = sums[o["name"]][b][0].value, sums[o["name"]][b][1].value
        out = {"name": o["name"], "source_column": o["source_column"], "selection": o.get("selection") or [],
               "bins": o["bins"], "thresholds": o.get("thresholds") or [], "blocks": acc[o["name"]]}
        if o["name"] in vals:
            _set_values(out, [[x for _, x in sorted(v, key=lambda e: e[0])] for v in vals[o["name"]]],
                        int(o.get("values_max", VALUES_MAX)))
        out_obs.append(out)
    merge_rules = dict(MERGE, **({"values": "concat"} if vals else {}))
    return {"summary_version": SUMMARY_VERSION,
            "run": {**(run or {}), "first_event": first_event, "block_size": block_size, "blocks": blocks,
                    "events_in_blocks": sum(events), "events_ignored": ignored,
                    "producer": producer or {"name": "python-csv"}},
            "observables": out_obs, "merge": merge_rules}


def _set_values(obs: dict, per_block: list[list[float]], values_max: int) -> None:
    """Write each block's values, or none of them (values_omitted) when a block holds more than values_max."""
    obs["values_max"] = values_max
    biggest = max(len(v) for v in per_block)
    if biggest > values_max:
        obs["values_omitted"] = f"a block holds {biggest} values, more than values_max {values_max}"
        obs.pop("quantile_method", None)
        for blk in obs["blocks"]:
            blk.pop("values", None)
        return
    obs.pop("values_omitted", None)
    obs["quantile_method"] = QUANTILE_METHOD
    for blk, v in zip(obs["blocks"], per_block):
        blk["values"] = v


def _merge_block(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, rule in MERGE.items():
        if rule == "sum":
            out[k] = a[k] + b[k] if not isinstance(a[k], list) else [x + y for x, y in zip(a[k], b[k])]
        elif rule == "hist":
            if len(a[k]) != len(b[k]):
                raise SummaryError("histograms with different binnings do not merge")
            out[k] = [x + y for x, y in zip(a[k], b[k])]
        else:
            vals = [v for v in (a[k], b[k]) if v is not None]
            out[k] = (min if rule == "min" else max)(vals) if vals else None
    return out


def merge(summaries: list[dict]) -> dict:
    """Merge the summaries of several jobs of one logical run, block by block (same observables and binning)."""
    if not summaries:
        raise SummaryError("nothing to merge")
    first = summaries[0]
    names = [o["name"] for o in first["observables"]]
    out = json.loads(json.dumps(first))
    for s in summaries[1:]:
        if [o["name"] for o in s["observables"]] != names or s["run"]["block_size"] != first["run"]["block_size"]:
            raise SummaryError("summaries of different observables or block sizes do not merge")
        for o_out, o in zip(out["observables"], s["observables"]):
            if o_out["bins"] != o["bins"] or o_out["thresholds"] != o["thresholds"]:
                raise SummaryError(f"{o['name']}: different binning or thresholds do not merge")
            keep = "values_max" in o_out and "values_omitted" not in o_out and "values_omitted" not in o
            for blk in o["blocks"]:
                i = blk["block"]
                merged = _merge_block(o_out["blocks"][i], blk)
                if keep:
                    merged["values"] = list(o_out["blocks"][i].get("values", [])) + list(blk.get("values", []))
                o_out["blocks"][i] = merged
            if "values_max" in o_out:
                if keep:
                    _set_values(o_out, [b["values"] for b in o_out["blocks"]], o_out["values_max"])
                else:
                    _set_values(o_out, [[0.0] * (o_out["values_max"] + 1)], o_out["values_max"])
        out["run"]["events_in_blocks"] += s["run"]["events_in_blocks"]
        out["run"]["events_ignored"] += s["run"]["events_ignored"]
    return out


def load(path) -> dict:
    """Read a summary file (no schema validation: the caller validates with contracts.schema)."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("summary_version") != SUMMARY_VERSION:
        raise SummaryError(f"{path}: not a {SUMMARY_VERSION}")
    return doc


def observable(summary: dict, name: str) -> dict:
    for o in summary["observables"]:
        if o["name"] == name:
            return o
    raise SummaryError(f"the summary has no observable {name!r}")


def merged_accumulators(obs: dict) -> dict:
    """The accumulators of all blocks of one observable merged."""
    out = obs["blocks"][0]
    for blk in obs["blocks"][1:]:
        out = _merge_block(out, blk)
    return out


def block_means(obs: dict) -> list[float]:
    """Per-block means sum / n (a block without selected events has no mean: SummaryError)."""
    if any(b["n"] == 0 for b in obs["blocks"]):
        raise SummaryError(f"{obs['name']}: a block has no selected event, so it has no mean")
    return [b["sum"] / b["n"] for b in obs["blocks"]]


def block_values(obs: dict) -> list[list[float]]:
    """The raw selected values of every block (SummaryError when the observable keeps none)."""
    if "values_max" not in obs or obs.get("values_omitted"):
        raise SummaryError(f"{obs['name']}: no per-block values ({obs.get('values_omitted') or 'not declared'})")
    return [b["values"] for b in obs["blocks"]]


def block_proportions(obs: dict, threshold_index: int = 0) -> list[float]:
    """Per-block fractions count_if[t] / n."""
    if any(b["n"] == 0 for b in obs["blocks"]):
        raise SummaryError(f"{obs['name']}: a block has no selected event, so it has no proportion")
    return [b["count_if"][threshold_index] / b["n"] for b in obs["blocks"]]
