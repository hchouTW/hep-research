"""The cell chain (plan R34; t07-t09-task-sheets.md, T08 interfaces): raw readout to calibrated cell energy e_c.

Chain order, fixed: (1) pedestal, subtracted; (2) gain, which multiplies, E = c (ADC - pedestal), or divides,
E = (ADC - pedestal) / g, as its payload states. Every value is kept side by side per cell: the raw value, the pedestal
applied, the value after the pedestal, the gain applied with its role, and e_c. Each step records the identity of the payload
it applied, in chain order, because the order is part of each constant's definition. The gain payload must have been derived
against the pedestal payload this chain applies (R32: a payload bound on top of another upstream chain is refused).

The readout's saturated flag passes through unchanged: it was set before the gain (t04-values-v4.md section 4.2), and no step
here sets or clears it. A dead cell has no value at any step (NaN), and is never in a cluster (section 7.1).
Both steps are linear and the gain step is multiplicative with no additive term, the case of plan R37's CAI-T08-1.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy

from .cell_input import InputError, Payload

CHAIN_ORDER = ("pedestal", "gain")
GAIN_ROLE = {"multiply": "multiplies: E = c (ADC - pedestal)", "divide": "divides: E = (ADC - pedestal) / g"}


@dataclass(frozen=True)
class CellChain:
    raw: numpy.ndarray             # (nx, ny), NaN at dead cells
    pedestal: numpy.ndarray        # applied per cell
    after_pedestal: numpy.ndarray
    gain: numpy.ndarray            # applied per cell
    energy: numpy.ndarray          # e_c, MeV; NaN at dead cells
    live: numpy.ndarray
    saturated: numpy.ndarray


def chain_record(pedestal: Payload, gain: Payload) -> list:
    """The chain as the product records it: one entry per step, in chain order."""
    check_chain(pedestal, gain)
    return [{"order": 1, "step": "pedestal", "operation": "subtract", "payload_id": pedestal.identity, "origin": pedestal.origin,
             "round": pedestal.round, "derived_against": list(pedestal.derived_against)},
            {"order": 2, "step": "gain", "operation": gain.operation, "role": GAIN_ROLE[gain.operation], "payload_id": gain.identity,
             "origin": gain.origin, "round": gain.round, "derived_against": list(gain.derived_against)}]


def check_chain(pedestal: Payload, gain: Payload) -> None:
    if pedestal.step != "pedestal" or gain.step != "gain":
        raise InputError(f"chain order is {CHAIN_ORDER}: got {pedestal.step} then {gain.step}")
    if pedestal.derived_against:
        raise InputError("pedestal payload: it is the first step, so it is derived against no upstream payload")
    if gain.derived_against != (pedestal.identity,):
        raise InputError("gain payload: derived against another upstream chain than the pedestal applied here; refused, never applied")
    if pedestal.values.shape != gain.values.shape:
        raise InputError("pedestal and gain payloads cover different channel counts")


def apply(raw: numpy.ndarray, live: numpy.ndarray, saturated: numpy.ndarray, pedestal: Payload, gain: Payload) -> CellChain:
    """One event's chain. raw, live, saturated: (nx, ny)."""
    check_chain(pedestal, gain)
    shape = raw.shape
    if pedestal.values.size != raw.size:
        raise InputError(f"payloads cover {pedestal.values.size} channels, the readout has {raw.size}")
    ped = pedestal.values.reshape(shape)
    g = gain.values.reshape(shape)
    with numpy.errstate(invalid="ignore"):
        after = numpy.where(live, raw - ped, numpy.nan)
        energy = numpy.where(live, after * g if gain.operation == "multiply" else after / g, numpy.nan)
    return CellChain(raw=numpy.where(live, raw, numpy.nan), pedestal=ped, after_pedestal=after, gain=g, energy=energy,
                     live=live.copy(), saturated=saturated & live)
