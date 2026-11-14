"""t07-alignment-payload/1: the alignment payload the T07 refit takes (plan R32, R33, R37; CAI-T07-3; D1 stage 9), in Python.

The native file holds the constants; native/alignment_payload.cpp reads the same bytes and refuses the same defects, and the driver applies
a payload through the placement route (payload_geometry.hpp, PlacedTelescope; user's choice 16) with `refit --alignment-payload FILE`.
Its R32 sidecar (conditions-payload/1, contracts/schemas/conditions_payload.json) holds a digest of the native file, never constants.

Format, one record per line, every line ending in a newline, numbers at 17 significant digits:

    t07-alignment-payload/1
    parametrization t07-plane-rigid/1 local sensor
    derived_against <64 lowercase hex: the nominal geometry identity the deltas apply to>
    origin nominal|measured
    derived_from none|<64 lowercase hex: the content identity of the payload this one was derived from>
    plane <1..8> <shift-loc0 mm> <shift-loc1 mm> <shift-normal mm> <rotation-loc0 rad> <rotation-loc1 rad> <rotation-normal rad>
    ...
    end <number of plane records>

- Mapping to plane deltas: one plane record is payload_geometry.hpp's PlaneDelta of that plane, in t07-plane-rigid/1's order
  (R32_PLANE_PARAMETERS of acts_native_product.py): moved = nominal * shift * R(normal) * R(loc1) * R(loc0), in the plane's own local frame,
  the sensor level. A plane without a record is at nominal. Planes appear in increasing order, each at most once, so one set of deltas has one text.
- Identity: the content identity of a payload is the SHA-256 of its bytes (payload_content_id). Its R32 identity is its sidecar's payload_id
  (contracts.conditions.payload_identity), which binds the content identity as content_sha256. A product records the content identity.
- Derived payload (R33: "plugin code derives a new payload with the other parameters at nominal; it has its own identity and records the payload
  it came from"): derive_subset keeps the chosen parameters of the chosen planes, sets every other parameter to nominal (0), and writes derived_from
  as the parent's content identity; its sidecar's derived_from is the parent sidecar's payload_id.
- Refused, never applied (R32): another first line, a record out of order or missing, another parametrization, frame or level, an identity that is not
  64 lowercase hex, an origin other than nominal or measured, a plane outside 1..8, a plane twice or out of order, a value that is not a finite number,
  a plane record with another count of values, an end count that is not the number of plane records, text after the end record, a last line without its
  newline, a payload labelled nominal that moves a plane (R32: nominal is the ideal geometry; D1 stage 9 fix round 1, m5); and, where the reader is given the geometry it binds to, a payload derived against another nominal geometry.

The nominal geometry identity (nominal_geometry_id): the SHA-256 of nominal_geometry_text, the frozen telescope's eight planes as the driver builds them
(telescope_geometry.cpp): bounds and local-to-global transform. The driver prints its own (`acts_tracking_driver geometry-id`); this module's copy is
a replica for tests without a build. It is not g4sim's geometry_id (D2): the T07 telescope has no geometry IR, so none can be formed (D1 stage 9 report).
Standard library only, but for the sidecar's identity, which is contracts.conditions'.
"""
from __future__ import annotations

import hashlib
import math
import re
import sys
from pathlib import Path

PAYLOAD_FORMAT = "t07-alignment-payload/1"
PARAMETRIZATION = ("t07-plane-rigid/1", "local", "sensor")  # name, frame, level (R32): the product's alignment_parametrization
PLANE_PARAMETERS = ("shift-loc0", "shift-loc1", "shift-normal", "rotation-loc0", "rotation-loc1", "rotation-normal")
PLANE_COUNT = 8
ORIGINS = ("nominal", "measured")
NO_SOURCE = "none"
GEOMETRY_FORMAT = "t07-telescope-nominal/1"
# Section 4.1 and telescope_geometry.cpp: planes at x = 0, 50, ..., 350 mm, 300 x 300 mm; rotation columns loc0 = ACTS y, loc1 = ACTS z, normal = ACTS x.
PLANE_SPACING_MM, PLANE_HALF_WIDTH_MM = 50.0, 150.0
NOMINAL_ROTATION = ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))  # row-major
_HEX = re.compile(r"^[0-9a-f]{64}$")
_DECIMAL = re.compile(r"^[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)([eE][+-]?[0-9]+)?$")  # what %.17g writes; no hexadecimal, inf or nan (the native reader's rule too)
_COUNT = re.compile(r"^(0|[1-9][0-9]*)$")


class PayloadFormatError(ValueError):
    """Not a t07-alignment-payload/1 this reader can apply: refused, never applied (R32)."""


def _number_text(value: float) -> str:
    if not math.isfinite(value):
        raise PayloadFormatError("a payload holds finite numbers only")
    return "%.17g" % value


def _number(token: str) -> float:
    if not _DECIMAL.match(token):
        raise PayloadFormatError(f"not a decimal number: {token}")
    value = float(token)
    if not math.isfinite(value):
        raise PayloadFormatError(f"not a finite number: {token}")
    return value


def nominal_geometry_text() -> str:
    """The text whose SHA-256 is the nominal geometry identity; native/alignment_payload.cpp writes the same bytes from the built geometry."""
    lines = [GEOMETRY_FORMAT, f"planes {PLANE_COUNT}"]
    for plane in range(1, PLANE_COUNT + 1):
        bounds = (-PLANE_HALF_WIDTH_MM, -PLANE_HALF_WIDTH_MM, PLANE_HALF_WIDTH_MM, PLANE_HALF_WIDTH_MM)
        rotation = [value for row in NOMINAL_ROTATION for value in row]
        translation = ((plane - 1) * PLANE_SPACING_MM, 0.0, 0.0)
        lines.append(" ".join([f"plane {plane} rectangle"] + [_number_text(value) for value in (*bounds, *rotation, *translation)]))
    return "\n".join(lines) + "\n"


def nominal_geometry_id() -> str:
    return hashlib.sha256(nominal_geometry_text().encode("ascii")).hexdigest()


def payload_content_id(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def encode_payload(deltas: dict, derived_against: str, origin: str = "measured", derived_from: str = NO_SOURCE) -> str:
    """deltas: {plane: six values in PLANE_PARAMETERS order}. The exact bytes the native reader takes."""
    if not _HEX.match(derived_against):
        raise PayloadFormatError("derived_against is a 64-character lowercase hexadecimal identity")
    if origin not in ORIGINS:
        raise PayloadFormatError(f"origin is nominal or measured, not {origin}")
    if derived_from != NO_SOURCE and not _HEX.match(derived_from):
        raise PayloadFormatError("derived_from is none or a 64-character lowercase hexadecimal identity")
    lines = [PAYLOAD_FORMAT, "parametrization " + " ".join(PARAMETRIZATION), f"derived_against {derived_against}", f"origin {origin}", f"derived_from {derived_from}"]
    for plane in sorted(deltas):
        values = list(deltas[plane])
        if not 1 <= int(plane) <= PLANE_COUNT or int(plane) != plane:
            raise PayloadFormatError(f"no plane {plane}: the telescope has planes 1 to {PLANE_COUNT}")
        if len(values) != len(PLANE_PARAMETERS):
            raise PayloadFormatError(f"plane {plane} has {len(values)} values, not {len(PLANE_PARAMETERS)}")
        lines.append(" ".join([f"plane {int(plane)}"] + [_number_text(float(value)) for value in values]))
    lines.append(f"end {len(deltas)}")
    return "\n".join(lines) + "\n"


def parse_payload(text: str, geometry_id: str | None = None) -> dict:
    """The payload as a dict, or PayloadFormatError. With geometry_id, a payload derived against another nominal geometry is refused too (R32)."""
    if not text.endswith("\n"):
        raise PayloadFormatError("the last line is not finished")
    lines = text[:-1].split("\n")
    if lines[0] != PAYLOAD_FORMAT:
        raise PayloadFormatError(f"not {PAYLOAD_FORMAT}")
    expected = ("parametrization", "derived_against", "origin", "derived_from")
    if len(lines) < 1 + len(expected) + 1:
        raise PayloadFormatError("the payload ends inside its header")
    header = {}
    for name, line in zip(expected, lines[1:1 + len(expected)]):
        tokens = line.split(" ")
        if tokens[0] != name:
            raise PayloadFormatError(f"expected the record {name}, found {tokens[0]}")
        header[name] = tokens[1:]
    if tuple(header["parametrization"]) != PARAMETRIZATION:
        raise PayloadFormatError(f"the parametrization is {' '.join(PARAMETRIZATION)}, not {' '.join(header['parametrization'])}")
    for name in ("derived_against", "origin", "derived_from"):
        if len(header[name]) != 1:
            raise PayloadFormatError(f"{name} has {len(header[name])} values")
    derived_against, origin, derived_from = header["derived_against"][0], header["origin"][0], header["derived_from"][0]
    if not _HEX.match(derived_against):
        raise PayloadFormatError("the alignment payload's derived_against is not a 64-character lowercase hexadecimal identity")
    if origin not in ORIGINS:
        raise PayloadFormatError(f"origin is nominal or measured, not {origin}")
    if derived_from != NO_SOURCE and not _HEX.match(derived_from):
        raise PayloadFormatError("the alignment payload's derived_from is not none or a 64-character lowercase hexadecimal identity")
    deltas, counted, last_plane = {}, None, 0
    for line in lines[1 + len(expected):]:
        if counted is not None:
            raise PayloadFormatError("text after the end record")
        tokens = line.split(" ")
        if tokens[0] == "end" and len(tokens) == 2:
            if not _COUNT.match(tokens[1]):
                raise PayloadFormatError(f"the end record counts {tokens[1]}")
            counted = int(tokens[1])
            continue
        if tokens[0] != "plane":
            raise PayloadFormatError(f"unknown record {tokens[0]}")
        if len(tokens) != 2 + len(PLANE_PARAMETERS):
            raise PayloadFormatError(f"a plane record has {len(tokens) - 2} values, not {len(PLANE_PARAMETERS)}")
        if not _COUNT.match(tokens[1]) or not 1 <= int(tokens[1]) <= PLANE_COUNT:
            raise PayloadFormatError(f"no plane {tokens[1]}: the telescope has planes 1 to {PLANE_COUNT}")
        plane = int(tokens[1])
        if plane <= last_plane:
            raise PayloadFormatError(f"plane {plane} twice or out of order")
        last_plane = plane
        deltas[plane] = [_number(token) for token in tokens[2:]]
    if counted is None:
        raise PayloadFormatError("the payload ends before its end record")
    if counted != len(deltas):
        raise PayloadFormatError(f"the end record counts {counted} planes, the payload holds {len(deltas)}")
    if origin == "nominal" and any(value != 0.0 for values in deltas.values() for value in values):
        raise PayloadFormatError("an alignment payload labelled nominal moves no plane: nominal is the ideal geometry (R32)")
    if geometry_id is not None and derived_against != geometry_id:
        raise PayloadFormatError(f"derived against the geometry {derived_against}, not the nominal geometry {geometry_id} it would be applied to")
    return {"content_id": payload_content_id(text), "derived_against": derived_against, "origin": origin, "derived_from": derived_from, "deltas": deltas}


def plane_deltas(payload: dict) -> list:
    """The eight PlaneDeltas the driver applies, plane 1 first: a plane without a record at nominal."""
    return [list(payload["deltas"].get(plane, [0.0] * len(PLANE_PARAMETERS))) for plane in range(1, PLANE_COUNT + 1)]


def derive_subset(parent_text: str, keep: dict) -> str:
    """keep: {plane: parameter names}. A new payload with those parameters of those planes, every other one at nominal, recording its parent (R33)."""
    parent = parse_payload(parent_text)
    deltas = {}
    for plane, names in keep.items():
        unknown = sorted(set(names) - set(PLANE_PARAMETERS))
        if unknown or plane not in parent["deltas"]:
            raise PayloadFormatError(f"the parent holds no {unknown or 'record'} for plane {plane}")
        deltas[plane] = [value if name in names else 0.0 for name, value in zip(PLANE_PARAMETERS, parent["deltas"][plane])]
    return encode_payload(deltas, parent["derived_against"], parent["origin"], parent["content_id"])


def payload_sidecar(text: str, tag: str, source: str, parent_sidecar: dict | None = None, iov_end: int = 1) -> dict:
    """The R32 sidecar of a native payload: conditions-payload/1, kind alignment-parameters, a digest of the content and no constants."""
    payload = parse_payload(text)
    if (parent_sidecar is None) != (payload["derived_from"] == NO_SOURCE):
        raise PayloadFormatError("a derived payload's sidecar names its parent's sidecar, and only a derived payload's")
    nonzero = [(plane, [name for name, value in zip(PLANE_PARAMETERS, values) if value != 0.0]) for plane, values in sorted(payload["deltas"].items())]
    freedoms = [{"structure": f"plane-{plane}", "parameters": names, "frame": "local", "level": "sensor"} for plane, names in nonzero if names]
    if not freedoms:  # post-freeze fix (the user, 2026-11-13): a payload that moves nothing states every plane at nominal (R32 needs the section)
        if payload["derived_against"] != nominal_geometry_id():
            raise PayloadFormatError("a payload that moves nothing states the nominal geometry's planes, and this one is derived against another geometry")
        planes = int(next(line.split()[1] for line in nominal_geometry_text().splitlines() if line.startswith("planes ")))
        freedoms = [{"structure": f"plane-{plane}", "parameters": list(PLANE_PARAMETERS), "frame": "local", "level": "sensor"} for plane in range(1, planes + 1)]
    sidecar = {"schema": "conditions-payload/1", "payload_id": "", "tag": tag, "kind": "alignment-parameters", "producer": {"kind": "external", "source": source},
               "iov": {"predicates": [{"coordinate": "run", "start": 0, "end": iov_end, "closure": "half-open"}]},
               "parametrization": {"name": PARAMETRIZATION[0].split("/")[0], "version": PARAMETRIZATION[0].split("/")[1]},
               "frame": {"name": "plane-local", "kind": "local"}, "derived_against": {"geometry_id": payload["derived_against"]},
               "constraints_used": [], "unconstrained_modes": [], "independent_validation": [], "origin": payload["origin"],
               "content_sha256": payload["content_id"], "required_extensions": []}
    if freedoms:
        sidecar["alignment"] = {"degrees_of_freedom": freedoms}
    if parent_sidecar is not None:
        if parent_sidecar["content_sha256"] != payload["derived_from"]:
            raise PayloadFormatError("the parent sidecar is not the sidecar of the payload this one was derived from")
        sidecar["derived_from"] = parent_sidecar["payload_id"]
    root = Path(__file__).resolve().parents[4]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from contracts.conditions import payload_identity  # adapters may import contracts (tools/check_layering.py)
    sidecar["payload_id"] = payload_identity(sidecar)
    return sidecar
