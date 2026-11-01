"""Garfield++ backend of detsim: capability garfield.gas-table-query 1.0.0 (TASK.md 8.2, 12.3; card GF-QUERY).

A module of detsim.py (docs/dev/detector-simulation/TASK.md and card-GF-QUERY.md). The electron drift velocity of
one 1D Garfield++ gas table at query fields E along +x with B = 0, queried in one process by the rendered script
assets/garfield/gas_table_query.py through ROOT's Python bindings, and checked against an INDEPENDENT parser of the
.gas file and an independent reimplementation of Garfield++'s 1D interpolation (it never calls Garfield++).

Interface (TASK.md 8.2): NAME; capabilities(); code_files(capability); check(task, capability, input_manifest,
input_files) (pure apart from reading the recorded table input, whose bytes are verified against the manifest's
SHA-256; CHECK_READS_INPUTS = True asks the shared layer for input_files); build_spec(...) -> ExecutionSpec; collect
and observables (read the attempt folder); probe(env_root) (reads files of the environment root only). This module
launches no process, writes nothing, and imports no third-party package (ROOT is imported only by the query script,
in the backend process).

Independent parser (storage form pinned by V-10): header lines up to "The gas tables follow:" (Version, GASOK bits,
Dimension F|T nE nA nB nexc nion, the E/p grid in V/(cm Torr), angles, B fields), the records tokenised with the
regular expression [-+]?\\d+\\.\\d+E[-+]\\d+ (numbers are fixed-width and may touch), each 1D record laid out as
MediumGas::ReadRecord1D reads it, and the footer (H Extr, L Extr, Interp, PGAS, TGAS). Node fields are E/p x PGAS
and velocities ve x 1e-3 (cm/us -> cm/ns), in double precision as LoadGasFile computes them.

Reimplementation (V-11): Interpolate1D for a 1D table: order 1 = the linear formula between the two adjacent nodes;
order 2 = Divdif's stencil (the stored value within 1e-6 of the end spacing at the first and last node; the average
of the quadratics through nodes (ix-1, ix, ix+1) and (ix, ix+1, ix+2) inside, a single quadratic through the first
or last three nodes next to an end), evaluated here in Lagrange form; extrapolation constant, linear (through the two
end nodes) or exponential (through the two end nodes in log space, exponent capped at 50).

Checks of collect (card GF-QUERY; tolerances fixed before any query): 1 nodes |v| within 4 ulp of the stored value
and perpendicular components exactly 0; 2 vx < 0 and vy = vz = 0 at every point; 3 interior points within
1e-12 |r| + 4 ulp(r) of the reimplementation; 4 outside points (only with allow_outside_validated_range) within the
same tolerance of the reimplemented extrapolation, rows labelled outside-validated-range. Besides: the script's
JSON status (its last stdout line; missing-dependency becomes the dependency check, which the shared layer maps to
failed / missing-dependency), node coverage (query points at the first, the last and an interior node), conditions,
the requested settings and every planned point. Any failure makes the attempt invalid (partial when a point, the
node coverage or the output is missing). Rows of a known example table carry the note "example table, pipeline
validation only". The environment identity holds the SHA-256 of every library the script loads and of ROOT's
libCore and libCPyCppyy.
"""
from __future__ import annotations

import sys

if __spec__ is None:  # run as a file (tests/skills/test_cli_robustness.py): a module of detsim.py, not a command
    if sys.argv[1:] in ([], ["--help"], ["-h"]):
        print((__doc__ or "detsim module").splitlines()[0] + "\nA module of detsim.py, not a command: "
              "python3 detsim.py --help")
        sys.exit(0)
    print('{"status": "rejected", "error_code": "usage", "message": "a module of detsim.py, not a command"}')
    sys.exit(2)

import base64  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import os  # noqa: E402
import platform  # noqa: E402
import re  # noqa: E402
from decimal import Decimal  # noqa: E402
from pathlib import Path  # noqa: E402

import detsim_canonical as canonical  # noqa: E402

NAME = "garfieldpp"
CHECK_READS_INPUTS = True
ASSETS_DIR = Path(__file__).resolve().parent
DESCRIPTOR_FILE = ASSETS_DIR / "garfield" / "gas_table_query.capability.json"
SCRIPT_FILE = ASSETS_DIR / "garfield" / "gas_table_query.py"
CAPABILITY_ID = "garfield.gas-table-query"
PINNED_COMMIT = "e2e58ea74ec8b20d347d78b7a769f40e3b156072"
SCRIPT_PATH = "ATTEMPT_ROOT/query/gas_table_query.py"
QUERY_PATH = "ATTEMPT_ROOT/query/query.json"
OUTPUT_PATH = "ATTEMPT_ROOT/raw/drift_velocity.txt"
QUERY_FORMAT = "garfield-gas-table-query/1"
OUTPUT_FORMAT = "garfield-gas-table-query-output/1"
BUILD_RECORD = "detsim-garfield-build.json"
BUILD_RECORD_FORMAT = "detsim-garfield-build/1"
NOTE_EXAMPLE = "example table, pipeline validation only"
# tables used under H0 #13 (local input only, pipeline validation only): SHA-256 -> what they are
EXAMPLE_TABLES = {"ba4357348c211812b40f982b979df34bf02738855ee6a1ba58555c35d196b732":
                  "Garfield++ e2e58ea Examples/GasFile/ar_80_co2_20_0T.gas"}
EXTRAPOLATION_CODES = {0: "constant", 1: "linear", 2: "exponential"}
NUMBER = re.compile(r"[-+]?\d+\.\d+E[-+]\d+")
ULPS = 4
RELATIVE = 1e-12
VELOCITY_QUANTITIES = ("drift_velocity_x", "drift_velocity_y", "drift_velocity_z", "drift_velocity_magnitude")
LIBRARIES = ("libGarfieldRandom", "libHeed", "libMagboltz", "libDegrade", "libneBEM", "libGarfield")


def _error(status: str, code: str, message: str, location: str | None = None, **details):
    from detsim_plan import DetsimError  # the shared layer (imported lazily: no import cycle with detsim_plan)
    return DetsimError(status, code, message, location, **details)


# ---------------------------------------------------------------- independent .gas parser (never calls Garfield++)

class GasTableError(ValueError):
    """The file is not a gas table in the pinned storage form; code is a stable reason."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _numbers(text: str) -> list[float]:
    return [float(t) for t in NUMBER.findall(text)]


def _take(lines: list[str], start: int, count: int, what: str) -> tuple[list[float], int]:
    """count numbers from lines[start:], whole lines at a time; (numbers, index of the next line)."""
    found: list[float] = []
    i = start
    while len(found) < count and i < len(lines):
        found += _numbers(lines[i])
        i += 1
    if len(found) != count:
        raise GasTableError("header", f"{what}: expected {count} numbers, found {len(found)}")
    following = lines[i].split() if i < len(lines) else []
    if following and NUMBER.fullmatch(following[0]):  # a further line of numbers: the block holds more than count
        raise GasTableError("header", f"{what}: more than the {count} numbers the Dimension line states")
    return found, i


def record_length_1d(version: int, gasok: str, nexc: int, nion: int) -> int:
    """Numbers per 1D record as MediumGas::ReadRecord1D reads them (value and discarded column pairs)."""
    length = 6 + 4 + 5 + 2 + 2 + 2 + 12 + 2 * nexc + 2 * nion
    length += sum(2 for bit in range(16, 20) if version >= 13 or gasok[bit] == "T")
    return length


def parse_gas_table(raw: bytes) -> dict:
    """The grids, the velocity along E, the footer settings and the conditions of a .gas file (pinned storage form);
    GasTableError for anything else (a malformed integer or number included: code "format")."""
    try:
        return _parse_gas_table(raw)
    except GasTableError:
        raise
    except (ValueError, IndexError, KeyError, TypeError) as err:
        raise GasTableError("format", f"malformed table ({type(err).__name__}: {err})") from None


def _parse_gas_table(raw: bytes) -> dict:
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        raise GasTableError("encoding", "a gas table is ASCII text") from None
    lines = text.splitlines()
    table: dict = {"version": None, "gasok": None, "dimension": None, "identifier": ""}
    end_of_header = None
    i = 0
    while i < len(lines):
        line = lines[i]
        words = line.replace(":", " ").split()
        if line.strip().startswith("The gas tables follow"):
            end_of_header = i
            break
        if not words:
            i += 1
            continue
        if words[0] == "Version" and len(words) > 1:
            table["version"] = int(words[1])
        elif words[0] == "GASOK" and len(words) > 2:
            table["gasok"] = words[2]
        elif words[0] == "Identifier":
            table["identifier"] = line.split(":", 1)[1].strip() if ":" in line else ""
        elif words[0] == "Dimension":
            if len(words) < 7 or words[1] not in ("F", "T"):
                raise GasTableError("header", "the Dimension line is not 'Dimension : F|T nE nA nB nexc nion'")
            table["dimension"] = words[1]
            table["n_e"], table["n_angles"], table["n_b"], table["n_exc"], table["n_ion"] = map(int, words[2:7])
        elif words[:2] == ["E", "fields"]:
            table["e_over_p"], i = _take(lines, i + 1, table.get("n_e", 0), "E fields")
            continue
        elif words[:2] == ["E-B", "angles"]:
            table["angles"], i = _take(lines, i + 1, table.get("n_angles", 0), "E-B angles")
            continue
        elif words[:2] == ["B", "fields"]:
            table["b_fields"], i = _take(lines, i + 1, table.get("n_b", 0), "B fields")
            continue
        i += 1
    if end_of_header is None:
        raise GasTableError("header", "no line 'The gas tables follow:'")
    if table["version"] not in (10, 11, 12, 13):
        raise GasTableError("version", f"version {table['version']} is not 10-13")
    if not isinstance(table["gasok"], str) or len(table["gasok"]) < 20 or set(table["gasok"][:20]) - {"T", "F"}:
        raise GasTableError("header", "no GASOK string of 20 T/F characters")
    if table["dimension"] is None or "e_over_p" not in table:
        raise GasTableError("header", "the Dimension line or the E fields are missing")
    footer = next((k for k in range(end_of_header + 1, len(lines))
                   if lines[k].replace(":", " ").split()[:2] == ["H", "Extr"]), None)
    if footer is None:
        raise GasTableError("footer", "no footer line 'H Extr:'")
    table["records_text"] = "\n".join(lines[end_of_header + 1:footer])
    for k in range(footer, len(lines)):
        words = lines[k].replace(":", " ").replace(",", " ").replace("=", " ").split()
        if words[:2] == ["H", "Extr"]:
            table["extrapolation_high"] = [int(w) for w in words[2:15]]
        elif words[:2] == ["L", "Extr"]:
            table["extrapolation_low"] = [int(w) for w in words[2:15]]
        elif words[:1] == ["Interp"]:
            table["interpolation"] = [int(w) for w in words[1:14]]
        for key, name in (("PGAS", "pressure_torr"), ("TGAS", "temperature_k")):
            match = re.search(key + r"\s*=\s*(" + NUMBER.pattern + ")", lines[k])
            if match:
                table[name] = float(match.group(1))
    for key in ("extrapolation_high", "extrapolation_low", "interpolation"):
        if len(table.get(key, [])) < 1:
            raise GasTableError("footer", f"the footer has no {key.replace('_', ' ')} entries")
    if table["dimension"] == "F":
        records = _numbers(table["records_text"])
        length = record_length_1d(table["version"], table["gasok"], table["n_exc"], table["n_ion"])
        count = table["n_e"] * max(table["n_angles"], 1) * max(table["n_b"], 1)
        if len(records) != length * count:
            raise GasTableError("records", f"expected {count} records of {length} numbers ({length * count}), "
                                           f"found {len(records)}")
        table["record_length"] = length
        table["velocity_e_cm_per_us"] = [records[r * length] for r in range(count)]
    del table["records_text"]
    return table


def node_fields(table: dict) -> list[float]:
    """E at the nodes in V/cm: E/p x PGAS in double precision, as LoadGasFile computes it."""
    return [ep * table["pressure_torr"] for ep in table["e_over_p"]]


def node_velocities(table: dict) -> list[float]:
    """The velocity along E at the nodes in cm/ns: the stored cm/us value x 1e-3, as ReadRecord1D computes it."""
    return [ve * 1e-3 for ve in table["velocity_e_cm_per_us"]]


# ---------------------------------------------------------------- independent reimplementation of Interpolate1D

def _quadratic(xs: list[float], ys: list[float], nodes: tuple[int, int, int], x: float) -> float:
    """The quadratic through three nodes (0-based indices) at x, in Lagrange form."""
    a, b, c = nodes
    xa, xb, xc = xs[a], xs[b], xs[c]
    return (ys[a] * ((x - xb) * (x - xc)) / ((xa - xb) * (xa - xc))
            + ys[b] * ((x - xa) * (x - xc)) / ((xb - xa) * (xb - xc))
            + ys[c] * ((x - xa) * (x - xb)) / ((xc - xa) * (xc - xb)))


def last_node_at_or_below(xs: list[float], x: float) -> int:
    """ix: the 1-based index of the last node <= x (increasing nodes; x >= xs[0])."""
    ix = 0
    for k, node in enumerate(xs):
        if node <= x:
            ix = k + 1
    return ix


def divdif_order2(xs: list[float], ys: list[float], x: float) -> float:
    """Divdif(ytab, xtab, n, x, 2) as pinned (TASK.md 12.3): end-node rule, then the stencil by ix."""
    n = len(xs)
    if n < 2:
        raise ValueError("Divdif needs at least two nodes")
    if abs(x - xs[0]) < 1e-6 * abs(abs(xs[1]) - abs(xs[0])):
        return ys[0]
    if abs(x - xs[n - 1]) < 1e-6 * abs(abs(xs[n - 1]) - abs(xs[n - 2])):
        return ys[n - 1]
    if n == 2:  # m = min(2, n - 1) = 1: the line through both nodes
        return ys[0] + (ys[1] - ys[0]) * (x - xs[0]) / (xs[1] - xs[0])
    ix = last_node_at_or_below(xs, x)
    if 2 <= ix <= n - 2:
        left = _quadratic(xs, ys, (ix - 2, ix - 1, ix), x)
        right = _quadratic(xs, ys, (ix - 1, ix, ix + 1), x)
        return 0.5 * (left + right)
    if ix <= 1:
        return _quadratic(xs, ys, (0, 1, 2), x)
    return _quadratic(xs, ys, (n - 3, n - 2, n - 1), x)


def linear_interpolation(xs: list[float], ys: list[float], x: float) -> float:
    """Numerics::LinearInterpolation: between the last node <= x and the next one."""
    ix = last_node_at_or_below(xs, x)
    if ix >= len(xs):
        return ys[-1]
    x0, x1, y0, y1 = xs[ix - 1], xs[ix], ys[ix - 1], ys[ix]
    if x1 - x0 < 1e-10:
        return y0
    f = (x - x0) / (x1 - x0)
    return y0 * (1.0 - f) + f * y1


def extrapolate(xs: list[float], ys: list[float], x: float, method: str, side: str) -> float:
    """Outside the grid, as Medium::Interpolate1D (non-log values) writes it: constant (the end value), linear or
    exponential through the two end nodes; the end value when the two end fields coincide."""
    n = len(xs)
    if side == "low":
        if xs[0] >= xs[1] or method == "constant":
            return ys[0]
        if method == "linear":
            extr4 = (ys[1] - ys[0]) / (xs[1] - xs[0])
            return ys[0] + extr4 * (x - xs[0])
        if method == "exponential":
            extr4 = math.log(ys[1] / ys[0]) / (xs[1] - xs[0])
            extr3 = math.log(ys[0]) - extr4 * xs[0]
            return math.exp(min(50.0, extr3 + extr4 * x))
    else:
        if xs[n - 1] <= xs[n - 2] or method == "constant":
            return ys[n - 1]
        if method == "linear":
            extr2 = (ys[n - 1] - ys[n - 2]) / (xs[n - 1] - xs[n - 2])
            return ys[n - 1] + extr2 * (x - xs[n - 1])
        if method == "exponential":
            extr2 = math.log(ys[n - 1] / ys[n - 2]) / (xs[n - 1] - xs[n - 2])
            extr1 = math.log(ys[n - 1]) - extr2 * xs[n - 1]
            return math.exp(min(50.0, extr1 + extr2 * x))
    raise ValueError(f"unknown extrapolation method {method!r}")


def reference_velocity(xs: list[float], ys: list[float], x: float, settings: dict) -> tuple[float, str]:
    """(reference |v| in cm/ns, region): region node, interior, below or above."""
    if x < xs[0]:
        return extrapolate(xs, ys, x, settings["low"], "low"), "below"
    if x > xs[-1]:
        return extrapolate(xs, ys, x, settings["high"], "high"), "above"
    if x in xs:
        return ys[xs.index(x)], "node"
    if settings["order"] == 1:
        return linear_interpolation(xs, ys, x), "interior"
    return divdif_order2(xs, ys, x), "interior"


def within_tolerance(value: float, reference: float, kind: str) -> bool:
    """Check 1 (node): |value - t| <= 4 ulp(t); checks 3 and 4: |value - r| <= 1e-12 |r| + 4 ulp(r)."""
    bound = ULPS * math.ulp(reference) + (0.0 if kind == "node" else RELATIVE * abs(reference))
    return math.isfinite(value) and abs(value - reference) <= bound


# ---------------------------------------------------------------- capability, check, build_spec

def capabilities() -> dict:
    descriptor = json.loads(DESCRIPTOR_FILE.read_text(encoding="utf-8"))
    return {descriptor["id"]: descriptor}


def code_files(capability: dict) -> list:
    return [("detsim_backend_garfield.py", Path(__file__).resolve()),
            ("garfield/gas_table_query.capability.json", DESCRIPTOR_FILE),
            ("garfield/gas_table_query.py", SCRIPT_FILE)]


def _issue(code: str, kind: str, message: str, location: str, **details) -> dict:
    return dict({"code": code, "kind": kind, "message": message, "location": location}, **details)


def _value(quantity: dict) -> Decimal:
    return Decimal(quantity["value"])


def node_coverage(queried_fields: list[float], fields: list[float]) -> list[str]:
    """What check 1 lacks: a query exactly at the first node, at the last node, at an interior node (doubles)."""
    found = set(queried_fields)
    missing = [] if fields[0] in found else ["the first node"]
    missing += [] if fields[-1] in found else ["the last node"]
    missing += [] if found & set(fields[1:-1]) else ["an interior node"]
    return missing


def table_input(task: dict, input_manifest: list) -> dict | None:
    items = [item for item in input_manifest if item["role"] == task["parameters"]["table_role"]]
    return items[0] if len(items) == 1 else None


def load_table(path: Path, sha256: str) -> dict:
    """Read and parse the table, after checking its bytes against the recorded SHA-256."""
    raw = Path(path).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != sha256:
        raise GasTableError("hash", f"the table's SHA-256 {actual} is not the recorded {sha256}")
    return parse_gas_table(raw)


def valid_range(table: dict) -> dict:
    fields = node_fields(table)
    return {"min": repr(fields[0]), "max": repr(fields[-1]), "unit": "V/cm"}


def table_settings(table: dict) -> dict:
    """The velocity entries (index 0) of the footer: interpolation order and extrapolation methods."""
    return {"order": table["interpolation"][0], "low": EXTRAPOLATION_CODES.get(table["extrapolation_low"][0]),
            "high": EXTRAPOLATION_CODES.get(table["extrapolation_high"][0])}


def check(task: dict, capability: dict, input_manifest: list, input_files: dict | None = None) -> list:
    """Semantic checks of a GF-QUERY task against its table (TASK.md 12.3, 11.3); [] when the task may run."""
    p = task["parameters"]
    item = table_input(task, input_manifest)
    if item is None:
        return [_issue("input-role-missing", "rejected", f"exactly one input of role {p['table_role']!r} (the gas "
                       "table) is needed", "$.inputs")]
    issues = []
    units = [("$.parameters.magnetic_field", p["magnetic_field"], "T"), ("$.parameters.temperature",
             p["temperature"], "K"), ("$.parameters.pressure", p["pressure"], "Torr")]
    units += [(f"$.parameters.query_fields[{i}]", q, "V/cm") for i, q in enumerate(p["query_fields"])]
    for where, quantity, unit in units:
        if quantity["unit"] != unit:
            issues.append(_issue("unit-unsupported", "rejected", f"{where} must be in {unit}, not "
                                 f"{quantity['unit']!r}", where))
    if issues:
        return issues
    if _value(p["magnetic_field"]) != 0:
        return [_issue("field-unsupported", "refused", "capability 1.0.0 queries B = 0 only (1D tables)",
                       "$.parameters.magnetic_field")]
    bad = [i for i, q in enumerate(p["query_fields"]) if _value(q) <= 0]
    if bad:
        return [_issue("field-not-positive", "rejected", f"query fields must be positive (E along +x); index {bad[0]}",
                       f"$.parameters.query_fields[{bad[0]}]")]
    if input_files is None or item["path"] not in input_files:
        return [_issue("table-unreadable", "rejected", "the shared layer did not pass the table file to check",
                       "$.inputs")]
    try:
        table = load_table(input_files[item["path"]], item["sha256"])
    except OSError as err:
        return [_issue("table-unreadable", "rejected", f"cannot read the table: {err.strerror or err}", "$.inputs")]
    except GasTableError as err:
        if err.code == "hash":
            return [_issue("input-changed", "refused", str(err), "$.inputs", path=item["path"])]
        return [_issue("table-format", "rejected", f"not a gas table in the pinned storage form ({err.code}): {err}",
                       "$.inputs", path=item["path"])]
    if table["dimension"] != "F" or table["n_angles"] != 1 or table["n_b"] != 1:
        return [_issue("table-not-1d", "refused", f"the table has Dimension : {table['dimension']} with "
                       f"{table['n_angles']} angle(s) and {table['n_b']} B field(s); capability 1.0.0 accepts only "
                       "1D tables (Dimension : F, one angle, one B)", "$.inputs", path=item["path"])]
    if table["gasok"][0] != "T":
        return [_issue("quantity-missing", "refused", "the table has no electron drift velocity along E (GASOK bit "
                       "1 is F)", "$.inputs", path=item["path"])]
    if "pressure_torr" not in table or "temperature_k" not in table:
        return [_issue("table-format", "rejected", "the footer states no PGAS or TGAS", "$.inputs")]
    fields = node_fields(table)
    if any(b >= a for a, b in zip(fields[1:], fields)) or len(fields) < 2:
        return [_issue("table-format", "rejected", "the E grid is not strictly increasing with two nodes or more",
                       "$.inputs")]
    mismatched = [(name, given, table[key]) for name, key, given in (("temperature", "temperature_k",
                                                                      p["temperature"]),
                                                                     ("pressure", "pressure_torr", p["pressure"]))
                  if _value(given) != Decimal(table[key])]
    if mismatched:
        return [_issue("condition-mismatch", "refused", "; ".join(
            f"{name} {given['value']} {given['unit']} differs from the table's {table_value!r}"
            for name, given, table_value in mismatched) + " (only the table's temperature and pressure are allowed)",
            "$.parameters." + mismatched[0][0], table_temperature_k=repr(table["temperature_k"]),
            table_pressure_torr=repr(table["pressure_torr"]))]
    settings = table_settings(table)
    if settings != p["interpolation"]:
        return [_issue("interpolation-mismatch", "refused", f"the task's interpolation {p['interpolation']} is not "
                       f"the table footer's velocity entries {settings} (Interp, L Extr, H Extr)",
                       "$.parameters.interpolation", table_interpolation=settings)]
    velocities = node_velocities(table)
    for side, ends in (("low", velocities[:2]), ("high", velocities[-2:])):
        if settings[side] == "exponential" and min(ends) <= 0:
            return [_issue("extrapolation-undefined", "refused", f"the table's {side} extrapolation is exponential "
                           f"but its two end velocities {ends} are not both positive (log undefined)", "$.inputs")]
    uncovered = node_coverage([float(q["value"]) for q in p["query_fields"]], fields)
    if uncovered:
        return [_issue("node-coverage", "rejected", "the query fields must include the first node, the last node "
                       f"and at least one interior node of the table (check 1); missing: {', '.join(uncovered)}",
                       "$.parameters.query_fields", first_node=repr(fields[0]), last_node=repr(fields[-1]))]
    if EXAMPLE_TABLES.get(item["sha256"]) and NOTE_EXAMPLE not in task["objective"]:
        return [_issue("note-missing", "rejected", f"this table is used under H0 #13 ({EXAMPLE_TABLES[item['sha256']]}"
                       f"): the objective must carry the note {NOTE_EXAMPLE!r}", "$.objective")]
    outside = [i for i, q in enumerate(p["query_fields"])
               if not fields[0] <= float(q["value"]) <= fields[-1]]
    if outside and not p.get("allow_outside_validated_range", False):
        return [_issue("out-of-domain", "refused", f"{len(outside)} query field(s) outside the table's range "
                       f"[{fields[0]!r}, {fields[-1]!r}] V/cm; set allow_outside_validated_range "
                       "(--allow-outside-validated-range) to use Garfield++'s extrapolation, labelled "
                       "outside-validated-range", f"$.parameters.query_fields[{outside[0]}]",
                       valid_range=valid_range(table), outside_indices=outside)]
    return []


def _rendered(path: str, raw: bytes) -> dict:
    return {"path": path, "encoding": "base64", "content": base64.b64encode(raw).decode("ascii"),
            "sha256": hashlib.sha256(raw).hexdigest()}


def query_document(task: dict, input_manifest: list) -> dict:
    p = task["parameters"]
    item = table_input(task, input_manifest)
    return {"format": QUERY_FORMAT, "capability": CAPABILITY_ID, "garfield_commit": PINNED_COMMIT,
            "table": "INPUT_ROOT/" + item["path"], "table_sha256": item["sha256"],
            "note": NOTE_EXAMPLE if item["sha256"] in EXAMPLE_TABLES else None,
            "points": [{"index": i, "field_v_per_cm": q["value"]} for i, q in enumerate(p["query_fields"])],
            "magnetic_field_t": p["magnetic_field"]["value"], "temperature_k": p["temperature"]["value"],
            "pressure_torr": p["pressure"]["value"], "interpolation": dict(p["interpolation"]),
            "allow_outside_validated_range": bool(p.get("allow_outside_validated_range", False))}


def build_spec(task: dict, capability: dict, input_manifest: list, environment: dict, profile: dict) -> dict:
    """The ExecutionSpec: ENV_ROOT/bin/python3 running the rendered query script on the rendered query."""
    commit = environment["identity"].get("garfield_commit")
    if commit != PINNED_COMMIT:
        raise _error("refused", "environment-not-pinned", f"the environment record names Garfield++ commit "
                     f"{commit!r}; capability {CAPABILITY_ID} 1.0.0 is pinned to {PINNED_COMMIT}",
                     "$.environment_ref")
    item = table_input(task, input_manifest)
    query = json.dumps(query_document(task, input_manifest), sort_keys=True, indent=1, ensure_ascii=True) + "\n"
    variables = environment["variables"]
    return {
        "argv": ["ENV_ROOT/bin/python3", "-B", "-s", SCRIPT_PATH, "--query", QUERY_PATH, "--table",
                 "INPUT_ROOT/" + item["path"], "--garfield-lib", "ENV_ROOT/garfield/lib", "--out", OUTPUT_PATH],
        "environment": {name: variables[name] for name in sorted(variables) if name in ALLOWLIST},
        "files": [_rendered(SCRIPT_PATH, SCRIPT_FILE.read_bytes()), _rendered(QUERY_PATH, query.encode("ascii"))],
        "expected_outputs": [OUTPUT_PATH],
        "timeout_s": task["budget"]["timeout_s"],
    }


# ---------------------------------------------------------------- collect and observables

def _local(attempt_dir: Path, logical: str) -> Path:
    """A logical ATTEMPT_ROOT/... or INPUT_ROOT/... path in the attempt folder (INPUT_ROOT = ATTEMPT_ROOT/input)."""
    root, *rest = logical.split("/")
    base = Path(attempt_dir) / "input" if root == "INPUT_ROOT" else Path(attempt_dir)
    return base.joinpath(*rest)


def query_from_spec(spec: dict) -> dict:
    item = next(f for f in spec["files"] if f["path"] == QUERY_PATH)
    return json.loads(base64.b64decode(item["content"]).decode("ascii"))


def parse_output(text: str) -> dict:
    """The query script's raw output; ValueError when malformed."""
    lines = text.splitlines()
    if not lines or lines[0] != "format " + OUTPUT_FORMAT:
        raise ValueError("the first line is not the output format")
    out: dict = {"points": {}, "end": None}
    for number, line in enumerate(lines[1:], start=2):
        words = line.split()
        if words[:1] == ["pressure_torr"] and len(words) == 2:
            out["pressure_torr"] = float(words[1])
        elif words[:1] == ["temperature_k"] and len(words) == 2:
            out["temperature_k"] = float(words[1])
        elif words[:1] == ["interpolation"] and len(words) == 4:
            out["interpolation"] = {"order": int(words[1]), "low": words[2], "high": words[3]}
        elif words[:1] == ["point"] and len(words) == 7:
            index = int(words[1])
            if index in out["points"]:
                raise ValueError(f"line {number}: point {index} twice")
            out["points"][index] = {"field": words[2], "strings": words[3:7],
                                    "values": [float(w) for w in words[3:7]]}
        elif words[:1] == ["end"] and len(words) == 2:
            out["end"] = int(words[1])
        else:
            raise ValueError(f"line {number}: unexpected {line[:60]!r}")
    return out


def classify(query: dict, table: dict) -> list[dict]:
    """Per query point: index, field (double), reference velocity and region from the reimplementation."""
    xs, ys = node_fields(table), node_velocities(table)
    out = []
    for point in query["points"]:
        x = float(point["field_v_per_cm"])
        reference, region = reference_velocity(xs, ys, x, query["interpolation"])
        out.append({"index": point["index"], "field": point["field_v_per_cm"], "x": x, "reference": reference,
                    "region": region})
    return out


def evaluate(query: dict, table: dict, queried: dict) -> list[dict]:
    """Checks 1-4 of card GF-QUERY as detsim-completeness/1 evidence (pass / fail; omitted when not applicable)."""
    points = classify(query, table)
    regions: dict = {"node": [], "interior": [], "outside": []}
    sign_failures, failures = [], {"node": [], "interior": [], "outside": []}
    for point in points:
        got = queried["points"].get(point["index"])
        if got is None:
            continue
        vx, vy, vz, magnitude = got["values"]
        if not (vx < 0 and vy == 0 and vz == 0):
            sign_failures.append(point["index"])
        group = "outside" if point["region"] in ("below", "above") else point["region"]
        regions[group].append(point["index"])
        kind = "node" if group == "node" else "interpolated"
        if not (within_tolerance(magnitude, point["reference"], kind) and within_tolerance(abs(vx), point["reference"],
                                                                                          kind)):
            failures[group].append(point["index"])
        if group == "node" and not (vy == 0 and vz == 0):
            failures[group].append(point["index"])
    evidence = []
    names = {"node": ("check-1-nodes", "|v| within 4 ulp of the stored value x 1e-3, vy = vz = 0"),
             "interior": ("check-3-interior", "|v| within 1e-12 |r| + 4 ulp(r) of the reimplemented order-"
                                              f"{query['interpolation']['order']} interpolation"),
             "outside": ("check-4-outside", f"|v| within 1e-12 |r| + 4 ulp(r) of the reimplemented "
                                            f"{query['interpolation']['low']} / {query['interpolation']['high']} "
                                            "extrapolation")}
    for group in ("node", "interior", "outside"):
        if regions[group]:
            name, rule = names[group]
            bad = sorted(set(failures[group]))
            evidence.append({"check": name, "result": "fail" if bad else "pass",
                             "detail": f"{len(regions[group])} point(s) {regions[group]}; {rule}"
                                       + (f"; failed at {bad}" if bad else "")})
        if group == "node":
            evidence.append({"check": "check-2-sign", "result": "fail" if sign_failures else "pass",
                             "detail": f"vx < 0 and vy = vz = 0 at all {len(queried['points'])} point(s)"
                                       + (f"; failed at {sign_failures}" if sign_failures else "")})
    if regions["outside"] and not query["allow_outside_validated_range"]:
        evidence.append({"check": "domain", "result": "fail", "detail": f"points {regions['outside']} outside the "
                                                                        "range without allow_outside_validated_range"})
    return evidence


def rows_for(query: dict, table: dict, queried: dict, source_sha256: str) -> list[dict]:
    """detsim-observables/1 rows: per point the field (V/cm) and vx, vy, vz, |v| (cm/ns) as normalized decimals."""
    rows = []
    for point in classify(query, table):
        got = queried["points"][point["index"]]
        labels = ["unvalidated"] + (["outside-validated-range"] if point["region"] in ("below", "above") else [])
        values = [("electric_field", "V/cm", point["field"])] + [
            (name, "cm/ns", text) for name, text in zip(VELOCITY_QUANTITIES, got["strings"])]
        for quantity, unit, text in values:
            rows.append({"quantity": quantity, "unit": unit, "value": canonical.normalize_decimal(text),
                         "uncertainty_type": "none", "point_kind": "query_point", "point": point["index"],
                         "labels": list(labels), "source_sha256": source_sha256})
            if query.get("note"):
                rows[-1]["note"] = query["note"]
    return rows


def check_rows(rows: list[dict], query: dict, table: dict) -> list[str]:
    """Problems of an observables table: five rows per point with the right units, and outside-validated-range
    exactly on the rows of points outside the table's range."""
    problems = []
    expected_units = dict({"electric_field": "V/cm"}, **{q: "cm/ns" for q in VELOCITY_QUANTITIES})
    by_point: dict = {}
    for row in rows:
        by_point.setdefault(row.get("point"), []).append(row)
        if expected_units.get(row.get("quantity")) != row.get("unit"):
            problems.append(f"point {row.get('point')} {row.get('quantity')}: unit {row.get('unit')!r}")
    for point in classify(query, table):
        found = by_point.get(point["index"], [])
        if sorted(r["quantity"] for r in found) != sorted(expected_units):
            problems.append(f"point {point['index']}: rows {sorted(r.get('quantity') for r in found)}")
        outside = point["region"] in ("below", "above")
        for row in found:
            if row.get("note") != query.get("note"):
                problems.append(f"point {point['index']} {row.get('quantity')}: note {row.get('note')!r}, expected "
                                f"{query.get('note')!r}")
            if ("outside-validated-range" in row.get("labels", [])) != outside:
                problems.append(f"point {point['index']} {row.get('quantity')}: outside-validated-range label "
                                f"{'missing' if outside else 'on an in-range row'}")
    return problems


def _read_attempt(attempt_dir: Path, spec: dict):
    """(query, table, output, raw bytes) of an attempt; raises ValueError / GasTableError / OSError."""
    query = query_from_spec(spec)
    table = load_table(_local(attempt_dir, query["table"]), query["table_sha256"])
    raw = _local(attempt_dir, OUTPUT_PATH).read_bytes()
    return query, table, parse_output(raw.decode("ascii")), raw


def script_status(attempt_dir: Path) -> dict | None:
    """The query script's JSON answer: the last stdout line that is a JSON object with a status (R-07 (a))."""
    try:
        lines = (Path(attempt_dir) / "logs" / "stdout.txt").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        if line.startswith("{"):
            try:
                answer = json.loads(line)
            except ValueError:
                continue
            if isinstance(answer, dict) and isinstance(answer.get("status"), str):
                return answer
    return None


def status_evidence(answer: dict | None) -> dict:
    """missing-dependency -> the shared layer's dependency check (failed, missing-dependency; TASK.md 11.3)."""
    if answer is None:
        return {"check": "script-status", "result": "fail", "detail": "no JSON status line on the script's stdout"}
    text = f"{answer.get('status')}" + (f" ({answer.get('error_code')}: {str(answer.get('message', ''))[:200]})"
                                        if answer.get("status") != "ok" else "")
    if answer["status"] == "missing-dependency":
        return {"check": "dependency", "result": "fail", "detail": "the query script reported " + text}
    return {"check": "script-status", "result": "pass" if answer["status"] == "ok" else "fail",
            "detail": "the query script reported " + text}


def collect(attempt_dir: Path, spec: dict) -> dict:
    missing = [p for p in spec["expected_outputs"] if not _local(attempt_dir, p).is_file()]
    doc = {"schema": "detsim-completeness/1", "state": "complete", "missing_outputs": missing, "evidence": [
        status_evidence(script_status(attempt_dir)),
        {"check": "expected-outputs", "result": "fail" if missing else "pass",
         "detail": f"{len(spec['expected_outputs']) - len(missing)} of {len(spec['expected_outputs'])} present"}]}
    if missing:
        return dict(doc, state="partial")
    try:
        query, table, queried, raw = _read_attempt(attempt_dir, spec)
    except OSError as err:  # never a host path in the evidence
        doc["evidence"].append({"check": "raw-format", "result": "fail",
                                "detail": f"{type(err).__name__}: {err.strerror or 'unreadable'} "
                                          f"({Path(err.filename or '').name or 'attempt file'})"})
        return dict(doc, state="invalid")
    except (ValueError, UnicodeDecodeError, KeyError) as err:
        doc["evidence"].append({"check": "raw-format", "result": "fail", "detail": f"{type(err).__name__}: {err}"})
        return dict(doc, state="invalid")
    evidence = doc["evidence"]
    evidence.append({"check": "table-identity", "result": "pass", "detail": f"input copy SHA-256 "
                     f"{query['table_sha256']} as planned; independent parser: {len(table['e_over_p'])} E nodes, "
                     f"record length {table['record_length']}" + (f"; {query['note']}" if query.get("note") else "")})
    conditions = (queried.get("pressure_torr") == float(query["pressure_torr"])
                  and queried.get("temperature_k") == float(query["temperature_k"])
                  and queried.get("pressure_torr") == table["pressure_torr"]
                  and queried.get("temperature_k") == table["temperature_k"])
    evidence.append({"check": "conditions", "result": "pass" if conditions else "fail",
                     "detail": f"medium {queried.get('pressure_torr')!r} Torr, {queried.get('temperature_k')!r} K after "
                               f"LoadGasFile; table {table['pressure_torr']!r} Torr, {table['temperature_k']!r} K"})
    settings_ok = queried.get("interpolation") == query["interpolation"]
    evidence.append({"check": "interpolation-settings", "result": "pass" if settings_ok else "fail",
                     "detail": f"requested settings {queried.get('interpolation')} as echoed by the script, planned "
                               f"{query['interpolation']} (the library does not report the settings it uses)"})
    wanted = {p["index"]: p["field_v_per_cm"] for p in query["points"]}
    absent = sorted(set(wanted) - set(queried["points"]))
    extra = sorted(set(queried["points"]) - set(wanted))
    mislabelled = sorted(i for i in set(wanted) & set(queried["points"]) if queried["points"][i]["field"] != wanted[i])
    complete = not absent and not extra and not mislabelled and queried["end"] == len(wanted)
    evidence.append({"check": "query-points", "result": "pass" if complete else "fail",
                     "detail": f"{len(queried['points'])} of {len(wanted)} point(s); end line {queried['end']}"
                               + (f"; missing {absent}" if absent else "") + (f"; unexpected {extra}" if extra else "")
                               + (f"; field differs at {mislabelled}" if mislabelled else "")})
    uncovered = node_coverage([float(p["field_v_per_cm"]) for p in query["points"] if p["index"] in queried["points"]],
                              node_fields(table))
    evidence.append({"check": "node-coverage", "result": "fail" if uncovered else "pass",
                     "detail": ("missing " + ", ".join(uncovered)) if uncovered else "query points at the first node, "
                               "the last node and an interior node of the table"})
    evidence += evaluate(query, table, queried)
    if complete:
        try:
            problems = check_rows(rows_for(query, table, queried, hashlib.sha256(raw).hexdigest()), query, table)
        except canonical.CanonicalError as err:
            problems = [f"a value is not a decimal: {err}"]
        evidence.append({"check": "rows", "result": "fail" if problems else "pass",
                         "detail": "; ".join(problems[:5]) or "five rows per point, units V/cm and cm/ns, "
                                                              "outside-validated-range exactly on outside points"})
    failed = [e for e in evidence if e["result"] != "pass"]
    state = "complete" if not failed else "partial" if absent or queried["end"] is None or uncovered else "invalid"
    return dict(doc, state=state)


def observables(attempt_dir: Path, spec: dict) -> dict:
    query, table, queried, raw = _read_attempt(attempt_dir, spec)
    return {"schema": "detsim-observables/1", "rows": rows_for(query, table, queried, hashlib.sha256(raw).hexdigest())}


# ---------------------------------------------------------------- environment probe (check --probe)

ALLOWLIST = ("PYTHONPATH", "DYLD_LIBRARY_PATH", "LD_LIBRARY_PATH")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _missing(what: list[str], env_root: Path):
    return _error("missing-dependency", "missing-dependency", "the Garfield++ environment root lacks: "
                  + "; ".join(what), "--env-root", missing=what)


def _define(text: str, name: str) -> str | None:
    match = re.search(r"#define\s+" + name + r"\s+(\"[^\"]*\"|\d+)", text)
    return match.group(1).strip('"') if match else None


def probe(env_root: Path) -> dict:
    """{identity, variables, facts} of a view folder: bin/python3, root -> a ROOT prefix with its Python bindings,
    garfield -> a Garfield++ install, and detsim-garfield-build.json (the commit and the library's SHA-256). Reads
    files only; the identity is content-based (commit, library hashes, versions), never the path."""
    env_root = Path(env_root)
    suffix = ".dylib" if sys.platform == "darwin" else ".so"
    missing = []
    python = env_root / "bin" / "python3"
    python_version = None
    if not python.is_file():
        missing.append("bin/python3 (the Python of ROOT's bindings)")
    else:
        real = Path(os.path.realpath(python))
        headers = sorted(real.parent.parent.glob("include/python3*/patchlevel.h"))
        if headers:
            python_version = _define(headers[0].read_text(encoding="utf-8", errors="replace"), "PY_VERSION")
        if python_version is None:
            missing.append("the Python version (include/python3.*/patchlevel.h next to bin/python3)")
    root_lib = env_root / "root" / "lib" / "root"
    needed_root = [root_lib / "ROOT" / "__init__.py"] + [
        next((root_lib / (name + s) for s in (".so", suffix) if (root_lib / (name + s)).is_file()), root_lib / name)
        for name in ("libCore", "libCPyCppyy")]  # ROOT names its libraries .so on macOS too
    missing += [f"root/lib/root/{p.name} (ROOT's Python bindings)" for p in needed_root if not p.is_file()]
    version_header = env_root / "root" / "include" / "root" / "ROOT" / "RVersion.hxx"
    root_version = None
    if version_header.is_file():
        text = version_header.read_text(encoding="utf-8", errors="replace")
        parts = [_define(text, f"ROOT_VERSION_{k}") for k in ("MAJOR", "MINOR", "PATCH")]
        if None not in parts:
            root_version = f"{int(parts[0])}.{int(parts[1]):02d}.{int(parts[2]):02d}"
    if root_version is None:
        missing.append("root/include/root/ROOT/RVersion.hxx (the ROOT version)")
    garfield_lib = env_root / "garfield" / "lib"
    missing += [f"garfield/lib/{name}{suffix}" for name in LIBRARIES if not (garfield_lib / (name + suffix)).is_file()]
    if not (garfield_lib / "libGarfield_rdict.pcm").is_file():
        missing.append("garfield/lib/libGarfield_rdict.pcm (the Garfield++ dictionary)")
    bindings = sorted(garfield_lib.glob("python3*/site-packages/Garfield/__init__.py"))
    if not bindings:
        missing.append("garfield/lib/python3.*/site-packages/Garfield (the Garfield++ Python bindings)")
    elif python_version is not None and bindings[0].parts[-4] != "python" + ".".join(python_version.split(".")[:2]):
        missing.append(f"Garfield++ bindings for Python {python_version} (found {bindings[0].parts[-4]})")
    if missing:
        raise _missing(missing, env_root)
    record_path = env_root / BUILD_RECORD
    if not record_path.is_file():
        raise _error("refused", "environment-unpinned", f"{BUILD_RECORD} is missing from the environment root: the "
                     "Garfield++ commit of this install is not recorded", "--env-root")
    try:
        record = canonical.load_json_strict(record_path.read_bytes())
    except canonical.CanonicalError as err:
        raise _error("refused", "environment-unpinned", f"{BUILD_RECORD} is not strict JSON: {err}",
                     "--env-root") from None
    library = Path(os.path.realpath(garfield_lib / ("libGarfield" + suffix)))
    library_sha = _sha256(library)
    if not isinstance(record, dict) or record.get("format") != BUILD_RECORD_FORMAT \
            or not re.fullmatch(r"[0-9a-f]{40}", str(record.get("garfield_commit"))):
        raise _error("refused", "environment-unpinned", f"{BUILD_RECORD} is not a {BUILD_RECORD_FORMAT} record "
                     "with a 40-hex garfield_commit", "--env-root")
    if record.get("library_sha256") != library_sha:
        raise _error("refused", "build-record-mismatch", f"{BUILD_RECORD} names library SHA-256 "
                     f"{record.get('library_sha256')}, the installed libGarfield has {library_sha}", "--env-root")
    options = record.get("build_options") if isinstance(record.get("build_options"), dict) else {}
    loaded = {name: _sha256(Path(os.path.realpath(garfield_lib / (name + suffix)))) for name in LIBRARIES}
    loaded.update({p.name.split(".")[0]: _sha256(Path(os.path.realpath(p))) for p in needed_root[1:]})
    identity = {"kind": "garfieldpp-view", "garfield_commit": record["garfield_commit"],
                "library_sha256": dict(sorted(loaded.items())),
                "root_version": root_version, "python_version": python_version,
                "build_options": {str(k): str(v) for k, v in sorted(options.items())},
                "platform": f"{sys.platform}-{platform.machine()}"}
    library_variable = "DYLD_LIBRARY_PATH" if sys.platform == "darwin" else "LD_LIBRARY_PATH"
    variables = {"PYTHONPATH": "ENV_ROOT/root/lib/root", library_variable: "ENV_ROOT/garfield/lib"}
    facts = {"backend": NAME, "garfield_describe": str(record.get("git_describe", "")),
             "library": library.name, "query_script_sha256": _sha256(SCRIPT_FILE),
             "bindings": str(bindings[0].parent.relative_to(env_root / "garfield"))}
    return {"identity": identity, "variables": variables, "facts": facts}
