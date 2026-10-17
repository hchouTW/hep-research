"""Validated-range caps, their uniform override, and runtime notices for long toy runs (S7). Standard library only.

Each core/stats module refuses inputs beyond its own caps (the caps table of the core/stats guide). Some caps mark
where a method or its runtime was validated, not where it stops working; those are overridable with the uniform
command-line option --allow-outside-validated-range. A run that uses the override goes ahead, records every cap it
exceeded, and its output carries the label `outside-validated-range` (a core artifact status), which the publication
gate refuses without a validation record (contracts/validate.py publication_gate). Caps that protect numerical
accuracy (the Poisson mean cap) or that partitioning handles (toy counts) are not overridable.

Usage in a module:
    from core.stats import _caps
    if len(bins) > 50:
        _caps.exceed("multibin-limit bins", len(bins), 50, LikelihoodError, "bins must be a list of 1 to 50 bins")
    ...
    _caps.add_argument(subparser)                    # the option on every subcommand
    _caps.allow_outside(args.allow_outside_validated_range)
    out.update(_caps.report())                       # {} when nothing was exceeded
    for _ in _caps.timed_range(toys, "shape-limit toys"):   # prints an estimated runtime to stderr when long

In library use the override is a context manager: `with _caps.outside_validated_range(): ...`; it resets afterwards.
"""
from __future__ import annotations

import contextlib
import sys
import time
from collections.abc import Iterator

OPTION = "--allow-outside-validated-range"
LABEL = "outside-validated-range"
NOTICE_S = 10.0  # a toy loop whose estimated runtime exceeds this prints the estimate first (stderr)
_PROBE_S = 0.5   # the estimate is made after this much time or 20 iterations, whichever comes first

_state: dict = {"allow": False, "exceeded": []}


def allow_outside(flag: bool) -> None:
    """Set the override for this process (the command-line option) and clear the record of exceeded caps."""
    _state["allow"] = bool(flag)
    _state["exceeded"] = []


@contextlib.contextmanager
def outside_validated_range() -> Iterator[None]:
    old = dict(_state, exceeded=list(_state["exceeded"]))
    allow_outside(True)
    try:
        yield
    finally:
        _state.update(old)


def exceed(name: str, value, cap, error: type[Exception], message: str) -> None:
    """Called where `value` is above `cap`: raise `error` unless the override is on, else record it."""
    if not _state["allow"]:
        raise error(f"{message}; beyond this validated range only with {OPTION} (outputs labeled {LABEL})")
    entry = {"cap": name, "value": value, "limit": cap}
    if entry not in _state["exceeded"]:
        _state["exceeded"].append(entry)


def report() -> dict:
    """The output fields of a run that exceeded a cap under the override; {} otherwise."""
    if not _state["exceeded"]:
        return {}
    return {"range_label": LABEL, "outside_validated_range": list(_state["exceeded"]),
            "outside_validated_range_note": "results beyond a validated range: label outside-validated-range; the "
                                            "publication gate refuses it without a validation record"}


def add_argument(parser) -> None:
    parser.add_argument(OPTION, dest="allow_outside_validated_range", action="store_true",
                        help="run beyond the validated-range caps marked overridable in the core/stats guide; the "
                             f"output is labeled {LABEL} and lists every cap exceeded")


def timed_range(n: int, what: str, *, clock=time.perf_counter, stream=None, threshold_s: float = NOTICE_S):
    """range(n) that, after a short probe, prints the estimated total runtime to stderr when it exceeds threshold_s.
    The estimate does not touch any random state, so results do not change."""
    stream = sys.stderr if stream is None else stream
    start = clock()
    told = False
    for i in range(n):
        if not told and i > 0 and (i >= 20 or clock() - start >= _PROBE_S):
            told = True
            est = (clock() - start) / i * n
            if est > threshold_s:
                print(f"{what}: estimated runtime {est:.0f} s for {n} iterations", file=stream, flush=True)
        yield i
