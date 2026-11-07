"""acts-tracking-product/1 in Python: read, write, reorder, subset, merge, and the map to reconstruction-product/1.

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
    """The text is not acts-tracking-product/1, or an operation would break a reference."""


def _number(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise ProductFormatError(f"not a finite number: {token}")
    return value


def _number_text(value: float) -> str:
    if not math.isfinite(value):
        raise ProductFormatError("a product holds finite numbers only")
    return "%.17g" % value


def _header_from_lines(lines) -> dict:
    header = {}
    for name, line in zip(TEXT_HEADER_FIELDS, lines):
        tokens = line.split(" ")
        if tokens[0] != name:
            raise ProductFormatError(f"expected the record {name}, found {tokens[0]}")
        header[name] = tokens[1:]
    if len(header) != len(TEXT_HEADER_FIELDS):
        raise ProductFormatError("the product ends inside its header")
    for name, values in header.items():
        if len(values) != (5 if name == "start_prior" else 1):
            raise ProductFormatError(f"{name} has {len(values)} values")
    parsed = {name: values[0] for name, values in header.items()}
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


RECORD_READERS = {"track": (11, _track_record, "tracks"), "state": (13, _state_record, "states"), "parameters": (31, _parameter_record, "parameters")}


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


def parse_product(text: str) -> dict:
    """A whole product as a dict, or ProductFormatError. A count in the end record catches a truncated file."""
    lines = text.split("\n")
    if lines[-1] != "":
        raise ProductFormatError("the last line is not finished")
    lines = lines[:-1]
    if not lines or lines[0] != PRODUCT_FORMAT:
        raise ProductFormatError(f"not {PRODUCT_FORMAT}")
    width = len(TEXT_HEADER_FIELDS)
    try:
        document = {"header": _header_from_lines(lines[1:1 + width]), "tracks": [], "states": [], "parameters": []}
        counted = None
        for line in lines[1 + width:]:
            if counted is not None:
                raise ProductFormatError("text after the end record")
            tokens = line.split(" ")
            if tokens[0] == "end" and len(tokens) == 4:
                counted = [int(token) for token in tokens[1:]]
                continue
            size, read_record, collection = RECORD_READERS.get(tokens[0], (None, None, None))
            if size != len(tokens):
                raise ProductFormatError(f"unknown record {tokens[0]}")
            document[collection].append(read_record(tokens))
    except (IndexError, ValueError) as error:
        if isinstance(error, ProductFormatError):
            raise
        raise ProductFormatError(str(error)) from error
    if counted is None:
        raise ProductFormatError("the product ends before its end record")
    if counted != [len(document[name]) for name in ("tracks", "states", "parameters")]:
        raise ProductFormatError("the end record counts other numbers than the product holds")
    _check_links(document)
    return document


def format_product(document: dict) -> str:
    """The exact bytes the driver writes for this document."""
    header = document["header"]
    lines = [PRODUCT_FORMAT]
    for name in TEXT_HEADER_FIELDS:
        if name == "start_prior":
            lines.append(" ".join(["start_prior"] + [_number_text(value) for value in header[name]]))
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
    lines.append(f"end {len(document['tracks'])} {len(document['states'])} {len(document['parameters'])}")
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
    return {"header": dict(document["header"], product_id=product_id, revision=revision), "tracks": [by_key[key] for key in track_keys],
            "states": states, "parameters": parameters}


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
    for name in MERGE_IDENTITY_FIELDS:
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


def _sidecar_base(product_id: str, revision: int, collection: str, role: str, objects: list, native_location: str) -> dict:
    document = {"schema": "reconstruction-product/1", "product_id": product_id, "revision": revision, "collection": collection,
                "native": {"type": PRODUCT_FORMAT, "location": native_location}, "presence": "present" if objects else "valid-empty",
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
    return [_sidecar_base(f"{base_id}.tracks", revision, "tracks", "validation", track_objects, native_location),
            _sidecar_base(f"{base_id}.track-states", revision, "track-states", "validation", state_objects, native_location)]


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
