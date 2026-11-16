"""Synthetic mapping runs for the PDE split of Part B section 6.7 (phase 3, WP-E): photons.csv and primaries.csv in
g4sim's S7 formats from a per-photon optics model (Geant4 transport NOT run; en/research-PDE.md used the same kind of
synthetic transport). Each event emits one photon, uniform over a box template placed at CENTRE with no rotation, with an
energy from a flat spectrum; the photon's history up to a sensor (absorbed at channel sipm/0 or sipm/1 with a bin-
dependent probability, its transit and arrival time) is drawn from the history stream, and, as Geant4 does in
DoAbsorption, one uniform per absorption decides Detection against the sensor efficiency (1 for the efficiency-1 run). So
two runs with the same seed and the PDE as the only change are nested. `tied_reflectance` models a PDE tied to the sensor
reflectance (a fraction rho of the undetected photons reflected and absorbed again at the other sensor, later): the
negative case of section 15.3.19."""
from __future__ import annotations

import random

from core.simulation import efficiency_map as em

HALF = [10.0, 10.0, 26.5]
CENTRE = [0.0, 0.0, 100.0]
SEGMENTATION = {"kind": "along_axis", "axis": 2, "width_mm": ["13.25"]}
SPECTRUM = {"energy_eV": ["2.0", "3.5"], "value": ["1", "1"]}
CHANNELS = ["sipm/0", "sipm/1"]


def pde_table(low=0.2, high=0.5) -> dict:
    """A PDE(E) rising linearly over the emission spectrum (knots at 2.0, 2.5, 3.0, 3.5 eV)."""
    e = [2.0, 2.5, 3.0, 3.5]
    return {"energy_eV": e, "value": [low + (high - low) * (x - 2.0) / 1.5 for x in e]}


def _q(efficiency, energy):
    if isinstance(efficiency, dict):
        e, v = efficiency["energy_eV"], efficiency["value"]
        if energy <= e[0]:
            return v[0]
        for (a, va), (b, vb) in zip(zip(e, v), zip(e[1:], v[1:])):
            if a <= energy <= b:
                return va + (vb - va) * (energy - a) / (b - a)
        return v[-1]
    return float(efficiency)


def run(photons=20000, seed=5, efficiency=1.0, rho=0.0, absorb=(0.10, 0.06)):
    """(photons.csv text, primaries.csv text, emitted {event: local}, detected [(event, channel, transit)]).
    efficiency: 1, a constant p or a PDE(E) table {energy_eV, value}; rho > 0 ties a reflectance to the PDE."""
    hist = random.Random(seed)
    det = random.Random(seed * 7919 + 1)        # the Detection uniform: one per absorption, whatever the efficiency
    lines, prim, emitted, detected = ["event,scorer,volume,global_ns,transit_ns,energy_eV,vx,vy,vz,dx,dy,dz,parent"], \
        ["event,particle,x_mm,y_mm,z_mm,energy_eV"], {}, []
    for event in range(photons):
        local = [hist.uniform(-h, h) for h in HALF]
        world = [a + c for a, c in zip(local, CENTRE)]
        energy = hist.uniform(2.0, 3.5)
        emitted[event] = local
        prim.append(f"{event},opticalphoton,{world[0]!r},{world[1]!r},{world[2]!r},{energy!r}")
        zfrac = (local[2] + HALF[2]) / (2 * HALF[2])
        u = hist.random()
        a0, a1 = absorb[0] * (0.6 + 0.8 * zfrac), absorb[1] * (1.4 - 0.8 * zfrac)
        channel = 0 if u < a0 else 1 if u < a0 + a1 else None
        transit = hist.expovariate(0.3 + 0.2 * zfrac)
        direction = [hist.uniform(-1, 1) for _ in range(3)]
        later = hist.expovariate(0.2)
        bounce = hist.random()
        if channel is None:
            continue
        v = det.random()
        q = _q(efficiency, energy)

        def row(ch, t):
            return (f"{event},sipm,{ch},{t + 1.0!r},{t!r},{energy!r},{world[0]!r},{world[1]!r},{world[2]!r},"
                    f"{direction[0]!r},{direction[1]!r},{direction[2]!r},0")
        if v < q:
            lines.append(row(channel, transit))
            detected.append((event, CHANNELS[channel], transit))
        elif rho > 0 and bounce < rho:            # reflected by the sensor (reflectivity tied to 1 - PDE), absorbed again
            other = 1 - channel
            if det.random() < q:
                lines.append(row(other, transit + later))
                detected.append((event, CHANNELS[other], transit + later))
    return "\n".join(lines) + "\n", "\n".join(prim) + "\n", emitted, detected


def build_map(emitted, detected, surfaces_sha256="1" * 64, materials_sha256="0" * 64) -> dict:
    return em.build(template="crystal", component=1, spectrum=SPECTRUM, segmentation=SEGMENTATION, half_mm=HALF,
                    channels=CHANNELS, emitted=emitted, detected=detected,
                    hashes={"materials_sha256": materials_sha256, "surfaces_sha256": surfaces_sha256,
                            "mapping_run_id": "synthetic"})


def bins_rows(events=400, large=0.5, bins=4, steps=10):
    """edep_visible_ly_split rows (event, volume, bin, E^L, E^S, n^L) for digitization: one volume, every bin."""
    return [(e, 0, b, large, 0.0, steps) for e in range(events) for b in range(bins)]
