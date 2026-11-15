#!/usr/bin/env python3
"""Scoring side of T10's destriping replay: the synthetic fixture t10-destripe/1 and its negative variants
(docs/dev/detector-reconstruction/t10-replay-stage-plan.md, section 2). The data side (destriper.py, destripe_recipe) never imports
this module.

Model: y_t = m_p(t) + a_b(t) + n_t, baseline b(t) = floor(t / L). 16 pixels, 32 baselines of L = 8 samples. Baseline b sweeps a
contiguous arc of arc_b in {2, 4} pixels from a seeded start. Map integers of magnitude 1..19 with a random sign; baselines in pairs
(v, -v), v in 1..9, permuted, so they sum to zero exactly. Streams: pointing default_rng(seed), signal seed + 1, noise seed + 2.

Variants: noiseless (y = m + a exactly), noisy (white Gaussian noise, sigma 1, artificial units), disconnected (baselines 0-15 see
pixels p mod 8, baselines 16-31 see 8 + p mod 8: two components, so two null modes). Files: destriper-timestream/1 (data side: no
seed, truth or variant) and destriper-truth/1 (scoring side).

Usage: t10_fixture.py write --variant noisy --seed 20260 --out DIR. Output: one JSON object with "status"; exit 0 written, 2 bad
input (an existing target is never overwritten).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy

FIXTURE = "t10-destripe/1"
VARIANTS = ("noiseless", "noisy", "disconnected")
PIXELS, BASELINES, LENGTH = 16, 32, 8
UNIT = "artificial-unit"
NOISE_PREMISE = "white noise of one variance per sample, stated by the fixture, not estimated"


def _pointing(seed: int) -> numpy.ndarray:
    rng = numpy.random.default_rng(seed)
    starts = rng.integers(0, PIXELS, BASELINES)
    arcs = rng.choice([2, 4], BASELINES)
    return numpy.concatenate([(starts[b] + numpy.arange(LENGTH) * arcs[b] // LENGTH) % PIXELS for b in range(BASELINES)])


def _signal(seed: int) -> tuple[list[int], list[int]]:
    rng = numpy.random.default_rng(seed + 1)
    magnitudes = rng.integers(1, 20, PIXELS)
    signs = rng.choice([-1, 1], PIXELS)
    sky = [int(m * s) for m, s in zip(magnitudes, signs)]
    pairs = rng.integers(1, 10, BASELINES // 2)
    offsets = numpy.concatenate([pairs, -pairs])[rng.permutation(BASELINES)]
    return sky, [int(value) for value in offsets]


def generate(variant: str, seed: int) -> tuple[dict, dict]:
    """(timestream, truth) of one variant."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
    pixel = _pointing(seed)
    if variant == "disconnected":
        half = PIXELS // 2
        pixel = pixel % half + half * (numpy.arange(pixel.size) // LENGTH >= BASELINES // 2)
    sky, offsets = _signal(seed)
    clean = [float(sky[p] + offsets[t // LENGTH]) for t, p in enumerate(pixel)]
    sigma = 0 if variant == "noiseless" else 1
    noise = numpy.random.default_rng(seed + 2).normal(0.0, 1.0, pixel.size) if sigma else numpy.zeros(pixel.size)
    value = [float(y + n) for y, n in zip(clean, noise)]
    timestream = {"format": "destriper-timestream/1", "role": "reconstruction-input", "unit": UNIT, "pixels": PIXELS,
                  "baseline_length": LENGTH, "noise_premise": NOISE_PREMISE, "pixel": [int(p) for p in pixel], "value": value}
    truth = {"format": "destriper-truth/1", "fixture": FIXTURE, "seed": seed, "variant": variant, "sigma": sigma, "unit": UNIT,
             "map": sky, "baselines": offsets}
    return timestream, truth


def _dump(document: dict) -> bytes:
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write(variant: str, seed: int, out: Path) -> tuple[Path, Path]:
    """Write <variant>.timestream.json and <variant>.truth.json under out; never overwrite."""
    timestream, truth = generate(variant, seed)
    out.mkdir(parents=True, exist_ok=True)
    paths = out / f"{variant}.timestream.json", out / f"{variant}.truth.json"
    for path in paths:
        if path.exists():
            raise FileExistsError(f"{path} exists: a fixture file is never overwritten")
    for path, document in zip(paths, (timestream, truth)):
        path.write_bytes(_dump(document))
    return paths


# Negative variants (stage plan section 2, F8): one change each to a global scan block, and the code read_sidecar refuses it with.
def _jitter(scan: dict) -> None:
    scan["constraint"], scan["regularization"] = None, "jitter"


def _chunk_average(scan: dict) -> None:
    scan["merging"] = {"kind": "chunk-average"}


def _unique_without_constraint(scan: dict) -> None:
    scan["constraint"], scan["uniqueness_claim"] = None, True


NEGATIVE_VARIANTS = {"jitter": (_jitter, "reconstruction.scan.jitter_precision"),
                     "chunk-average": (_chunk_average, "reconstruction.scan.chunk_average"),
                     "unique-without-constraint": (_unique_without_constraint, "reconstruction.scan.unique_claim")}


def negative_variant(product: dict, name: str) -> dict:
    """A copy of a reconstruction-product/1 with one negative change to its scan block; the input is not changed."""
    bad = json.loads(json.dumps(product))
    NEGATIVE_VARIANTS[name][0](bad["scan"])
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="operation", required=True)
    w = sub.add_parser("write", help="write one variant's timestream and truth files")
    w.add_argument("--variant", required=True, choices=VARIANTS)
    w.add_argument("--seed", required=True, type=int)
    w.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        paths = write(args.variant, args.seed, args.out)
    except (OSError, ValueError) as exc:
        print(json.dumps({"operation": "write", "status": "rejected", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({"operation": "write", "status": "written", "variant": args.variant, "seed": args.seed,
                      "files": [str(path) for path in paths]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
