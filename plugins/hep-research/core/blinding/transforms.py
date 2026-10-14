"""Input-blinding transforms (task P4.1, C02, T1.1, T1.6; DP-3 modes; agentic-architecture.md §6.2).

Each transform takes the custodian's unblinded input and returns a Release dict:
  mode       binned-mask | event-removal | common-offset | common-scale
  released   what goes into the release directory (no key material: offsets and scales are inputs, never outputs)
  sealed     numbers a scan of agent-visible output must not find (core.blinding.scan_*), custodian-side only
  protected  the features the mode conceals; retained: the information it keeps on purpose (manifest fields)
  parameters non-secret description for transform.parameters of the release manifest (no key-like names)
Statistical outputs follow the transform (rule 7): binned-mask masks errors with the values; common-offset and
common-scale withhold input uncertainties (they were computed before the transform and give it away: Poisson errors
reveal the counts); event-removal releases no totals, no removed count and no input order or identifiers.

What a mode does not protect is listed in LIMITS[mode] and probed by core.blinding.residual; a release is acceptable
only after that review (rule 6: the agent can run any code on what it receives). Run by the custodian; run by an agent
on synthetic data the functions are an exercise. Refused inputs raise ValueError.
"""
from __future__ import annotations

import math
import numbers
from typing import Any

from core.blinding.blinding import blinded_mask, mask_binned, seal
from core.protected.guard import guard

MODES = ("binned-mask", "event-removal", "common-offset", "common-scale")

LIMITS = {
    "binned-mask": ("sums over unblinded bins and the sideband total are public by definition; a smooth sideband "
                    "extrapolation into the blinded region can be the protected quantity itself; masks of different "
                    "regions in two releases of the same source reveal the bins in their difference",),
    "event-removal": ("original totals in cutflows, metadata, figures or caches outside this release reveal the "
                      "removed count by subtraction; event or run identifiers kept elsewhere reveal index gaps; a "
                      "second release with another region reveals the events in the difference",),
    "common-offset": ("a physical boundary or reference point (non-negative quantities, resonance or calibration "
                      "peaks, kinematic endpoints) bounds or fixes the offset; for counts, Poisson structure "
                      "(variance about mean - c) and integer residues expose it; uncertainties computed before the "
                      "offset expose the absolute values; two releases with different offsets reveal their difference",),
    "common-scale": ("unit-area shapes and densities are scale-free; for counts, integer quantization (multiples of the "
                     "scale) and variance/mean about the scale expose it; per-event weights reveal it directly; "
                     "unscaled predictions, simulation or control regions in the same release reveal it by ratio",),
}


def _finite(values, what: str) -> list[float]:
    out = []
    for i, v in enumerate(values):
        if isinstance(v, bool) or not isinstance(v, numbers.Real) or not math.isfinite(v):
            raise ValueError(f"{what}[{i}] is not a finite number")
        out.append(float(v))
    return out


def _release(mode: str, released: dict, sealed, protected, retained, parameters: dict) -> dict:
    return {"mode": mode, "released": released, "sealed": sorted({float(x) for x in sealed if x != 0}),
            "protected": list(protected), "retained": list(retained), "parameters": dict(parameters, mode=mode),
            "limits": list(LIMITS[mode])}


def binned_mask(edges, values, region: dict, errors=None, flow: bool = False, references=()) -> dict:
    """Mask the blinded bins (core.blinding.mask_binned) and seal what would reveal them (core.blinding.seal)."""
    guard("core.blinding.transforms.binned_mask")
    released = mask_binned(edges, values, region, errors=errors, flow=flow)
    sealed = seal(edges, values, region, references=references, flow=flow)
    return _release("binned-mask", released, sealed, ["blinded-region content"],
                    ["bins outside the blinded region", "bin edges"],
                    {"variable": region.get("variable"), "region": {"low": region.get("low"), "high": region.get("high")}})


def event_removal(events, variable: str, region: dict, drop_fields=()) -> dict:
    """Remove every event whose `variable` lies in [low, high). The released events keep only the fields not in
    drop_fields (identifiers, run or block numbers), are sorted by `variable` (input order can carry the removed
    positions), and carry no total. Sealed: the removed count, the input total, the removed events' values."""
    guard("core.blinding.transforms.event_removal")
    bounds = region.get("low"), region.get("high")
    if not all(isinstance(b, numbers.Real) and not isinstance(b, bool) for b in bounds):
        raise ValueError("region needs low < high")
    lo, hi = float(bounds[0]), float(bounds[1])  # type: ignore[arg-type]
    if not lo < hi:
        raise ValueError("region needs low < high")
    kept: list[dict] = []
    removed: list[dict] = []
    for i, ev in enumerate(events):
        if not isinstance(ev, dict) or variable not in ev:
            raise ValueError(f"event {i} has no {variable!r}")
        x = _finite([ev[variable]], variable)[0]
        (removed if lo <= x < hi else kept).append(ev)
    drop = set(drop_fields)
    released = sorted(({k: v for k, v in ev.items() if k not in drop} for ev in kept), key=lambda e: e[variable])
    sealed: list[float] = [float(len(removed)), float(len(events))] + [float(ev[variable]) for ev in removed]
    return _release("event-removal", {"variable": variable, "events": released}, sealed,
                    ["events in the blinded region", "the number of removed events"],
                    ["every event outside the blinded region (without the dropped fields)"],
                    {"variable": variable, "region": {"low": lo, "high": hi}, "dropped_fields": sorted(drop)})


def common_offset(values, shift, kind: str = "continuous") -> dict:
    """Release x + c for a secret c (`shift`, an input). Counts are refused: their Poisson structure and integer
    residues reveal c (LIMITS); use binned-mask or event-removal for counts. Input uncertainties are withheld."""
    guard("core.blinding.transforms.common_offset")
    if kind != "continuous":
        raise ValueError("common-offset is refused for counts: variance about mean - c and integer residues reveal the offset")
    c = _finite([shift], "shift")[0]
    if c == 0:
        raise ValueError("a zero offset hides nothing")
    xs = _finite(values, "values")
    released = [x + c for x in xs]
    return _release("common-offset", {"values": released, "uncertainties": "withheld"}, xs + [c, -c],
                    ["absolute location"], ["differences between values"], {"kind": kind})


def common_scale(values, factor, weights=None) -> dict:
    """Release a * x for a secret a (`factor`, an input; a > 0 and not 1). Per-event weights are refused (they reveal
    a directly). Input uncertainties are withheld."""
    guard("core.blinding.transforms.common_scale")
    if weights is not None:
        raise ValueError("common-scale with per-event weights is refused: the weights reveal the scale")
    a = _finite([factor], "factor")[0]
    if a <= 0 or a == 1:
        raise ValueError("the scale must be positive and not 1")
    xs = _finite(values, "values")
    released = [a * x for x in xs]
    return _release("common-scale", {"values": released, "uncertainties": "withheld"}, xs + [a, 1 / a],
                    ["normalization"], ["ratios between values", "shape"], {})


def apply(mode: str, **kw: Any) -> dict:
    """Dispatch by mode name (the custodian's preparation step)."""
    fns: dict[str, Any] = {"binned-mask": binned_mask, "event-removal": event_removal, "common-offset": common_offset,
                           "common-scale": common_scale}
    fn = fns.get(mode)
    if fn is None:
        raise ValueError(f"unknown blinding mode {mode!r}; one of {list(MODES)}")
    return fn(**kw)


__all__ = ["LIMITS", "MODES", "apply", "binned_mask", "blinded_mask", "common_offset", "common_scale", "event_removal"]
