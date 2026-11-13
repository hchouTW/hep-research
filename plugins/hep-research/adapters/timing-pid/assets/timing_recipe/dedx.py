"""dE/dx with every sample kept before truncation and normalization (plan R35; t10-timing-stage-plan.md section 6.1).

Per sample: identifier, layer, deposit [MeV], path length [cm], saturation flag, and dE/dx = deposit / path. Truncation, a fixture
rule after particle-identification.md ("discard the highest-loss fraction of samples ... and average the rest"): sort ascending by
dE/dx (ties by sample identifier), drop the highest floor(f n), keep the rest (at least one), and average the kept values. The
normalization divides by a stated reference value with its source. Flags: few-samples when n < FEW_SAMPLES; saturated-in-kept when a
kept sample is saturated (its deposit is a lower bound, so the mean is biased low). The record (timing-dedx/1) keeps every sample,
the kept and dropped sets, f, n, the mean, the normalized value and the flags; check() recomputes all of it from the samples.
Synthetic inputs only; no dE/dx resolution or PID quality is claimed.
"""
from __future__ import annotations

import math

from .timing_payload import InputError

FORMAT = "timing-dedx/1"
FEW_SAMPLES = 4
SAMPLE_KEYS = ("sample_id", "layer", "deposit_mev", "path_length_cm", "saturated")


def _finite(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _count(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _derive(samples, fraction, normalization, track_id=None) -> dict:
    if track_id is not None and (isinstance(track_id, bool) or not isinstance(track_id, int) or track_id < 0):
        raise InputError("dE/dx: track_id is null or a non-negative integer")
    if not isinstance(samples, list) or not samples:
        raise InputError("dE/dx: no samples: a value is never kept without the samples it came from")
    kept_samples = []
    for sample in samples:
        if not isinstance(sample, dict) or not set(SAMPLE_KEYS) <= set(sample):
            raise InputError(f"dE/dx: each sample is {{{', '.join(SAMPLE_KEYS)}}}")
        if not _count(sample["sample_id"]) or not _count(sample["layer"]) or not isinstance(sample["saturated"], bool):
            raise InputError("dE/dx: sample_id and layer are non-negative integers, saturated a boolean")
        if not _finite(sample["deposit_mev"]) or sample["deposit_mev"] < 0:
            raise InputError(f"dE/dx: sample {sample['sample_id']}: the deposit is not a non-negative number")
        if not _finite(sample["path_length_cm"]) or sample["path_length_cm"] <= 0:
            raise InputError(f"dE/dx: sample {sample['sample_id']}: no positive path length")
        kept_samples.append({key: sample[key] for key in SAMPLE_KEYS} | {"dedx_mev_per_cm": sample["deposit_mev"] / sample["path_length_cm"]})
    ids = [s["sample_id"] for s in kept_samples]
    if len(ids) != len(set(ids)):
        raise InputError("dE/dx: a sample identifier is used twice")
    if not _finite(fraction) or not 0 <= fraction < 1:
        raise InputError("dE/dx: the truncation fraction is in [0, 1)")
    if not isinstance(normalization, dict) or set(normalization) != {"value_mev_per_cm", "source"} \
            or not _finite(normalization["value_mev_per_cm"]) or normalization["value_mev_per_cm"] <= 0 \
            or not isinstance(normalization["source"], str) or not normalization["source"]:
        raise InputError("dE/dx: the normalization is {value_mev_per_cm > 0, source}")
    n = len(kept_samples)
    drop = math.floor(fraction * n)
    if n - drop < 1:
        raise InputError("dE/dx: the truncation keeps no sample")
    order = sorted(kept_samples, key=lambda s: (s["dedx_mev_per_cm"], s["sample_id"]))
    kept, dropped = order[:n - drop], order[n - drop:]
    mean = math.fsum(s["dedx_mev_per_cm"] for s in kept) / len(kept)
    flags = sorted(({"few-samples"} if n < FEW_SAMPLES else set()) | ({"saturated-in-kept"} if any(s["saturated"] for s in kept) else set()))
    return {"format": FORMAT, "track_id": track_id, "samples": kept_samples, "truncation_fraction": fraction, "n": n, "n_kept": len(kept),
            "kept": sorted(s["sample_id"] for s in kept), "dropped": sorted(s["sample_id"] for s in dropped),
            "truncated_mean_mev_per_cm": mean, "normalization": dict(normalization),
            "normalized": mean / normalization["value_mev_per_cm"], "flags": flags}


def measure(samples: list, truncation_fraction: float, normalization: dict, track_id: int | None = None) -> dict:
    """The dE/dx record of one track's samples; track_id ties it to the track whose PID it informs (fix round 1, N3)."""
    return _derive(samples, truncation_fraction, normalization, track_id)


def check(record: dict) -> None:
    """Refuses a dE/dx record that does not follow from its own samples (raises InputError, never another exception)."""
    try:
        if not isinstance(record, dict) or record.get("format") != FORMAT:
            raise InputError(f"dE/dx: not a {FORMAT} record")
        samples = record.get("samples")
        raw = [{key: s[key] for key in SAMPLE_KEYS} for s in samples] if isinstance(samples, list) else None
        expected = _derive(raw, record.get("truncation_fraction"), record.get("normalization"), record.get("track_id"))
    except InputError:
        raise
    except (TypeError, KeyError, AttributeError, ValueError) as exc:
        raise InputError(f"dE/dx: malformed record ({type(exc).__name__}: {exc})") from None
    if record != expected:
        raise InputError("dE/dx: the record does not follow from its samples (a retained value, set, mean or flag differs)")
