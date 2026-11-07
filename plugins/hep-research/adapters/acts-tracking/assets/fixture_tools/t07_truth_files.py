"""The truth side of the T07 fixture files, as numpy layouts: the mirror of native/t07_truth_file.*. Scoring and generator checks only:
data-side code may not import this module (tests/adapters/test_acts_tracking.py; t07-t09-task-sheets.md, Input).

A truth file has role truth and the suffix .t07truth. Its records run in the data file's order, so position pairs the two. It holds
the seed integers, digests and event indices, and it names its data file by SHA-256. Little-endian and packed.
"""
from __future__ import annotations

import numpy

from t07_fixture_files import assert_finished, check_identity, take_records

TRUTH_MAGIC = b"T07TRUT1"
TRUTH_ROLE = "truth"
NO_HIT_KEY = 0xFFFFFFFF
PLANES = 8

TRUTH_HEADER = numpy.dtype([("magic", "S8"), ("role", "S24"), ("generator", "S32"), ("fixture_id", "<u4"), ("block", "<u4"), ("stratum", "<u4"),
                            ("event_count", "<u4"), ("sigma_loc0_mm", "<f8"), ("sigma_loc1_mm", "<f8"), ("data_sha256", "V32")])
TRUTH_EVENT = numpy.dtype([("event_digest", "V32"), ("event_index", "<u8"), ("momentum_bin", "<u4"), ("occupancy_level", "<u4"),
                           ("near_separation", "<u4"), ("vertex_count", "<u4"), ("track_count", "<u4"),
                           ("noise_counts", "<u4", (PLANES,)), ("reserved", "<u4")])
VERTEX = numpy.dtype([("u_mm", "<f8"), ("v_mm", "<f8"), ("z_mm", "<f8")])
TRACK = numpy.dtype([("particle_key", "<u4"), ("vertex_index", "<u4"), ("charge", "<i4"), ("reserved", "<u4"), ("momentum_gev", "<f8"),
                     ("slope_u", "<f8"), ("slope_v", "<f8"), ("q_over_p", "<f8"), ("hit_keys", "<u4", (PLANES,)),
                     ("crossings", "<f8", (PLANES, 4))])  # per plane: loc0, loc1, phi, theta


def truth_header_of(stream, path) -> dict:
    fields = take_records(stream, TRUTH_HEADER, 1, path)[0]
    check_identity(fields, TRUTH_MAGIC, TRUTH_ROLE, path)
    return {"role": TRUTH_ROLE, "generator": bytes(fields["generator"]).decode(), "fixture_id": int(fields["fixture_id"]), "block": int(fields["block"]),
            "stratum": int(fields["stratum"]), "event_count": int(fields["event_count"]), "sigma_loc0_mm": float(fields["sigma_loc0_mm"]),
            "sigma_loc1_mm": float(fields["sigma_loc1_mm"]), "data_sha256": bytes(fields["data_sha256"]).hex()}


def read_truth_header(path) -> dict:
    with open(path, "rb") as stream:
        return truth_header_of(stream, path)


def iter_truth_events(path):
    with open(path, "rb") as stream:
        header = truth_header_of(stream, path)
        for _ in range(header["event_count"]):
            head = take_records(stream, TRUTH_EVENT, 1, path)[0]
            event = {name: head[name] for name in ("event_index", "momentum_bin", "occupancy_level", "near_separation", "noise_counts")}
            event["event_digest"] = bytes(head["event_digest"])
            event["vertices"] = take_records(stream, VERTEX, int(head["vertex_count"]), path)
            event["tracks"] = take_records(stream, TRACK, int(head["track_count"]), path)
            yield event
        assert_finished(stream, path)
