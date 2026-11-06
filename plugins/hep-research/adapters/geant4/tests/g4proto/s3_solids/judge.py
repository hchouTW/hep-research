#!/usr/bin/env python3
"""GB23 and GB24 (g4sim plan, Section 23): ask real Geant4 solids, and judge the answers against exact geometry.

GB23: prisms with n = 6 and 8, built from the apothem the expander computes, with points near the vertices and the midpoints of the side faces;
the exact verdict comes from the circumradius and a vertex at phi 0. A negative control builds the prism from the circumradius as rOuter, and
another turns the vertices by half a side: both must disagree. GB24: three parameter sets per shape against Python's analytic volume.

Usage: judge.py PROGRAM FOLDER   From an activated Geant4 environment. Prints JSON with a status key; exit 0 confirmed, 1 not confirmed, 2 bad input.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))

from core.geometry import expand, rotation  # noqa: E402

VOLUME_TOLERANCE = 1e-12
OFFSETS_MM = ("1e-3", "1e-6", "1e-8")  # each far above the surface tolerance of 1e-9 mm, which is a shell of half that on each side
PRISMS = ((6, "10", "4"), (8, "10", "4"), (6, "37.5", "120"), (8, "37.5", "120"))


def prism_solid(sides: int, radius: str, length: str) -> dict:
    return expand._other_solid("polygon_prism", {"sides": sides, "radius_mm": radius, "length_mm": length}, expand._Values({}), "")[1]


def exact(number: Decimal) -> Fraction:
    return Fraction(number)


def direction(turn: Fraction) -> tuple:
    """Cosine and sine of a fraction of a turn, to 34 digits."""
    with localcontext() as context:
        context.prec = 50
        angle = Decimal(turn.numerator) * 360 / Decimal(turn.denominator)
    return tuple(exact(value) for value in rotation.cos_sin(angle))


def in_prism(sides: int, radius: Fraction, point: tuple) -> bool:
    """Whether a point of the plane is inside the regular polygon of this circumradius with a vertex at phi 0."""
    apothem = radius * direction(Fraction(1, 2 * sides))[0]
    return all(point[0] * c + point[1] * s < apothem for c, s in (direction(Fraction(2 * k + 1, 2 * sides)) for k in range(sides)))


def prism_questions(sides: int, radius: Fraction, half_z: Fraction) -> list:
    """Points just inside and outside each vertex and each face midpoint, each rounded to a double, which is the point Geant4 is really asked about."""
    apothem = radius * direction(Fraction(1, 2 * sides))[0]
    rows = []
    for k in range(sides):
        for reach, turn in ((radius, Fraction(k, sides)), (apothem, Fraction(2 * k + 1, 2 * sides))):
            c, s = direction(turn)
            for offset in OFFSETS_MM:
                for sign in (-1, 1):
                    distance = reach + sign * Fraction(Decimal(offset))
                    rows.append((float(distance * c), float(distance * s), float(half_z / 2)))
    return rows


def ask(program: str, folder: Path, questions: list) -> dict:
    (folder / "questions.txt").write_text("".join(line + "\n" for line in questions), encoding="utf-8")
    subprocess.run([program, str(folder / "questions.txt"), str(folder / "answers.txt")], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return dict(line.split() for line in (folder / "answers.txt").read_text(encoding="utf-8").splitlines())


def gb23(program: str, folder: Path) -> dict:
    questions, wanted, control_built_from_radius, control_turned = [], {}, {}, {}
    for number, (sides, radius, length) in enumerate(PRISMS):
        solid = prism_solid(sides, radius, length)
        apothem, half_z = float(solid["apothem_mm"]), float(solid["dz_mm"])
        circumradius = Fraction(Decimal(radius))
        half_turn = direction(Fraction(1, 2 * sides))
        for index, (x, y, z) in enumerate(prism_questions(sides, circumradius, Fraction(Decimal(solid["dz_mm"])))):
            place = f"{x.hex()} {y.hex()} {z.hex()}"
            key = f"{number}.{index}"
            verdict = "inside" if in_prism(sides, circumradius, (Fraction(x), Fraction(y))) else "outside"
            wanted[key] = verdict
            questions.append(f"prism {key} {sides} {apothem.hex()} {half_z.hex()} {place}")
            control_built_from_radius[f"r{key}"] = verdict
            questions.append(f"prism r{key} {sides} {float(radius).hex()} {half_z.hex()} {place}")
            # the same question with the point turned by half a side: a prism whose vertices lay on the faces' directions would answer it as wanted
            turned = (float(x * half_turn[0] - y * half_turn[1]), float(x * half_turn[1] + y * half_turn[0]))
            control_turned[f"t{key}"] = verdict
            questions.append(f"prism t{key} {sides} {apothem.hex()} {half_z.hex()} {turned[0].hex()} {turned[1].hex()} {z.hex()}")
    answers = ask(program, folder, questions)
    differ = [key for key, verdict in wanted.items() if answers[key] != verdict]
    return {"confirmed": not differ and bool(wanted), "points": len(wanted), "inside": sum(v == "inside" for v in wanted.values()), "differ": differ[:10],
            "control_radius_as_apothem_differ": sum(answers[key] != v for key, v in control_built_from_radius.items()),
            "control_vertices_turned_differ": sum(answers[key] != v for key, v in control_turned.items())}


def gb24(program: str, folder: Path) -> dict:
    questions, wanted = [], {}

    def hexes(*values) -> str:
        return " ".join(float(value).hex() for value in values)
    for number, (a, b, c) in enumerate(((1.0, 2.0, 3.0), (10.5, 0.25, 77.0), (1234.5, 3.5, 0.125))):
        questions.append(f"box box{number} {hexes(a, b, c)}")
        wanted[f"box{number}"] = 8 * Fraction(a) * Fraction(b) * Fraction(c)
    for number, (x1, x2, y1, y2, z) in enumerate(((5.0, 5.0, 5.0, 5.0, 10.0), (3.0, 7.0, 2.0, 9.0, 11.5), (10.0, 0.5, 0.75, 40.0, 3.25))):
        questions.append(f"trd trd{number} {hexes(x1, x2, y1, y2, z)}")
        x1, x2, y1, y2, z = (Fraction(value) for value in (x1, x2, y1, y2, z))
        wanted[f"trd{number}"] = 2 * z / 6 * (4 * x1 * y1 + 4 * x2 * y2 + 4 * (x1 + x2) * (y1 + y2))  # prismatoid: h (A1 + A2 + 4 Am) / 6
    for number, (rmin, rmax, z, span) in enumerate(((0.0, 10.0, 20.0, 2 * math.pi), (5.0, 10.0, 40.0, 2 * math.pi), (3.0, 7.5, 2.5, math.pi / 3))):
        questions.append(f"tube tube{number} {hexes(rmin, rmax, z, 0.0, span)}")
        wanted[f"tube{number}"] = float(span) * (rmax * rmax - rmin * rmin) * z  # (span / 2) (rmax^2 - rmin^2) (2 z)
    for number, (sides, radius, length) in enumerate(((6, "10", "4"), (8, "37.5", "120"), (5, "2.5", "0.75"))):
        solid = prism_solid(sides, radius, length)
        questions.append(f"polyprism prism{number} {sides} {hexes(solid['apothem_mm'], solid['dz_mm'])}")
        wanted[f"prism{number}"] = sides * float(radius) ** 2 * math.sin(2 * math.pi / sides) * float(solid["dz_mm"])  # (n R^2 sin(2 pi / n) / 2) (2 dz)
    answers = ask(program, folder, questions)
    relative = {key: abs(float.fromhex(answers[key]) / float(value) - 1) for key, value in wanted.items()}
    failing = {key: value for key, value in relative.items() if value > VOLUME_TOLERANCE}
    return {"confirmed": not failing, "largest_relative_difference": max(relative.values()), "failing": failing}


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"status": "rejected", "message": "usage: judge.py PROGRAM FOLDER"}))
        return 2
    folder = Path(sys.argv[2])
    folder.mkdir(parents=True, exist_ok=True)
    first = gb23(sys.argv[1], folder)
    second = gb24(sys.argv[1], folder)
    controls = first["control_radius_as_apothem_differ"] > 0 and first["control_vertices_turned_differ"] > 0
    confirmed = first["confirmed"] and second["confirmed"] and controls
    print(json.dumps({"status": "ok" if confirmed else "failed", "GB23": first, "GB24": second, "controls_detected": controls}, indent=1))
    return 0 if confirmed else 1


if __name__ == "__main__":
    sys.exit(main())
