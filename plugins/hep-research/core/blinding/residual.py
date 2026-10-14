"""Residual-information checks for a prepared release (task P4.3, C02; agentic-architecture.md §6.2 rule 6).

residual_checks(release, context) looks at a Release from core.blinding.transforms together with what the custodian
knows about its context, and reports each way it can see that the release still gives away a protected feature:

  binned-mask      mask.region_mismatch_with_other (another release of the source masks another region)
  event-removal    removal.totals_elsewhere (a cutflow or metadata total of the source is agent-visible),
                   removal.index_fields (a kept field looks like a sequential identifier with gaps),
                   removal.region_mismatch_with_other
  common-offset    offset.boundary (a declared physical boundary or reference point bounds or fixes the offset),
                   offset.integer_residue (the released values share one fractional part: they were integers),
                   offset.uncertainties (input uncertainties travel with the release),
                   offset.other_offset (another release of the source with another offset gives their difference)
  common-scale     scale.quantization (the released values are near-integer multiples of one number),
                   scale.companion (an unscaled companion of the same quantity travels with the release),
                   scale.unit_area (the values sum to one: the scale is not hidden, nor needed), scale.uncertainties

Findings carry a code and a message, never a recovered value or count (HC-08). The checks are advisory and partial:
what they cannot see (LIMITS in core.blinding.transforms, and anything outside the given context) stays a
composition-review question; an empty result is not a proof that nothing leaks.
"""
from __future__ import annotations

import math
import re

from core.blinding.transforms import LIMITS

ID_LIKE = re.compile(r"(^|_)(id|event|evt|run|lumi|block|index|idx|seq|number)($|_)", re.I)


def _risk(code: str, message: str) -> dict:
    return {"code": code, "message": message}


MAX_COUNT = 1000  # smallest count tried: scaled counts up to this are recognized


def _near_integer_multiples(values: list[float], tol: float = 1e-9) -> bool:
    """True when every nonzero value is (close to) an integer multiple of one unit, the smallest nonzero magnitude
    divided by an integer up to MAX_COUNT: the signature of scaled counts."""
    nz = sorted(abs(v) for v in values if v != 0)
    if len(nz) < 3:
        return False
    for k in range(1, MAX_COUNT + 1):
        unit = nz[0] / k
        if all(abs(v / unit - round(v / unit)) < 1e-6 + tol * (v / unit) for v in nz):
            return True
    return False


def residual_checks(release: dict, context: dict | None = None) -> list[dict]:
    """See the module docstring. context keys (all optional): nonnegative (bool), reference_points (list of known
    physical values), visible_totals (bool: a total of the source is agent-visible elsewhere), uncertainties_released
    (bool), companions (list of arrays released next to it), other_releases (list of Release dicts of the same source)."""
    ctx = dict(context or {})
    mode = release.get("mode")
    if mode not in LIMITS:
        raise ValueError(f"unknown mode {mode!r}")
    risks: list[dict] = []
    rel = release.get("released") or {}
    others = [o for o in ctx.get("other_releases") or [] if isinstance(o, dict)]
    if mode in ("binned-mask", "event-removal"):
        for o in others:
            if o.get("mode") == mode and o.get("parameters", {}).get("region") != release.get("parameters", {}).get("region"):
                code = "mask.region_mismatch_with_other" if mode == "binned-mask" else "removal.region_mismatch_with_other"
                risks.append(_risk(code, "another release of this source uses another region: their difference is revealed"))
    if mode == "event-removal":
        if ctx.get("visible_totals"):
            risks.append(_risk("removal.totals_elsewhere", "a total of the source is visible: subtraction gives the removed count"))
        events = rel.get("events") or []
        fields = {k for ev in events if isinstance(ev, dict) for k in ev}
        for f in sorted(fields):
            vals = [ev.get(f) for ev in events if isinstance(ev.get(f), int) and not isinstance(ev.get(f), bool)]
            if ID_LIKE.search(f) and len(vals) == len(events) and len(set(vals)) == len(vals) and vals:
                risks.append(_risk("removal.index_fields", f"field {f!r} looks like a sequential identifier: gaps reveal "
                                                           "where events were removed (drop it)"))
    if mode == "common-offset":
        vals = [v for v in rel.get("values") or [] if isinstance(v, (int, float))]
        if ctx.get("nonnegative") or ctx.get("reference_points"):
            risks.append(_risk("offset.boundary", "a physical boundary or reference point bounds or fixes the offset"))
        fr = {round(math.modf(v)[0] % 1.0, 9) for v in vals}
        if len(vals) >= 3 and len(fr) == 1:
            risks.append(_risk("offset.integer_residue", "the released values share one fractional part: the inputs were "
                                                         "integers and the offset's fractional part is revealed"))
        if ctx.get("uncertainties_released") or rel.get("uncertainties") not in (None, "withheld"):
            risks.append(_risk("offset.uncertainties", "uncertainties computed before the offset reveal absolute values"))
        for o in others:
            if o.get("mode") == "common-offset":
                risks.append(_risk("offset.other_offset", "another release of this source with its own offset: the two "
                                                          "offsets' difference is revealed"))
    if mode == "common-scale":
        vals = [v for v in rel.get("values") or [] if isinstance(v, (int, float))]
        if _near_integer_multiples(vals):
            risks.append(_risk("scale.quantization", "the values are integer multiples of one number: scaled counts "
                                                     "reveal the scale"))
        if vals and abs(sum(vals) - 1.0) < 1e-9:
            risks.append(_risk("scale.unit_area", "the values are a unit-area shape: no normalization is hidden"))
        if ctx.get("companions"):
            risks.append(_risk("scale.companion", "an unscaled companion travels with the release: the ratio reveals the scale"))
        if ctx.get("uncertainties_released") or rel.get("uncertainties") not in (None, "withheld"):
            risks.append(_risk("scale.uncertainties", "uncertainties computed before the scale reveal it (variance/mean)"))
    return risks
