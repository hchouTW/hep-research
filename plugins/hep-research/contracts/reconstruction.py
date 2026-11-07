"""Reconstruction semantics sidecars (detector reconstruction plan, docs/dev/detector-reconstruction/contract-map.md).

The closed schemas of the plugin cannot hold reconstruction semantics, so these sidecars hold them beside the old
recipes, tool contracts and responses, which keep their meaning. Every function works on parsed documents; nothing here
reads a file, runs a backend or solves a problem. A passing sidecar shows that the stated semantics are expressible and
consistent, never instrument quality or a backend's correctness (plan Section 12.1).

Reader rule (K13): read_sidecar stops at an unknown format or an unknown required extension, before reading anything
else in the document; an unknown optional extension is ignored and reported as a warning. Every other public function
takes whole documents and reads them the same way, so it acts only on what read_sidecar accepts (contracts.sidecar_reader).
read_sidecar and the functions that return a report return one for malformed input too; the others return a safe refusal,
such as False, None or an empty list.
"""
from __future__ import annotations

import math
from collections import Counter
from fractions import Fraction

import numpy

from contracts import conditions
from contracts.recipe_semantics import canonical_sha256
from contracts.schema import Report, load_schema, validate
from contracts.sidecar_reader import KNOWN_EXTENSIONS, read_document, reader_path

TOOL_MAPPING_VERSIONS = frozenset({"1"})
NOT_EVIDENCE = frozenset({"file-name", "array-shape", "model-confidence"})
CONNECTED_SEMANTICS = (("kind", "quantity_kind"), ("unit", "unit"), ("basis", "basis"), ("reference_hypothesis", "hypothesis"),
                       ("observation_level", "observation_level"), ("period", "period"))
DATA_SIDE_ROLES = ("reconstruction-input", "conditions")  # Section 8.4, check 3: these do not depend on truth
# K05 keeps the energy kinds apart, and W6 asks for an energy observable before a per-event energy. Reading: energy-loss is a
# specific energy per path length (dE/dx) of a track, formed from calibrated deposits and a length, so it is not itself an
# energy a sensor delivers per event and stays outside this set; a method that delivers it per event names its energy kind.
ENERGY_OBSERVABLES = frozenset({"energy-deposited", "energy-visible", "energy-calibrated", "energy-recoil", "energy-incident"})
# Plan Section 12 and W2: comparators are fixed before execution; Section 14.1: numerical reproducibility fixes quantities,
# matching rules and tolerances. A rounded sum is wrong by a small multiple of the rounding unit times the sum of its terms'
# sizes, so every comparison here is relative to that sum and follows signal, weights and design. It bounds a residual, not
# the error of a parameter: on an ill-conditioned model a wrong value can leave a small residual. The ceiling, near 4.5e6
# rounding units, leaves room for a conditioned fit and buys no agreement. The schema floors a record's comparator at 1e-15,
# near nine rounding units: below the rounding of its own terms a tolerance compares nothing and would buy a rank, which
# Section 9.5 refuses (no fabricated identifiability). Neither bound is a physics threshold.
RELATIVE_TOLERANCE_CEILING = 1e-9
RECONSTRUCTION_ONLY_KEYS = ("sampling", "retention", "conditions_used", "required_extensions", "optional_extensions", "extensions")
REDUCED_LEVELS = ("raw", "waveform", "conditions_snapshot")  # R34: recalibration starts from these
NOT_RECIPE_IDENTITY = ("status", "evidence_ref", "runtime_evidence")  # what evidence itself changes
NOT_BINDING_IDENTITY = ("request",)  # Section 8.4, check 6: a request inside the tested domain keeps its evidence
NOT_ROUTINE_STAGES = ("artificial-witness", "backend-smoke")  # Section 12.1: no automatic promotion between levels
UNIT_SCALES = {"ps": ("time", 1e-12), "ns": ("time", 1e-9), "us": ("time", 1e-6), "µs": ("time", 1e-6), "μs": ("time", 1e-6),  # micro sign and Greek mu
               "ms": ("time", 1e-3), "s": ("time", 1.0), "min": ("time", 60.0), "h": ("time", 3600.0), "d": ("time", 86400.0),  # no yr: a year needs a choice
               "Hz": ("frequency", 1.0), "kHz": ("frequency", 1e3), "MHz": ("frequency", 1e6), "GHz": ("frequency", 1e9)}
SEPARATE_SAMPLE_ROLES = frozenset({"training-calibration", "validation"})  # K08: sample roles stay separate


def _in_base_unit(measure: dict) -> tuple | None:
    """(dimension, value in the base unit), or None for a unit this reader cannot convert."""
    known = UNIT_SCALES.get(measure["unit"])
    return (known[0], measure["value"] * known[1]) if known else None


def _same_measure(first: dict | None, second: dict | None) -> bool:
    """One measure in two units is one measure (K05: meaning, not spelling); a unit that cannot be converted compares as text."""
    if first is None or second is None or first["unit"] == second["unit"]:
        return first == second
    converted = _in_base_unit(first), _in_base_unit(second)
    return None not in converted and converted[0][0] == converted[1][0] and math.isclose(converted[0][1], converted[1][1], rel_tol=1e-12)


def _as_fractions(matrix) -> list[list[Fraction]]:
    return [[Fraction(value) for value in row] for row in matrix]


def _row_reduced(matrix) -> tuple[list[list[Fraction]], int]:
    """Exact row reduction: the rank of the stored numbers as they stand, used where no comparator is declared."""
    rows, rank = _as_fractions(matrix), 0
    for column in range(len(rows[0]) if rows else 0):
        pivot = next((index for index in range(rank, len(rows)) if rows[index][column]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        rows[rank] = [value / rows[rank][column] for value in rows[rank]]
        for index, row in enumerate(rows):
            if index != rank and row[column]:
                rows[index] = [value - row[column] * lead for value, lead in zip(row, rows[rank])]
        rank += 1
    return rows, rank


def matrix_rank(matrix, relative_tolerance: float = 0) -> int:
    """The exact rank of the stored numbers, or with a tolerance the numerical rank (see _numerical_rank)."""
    return _numerical_rank(matrix, relative_tolerance) if relative_tolerance else _row_reduced(matrix)[1]


def _unit_columns(matrix) -> tuple[numpy.ndarray, numpy.ndarray]:
    """The matrix with each column scaled to unit norm, and the norms (1 for a zero column, which stays as it is). A
    parameter's unit scales its column and nothing else, so what is judged on these columns does not depend on the units
    in which the parameters are stated (K05: meaning, not spelling). Rows in different units are not scaled here: a W2
    model whitens by its noise covariance, which this reader does not do. A column norm overflows or underflows beyond
    about 1e154 and 1e-162, so a column of such entries reads as null; no honest record holds them."""
    stored = numpy.array(matrix, dtype=float)
    if stored.ndim != 2 or 0 in stored.shape:
        return numpy.zeros((0, 0)), numpy.ones(0)
    norms = numpy.linalg.norm(stored, axis=0)
    norms = numpy.where(norms > 0, norms, 1.0)
    return stored / norms, norms


def _scaled_rank(scaled: numpy.ndarray, relative_tolerance: float) -> int:
    singular = numpy.linalg.svd(scaled, compute_uv=False) if scaled.size else numpy.zeros(0)
    return int((singular > relative_tolerance * singular.max()).sum()) if singular.size and singular.max() > 0 else 0


def _numerical_rank(matrix, relative_tolerance: float) -> int:
    """Singular values above relative_tolerance times the largest, on columns scaled to unit norm (_unit_columns). Plan
    Section 14.1 fixes a tolerance for a numerical comparison, and W5 asks that a degeneracy be preserved: the stored
    entries of a float operator carry rounding of order the rounding unit times the operator's size, so a singular value
    below the tolerance times the largest cannot be told from zero, and exact rank would call such an operator invertible.
    Without the column scaling a column in small units would read as a null mode, and the same model would pass or fail
    by its time unit."""
    return _scaled_rank(_unit_columns(matrix)[0], relative_tolerance)


def _matrix_product(left, right) -> list[list[Fraction]]:
    return [[sum((a * b for a, b in zip(row, column)), Fraction(0)) for column in zip(*right)] for row in left]


def _transposed(matrix) -> list[list[Fraction]]:
    return [list(column) for column in zip(*matrix)]


def _integer_rows(matrix) -> tuple[list[list[int]], int]:
    """Exact integers and their common scale: elimination on integers avoids a gcd at every step, which a dense covariance
    of float entries cannot afford."""
    rows = _as_fractions(matrix)
    scale = math.lcm(*(value.denominator for row in rows for value in row))
    return [[int(value * scale) for value in row] for row in rows], scale


def _inverse_matrix(matrix) -> list[list[Fraction]] | None:
    """Fraction-free Gauss-Jordan elimination: each division is exact, and the diagonal ends as the determinant."""
    integers, scale = _integer_rows(matrix)
    size = len(integers)
    rows = [row + [int(index == column) for column in range(size)] for index, row in enumerate(integers)]
    previous = 1
    for step in range(size):
        pivot = next((index for index in range(step, size) if rows[index][step]), None)
        if pivot is None:
            return None
        rows[step], rows[pivot] = rows[pivot], rows[step]
        lead = rows[step][step]
        for index in range(size):
            if index != step:
                factor = rows[index][step]
                rows[index] = [(lead * value - factor * other) // previous for value, other in zip(rows[index], rows[step])]
        previous = lead
    return [[Fraction(value * scale, previous) for value in row[size:]] for row in rows]


def _rectangular(matrix, width: int) -> bool:
    return all(len(row) == width for row in matrix)


def _in_row_space(weights, matrix, relative_tolerance: float = 0) -> bool:
    if not relative_tolerance:
        return matrix_rank(list(matrix) + [list(weights)]) == matrix_rank(matrix)
    rows, norms = _unit_columns(matrix)
    combination = numpy.array(weights, dtype=float) / norms  # the same combination, in the scaled parameters
    size, largest = float(numpy.linalg.norm(combination)), float(numpy.linalg.norm(rows, 2))
    if largest == 0:
        # W2: a template with no support in the window leaves the amplitude unidentifiable, and A34 asks that this be stated:
        # the row space of a zero design holds only the zero combination, so nothing else is determined
        return not any(weights)
    row = combination * largest / size if size else combination  # judged at the operator's own scale
    return _scaled_rank(numpy.vstack([rows, row]), relative_tolerance) == _scaled_rank(rows, relative_tolerance)


def _consistent_solution(matrix, right_side) -> list[Fraction] | None:
    """One exact solution of a consistent system, free parameters at zero; None when the system has none."""
    width = len(matrix[0])
    reduced, _ = _row_reduced([list(row) + [value] for row, value in zip(matrix, right_side)])
    solution = [Fraction(0)] * width
    for row in reduced:
        pivot = next((column for column, value in enumerate(row) if value), None)
        if pivot == width:
            return None
        if pivot is not None:
            solution[pivot] = row[width]
    return solution


def _weighted_sum(weights, values) -> Fraction:
    return sum((Fraction(weight) * value for weight, value in zip(weights, values)), Fraction(0))


def _absolute(matrix) -> list[list[Fraction]]:
    return [[abs(value) for value in row] for row in _as_fractions(matrix)]


def _within_rounding(found, stated, terms_size, tolerance) -> bool:
    return abs(Fraction(found) - Fraction(stated)) <= Fraction(tolerance) * terms_size


def _positive_definite(matrix) -> bool:
    """Symmetric, with every leading principal minor positive (fraction-free elimination without pivoting)."""
    rows, _ = _integer_rows(matrix)
    if any(rows[i][j] != rows[j][i] for i in range(len(rows)) for j in range(i)):
        return False
    previous = 1
    for pivot in range(len(rows)):
        lead = rows[pivot][pivot]
        if lead <= 0:
            return False
        for index in range(pivot + 1, len(rows)):
            factor = rows[index][pivot]
            rows[index] = [(lead * value - factor * other) // previous for value, other in zip(rows[index], rows[pivot])]
        previous = lead
    return True


def _check_port(port: dict, report: Report, path: str = "$") -> None:
    semantics = port["quantity"]
    if semantics["kind"] == "angle" and "period" not in semantics:
        report.add("error", f"{path}.quantity", "reconstruction.port.angle_without_period",
                   "an angle states its period; the same rad on an axis and on a vector is not the same quantity (K05)")


def _check_presence(product: dict, report: Report) -> None:
    """A06. An empty list is valid-empty, never present. Present may leave objects out: W1 keeps the native object a typed
    native reference, so a sidecar need not list a native collection. Absent, invalid and not-applicable never pass as empty."""
    presence, objects = product["presence"], product.get("objects")
    if presence == "present" and objects == []:
        report.add("error", "$.objects", "reconstruction.presence.present_without_objects", "an empty list is valid-empty; present lists objects or leaves the key out")
    elif presence == "valid-empty" and objects is None:
        report.add("error", "$.objects", "reconstruction.presence.empty_without_objects", "valid-empty states an empty objects list")
    elif presence == "valid-empty" and objects:
        report.add("error", "$.objects", "reconstruction.presence.empty_with_objects", "a valid empty collection holds no object")
    elif presence not in ("present", "valid-empty") and objects is not None:
        report.add("error", "$.objects", "reconstruction.presence.objects_without_presence",
                   f"{presence} is not an empty collection: leave objects out")


def _check_identifiability(estimate: dict, design, report: Report, path: str) -> int:
    declared, parameters = estimate["identifiability"], estimate["parameters"]
    tolerance = estimate["comparator"]["relative_tolerance"]
    rank = matrix_rank(design, tolerance)
    unidentifiable = [name for index, name in enumerate(parameters)
                      if not _in_row_space([int(column == index) for column in range(len(parameters))], design, tolerance)]
    expected_status = "full" if rank == len(parameters) else "rank-deficient"
    if (declared["rank"], declared["status"], declared["unidentifiable"]) != (rank, expected_status, unidentifiable):
        report.add("error", f"{path}.identifiability", "reconstruction.estimate.identifiability_mismatch",
                   f"the design has rank {rank} of {len(parameters)}; unidentifiable: {unidentifiable}")
    for component in declared.get("components", []):
        if len(component["weights"]) != len(parameters) or not _in_row_space(component["weights"], design, tolerance):
            report.add("error", f"{path}.identifiability.components", "reconstruction.estimate.component_not_identifiable",
                       f"{component['weights']} is not a combination the design determines")
        elif estimate["model"]["shape"] == "fixed-template":  # outside that domain the linear model fixes no value
            if matrix_rank(design) == rank:
                _check_component(estimate, component, design, report, path)
            else:
                # Section 9.5: a null mode that rounding hides gains no identifiability here, and Section 14.1 fixes the comparison
                # at the stated tolerance; the exact numbers fix a value only on the exact row space, so the stated one is reported unchecked
                report.add("warning", f"{path}.identifiability.components", "reconstruction.estimate.component_unchecked",
                           f"{component['weights']} was not checked: the design has rank {matrix_rank(design)} exactly and {rank} at the stated "
                           "tolerance, so the stored numbers fix no value to compare")
    return rank


def _check_component(estimate: dict, component: dict, design, report: Report, path: str) -> None:
    """The value and variance of an identifiable combination c are fixed by the model: c.x for any solution x of the normal
    equations, and c.u with N u = c, so a stated number is checked, not trusted."""
    weighted = _matrix_product(_transposed(_as_fractions(design)), _inverse_matrix(estimate["model"]["noise_covariance"]))
    normal = _matrix_product(weighted, _as_fractions(design))
    projected = [row[0] for row in _matrix_product(weighted, [[Fraction(value)] for value in estimate["observation"]])]
    tolerance, weights = estimate["comparator"]["relative_tolerance"], component["weights"]
    solution, dual = _consistent_solution(normal, projected), _consistent_solution(normal, [Fraction(weight) for weight in weights])
    if solution is None or dual is None:
        # the weights lie in the row space at the stated tolerance (Section 14.1) and not exactly, so the exact model fixes no value for them
        report.add("warning", f"{path}.identifiability.components", "reconstruction.estimate.component_unchecked",
                   f"{weights} was not checked: it is a determined combination at the stated tolerance and not exactly, so the stored numbers fix no value to compare")
        return
    value, variance = _weighted_sum(weights, solution), _weighted_sum(weights, dual)
    value_size = sum(abs(Fraction(weight) * term) for weight, term in zip(weights, solution)) + abs(Fraction(component["value"]))
    variance_size = sum(abs(Fraction(weight) * term) for weight, term in zip(weights, dual))
    if not _within_rounding(value, component["value"], value_size, tolerance) or (
            "variance" in component and not _within_rounding(variance, component["variance"], variance_size, tolerance)):
        report.add("error", f"{path}.identifiability.components", "reconstruction.estimate.component_mismatch",
                   f"{weights} has value {float(value)} and variance {float(variance)} under the stated model")


def _check_normal_equations(estimate: dict, design, noise, report: Report, path: str) -> None:
    """Comparator of a full-rank record: M^T R^-1 (d - M x) = 0 and C (M^T R^-1 M) = 1, each entry relative to the sum of its
    terms' sizes (RELATIVE_TOLERANCE_CEILING). It checks a stated solution; it does not produce one."""
    solution, covariance = estimate["solution"], estimate["covariance"]["matrix"]
    tolerance, size = estimate["comparator"]["relative_tolerance"], len(estimate["parameters"])
    consistent = solution is not None and covariance is not None and len(solution) == size and \
        len(covariance) == size and _rectangular(covariance, size)
    if consistent:
        precision = _inverse_matrix(noise)
        weighted = _matrix_product(_transposed(_as_fractions(design)), precision)
        weighted_size = _matrix_product(_transposed(_absolute(design)), _absolute(precision))
        normal, normal_size = _matrix_product(weighted, _as_fractions(design)), _matrix_product(weighted_size, _absolute(design))
        parameters = [[Fraction(value)] for value in solution]
        fitted, fitted_size = _matrix_product(_as_fractions(design), parameters), _matrix_product(_absolute(design), _absolute(parameters))
        residual = [[Fraction(value) - row[0]] for value, row in zip(estimate["observation"], fitted)]
        residual_size = [[abs(Fraction(value)) + row[0]] for value, row in zip(estimate["observation"], fitted_size)]
        gradient, gradient_size = _matrix_product(weighted, residual), _matrix_product(weighted_size, residual_size)
        unit, unit_size = _matrix_product(_as_fractions(covariance), normal), _matrix_product(_absolute(covariance), normal_size)
        consistent = all(_within_rounding(gradient[i][0], 0, gradient_size[i][0], tolerance) for i in range(size)) and all(
            _within_rounding(unit[i][j], int(i == j), unit_size[i][j], tolerance) for i in range(size) for j in range(size))
    if not consistent:
        report.add("error", path, "reconstruction.estimate.solution_mismatch",
                   f"solution or covariance does not satisfy the normal equations within {tolerance} of their terms' size")


def _check_estimate(estimate: dict, report: Report, path: str) -> None:
    """W2: a full-rank record satisfies its model; a rank-deficient one delivers identifiable components only."""
    design, noise, parameters = estimate["model"]["design"], estimate["model"]["noise_covariance"], estimate["parameters"]
    if any(len(row) != len(parameters) for row in design) or len(estimate["observation"]) != len(design) or \
            len(noise) != len(design) or any(len(row) != len(design) for row in noise):
        report.add("error", f"{path}.model", "reconstruction.estimate.dimension_mismatch", "design, noise and observation do not agree")
        return
    if not _positive_definite(noise):
        report.add("error", f"{path}.model.noise_covariance", "reconstruction.estimate.noise_not_positive_definite",
                   "the declared noise covariance is not positive definite")
        return
    rank = _check_identifiability(estimate, design, report, path)
    covariance = estimate["covariance"]
    if covariance["scope"] == "fixed-model" and covariance["includes"]:
        report.add("error", f"{path}.covariance", "reconstruction.estimate.covariance_scope",
                   f"a fixed-model covariance cannot include {covariance['includes']}: template and conditions uncertainty is outside it")
    fixed_template = estimate["model"]["shape"] == "fixed-template"
    if not fixed_template and (estimate["status"] != "out-of-domain" or estimate["optimal_claim"]):
        report.add("error", path, "reconstruction.estimate.out_of_domain_claim",
                   "outside the fixed-template domain the status is out-of-domain and the estimator is not claimed optimal")
    expected = "fit" if rank == len(parameters) else "rank-deficient"
    if fixed_template and (estimate["status"] != expected or (estimate["optimal_claim"] and expected != "fit")):
        report.add("error", f"{path}.status", "reconstruction.estimate.status_mismatch",
                   f"this model is {expected}; only a fit is claimed optimal")
    if rank < len(parameters):
        if estimate["regularization"] == "jitter":
            report.add("error", f"{path}.regularization", "reconstruction.estimate.jitter_precision",
                       "jitter cannot manufacture precision for a null mode (Sections 8.5, 9.5)")
        if estimate["solution"] is not None or covariance["matrix"] is not None:
            report.add("error", path, "reconstruction.estimate.spurious_precision",
                       "a rank-deficient model delivers identifiable components only, with no solution or covariance")
    elif fixed_template:
        _check_normal_equations(estimate, design, noise, report, path)


def _expected_window(key: int, radius: int, keys: range, missing) -> str:
    if key - radius < keys.start or key + radius >= keys.stop:
        return "edge-incomplete"
    return "gap-adjacent" if any(key + step in missing for step in range(-radius, radius + 1) if step) else "complete"


def _check_frame_partitions(frames: dict, keys: range, report: Report, path: str) -> None:
    position = keys.start
    span = keys.stop - keys.start
    for partition in sorted(frames["partitions"], key=lambda item: item["core"][0]):
        start, end = partition["core"]
        if start != position or end <= start:
            report.add("error", f"{path}.partitions", "reconstruction.frames.cores_do_not_tile", f"core {partition['core']} leaves a gap or an overlap at {position}")
        position = end
        expected = {key for offset in range(1, min(partition["halo"], span) + 1) for key in (start - offset, end - 1 + offset)  # no key lies further
                    if key in keys and key not in frames["missing_keys"]}
        if set(partition["halo_keys"]) != expected:
            report.add("error", f"{path}.partitions", "reconstruction.frames.halo_mismatch",
                       f"{partition['partition_id']} rereads {partition['halo_keys']}; retained halo keys are {sorted(expected)}, and a halo restores no gap")
    if position != keys.stop:
        report.add("error", f"{path}.partitions", "reconstruction.frames.cores_do_not_tile", f"the cores end at {position}, the domain at {keys.stop}")


def _check_frame_outputs(frames: dict, keys: range, report: Report, path: str) -> None:
    partitions, missing = {item["partition_id"]: item for item in frames["partitions"]}, set(frames["missing_keys"])
    seen = Counter(key_output["key"] for key_output in frames["outputs"])
    for key in sorted(key for key, times in seen.items() if times > 1):
        report.add("error", f"{path}.outputs", "reconstruction.frames.halo_double_count", f"key {key} has more than one output")
    for key in keys:
        if key not in seen and key not in missing:
            report.add("error", f"{path}.outputs", "reconstruction.frames.key_without_output", f"key {key} is neither output nor marked missing")
    for key_output in frames["outputs"]:
        key, owner = key_output["key"], partitions.get(key_output["owner"])
        if key in missing:
            report.add("error", f"{path}.outputs", "reconstruction.frames.missing_restored", f"key {key} is an original gap; a halo does not restore it")
        elif owner is None or not owner["core"][0] <= key < owner["core"][1]:
            report.add("error", f"{path}.outputs", "reconstruction.frames.wrong_owner", f"key {key} is outside the core of {key_output['owner']}")
        elif key_output["window"] != _expected_window(key, owner["halo"], keys, missing):
            claimed_complete = key_output["window"] == "complete"
            report.add("error", f"{path}.outputs", f"reconstruction.frames.{'incomplete_window_claimed' if claimed_complete else 'window_mismatch'}",
                       f"key {key} has the window {_expected_window(key, owner['halo'], keys, missing)}, not {key_output['window']}")


def _check_frames(frames: dict, report: Report, path: str) -> None:
    """W3: ownership, halos, gaps and accounts agree."""
    keys = range(*frames["domain"])
    if keys.stop - keys.start > len(frames["outputs"]) + len(frames["missing_keys"]):  # one finding, and no walk of a huge domain
        report.add("error", f"{path}.outputs", "reconstruction.frames.key_without_output",
                   f"the domain holds {keys.stop - keys.start} keys, and outputs and marked gaps account for fewer")
        return
    _check_frame_partitions(frames, keys, report, path)
    if not report.ok:
        return
    _check_frame_outputs(frames, keys, report, path)
    accounts, windows = frames["accounts"], {}
    for key_output in frames["outputs"]:
        windows.setdefault(key_output["window"], []).append(key_output["key"])
    expected = {"observed": len(keys) - len(frames["missing_keys"]), "owned": len(frames["outputs"]), "missing": len(frames["missing_keys"]),
                "edge_incomplete": sorted(windows.get("edge-incomplete", [])), "gap_adjacent": sorted(windows.get("gap-adjacent", []))}
    if accounts != expected or accounts["owned"] != accounts["observed"]:
        report.add("error", f"{path}.accounts", "reconstruction.frames.accounts_mismatch", f"the accounts should read {expected}")


def _check_hypotheses(candidates: dict, report: Report, path: str) -> None:
    seen: dict = {}
    for item in candidates["hypotheses"]:
        seen.setdefault(item["hypothesis_id"], []).append(item)
        if item.get("hypothesis_kind") == "ordering" and not all(field in item for field in ("ordering", "escape", "quality")):
            report.add("error", f"{path}.hypotheses", "reconstruction.candidate.ordering_incomplete",
                       f"{item['hypothesis_id']}: an ordering hypothesis keeps its ordering, escape state and own quality")
    for identity, revisions in seen.items():
        numbers = [item["revision"] for item in revisions]
        if len(set(numbers)) != len(numbers):
            report.add("error", f"{path}.hypotheses", "reconstruction.candidate.duplicate_revision", f"{identity} repeats a revision")
        if sum(item["state"] == "committed" for item in revisions) > 1:  # W4: never old and new at once; an open replacement beside a commit is Section 10.1's in-flight state
            report.add("error", f"{path}.hypotheses", "reconstruction.candidate.two_committed_revisions", f"{identity} has two committed revisions")
    for group, identity in candidates["selection_policy"]["selected"].items():
        selected = _live_revision(candidates, identity)
        if selected is None or selected["exclusive_group"] != group:
            report.add("error", f"{path}.selection_policy", "reconstruction.candidate.selection_unresolved",
                       f"{group} selects {identity}, which has no committed revision in that group")


def _check_consumers(candidates: dict, report: Report, path: str) -> None:
    held: dict = {}
    counted: dict = {}
    entries: list = []
    selected = candidates["selection_policy"]["selected"]
    for consumer in candidates["consumers"]:
        identity, name = consumer["hypothesis_id"], consumer["consumer"]
        held.setdefault((name, identity), set()).add(consumer["revision"])
        target = next((item for item in candidates["hypotheses"]
                       if item["hypothesis_id"] == identity and item["revision"] == consumer["revision"]), None)
        if target is None or target["state"] == "discarded":
            report.add("error", f"{path}.consumers", "reconstruction.candidate.dangling", f"{name} reads {identity} revision {consumer['revision']}, which does not exist")
        elif target["state"] == "superseded":
            report.add("error", f"{path}.consumers", "reconstruction.candidate.stale_revision", f"{name} still reads revision {consumer['revision']} of {identity}")
        elif target["state"] == "open":
            report.add("error", f"{path}.consumers", "reconstruction.candidate.uncommitted_revision", f"{name} reads an incomplete replacement of {identity}")
        elif consumer["use"] == "count":
            counted.setdefault((name, target["exclusive_group"]), set()).add(identity)
            if selected.get(target["exclusive_group"]) != identity:
                report.add("error", f"{path}.consumers", "reconstruction.candidate.count_not_selected",
                           f"{name} counts {identity}; the policy selects {selected.get(target['exclusive_group'])} in {target['exclusive_group']}")
            if (name, identity, consumer["revision"]) in entries:
                report.add("error", f"{path}.consumers", "reconstruction.candidate.counted_twice", f"{name} counts {identity} twice")
            entries.append((name, identity, consumer["revision"]))
    for (name, identity), revisions in held.items():
        if len(revisions) > 1:
            report.add("error", f"{path}.consumers", "reconstruction.candidate.double_revision", f"{name} holds revisions {sorted(revisions)} of {identity}")
    for (name, group), identities in counted.items():
        if len(identities) > 1:
            report.add("error", f"{path}.consumers", "reconstruction.candidate.exclusive_counted",
                       f"{name} counts {sorted(identities)} of the exclusive group {group}: counting follows the selected hypothesis")


def _check_candidates(candidates: dict, report: Report, path: str) -> None:
    """W4: sharing is allowed; revisions, commits and counting are checked, and no unique-use flag removes a hypothesis early."""
    _check_hypotheses(candidates, report, path)
    _check_consumers(candidates, report, path)
    for step in candidates["pruning"]:
        if step["rule"] == "unique-hit-use" and step["stage"] == "before-selection":
            report.add("error", f"{path}.pruning", "reconstruction.candidate.premature_unique_use",
                       f"a unique hit-use flag removed {step['removed']} before selection; sharing inside candidates is valid")


def _probability_column(column, tolerance) -> bool:
    """Non-negative entries whose sum does not exceed 1 by more than the record's comparator (Section 14.1) times the number
    of terms times their size: a sum of n double-precision rounded terms is wrong by at most n rounding units of its terms'
    size, so any comparator at or above the schema's floor covers an operator column-normalized in double precision. An
    operator normalized and stored in single precision exceeds 1 by up to about 2e-7 and is refused at the ceiling: a true
    reading of the stored numbers, and renormalizing in double precision is the way to state it. A sum beyond the bound is
    refused; an excess inside it (1e-6 with 1000 terms at the ceiling) is not caught. A negative entry is exact: normalizing
    non-negative entries never makes one."""
    column_sum, terms_size = sum(Fraction(value) for value in column), sum(abs(Fraction(value)) for value in column)
    return min(column) >= 0 and column_sum - 1 <= Fraction(tolerance) * len(column) * terms_size


def _check_operator(operator: dict, report: Report, path: str, tolerance: float) -> None:
    normalization = operator["normalization"]
    if normalization["kind"] != "none" and normalization["basis"] == "default":
        report.add("error", f"{path}.normalization", "reconstruction.inversion.default_normalization",
                   "normalizing an operator by default changes its meaning; a normalization is declared with the operator first")
    if operator["interpretation"] == "probability" and not all(_probability_column(column, tolerance) for column in zip(*operator["matrix"])):
        report.add("error", f"{path}.interpretation", "reconstruction.inversion.not_a_probability", "a column of this operator is not a probability distribution")


def _residual_within(matrix, vector, target, tolerance) -> bool:
    """Each entry of A x - target is within the tolerance of the sum of its terms' sizes (RELATIVE_TOLERANCE_CEILING)."""
    exact_vector = [[Fraction(value)] for value in vector]
    found = _matrix_product(_as_fractions(matrix), exact_vector)
    sizes = _matrix_product(_absolute(matrix), _absolute(exact_vector))
    return all(_within_rounding(row[0], value, size[0] + abs(Fraction(value)), tolerance) for row, value, size in zip(found, target, sizes))


def _check_inversion(inversion: dict, report: Report, path: str) -> None:
    """W5: every solution gives the observed values, the null space is complete, and no solution passes as unique. Equality,
    rank and the probability sums follow the record's comparator (Section 14.1), so honest float operators and solver
    solutions are accepted; rank is judged on unit-norm columns, so it does not depend on the units of the parameters."""
    matrix, tolerance = inversion["operator"]["matrix"], inversion["comparator"]["relative_tolerance"]
    if not _rectangular(matrix, len(matrix[0])):
        report.add("error", f"{path}.operator.matrix", "reconstruction.inversion.dimension_mismatch", "the operator's rows differ in length")
        return
    _check_operator(inversion["operator"], report, f"{path}.operator", tolerance)
    width = len(matrix[0])
    for index, solution in enumerate(inversion["solutions"]):
        if len(solution) != width or len(inversion["observed"]) != len(matrix) or not _residual_within(matrix, solution, inversion["observed"], tolerance):
            report.add("error", f"{path}.solutions[{index}]", "reconstruction.inversion.solution_mismatch", f"{solution} does not give the observed values")
    directions = inversion["null_directions"]
    for index, direction in enumerate(directions):
        if len(direction) != width or not any(direction) or not _residual_within(matrix, direction, [0] * len(matrix), tolerance):
            report.add("error", f"{path}.null_directions[{index}]", "reconstruction.inversion.null_direction_invalid", f"{direction} is not a null direction of the operator")
    nullity = width - matrix_rank(matrix, tolerance)
    if len(directions) != nullity or not _rectangular(directions, width) or (directions and matrix_rank(directions, tolerance) != nullity):
        report.add("error", f"{path}.null_directions", "reconstruction.inversion.null_space_incomplete", f"the operator has {nullity} independent null directions at the stated tolerance")
    if nullity and inversion["uniqueness_claim"]:
        report.add("error", f"{path}.uniqueness_claim", "reconstruction.inversion.unique_claim", "a solver's single answer is not a unique solution of a degenerate operator")
    selected = inversion["selected_solution"]
    if selected is not None:
        if selected >= len(inversion["solutions"]):
            report.add("error", f"{path}.selected_solution", "reconstruction.inversion.selection_unresolved", f"there is no solution {selected}")
        if inversion["prior"] is None:
            report.add("error", f"{path}.prior", "reconstruction.inversion.selection_without_prior", "a selected solution states the prior that selected it")
        elif nullity and not inversion["undetermined_components"]:
            report.add("error", f"{path}.undetermined_components", "reconstruction.inversion.undetermined_missing",
                       "a selected solution states the components the data do not determine")


def _check_count_intervals(counts: dict, channels: dict, report: Report, path: str) -> None:
    for item in counts["intervals"]:
        if item["channel"] not in channels:
            report.add("error", f"{path}.intervals", "reconstruction.counts.unknown_channel", f"{item['interval_id']}: {item['channel']} is not a declared channel")
        if item["presence"] == "present" and "count" not in item:
            report.add("error", f"{path}.intervals", "reconstruction.counts.count_missing", f"{item['interval_id']} is present and holds no count")
        elif item["presence"] != "present" and "count" in item:
            report.add("error", f"{path}.intervals", "reconstruction.counts.absent_filled", f"{item['interval_id']} is {item['presence']}: it holds no count, not even zero")


def _check_rates(counts: dict, channels: dict, report: Report, path: str) -> None:
    for rate in counts["rates"]:
        channel, denominator = channels.get(rate["channel"]), rate["denominator"]
        if channel is None:
            report.add("error", f"{path}.rates", "reconstruction.counts.unknown_channel", f"{rate['channel']} is not a declared channel")
            continue
        if denominator["source"] == "run-time":
            report.add("error", f"{path}.rates", "reconstruction.counts.run_time_denominator", f"{rate['channel']}: a rate uses the channel's valid exposure, not the run time")
        elif not _same_measure({"value": denominator["value"], "unit": denominator["unit"]}, channel["valid_exposure"]):
            report.add("error", f"{path}.rates", "reconstruction.counts.exposure_mismatch", f"{rate['channel']}: the denominator is not this channel's valid exposure")
        if rate["response_ref"] != channel["response_ref"]:
            report.add("error", f"{path}.rates", "reconstruction.counts.response_mismatch", f"{rate['channel']}: the rate names another channel's response")
        if rate["selection_ref"] != channel["selection_ref"]:
            report.add("error", f"{path}.rates", "reconstruction.counts.selection_mismatch", f"{rate['channel']}: the rate names another selection")


def _check_selections(counts: dict, report: Report, path: str) -> None:
    """W6: selection is distinguishable from presence and exposure, and every channel states its own."""
    known = {item["selection_id"] for item in counts["selections"]}
    for item in counts["channels"]:
        if item["selection_ref"] not in known:
            report.add("error", f"{path}.channels", "reconstruction.counts.unknown_selection", f"{item['channel']}: {item['selection_ref']} is not a declared selection")
    for item in counts["selections"]:
        if item["kind"] == "threshold" and item["threshold"] is None:
            report.add("error", f"{path}.selections", "reconstruction.counts.threshold_missing", f"{item['selection_id']} is a threshold and states no value")
        # W6: selection is distinguishable, so a record's content matches the kind it declares
        if (item["kind"] == "none" and item["threshold"] is not None) or (item["kind"] == "window" and "window" not in item) or (
                item["kind"] == "native-rule" and "reference" not in item):
            report.add("error", f"{path}.selections", "reconstruction.counts.selection_incomplete", f"{item['selection_id']}: its content does not match its kind {item['kind']}")


def _check_counts(counts: dict, report: Report, path: str) -> None:
    """W6, A19, A23, A24."""
    channels = {item["channel"]: item for item in counts["channels"]}
    _check_count_intervals(counts, channels, report, path)
    _check_rates(counts, channels, report, path)
    _check_selections(counts, report, path)
    run_time = counts["run_time"]
    for item in counts["channels"]:
        if item["valid_exposure"]["value"] < 0:
            report.add("error", f"{path}.channels", "reconstruction.counts.negative_exposure", f"{item['channel']}: an exposure is not negative")
        exposure, whole_run = _in_base_unit(item["valid_exposure"]), _in_base_unit(run_time)
        above = False
        if item["valid_exposure"]["unit"] == run_time["unit"]:
            above = item["valid_exposure"]["value"] > run_time["value"]
        elif exposure is None or whole_run is None or exposure[0] != whole_run[0]:
            # W6 asks that exposure be checked; a unit this reader cannot convert leaves that check undone, which is reported, not hidden
            report.add("warning", f"{path}.channels", "reconstruction.counts.exposure_not_compared",
                       f"{item['channel']}: {item['valid_exposure']['unit']} and {run_time['unit']} cannot be compared by this reader, so the exposure was not checked against the run time")
        else:  # one measure in two units is one measure (K05), so a fully live channel is not above the run
            above = exposure[1] > whole_run[1] and not math.isclose(exposure[1], whole_run[1], rel_tol=1e-12)
        if above:  # W6: exposure is valid exposure, a part of the run
            report.add("error", f"{path}.channels", "reconstruction.counts.exposure_above_run_time", f"{item['channel']}: valid exposure exceeds the run time")
    model = counts["count_model"]
    if model["inferred_from"] is not None:
        report.add("error", f"{path}.count_model", "reconstruction.counts.poisson_from_integer", "an integer type establishes no count model")
    if not model["premises"]:
        report.add("error", f"{path}.count_model", "reconstruction.counts.model_without_premises", "a count model follows from stated sampling and dead-time premises")
    energy_observed = bool(ENERGY_OBSERVABLES & set(counts["observables"]))
    if counts["per_event_energy"] and not energy_observed:
        report.add("error", path, "reconstruction.counts.energy_without_observable", "no energy observable exists, so no per-event energy is delivered")
    if counts["per_event_energy"] and counts["capability"] == "counting":  # A24: capabilities and outputs stay distinct
        report.add("error", f"{path}.capability", "reconstruction.counts.capability_mismatch", "a counting sensor delivers no per-event energy")


def _check_coordinate_map(item: dict, report: Report, path: str) -> None:
    """W7: coordinates are mapped correctly. The sideband is declared, not assumed: physical = oscillator + sign x intermediate."""
    oscillator = dict(item["local_oscillator"])
    if oscillator["unit"] != item["interval_unit"]:  # K05: one frequency in two units
        converted, base = _in_base_unit(oscillator), _in_base_unit({"value": 1, "unit": item["interval_unit"]})
        if converted is None or base is None or converted[0] != base[0]:
            report.add("error", f"{path}.settings", "reconstruction.scan.coordinate_map", f"{item['setting_id']}: {oscillator['unit']} cannot be compared with {item['interval_unit']}")
            return
        oscillator = {"value": converted[1] / base[1], "unit": item["interval_unit"]}
    mapped = sorted(oscillator["value"] + item["sideband_sign"] * edge for edge in item["intermediate_interval"])
    expected = sorted(item["physical_interval"])
    terms_size = max([abs(oscillator["value"])] + [abs(edge) for edge in item["intermediate_interval"]])
    same_edges = len(mapped) == len(expected) and all(math.isclose(a, b, rel_tol=0, abs_tol=RELATIVE_TOLERANCE_CEILING * terms_size) for a, b in zip(mapped, expected))
    if not same_edges:
        report.add("error", f"{path}.settings", "reconstruction.scan.coordinate_map", f"{item['setting_id']}: the physical interval does not follow from its oscillator and sideband")


def _check_overlaps(scan: dict, report: Report, path: str) -> None:
    settings = {item["setting_id"]: item for item in scan["settings"]}
    marked = {(frozenset((first, second)), segment) for overlap in scan["overlaps"] for segment in overlap["raw_segments"]
              for first in overlap["settings"] for second in overlap["settings"] if first != second}
    names = list(settings)
    for index, first in enumerate(names):
        for second in names[index + 1:]:
            for segment in sorted(set(settings[first]["raw_segments"]) & set(settings[second]["raw_segments"])):
                if (frozenset((first, second)), segment) not in marked:
                    report.add("error", f"{path}.overlaps", "reconstruction.scan.overlap_unmarked", f"{segment} is shared by two settings and not marked")
    for overlap in scan["overlaps"]:
        for segment in overlap["raw_segments"]:
            if not all(name in settings and segment in settings[name]["raw_segments"] for name in overlap["settings"]):
                report.add("error", f"{path}.overlaps", "reconstruction.scan.overlap_unsupported", f"{segment} is not held by every setting of this overlap")
        if overlap["independent_exposure"]:
            report.add("error", f"{path}.overlaps", "reconstruction.scan.shared_raw_as_independent", "reuse of the same raw data is not independent exposure")
        if not overlap["shared_noise"] and "noise_premise" not in overlap:
            report.add("error", f"{path}.overlaps", "reconstruction.scan.shared_noise_denied", "a shared segment is shared noise unless a premise says otherwise")
        if scan["noise_model"]["kind"] == "independent-poisson" and (overlap["shared_noise"] or "noise_premise" not in overlap):  # W7
            report.add("error", f"{path}.noise_model", "reconstruction.scan.independent_poisson", "settings that share noise are not independent Poisson bins")


def _check_radio_frequency_scan(scan: dict, report: Report, path: str) -> None:
    for item in scan["settings"]:
        _check_coordinate_map(item, report, path)
    _check_overlaps(scan, report, path)


def _check_reported_values(scan: dict, design, report: Report, path: str) -> None:
    """W7 names no estimator, and Section 10.3 leaves the estimate to a native solver, so a value is compared only when every
    estimator agrees: the observations, with a constraint that states a value, are exactly consistent."""
    constraint = scan["constraint"]
    exact_constraint = constraint is not None and "value" in constraint
    system = design if exact_constraint or constraint is None else scan["model"]["design"]  # a prior states no value, so the data alone
    observed = [Fraction(value) for value in scan["model"]["observation"]] + ([Fraction(constraint["value"])] if exact_constraint else [])
    solution = _consistent_solution(_as_fractions(system), observed)
    if solution is None:
        return
    for item in scan["reported"]:
        if _in_row_space(item["weights"], system):
            value = _weighted_sum(item["weights"], solution)
            terms_size = sum(abs(Fraction(weight) * term) for weight, term in zip(item["weights"], solution)) + abs(Fraction(item["value"]))
            if not _within_rounding(value, item["value"], terms_size, RELATIVE_TOLERANCE_CEILING):
                report.add("error", f"{path}.reported", "reconstruction.scan.reported_mismatch", f"{item['weights']} gives {float(value)}; the observations are consistent, so every estimator agrees")


def _check_global_scan(scan: dict, report: Report, path: str) -> None:
    model, constraint = scan["model"], scan["constraint"]
    # Accepted limits (decisions.md): a scan has no comparator, so its rank is judged at RELATIVE_TOLERANCE_CEILING alone, and
    # column scaling removes units, not an offset, so a polynomial in an uncentred coordinate can read rank-deficient;
    # centring the coordinate is the accepted form. The constraint row is a row at its own scale, and rows are not scaled;
    # a constraint stated at the design's scale is the accepted form. Both fail towards "not determined".
    design = model["design"] + ([constraint["weights"]] if constraint else [])
    parameters = model["parameters"]
    if not _rectangular(design + [item["weights"] for item in scan["reported"]], len(parameters)) or len(model["observation"]) != len(model["design"]):
        report.add("error", f"{path}.model", "reconstruction.scan.dimension_mismatch", "design, constraint, observation and reported weights do not agree")
        return
    rank = matrix_rank(design, RELATIVE_TOLERANCE_CEILING)
    for item in scan["reported"]:
        if not _in_row_space(item["weights"], design, RELATIVE_TOLERANCE_CEILING):
            report.add("error", f"{path}.reported", "reconstruction.scan.unidentifiable_reported", f"{item['weights']} is not determined by the observations")
    _check_reported_values(scan, design, report, path)
    expected = [name for index, name in enumerate(parameters) if not _in_row_space([int(column == index) for column in range(len(parameters))], design, RELATIVE_TOLERANCE_CEILING)]
    if scan["unidentifiable"] != expected:
        report.add("error", f"{path}.unidentifiable", "reconstruction.scan.unidentifiable_unnamed", f"the design leaves {expected} undetermined")
    if rank < len(parameters):
        if scan["regularization"] == "jitter":
            report.add("error", f"{path}.regularization", "reconstruction.scan.jitter_precision", "jitter on a null mode identifies nothing")
        if scan["uniqueness_claim"]:
            report.add("error", f"{path}.uniqueness_claim", "reconstruction.scan.unique_claim", "the design has a null mode, so no solution is unique")


def _check_constraint_resolution(resolution: dict, report: Report, path: str) -> None:
    """A03, A25, G02: external first, then qualified internal or joint constraints; restriction only if none suffices."""
    alternatives = resolution["internal"] + resolution["joint"]
    enough = resolution["external"]["state"] == "available" or any(item["state"] == "qualified" and item["sufficient"] for item in alternatives)
    if resolution["outcome"] == "full" and not enough:
        report.add("error", path, "reconstruction.constraint.full_without_information", f"no available or qualified constraint delivers {resolution['target']}")
    if resolution["outcome"] == "full" and resolution["restriction"] is not None:
        report.add("error", path, "reconstruction.constraint.restriction_on_full", "a full delivery carries no restriction")
    if resolution["outcome"] == "restricted":
        if not alternatives:
            report.add("error", path, "reconstruction.constraint.alternatives_not_checked", "check internal or joint constraints before restricting delivery")
        elif enough:
            report.add("error", path, "reconstruction.constraint.needless_restriction", "a qualified constraint suffices, so delivery is not restricted")
        if resolution["restriction"] is None:
            report.add("error", path, "reconstruction.constraint.restriction_unstated", "a restricted delivery states what it omits and why")


def _check_association(association: dict, report: Report, path: str) -> None:
    """A22: association follows each kind's respective response. A shared timing reference is allowed: nothing says the
    time bases must differ, so each member only states its base and window (schema)."""
    members = association["members"]
    for index, first in enumerate(members):
        for second in members[index + 1:]:
            if first["sensor_kind"] != second["sensor_kind"] and first["response_ref"] == second["response_ref"]:
                report.add("error", f"{path}.members", "reconstruction.association.shared_response",
                           f"{first['sensor_kind']} and {second['sensor_kind']} associate through their own response")


def _names_a_track(axis: str) -> bool:
    """W7's negative is a frequency-time track treated as spatial, so an axis that names such a track; a pixel radius or a sky
    map is a real spatial coordinate. Axis names are free text, so this catches a named track only."""
    words = set(axis.lower().replace("_", "-").split("-"))
    return "track" in words and bool({"frequency", "freq", "time", "t"} & words)


SCAN_SUBCASES = {"rf-scan": (("settings", "overlaps"), _check_radio_frequency_scan), "retarding-scan": (("visits",), None),
                 "global": (("model", "reported", "constraint", "regularization", "uniqueness_claim"), _check_global_scan)}


def _check_scan(scan: dict, report: Report, path: str) -> None:
    """W7: the three subcases stay separate; each keeps its coordinates, overlaps, visits or identifiable combinations."""
    fields, check_subcase = SCAN_SUBCASES[scan["subcase"]]
    foreign = [field for name, (others, _) in SCAN_SUBCASES.items() if name != scan["subcase"] for field in others if field in scan]
    if foreign:
        report.add("error", path, "reconstruction.scan.subcases_merged", f"{scan['subcase']} holds {foreign} of another subcase: no shared solver")
    missing = [field for field in fields if field not in scan]
    if missing:
        report.add("error", path, "reconstruction.scan.subcase_incomplete", f"{scan['subcase']} needs {missing}")
    elif check_subcase is not None:
        check_subcase(scan, report, path)
    if any(item["kind"] == "spatial" and _names_a_track(item["axis"]) for item in scan["coordinates"]):
        report.add("error", f"{path}.coordinates", "reconstruction.scan.track_as_spatial", "a scan track is a frequency, setting or time coordinate, not a spatial track")
    if scan["merging"]["kind"] == "chunk-average":
        report.add("error", f"{path}.merging", "reconstruction.scan.chunk_average", "counts are not averaged before time and conditions are kept")
    if scan["noise_model"]["kind"] == "independent-poisson" and not scan["noise_model"]["premises"]:
        report.add("error", f"{path}.noise_model", "reconstruction.scan.independent_poisson", "independent Poisson noise is a premise to state, not a default")


PRODUCT_BLOCKS = {"estimate": ("reconstruction:estimate-v1", _check_estimate), "frames": ("reconstruction:frames-v1", _check_frames),
          "candidates": ("reconstruction:candidates-v1", _check_candidates),
          "inversion": ("reconstruction:inversion-v1", _check_inversion), "counts": ("reconstruction:counts-v1", _check_counts),
          "scan": ("reconstruction:scan-v1", _check_scan),
          "constraint_resolution": ("reconstruction:constraints-v1", _check_constraint_resolution),
          "association": ("reconstruction:association-v1", _check_association)}


def _check_retention(retention: dict, report: Report, path: str) -> None:
    if any(retention[level] == "removed" for level in REDUCED_LEVELS) and "lost_recalibrations" not in retention:
        report.add("error", path, "reconstruction.retention.loss_unstated", "reduced retention states which recalibrations it can no longer support (R34)")


def _check_product(product: dict, report: Report, path: str = "$") -> None:
    _check_presence(product, report)
    if "retention" in product:
        _check_retention(product["retention"], report, f"{path}.retention")
    for block, (extension, check_product_block) in PRODUCT_BLOCKS.items():
        if block in product:
            if extension not in product["required_extensions"]:
                report.add("error", f"{path}.{block}", "reconstruction.extension.undeclared_block",
                           f"the block {block} changes the meaning of the product and needs {extension} in required_extensions")
            check_product_block(product[block], report, f"{path}.{block}")
        elif extension in product["required_extensions"]:
            report.add("error", path, "reconstruction.extension.block_missing", f"{extension} is required and the block {block} is absent")
    if "frames" in product:
        recorded = {record["payload_id"] for record in product["conditions_used"]}
        for key_output in product["frames"]["outputs"]:
            if key_output["payload_id"] not in recorded:
                report.add("error", f"{path}.conditions_used", "reconstruction.frames.unrecorded_payload", f"key {key_output['key']} used a payload this product does not record")
    keys = Counter(item["key"] for item in product.get("objects", []))
    for key in sorted((key for key, times in keys.items() if times > 1), key=str):
        report.add("error", f"{path}.objects", "reconstruction.product.duplicate_key", f"key {key!r} appears twice in {product['product_id']}")


def _check_support_domain(recipe: dict, report: Report, path: str) -> None:
    """A02: the request is inside the support domain on every axis of the domain. Section 8.4 check 6 asks a domain of routine
    use only: pilots are judged separately, and a proposal keeps its unknowns (Section 8.7), so no domain means nothing to
    check for them."""
    binding = recipe["profile_binding"]
    domain, request = binding["support_domain"], binding["request"]
    if not domain and recipe["status"] != "routine":
        return
    if not domain or set(domain) - set(request):
        report.add("error", f"{path}.request", "reconstruction.recipe.request_incomplete", f"the request states no value for {sorted(set(domain) - set(request)) or 'a declared support domain'}")
    for axis, value in request.items():
        supported = domain.get(axis)
        if supported is None or not supported["min"] <= value <= supported["max"]:
            report.add("error", f"{path}.request", "reconstruction.recipe.outside_support_domain", f"{axis}={value} is outside the support domain of this binding")


def _check_recipe(recipe: dict, report: Report, path: str = "$") -> None:
    if recipe["command"] is not None and (recipe["status"] == "proposal" or recipe["implementation"]["backend"] is None):
        report.add("error", f"{path}.command", "reconstruction.recipe.proposal_not_executable",
                   "a proposal or an unselected backend has no command; null is never filled with a guess")
    for port in recipe["inputs"]:
        _check_port(port, report, f"{path}.inputs")
        if port["direction"] != "input":
            report.add("error", f"{path}.inputs", "reconstruction.recipe.port_direction", f"{port['port_id']} is not an input")
    for port in recipe["outputs"]:
        _check_port(port, report, f"{path}.outputs")
        if port["direction"] != "output":
            report.add("error", f"{path}.outputs", "reconstruction.recipe.port_direction", f"{port['port_id']} is not an output")
    sources = {port["port_id"]: port.get("source_ref") for port in recipe["inputs"]}
    for first, second in recipe["independent_inputs"]:
        if sources.get(first) is not None and sources.get(first) == sources.get(second):
            report.add("error", f"{path}.independent_inputs", "reconstruction.recipe.same_source_independent",
                       f"{first} and {second} come from one source: they are not assumed independent")
    for converter in recipe["converters"]:
        _check_converter(converter, report)
    _check_support_domain(recipe, report, f"{path}.profile_binding")
    reproducibility = recipe["reproducibility"]
    if reproducibility is None:  # Section 8.7: a proposal keeps its unknowns; G03: others declare a form
        if recipe["status"] != "proposal":
            report.add("error", f"{path}.reproducibility", "reconstruction.recipe.reproducibility_undeclared", "a recipe that is no proposal declares its reproducibility form")
    elif reproducibility["form"] != "byte" and not reproducibility["comparators"]:
        report.add("error", f"{path}.reproducibility", "reconstruction.recipe.comparators_missing", f"{reproducibility['form']} reproducibility is judged by declared comparators")
    if recipe["execution"]["concurrency"] == "serialized" and recipe["execution"]["slots"] > 1:
        report.add("error", f"{path}.execution", "reconstruction.recipe.reentrant_on_serialized", "a serialized backend takes one slot: an unsupported reentrant mode is never configured")
    if recipe["status"] == "routine" and recipe["evidence_ref"] is None:
        report.add("error", f"{path}.evidence_ref", "reconstruction.recipe.routine_without_evidence", "routine use needs binding evidence")
    mapping = recipe["tool_contract"]
    if mapping is not None and mapping["mapping_version"] not in TOOL_MAPPING_VERSIONS:
        report.add("error", f"{path}.tool_contract", "reconstruction.recipe.unknown_mapping_version", f"mapping version {mapping['mapping_version']} is not known to this reader")


def _check_evidence(evidence: dict, report: Report, path: str = "$") -> None:
    states = [item["state"] for item in evidence["checks"]]
    if evidence["state"] == "passed" and ("pass" not in states or "fail" in states or "inconclusive" in states):
        # Section 9.8: skipped never yields a pass, so a skip alone passes nothing; which checks are required is judged against the recipe
        report.add("error", f"{path}.state", "reconstruction.evidence.pass_without_checks", "passed needs a passed check and no failed or inconclusive one; skipped is not a pass")


def _check_selection(record: dict, report: Report, path: str = "$") -> None:
    decision = record["decision"]
    chosen, state = decision["chosen_recipe"], decision["state"]
    if state in ("needs-evidence", "abstained"):
        if chosen is not None:
            report.add("error", f"{path}.decision", "reconstruction.selection.choice_without_decision", f"{state} names no recipe")
        return
    candidate = next((item for item in record["candidates"] if item["recipe"] == chosen and chosen is not None), None)
    if candidate is None:
        report.add("error", f"{path}.decision", "reconstruction.selection.unknown_choice", f"{chosen} is not a candidate of this record")
    elif state == "selected" and candidate["quality_evidence"] is None:
        report.add("error", f"{path}.decision", "reconstruction.selection.choice_without_evidence", "a selected recipe has quality evidence; else use the qualified default")


def _check_signature(signature: dict, report: Report, path: str = "$") -> None:
    values: dict = {}
    for fact in signature["facts"]:
        kind = fact["source"]["kind"]
        if kind in NOT_EVIDENCE:
            report.add("error", f"{path}.facts", "reconstruction.signature.not_evidence", f"{fact['key']}: a {kind} is not evidence (K15)")
        if kind == "llm-extraction" and fact["method"] != "declared":
            report.add("error", f"{path}.facts", "reconstruction.signature.unconfirmed_fact", f"{fact['key']}: an extracted value stays declared until checked")
        values.setdefault((fact["key"], fact["scope"]), set()).add(fact["value"])
    for (key, _), found in values.items():
        if len(found) > 1 and key not in signature["conflicts"]:
            report.add("error", f"{path}.conflicts", "reconstruction.signature.hidden_conflict", f"{key} has conflicting values and is not listed as a conflict")


SIDECAR_CHECKS = {"reconstruction-port/1": _check_port, "reconstruction-product/1": _check_product, "conditions-payload/1": conditions._check_payload,
                  "reconstruction-recipe/1": _check_recipe, "binding-evidence/1": _check_evidence, "selection-record/1": _check_selection,
                  "input-signature/1": _check_signature}


def read_sidecar(document, known_extensions=KNOWN_EXTENSIONS) -> Report:
    """Read one sidecar: format, K13 extensions, schema, finite numbers, then its semantic rules. Always returns a report."""
    return read_document(document, known_extensions)


@reader_path("product", refused=lambda report, arguments: None)
def object_count(product: dict) -> int | None:
    """The number of listed objects, or None when none are listed: absent is not zero, and a native collection the sidecar
    does not enumerate has no count here."""
    objects = product.get("objects")
    return len(objects) if objects is not None and product["presence"] in ("present", "valid-empty") else None


def _dereference(reference: dict, products) -> dict | None:
    product = next((item for item in products if item["product_id"] == reference["product_id"]), None)
    if product is None or product["revision"] != reference["revision"] or product["collection"] != reference["collection"]:
        return None
    objects = product.get("objects", [])
    if "row" in reference:
        return objects[reference["row"]] if reference["row"] < len(objects) else None
    return next((item for item in objects if item["key"] == reference.get("key")), None)


@reader_path("products", refused=lambda report, arguments: None)
def dereference(reference: dict, products) -> dict | None:
    """The object a reference names, or None when it cannot be reached: inability to dereference is explicit (A08). A row
    is read inside the named product only; check_products refuses a row that crosses products."""
    return _dereference(reference, products)


def _check_reference(reference: dict, holder: dict, products, report: Report, path: str) -> None:
    target = next((item for item in products if item["product_id"] == reference["product_id"]), None)
    if "row" in reference and reference["product_id"] != holder["product_id"]:
        report.add("error", path, "reconstruction.reference.row_across_products",
                   f"row {reference['row']} of {reference['product_id']} read from {holder['product_id']}: a row is valid inside its product only")
    elif target is not None and target["revision"] != reference["revision"]:
        report.add("error", path, "reconstruction.reference.stale_revision",
                   f"revision {reference['revision']} of {reference['product_id']}; the product is at {target['revision']}")
    elif target is not None and "objects" not in target and target["presence"] == "present" and target["collection"] == reference["collection"]:
        # W1: wrong dereferencing is detected; revision and collection are known without the objects, so only the object itself is beyond reach
        report.add("warning", path, "reconstruction.reference.native_only", f"{reference['product_id']} lists no objects, so this link cannot be followed here (A08)")
    elif _dereference(reference, products) is None:
        report.add("error", path, "reconstruction.reference.dangling", f"{reference} reaches no object")
    if target is not None and target["role"] == "truth-reference" and holder["role"] in DATA_SIDE_ROLES:
        report.add("error", path, "reconstruction.product.truth_on_data_side",
                   f"{holder['product_id']} reads truth from {target['product_id']} without saying so in its role")


@reader_path("products")
def check_products(products) -> Report:
    """Identities and every source link across a set of products (W1, A08, A09)."""
    report = Report()
    identities = [product["product_id"] for product in products]
    for identity in sorted({name for name in identities if identities.count(name) > 1}):
        report.add("error", "$", "reconstruction.product.duplicate_identity", f"{identity} appears twice")
    for index, product in enumerate(products):
        for row, item in enumerate(product.get("objects", [])):
            for link, reference in enumerate(item.get("source_links", [])):
                _check_reference(reference, product, products, report, f"$[{index}].objects[{row}].source_links[{link}]")
    return report


@reader_path("product", refused=lambda report, arguments: False)
def can_recompute(product: dict, level: str) -> bool:
    """Whether information at this level can still be reached: removed information is not inferred from summaries (8.3)."""
    return product.get("retention", {}).get(level) in ("kept", "reproducible")


@reader_path("product", "payloads")
def check_frame_conditions(product: dict, payloads) -> Report:
    """W3, Section 9.3: each key uses the payload valid at that key, so the first payload never covers a whole chunk."""
    report, frames = Report(), product["frames"]
    known = {payload["payload_id"]: payload for payload in payloads}
    for index, key_output in enumerate(frames["outputs"]):
        payload = known.get(key_output["payload_id"])
        if payload is None:
            report.add("error", f"$.outputs[{index}].payload_id", "reconstruction.frames.unknown_payload", f"{key_output['payload_id']} is not among the payloads given")
        elif not conditions._iov_holds(payload["iov"], dict(frames.get("fixed_coordinates", {}), **{frames["key_coordinate"]: key_output["key"]})):
            report.add("error", f"$.outputs[{index}].payload_id", "reconstruction.frames.payload_outside_iov",
                       f"key {key_output['key']} lies outside the IOV of the payload it used")
    return report


@reader_path("first", "second", refused=lambda report, arguments: False)
def same_observable_domain(first: dict, second: dict) -> bool:
    """W3: two frame records can be compared only over the same keys, windows and gaps."""
    def domain(product):
        frames = product["frames"]
        return sorted((key_output["key"], key_output["window"]) for key_output in frames["outputs"]), sorted(frames["missing_keys"])
    return domain(first) == domain(second)


def _live_revision(candidates: dict, identity: str) -> dict | None:
    """The committed revision; Section 10.1: consumers never see an incomplete replacement."""
    return next((item for item in candidates["hypotheses"] if item["hypothesis_id"] == identity and item["state"] == "committed"), None)


@reader_path("product", refused=lambda report, arguments: [])
def selected_objects(product: dict) -> list[tuple]:
    """W4: what final counting sees, one (hypothesis, revision) per exclusive group under the selection policy."""
    candidates = product["candidates"]
    return [(identity, _live_revision(candidates, identity)["revision"])
            for _, identity in sorted(candidates["selection_policy"]["selected"].items())
            if _live_revision(candidates, identity) is not None]


def _check_candidate_link(reference: dict, products, report: Report, path: str) -> None:
    target = next((item for item in products if item["product_id"] == reference["product_id"]), None)
    if target is not None and "objects" not in target and target["presence"] == "present" and \
            (target["revision"], target["collection"]) == (reference["revision"], reference["collection"]):
        # W1: wrong dereferencing is detected; revision and collection are known without the objects, so only the object itself is beyond reach
        report.add("warning", path, "reconstruction.reference.native_only", f"{reference['product_id']} lists no objects, so this link cannot be followed here (A08)")
    elif _dereference(reference, products) is None:
        report.add("error", path, "reconstruction.candidate.dangling", f"{reference} reaches no measurement")


@reader_path("product", "products")
def check_candidate_links(product: dict, products) -> Report:
    """Every measurement of a live hypothesis still reaches an object: a dangling association is detectable after commit."""
    report = Report()
    for index, item in enumerate(product["candidates"]["hypotheses"]):
        if item["state"] in ("open", "committed"):
            for reference in item["measurements"]:
                _check_candidate_link(reference, products, report, f"$.hypotheses[{index}].measurements")
    return report


@reader_path("product", refused=lambda report, arguments: [])
def observed_intervals(product: dict) -> list[dict]:
    """W6: the intervals that are observations. A zero is one; an absent interval is not, and is never filled."""
    return [item for item in product["counts"]["intervals"] if item["presence"] == "present"]


@reader_path("recipe", refused=lambda report, arguments: False)
def runnable(recipe: dict) -> bool:
    """Whether a recipe may start a backend; a proposal never does (A16)."""
    return recipe["status"] != "proposal" and recipe["implementation"]["backend"] is not None and recipe["command"] is not None


@reader_path("first", "second")
def check_rebinding(first: dict, second: dict) -> Report:
    """A02: a profile switch keeps the method card, changes the profile and its device conditions, and stays inside the
    support domain of the new binding."""
    report = Report()
    if first["method"] != second["method"]:
        report.add("error", "$.method", "reconstruction.recipe.method_card_changed", "a rebinding refers to the same method card")
    if first["profile_binding"]["profile_id"] == second["profile_binding"]["profile_id"]:
        report.add("error", "$.profile_binding", "reconstruction.recipe.profile_not_rebound", "a profile switch names another profile")
    identities = [[record["payload_id"] for record in recipe["profile_binding"]["conditions"]] for recipe in (first, second)]
    if identities[0] and identities[0] == identities[1]:
        report.add("error", "$.profile_binding", "reconstruction.recipe.conditions_not_rebound", "a profile switch rebinds the device conditions")
    _check_support_domain(second, report, "$.profile_binding")
    return report


def recipe_identity(recipe: dict) -> str:
    """The digest evidence binds to. Status, evidence and runtime fields are outside it because evidence itself changes them,
    and the request because check 6 of Section 8.4 judges it against the tested domain. The support domain is inside it."""
    binding = {field: value for field, value in recipe["profile_binding"].items() if field not in NOT_BINDING_IDENTITY}
    return canonical_sha256(dict({field: value for field, value in recipe.items() if field not in NOT_RECIPE_IDENTITY}, profile_binding=binding))


def _check_evidence_scope(recipe: dict, evidence: dict, report: Report) -> None:
    """Section 8.4, check 6: "the tested domain must cover the request, and required checks and denominators must be
    constructible". Section 12.1: a level supports its own domain only."""
    tested = evidence["scope"]["tested_domain"]
    for axis, value in recipe["profile_binding"]["request"].items():
        if axis not in tested or not tested[axis]["min"] <= value <= tested[axis]["max"]:
            report.add("error", "$.evidence_ref", "reconstruction.recipe.request_outside_tested_domain", f"{axis}={value} is outside what {evidence['evidence_id']} tested: {evidence['scope']['statement']}")
    evidenced = {item["check_id"]: item for item in evidence["checks"]}
    for check_id in recipe["checks"]:
        item = evidenced.get(check_id)
        if item is None or item["state"] != "pass":
            report.add("error", "$.evidence_ref", "reconstruction.recipe.required_check_not_evidenced", f"{check_id} is required and {evidence['evidence_id']} did not pass it")
        elif not item["constructible"]:
            report.add("error", "$.evidence_ref", "reconstruction.recipe.required_check_not_constructible", f"{check_id} cannot be constructed for this binding")


@reader_path("recipe", "evidence")
def check_recipe_evidence(recipe: dict, evidence: dict) -> Report:
    """Section 8.4, check 6: routine use needs passed evidence for this very recipe, covering the request and its checks. A
    changed recipe inherits nothing (Section 17.3), and a witness or a smoke run supports no routine use (Section 12.1). The
    plan names no minimum stage above those: a passed simulation pilot is allowed for the domain it tested."""
    report = Report()
    if recipe["status"] != "routine":
        return report
    if evidence["state"] != "passed" or evidence["recipe_id"] != recipe["recipe_id"] or evidence["evidence_id"] != recipe["evidence_ref"]:
        report.add("error", "$.evidence_ref", "reconstruction.recipe.evidence_not_passed",
                   f"{evidence['evidence_id']} is {evidence['state']} for {evidence['recipe_id']}: not passed evidence for this recipe")
    if evidence["recipe_sha256"] != recipe_identity(recipe):
        report.add("error", "$.evidence_ref", "reconstruction.recipe.evidence_of_another_recipe", "the recipe changed since this evidence: old evidence is not inherited")
    if evidence["stage"] in NOT_ROUTINE_STAGES:
        report.add("error", "$.evidence_ref", "reconstruction.recipe.evidence_stage_insufficient", f"{evidence['stage']} evidence does not support routine use")
    _check_evidence_scope(recipe, evidence, report)
    return report


@reader_path("recipe")
def check_tool_mapping(recipe: dict, contract: dict) -> Report:
    """A41: a mapping names an operation the closed contract really has, and claims no support beyond it. The contract is an
    old closed format, so its own schema reads it."""
    report, mapping = validate(contract, "tool_contract.json"), recipe["tool_contract"]
    if not report.ok:
        return report
    if mapping is not None and (mapping["tool_id"] != contract["tool_id"]
                                or mapping["operation_id"] not in [item["operation_id"] for item in contract["operations"]]):
        report.add("error", "$.tool_contract", "reconstruction.recipe.tool_operation_missing",
                   f"{mapping['tool_id']}:{mapping['operation_id']} is not an operation of {contract['tool_id']}")
    return report


def _property_names(schema) -> set:
    """Every property name a schema declares, at any depth."""
    if isinstance(schema, list):
        return set().union(*map(_property_names, schema)) if schema else set()
    if not isinstance(schema, dict):
        return set()
    return set(schema.get("properties", {})) | _property_names(list(schema.values()))


def _reconstruction_keys(value, old_names: set, path: str = "$") -> list[str]:
    if isinstance(value, list):
        return [found for index, item in enumerate(value) for found in _reconstruction_keys(item, old_names, f"{path}[{index}]")]
    if not isinstance(value, dict):
        return []
    found = [f"{path}.{key}" for key in value if key not in old_names and (
        key in PRODUCT_BLOCKS or key in RECONSTRUCTION_ONLY_KEYS or str(key).startswith(("reconstruction:", "conditions:")))]
    return found + [item for key, inner in value.items() for item in _reconstruction_keys(inner, old_names, f"{path}.{key}")]


def check_response_free_of_semantics(document) -> Report:
    """Contract-map.md: no reconstruction semantics go into a response. The old response path cannot enforce that, since
    its schema is open and its adapter drops unknown keys, so a task that writes a response calls this on the whole artifact.
    A name an old response schema declares stays allowed at any depth."""
    report = Report()
    if not isinstance(document, dict) or document.get("artifact_type") != "response" or not isinstance(document.get("extension"), dict):
        report.add("error", "$", "reconstruction.response.not_a_response", "this check reads a whole response artifact")
        return report
    old_names = set().union(*(_property_names(load_schema(name)) for name in ("envelope.json", "ext_response.json", "ext_response_v2_8.json")))
    found = _reconstruction_keys(document, old_names)
    if found:
        report.add("error", "$", "reconstruction.response.holds_semantics", f"{found} belong in a sidecar, and an old reader would drop them")
    return report


def _check_semantics(source: dict, target: dict, report: Report, path: str) -> None:
    for field, name in CONNECTED_SEMANTICS:
        if source.get(field) != target.get(field):
            report.add("error", f"{path}.{field}", f"reconstruction.connect.{name}_mismatch",
                       f"{field} {source.get(field)!r} does not match {target.get(field)!r}: matching names or units do not establish meaning")


def _check_converter(converter: dict, report: Report) -> None:
    if converter["information_loss"] and not (converter.get("retention_ref") or converter.get("response_ref")):
        report.add("error", "$.converter", "reconstruction.converter.loss_unrecorded",
                   f"{converter['converter_id']} loses information: record it in retention or response, it is not a format change")


def _check_sample_interval(source_port: dict, target_port: dict, converter: dict | None, report: Report) -> None:
    """Section 8.4, check 2. A converter changes the interval only if it says so (contract map: its own input and output
    semantics); else the two ports must agree."""
    entering, leaving = source_port.get("sample_interval"), target_port.get("sample_interval")
    resamples = converter is not None and ("input_sample_interval" in converter or "output_sample_interval" in converter)
    agrees = _same_measure(entering, converter.get("input_sample_interval")) and _same_measure(leaving, converter.get("output_sample_interval")) \
        if resamples else _same_measure(entering, leaving)
    if not agrees:
        report.add("error", "$.sample_interval", "reconstruction.connect.sample_interval_mismatch", f"sample interval {entering} does not reach {leaving}")


@reader_path("source_port", "target_port")
def check_connection(source_port: dict, target_port: dict, converter: dict | None = None,
                     known_extensions=KNOWN_EXTENSIONS) -> Report:
    """The contract-level parts of the connection checks of plan Section 8.4, from an output port to an input port:
    structure, semantics including the sample interval (through a declared converter when one is given), roles and
    execution. Conditions and quality are judged where their records are: contracts.conditions.check_binding and
    check_recipe_evidence."""
    report = Report()
    if converter is not None:
        validate(converter, {"$ref": "reconstruction_common.json#/$defs/converter"}, report=report, path="$.converter")
        if not report.ok:
            return report
    if source_port["direction"] != "output" or target_port["direction"] != "input":
        report.add("error", "$", "reconstruction.connect.direction", "a connection runs from an output port to an input port")
    if source_port["native"]["type"] != target_port["native"]["type"] and converter is None:
        report.add("error", "$.native", "reconstruction.connect.native_type_mismatch",
                   f"{source_port['native']['type']} is not {target_port['native']['type']}")
    if source_port["cardinality"] == "many" and target_port["cardinality"] != "many":
        report.add("error", "$.cardinality", "reconstruction.connect.cardinality_mismatch", "a collection cannot feed a single-object port")
    unaccepted = sorted(set(source_port["presence"]) - set(target_port["presence"]))
    if unaccepted:
        report.add("error", "$.presence", "reconstruction.connect.presence_not_accepted",
                   f"the output can be {unaccepted}, which the input does not accept; absent and invalid never pass as empty")
    if converter is None:
        _check_semantics(source_port["quantity"], target_port["quantity"], report, "$.quantity")
    else:
        _check_converter(converter, report)
        _check_semantics(source_port["quantity"], converter["input"], report, "$.converter.input")
        _check_semantics(converter["output"], target_port["quantity"], report, "$.converter.output")
    # Section 8.4 check 3: data-side ports do not depend on truth, so truth may reach any other port (validation compares with
    # it); it asks that roles be explicit, not equal, so reconstruction output may feed validation and calibration. K08 keeps
    # the sample roles apart, the one further refusal here.
    if source_port["role"] == "truth-reference" and target_port["role"] in DATA_SIDE_ROLES:
        report.add("error", "$.role", "reconstruction.connect.truth_on_data_side", "a truth role cannot feed a data-side port (A09)")
    elif {source_port["role"], target_port["role"]} == SEPARATE_SAMPLE_ROLES:
        report.add("error", "$.role", "reconstruction.connect.role_mismatch", f"role {source_port['role']} does not feed role {target_port['role']}: sample roles stay separate (K08)")
    _check_sample_interval(source_port, target_port, converter, report)
    source_mode = source_port.get("execution", {}).get("concurrency")
    if source_mode == "serialized" and target_port.get("execution", {}).get("concurrency") == "reentrant":
        report.add("error", "$.execution", "reconstruction.connect.unsafe_execution",
                   "a serialized producer cannot feed a port that expects reentrant execution")
    return report

