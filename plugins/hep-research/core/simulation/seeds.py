"""Seed hash H of simulation runs (the C++ twin is SimHash.hh of the Geant4 adapter's g4sim headers; both must agree).

H(x1, ..., xn) = int.from_bytes(sha256("\\x1f".join(str(x) for x in (x1, ..., xn)).encode("utf-8"))[:8], "big")
                 % (2**31 - 1) + 1, a value in [1, 2**31 - 1] (what a Geant4 engine accepts as a seed); integers are
written as decimal strings without leading zeros. Each evidence point of a study is one logical run with seed
S = H(study_id, role, point_id); the job starting at event e has the seed pair (H(S, e, 0), H(S, e, 1)), and under
per-event seeding event i has (H(S, i, 0), H(S, i, 1)).

Relation to core.stats.toy_ensemble.toy_seed: both are SHA-256 derived and independent of how the work is split, but
toy_seed is a 63-bit seed of one statistical toy, while H is limited to [1, 2**31 - 1] for the Geant4 engines and
hashes its arguments joined by the unit separator."""
from __future__ import annotations

import hashlib

from core import trace

MODULUS = 2 ** 31 - 1
SEP = "\x1f"


def H(*parts) -> int:
    """The seed hash; parts are joined by the unit separator after str() (integers in decimal, no leading zeros)."""
    trace.tag("geant4-seed-hash")
    if not parts:
        raise ValueError("H needs at least one part")
    for p in parts:
        if isinstance(p, bool) or not isinstance(p, (int, str)):
            raise ValueError(f"H parts are integers or strings, not {type(p).__name__}")
    digest = hashlib.sha256(SEP.join(str(p) for p in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % MODULUS + 1


def logical_run_seed(study_id: str, role: str, point_id: str) -> int:
    """S of one evidence point (one logical run)."""
    return H(study_id, role, point_id)


def job_seeds(s: int, first_event: int) -> tuple[int, int]:
    """The seed pair of the job of logical run s that starts at event first_event (also the event seeds of
    per-event seeding, with first_event the event number)."""
    return H(s, first_event, 0), H(s, first_event, 1)
