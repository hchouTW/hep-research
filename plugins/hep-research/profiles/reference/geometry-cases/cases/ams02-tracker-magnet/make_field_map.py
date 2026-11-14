#!/usr/bin/env python3
"""The field map of the ams02-tracker-magnet case: a parametrized approximation, not the AMS measured map.

The AMS-02 magnet's measured map (120,000 points, ams02:C93) is not public. This map is built from the magnet's published
description only: a cylindrical shell of 64 Nd-Fe-B sectors, 800 mm long, inner diameter 1115 mm (ams02:C93), outer radius
649 mm (ams02:C199, a tier-3 thesis of the same magnet in its AMS-01 configuration), each sector magnetized uniformly at the
angle alpha = 2 phi + pi/2 of its centre (the ideal Halbach-dipole law of ams02:C200), turned so that the central field lies
along +x (the AMS frame, ams02:C211). The remanence Br is not published: it is CALIBRATED so that |B(0)| = 0.14 T, the tier-1
central field (ams02:C93), so the central field is an input of this map, never a quantity measured with it.

Method: magnetic surface charges sigma = M.n on the arcs and radial faces of each sector (the caps carry none, M having no z
component; a uniform sector has no volume charge), the z integral of each charge strip done in closed form, the arcs and radial
faces summed numerically (ARC and RADIAL points per sector face). B = mu0 H outside the material; inside it B = mu0 (H + M), so
nodes in the shell are inside a sector's magnetization (those nodes lie where the case has no volume and no track).

The grid, in the local frame of the template 'bore' (placed once at the world's origin): x and y from -700 to 700 mm in 100 mm
steps, z from -750 to 750 mm in 50 mm steps, covering bore's bounding box (radius 649 mm, |z| <= 714 mm).

Usage: python3 make_field_map.py [--out FILE] [--swap-xy]   (numpy). --swap-xy writes the negative control's map, whose columns
bx and by are exchanged (a frame mistake: the field along y). Prints the file's sha256.
"""
from __future__ import annotations

import argparse
import hashlib
import math
from pathlib import Path

import numpy as np

INNER_RADIUS_MM = 1115 / 2          # ams02:C93, inner diameter 1115 mm
OUTER_RADIUS_MM = 649.0             # ams02:C199, outer radius 64.9 cm (AMS-01 configuration of the same magnet)
HALF_LENGTH_MM = 400.0    # ams02:C93, 800 mm long
SECTORS = 64              # ams02:C93
B_CENTRE_T = 0.14         # ams02:C93, 1.4 kG: the calibration of Br
ARC, RADIAL = 48, 48      # integration points per sector arc and per radial face
REGULARIZE_MM2 = 1.0      # keeps a node that falls on a charge strip finite (only nodes inside the shell come near one)
ORIGIN, STEP, COUNT = (-700, -700, -750), (100, 100, 50), (15, 15, 31)


def strips(offset: float):
    """Charge strips (x, y, width_mm, sigma per unit M0) of all sectors, magnetization angle alpha = 2 phi_c + pi/2 + offset."""
    width = 2 * math.pi / SECTORS
    xs, ys, ws, ss = [], [], [], []
    for k in range(SECTORS):
        lo, hi = (k - 0.5) * width, (k + 0.5) * width   # sector k centred on phi = k * width: nodes on the axes miss the faces
        alpha = 2 * (k * width) + math.pi / 2 + offset
        mx, my = math.cos(alpha), math.sin(alpha)
        phis = lo + (np.arange(ARC) + 0.5) * (hi - lo) / ARC
        for radius, sign in ((OUTER_RADIUS_MM, 1.0), (INNER_RADIUS_MM, -1.0)):   # outer arc: normal +r; inner arc: normal -r
            xs.append(radius * np.cos(phis)); ys.append(radius * np.sin(phis))
            ws.append(np.full(ARC, radius * (hi - lo) / ARC))
            ss.append(sign * (mx * np.cos(phis) + my * np.sin(phis)))
        radii = INNER_RADIUS_MM + (np.arange(RADIAL) + 0.5) * (OUTER_RADIUS_MM - INNER_RADIUS_MM) / RADIAL
        for phi, sign in ((lo, -1.0), (hi, 1.0)):              # radial faces: normal -phi_hat at lo, +phi_hat at hi
            nx, ny = -math.sin(phi), math.cos(phi)
            xs.append(radii * math.cos(phi)); ys.append(radii * math.sin(phi))
            ws.append(np.full(RADIAL, (OUTER_RADIUS_MM - INNER_RADIUS_MM) / RADIAL))
            ss.append(np.full(RADIAL, sign * (mx * nx + my * ny)))
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(ws), np.concatenate(ss)


def field(points: np.ndarray, offset: float, br: float) -> np.ndarray:
    """B in tesla at points (N x 3, mm) for remanence br (tesla): sum over strips of the closed-form z integral."""
    sx, sy, sw, ss = strips(offset)
    out = np.zeros_like(points)
    for start in range(0, len(points), 256):
        p = points[start:start + 256]
        dx = p[:, 0:1] - sx[None, :]
        dy = p[:, 1:2] - sy[None, :]
        dd = dx * dx + dy * dy + REGULARIZE_MM2
        u2 = HALF_LENGTH_MM - p[:, 2:3]
        u1 = -HALF_LENGTH_MM - p[:, 2:3]
        r2, r1 = np.sqrt(dd + u2 * u2), np.sqrt(dd + u1 * u1)
        inplane = (u2 / r2 - u1 / r1) / dd          # integral of 1/|r - r'|^3 times the in-plane offset, per unit offset
        along = 1.0 / r2 - 1.0 / r1                  # integral of (z - z') / |r - r'|^3
        q = sw * ss                                   # charge per unit length of strip, per unit M0
        out[start:start + 256, 0] = (q * dx * inplane).sum(axis=1)
        out[start:start + 256, 1] = (q * dy * inplane).sum(axis=1)
        out[start:start + 256, 2] = (q * along).sum(axis=1)
    out *= br / (4 * math.pi)                         # mu0 H with mu0 M0 = br; lengths cancel (mm^2 / mm^2)
    r = np.hypot(points[:, 0], points[:, 1])
    inside = (r >= INNER_RADIUS_MM) & (r <= OUTER_RADIUS_MM) & (np.abs(points[:, 2]) <= HALF_LENGTH_MM)
    if inside.any():                                  # in the material B = mu0 (H + M): add the magnetization of the sector
        width = 2 * math.pi / SECTORS
        k = np.round(np.arctan2(points[inside, 1], points[inside, 0]) / width) % SECTORS
        alpha = 2 * (k * width) + math.pi / 2 + offset
        out[inside, 0] += br * np.cos(alpha)
        out[inside, 1] += br * np.sin(alpha)
    return out


def calibrated():
    """The magnetization offset that puts B(0) along +x, and the Br that makes |B(0)| = 0.14 T."""
    centre = np.zeros((1, 3))
    raw = field(centre, 0.0, 1.0)[0]
    offset = math.atan2(raw[1], raw[0])               # with alpha = 2 phi + c, turning every magnetization by delta turns the central field by -delta
    unit = field(centre, offset, 1.0)[0]
    if not (unit[0] > 0 and abs(unit[1]) < 1e-9 * unit[0]):
        raise SystemExit(f"the central field is not along +x: {unit}")
    return offset, B_CENTRE_T / math.hypot(*unit), unit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("magnet-field-map.txt"))
    parser.add_argument("--swap-xy", action="store_true")
    args = parser.parse_args()
    offset, br, unit = calibrated()
    xs = [ORIGIN[0] + STEP[0] * i for i in range(COUNT[0])]
    ys = [ORIGIN[1] + STEP[1] * j for j in range(COUNT[1])]
    zs = [ORIGIN[2] + STEP[2] * k for k in range(COUNT[2])]
    nodes = np.array([(x, y, z) for z in zs for y in ys for x in xs], dtype=float)   # x fastest, then y, then z
    values = field(nodes, offset, br)
    if args.swap_xy:
        values = values[:, [1, 0, 2]]
    lines = ["g4sim-field-map/1", "origin_mm %d %d %d" % ORIGIN, "step_mm %d %d %d" % STEP, "count %d %d %d" % COUNT, "bx_tesla by_tesla bz_tesla"]
    lines += ["%.6e %.6e %.6e" % tuple(row) for row in values]
    text = "\n".join(lines) + "\n"
    args.out.write_text(text, encoding="utf-8")
    print(f"offset_rad {offset:.9f} br_T {br:.6f} unit_centre {unit[0]:.6e} {unit[1]:.6e} {unit[2]:.6e}")
    print(f"sha256 {hashlib.sha256(text.encode('utf-8')).hexdigest()} {args.out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
