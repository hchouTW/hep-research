"""acts-tracking-product/1 and /2 in Python: read, write, reorder, subset, merge, and the map to reconstruction-product/1.

/2 (D1 stage 8) is the refit's: /1's records unchanged, plus R33's outputs of the track fit under the conventions t07-r33/1 of
native/track_fit_outputs.hpp: a track_output per fitted track, four residual records per measurement state (predicted, filtered,
smoothed, unbiased; never mixed, BP03) and a measurement_output per state with a hit (measurement or outlier), a residual_covariance per
fitted track, and the header lines r33_conventions and alignment_parametrization. /1 is still read, as every earlier job wrote it.
The reader refuses a /2 product that lacks any R33 record a measurement or a fitted track needs (r33_outputs lists them). The residual
algebra here (residual_of, unbiased_from_smoothed) is this module's own, so recomputed_residuals is a check of the driver's, not a copy.

This is the format of native/native_product.*, the driver's own, because the ACTS package has no persistence layer
(t07-t09-task-sheets.md, Output). Plan Section 8.3 asks that native reference mappings survive round trip, reordering,
subsetting and merging, so objects are found by product identity, collection, key and revision, never by row (W1). The reader
stops at anything it does not know, and refuses a failed track without its category: nothing leaves a denominator.

The map writes reconstruction-product/1 sidecars, with no new contract (contract-map.md, Existing schemas; K04). One
collection per product id, as contracts.reconstruction.dereference reads them: `<id>.tracks` and `<id>.track-states`. A refit of
a known hit set is truth-assisted (BP03; t04-values-v4.md section 8.1), so its sidecars carry role validation and never a
data-side role. Standard library only.
"""
from __future__ import annotations

import math

PRODUCT_FORMAT = "acts-tracking-product/1"
PRODUCT_FORMAT_R33 = "acts-tracking-product/2"
R33_CONVENTIONS = "t07-r33/1"
RESIDUAL_TYPES = ("predicted", "filtered", "smoothed", "unbiased")
R32_PLANE_PARAMETERS = ("shift-loc0", "shift-loc1", "shift-normal", "rotation-loc0", "rotation-loc1", "rotation-normal")  # t07-plane-rigid/1
TOPOLOGIES = ("collision", "cosmic", "resonance-candidate")
CONSTRAINTS = ("none", "beam", "vertex")
R33_COLLECTIONS = ("track_outputs", "residuals", "measurement_outputs", "residual_covariances")
ALIGNMENT_PARAMETRIZATION = ["t07-plane-rigid/1", "local", "sensor"]  # name, frame, level (R32)
R33_HEADER_FIELDS = ("r33_conventions", "alignment_parametrization")
# What R33 asks per measurement and per track, as r33_outputs returns it; every key must be there for every measurement of a /2 product.
R33_MEASUREMENT_FIELDS = ("surface", "geometry_id", "measurement", "measurement_covariance", "residuals", "local_derivative", "reference_derivative", "alignment_derivative",
                          "local_slope", "incidence_rad", "sensitive_path_mm", "path_factor", "thickness_mm")
R33_TRACK_FIELDS = ("charge", "charge_status", "q_over_p", "q_over_p_variance", "reference_state_index", "topology", "constraint", "field", "residual_covariance")
TEXT_HEADER_FIELDS = ("product_id", "revision", "recipe", "stage", "evidence_class", "data_product", "data_sha256", "hit_sets_sha256",
                      "field_tesla", "qop_status", "material_model", "start_prior", "acts_version")
STATE_KINDS = ("measurement", "hole", "outlier")
STATE_TYPES = ("predicted", "filtered", "smoothed")
PARAMETER_COUNT, COVARIANCE_COUNT = 6, 21
FINDING_STAGE = "find-ckf"  # the only stage reported as finding, and only with evidence class data-side (BP03)
# Only the fields of a product that say what was fitted; two products that differ here cannot be merged into one.
MERGE_IDENTITY_FIELDS = ("recipe", "stage", "evidence_class", "data_product", "data_sha256", "field_tesla", "qop_status", "material_model",
                         "start_prior", "acts_version")


class ProductFormatError(ValueError):
    """The text is not acts-tracking-product/1 or /2, or an operation would break a reference."""


def _number(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise ProductFormatError(f"not a finite number: {token}")
    return value


def _number_text(value: float) -> str:
    if not math.isfinite(value):
        raise ProductFormatError("a product holds finite numbers only")
    return "%.17g" % value


def _header_from_lines(lines, fields=TEXT_HEADER_FIELDS) -> dict:
    header = {}
    for name, line in zip(fields, lines):
        tokens = line.split(" ")
        if tokens[0] != name:
            raise ProductFormatError(f"expected the record {name}, found {tokens[0]}")
        header[name] = tokens[1:]
    if len(header) != len(fields):
        raise ProductFormatError("the product ends inside its header")
    for name, values in header.items():
        if len(values) != {"start_prior": 5, "alignment_parametrization": 3}.get(name, 1):
            raise ProductFormatError(f"{name} has {len(values)} values")
    parsed = {name: values[0] for name, values in header.items()}
    if "alignment_parametrization" in header:
        parsed["alignment_parametrization"] = header["alignment_parametrization"]
    parsed["revision"] = int(parsed["revision"])
    if parsed["revision"] < 1:
        raise ProductFormatError("a revision starts at 1")
    parsed["field_tesla"] = _number(parsed["field_tesla"])
    parsed["start_prior"] = [_number(token) for token in header["start_prior"]]
    if (parsed["field_tesla"] == 0.0) != (parsed["qop_status"] == "assumed-not-measured"):
        raise ProductFormatError("q/p is assumed at zero field, and only there")
    return parsed


def _track_record(tokens) -> dict:
    status, category = tokens[3], tokens[4]
    if status not in ("fitted", "failed"):
        raise ProductFormatError(f"unknown track status {status}")
    if (status == "failed") == (category == "none"):
        raise ProductFormatError("a failed track states its category, and only a failed track")
    return {"key": tokens[1], "event_ordinal": int(tokens[2]), "status": status, "failure_category": category,
            "measurements": int(tokens[5]), "holes": int(tokens[6]), "outliers": int(tokens[7]), "chi2": _number(tokens[8]),
            "measured_coordinates": int(tokens[9]), "assumed_q_over_p": _number(tokens[10])}


def _state_record(tokens) -> dict:
    kind = tokens[4]
    if kind not in STATE_KINDS:
        raise ProductFormatError(f"unknown state kind {kind}")
    hit_key = None if tokens[5] == "none" else int(tokens[5])
    if hit_key is not None and hit_key < 0:
        raise ProductFormatError("a hit key is not negative")
    if (kind == "hole") != (hit_key is None):
        raise ProductFormatError("a hole has no hit, and every other state has one")
    return {"track_key": tokens[1], "index": int(tokens[2]), "plane": int(tokens[3]), "kind": kind, "hit_key": hit_key,
            "loc0_mm": _number(tokens[6]), "loc1_mm": _number(tokens[7]), "covariance": [_number(token) for token in tokens[8:11]],
            "path_length_mm": _number(tokens[11]), "chi2": _number(tokens[12])}


def _parameter_record(tokens) -> dict:
    state_type = tokens[3]
    if state_type not in STATE_TYPES:
        raise ProductFormatError(f"unknown state type {state_type}")
    return {"track_key": tokens[1], "state_index": int(tokens[2]), "state_type": state_type,
            "parameters": [_number(token) for token in tokens[4:10]], "covariance": [_number(token) for token in tokens[10:31]]}


def _track_output_record(tokens) -> dict:
    return {"track_key": tokens[1], "charge": int(tokens[2]), "q_over_p": _number(tokens[3]), "q_over_p_variance": _number(tokens[4]),
            "reference_state_index": int(tokens[5]), "topology": tokens[6], "constraint": tokens[7], "field": tokens[8]}


def _residual_record(tokens) -> dict:
    if tokens[3] not in RESIDUAL_TYPES:
        raise ProductFormatError(f"unknown residual type {tokens[3]}")
    return {"track_key": tokens[1], "state_index": int(tokens[2]), "state_type": tokens[3], "residual": [_number(token) for token in tokens[4:6]],
            "covariance": [_number(token) for token in tokens[6:9]]}


def _measurement_output_record(tokens) -> dict:
    geometry_id = int(tokens[3])
    if geometry_id <= 0:
        raise ProductFormatError("a geometry identifier is positive")
    return {"track_key": tokens[1], "state_index": int(tokens[2]), "geometry_id": geometry_id, "projector": [int(tokens[4]), int(tokens[5])],
            "local_slope": [_number(tokens[6]), _number(tokens[7])], "incidence_rad": _number(tokens[8]), "thickness_mm": _number(tokens[9]),
            "path_factor": _number(tokens[10]), "sensitive_path_mm": _number(tokens[11]), "alignment_derivative": [_number(token) for token in tokens[12:24]],
            "reference_derivative": [_number(token) for token in tokens[24:36]]}


def _residual_covariance_record(tokens) -> dict:
    count = int(tokens[2])
    if count < 1 or len(tokens) != 3 + (2 * count) * (2 * count + 1) // 2:
        raise ProductFormatError("a residual_covariance of the wrong size")
    return {"track_key": tokens[1], "measurement_count": count, "covariance": [_number(token) for token in tokens[3:]]}


RECORD_READERS = {"track": (11, _track_record, "tracks"), "state": (13, _state_record, "states"), "parameters": (31, _parameter_record, "parameters")}
R33_RECORD_READERS = {"track_output": (9, _track_output_record, "track_outputs"), "residual": (9, _residual_record, "residuals"),
                      "measurement_output": (36, _measurement_output_record, "measurement_outputs"),
                      "residual_covariance": (None, _residual_covariance_record, "residual_covariances")}  # its size follows its count


def _check_links(document: dict) -> None:
    keys = [track["key"] for track in document["tracks"]]
    if len(keys) != len(set(keys)):
        raise ProductFormatError("a track key appears twice")
    states = [(state["track_key"], state["index"]) for state in document["states"]]
    if len(states) != len(set(states)):
        raise ProductFormatError("a state appears twice")
    if not {key for key, _ in states} <= set(keys):
        raise ProductFormatError("a state of an unknown track")
    records = [(item["track_key"], item["state_index"], item["state_type"]) for item in document["parameters"]]
    if len(records) != len(set(records)):
        raise ProductFormatError("parameters appear twice")
    if not {record[:2] for record in records} <= set(states):
        raise ProductFormatError("parameters of an unknown state")
    if document.get("format", PRODUCT_FORMAT) == PRODUCT_FORMAT_R33:
        defects = r33_defects(document)
        if defects:
            raise ProductFormatError(defects[0])


def r33_defects(document: dict) -> list:
    """Everything a /2 product's R33 records lack or hold wrongly, as the native reader refuses it (native_product.cpp)."""
    defects = []
    kind_of = {(state["track_key"], state["index"]): state["kind"] for state in document["states"]}
    status_of = {track["key"]: track["status"] for track in document["tracks"]}
    measurements = {key for key, kind in kind_of.items() if kind == "measurement"}
    with_hits = {key for key, kind in kind_of.items() if kind in ("measurement", "outlier")}
    if document["header"].get("r33_conventions") != R33_CONVENTIONS:
        defects.append("the header does not name the R33 conventions")
    if document["header"].get("alignment_parametrization") != ALIGNMENT_PARAMETRIZATION:
        defects.append("the header does not name the alignment parametrization t07-plane-rigid/1, local, sensor")
    field = "off" if document["header"]["field_tesla"] == 0.0 else "on"
    outputs = [item["track_key"] for item in document["track_outputs"]]
    if len(outputs) != len(set(outputs)):
        defects.append("a track_output twice")
    for item in document["track_outputs"]:
        if status_of.get(item["track_key"]) != "fitted":
            defects.append(f"a track_output of a track that is not fitted: {item['track_key']}")
        if item["charge"] not in (1, -1) or (item["charge"] > 0) != (item["q_over_p"] > 0.0) or not item["q_over_p_variance"] > 0.0:
            defects.append(f"charge, q/p or its variance wrong in {item['track_key']}")
        if item["topology"] not in TOPOLOGIES or item["constraint"] not in CONSTRAINTS or item["field"] != field:
            defects.append(f"topology, constraint or field wrong in {item['track_key']}")
        if (item["track_key"], item["reference_state_index"]) not in measurements:
            defects.append(f"a reference state that is not a measurement in {item['track_key']}")
    missing_outputs = sorted(key for key, status in status_of.items() if status == "fitted" and key not in set(outputs))
    if missing_outputs:
        defects.append(f"fitted tracks without their track_output: {missing_outputs[:3]}")
    residual_keys = [(item["track_key"], item["state_index"], item["state_type"]) for item in document["residuals"]]
    if len(residual_keys) != len(set(residual_keys)):
        defects.append("a residual twice")
    output_keys = [(item["track_key"], item["state_index"]) for item in document["measurement_outputs"]]
    if len(output_keys) != len(set(output_keys)):
        defects.append("a measurement_output twice")
    if not {key[:2] for key in residual_keys} <= with_hits or not set(output_keys) <= with_hits:
        defects.append("an R33 record of a state that holds no hit")
    if set(residual_keys) != {key + (state_type,) for key in with_hits for state_type in RESIDUAL_TYPES}:
        defects.append("a state with a hit without one of its four residuals")
    if set(output_keys) != with_hits:
        defects.append("a state with a hit without its measurement_output")
    measured_of = {}
    for track_key, _ in measurements:
        measured_of[track_key] = measured_of.get(track_key, 0) + 1
    covariance_keys = [item["track_key"] for item in document["residual_covariances"]]
    if len(covariance_keys) != len(set(covariance_keys)):
        defects.append("a residual_covariance twice")
    for item in document["residual_covariances"]:
        if status_of.get(item["track_key"]) != "fitted" or item["measurement_count"] != measured_of.get(item["track_key"], 0):
            defects.append(f"a residual_covariance that does not cover a fitted track's measurements: {item['track_key']}")
    wanted = {key for key, status in status_of.items() if status == "fitted" and measured_of.get(key, 0) > 0}
    if set(covariance_keys) != wanted:
        defects.append("a fitted track without its residual_covariance")
    return defects


def parse_product(text: str) -> dict:
    """A whole product as a dict, or ProductFormatError. A count in the end record catches a truncated file."""
    lines = text.split("\n")
    if lines[-1] != "":
        raise ProductFormatError("the last line is not finished")
    lines = lines[:-1]
    if not lines or lines[0] not in (PRODUCT_FORMAT, PRODUCT_FORMAT_R33):
        raise ProductFormatError(f"not {PRODUCT_FORMAT} or {PRODUCT_FORMAT_R33}")
    with_r33 = lines[0] == PRODUCT_FORMAT_R33
    fields = TEXT_HEADER_FIELDS + (R33_HEADER_FIELDS if with_r33 else ())
    readers = dict(RECORD_READERS, **(R33_RECORD_READERS if with_r33 else {}))
    collections = ("tracks", "states", "parameters") + (R33_COLLECTIONS if with_r33 else ())
    width = len(fields)
    try:
        document = {"header": _header_from_lines(lines[1:1 + width], fields)}
        if with_r33:  # a /1 document stays the dict it always was: no format key means /1
            document = {"format": PRODUCT_FORMAT_R33, **document}
        document.update({name: [] for name in collections})
        counted = None
        for line in lines[1 + width:]:
            if counted is not None:
                raise ProductFormatError("text after the end record")
            tokens = line.split(" ")
            if tokens[0] == "end" and len(tokens) == 1 + len(collections):
                counted = [int(token) for token in tokens[1:]]
                continue
            size, read_record, collection = readers.get(tokens[0], (0, None, None))
            if read_record is None or (size is not None and size != len(tokens)) or (size is None and len(tokens) < 3):
                raise ProductFormatError(f"unknown record {tokens[0]}")
            document[collection].append(read_record(tokens))
    except (IndexError, ValueError) as error:
        if isinstance(error, ProductFormatError):
            raise
        raise ProductFormatError(str(error)) from error
    if counted is None:
        raise ProductFormatError("the product ends before its end record")
    if counted != [len(document[name]) for name in collections]:
        raise ProductFormatError("the end record counts other numbers than the product holds")
    _check_links(document)
    return document


def format_product(document: dict) -> str:
    """The exact bytes the driver writes for this document."""
    header = document["header"]
    version = document.get("format", PRODUCT_FORMAT)
    if version not in (PRODUCT_FORMAT, PRODUCT_FORMAT_R33):
        raise ProductFormatError(f"unknown version {version}")
    with_r33 = version == PRODUCT_FORMAT_R33
    if not with_r33 and any(document.get(name) for name in R33_COLLECTIONS):
        raise ProductFormatError("R33 records belong to acts-tracking-product/2 only")
    lines = [version]
    for name in TEXT_HEADER_FIELDS + (R33_HEADER_FIELDS if with_r33 else ()):
        if name == "start_prior":
            lines.append(" ".join(["start_prior"] + [_number_text(value) for value in header[name]]))
        elif name == "alignment_parametrization":
            lines.append(" ".join([name] + list(header[name])))
        elif name == "field_tesla":
            lines.append(f"field_tesla {_number_text(header[name])}")
        else:
            lines.append(f"{name} {header[name]}")
    for track in document["tracks"]:
        lines.append(" ".join(["track", track["key"], str(track["event_ordinal"]), track["status"], track["failure_category"], str(track["measurements"]),
                               str(track["holes"]), str(track["outliers"]), _number_text(track["chi2"]), str(track["measured_coordinates"]),
                               _number_text(track["assumed_q_over_p"])]))
    for state in document["states"]:
        hit_text = "none" if state["hit_key"] is None else str(state["hit_key"])
        numbers = [state["loc0_mm"], state["loc1_mm"], *state["covariance"], state["path_length_mm"], state["chi2"]]
        lines.append(" ".join(["state", state["track_key"], str(state["index"]), str(state["plane"]), state["kind"], hit_text]
                              + [_number_text(value) for value in numbers]))
    for item in document["parameters"]:
        lines.append(" ".join(["parameters", item["track_key"], str(item["state_index"]), item["state_type"]]
                              + [_number_text(value) for value in item["parameters"] + item["covariance"]]))
    end = [len(document["tracks"]), len(document["states"]), len(document["parameters"])]
    if with_r33:
        for item in document["track_outputs"]:
            lines.append(" ".join(["track_output", item["track_key"], str(item["charge"]), _number_text(item["q_over_p"]), _number_text(item["q_over_p_variance"]),
                                   str(item["reference_state_index"]), item["topology"], item["constraint"], item["field"]]))
        for item in document["residuals"]:
            lines.append(" ".join(["residual", item["track_key"], str(item["state_index"]), item["state_type"]]
                                  + [_number_text(value) for value in item["residual"] + item["covariance"]]))
        for item in document["measurement_outputs"]:
            numbers = (item["local_slope"] + [item["incidence_rad"], item["thickness_mm"], item["path_factor"], item["sensitive_path_mm"]] + item["alignment_derivative"]
                       + item["reference_derivative"])
            lines.append(" ".join(["measurement_output", item["track_key"], str(item["state_index"]), str(item["geometry_id"]), str(item["projector"][0]), str(item["projector"][1])]
                                  + [_number_text(value) for value in numbers]))
        for item in document["residual_covariances"]:
            lines.append(" ".join(["residual_covariance", item["track_key"], str(item["measurement_count"])] + [_number_text(value) for value in item["covariance"]]))
        end += [len(document[name]) for name in R33_COLLECTIONS]
    lines.append("end " + " ".join(str(count) for count in end))
    return "\n".join(lines) + "\n"


def _with_tracks(document: dict, track_keys, product_id: str, revision: int) -> dict:
    """The same objects in the order of track_keys, under a stated identity. A derived product is a new identity or a new revision."""
    by_key = {track["key"]: track for track in document["tracks"]}
    missing = [key for key in track_keys if key not in by_key]
    if missing or len(set(track_keys)) != len(track_keys):
        raise ProductFormatError(f"not a selection of this product's tracks: {missing or 'a key twice'}")
    order = {key: position for position, key in enumerate(track_keys)}
    states = sorted((state for state in document["states"] if state["track_key"] in order), key=lambda state: (order[state["track_key"]], state["index"]))
    parameters = sorted((item for item in document["parameters"] if item["track_key"] in order),
                        key=lambda item: (order[item["track_key"]], item["state_index"], STATE_TYPES.index(item["state_type"])))
    selected = {"header": dict(document["header"], product_id=product_id, revision=revision), "tracks": [by_key[key] for key in track_keys], "states": states,
                "parameters": parameters}
    if document.get("format", PRODUCT_FORMAT) == PRODUCT_FORMAT_R33:
        selected = {"format": PRODUCT_FORMAT_R33, **selected}
        selected["track_outputs"] = sorted((item for item in document["track_outputs"] if item["track_key"] in order), key=lambda item: order[item["track_key"]])
        selected["residuals"] = sorted((item for item in document["residuals"] if item["track_key"] in order),
                                       key=lambda item: (order[item["track_key"]], item["state_index"], RESIDUAL_TYPES.index(item["state_type"])))
        selected["measurement_outputs"] = sorted((item for item in document["measurement_outputs"] if item["track_key"] in order),
                                                 key=lambda item: (order[item["track_key"]], item["state_index"]))
        selected["residual_covariances"] = sorted((item for item in document["residual_covariances"] if item["track_key"] in order), key=lambda item: order[item["track_key"]])
    return selected


def reorder_tracks(document: dict, track_keys) -> dict:
    """All tracks, in a new order: same identity and revision, because no object changed."""
    if set(track_keys) != {track["key"] for track in document["tracks"]}:
        raise ProductFormatError("a reordering holds every track")
    return _with_tracks(document, track_keys, document["header"]["product_id"], document["header"]["revision"])


def subset_tracks(document: dict, track_keys, product_id: str) -> dict:
    """Some tracks, under a new identity: a subset is not the product it came from."""
    if product_id == document["header"]["product_id"]:
        raise ProductFormatError("a subset takes its own product identity")
    return _with_tracks(document, track_keys, product_id, 1)


def merge_products(first: dict, second: dict, product_id: str) -> dict:
    """Two products of one fit configuration and one data file, under a new identity. Keys that collide are refused: two
    products may both hold key 0 (W1), and renaming here would cut the mapping to their sources."""
    if first.get("format", PRODUCT_FORMAT) != second.get("format", PRODUCT_FORMAT):
        raise ProductFormatError("the products are of two versions")
    for name in MERGE_IDENTITY_FIELDS + (R33_HEADER_FIELDS if first.get("format") == PRODUCT_FORMAT_R33 else ()):
        if first["header"][name] != second["header"][name]:
            raise ProductFormatError(f"the products differ in {name}, so one header cannot describe both")
    shared = {track["key"] for track in first["tracks"]} & {track["key"] for track in second["tracks"]}
    if shared:
        raise ProductFormatError(f"both products hold the keys {sorted(shared)}")
    if product_id in (first["header"]["product_id"], second["header"]["product_id"]):
        raise ProductFormatError("a merge takes its own product identity")
    hit_sets_sha256 = "+".join((first["header"]["hit_sets_sha256"], second["header"]["hit_sets_sha256"]))  # both stay on record
    header = dict(first["header"], product_id=product_id, revision=1, hit_sets_sha256=hit_sets_sha256)
    merged = {"header": header, "tracks": first["tracks"] + second["tracks"], "states": first["states"] + second["states"],
              "parameters": first["parameters"] + second["parameters"]}
    if first.get("format", PRODUCT_FORMAT) == PRODUCT_FORMAT_R33:
        merged = {"format": PRODUCT_FORMAT_R33, **merged, **{name: first[name] + second[name] for name in R33_COLLECTIONS}}
    _check_links(merged)
    return merged


def state_key(track_key: str, state_index: int, state_type: str) -> str:
    return f"{track_key}/state-{state_index}/{state_type}"


def measurement_key(event_ordinal: int, hit_key: int) -> str:
    return f"event-{event_ordinal}/hit-{hit_key}"


def measurement_view_id(header: dict) -> str:
    """The sidecar lists only the measurements one product reaches, so it is a view with its own identity, not the data file's:
    two refits of one file then read together."""
    return f"{header['data_product']}.view.{header['product_id']}"


def _sidecar_base(product_id: str, revision: int, collection: str, role: str, objects: list, native_location: str, native_type: str = PRODUCT_FORMAT) -> dict:
    document = {"schema": "reconstruction-product/1", "product_id": product_id, "revision": revision, "collection": collection,
                "native": {"type": native_type, "location": native_location}, "presence": "present" if objects else "valid-empty",
                "role": role, "objects": objects, "conditions_used": [], "required_extensions": []}
    return document


def sidecars_for_product(document: dict, native_location: str) -> list:
    """reconstruction-product/1 for the tracks and the per-surface states. Predicted, filtered and smoothed are separate objects,
    told apart by state_type (BP03). A failed track stays an object. Role validation: truth-assisted, off the data side."""
    header = document["header"]
    if header["evidence_class"] != "truth-assisted" or header["stage"] != "refit-known-hit-set":
        raise ProductFormatError("this stage maps refits of known hit sets only")
    revision, base_id = header["revision"], header["product_id"]
    ordinal_of = {track["key"]: track["event_ordinal"] for track in document["tracks"]}
    state_of = {(state["track_key"], state["index"]): state for state in document["states"]}
    # state_type means predicted, filtered or smoothed (W1), so a track has none. The closed schema has no field for an outcome, and
    # it reaches the sidecar in the typed native reference: track:<key>:<status>:<failure category>.
    track_objects = [{"key": track["key"], "native_ref": f"track:{track['key']}:{track['status']}:{track['failure_category']}"} for track in document["tracks"]]
    state_objects = []
    for item in document["parameters"]:
        state = state_of[(item["track_key"], item["state_index"])]
        entry = {"key": state_key(item["track_key"], item["state_index"], item["state_type"]),
                 "native_ref": f"parameters:{item['track_key']}:{item['state_index']}:{item['state_type']}",
                 "surface": f"plane-{state['plane']}", "state_type": item["state_type"]}
        if state["hit_key"] is not None:
            entry["source_links"] = [{"product_id": measurement_view_id(header), "collection": "measurements", "revision": 1,
                                      "key": measurement_key(ordinal_of[item["track_key"]], state["hit_key"])}]
        state_objects.append(entry)
    native_type = document.get("format", PRODUCT_FORMAT)
    return [_sidecar_base(f"{base_id}.tracks", revision, "tracks", "validation", track_objects, native_location, native_type),
            _sidecar_base(f"{base_id}.track-states", revision, "track-states", "validation", state_objects, native_location, native_type)]


def measurement_sidecar(document: dict, native_location: str) -> dict:
    """The measurements a product's states reach, with role reconstruction-input: no field of them comes from truth. A view of the
    data file: native location names the file itself."""
    ordinal_of = {track["key"]: track["event_ordinal"] for track in document["tracks"]}
    objects = {}
    for state in document["states"]:
        if state["hit_key"] is not None:
            key = measurement_key(ordinal_of[state["track_key"]], state["hit_key"])
            objects[key] = {"key": key, "native_ref": f"hit:{key}", "surface": f"plane-{state['plane']}"}
    sidecar = _sidecar_base(measurement_view_id(document["header"]), 1, "measurements", "reconstruction-input", list(objects.values()), native_location)
    sidecar["native"]["type"] = "t07-data-file/1"
    return sidecar


def fit_summary(document: dict) -> dict:
    """What a reader must see first: the evidence class, the failures, and that zero field measures no q/p."""
    header = document["header"]
    failed = [track for track in document["tracks"] if track["status"] == "failed"]
    finding = header["stage"] == FINDING_STAGE and header["evidence_class"] == "data-side"
    return {"evidence_class": header["evidence_class"], "stage": header["stage"], "reported_as_finding": finding, "tracks": len(document["tracks"]),
            "failed": len(failed), "failure_categories": sorted({track["failure_category"] for track in failed}), "qop_status": header["qop_status"]}


# ---- R33 (t07-r33/1): the residual algebra, this module's own, and the reading of a /2 product's outputs.

def residual_of(measurement, measurement_covariance, projected_state, projected_covariance, state_holds_the_hit: bool) -> tuple:
    """r = m - H x, R = V + H C H^T without the hit (predicted), V - H C H^T with it (filtered, smoothed). Covariances as (00, 01, 11)."""
    sign = -1.0 if state_holds_the_hit else 1.0
    value = (measurement[0] - projected_state[0], measurement[1] - projected_state[1])
    return value, tuple(measurement_covariance[index] + sign * projected_covariance[index] for index in range(3))


def unbiased_from_smoothed_1d(smoothed: float, smoothed_variance: float, measurement_variance: float) -> tuple:
    """One coordinate: r* = V r_s / R_s, R* = V^2 / R_s."""
    return measurement_variance * smoothed / smoothed_variance, measurement_variance ** 2 / smoothed_variance


def unbiased_from_smoothed(smoothed, smoothed_covariance, measurement_covariance) -> tuple:
    """r* = V R_s^-1 r_s, R* = V R_s^-1 V, in 2 x 2 algebra written out. Covariances as (00, 01, 11)."""
    a, b, d = smoothed_covariance
    determinant = a * d - b * b
    weight = ((d / determinant, -b / determinant), (-b / determinant, a / determinant))
    v = ((measurement_covariance[0], measurement_covariance[1]), (measurement_covariance[1], measurement_covariance[2]))
    weighted = (weight[0][0] * smoothed[0] + weight[0][1] * smoothed[1], weight[1][0] * smoothed[0] + weight[1][1] * smoothed[1])
    value = (v[0][0] * weighted[0] + v[0][1] * weighted[1], v[1][0] * weighted[0] + v[1][1] * weighted[1])
    vw = [[sum(v[row][inner] * weight[inner][column] for inner in range(2)) for column in range(2)] for row in range(2)]
    product = [[sum(vw[row][inner] * v[inner][column] for inner in range(2)) for column in range(2)] for row in range(2)]
    return value, (product[0][0], 0.5 * (product[0][1] + product[1][0]), product[1][1])


def recomputed_residuals(document: dict) -> dict:
    """{(track_key, state_index, residual type): (r, R)} from the product's own hits and states, for every measurement state."""
    states = {(state["track_key"], state["index"]): state for state in document["states"] if state["kind"] in ("measurement", "outlier")}
    by_type = {(item["track_key"], item["state_index"], item["state_type"]): item for item in document["parameters"]}
    recomputed = {}
    for key, state in states.items():
        measurement, covariance = (state["loc0_mm"], state["loc1_mm"]), state["covariance"]
        for state_type in STATE_TYPES:
            item = by_type[key + (state_type,)]
            projected = (item["parameters"][0], item["parameters"][1])
            projected_covariance = (item["covariance"][0], item["covariance"][1], item["covariance"][6])  # (0, 0), (0, 1), (1, 1) of the upper triangle
            holds_the_hit = state_type != "predicted" and state["kind"] == "measurement"  # an outlier's states never hold its hit
            recomputed[key + (state_type,)] = residual_of(measurement, covariance, projected, projected_covariance, holds_the_hit)
        smoothed = recomputed[key + ("smoothed",)]
        recomputed[key + ("unbiased",)] = unbiased_from_smoothed(*smoothed, covariance) if state["kind"] == "measurement" else smoothed
    return recomputed


def residual_record_defects(document: dict, relative: float, absolute_mm: float) -> list:
    """Each residual record that differs from recomputed_residuals by more than relative x its size plus absolute_mm (absolute_mm^2 in a covariance)."""
    recomputed = recomputed_residuals(document)
    defects = []
    for item in document["residuals"]:
        value, covariance = recomputed[(item["track_key"], item["state_index"], item["state_type"])]
        scale = math.sqrt(abs(covariance[0]) + abs(covariance[2]))
        bad_value = any(abs(item["residual"][index] - value[index]) > relative * scale + absolute_mm for index in range(2))
        bad_covariance = any(abs(item["covariance"][index] - covariance[index]) > relative * scale ** 2 + absolute_mm ** 2 for index in range(3))
        if bad_value or bad_covariance:
            defects.append(f"{item['track_key']} state {item['state_index']} {item['state_type']}: {item['residual']} {item['covariance']} against {value} {covariance}")
    return defects


def closed_form_residual_derivative(local_position, local_direction) -> list:
    """dr/da in t07-plane-rigid/1, rows loc0 and loc1, as track_fit_outputs.hpp's closed form (its comment says why)."""
    slope0, slope1 = local_direction[0] / local_direction[2], local_direction[1] / local_direction[2]
    l0, l1 = float(local_position[0]), float(local_position[1])
    change = ((-1.0, 0.0, slope0, slope0 * l1, -slope0 * l0, l1), (0.0, -1.0, slope1, slope1 * l1, -slope1 * l0, -l0))
    return [[-value for value in row] for row in change]


def r33_outputs(document: dict) -> dict:
    """R33's outputs of a /2 product, by measurement (track key, state index) and by track, with every field R33_MEASUREMENT_FIELDS and R33_TRACK_FIELDS name."""
    if document.get("format") != PRODUCT_FORMAT_R33:
        raise ProductFormatError("R33 outputs are in acts-tracking-product/2 only")
    residuals = {}
    for item in document["residuals"]:
        residuals.setdefault((item["track_key"], item["state_index"]), {})[item["state_type"]] = {"residual": item["residual"], "covariance": item["covariance"]}
    states = {(state["track_key"], state["index"]): state for state in document["states"]}
    measurements = {}
    for item in document["measurement_outputs"]:
        key = (item["track_key"], item["state_index"])
        state = states[key]
        local = [[-1.0 if column == item["projector"][row] else 0.0 for column in range(6)] for row in range(2)]  # dr/dx = -H
        derivative = item["alignment_derivative"]
        reference = item["reference_derivative"]
        measurements[key] = {"surface": f"plane-{state['plane']}", "geometry_id": item["geometry_id"], "measurement": [state["loc0_mm"], state["loc1_mm"]],
                             "measurement_covariance": state["covariance"], "residuals": residuals.get(key, {}), "local_derivative": local,
                             "reference_derivative": [reference[:6], reference[6:]],
                             "alignment_derivative": [derivative[:6], derivative[6:]], "local_slope": item["local_slope"], "incidence_rad": item["incidence_rad"],
                             "sensitive_path_mm": item["sensitive_path_mm"], "path_factor": item["path_factor"], "thickness_mm": item["thickness_mm"]}
    covariances = {item["track_key"]: residual_covariance_matrix(item) for item in document["residual_covariances"]}
    charge_status = "measured" if document["header"]["qop_status"] == "measured" else "assumed"  # at zero field the charge is the assumed q/p's sign
    tracks = {item["track_key"]: dict({name: item[name] for name in R33_TRACK_FIELDS if name in item}, charge_status=charge_status,
                                      residual_covariance=covariances.get(item["track_key"])) for item in document["track_outputs"]}
    return {"measurements": measurements, "tracks": tracks, "material_model": document["header"]["material_model"],
            "alignment_parametrization": document["header"]["alignment_parametrization"]}


def residual_covariance_matrix(record: dict) -> list:
    """The full (2n) x (2n) matrix of a residual_covariance record, loc0 then loc1 of each measurement state in order."""
    size = 2 * record["measurement_count"]
    matrix = [[0.0] * size for _ in range(size)]
    values = iter(record["covariance"])
    for row in range(size):
        for column in range(row, size):
            matrix[row][column] = matrix[column][row] = next(values)
    return matrix


def residual_covariance_largest_difference(document: dict) -> float:
    """The largest |block - smoothed| / sqrt(R00 R11) over every diagonal block of every track: the reading of the identity below (fix round 3, N3)."""
    largest = 0.0
    for defect_scale in _diagonal_differences(document):
        largest = max(largest, defect_scale[0])
    return largest


def _diagonal_differences(document: dict):
    smoothed = {(item["track_key"], item["state_index"]): item["covariance"] for item in document["residuals"] if item["state_type"] == "smoothed"}
    measured = {}
    for state in document["states"]:
        if state["kind"] == "measurement":
            measured.setdefault(state["track_key"], []).append(state["index"])
    for item in document["residual_covariances"]:
        matrix = residual_covariance_matrix(item)
        for position, index in enumerate(sorted(measured[item["track_key"]])):
            block = (matrix[2 * position][2 * position], matrix[2 * position][2 * position + 1], matrix[2 * position + 1][2 * position + 1])
            expected = smoothed[(item["track_key"], index)]
            scale = math.sqrt(abs(expected[0] * expected[2]))
            yield max(abs(block[entry] - expected[entry]) for entry in range(3)) / scale, item["track_key"], index, block, expected


def residual_covariance_defects(document: dict, relative: float) -> list:
    """The identity of t07-r33/1: each diagonal 2 x 2 block of a track's residual covariance is that state's smoothed residual covariance, to
    relative x sqrt(R00 R11). The blocks come from the Jacobian chain, the smoothed residual covariances from ACTS's smoother."""
    smoothed = {(item["track_key"], item["state_index"]): item["covariance"] for item in document["residuals"] if item["state_type"] == "smoothed"}
    measured = {}
    for state in document["states"]:
        if state["kind"] == "measurement":
            measured.setdefault(state["track_key"], []).append(state["index"])
    defects = []
    for item in document["residual_covariances"]:
        matrix = residual_covariance_matrix(item)
        for position, index in enumerate(sorted(measured[item["track_key"]])):
            block = (matrix[2 * position][2 * position], matrix[2 * position][2 * position + 1], matrix[2 * position + 1][2 * position + 1])
            expected = smoothed[(item["track_key"], index)]
            scale = math.sqrt(abs(expected[0] * expected[2]))
            if any(abs(block[entry] - expected[entry]) > relative * scale for entry in range(3)):
                defects.append(f"{item['track_key']} state {index}: block {block} against smoothed {expected}")
    return defects
