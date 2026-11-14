"""The recipe's method card (timing-method-card/2; plan section 9.6 and A37; t10-timing-stage-plan.md sections 6.1 and 6.4).

For each unconstrained mode: its name, a witness, the named external information that constrains it, the independent observables
that can confirm it, and the constraints used in the derivation, which are never offered as independent observables (section 9.6:
"a mass/scale constraint already used for derivation cannot masquerade as independent validation"; CAI-T06-3 carries the contract
part). Stage 2 fix round 1 (I3): every constraining item and every observable has an identifier (constraint.* and observable.*)
and a text; per mode the two identifier sets are disjoint, so an item that constrains a mode is never offered as its validation, and
constraints_used names that mode's constraint identifiers only. check() refuses a card that leaves a mode without a named
constraint, an independent observable or a witness, or that breaks those rules.
"""
from __future__ import annotations

import json
from pathlib import Path

from .timing_payload import InputError

FORMAT = "timing-method-card/2"
CARD = Path(__file__).resolve().parents[1] / "timing-method-card.json"
MODE_KEYS = {"mode", "description", "witness", "constraining_information", "independent_observables", "constraints_used",
             "identifiable_combinations"}


def load(path: Path = CARD) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"method card: cannot read {path}: {exc}") from None


def _names(value) -> bool:
    return isinstance(value, list) and all(isinstance(v, str) and v for v in value)


def _items(value) -> bool:
    """A list of {id, text}. The card's convention is constraint.* and observable.* identifiers; the check does not rely on it, so
    the same identifier in both lists is caught by the disjointness rule itself."""
    return isinstance(value, list) and all(isinstance(v, dict) and set(v) == {"id", "text"} and isinstance(v["id"], str) and v["id"]
                                           and isinstance(v["text"], str) and v["text"] for v in value)


def check(card: dict) -> None:
    """Refuses an incomplete card (raises InputError, never another exception)."""
    if not isinstance(card, dict) or card.get("format") != FORMAT or not isinstance(card.get("unconstrained_modes"), list) \
            or not card["unconstrained_modes"]:
        raise InputError(f"method card: not a {FORMAT} card with its unconstrained modes")
    seen = set()
    for mode in card["unconstrained_modes"]:
        if not isinstance(mode, dict) or set(mode) != MODE_KEYS:
            raise InputError(f"method card: each mode is {{{', '.join(sorted(MODE_KEYS))}}}")
        name = mode["mode"]
        if not isinstance(name, str) or not name or name in seen:
            raise InputError("method card: each mode has a distinct name")
        seen.add(name)
        if not isinstance(mode["witness"], str) or not mode["witness"]:
            raise InputError(f"method card: {name} names no witness")
        for key in ("constraining_information", "independent_observables"):
            if not _items(mode[key]):
                raise InputError(f"method card: {name}: {key} is a list of {{id, text}}")
        for key in ("constraints_used", "identifiable_combinations"):
            if not _names(mode[key]):
                raise InputError(f"method card: {name}: {key} is a list of names")
        if not mode["constraining_information"]:
            raise InputError(f"method card: {name} names no external information that constrains it (section 9.6, A37)")
        if not mode["independent_observables"]:
            raise InputError(f"method card: {name} names no independent observable that can confirm it (section 9.6)")
        constraint_ids = [item["id"] for item in mode["constraining_information"]]
        observable_ids = [item["id"] for item in mode["independent_observables"]]
        if len(set(constraint_ids)) != len(constraint_ids) or len(set(observable_ids)) != len(observable_ids):
            raise InputError(f"method card: {name}: an item identifier is listed twice")
        overlap = sorted(set(constraint_ids) & set(observable_ids))
        if overlap:
            raise InputError(f"method card: {name}: {overlap} constrain the mode and cannot also be its independent validation (section 9.6)")
        reused = sorted(set(mode["constraints_used"]) & set(observable_ids))
        if reused:
            raise InputError(f"method card: {name}: {reused} were used in the derivation and cannot be its independent validation")
        unknown = sorted(set(mode["constraints_used"]) - set(constraint_ids))
        if unknown:
            raise InputError(f"method card: {name}: constraints_used names {unknown}, which are not this mode's constraints")
