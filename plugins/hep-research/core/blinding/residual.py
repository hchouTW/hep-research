"""Residual-information checks for a prepared release (task P4.3, C02; protected-data-architecture.md §6.2 rule 6).

residual_checks(release, context) looks at a Release from core.blinding.transforms together with what the custodian
knows about its context, and reports each way it can see that the release still gives away a protected feature:

  binned-mask      mask.region_mismatch_with_other (another release of the source masks another region)
  event-removal    removal.totals_elsewhere (a cutflow or metadata total of the source is agent-visible),
                   removal.index_fields (a kept integer field is named like an identifier or a sequence),
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

import re

from core.blinding.transforms import LIMITS

ID_TOKENS = frozenset({"id", "event", "evt", "run", "lumi", "luminosity", "block", "index", "idx", "seq", "number",
                       "no", "num", "entry", "nr", "orbit", "bx", "bunch", "ls"})


def _id_like(name: str) -> bool:
    """A field name whose tokens (snake_case, camelCase, digits split off) name an identifier or a sequence."""
    tokens = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", name)
    return any(t.lower() in ID_TOKENS for t in tokens)


def _risk(code: str, message: str) -> dict:
    return {"code": code, "message": message}


MAX_COUNT = 10 ** 5  # largest smallest-count recognized in scaled counts (a fraction closer than float precision)


def _near_integer_multiples(values: list[float], tol: float = 1e-14) -> bool:
    """True when every nonzero value is (close to) an integer multiple of one unit: each ratio to the smallest
    magnitude is a fraction with a denominator up to MAX_COUNT, exact to float precision. Scaled counts n_i * a give
    ratios n_i / n_min exactly; generic real numbers do not."""
    from fractions import Fraction
    nz = sorted(abs(v) for v in values if v != 0)
    if len(nz) < 3:
        return False
    for v in nz:
        r = v / nz[0]
        f = Fraction(r).limit_denominator(MAX_COUNT)
        if abs(float(f) - r) > tol * max(1.0, r):
            return False
    return True


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
            if _id_like(f) and vals:
                risks.append(_risk("removal.index_fields", f"field {f!r} looks like an identifier or sequence number: "
                                                           "gaps and counts per value reveal where events were removed "
                                                           "(drop it)"))
    if mode == "common-offset":
        vals = [v for v in rel.get("values") or [] if isinstance(v, (int, float))]
        if ctx.get("nonnegative") or ctx.get("reference_points"):
            risks.append(_risk("offset.boundary", "a physical boundary or reference point bounds or fixes the offset"))
        fracs = [v % 1.0 for v in vals]
        same = len(vals) >= 3 and all(
            min(abs(f - fracs[0]), 1 - abs(f - fracs[0])) <= 8 * 2.2e-16 * max(1.0, abs(v)) + 1e-12
            for f, v in zip(fracs, vals))
        if same:
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
