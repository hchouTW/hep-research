"""acts-tracking-finding-record/1: what acts_tracking_finder did with every event and candidate, read back. Data side: no truth here.

The record holds the search, candidates and selected branches and failure categories (t07-t09-task-sheets.md, Output; BP03), beside the product, which
holds the selected tracks' states. The reader stops at anything it does not know, and at a record that hides a limit: a candidate of a truncated
seed is marked search-truncated (BP03; section 8.4), and a failed candidate states its category (t04-prereg.md, Failure classes). Sections cited are
of t04-values-v4.md. Standard library only.
"""
from __future__ import annotations

import math

RECORD_FORMAT = "acts-tracking-finding-record/1"
HEADER_FIELDS = ("recipe", "stage", "evidence_class", "product_id", "data_sha256", "product_events", "configuration_sha256")
FINDING_RECIPE, FINDING_STAGE, FINDING_EVIDENCE_CLASS = "reco.track.acts-ckf-planar/1", "find-ckf", "data-side"
EVENT_COUNTERS = ("hit_count", "seeds_found", "seeds_run", "seeds_skipped", "seeds_failed", "seeds_without_candidate", "seeds_truncated", "seed_budget_reached",
                  "ambiguity_budget_reached", "candidates", "selected")
CANDIDATE_CATEGORY_OF_OUTCOME = {"selected": "none", "evicted": "ambiguity", "fit-failed": "fit"}
EVENT_CATEGORIES = ("none", "seed-or-finding", "search-truncated")
CONFIGURATION_KEYS = ("seed_plane_triples", "seed_lowest_momentum_gev", "seed_largest_slope_u", "seed_largest_slope_v", "seed_window_sigma", "seed_prior_inflation", "finding_chi2_cut",
                      "finding_least_measurements", "finding_most_holes", "finding_most_branches_per_surface", "finding_most_branches_per_seed", "finding_most_seeds_per_event",
                      "finding_most_propagator_steps", "ambiguity_most_shared_hits", "ambiguity_most_iterations")


class RecordFormatError(ValueError):
    """The text is not acts-tracking-finding-record/1, or it hides what a limit did."""


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
    truncated = event["seeds_truncated"] > 0 or event["seed_budget_reached"] or event["ambiguity_budget_reached"]
    if event["selected"] == 0 and event["failure_category"] != ("search-truncated" if truncated else "seed-or-finding"):
        defects.append(f"event {event['ordinal']} has no track and says {event['failure_category']}")
    if event["selected"] > 0 and event["failure_category"] != "none":
        defects.append(f"event {event['ordinal']} has tracks and says {event['failure_category']}")
    if any(item["search_truncated"] for item in found) and event["seeds_truncated"] == 0:
        defects.append(f"event {event['ordinal']} marks a candidate and no seed")
    return defects


def parse_record(text: str) -> dict:
    """A whole record, or RecordFormatError. The end record's counts catch a truncated file."""
    lines = text.split("\n")
    if lines[-1] != "":
        raise RecordFormatError("the last line is not finished")
    lines = lines[:-1]
    if not lines or lines[0] != RECORD_FORMAT:
        raise RecordFormatError(f"not {RECORD_FORMAT}")
    header, configuration, events, counted = {}, {}, [], None
    try:
        for name, line in zip(HEADER_FIELDS, lines[1:]):
            tokens = line.split(" ")
            if tokens[0] != name or len(tokens) != 2:
                raise RecordFormatError(f"expected the record {name}, found {line}")
            header[name] = tokens[1]
        if len(header) != len(HEADER_FIELDS):
            raise RecordFormatError("the record ends inside its header")
        header["product_events"] = int(header["product_events"])
        for line in lines[1 + len(HEADER_FIELDS):]:
            if counted is not None:
                raise RecordFormatError("text after the end record")
            tokens = line.split(" ")
            if tokens[0] == "configuration" and len(tokens) == 3 and not events:
                configuration[tokens[1]] = tokens[2]
            elif tokens[0] == "event":
                events.append(_event(tokens))
            elif tokens[0] == "candidate":
                candidate = _candidate(tokens)
                if not events or events[-1]["ordinal"] != candidate["ordinal"]:
                    raise RecordFormatError(f"{candidate['key']} is not under its event")
                events[-1]["found"].append(candidate)
            elif tokens[0] == "end" and len(tokens) == 3:
                counted = [int(token) for token in tokens[1:]]
            else:
                raise RecordFormatError(f"unknown record {tokens[0]}")
    except (IndexError, ValueError) as error:
        if isinstance(error, RecordFormatError):
            raise
        raise RecordFormatError(str(error)) from error
    if counted is None:
        raise RecordFormatError("the record ends before its end record")
    if counted != [len(events), sum(len(event["found"]) for event in events)]:
        raise RecordFormatError("the end record counts other numbers than the record holds")
    if set(configuration) != set(CONFIGURATION_KEYS):
        raise RecordFormatError(f"the effective configuration differs: {sorted(set(configuration) ^ set(CONFIGURATION_KEYS))}")
    if (header["recipe"], header["stage"], header["evidence_class"]) != (FINDING_RECIPE, FINDING_STAGE, FINDING_EVIDENCE_CLASS):
        raise RecordFormatError("this record format is finding's alone: a refit or a truth-seeded run is not finding")
    for event in events:
        defects = event_defects(event)
        if defects:
            raise RecordFormatError(defects[0])
    return {"header": header, "configuration": configuration, "events": events}


def format_record(document: dict) -> str:
    """The exact bytes the finder writes for this document."""
    header = document["header"]
    lines = [RECORD_FORMAT] + [f"{name} {header[name]}" for name in HEADER_FIELDS]
    lines += [f"configuration {name} {document['configuration'][name]}" for name in CONFIGURATION_KEYS]
    for event in document["events"]:
        lines.append(" ".join(["event", str(event["ordinal"])] + [str(event[name]) for name in EVENT_COUNTERS] + [event["failure_category"]]))
        for item in event["found"]:
            numbers = ["%.17g" % item[name] for name in ("search_chi2", "q_over_p", "fit_chi2")]
            lines.append(" ".join(["candidate", item["key"], str(item["ordinal"]), item["seed_planes"], item["outcome"], item["failure_category"], "1" if item["search_truncated"] else "0",
                                   str(item["measurements"]), str(item["holes"]), *numbers, str(item["fit_coordinates"]), ",".join(str(key) for key in item["hit_keys"])]))
    lines.append(f"end {len(document['events'])} {sum(len(event['found']) for event in document['events'])}")
    return "\n".join(lines) + "\n"
