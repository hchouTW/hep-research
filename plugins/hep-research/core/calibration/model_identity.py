"""The g4sim model identity (Part B section 5.1, clause 1 item 2 of section 5.2; owner calib_contract.py check).

A model is "everything other than theta and phi", so it is identified by five items locked with the contract, never by
g4sim's own geometry_id, request_id or run_id (those change with every design point):

1. detector_spec: the pair (masked hash of detector-spec/1, masked hash of the alignment-overlay/1 or None) (D86);
2. simulation_request: masked hash of simulation-request/1;
3. run_physics: masked hash of the g4sim-run/1 blocks other than `run` and `output`;
4. response_pipeline: masked hash of response-pipeline/1 without `run_seed` and `replica`, folded with the efficiency
   map part, the condition-snapshot/1 part with the plan's event-time rule (D86), and the PDE(E) part (section 6.7);
5. build_environment: g4sim's build_hash, the Geant4 version and the version of each data set used.

Reading: detector-spec/1 is read by g4sim's own procedure (core.canonical.load_spec_json with the type table that
contracts.geometry generates from its schema; the caller passes that table). g4sim has no reading procedure for the
other documents, so this module normalizes their numbers with a type table generated from their schemas
(`type_table`): an integer field becomes an integer, a number field, or a number at a place the schema leaves untyped,
becomes a decimal/1 string; strings, booleans and the tree are kept as they are, so normalization adds no field and
derives no value (section 19, derived fields; approval A12). Masking replaces each theta/phi leaf, named by a JSON
Pointer, with MASK; a pointer to a container or to nothing is refused. Standard library only.
"""
from __future__ import annotations

import decimal
import json
import re

from core.canonical import (CanonicalError, canonical_sha256, load_spec_json, normalize_decimal,
                            require_hash_scope)
from core.canonical.encoding import INTEGER_LIMIT
from core.simulation import efficiency_map, response

MASK = "calib-masked/1"
SCALE_SUFFIX = "/~scale"     # a mask-list entry for a scale binding ("~s" is no JSON Pointer escape, so no key collides)
ITEMS = ("detector_spec", "simulation_request", "run_physics", "response_pipeline", "build_environment")
DOCUMENTS = ("detector-spec", "alignment-overlay", "simulation-request", "run-card", "response-pipeline",
             "condition-snapshot")
SPEC_UNHASHED = ("legacy",)                       # g4sim's own: expansion never reads it (contracts.geometry)
SPEC_SOURCES = ("source_of_facts",)               # top-level sources of a detector-spec (marker part)
SPEC_LABEL_KEY = "facts"                          # material and surface source labels (marker part)
LABELS = ("description", "source_of_facts")      # removed from overlays, snapshots and PDE(E) tables (D86)
RUN_EXCLUDED = ("run", "output")                  # section 5.1: seeds, event intervals, threads, chunk; output files
PIPELINE_EXCLUDED = ("run_seed", "replica")       # section 5.1: seeds (section 6.6)
SCHEMAS = {"detector-spec": "detector-spec/1", "alignment-overlay": "alignment-overlay/1",
           "simulation-request": "simulation-request/1", "run-card": "g4sim-run/1",
           "response-pipeline": "response-pipeline/1", "condition-snapshot": "condition-snapshot/1"}
SHA = re.compile(r"^[0-9a-f]{64}$")


class IdentityError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# ------------------------------------------------------------------ type tables and normalization
def type_table(schema: dict) -> dict:
    """{JSON Pointer: "integer" | "quantity"} of a JSON schema: "type": "integer" fields are integers, "type": "number"
    fields quantities; "*" stands for any key or index. Follows properties, additionalProperties, items, anyOf, oneOf
    and local $refs (also the #/$defs/quantity and #/$defs/integer convention of detector_spec.json)."""
    defs = schema.get("$defs", {})
    table: dict = {}

    def walk(node, pointer, seen):
        if not isinstance(node, dict):
            return
        ref = node.get("$ref", "")
        if ref in ("#/$defs/quantity", "#/$defs/integer"):
            table[pointer] = ref.rsplit("/", 1)[1]
            return
        if ref.startswith("#/$defs/") and ref not in seen:
            walk(defs.get(ref.rsplit("/", 1)[1], {}), pointer, seen | {ref})
        kind = node.get("type")
        if kind == "integer":
            table[pointer] = "integer"
        elif kind == "number":
            table[pointer] = "quantity"
        for key, child in (node.get("properties") or {}).items():
            walk(child, f"{pointer}/{key.replace('~', '~0').replace('/', '~1')}", seen)
        if isinstance(node.get("additionalProperties"), dict):
            walk(node["additionalProperties"], f"{pointer}/*", seen)
        if isinstance(node.get("items"), dict):
            walk(node["items"], f"{pointer}/*", seen)
        for form in node.get("anyOf", []) + node.get("oneOf", []):
            walk(form, pointer, seen)
    walk(schema, "", frozenset())
    return table


def _segments(pointer: str) -> list[str]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise IdentityError("identity.pointer", f"{pointer!r} is not a JSON Pointer")
    return [p.replace("~1", "/").replace("~0", "~") for p in pointer[1:].split("/")]


def _kind_at(table: dict, path: list[str]):
    """The declared type at a path: exact segments or "*" wildcards; None when undeclared."""
    for pointer, kind in table.items():
        segs = _segments(pointer) if pointer else []
        if len(segs) == len(path) and all(s in ("*", p) for s, p in zip(segs, path)):
            return kind
    return None


def _number_text(value) -> str:
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise IdentityError("identity.number", f"{value!r} is not a finite number")
        return repr(value)
    return str(value)


def _leaf(value, kind, where):
    if kind == "decimal-string" and isinstance(value, str):
        try:                                   # A16 (iii): one spelling per value ("0.05" and "0.050" alike)
            return normalize_decimal(value)
        except CanonicalError as err:
            raise IdentityError("identity.number", f"{where}: {err}") from None
    if isinstance(value, bool) or not isinstance(value, (int, float, decimal.Decimal)):
        return value
    text = _number_text(value)
    if kind == "integer":
        number = decimal.Decimal(text)
        if number != number.to_integral_value():
            raise IdentityError("identity.integer", f"{where}: {text} is not an integer")
        if abs(number) > INTEGER_LIMIT:
            raise IdentityError("identity.integer", f"{where}: integers lie within +-(2^53 - 1)")
        return int(number)
    try:
        return normalize_decimal(text)
    except CanonicalError as err:
        raise IdentityError("identity.number", f"{where}: {err}") from None


def _unique(pairs):
    keys = [k for k, _ in pairs]
    if len(set(keys)) != len(keys):
        raise IdentityError("identity.json", "an object key appears more than once")
    return dict(pairs)


def _constant(name):
    raise IdentityError("identity.json", f"{name} is not JSON")


def _parse(document):
    if isinstance(document, (bytes, bytearray)):
        try:
            document = bytes(document).decode("utf-8")
        except UnicodeDecodeError as err:
            raise IdentityError("identity.json", f"not UTF-8: {err}") from None
    if isinstance(document, str):
        try:
            return json.loads(document, object_pairs_hook=_unique, parse_float=decimal.Decimal,
                              parse_constant=_constant)
        except IdentityError:
            raise
        except ValueError as err:
            raise IdentityError("identity.json", f"not JSON: {err}") from None
    return document


def normalize(document, table: dict):
    """The document with every number normalized by `table` (see type_table); text is parsed with exact decimals,
    a parsed document's floats are read by their repr. The tree is kept: no field is added, removed or derived."""
    def go(value, path):
        if isinstance(value, dict):
            return {k: go(v, path + [k]) for k, v in value.items()}
        if isinstance(value, list):
            return [go(v, path + [str(i)]) for i, v in enumerate(value)]
        return _leaf(value, _kind_at(table, path), "/" + "/".join(path))
    return go(_parse(document), [])


def leaf_pointers(value, prefix: str = "") -> set[str]:
    """Every leaf of a JSON tree as a JSON Pointer (an empty object or list counts as a leaf)."""
    if isinstance(value, dict) and value:
        return set().union(*(leaf_pointers(v, f"{prefix}/{k.replace('~', '~0').replace('/', '~1')}")
                             for k, v in value.items()))
    if isinstance(value, list) and value:
        return set().union(*(leaf_pointers(v, f"{prefix}/{i}") for i, v in enumerate(value)))
    return {prefix}


def read_spec(text, spec_field_types: dict):
    """detector-spec/1 by g4sim's reading procedure (spellings of a value give the same hash)."""
    try:
        return load_spec_json(text, spec_field_types, unhashed=SPEC_UNHASHED)
    except CanonicalError as err:
        raise IdentityError("identity.detector_spec", f"detector-spec/1 reading: {err}") from None


# ------------------------------------------------------------------ masking and the items
def _scale_shape(values, pointer):
    """A scale-bound array (theta multiplies every element, nominal 1) as [MASK, v_1/v_0, ...]: invariant under the
    scale, keeping the shape in the identity; ratios to 12 significant digits, so the float rounding of s v_i / (s v_0)
    does not move the hash."""
    if not isinstance(values, list) or not values or any(isinstance(v, (dict, list, bool)) for v in values):
        raise IdentityError("identity.mask_scale", f"{pointer}: a scale binding names an array of numbers")
    first = float(values[0])
    if first == 0:
        raise IdentityError("identity.mask_scale", f"{pointer}: the first element of a scaled array is 0")
    return [MASK] + [f"{float(v) / first:.12g}" for v in values[1:]]


def mask(document, pointers) -> dict:
    """The document with each pointer's leaf replaced by MASK. Refuses a pointer to nothing, to a container (masking a
    whole container to hide non-parameter settings is forbidden, section 5.1) or to the document root. A pointer with
    SCALE_SUFFIX names a scale-bound array, replaced by its shape (_scale_shape)."""
    out = json.loads(json.dumps(document))
    for pointer in sorted(set(pointers)):
        if pointer.endswith(SCALE_SUFFIX):
            base = pointer[: -len(SCALE_SUFFIX)]
            segs = _segments(base)
            node = out
            for s in segs[:-1]:
                node = _step(node, s, base)
            last = segs[-1]
            target = _step(node, last, base)
            shaped = _scale_shape(target, base)
            if isinstance(node, dict):
                node[last] = shaped
            else:
                node[int(last)] = shaped
            continue
        segs = _segments(pointer)
        if not segs or segs == [""]:
            raise IdentityError("identity.mask_root", "the whole document cannot be masked")
        node = out
        for s in segs[:-1]:
            node = _step(node, s, pointer)
        last = segs[-1]
        if isinstance(node, dict) and last in node:
            target = node[last]
        elif isinstance(node, list) and last.isdigit() and int(last) < len(node):
            target = node[int(last)]
        else:
            raise IdentityError("identity.mask_missing", f"{pointer} names no field of the document")
        if isinstance(target, (dict, list)):
            raise IdentityError("identity.mask_container", f"{pointer} is a container: only leaves holding theta or "
                                "phi are masked (section 5.1)")
        if isinstance(node, dict):
            node[last] = MASK
        else:
            node[int(last)] = MASK
    return out


def _step(node, s, pointer):
    if isinstance(node, dict) and s in node:
        return node[s]
    if isinstance(node, list) and s.isdigit() and int(s) < len(node):
        return node[int(s)]
    raise IdentityError("identity.mask_missing", f"{pointer} names no field of the document")


def _schema(document, kind):
    if not isinstance(document, dict) or document.get("schema") != SCHEMAS[kind]:
        got = document.get("schema") if isinstance(document, dict) else type(document).__name__
        raise IdentityError("identity.document", f"the {kind} document is {SCHEMAS[kind]}, not {got!r}")


def _without_labels(value, key=SPEC_LABEL_KEY):
    if isinstance(value, dict):
        return {k: _without_labels(v, key) for k, v in value.items() if k != key}
    if isinstance(value, list):
        return [_without_labels(v, key) for v in value]
    return value


def _hash(document) -> str:
    try:
        require_hash_scope(document)
    except CanonicalError as err:
        raise IdentityError("identity.hash_scope", str(err)) from None
    return canonical_sha256(document)


def spec_hash(spec: dict, pointers=()) -> str:
    """Masked hash of a detector-spec read by read_spec. Its source labels (top-level source_of_facts and every
    `facts` label, the marker part of g4sim's IR) are left out: a change of provenance_id does not change the model
    identity (section 5.1). The IR is never hashed (its `alignment` field is an id derived from theta, D86)."""
    _schema(spec, "detector-spec")
    body = _without_labels({k: v for k, v in spec.items() if k not in SPEC_SOURCES + SPEC_UNHASHED})
    return _hash(mask(body, pointers))


OVERLAY_DECIMAL_STRINGS = {"/shifts/*/delta_mm/*": "decimal-string", "/shifts/*/rotation/zyx_deg/*": "decimal-string"}


def overlay_hash(overlay, table: dict, pointers=()) -> str:
    """Masked hash of an alignment-overlay/1 without description and source_of_facts (D86, section 5.1); only the
    delta_mm and zyx_deg entries holding theta or phi are masked. The schema types those entries as plain strings
    ("decimal strings"); A16 (iii) reads them as decimals, so each is canonicalized before hashing and two spellings
    of one value give one model identity (g4sim's own geometry_id still differs: reported upstream, D83)."""
    doc = normalize(overlay, {**table, **OVERLAY_DECIMAL_STRINGS})
    _schema(doc, "alignment-overlay")
    return _hash(mask({k: v for k, v in doc.items() if k not in LABELS}, pointers))


def request_hash(request, table: dict, pointers=()) -> str:
    doc = normalize(request, table)
    _schema(doc, "simulation-request")
    return _hash(mask(doc, pointers))


def run_physics_hash(card, table: dict, pointers=()) -> str:
    """Masked hash of every top-level block of g4sim-run/1 except `run` and `output` (section 5.1)."""
    doc = normalize(card, table)
    _schema(doc, "run-card")
    bad = [p for p in pointers if _segments(p)[0] in RUN_EXCLUDED]
    if bad:
        raise IdentityError("identity.run_block", f"{bad}: the run and output blocks are not in the model identity, "
                            "so no theta or phi is bound there")
    return _hash(mask({k: v for k, v in doc.items() if k not in RUN_EXCLUDED}, pointers))


def pipeline_document_hash(pipeline, table: dict, pointers=()) -> str:
    doc = normalize(pipeline, table)
    _schema(doc, "response-pipeline")
    bad = [p for p in pointers if _segments(p)[0] in PIPELINE_EXCLUDED]
    if bad:
        raise IdentityError("identity.pipeline_seed", f"{bad}: run_seed and replica are seeds, excluded from the "
                            "model identity (section 5.1)")
    return _hash(mask({k: v for k, v in doc.items() if k not in PIPELINE_EXCLUDED}, pointers))


SNAPSHOT_POINTER = re.compile(r"^/iovs/\d+/rows/\d+/(gain_factor|threshold)$")


def snapshot_hash(snapshot, table: dict, pointers=(), event_time_rule=None) -> str:
    """The condition-snapshot/1 part of the response item (D86): the snapshot without description and source_of_facts,
    its theta/phi row values masked by /iovs/<k>/rows/<j>/<quantity>, together with the plan's event-time rule."""
    doc = normalize(snapshot, table)
    _schema(doc, "condition-snapshot")
    bad = [p for p in pointers if not SNAPSHOT_POINTER.match(p)]
    if bad:
        raise IdentityError("identity.snapshot_pointer", f"{bad}: a snapshot value holding theta or phi is a row's "
                            "gain_factor or threshold, /iovs/<k>/rows/<j>/<quantity> (D87; dead is never theta or phi, "
                            "temperature_K has no role)")
    if not isinstance(event_time_rule, dict) or not event_time_rule:
        raise IdentityError("identity.event_time_rule", "a snapshot is hashed with the plan's event-time rule "
                            "(event_time_ns as a function of the global event number, section 6.6, D86)")
    return _hash({"snapshot": mask({k: v for k, v in doc.items() if k not in LABELS}, pointers),
                  "event_time_rule": normalize(event_time_rule, {})})


def map_part(map_document=None, mapping: dict | None = None) -> dict | None:
    """The efficiency-map part of the response item (section 5.1): fixed-map mode, the map hash as built
    (efficiency_map.map_sha256); mode where the map varies with theta, the mapping-run settings with the map hash
    masked (mapping: segmentation, component, and the three masked g4sim specification hashes, computed with this
    module's functions)."""
    if map_document is not None and mapping is not None:
        raise IdentityError("identity.map_mode", "a map is either fixed (its hash) or varies with theta (its "
                            "mapping-run settings), not both")
    if map_document is not None:
        return {"mode": "fixed", "map_sha256": efficiency_map.map_sha256(map_document)}
    if mapping is not None:
        need = ("segmentation", "component", "detector_spec", "simulation_request", "run_physics")
        missing = [k for k in need if k not in mapping]
        if missing:
            raise IdentityError("identity.mapping_settings", f"the mapping-run settings lack {missing}")
        return {"mode": "varies-with-theta", "map_sha256": MASK, **{k: normalize(mapping[k], {}) for k in need}}
    return None


def response_hash(pipeline_sha256: str, efficiency_map_part=None, snapshot_sha256=None, pde_part=None) -> str:
    """Item 4: the masked pipeline hash folded with the map part, the snapshot part (D86) and the PDE(E) part of
    section 6.7 (route 3; given by the caller); absent parts are null, so adding one changes the item."""
    return canonical_sha256({"pipeline": pipeline_sha256, "efficiency_map": efficiency_map_part,
                             "conditions": snapshot_sha256, "pde": pde_part})


def build_environment(record) -> dict:
    """Item 5: build_hash (SHA-256 of the g4sim_run executable), the Geant4 version and each data set's version."""
    if not isinstance(record, dict) or not SHA.match(str(record.get("build_hash", ""))) \
            or not isinstance(record.get("geant4_version"), str) or not record.get("geant4_version") \
            or not isinstance(record.get("datasets"), dict) or not record["datasets"] \
            or not all(isinstance(v, str) and v for v in record["datasets"].values()):
        raise IdentityError("identity.build_environment", "the build environment gives build_hash (64 hex), "
                            "geant4_version and datasets {name: version} from the installation record")
    return {"build_hash": record["build_hash"], "geant4_version": record["geant4_version"],
            "datasets": dict(sorted(record["datasets"].items()))}


# ------------------------------------------------------------------ the five items of one model
def masks(contract: dict) -> dict:
    """{document: [pointers]} of the theta and phi bindings of the contract's parameters[] (section 5.1: the mask
    list is locked with the binding). psi bindings are not masked: a psi value is part of the model."""
    out: dict = {d: [] for d in DOCUMENTS}
    for p in contract.get("parameters", []):
        if p.get("role") not in ("theta", "phi"):
            continue
        for b in p.get("bindings", []) or []:
            if b.get("document") in out:
                scale = b.get("form", "value") == "scale"
                out[b["document"]].append(b.get("pointer") + SCALE_SUFFIX if scale else b.get("pointer"))
    return out


def identity(documents: dict, mask_list: dict, tables: dict) -> dict:
    """The five items of one model. documents: detector_spec (text, read by g4sim's procedure with
    tables["detector-spec"]), alignment_overlay (optional), simulation_request, run_card, response_pipeline,
    efficiency_map (optional map document, fixed mode) or mapping (optional settings, map varies with theta),
    condition_snapshot with event_time_rule (optional), pde (optional part, section 6.7), build_environment.
    tables: type tables by document kind. mask_list: masks(contract)."""
    spec = read_spec(documents["detector_spec"], tables["detector-spec"])
    if isinstance(spec, dict) and spec.get("schema") == "geometry-ir/1":
        raise IdentityError("identity.ir", "the IR is never hashed (its alignment field is derived from theta, D86)")
    overlay = documents.get("alignment_overlay")
    if overlay is None and mask_list.get("alignment-overlay"):
        raise IdentityError("identity.overlay_missing", "alignment parameters are bound to an overlay, and the model "
                            "applies none (an overlay at every design point, the nominal one included, D86)")
    det = [spec_hash(spec, mask_list.get("detector-spec", ())),
           None if overlay is None else overlay_hash(overlay, tables["alignment-overlay"],
                                                     mask_list.get("alignment-overlay", ()))]
    snapshot = documents.get("condition_snapshot")
    if snapshot is None and mask_list.get("condition-snapshot"):
        raise IdentityError("identity.snapshot_missing", "parameters are bound to a condition snapshot the model does "
                            "not apply")
    snap = None if snapshot is None else snapshot_hash(snapshot, tables["condition-snapshot"],
                                                       mask_list.get("condition-snapshot", ()),
                                                       documents.get("event_time_rule"))
    pipe = pipeline_document_hash(documents["response_pipeline"], tables["response-pipeline"],
                                  mask_list.get("response-pipeline", ()))
    return {"detector_spec": det,
            "simulation_request": request_hash(documents["simulation_request"], tables["simulation-request"],
                                               mask_list.get("simulation-request", ())),
            "run_physics": run_physics_hash(documents["run_card"], tables["run-card"], mask_list.get("run-card", ())),
            "response_pipeline": response_hash(pipe, map_part(documents.get("efficiency_map"),
                                                              documents.get("mapping")), snap, documents.get("pde")),
            "build_environment": build_environment(documents.get("build_environment"))}


def item_findings(model_id, declared) -> list[dict]:
    """Clause 1 item 2: a g4sim model carries the five items, each of its form."""
    path = f"$.models[{model_id}].identity"
    if not isinstance(declared, dict):
        return [{"code": "models.identity_missing", "path": path, "message": f"model {model_id!r} carries none of "
                 "the five g4sim identity items of section 5.1 (clause 1 item 2)"}]
    out = []
    missing = [k for k in ITEMS if k not in declared]
    if missing:
        out.append({"code": "models.identity_missing", "path": path, "message": f"model {model_id!r} lacks the "
                    f"identity items {missing} (section 5.1, clause 1 item 2)"})
    det = declared.get("detector_spec")
    if "detector_spec" in declared and not (isinstance(det, list) and len(det) == 2 and SHA.match(str(det[0]))
                                            and (det[1] is None or SHA.match(str(det[1])))):
        out.append({"code": "models.identity_form", "path": path + ".detector_spec", "message": "the detector-spec "
                    "item is the pair [masked spec hash, masked overlay hash or null] (D86)"})
    for k in ("simulation_request", "run_physics", "response_pipeline"):
        if k in declared and not SHA.match(str(declared[k])):
            out.append({"code": "models.identity_form", "path": f"{path}.{k}", "message": f"{k} is a SHA-256"})
    if "build_environment" in declared:
        try:
            build_environment(declared["build_environment"])
        except IdentityError as err:
            out.append({"code": "models.identity_form", "path": path + ".build_environment", "message": str(err)})
    return out


def changed_items(old: dict, current: dict) -> list[str]:
    """Section 10.3: the identity items that differ between two records of a model; any change marks the result as
    needing a redo (until the open question of section 19 on keeping old results is decided)."""
    return [k for k in ITEMS if (old or {}).get(k) != (current or {}).get(k)]


# ------------------------------------------------------------------ g4sim-digi-job/1 against the hashed documents
def _stage(pipeline: dict, kind: str, name: str | None = None) -> dict | None:
    found = [s for s in pipeline.get("stages", []) if s.get("kind") == kind and (name is None or s.get("name") == name)]
    return found[0] if len(found) == 1 else None


def digi_job_findings(job: dict, pipeline: dict, theta_values: dict | None = None, efficiencies: dict | None = None,
                      map_document: dict | None = None, map_replica: int = 0, snapshot: dict | None = None,
                      timing: dict | None = None) -> list[dict]:
    """Section 5.1 (D86) and section 15.3.19: a g4sim-digi-job/1 is not hashed; it must equal the hashed documents at
    the evaluation's theta. The job's stage, sensor and electronics blocks equal the parameters of the pipeline stages
    of the same name and kind (scintillation, sensor, electronics), a field in theta_values ({"<block>/<field>":
    value}) taking that value instead; its channels are the map's; its efficiencies are `efficiencies` when given
    (the PDE-split or joint-pattern replica the caller computed, section 6.7), else the map's replica map_replica; its
    conditions equal the snapshot (absent when no snapshot is applied); its timing equals `timing` when given.
    The seed, replica, keys and event-time checks of section 6.6 are calib_design.py's. Returns findings."""
    out = []
    theta_values = theta_values or {}

    def bad(code, message):
        out.append({"code": code, "path": "$.job", "message": message})
    for block, kind in (("stage", "scintillation"), ("sensor", "sensor"), ("electronics", "electronics")):
        mine = job.get(block) or {}
        stage = _stage(pipeline, kind, mine.get("name"))
        if stage is None:
            bad("digi_job.stage_missing", f"the job's {block} {mine.get('name')!r} is no single {kind} stage of the "
                "hashed response-pipeline/1")
            continue
        params = {k: v.get("value") for k, v in stage.get("parameters", {}).items() if isinstance(v, dict)}
        for field, value in params.items():
            want = theta_values.get(f"{block}/{field}", value)
            if field not in mine or mine[field] != want:
                bad("digi_job.differs", f"{block}.{field} is {mine.get(field)!r}, the hashed pipeline at theta gives "
                    f"{want!r}")
        extra = sorted(set(mine) - set(params) - {"name"})
        if extra:
            bad("digi_job.differs", f"{block} carries {extra}, which the hashed pipeline stage does not declare")
    if map_document is not None:
        if list(job.get("channels") or []) != list(map_document.get("channels") or []):
            bad("digi_job.channels", "the job's channels are not the map's")
        if efficiencies is None:
            form = map_document.get("form") or {}
            bins = [str(r["bin"]) for r in form.get("bins", [])] if form.get("kind") == efficiency_map.FORM \
                else sorted(job.get("efficiencies") or {}, key=int)
            try:
                efficiencies = {b: response.efficiencies(map_document, int(b), map_replica) for b in bins}
            except (KeyError, ValueError) as err:
                bad("digi_job.efficiencies", f"the map's efficiencies cannot be computed: {err}")
    if efficiencies is not None and dict(job.get("efficiencies") or {}) != {str(k): list(v) for k, v in
                                                                             efficiencies.items()}:
        bad("digi_job.efficiencies", f"the job's efficiencies are not the map's (replica {map_replica}) or the "
            "declared replica's")
    if snapshot is None and "conditions" in job:
        bad("digi_job.conditions", "the job carries conditions, and the model applies no snapshot")
    if snapshot is not None and job.get("conditions") != snapshot:
        bad("digi_job.conditions", "the job's conditions are not the hashed snapshot")
    if timing is not None and job.get("timing") != timing:
        bad("digi_job.timing", "the job's timing differs from the documents")
    return out
