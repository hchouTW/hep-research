"""Synthetic efficiency-map fixtures for the WP-D tests (phase 3): g4sim's map builder and replica law, with a
per-photon detection model in place of the optical transport (Geant4 not run; as en/research-D28.md)."""
from __future__ import annotations

import random

from core.simulation import efficiency_map as em

HALF = [10.0, 10.0, 26.5]
SEGMENTATION = {"kind": "along_axis", "axis": 2, "width_mm": ["13.25"]}
SPECTRUM = {"energy_eV": ["2", "3"], "value": ["1", "1"]}


def build(emitted: dict, detections: dict, run_id: str = "x") -> dict:
    channels = sorted(set(detections.values()))
    detected = [(e, c, 1.0 + (e % 7)) for e, c in sorted(detections.items())]
    return em.build(template="crystal", component=1, spectrum=SPECTRUM, segmentation=SEGMENTATION, half_mm=HALF,
                    channels=channels, emitted=emitted, detected=detected,
                    hashes={"materials_sha256": "0" * 64, "surfaces_sha256": "1" * 64, "mapping_run_id": run_id})


def scan(thetas=(0.9, 1.0, 1.1), photons: int = 4000, divergence: float = 0.1, seed: int = 5):
    """A shared-seed scan: the same emitted photons at every design point; each photon keeps its fate from the previous
    design point unless its history diverges (probability `divergence` per step), when it is redrawn at that point's
    theta (a coupling of the detections across theta). Returns (maps, bins, detections, channels)."""
    draw = random.Random(seed)
    emitted = {e: [draw.uniform(-h, h) for h in HALF] for e in range(photons)}
    bins = {e: em.bin_of(SEGMENTATION, HALF, p) for e, p in emitted.items()}
    u0 = {e: draw.random() for e in emitted}
    dets: list = []
    prev = None
    for j, th in enumerate(thetas):
        cur = {}
        for e, p in emitted.items():
            if prev is None or draw.random() < divergence:
                z = p[2]
                pl = th * (0.04 - 0.01 * z / HALF[2])
                pr = th * (0.03 + 0.01 * z / HALF[2])
                u = u0[e] if prev is None else draw.random()
                ch = "left" if u < pl else ("right" if u < pl + pr else None)
            else:
                ch = prev.get(e)
            if ch is not None:
                cur[e] = ch
        dets.append(cur)
        prev = cur
    maps = [build(emitted, d, f"map{j}") for j, d in enumerate(dets)]
    return maps, bins, dets, [m["channels"] for m in maps]
