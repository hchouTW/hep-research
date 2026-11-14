"""acts-tracking-finding-record/1 and /2: what acts_tracking_finder did with every event and candidate, read back. Data side: no truth here.

The record holds the search, candidates of at least 6 hits and selected branches and failure categories (t07-t09-task-sheets.md, Output; BP03), beside the
product, which holds the selected tracks' states. The reader stops at anything it does not know, and at a record that hides a limit: a candidate of a
truncated seed, or of an event whose seed or ambiguity budget ran out, is marked search-truncated (BP03; section 8.4), and a failed candidate states its
category (t04-prereg.md, Failure classes). acts-tracking-finding-seeds/1, the finder's optional side file, says what became of every seed. Sections cited
are of t04-values-v4.md. Standard library only.

/2 (D1 stage 7) is written when the finder is asked for the vertex step, recipe reco.vertex.acts-amvf/1 (native/track_vertexing.hpp): the same lines as /1, plus in the
header the vertex recipe, the hash of its configuration and that configuration, and after each event's candidates one vertexing line (status, tracks handed over,
tracks that could not be carried to the reference line, vertices), each vertex (global ACTS x, y, z in mm, covariance xx xy xz yy yz zz, chi2, ndf, track count) and
its tracks (candidate key, weight, chi2, compatibility). /1 stays readable, since earlier jobs' records are compared with this one, and finding_lines_of gives the /1
text a /2 record holds, so the finder's track lines can be compared byte for byte. A vertex track must be a selected candidate of its event, and nothing is dropped.
"""
from __future__ import annotations

import hashlib
import math

RECORD_FORMAT = "acts-tracking-finding-record/1"
VERTEX_RECORD_FORMAT = "acts-tracking-finding-record/2"
VERTEX_RECIPE = "reco.vertex.acts-amvf/1"
VERTEX_HEADER_FIELDS = ("vertex_recipe", "vertex_configuration_sha256")
VERTEX_CONFIGURATION_KEYS = ("vertex_seed_finder", "vertex_seed_density", "vertex_seed_gaussian_shaped", "vertex_seed_d0_max_significance", "vertex_seed_z0_max_significance",
                             "vertex_fitter", "vertex_linearizer", "vertex_linearizer_target_tolerance", "vertex_estimator_max_iterations", "vertex_estimator_precision",
                             "vertex_fitter_max_iterations", "vertex_fitter_max_dist_to_lin_point_mm", "vertex_fitter_min_weight", "vertex_fitter_max_relative_shift",
                             "vertex_fitter_do_smoothing", "vertex_fitter_use_time", "vertex_annealing_cut_off", "vertex_annealing_temperatures",
                             "vertex_finder_tracks_max_z_interval_mm", "vertex_finder_tracks_max_significance", "vertex_finder_max_vertex_chi2", "vertex_finder_do_real_multi_vertex",
                             "vertex_finder_use_fast_compatibility", "vertex_finder_max_merge_vertex_significance", "vertex_finder_min_weight", "vertex_finder_max_iterations",
                             "vertex_finder_add_single_track_vertices", "vertex_finder_do_full_splitting", "vertex_finder_maximum_vertex_contamination",
                             "vertex_finder_use_seed_constraint", "vertex_finder_initial_variances", "vertex_finder_default_constraint_fit_quality",
                             "vertex_finder_use_vertex_cov_for_ip_estimation", "vertex_finder_use_time", "vertex_finder_do_not_break_while_seeding", "vertex_reference_x_mm",
                             "vertex_reference_y_mm", "vertex_reference_z_mm", "vertex_constraint_in_fit", "vertex_track_state", "vertex_reference_propagation_max_steps")
VERTEXING_STATUSES = ("ok", "failed")
VERTEX_LINES = ("vertexing", "vertex", "vertex-track")
HEADER_FIELDS = ("recipe", "stage", "evidence_class", "product_id", "data_sha256", "product_events", "configuration_sha256")
FINDING_RECIPE, FINDING_STAGE, FINDING_EVIDENCE_CLASS = "reco.track.acts-ckf-planar/1", "find-ckf", "data-side"
EVENT_COUNTERS = ("hit_count", "seeds_found", "seeds_run", "seeds_skipped", "seeds_failed", "seeds_without_candidate", "seeds_truncated", "seed_budget_reached",
                  "ambiguity_budget_reached", "candidates", "selected")
CANDIDATE_CATEGORY_OF_OUTCOME = {"selected": "none", "evicted": "ambiguity", "fit-failed": "fit"}
EVENT_CATEGORIES = ("none", "seed-or-finding", "search-truncated")
CONFIGURATION_KEYS = ("seed_plane_triples", "seed_lowest_momentum_gev", "seed_largest_slope_u", "seed_largest_slope_v", "seed_window_sigma", "seed_prior_inflation", "finding_chi2_cut",
                      "finding_least_measurements", "finding_most_holes", "finding_most_branches_per_surface", "finding_most_branches_per_seed", "finding_most_seeds_per_event",
                      "finding_most_propagator_steps", "ambiguity_most_shared_hits", "ambiguity_most_iterations", "finding_fit_passes", "seed_derivative_step_sigma", "refit_start_x_mm",
                      "refit_prior_loc_sigma_mm", "refit_prior_angle_sigma", "refit_prior_qop_sigma_per_gev", "refit_prior_time_sigma", "diagnostic_build",
                      "seed_slope_along_v", "seed_covariance_phi_term")
# What jobs 7493849 to 7494405 wrote, in their order: their configuration hash covers these lines, so a later record can be compared with them key by key.
EARLIER_CONFIGURATION_KEYS = CONFIGURATION_KEYS[:15]
# What job 7496491 wrote: the two keys after these name the seed's code, the slope along v and the covariance's phi term, so that the hash tells recipes apart (D1 stage 5e review, m5).
STAGE_5D_CONFIGURATION_KEYS = CONFIGURATION_KEYS[:23]
SEED_FILE_FORMAT = "acts-tracking-finding-seeds/1"
SEED_OUTCOMES = ("skipped", "no-start", "filter-error", "step-limit", "no-candidate", "candidates")


class RecordFormatError(ValueError):
    """The text is not acts-tracking-finding-record/1 or /2, or it hides what a limit did or drops a vertex or a track at one."""


def _number(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise RecordFormatError(f"not a finite number: {token}")
    return value


def _event(tokens) -> dict:
    if len(tokens) != 14:
        raise RecordFormatError(f"an event has {len(tokens)} fields")
    event = {"ordinal": int(tokens[1]), "failure_category": tokens[13], "found": []}
    event.update({name: int(token) for name, token in zip(EVENT_COUNTERS, tokens[2:13])})
    if event["failure_category"] not in EVENT_CATEGORIES:
        raise RecordFormatError(f"unknown event category {event['failure_category']}")
    return event


def _candidate(tokens) -> dict:
    if len(tokens) != 14:
        raise RecordFormatError(f"a candidate has {len(tokens)} fields")
    outcome, category = tokens[4], tokens[5]
    if CANDIDATE_CATEGORY_OF_OUTCOME.get(outcome) != category:
        raise RecordFormatError(f"outcome {outcome} with category {category}")
    candidate = {"key": tokens[1], "ordinal": int(tokens[2]), "seed_planes": tokens[3], "outcome": outcome, "failure_category": category, "search_truncated": tokens[6] == "1",
                 "measurements": int(tokens[7]), "holes": int(tokens[8]), "search_chi2": _number(tokens[9]), "q_over_p": _number(tokens[10]), "fit_chi2": _number(tokens[11]),
                 "fit_coordinates": int(tokens[12]), "hit_keys": [int(key) for key in tokens[13].split(",")]}
    if tokens[6] not in ("0", "1"):
        raise RecordFormatError("search_truncated is 0 or 1")
    if candidate["measurements"] != len(candidate["hit_keys"]):
        raise RecordFormatError(f"{candidate['key']} counts {candidate['measurements']} hits and lists {len(candidate['hit_keys'])}")
    return candidate


def _vertexing(tokens) -> dict:
    if len(tokens) != 6 or tokens[2] not in VERTEXING_STATUSES:
        raise RecordFormatError(f"not a vertexing line: {' '.join(tokens)}")
    return {"ordinal": int(tokens[1]), "status": tokens[2], "input_tracks": int(tokens[3]), "unconverted_tracks": int(tokens[4]), "vertex_count": int(tokens[5]), "vertices": []}


def _vertex(tokens) -> dict:
    if len(tokens) != 15:
        raise RecordFormatError(f"a vertex has {len(tokens)} fields")
    numbers = [_number(token) for token in tokens[3:14]]
    return {"key": tokens[1], "ordinal": int(tokens[2]), "position_mm": numbers[0:3], "covariance": numbers[3:9], "chi2": numbers[9], "ndf": numbers[10],
            "track_count": int(tokens[14]), "tracks": []}


def _vertex_track(tokens) -> dict:
    if len(tokens) != 6:
        raise RecordFormatError(f"a vertex track has {len(tokens)} fields")
    return {"vertex_key": tokens[1], "track_key": tokens[2], "weight": _number(tokens[3]), "chi2": _number(tokens[4]), "compatibility": _number(tokens[5])}


def covariance_is_positive_definite(covariance) -> bool:
    """xx xy xz yy yz zz: Sylvester's criterion, every leading principal minor positive (D1 stage 7b: a positive diagonal is not enough). The determinant is an explicit
    cofactor sum, so a positive definite matrix with a condition number above about 1e12 can be refused by rounding: stricter, never looser (D1 stage 7b review n1)."""
    xx, xy, xz, yy, yz, zz = covariance
    second = xx * yy - xy * xy
    third = xx * (yy * zz - yz * yz) - xy * (xy * zz - yz * xz) + xz * (xy * yz - yy * xz)
    return xx > 0.0 and second > 0.0 and third > 0.0


def vertexing_defects(event: dict) -> list:
    """An event of a /2 record: one vertexing line, every vertex it counts, every track each vertex counts, and each of those a selected candidate of the event, once per vertex.
    A failed event keeps no vertex. A vertex's covariance is positive definite."""
    vertexing = event.get("vertexing")
    if vertexing is None:
        return [f"event {event['ordinal']} has no vertexing line"]
    defects = []
    if vertexing["vertex_count"] != len(vertexing["vertices"]):
        defects.append(f"event {event['ordinal']} counts {vertexing['vertex_count']} vertices and holds {len(vertexing['vertices'])}")
    if vertexing["status"] == "failed" and vertexing["vertices"]:
        defects.append(f"event {event['ordinal']} failed its vertexing and keeps a vertex")
    selected = {item["key"] for item in event["found"] if item["outcome"] == "selected"}
    if vertexing["input_tracks"] + vertexing["unconverted_tracks"] != len(selected):
        defects.append(f"event {event['ordinal']} hands {vertexing['input_tracks']} and loses {vertexing['unconverted_tracks']} of its {len(selected)} delivered tracks")
    for vertex in vertexing["vertices"]:
        keys = [track["track_key"] for track in vertex["tracks"]]
        if vertex["track_count"] != len(keys):
            defects.append(f"{vertex['key']} counts {vertex['track_count']} tracks and lists {len(keys)}")
        if not set(keys) <= selected or len(set(keys)) != len(keys):
            defects.append(f"{vertex['key']} holds a track that is not a delivered track of its event, or one twice")
        if not covariance_is_positive_definite(vertex["covariance"]):
            defects.append(f"{vertex['key']} has a covariance that is not positive definite")
    return defects


def finding_lines_of(text: str) -> str:
    """The /1 record a /2 record holds: its vertex header and lines left out, the end record without the vertex count. A /1 record comes back as it is."""
    lines = text.split("\n")
    if lines[0] == RECORD_FORMAT:
        return text
    if lines[0] != VERTEX_RECORD_FORMAT or lines[-1] != "":
        raise RecordFormatError(f"not {RECORD_FORMAT} or {VERTEX_RECORD_FORMAT}")
    kept = [RECORD_FORMAT]
    for line in lines[1:-1]:
        name = line.split(" ", 1)[0]
        if name in VERTEX_HEADER_FIELDS or name == "vertex_configuration" or name in VERTEX_LINES:
            continue
        if name == "end":
            tokens = line.split(" ")
            if len(tokens) != 4:
                raise RecordFormatError("a /2 end record counts events, candidates and vertices")
            line = " ".join(tokens[:3])
        kept.append(line)
    return "\n".join(kept) + "\n"


def vertex_configuration_sha256(configuration: dict) -> str:
    """As the finder hashes it: the vertex_configuration lines, in their order."""
    return hashlib.sha256("".join(f"vertex_configuration {name} {configuration[name]}\n" for name in VERTEX_CONFIGURATION_KEYS).encode()).hexdigest()


def event_defects(event: dict) -> list:
    """A limit reached and not marked, or a candidate that left a count: each is a failed observation dropped (t04-prereg.md)."""
    defects = []
    found = event["found"]
    if len(found) != event["candidates"]:
        defects.append(f"event {event['ordinal']} counts {event['candidates']} candidates and holds {len(found)}")
    if sum(item["outcome"] == "selected" for item in found) != event["selected"]:
        defects.append(f"event {event['ordinal']} counts {event['selected']} selected")
    if event["seeds_run"] + event["seeds_skipped"] != event["seeds_found"]:
        defects.append(f"event {event['ordinal']} loses seeds between found and run")
    settled = event["seeds_failed"] + event["seeds_without_candidate"]
    if settled > event["seeds_run"] or event["seeds_run"] - settled > event["candidates"] + event["seeds_truncated"]:
        defects.append(f"event {event['ordinal']} runs {event['seeds_run']} seeds and accounts for {settled} failed or empty, with {event['candidates']} candidates")
    truncated = event["seeds_truncated"] > 0 or event["seed_budget_reached"] or event["ambiguity_budget_reached"]
    if event["selected"] == 0 and event["failure_category"] != ("search-truncated" if truncated else "seed-or-finding"):
        defects.append(f"event {event['ordinal']} has no track and says {event['failure_category']}")
    if event["selected"] > 0 and event["failure_category"] != "none":
        defects.append(f"event {event['ordinal']} has tracks and says {event['failure_category']}")
    if any(item["search_truncated"] for item in found) and not truncated:
        defects.append(f"event {event['ordinal']} marks a candidate and no limit")
    if (event["seed_budget_reached"] or event["ambiguity_budget_reached"]) and not all(item["search_truncated"] for item in found):
        defects.append(f"event {event['ordinal']} reached an event budget and leaves a candidate unmarked")
    return defects


def parse_record(text: str, configuration_keys=CONFIGURATION_KEYS, marks_event_budgets: bool = True) -> dict:
    """A whole record, or RecordFormatError. The end record's counts catch a truncated file. An earlier job's record, read for comparison, names its own keys, and did not yet mark
    candidates for an event's budgets."""
    lines = text.split("\n")
    if lines[-1] != "":
        raise RecordFormatError("the last line is not finished")
    lines = lines[:-1]
    if not lines or lines[0] not in (RECORD_FORMAT, VERTEX_RECORD_FORMAT):
        raise RecordFormatError(f"not {RECORD_FORMAT} or {VERTEX_RECORD_FORMAT}")
    with_vertices = lines[0] == VERTEX_RECORD_FORMAT
    header, configuration, vertex_configuration, events, counted = {}, {}, {}, [], None
    try:
        for name, line in zip(HEADER_FIELDS, lines[1:]):
            tokens = line.split(" ")
            if tokens[0] != name or len(tokens) != 2:
                raise RecordFormatError(f"expected the record {name}, found {line}")
            header[name] = tokens[1]
        if len(header) != len(HEADER_FIELDS):
            raise RecordFormatError("the record ends inside its header")
        header["product_events"] = int(header["product_events"])
        vertex_key_of_line = {}
        for line in lines[1 + len(HEADER_FIELDS):]:
            if counted is not None:
                raise RecordFormatError("text after the end record")
            tokens = line.split(" ")
            vertexing = events[-1].get("vertexing") if events else None
            if tokens[0] == "configuration" and len(tokens) == 3 and not events and not vertex_configuration and "vertex_recipe" not in header:
                configuration[tokens[1]] = tokens[2]
            elif with_vertices and tokens[0] in VERTEX_HEADER_FIELDS and len(tokens) == 2 and not events and tokens[0] not in header:
                if tokens[0] == "vertex_configuration_sha256" and "vertex_recipe" not in header:
                    raise RecordFormatError("the vertex configuration hash comes after the vertex recipe")
                header[tokens[0]] = tokens[1]
            elif with_vertices and tokens[0] == "vertex_configuration" and len(tokens) == 3 and not events and "vertex_configuration_sha256" in header:
                vertex_configuration[tokens[1]] = tokens[2]
            elif tokens[0] == "event":
                if with_vertices and events and "vertexing" not in events[-1]:
                    raise RecordFormatError(f"event {events[-1]['ordinal']} has no vertexing line")
                events.append(_event(tokens))
            elif tokens[0] == "candidate":
                candidate = _candidate(tokens)
                if not events or events[-1]["ordinal"] != candidate["ordinal"] or vertexing is not None:
                    raise RecordFormatError(f"{candidate['key']} is not under its event, before its vertexing line")
                events[-1]["found"].append(candidate)
            elif with_vertices and tokens[0] == "vertexing":
                found = _vertexing(tokens)
                if not events or events[-1]["ordinal"] != found["ordinal"] or vertexing is not None:
                    raise RecordFormatError(f"a vertexing line of event {found['ordinal']} is not its event's one, after its candidates")
                events[-1]["vertexing"] = found
            elif with_vertices and tokens[0] == "vertex":
                vertex = _vertex(tokens)
                if vertexing is None or events[-1]["ordinal"] != vertex["ordinal"] or vertex["key"] in vertex_key_of_line:
                    raise RecordFormatError(f"{vertex['key']} is not under its event's vertexing line, or appears twice")
                vertexing["vertices"].append(vertex)
                vertex_key_of_line[vertex["key"]] = vertex
            elif with_vertices and tokens[0] == "vertex-track":
                track = _vertex_track(tokens)
                if vertexing is None or not vertexing["vertices"] or vertexing["vertices"][-1]["key"] != track["vertex_key"]:
                    raise RecordFormatError(f"a track of {track['vertex_key']} is not under its vertex")
                vertexing["vertices"][-1]["tracks"].append({name: track[name] for name in ("track_key", "weight", "chi2", "compatibility")})
            elif tokens[0] == "end" and len(tokens) == (4 if with_vertices else 3):
                if with_vertices and events and "vertexing" not in events[-1]:
                    raise RecordFormatError(f"event {events[-1]['ordinal']} has no vertexing line")
                counted = [int(token) for token in tokens[1:]]
            else:
                raise RecordFormatError(f"unknown record {tokens[0]}")
    except (IndexError, ValueError) as error:
        if isinstance(error, RecordFormatError):
            raise
        raise RecordFormatError(str(error)) from error
    if counted is None:
        raise RecordFormatError("the record ends before its end record")
    expected_counts = [len(events), sum(len(event["found"]) for event in events)]
    if with_vertices:
        expected_counts.append(sum(len(event["vertexing"]["vertices"]) for event in events))
    if counted != expected_counts:
        raise RecordFormatError("the end record counts other numbers than the record holds")
    if set(configuration) != set(configuration_keys):
        raise RecordFormatError(f"the effective configuration differs: {sorted(set(configuration) ^ set(configuration_keys))}")
    if with_vertices:
        if header.get("vertex_recipe") != VERTEX_RECIPE or "vertex_configuration_sha256" not in header:
            raise RecordFormatError(f"a /2 record names the vertex recipe {VERTEX_RECIPE} and the hash of its configuration")
        if list(vertex_configuration) != list(VERTEX_CONFIGURATION_KEYS):
            raise RecordFormatError(f"the vertex configuration differs: {sorted(set(vertex_configuration) ^ set(VERTEX_CONFIGURATION_KEYS))}")
        if vertex_configuration_sha256(vertex_configuration) != header["vertex_configuration_sha256"]:
            raise RecordFormatError("the vertex configuration hash is not that of the configuration it heads")
    if (header["recipe"], header["stage"], header["evidence_class"]) != (FINDING_RECIPE, FINDING_STAGE, FINDING_EVIDENCE_CLASS):
        raise RecordFormatError("this record format is finding's alone: a refit or a truth-seeded run is not finding")
    for event in events:
        defects = [defect for defect in event_defects(event) if marks_event_budgets or "budget" not in defect]
        if with_vertices:
            defects += vertexing_defects(event)
        if defects:
            raise RecordFormatError(defects[0])
    document = {"header": header, "configuration": configuration, "events": events}
    if with_vertices:
        document["vertex_configuration"] = vertex_configuration
    return document


def iter_seed_events(path):
    """Each event's seeds, one event at a time, as a list of {planes, hit_keys, outcome, first_candidate, candidates, short_branches}. An o3 file holds over a million."""
    with open(path, encoding="utf-8") as stream:
        if stream.readline().rstrip("\n") != SEED_FILE_FORMAT:
            raise RecordFormatError(f"not {SEED_FILE_FORMAT}")
        events = 0
        for line in stream:
            tokens = line.split()
            if not tokens or tokens[0] not in ("event", "end") or len(tokens) != (3 if tokens[0] == "event" else 2):
                raise RecordFormatError(f"expected an event, found {line.strip()}")
            if tokens[0] == "end":
                if int(tokens[1]) != events:
                    raise RecordFormatError(f"the seed file ends at {tokens[1]} events and holds {events}")
                return
            if int(tokens[1]) != events:
                raise RecordFormatError(f"event {tokens[1]} out of order")
            seeds = [_seed(next(stream).split()) for _ in range(int(tokens[2]))]
            events += 1
            yield seeds
    raise RecordFormatError("the seed file ends before its end record")


def _seed(tokens) -> dict:
    if len(tokens) != 7 or tokens[0] != "seed" or tokens[3] not in SEED_OUTCOMES:
        raise RecordFormatError(f"not a seed: {tokens}")
    return {"planes": tokens[1], "hit_keys": [int(key) for key in tokens[2].split(",")], "outcome": tokens[3], "first_candidate": int(tokens[4]), "candidates": int(tokens[5]),
            "short_branches": int(tokens[6])}


def format_record(document: dict) -> str:
    """The exact bytes the finder writes for this document: /2 when its header names the vertex recipe, /1 otherwise."""
    header = document["header"]
    with_vertices = "vertex_recipe" in header
    lines = [VERTEX_RECORD_FORMAT if with_vertices else RECORD_FORMAT] + [f"{name} {header[name]}" for name in HEADER_FIELDS]
    lines += [f"configuration {name} {document['configuration'][name]}" for name in CONFIGURATION_KEYS]
    if with_vertices:
        lines += [f"{name} {header[name]}" for name in VERTEX_HEADER_FIELDS]
        lines += [f"vertex_configuration {name} {document['vertex_configuration'][name]}" for name in VERTEX_CONFIGURATION_KEYS]
    for event in document["events"]:
        lines.append(" ".join(["event", str(event["ordinal"])] + [str(event[name]) for name in EVENT_COUNTERS] + [event["failure_category"]]))
        for item in event["found"]:
            numbers = ["%.17g" % item[name] for name in ("search_chi2", "q_over_p", "fit_chi2")]
            lines.append(" ".join(["candidate", item["key"], str(item["ordinal"]), item["seed_planes"], item["outcome"], item["failure_category"], "1" if item["search_truncated"] else "0",
                                   str(item["measurements"]), str(item["holes"]), *numbers, str(item["fit_coordinates"]), ",".join(str(key) for key in item["hit_keys"])]))
        if with_vertices:
            vertexing = event["vertexing"]
            lines.append(" ".join(["vertexing", str(event["ordinal"]), vertexing["status"], str(vertexing["input_tracks"]), str(vertexing["unconverted_tracks"]), str(len(vertexing["vertices"]))]))
            for vertex in vertexing["vertices"]:
                numbers = ["%.17g" % value for value in vertex["position_mm"] + vertex["covariance"] + [vertex["chi2"], vertex["ndf"]]]
                lines.append(" ".join(["vertex", vertex["key"], str(vertex["ordinal"]), *numbers, str(len(vertex["tracks"]))]))
                lines += [" ".join(["vertex-track", vertex["key"], track["track_key"], *("%.17g" % track[name] for name in ("weight", "chi2", "compatibility"))]) for track in vertex["tracks"]]
    end = f"end {len(document['events'])} {sum(len(event['found']) for event in document['events'])}"
    if with_vertices:
        end += f" {sum(len(event['vertexing']['vertices']) for event in document['events'])}"
    lines.append(end)
    return "\n".join(lines) + "\n"
