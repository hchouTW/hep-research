"""The cell chain (plan R34; t07-t09-task-sheets.md, T08 interfaces): raw readout to calibrated cell energy e_c.

Chain order, fixed: (1) pedestal, subtracted; (2) gain, which multiplies, E = c (ADC - pedestal), or divides,
E = (ADC - pedestal) / g, as its payload states. Every value is kept side by side per cell: the raw value, the pedestal
applied, the value after the pedestal, the gain applied with its role, and e_c. Each step records the identity of the payload
it applied, in chain order, because the order is part of each constant's definition. The gain payload must have been derived
against the pedestal payload this chain applies (R32: a payload bound on top of another upstream chain is refused).

The readout's saturated flag passes through unchanged: it was set before the gain (t04-values-v4.md section 4.2), and no step
here sets or clears it. A dead cell has no value at any step (NaN), and is never in a cluster (section 7.1).
Both steps are linear and the gain step is multiplicative with no additive term, the case of plan R37's CAI-T08-1: no
cell-level step follows the gain (the readout clips before it; T_c and T_s are clustering's selections, not cell steps).
A calo-gain-payload/1 gain is refused against another channel map than the readout grid's (D2 stage 2).

Units (D2 stage 4, scenario A38: a repeated correction cannot pass): each step is applied only to the values it was made for.
The pedestal is in the readout's raw unit; a multiplying gain is in MeV per raw unit, a dividing gain in raw units per MeV. So an
already-calibrated readout (raw unit MeV) is never given an ADC pedestal and gain again, and a gain made for calibrated values is
never applied to ADC values. The identity readout of a labelled input (raw unit MeV, pedestal MeV, gain MeV/MeV) is consistent.
Units cannot show a correction whose unit matches the values it is applied to again: a second gain in MeV/MeV on a readout that
is already calibrated, or a second pedestal in adc on an ADC readout that is already pedestal-subtracted. Neither case is
detectable from these files.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy

from .cell_input import InputError, Payload
from .gain_payload import check_channel_map

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
    """The chain as the product records it: one entry per step, in chain order. A calo-gain-payload/1 gain also records its
    format, channel map and source (D2 stage 2); a stage 1 calo-calibration-payload/1 gain records exactly what it did before."""
    check_chain(pedestal, gain)
    gain_record = {"order": 2, "step": "gain", "operation": gain.operation, "role": GAIN_ROLE[gain.operation], "payload_id": gain.identity,
                   "origin": gain.origin, "round": gain.round, "derived_against": list(gain.derived_against)}
    if gain.channel_map is not None:
        gain_record.update({"format": gain.format, "channel_map": gain.channel_map, "derived_from": gain.derived_from})
    return [{"order": 1, "step": "pedestal", "operation": "subtract", "payload_id": pedestal.identity, "origin": pedestal.origin,
             "round": pedestal.round, "derived_against": list(pedestal.derived_against)},
            gain_record]


def gain_step(after_pedestal, gain, operation: str):
    """The gain step alone, E = c (ADC - pedestal) or (ADC - pedestal) / g. The chain and the fixed-membership re-evaluation
    (recalibration.py) both apply it, so they share one arithmetic. No cell-level step follows it in this chain."""
    return after_pedestal * gain if operation == "multiply" else after_pedestal / gain


def gain_unit(operation: str, raw_unit: str) -> str:
    return f"MeV/{raw_unit}" if operation == "multiply" else f"{raw_unit}/MeV"


def check_units(raw_unit: str, pedestal: Payload, gain: Payload) -> None:
    """Refuses payloads whose units are not those of the readout's raw values (see the module text)."""
    if pedestal.document.get("unit") != raw_unit:
        raise InputError(f"pedestal payload: unit {pedestal.document.get('unit')!r} is not the readout's raw unit {raw_unit!r}; a "
                         "correction is applied only to the values it was made for, so a calibrated readout is never calibrated again")
    expected = gain_unit(gain.operation, raw_unit)
    if gain.document.get("unit") != expected:
        raise InputError(f"gain payload: unit {gain.document.get('unit')!r} is not {expected!r}, the {gain.operation} role's unit for "
                         f"a readout in {raw_unit!r}; a correction is applied only to the values it was made for")


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
    check_channel_map(gain, shape[0], shape[1], "gain payload")
    ped = pedestal.values.reshape(shape)
    g = gain.values.reshape(shape)
    with numpy.errstate(invalid="ignore"):
        after = numpy.where(live, raw - ped, numpy.nan)
        energy = numpy.where(live, gain_step(after, g, gain.operation), numpy.nan)
    return CellChain(raw=numpy.where(live, raw, numpy.nan), pedestal=ped, after_pedestal=after, gain=g, energy=energy,
                     live=live.copy(), saturated=saturated & live)
