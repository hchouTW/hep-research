"""The surrogate-model interface stub of P6 (Part B sections 6.4, 7.1, 8.2 note 4; calib_emulator.py). Phase 1
delivers only the interface; the surrogate model, ask/tell, the training set (D80), P6 itself, V_emu and the surrogate
domain are phase 3. Every call answers `incomplete` (exit 3), never a pass."""
from __future__ import annotations

from typing import Protocol

PHASE = 3


class Surrogate(Protocol):
    """What a surrogate model gives the engine (section 6.4): the interpolated observables and their V_MC, V_emu
    separately; queries outside the domain are always rejected."""

    def predict(self, theta: dict) -> dict: ...          # {pred, V_MC, V_emu}

    def domain(self) -> dict: ...                         # the surrogate domain (calib_emulator.py)


def incomplete(what: str) -> dict:
    return {"status": "incomplete", "reason": f"{what} is delivered in phase {PHASE} (section 17); phase 1 has the "
            "interface only"}


def training_set(*_args, **_kwargs) -> dict:
    return incomplete("the surrogate's training set (D80)")


def p6(*_args, **_kwargs) -> dict:
    return dict(incomplete("P6"), gate="P6")


def ask(*_args, **_kwargs) -> dict:
    return incomplete("ask/tell")


def tell(*_args, **_kwargs) -> dict:
    return incomplete("ask/tell")
