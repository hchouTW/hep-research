"""Convex polyhedra for the checks of rotated placements (Section 7.3, item 6): a separating-axis test says whether two interiors overlap, and
the true minimum distance says whether a gap is legal. Exact decimal arithmetic, 34 digits.

The distance is taken over vertex-face and edge-edge pairs, the only pairs where two disjoint convex polyhedra can be closest. Part B allows GJK
to a duality gap below epsilon; with the few vertices of a template this enumeration gives the same minimum with no iteration.
"""
from __future__ import annotations

from decimal import Decimal

from core.geometry.numbers import CONTEXT, EPSILON_MM, add, divide, multiply, subtract
from core.geometry.rotation import cos_sin, rotate

_ZERO, _ONE = Decimal(0), Decimal(1)
BOX_FACES = ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))


def box_vertices(half: tuple) -> list:
    return [(multiply(Decimal(sx), half[0]), multiply(Decimal(sy), half[1]), multiply(Decimal(sz), half[2])) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]


class Polyhedron:
    """Vertices and faces, each face an ordered loop of vertex indices."""

    def __init__(self, vertices: list, faces: tuple):
        self.vertices, self.faces = vertices, faces
        edges = set()
        for loop in faces:
            for at, first in enumerate(loop):
                second = loop[(at + 1) % len(loop)]
                edges.add((min(first, second), max(first, second)))
        self.edges = sorted(edges)

    def placed(self, matrix, centre: tuple) -> Polyhedron:
        return Polyhedron([tuple(add(a, b) for a, b in zip(rotate(matrix, vertex), centre)) for vertex in self.vertices], self.faces)


def box(half: tuple) -> Polyhedron:
    return Polyhedron(box_vertices(half), BOX_FACES)


def trd(solid: dict) -> Polyhedron:
    x1, x2, y1, y2, z = (Decimal(solid[key]) for key in ("dx1_mm", "dx2_mm", "dy1_mm", "dy2_mm", "dz_mm"))
    vertices = [(multiply(Decimal(sx), x), multiply(Decimal(sy), y), multiply(Decimal(sz), z))
                for sx in (-1, 1) for sy in (-1, 1) for sz, x, y in ((-1, x1, y1), (1, x2, y2))]
    return Polyhedron(vertices, BOX_FACES)


def prism(sides: int, radius: Decimal, half_length: Decimal) -> Polyhedron:
    """A regular prism along z, with a vertex at phi = 0 (GB23 confirms G4Polyhedra's)."""
    ring = [cos_sin(divide(multiply(Decimal(360), Decimal(k)), Decimal(sides))) for k in range(sides)]
    vertices = [(multiply(radius, Decimal(c)), multiply(radius, Decimal(s)), CONTEXT.minus(half_length)) for c, s in ring]
    vertices += [(multiply(radius, Decimal(c)), multiply(radius, Decimal(s)), half_length) for c, s in ring]
    side_faces = tuple((k, (k + 1) % sides, sides + (k + 1) % sides, sides + k) for k in range(sides))
    return Polyhedron(vertices, (tuple(reversed(range(sides))), tuple(range(sides, 2 * sides)), *side_faces))


CIRCUMSCRIBED_SIDES = 32


def circumscribed(rmax: Decimal, half_length: Decimal) -> Polyhedron:
    """A prism around a tube: passing against it proves the tube clear, and failing proves nothing (Section 7.3)."""
    return prism(CIRCUMSCRIBED_SIDES, divide(rmax, Decimal(cos_sin(divide(Decimal(180), Decimal(CIRCUMSCRIBED_SIDES)))[0])), half_length)


def _minus(a: tuple, b: tuple) -> tuple:
    return tuple(subtract(x, y) for x, y in zip(a, b))


def _dot(a: tuple, b: tuple) -> Decimal:
    return add(add(multiply(a[0], b[0]), multiply(a[1], b[1])), multiply(a[2], b[2]))


def _cross(a: tuple, b: tuple) -> tuple:
    return (subtract(multiply(a[1], b[2]), multiply(a[2], b[1])), subtract(multiply(a[2], b[0]), multiply(a[0], b[2])),
            subtract(multiply(a[0], b[1]), multiply(a[1], b[0])))


def _length(a: tuple) -> Decimal:
    return CONTEXT.sqrt(_dot(a, a))


def _normal(polyhedron: Polyhedron, loop: tuple) -> tuple:
    v = polyhedron.vertices
    return _cross(_minus(v[loop[1]], v[loop[0]]), _minus(v[loop[2]], v[loop[0]]))


def separating_gap(a: Polyhedron, b: Polyhedron) -> Decimal:
    """The largest projection gap over all candidate axes: at least -epsilon only when the interiors are disjoint."""
    axes = [_normal(a, loop) for loop in a.faces] + [_normal(b, loop) for loop in b.faces]
    for first in a.edges:
        for second in b.edges:
            axes.append(_cross(_minus(a.vertices[first[1]], a.vertices[first[0]]), _minus(b.vertices[second[1]], b.vertices[second[0]])))
    best = None
    for axis in axes:
        size = _length(axis)
        if size <= Decimal("1e-25"):  # parallel edges give no axis
            continue
        unit = tuple(divide(value, size) for value in axis)
        on_a = [_dot(unit, vertex) for vertex in a.vertices]
        on_b = [_dot(unit, vertex) for vertex in b.vertices]
        gap = max(subtract(min(on_b), max(on_a)), subtract(min(on_a), max(on_b)))
        best = gap if best is None or gap > best else best
    return best


def planes(polyhedron: Polyhedron) -> list:
    """(unit outward normal, a point on the face) of every face of a polyhedron around the origin."""
    out = []
    for loop in polyhedron.faces:
        normal = _normal(polyhedron, loop)
        size = _length(normal)
        unit = tuple(divide(value, size) for value in normal)
        anchor = polyhedron.vertices[loop[0]]
        if _dot(unit, anchor) < _ZERO:
            unit = tuple(CONTEXT.minus(value) for value in unit)
        out.append((unit, anchor))
    return out


def face_gaps(mother: Polyhedron, points: list) -> list:
    """For each face of a convex mother, the smallest distance from it inward to any point: negative when a point is outside."""
    return [min(_dot(unit, _minus(anchor, point)) for point in points) for unit, anchor in planes(mother)]


def nearest_to_axis(polyhedron: Polyhedron) -> Decimal:
    """The least distance in x and y from the z axis to any edge; zero when the footprint's box holds the axis."""
    xs, ys = [v[0] for v in polyhedron.vertices], [v[1] for v in polyhedron.vertices]
    if min(xs) <= _ZERO <= max(xs) and min(ys) <= _ZERO <= max(ys):
        return _ZERO
    best = None
    for first, second in polyhedron.edges:
        p, q = polyhedron.vertices[first], polyhedron.vertices[second]
        along = (subtract(q[0], p[0]), subtract(q[1], p[1]), _ZERO)
        flat = (p[0], p[1], _ZERO)
        size = _dot(along, along)
        share = _clamp(divide(CONTEXT.minus(_dot(flat, along)), size)) if size > _ZERO else _ZERO
        value = _length(tuple(add(a, multiply(share, b)) for a, b in zip(flat, along)))
        best = value if best is None or value < best else best
    return best


def disjoint(a: Polyhedron, b: Polyhedron) -> bool:
    return separating_gap(a, b) >= CONTEXT.minus(EPSILON_MM)


def _inside(point: tuple, polyhedron: Polyhedron, loop: tuple, normal: tuple) -> bool:
    v = polyhedron.vertices
    for at, index in enumerate(loop):
        edge = _minus(v[loop[(at + 1) % len(loop)]], v[index])
        if _dot(_cross(edge, _minus(point, v[index])), normal) < CONTEXT.minus(EPSILON_MM):
            return False
    return True


def _vertex_to_faces(a: Polyhedron, b: Polyhedron) -> Decimal | None:
    best = None
    for loop in b.faces:
        normal = _normal(b, loop)
        size = _length(normal)
        unit = tuple(divide(value, size) for value in normal)
        anchor = b.vertices[loop[0]]
        for point in a.vertices:
            height = _dot(_minus(point, anchor), unit)
            foot = tuple(subtract(p, multiply(height, n)) for p, n in zip(point, unit))
            if _inside(foot, b, loop, normal):
                distance = abs(height)
                best = distance if best is None or distance < best else best
    return best


def _clamp(value: Decimal) -> Decimal:
    return _ZERO if value < _ZERO else _ONE if value > _ONE else value


def _segments(p1: tuple, q1: tuple, p2: tuple, q2: tuple) -> Decimal:
    """The distance between two segments."""
    d1, d2, r = _minus(q1, p1), _minus(q2, p2), _minus(p1, p2)
    a, e, f = _dot(d1, d1), _dot(d2, d2), _dot(d2, r)
    c, b = _dot(d1, r), _dot(d1, d2)
    denominator = subtract(multiply(a, e), multiply(b, b))
    s = _clamp(divide(subtract(multiply(b, f), multiply(c, e)), denominator)) if denominator > Decimal("1e-30") else _ZERO
    t = divide(add(multiply(b, s), f), e)
    if t < _ZERO:
        t, s = _ZERO, _clamp(divide(CONTEXT.minus(c), a))
    elif t > _ONE:
        t, s = _ONE, _clamp(divide(subtract(b, c), a))
    near1 = tuple(add(p, multiply(s, d)) for p, d in zip(p1, d1))
    near2 = tuple(add(p, multiply(t, d)) for p, d in zip(p2, d2))
    return _length(_minus(near1, near2))


def distance(a: Polyhedron, b: Polyhedron) -> Decimal:
    """The true minimum distance between two polyhedra with disjoint interiors."""
    found = [value for value in (_vertex_to_faces(a, b), _vertex_to_faces(b, a)) if value is not None]
    for first in a.edges:
        for second in b.edges:
            found.append(_segments(a.vertices[first[0]], a.vertices[first[1]], b.vertices[second[0]], b.vertices[second[1]]))
    return min(found)
