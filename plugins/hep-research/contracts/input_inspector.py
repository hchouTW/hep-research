"""Bounded input inspector (detector reconstruction T14; plan Sections 5.5, 5.6, 5.8, 5.15; K15; plan K17 row; contract-map.md).

inspect_inputs forms one input signature per product and scope from readable inputs, or stops; its record is an
input-inspection/1 sidecar. Only the probes in PROBES run, with their fixed parameters, and a JSON document reaches a fact
only through read_document, the one K13 stop, or, for an envelope artifact, through contracts.validate.validate_artifact, its
existing validator (K15; decisions.md, "T14 rulings"). judge_candidates applies necessary conditions to one signature, without ranking
or selecting. What cannot be read stays unknown and malformed input gives no exception. The module writes nothing, runs
nothing, starts no backend and reads no ROOT file: `uproot` is not approved (K15), and a missing reader means "not yet
observed" (Section 5.6).

The budget holds the five limits of Section 5.6 item 5. Probes, the bytes a probe reads, and tools are never passed. Seconds and
memory are charged for the whole inspection and watched while it runs (_Spending), and a limit reached ends in stopped with its
reason (A59). The readers are imported before the budget starts, so that one-time cost is not charged, and a stop waits for the end
of any import that does run under the watch: a stop inside one can break a module for the life of the process. What this cannot do,
stated rather than hidden: a watch runs between Python calls, so one C call (a blocking read, the JSON parser on a list of plain
numbers, one NumPy routine, one regular expression of a validator) runs to its end, and the overrun is caught as soon as it returns:
that probe's facts are dropped and the record says stopped. A hard stop would need a separate process, which Section 5.6's lightweight read-only probe
does not call for. Memory is the rise of the process's peak resident size (getrusage), which sees C libraries too but is one number
for the process: an earlier, higher peak hides a rise below it, so the limit reads "the peak grows by at most this much". Where
getrusage does not exist, a declared memory limit cannot be kept, so inspection stops at once with budget-memory.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import stat
import sys
import time

try:
    import resource
except ImportError:  # not on every platform (Windows); a declared memory limit then stops inspection (_peak_resident_bytes)
    HAS_GETRUSAGE = False
else:
    HAS_GETRUSAGE = True

from contracts.schema import Report, load_schema
from contracts.sidecar_reader import MALFORMED_DOCUMENT, read_document, reader_path

JSON_PROBE = "probe.json-document"
CSV_PROBE = "probe.csv-head"
# Section 5.6: "known tool/reader contracts and fixed parameter combinations". The plan gives no values; these are engineering
# limits of a probe, not physics and not budgets. byte_ceiling: JSON cannot be parsed in part, so a document is read whole or not at
# all, and this is the most one parse may take with no check inside it. document_ceiling: a list file holds a few products, and
# this bounds the signatures one file can make. window_bytes: a CSV is read through one window, enough for a wide header and a
# sample of rows. reader_version is the version of these rules: the standard library's parsers have no separate one, and
# Section 5.6 item 2's "verified" is the read-back check that a record names exactly this version and these parameters.
PROBES: dict[str, dict] = {JSON_PROBE: {"reader": "json", "reader_version": "1", "parameters": {"byte_ceiling": 16 * 1024 * 1024, "document_ceiling": 1024}},
          CSV_PROBE: {"reader": "csv", "reader_version": "1", "parameters": {"window_bytes": 64 * 1024}}}
# A43: the extension picks a reader and establishes nothing else.
PROBE_BY_SUFFIX = {".json": JSON_PROBE, ".csv": CSV_PROBE}
# Engineering limits of the watch: looks at the clock and the memory every so many Python events, and reads a file in chunks.
WATCH_INTERVAL = 64
READ_CHUNK_BYTES = 1024 * 1024
# Section 5.6 item 5: read, time, memory, tool and probe-count limits. A tool is a registered reader, since no other tool exists here.
BUDGET_COUNTS = ("probes", "bytes", "memory_bytes", "tools")
RESOURCE_STOPS = ("budget-seconds", "budget-memory")  # the two limits a C call can pass before the watch sees it
BUDGET_STOPS = RESOURCE_STOPS + ("budget-probes", "budget-bytes", "budget-tools", "budget-not-declared")
# K15: these go to a fact as a caller declares them, stating which. The rest are not evidence, also when only a reference says so.
DECLARABLE_KINDS = frozenset({"declaration", "llm-extraction"})
NOT_EVIDENCE_REFERENCES = ("file-name:", "array-shape:", "model-confidence:")
# Section 8.2: only these deliver an observation; absent, invalid and not-applicable generate no candidate.
DELIVERED_PRESENCE = ("present", "valid-empty")
# A reading of Section 5.5, which names kinds of representation and not blocks: a block states one where its witness does.
REPRESENTATION_BY_BLOCK = {"counts": "count", "candidates": "candidate"}
# Section 5.5 lists frame and scan under acquisition.
ACQUISITION_BY_BLOCK = {"frames": "frames", "scan": "scan"}
# Blocks that state no representation but correspond to a blueprint.
OTHER_BLOCKS = ("estimate", "inversion", "association")
# K15 and decisions.md, "T14 rulings": an envelope artifact reports these three facts and nothing else: no physics is inferred from it.
ARTIFACT_SCHEMA = "artifact-envelope"
# The same ruling: a file that parsed but has no known schema keeps `container`. These two codes say "no known schema". Any other
# refusal is of a schema this reader knows (K13, or its rules), and keeps nothing.
NO_KNOWN_SCHEMA = ("reconstruction.reader.unknown_format", "artifact.unknown_type")
# Section 5.15 ("Minimum signature clues") and the witnesses' Correspondence lines: candidates to check only, many to many; a match
# authorizes nothing. Each row cites its source. This table is a reading from Sections 5.15, W1-W5 and W7 (decisions.md, "T14 rulings"),
# not an owner's sign-off, and is to be rechecked before anything depends on it.
CANDIDATES_BY_CLUE = {
    ("representation", "waveform"): ("BP01", "BP05", "BP06", "BP07", "BP08", "BP09"),  # 5.15: BP01, BP07 samples; BP05 waveforms; BP06 traces; BP08 drift waveforms; BP09 pulse
    ("representation", "count"): ("BP06", "BP09", "BP12", "BP13"),  # 5.15: BP06 photosensor count; BP09 count; BP12 count/threshold (W6); BP13 retarding counts
    ("representation", "image"): ("BP02", "BP10", "BP11"),  # 5.15: BP02 image features; BP10 detector maps, shadowgrams (W5); BP11 camera observations
    ("representation", "measurement"): ("BP02", "BP03"),  # 5.15: BP03 measurements; W1 corresponds to BP02/BP03
    ("representation", "candidate"): ("BP03", "BP04", "BP15"),  # W4 corresponds to BP03/BP04/BP15
    ("representation", "track"): ("BP03", "BP04"),  # 5.15: BP03 existing track candidates; BP04 tracks
    ("representation", "iq"): ("BP09", "BP13"),  # 5.15: BP09 pulse/IQ; BP13 IQ/frequency-time
    ("block", "estimate"): ("BP01", "BP09"),  # W2 corresponds to BP01/BP09
    ("block", "inversion"): ("BP10",),  # W5 corresponds to BP10
    ("block", "association"): ("BP15",),  # 5.15: BP15 outputs and associations
    ("acquisition", "frames"): ("BP08", "BP11", "BP12"),  # W3 corresponds to BP08/BP11/BP12
    ("acquisition.subcase", "rf-scan"): ("BP13",),  # W7 RF subcase; 5.15: BP13 scan settings
    ("acquisition.subcase", "retarding-scan"): ("BP13",),  # W7 retarding subcase; 5.15: BP13 retarding counts
    ("acquisition.subcase", "global"): ("BP13", "BP14"),  # W7 corresponds to BP13/BP14; 5.15: BP14 pointing plus timestream
}
# A46: the conflict names the probe it needs. Section 5.6 item 3 lists schema, clock, mask, payload and sampling probes; a name
# outside PROBES has no runtime reader yet, and the record says so (probe_registered).
CONFLICT_PROBES = (("sampling.time_", "probe.clock"), ("clock", "probe.clock"), ("sampling.", "probe.sampling"), ("mask", "probe.mask"),
                   ("conditions.", "probe.payload"), ("geometry", "probe.payload"))
SCHEMA_PROBE = "probe.schema"
# Section 5.5, the signature dimensions a reader may establish; "detector" stays unknown unless a source states it (Section 5.5,
# last paragraph: a hardware name may stay unknown).
ONE_VALUE_PREFIX = "constraint."  # DS2: a constraint holds one value across a product's scopes. `product_schema` does not: each file has its own, and K15 keeps them as labels
SIGNATURE_DIMENSIONS = ("container", "product_schema", "representation", "retention", "quantity", "coordinates", "acquisition", "sampling", "conditions", "detector")
# One key must not clear a dimension that needs several; the others are established by any fact under their name.
DIMENSION_KEYS = {"sampling": ("sampling.interval.value", "sampling.interval.unit", "sampling.time_origin", "sampling.time_system"),
                  "retention": ("retention.raw", "retention.waveform", "retention.truth", "retention.candidates", "retention.conditions_snapshot")}


def _peak_resident_bytes() -> int | None:
    """Peak resident size of this process. getrusage gives kibibytes on Linux and bytes on macOS."""
    if not HAS_GETRUSAGE:
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def _inside_import(frame) -> bool:
    """A stop inside a first-time import can leave an extension module half loaded for the life of the process (a valid product then
    reads as malformed), so it waits for the import to end. Walked only when a limit has passed."""
    while frame is not None:
        if frame.f_code.co_filename.startswith("<frozen importlib"):
            return True
        frame = frame.f_back
    return False


def _load_readers() -> bool:
    """Import what a read needs before the budget starts, and say whether it could be. contracts.sidecar_reader and _document_report
    import these lazily, and NumPy comes in behind contracts.reconstruction."""
    try:
        import contracts.reconstruction  # noqa: F401
        import contracts.validate  # noqa: F401
    except ImportError:
        return False
    return True


class _BudgetStop(BaseException):
    """Raised by the watch inside a probe. Not an Exception, so no handler for malformed input can swallow it."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class _DuplicateKey(ValueError):
    """Python keeps the last of two equal JSON keys, which would resolve a conflict silently (A46)."""


class _Spending:
    """What one inspection has spent, watched while it runs: Section 5.6 item 5, A59. The watch is a per-thread profile function,
    restored on leaving. A profile function that raises is unset by Python, so a stop fires once."""

    def __init__(self, limits: dict | None, clock):
        self.limits, self.clock = limits, clock
        self.memory_base = _peak_resident_bytes() if limits else 0
        self.spent: dict[str, float] = {"probes": 0, "bytes": 0, "seconds": 0, "memory_bytes": 0, "tools": 0}
        self.readers: set = set()
        self.plans: list = []
        self.records: dict = {}
        self.stopped = None if limits else "budget-not-declared"
        self.started = clock()
        self.events = 0
        self.rise = 0
        self.previous_watch = sys.getprofile()

    def resume(self) -> None:
        if self.limits:
            sys.setprofile(self.watch)

    def pause(self) -> None:
        sys.setprofile(self.previous_watch)

    def elapsed(self) -> float:
        return max(0.0, self.clock() - self.started)

    def memory(self) -> int | None:
        """The rise of the peak so far, or None when it cannot be measured."""
        peak = _peak_resident_bytes() if self.limits else None
        if peak is None or self.memory_base is None:
            return None
        self.rise = max(self.rise, peak - self.memory_base)
        return self.rise

    def overrun(self, seconds: float | None = None) -> str | None:
        """The limit passed, judged on `seconds` when the caller has read the clock already."""
        if not self.limits:
            return None
        if (self.elapsed() if seconds is None else seconds) >= self.limits["seconds"]:
            return "budget-seconds"
        rise = self.memory()
        return "budget-memory" if rise is None or rise > self.limits["memory_bytes"] else None

    def check(self) -> None:
        reason = self.overrun()
        if reason:
            raise _BudgetStop(reason)

    def watch(self, frame, event, argument) -> None:
        self.events += 1
        if self.events % WATCH_INTERVAL == 0:
            try:
                reason = self.overrun()
            except RecursionError:  # at the stack limit a look fails, and an escaping error would unset the watch
                return
            if reason and not _inside_import(frame):
                raise _BudgetStop(reason)


def _fact(key: str, value, scope: str, reference: str, kind: str = "reader", method: str = "observed", validity: str = "this read", reader_version: str = "1") -> dict:
    """K15: every fact keeps its value, scope, source, method and validity."""
    return {"key": key, "value": value, "scope": scope, "source": {"kind": kind, "reference": reference}, "reader_version": reader_version,
            "method": method, "validity": validity}


def _refuse_constant(constant: str):
    """NaN and Infinity are not JSON, and a file holding one must not keep `container: json`."""
    raise ValueError(f"{constant} is not JSON")


def _unique_keys(pairs: list) -> dict:
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise _DuplicateKey("a key appears twice in one object")
    return dict(pairs)


def _read_bounded(path, planned: int, spending: _Spending) -> bytes:
    """O_NONBLOCK and the second check: a pipe swapped in after the stat must not block the inspection. Every chunk is charged as it
    arrives, and a slow file is stopped between chunks; a single stalled read cannot be interrupted (module docstring)."""
    spending.pause()  # a stop between these two calls would leave the descriptor with no owner
    stream = os.fdopen(os.open(path, os.O_RDONLY | os.O_NONBLOCK), "rb")
    chunks = []
    with stream:
        spending.resume()
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise OSError("not a regular file")
        remaining = planned
        while remaining > 0:
            chunk = stream.read(min(READ_CHUNK_BYTES, remaining))
            if not chunk:
                break
            spending.spent["bytes"] += len(chunk)
            remaining -= len(chunk)
            chunks.append(chunk)
            spending.check()
    return b"".join(chunks)


def _stated(key: str, value, scope: str, reference: str) -> dict:
    """Section 5.5: what a document says about the world is a sourced declaration, not a direct observation."""
    return _fact(key, value, scope, reference, kind="declaration", method="declared", validity="as the document states")


def _sampling_facts(sampling: dict, owner: str, reference: str) -> list:
    statements = {"sampling.interval.value": sampling["interval"]["value"], "sampling.interval.unit": sampling["interval"]["unit"],
              "sampling.time_origin": sampling["time_origin"], "sampling.time_system": sampling["time_system"],
              "sampling.channels": len(sampling["channels"]), "sampling.missing_samples": len(sampling["missing_samples"])}
    return [_stated(key, value, owner, reference) for key, value in statements.items()]


def _constraint_facts(resolution: dict, owner: str, reference: str) -> list:
    """A47: each alternative stays a separate fact, so a condition can name the branch it used."""
    facts = [_stated(f"constraint.external.{resolution['external']['name']}", resolution["external"]["state"], owner, reference),
             _stated("constraint.outcome", resolution["outcome"], owner, reference)]
    for group in ("internal", "joint"):
        for option in resolution[group]:
            facts += [_stated(f"constraint.{group}.{option['name']}", option["state"], owner, reference),
                      _stated(f"constraint.{group}.{option['name']}.sufficient", option["sufficient"], owner, reference)]
    return facts


def _block_facts(document: dict, owner: str, reference: str) -> list:
    """What the blocks of a delivered product say about its form. Each keeps a scope of its own, so one product can carry several
    labels (K15, multi-label)."""
    facts = [_fact("representation", label, f"{owner}/block.{block}", reference) for block, label in REPRESENTATION_BY_BLOCK.items() if block in document]
    facts += [_fact("acquisition", label, f"{owner}/block.{block}", reference) for block, label in ACQUISITION_BY_BLOCK.items() if block in document]
    facts += [_fact("block", block, f"{owner}/block.{block}", reference) for block in OTHER_BLOCKS if block in document]
    if "scan" in document:
        facts.append(_fact("acquisition.subcase", document["scan"]["subcase"], f"{owner}/block.scan", reference))
    if document.get("retention", {}).get("waveform") == "kept":  # the only way a product says it holds traces; a shape says nothing (Section 5.5)
        facts.append(_fact("representation", "waveform", f"{owner}/block.retention", reference, kind="derivation", method="derived", validity="while the retention statement holds"))
    return facts


def _product_facts(document: dict, owner: str, reference: str) -> list:
    """Only fields of a document read_document accepted."""
    facts = [_fact("product_id", document["product_id"], owner, reference), _fact("revision", document["revision"], owner, reference)]
    facts += [_stated(key, document[key], owner, reference) for key in ("presence", "role", "collection")]
    facts.append(_stated("native.type", document["native"]["type"], owner, reference))
    facts.append(_stated("conditions_used_count", len(document["conditions_used"]), owner, reference))  # none consumed is not "none needed" (Section 8.7)
    for used in document["conditions_used"]:
        facts += [_stated(f"conditions.{used['slot']}.payload_id", used["payload_id"], owner, reference), _stated(f"conditions.{used['slot']}.origin", used["origin"], owner, reference)]
    if "sampling" in document:
        facts += _sampling_facts(document["sampling"], owner, reference)
    if "retention" in document:
        facts += [_stated(f"retention.{level}", state, owner, reference) for level, state in document["retention"].items() if isinstance(state, str)]
    if "constraint_resolution" in document:
        facts += _constraint_facts(document["constraint_resolution"], owner, reference)
    if document["presence"] in DELIVERED_PRESENCE:
        facts += _block_facts(document, owner, reference)
    return facts


def _payload_facts(document: dict, owner: str, input_scope: str, reference: str) -> list:
    facts = [_stated("conditions.kind", document["kind"], input_scope, reference), _stated("conditions.origin", document["origin"], input_scope, reference),
             _fact("conditions.payload_id", document["payload_id"], input_scope, reference)]
    if "geometry_id" in document["derived_against"]:
        facts.append(_stated("geometry_id", document["derived_against"]["geometry_id"], owner, reference))
    return facts


def _is_artifact(document) -> bool:
    return isinstance(document, dict) and "artifact_type" in document and "schema" not in document


def _document_report(document) -> Report:
    """The one reading of a parsed document: an envelope artifact through its existing validator, which refuses an unknown required
    capability as K13 refuses an extension, and anything else through read_document. A validator fault is a refusal."""
    if not _is_artifact(document):
        return read_document(document)
    report = Report()
    if document["artifact_type"] not in load_schema("envelope.json")["properties"]["artifact_type"]["enum"]:
        report.add("error", "$.artifact_type", "artifact.unknown_type", f"{document['artifact_type']!r} is not an artifact type this reader knows")
        return report
    if document.get("required_extensions") or (isinstance(document.get("extension"), dict) and document["extension"].get("required_extensions")):
        # K13: the envelope is open, so its validator lets these keys pass; no extension is known here, so none can be honoured
        report.add("error", "$.required_extensions", "reconstruction.reader.unknown_required_extension", "an artifact asks for an extension this reader does not implement")
        return report
    from contracts.validate import validate_artifact  # imported here: heavy, and needed only for an artifact
    try:
        return validate_artifact(document)
    except (*MALFORMED_DOCUMENT, ImportError) as error:
        report.add("error", "$", "artifact.malformed", f"the validator could not read it: {type(error).__name__}")
        return report


def _document_facts(document: dict, owner: str, input_scope: str, reference: str) -> list:
    """Per-file facts keep the scope of their file, so a metadata file beside a table is no conflict (K15)."""
    if _is_artifact(document):
        return [_fact("container", "json", input_scope, reference), _fact("product_schema", ARTIFACT_SCHEMA, input_scope, reference),
                _fact("artifact_type", document["artifact_type"], input_scope, reference)]
    facts = [_fact("container", "json", input_scope, reference), _fact("product_schema", document["schema"], input_scope, reference)]
    if document["schema"] == "reconstruction-product/1":
        facts += _product_facts(document, owner, reference)
    elif document["schema"] == "conditions-payload/1":
        facts += _payload_facts(document, owner, input_scope, reference)
    return facts


def _failed_probe(label: str, stop_reason: str) -> dict:
    return {"outcome": "failed", "stop_reason": stop_reason, "groups": {label: []}, "warnings": [], "documents_refused": 0}


def _json_outcome(raw: bytes, label: str, run: str, reference: str, spending: _Spending) -> dict:
    """A file holds one sidecar or a list of them, a reading of A45: each is read on its own, a list keeps each product's identity,
    and everything refused shares one signature, so a list of junk cannot multiply the record (M1)."""
    try:
        parsed = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_keys, parse_constant=_refuse_constant)
    except _DuplicateKey:
        return _failed_probe(label, "json.duplicate-key")
    except (ValueError, RecursionError):
        return _failed_probe(label, "json.malformed")
    several = isinstance(parsed, list)
    documents = parsed if several else [parsed]
    if not documents:
        return {"outcome": "partial", "stop_reason": "json.no-documents", "groups": {label: [_fact("container", "json", f"{label}/{run}", reference)]}, "warnings": [], "documents_refused": 0}
    if len(documents) > PROBES[JSON_PROBE]["parameters"]["document_ceiling"]:
        return _failed_probe(label, "json.document-ceiling")
    groups: dict = {}
    refusals, warnings, products = [], [], []
    for index, document in enumerate(documents):
        spending.resume()  # Python unsets a profile function that fails at the stack limit or in a weakref callback
        spending.check()
        report = _document_report(document)  # K13: the one stop; no fact comes from a document it refuses
        if not report.ok:
            refusals.append(report.errors[0].code)
            refused_owner = f"{label}/refused" if several else label
            held = groups.setdefault(refused_owner, [])
            if refusals[-1] in NO_KNOWN_SCHEMA and not held:  # what parsed stays, and says nothing of the document
                held.append(_fact("container", "json", f"{refused_owner}/{run}", reference))
            continue
        warnings += [finding.code for finding in report.findings]
        owner = label
        if several:
            owner = f"{label}/{document['product_id']}" if "product_id" in document and not _is_artifact(document) else f"{label}/element.{index}"
            products.append(owner)  # by value: a product may be named `refused`
        facts = _document_facts(document, owner, f"{owner}/{run}", reference)
        if not several and not _is_artifact(document) and document.get("product_id", label) != label:  # A46; an envelope is open, so its key is unchecked: the caller's name for the file is metadata too
            facts.append(_fact("product_id", label, owner, "input-label", kind="declaration", method="declared", validity="as the caller named it", reader_version="not-read"))
        groups.setdefault(owner, []).extend(facts)
    outcome = "read" if not refusals else "partial" if any(groups.values()) else "refused"
    stop_reason = next((code for code in refusals if code not in NO_KNOWN_SCHEMA), refusals[0]) if refusals else None  # a K13 stop outranks "no known schema"
    return {"outcome": outcome, "stop_reason": stop_reason, "groups": groups, "products": products, "warnings": warnings, "documents_refused": len(refusals)}


def _number(cell: str) -> bool:
    try:
        float(cell)
    except ValueError:
        return False
    return True


def _csv_rows(raw: bytes, truncated: bool) -> list | None:
    """Rows of a table, or None. A record cut at the edge of the window is the unread portion, also inside a quoted cell."""
    text = raw.decode("utf-8-sig")
    # '#' lines are comments in the plugin's CSV products, as skills/hep-detector/scripts/build_response.py reads them
    lines = [line for line in io.StringIO(text, newline="") if not line.startswith("#")]
    rows: list = []
    try:
        for row in csv.reader(lines, strict=True):
            if row:
                rows.append(row)
    except csv.Error:
        return rows if truncated and len(rows) > 1 else None
    return rows


def _csv_outcome(raw: bytes, label: str, run: str, reference: str, truncated: bool) -> dict:
    """Header and whole rows inside the window. Column names and cell text stay strings: a name is not a quantity (K15), and no row
    count, numeric type or shape is read as a physics fact (Section 5.5). The suffix chose this reader and proves nothing, so what does
    not read as a table with a header is a failed probe and stays unknown (A59). Those tests are a reading: the plan names none. Prose
    that happens to parse still can pass; it stays an inert string."""
    if b"\0" in raw:
        return _failed_probe(label, "csv.not-text")
    try:
        rows = _csv_rows(raw, truncated)
    except ValueError:
        return _failed_probe(label, "csv.malformed")
    if rows is None:
        return _failed_probe(label, "csv.malformed")
    if not rows:
        return _failed_probe(label, "csv.no-header-in-window")
    header, sample = rows[0], rows[1:]
    if len(set(header)) != len(header):
        return _failed_probe(label, "csv.duplicate-column")
    if any(len(row) != len(header) for row in sample):
        return _failed_probe(label, "csv.ragged-rows")
    if not sample:
        return _failed_probe(label, "csv.no-rows-in-window")
    if all(_number(cell) for cell in header):
        return _failed_probe(label, "csv.no-header")
    if len(header) == 1 and "\t" in header[0]:
        return _failed_probe(label, "csv.not-comma-separated")
    observed = {"container": "csv", "columns": json.dumps(header), "column_count": len(header), "sample_rows": len(sample)}
    return {"outcome": "read", "stop_reason": None, "warnings": [], "documents_refused": 0, "groups": {label: [_fact(key, value, f"{label}/{run}", reference) for key, value in observed.items()]}}


def _declared_budget(budget) -> dict | None:
    """Plan K17 row and Section 5.6 item 5: the caller declares every limit. No default here is a reading, stricter than K10's."""
    if not isinstance(budget, dict) or set(budget) != set(BUDGET_COUNTS) | {"seconds"}:
        return None
    whole = all(type(budget[name]) is int and budget[name] >= 0 for name in BUDGET_COUNTS)
    seconds = budget["seconds"]
    timed = type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0
    return dict(budget) if whole and timed else None


def _planned_probe(index: int, entry) -> dict:
    """What can be known before any read: the reader, from the suffix alone (A43), and the size. A plan with a stop_reason
    does not run."""
    plan = {"index": index, "run": f"run.{index}", "target": f"input.{index}", "probe": None, "size": None, "planned": 0, "stop_reason": None}
    if not isinstance(entry, dict):
        return dict(plan, stop_reason="input-malformed")
    label = entry.get("product")
    if isinstance(label, str) and label:
        plan["target"] = label
    else:
        return dict(plan, stop_reason="input-malformed")
    try:
        given = entry.get("path")
        if given is None:  # os.fspath(None) is the same TypeError
            raise TypeError("no path")
        path = os.fspath(given)
        status = os.stat(path)
    except (TypeError, ValueError):
        return dict(plan, stop_reason="input-malformed")
    except OSError:
        return dict(plan, stop_reason="input-unreadable")
    plan.update(path=path, size=status.st_size)
    suffix = os.path.splitext(path)[1]
    probe = PROBE_BY_SUFFIX.get(suffix.lower() if isinstance(suffix, str) else None)
    if probe is None:  # K15: no recognition without a runtime reader; the file is not opened
        return dict(plan, stop_reason="no-runtime-reader")
    plan["probe"] = probe
    if not stat.S_ISREG(status.st_mode):
        return dict(plan, stop_reason="input-not-regular-file")
    parameters = PROBES[probe]["parameters"]
    if probe == JSON_PROBE and status.st_size > parameters["byte_ceiling"]:
        return dict(plan, stop_reason="probe-ceiling")
    return dict(plan, planned=status.st_size if probe == JSON_PROBE else min(status.st_size, parameters["window_bytes"]))


def _budget_stop(spending: _Spending, plan: dict) -> str | None:
    """Section 5.6 item 5: the limit that forbids this probe, before it starts."""
    limits, spent = spending.limits, spending.spent
    if limits is None:  # _run_probes never asks: an undeclared budget has stopped already
        return "budget-not-declared"
    if spent["probes"] >= limits["probes"]:
        return "budget-probes"
    if PROBES[plan["probe"]]["reader"] not in spending.readers and len(spending.readers) >= limits["tools"]:
        return "budget-tools"
    if spent["bytes"] + plan["planned"] > limits["bytes"]:
        return "budget-bytes"
    return spending.overrun()


def _run_probe(plan: dict, spending: _Spending) -> dict:
    """One registered probe with its fixed parameters. Nothing in the file chooses a probe, a parameter or a next step. A limit
    reached inside it, or passed by a C call the watch could not enter, drops its facts: A59, marked unknown with the reason."""
    began, bytes_before = spending.elapsed(), spending.spent["bytes"]
    target, run, reference = plan["target"], plan["run"], f"{plan['probe']}:{plan['run']}"
    try:
        try:  # _read_bounded starts the watch, on only here, so a stop always lands where it is caught
            raw = _read_bounded(plan["path"], plan["planned"], spending)
            if plan["probe"] == JSON_PROBE:
                scanned = _json_outcome(raw, target, run, reference, spending)
            else:  # the rest of a row cut at the window edge is part of the unread portion
                truncated = plan["planned"] < plan["size"]
                scanned = _csv_outcome(raw[:raw.rfind(b"\n") + 1] if truncated else raw, target, run, reference, truncated)
        finally:
            spending.pause()
    except OSError:
        scanned = _failed_probe(target, "input-unreadable")
    except _BudgetStop as stop:
        scanned = _failed_probe(target, stop.reason)
    except MemoryError:
        scanned = _failed_probe(target, "budget-memory")
    overrun = spending.overrun()
    if overrun and scanned["stop_reason"] not in RESOURCE_STOPS:
        scanned = _failed_probe(target, overrun)
    scanned.update(bytes_read=spending.spent["bytes"] - bytes_before, seconds=max(0.0, spending.elapsed() - began), memory_bytes=spending.rise)
    return scanned


def _probe_record(plan: dict, scanned: dict | None, stop_reason: str | None) -> dict:
    """Section 5.6 item 2: reading scope, sampling rule, cost and unread portion of one probe, run or not."""
    scanned = scanned or {"outcome": "not-run", "stop_reason": stop_reason, "warnings": [], "bytes_read": 0, "seconds": 0, "memory_bytes": 0, "documents_refused": 0}
    registered: dict = PROBES.get(plan["probe"], {"reader": None, "reader_version": None, "parameters": {}})
    if scanned["outcome"] == "not-run":
        scope, sampling = "nothing", "none"
    elif plan["planned"] < plan["size"]:
        scope, sampling = "first window", "header and complete rows inside the fixed window"
    else:
        scope, sampling = "whole file", "none"
    return {"run": plan["run"], "probe": plan["probe"] if registered["reader"] else None, "reader": registered["reader"], "reader_version": registered["reader_version"],
            "parameters": dict(registered["parameters"]), "target": plan["target"], "outcome": scanned["outcome"], "stop_reason": scanned["stop_reason"],
            "cost": {"bytes_read": scanned["bytes_read"], "seconds": scanned["seconds"], "memory_bytes": scanned["memory_bytes"]}, "read_scope": scope, "sampling": sampling,
            "unread_bytes": None if plan["size"] is None else plan["size"] - scanned["bytes_read"], "documents_refused": scanned["documents_refused"], "warnings": scanned["warnings"]}


def _fact_value(value) -> bool:
    """input_signature.json: a fact holds a string, a finite number or a boolean."""
    return type(value) in (str, bool, int) or (type(value) is float and math.isfinite(value))


def _settled(fact: dict) -> bool:
    """K15: a value an LLM extracted stays a declaration to check, so it establishes nothing yet."""
    return fact["source"]["kind"] != "llm-extraction" and fact["method"] in ("observed", "declared", "derived")


def _established(dimension: str, settled_keys: set) -> bool:
    if dimension in DIMENSION_KEYS:
        return all(key in settled_keys for key in DIMENSION_KEYS[dimension])
    return any(key == dimension or key.startswith(f"{dimension}.") for key in settled_keys)


def _family_candidates(facts: list) -> list:
    """Section 5.15: every clue keeps its candidates; a conflict between labels keeps both sets (A46)."""
    clues = {(fact["key"], fact["value"]) for fact in facts if _settled(fact)}
    return sorted({candidate for clue in clues for candidate in CANDIDATES_BY_CLUE.get(clue, ())})


def _declared_facts(entry: dict, label: str) -> tuple:
    """Section 5.6 item 1: a known manifest may state facts. They stay declarations, a declaration states its kind, and what is not
    evidence stays visible and unused (K15, A49). A declared fact can describe a file no reader opens, a reading of Section 5.5."""
    offered = entry.get("declared", [])
    if not isinstance(offered, list):
        return [], [{"product": label, "key": "declared", "reason": "declaration-malformed"}]
    facts, refused = [], []
    for item in offered:
        fields = item if isinstance(item, dict) else {}
        key, value, reference, kind = fields.get("key"), fields.get("value"), fields.get("reference"), fields.get("kind")
        if not (isinstance(key, str) and key and _fact_value(value) and isinstance(reference, str) and reference and isinstance(kind, str)):
            refused.append({"product": label, "key": key if isinstance(key, str) and key else "declared", "reason": "declaration-malformed"})
        elif kind not in DECLARABLE_KINDS or reference.startswith(NOT_EVIDENCE_REFERENCES):
            refused.append({"product": label, "key": key, "reason": "not-evidence"})
        else:
            facts.append(_fact(key, value, label, reference, kind=kind, method="declared", validity="as declared", reader_version="not-read"))
    return facts, refused


def _same_value(first, second) -> bool:
    """A number and a boolean differ, though Python calls 1 and True equal; 1 and 1.0 are the same value."""
    return isinstance(first, bool) == isinstance(second, bool) and first == second


def _required_probe(key: str) -> str:
    return next((probe for prefix, probe in CONFLICT_PROBES if key.startswith(prefix)), SCHEMA_PROBE)


def _conflict(key: str, scope: str, facts: list) -> dict:
    """A46: every value stays with its source, and no value is chosen. Section 5.5: no majority vote."""
    required = _required_probe(key)
    return {"key": key, "scope": scope, "values": [{"value": fact["value"], "source_kind": fact["source"]["kind"], "reference": fact["source"]["reference"]} for fact in facts],
            "required_probe": required, "probe_registered": required in PROBES}


def _conflicts(facts: list) -> list:
    """Section 5.5: values differ on one key and scope, or a statement about a whole product matches nothing read in its narrower
    scopes (a reading, so that metadata against the read schema is caught while multi-label stays clean). Facts of different scopes
    are multi-label, not a conflict (K15). A46, A48: a waveform claimed on a product whose traces were removed. Linear in the facts."""
    by_key: dict = {}
    for fact in facts:
        by_key.setdefault(fact["key"], {}).setdefault(fact["scope"], []).append(fact)
    found = []
    for key in sorted(by_key):
        scopes = by_key[key]
        for scope in sorted(scopes):
            same_scope = scopes[scope]
            narrower = [fact for inner_scope, held in scopes.items() if inner_scope.startswith(f"{scope}/") for fact in held]
            if any(not _same_value(fact["value"], same_scope[0]["value"]) for fact in same_scope):
                found.append(_conflict(key, scope, same_scope))
            elif narrower and not any(_same_value(same_scope[0]["value"], fact["value"]) for fact in narrower):
                found.append(_conflict(key, scope, same_scope + narrower))
    removed = [fact for held in by_key.get("retention.waveform", {}).values() for fact in held if fact["value"] == "removed"]
    claimed = [fact for held in by_key.get("representation", {}).values() for fact in held if fact["value"] == "waveform"]
    if removed and claimed:
        found.append(_conflict("representation", claimed[0]["scope"], claimed + removed))
    return found


def _signature(label: str, facts: list, records: list, conflicts: list) -> dict:
    """K15: per product and scope. A dimension no fact establishes stays unknown."""
    if not any(record["outcome"] in ("read", "partial") for record in records):
        window = "not read"
    else:
        window = "bounded sample" if any(record["read_scope"] == "first window" for record in records) else "whole product"
    settled_keys = {fact["key"] for fact in facts if _settled(fact)}
    return {"schema": "input-signature/1", "signature_id": f"signature.{label}", "scope": {"product": label, "window": window}, "facts": facts,
            "unknown": [dimension for dimension in SIGNATURE_DIMENSIONS if not _established(dimension, settled_keys)],
            "conflicts": sorted({conflict["key"] for conflict in conflicts}), "family_candidates": _family_candidates(facts), "required_extensions": []}


def _inspection(state: str, stop_reason, limits, spent: dict, signatures: list, probes: list, refused: list | None = None, conflicts: list | None = None) -> dict:
    products_read = sorted({probe["target"] for probe in probes if probe["outcome"] in ("read", "partial")})
    products_unread = sorted({probe["target"] for probe in probes} - set(products_read))
    return {"schema": "input-inspection/1", "state": state, "stop_reason": stop_reason, "budget": limits, "spent": spent, "signatures": signatures,
            "probes": probes, "conflicts": conflicts or [], "refused_declarations": refused or [], "products_read": products_read, "products_unread": products_unread,
            "required_extensions": []}


def _no_cost() -> dict:
    return {"probes": 0, "bytes": 0, "seconds": 0, "memory_bytes": 0, "tools": 0}


def _public_probe(record: dict) -> dict:
    return {name: field for name, field in record.items() if name not in ("groups", "products")}


def _run_probes(spending: _Spending) -> None:
    """Section 5.16: of known probes, lower costs first, in a fixed order; no information-gain number is formed. The sentence also
    asks for common blockers and more direct sources first; there is one probe per file, so there is nothing else to order."""
    for plan in sorted(spending.plans, key=lambda item: (item["planned"], item["index"])):
        if plan["stop_reason"]:
            spending.records[plan["index"]] = _probe_record(plan, None, plan["stop_reason"])
            continue
        spending.stopped = spending.stopped or _budget_stop(spending, plan)
        if spending.stopped:
            spending.records[plan["index"]] = _probe_record(plan, None, spending.stopped)
            continue
        spending.spent["probes"] += 1
        spending.readers.add(PROBES[plan["probe"]]["reader"])
        spending.spent["tools"] = len(spending.readers)
        scanned = _run_probe(plan, spending)
        spending.records[plan["index"]] = dict(_probe_record(plan, scanned, None), groups=scanned["groups"], products=scanned.get("products", []))
        if scanned["stop_reason"] in BUDGET_STOPS:
            spending.stopped = scanned["stop_reason"]


def _gathered_facts(inputs, records: dict) -> tuple:
    """Facts and records by owner. A declaration on a file reaches each product read from it, so a list file hides no conflict (A46)."""
    grouped: dict = {}
    refused: list = []
    for index in sorted(records):
        record = records[index]
        target = record["target"]
        for owner, facts in record.get("groups", {target: []}).items():
            held = grouped.setdefault(owner, {"facts": [], "records": []})
            held["facts"] += facts
            held["records"].append(record)
        if isinstance(inputs[index], dict):
            declared, offered = _declared_facts(inputs[index], target)
            refused += offered
            for owner in record.get("products") or [target]:
                if declared:
                    held = grouped.setdefault(owner, {"facts": [], "records": [record]})
                    held["facts"] += [dict(fact, scope=owner) for fact in declared]
    return grouped, refused


def _inspected(inputs, spending: _Spending) -> dict:
    spending.plans = [_planned_probe(index, entry) for index, entry in enumerate(inputs)]
    _run_probes(spending)
    if not spending.stopped:  # after a stop only what was read within the budget is left to assemble
        spending.resume()
    grouped, refused = _gathered_facts(inputs, spending.records)
    by_owner = {owner: _conflicts(held["facts"]) for owner, held in grouped.items()}
    signatures = [_signature(owner, held["facts"], held["records"], by_owner[owner]) for owner, held in grouped.items()]
    probes = [_public_probe(spending.records[index]) for index in sorted(spending.records)]
    conflicts = [conflict for found in by_owner.values() for conflict in found]
    first_reason = next((probe["stop_reason"] for probe in probes if probe["stop_reason"]), None)
    open_reason = first_reason or ("conflict-unresolved" if conflicts else None)  # A46: a conflict is never a clean end
    state = "stopped" if spending.stopped else "partial" if open_reason else "complete"
    return _inspection(state, spending.stopped or open_reason, spending.limits, spending.spent, signatures, probes, refused, conflicts)


def _bare_record(reason: str, spending: _Spending) -> dict:
    """Fail closed, cost kept: every product unknown and no fact, when assembly stopped or the reader refused the record."""
    for plan in spending.plans:
        spending.records.setdefault(plan["index"], _probe_record(plan, None, reason))
    probes = [_public_probe(spending.records[index]) for index in sorted(spending.records)]
    signatures = [] if reason == "record-refused" else [_signature(label, [], [], []) for label in sorted({probe["target"] for probe in probes})]
    return _inspection("stopped", reason, spending.limits, spending.spent, signatures, probes)


def _closed(record: dict, spending: _Spending) -> dict:
    """The whole inspection is charged, the last check included (plan K17 row: total cost), and an overrun found now still stops."""
    seconds = spending.elapsed()  # one reading decides and charges, so a record never exceeds what it was judged on
    overrun = spending.overrun(seconds)
    spending.spent.update(seconds=seconds, memory_bytes=spending.rise)
    if overrun:
        record["state"], record["stop_reason"] = "stopped", overrun
    return record


def inspect_inputs(inputs, budget, clock=time.monotonic) -> dict:
    """One bounded inspection of the inputs, each {"product": name, "path": location, "declared": [facts]}, under a declared budget of
    probes, bytes, seconds, memory_bytes and tools. Always returns an input-inspection/1 record: what cannot be read stays unknown
    (Sections 5.6, 5.7). A declared fact is {"key", "value", "reference", "kind"}."""
    if not isinstance(inputs, (list, tuple)):
        return _inspection("stopped", "inputs-malformed", None, _no_cost(), [], [])
    if not inputs:  # A16; Section 5.3 step 1: a conceptual question names no input, so nothing is read and no budget is needed
        return _inspection("not-needed", None, None, _no_cost(), [], [])
    if not _load_readers():
        return _inspection("stopped", "readers-unavailable", None, _no_cost(), [], [])
    spending = _Spending(_declared_budget(budget), clock)
    try:
        try:
            record = _closed(_inspected(inputs, spending), spending)
            reason = None if read_document(record).ok else "record-refused"
        finally:
            spending.pause()
    except _BudgetStop as stop:
        reason = stop.reason
    except MemoryError:
        reason = "budget-memory"
    except (*MALFORMED_DOCUMENT, ImportError):
        reason = "record-refused"
    return _closed(_bare_record(reason, spending) if reason else record, spending)


def _check_probe(probe: dict, report: Report, path: str) -> None:
    registered = PROBES.get(probe["probe"])
    if probe["probe"] is None:
        fixed = probe["outcome"] == "not-run" and probe["reader"] is None and probe["reader_version"] is None and probe["parameters"] == {}
    else:
        fixed = registered is not None and all(probe[field] == registered[field] for field in ("reader", "reader_version", "parameters"))
    if not fixed:  # Section 5.6: known reader contracts and fixed parameter combinations, with verified versions
        report.add("error", f"{path}.probes", "reconstruction.inspection.unknown_probe", f"{probe['run']} is not a registered probe with its fixed parameters")
    if (probe["outcome"] == "read") != (probe["stop_reason"] is None):  # A59
        report.add("error", f"{path}.probes", "reconstruction.inspection.stop_without_reason", f"{probe['run']}: {probe['outcome']} and stop reason {probe['stop_reason']!r}")
    if (probe["outcome"] == "not-run") != (probe["read_scope"] == "nothing"):  # Section 5.6 item 2
        report.add("error", f"{path}.probes", "reconstruction.inspection.scope_mismatch", f"{probe['run']}: {probe['outcome']} with read scope {probe['read_scope']!r}")


def _check_state(inspection: dict, report: Report, path: str) -> None:
    """A59, A46: what stayed unknown or in conflict is never a clean answer, and a stop states its reason."""
    state, probes = inspection["state"], inspection["probes"]
    if state in ("partial", "stopped") and inspection["stop_reason"] is None:
        report.add("error", f"{path}.stop_reason", "reconstruction.inspection.stop_without_reason", f"a {state} inspection states why")
    clean = state == "complete" and (inspection["stop_reason"] is not None or not probes or inspection["conflicts"] or any(probe["outcome"] != "read" for probe in probes))
    if clean or (state == "not-needed" and (probes or inspection["signatures"])):
        report.add("error", f"{path}.state", "reconstruction.inspection.state_hides_a_stop", f"{state} does not fit the probes of this record")


def _check_products(inspection: dict, report: Report, path: str) -> None:
    """Section 5.6 item 5: the deliverable portions are the products some probe read."""
    probes = inspection["probes"]
    read_targets = {probe["target"] for probe in probes if probe["outcome"] in ("read", "partial")}
    if set(inspection["products_read"]) != read_targets or set(inspection["products_unread"]) != {probe["target"] for probe in probes} - read_targets:
        report.add("error", f"{path}.products_read", "reconstruction.inspection.products_mismatch", "products_read and products_unread do not follow from the probes")


def _check_cost(inspection: dict, report: Report, path: str) -> None:
    """Section 5.6 items 2 and 5, SEL03, plan K17 row: no cost disappears, and no limit is passed. A C call can pass seconds or memory
    before anything can look, so that is accepted only as an honest stop for that reason."""
    probes = inspection["probes"]
    spent, limits = inspection["spent"], inspection["budget"]
    ran = [probe for probe in probes if probe["outcome"] != "not-run"]
    tools = {probe["reader"] for probe in ran}
    charged = sum(probe["cost"]["seconds"] for probe in probes)  # the probes are only part of the whole, so the total can be larger
    if spent["probes"] != len(ran) or spent["tools"] != len(tools) or spent["bytes"] != sum(probe["cost"]["bytes_read"] for probe in probes) or spent["seconds"] < charged * (1 - 1e-9):
        report.add("error", f"{path}.spent", "reconstruction.inspection.cost_mismatch", "spent does not add up from the probes")
    passed = limits and any(spent[name] > limits[name] for name in ("probes", "bytes", "tools"))
    honest_stop = inspection["state"] == "stopped" and inspection["stop_reason"] in RESOURCE_STOPS
    resources = limits and any(spent[name] > limits[name] for name in ("seconds", "memory_bytes")) and not honest_stop
    if (ran and limits is None) or passed or resources:
        report.add("error", f"{path}.spent", "reconstruction.inspection.over_budget", "more was spent than the declared budget allows, and no stop says so")


def _check_inspection(inspection: dict, report: Report, path: str = "$") -> None:
    """Semantic rules of input-inspection/1; each signature goes through the one K13 reader."""
    for index, signature in enumerate(inspection["signatures"]):
        report.findings.extend(read_document(signature, path=f"{path}.signatures[{index}]").findings)
    if not report.ok:
        return
    for probe in inspection["probes"]:
        _check_probe(probe, report, path)
    _check_state(inspection, report, path)
    _check_products(inspection, report, path)
    _check_cost(inspection, report, path)
    runs = {f"{probe['probe']}:{probe['run']}" for probe in inspection["probes"] if probe["outcome"] in ("read", "partial")}
    named = {conflict["key"] for conflict in inspection["conflicts"]}
    for signature in inspection["signatures"]:
        for fact in signature["facts"]:
            if fact["source"]["kind"] in ("reader", "derivation") and fact["source"]["reference"] not in runs:  # K15: no claim without a runtime reader
                report.add("error", f"{path}.signatures", "reconstruction.inspection.fact_without_reader", f"{fact['key']}: no probe that ran stands behind it")
        for key in signature["conflicts"]:
            if key not in named:  # A46
                report.add("error", f"{path}.conflicts", "reconstruction.inspection.conflict_without_probe", f"{key}: a conflict names the probe it needs")


def _condition_state(state: str, branch=(), open_keys=(), unmet=()) -> dict:
    return {"state": state, "branch": list(branch), "open": list(open_keys), "unmet": list(unmet)}


def _same_product(scope: str, product: str) -> bool:
    """Section 5.5: a signature is per product and scope, so a fact of another product says nothing here. A file's fact reaches the
    products read from it, and a block's fact belongs to its product."""
    return scope == product or scope.startswith(f"{product}/") or product.startswith(f"{scope}/")


def _fact_state(signature: dict, key: str, expected) -> dict:
    """SEL05: satisfied, unsatisfied, unknown or conflicting. An unknown necessary condition is not treated as true. DS2: "If schema
    or the internal evidence used has a scope conflict, resolve it first". A schema conflict is what _conflicts names: two values in one scope,
    or a statement about a product that nothing read in it matches. Two files under one label keep two schemas, as labels (K15). A constraint
    in two scopes of one product conflicts here too; the inspector keeps those facts at the owner's scope, so this acts on a hand-written window."""
    facts = [fact for fact in signature["facts"] if fact["key"] == key and _same_product(fact["scope"], signature["scope"]["product"])]
    unit_key = f"{key[:-len('.value')]}.unit" if key.endswith(".value") else None  # 1 ns against 1 ps: the bare 1 means nothing
    if key in signature["conflicts"] or unit_key in signature["conflicts"] or any(fact["method"] == "conflict" for fact in facts):
        return _condition_state("conflicting", open_keys=[key])
    settled = [fact for fact in facts if _settled(fact)]
    if key.startswith(ONE_VALUE_PREFIX) and any(not _same_value(fact["value"], settled[0]["value"]) for fact in settled):
        return _condition_state("conflicting", open_keys=[key])
    if not settled or key in signature["unknown"]:
        return _condition_state("unknown", open_keys=[key])
    if any(_same_value(fact["value"], expected) for fact in settled):
        return _condition_state("satisfied", branch=[key])
    return _condition_state("unsatisfied", unmet=[key])


def _joined(parts: list, order: tuple, branch: list) -> dict:
    """The first state of `order` found among the parts. No key is lost: an open key on an unused branch stays visible."""
    state = next(state for state in order if any(part["state"] == state for part in parts))
    return _condition_state(state, branch if state == "satisfied" else [], [key for part in parts for key in part["open"]], [key for part in parts for key in part["unmet"]] if state != "satisfied" else [])


def _judged_condition(signature: dict, condition) -> dict:
    """Section 5.8. AND: one unsatisfied item makes a candidate ineligible, and otherwise unknowns and conflicts forbid routine
    composition. OR: a branch passes only when fully satisfied, and the branch used is named; unused branches may be missing. A
    conflict on any branch gives `conflicting`, even if another branch would pass: the user's ruling (decisions.md, "T14 rulings").
    So conflict outranks unsatisfied at every level, or an AND inside a branch would hide it. Either state excludes the candidate.
    A malformed condition is unknown: an empty list must not read as vacuously true."""
    shape = set(condition) if isinstance(condition, dict) else None
    if shape == {"fact", "equals"} and isinstance(condition["fact"], str) and condition["fact"] and _fact_value(condition["equals"]):
        return _fact_state(signature, condition["fact"], condition["equals"])
    if shape in ({"all_of"}, {"any_of"}):
        items = condition.get("all_of", condition.get("any_of"))
        if isinstance(items, list) and items:
            parts = [_judged_condition(signature, item) for item in items]
            if shape == {"all_of"}:
                return _joined(parts, ("conflicting", "unsatisfied", "unknown", "satisfied"), [key for part in parts for key in part["branch"]])
            used: list = next((part["branch"] for part in parts if part["state"] == "satisfied"), [])
            return _joined(parts, ("conflicting", "satisfied", "unknown", "unsatisfied"), used)
    return _condition_state("unknown", open_keys=["malformed condition"])


def _judgment(name, judged: dict) -> dict:
    """Only these fields: a candidate's score, confidence or claimed state is not read and not carried on (A49)."""
    reasons = {"satisfied": "every necessary condition holds", "unsatisfied": f"not satisfied: {', '.join(judged['unmet'])}",
               "unknown": f"not established: {', '.join(judged['open'])}", "conflicting": f"in conflict or not established: {', '.join(judged['open'])}" + (f"; not satisfied: {', '.join(judged['unmet'])}" if judged["unmet"] else "")}
    return {"candidate": name, "state": judged["state"], "eligible": judged["state"] == "satisfied", "branch": judged["branch"], "open": judged["open"], "reason": reasons[judged["state"]]}


def _candidate_name(candidate, index: int) -> str:
    name = candidate.get("candidate") if isinstance(candidate, dict) else None
    return name if isinstance(name, str) and name else f"candidate.{index}"


def _refused_judgments(report: Report, arguments: dict) -> list:
    """Fail closed: a signature the reader refuses leaves every candidate unknown."""
    candidates = arguments.get("candidates")
    named = candidates if isinstance(candidates, list) else []
    return [_judgment(_candidate_name(candidate, index), _condition_state("unknown", open_keys=["signature refused"])) for index, candidate in enumerate(named)]


@reader_path("signature", refused=_refused_judgments)
def judge_candidates(signature: dict, candidates) -> list:
    """Each candidate, {"candidate": name, "requires": condition}, judged on one product's signature, in the given order.
    A condition is {"fact": key, "equals": value}, {"all_of": [...]} or {"any_of": [...]}. This judges necessary conditions
    only (SEL05): it ranks nothing and selects nothing. A candidate with no name is not judged eligible."""
    if not isinstance(candidates, list):
        return []
    judged = []
    for index, candidate in enumerate(candidates):
        named = isinstance(candidate, dict) and isinstance(candidate.get("candidate"), str) and bool(candidate["candidate"])
        condition = _judged_condition(signature, candidate["requires"]) if named and "requires" in candidate else _condition_state("unknown", open_keys=["malformed candidate"])
        judged.append(_judgment(_candidate_name(candidate, index), condition))
    return judged
