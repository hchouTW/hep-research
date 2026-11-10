"""adapters/acts-tracking, T07's scenarios A05 and A17 (t07-t09-task-sheets.md, Acceptance; plan section 13), as the T07 close-out reads them (D1 stage 11,
docs/dev/detector-reconstruction/t07-closeout.md). A07 and A39 rest on tests in the other modules, named there; A01 stays open by the sheet.

A05, interleaved contexts, event slots, threads: no context or state contamination. For this driver: the finder and the refit are single-threaded and run one
context per process (the field, the geometry and an optional alignment payload are fixed for the whole invocation; no IOV changes inside a run), and the finder
keeps one TrackFinder and one TrackVertexer over all events. So what can carry from one event to the next is state inside a process. Shown here:
- the finder with its vertex step, on a file that interleaves the clean fixture at o1 (stratum 0) in reverse order with the noise fixture at o3 (stratum 11) in
  a fixed permuted order, writes for every event the lines it writes when it reads that event's own file in file order: event, candidates, vertexing, vertices
  and vertex tracks, byte for byte, with the event ordinal taken out of the keys. The end totals are the sum of the two runs: nothing dropped or counted twice;
- the refit of a fixed hit-set list and of the same list reversed gives every track the same records, R33's among them.
A payload context interleaved with the nominal one inside one process cannot happen by construction (one --alignment-payload per invocation), so it is not tested
here; that two such runs stay apart is A17.

A17, results bound to their hypothesis: a refit under an alignment payload, and one under another field, carry their identity and never overwrite each other. The
product's header line alignment_payload already records the payload (stage 9) and merge refuses two products of different payloads (stage 9). Found in this stage:
the reconstruction-product/1 sidecars of a refit that applied a payload said conditions_used [], "none consumed" (contracts/schemas/reconstruction_product.json),
so the binding was lost at the contract level. sidecars_for_product now takes the payload's R32 sidecar and records it, and refuses a product with a payload line
and no sidecar, a sidecar of another payload or origin, and a sidecar for a product that applied none (HypothesisBinding, failing first before the change).

Predictions, fixed before the stage 11 job: A05 byte-equal on every event of both files and on the reversed refit (refuted by any differing line: that would be
state carried across events, a finding, not a tolerance); A17 needs no build. Each judge is driven with honest input and one defect, without a build. The built
class needs the build job and skips without it; that job counts a skip as a failure. Run from the plugin root: python -m unittest tests.adapters.test_acts_scenarios -v
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.adapters import test_acts_finding as finding_tests
from tests.adapters import test_acts_track_outputs as outputs_tests

native_product, fixture_files, truth_files, finding_record = finding_tests.native_product, finding_tests.fixture_files, finding_tests.truth_files, finding_tests.finding_record
sys.path.insert(0, str(outputs_tests.ADAPTER / "assets" / "fixture_tools"))
import t07_alignment_payload as alignment_payload  # noqa: E402

from contracts.conditions import check_used  # noqa: E402
from contracts.reconstruction import read_sidecar  # noqa: E402

BUILD_DIR = os.environ.get("HEP_ACTS_TRACKING_BUILD", "")
DRIVER = Path(BUILD_DIR) / "acts_tracking_driver"
BUILT = finding_tests.BUILT and DRIVER.is_file()
NOT_BUILT = "HEP_ACTS_TRACKING_BUILD names no built finder or driver: this test needs the T07 build job, which runs it"

# A05, fixed before the run.
ORDER_EVENTS = 200           # events of each file: clean stratum 0 (o1) and noise stratum 11 (o3), block 1
ORDER_CLEAN_STRATUM, ORDER_NOISE_STRATUM = 0, 11
ORDER_STEP = 7               # the noise file is read in the order (7 i) mod 200, a permutation since 7 and 200 share no factor; no random draw
ORDINAL_FIELD = {"event": 1, "candidate": 2, "vertexing": 1, "vertex": 2}  # the token that is the event ordinal (acts_finding_record.py)
EVENT_LINES = ("event", "candidate", "vertexing", "vertex", "vertex-track")
SLOT = native_product.ALIGNMENT_SLOT


# ---- A05: the judges. Each takes record text and names what is wrong, so each is tested without a build.

def event_blocks(text: str) -> list:
    """The lines of each event of a finding record, /1 or /2, in file order, with the event ordinal taken out: as the event's own data file would give them."""
    blocks = []
    for line in text.split("\n"):
        tokens = line.split(" ")
        if tokens[0] not in EVENT_LINES:
            continue
        if tokens[0] == "event":
            blocks.append([])
        if not blocks:
            raise ValueError(f"a {tokens[0]} line before any event")
        ordinal = len(blocks) - 1
        if tokens[0] in ORDINAL_FIELD:
            if tokens[ORDINAL_FIELD[tokens[0]]] != str(ordinal):
                raise ValueError(f"a {tokens[0]} line of event {tokens[ORDINAL_FIELD[tokens[0]]]} under event {ordinal}")
            tokens[ORDINAL_FIELD[tokens[0]]] = "*"
        prefix = f"event-{ordinal}-"
        blocks[-1].append(" ".join("event-*-" + token[len(prefix):] if token.startswith(prefix) else token for token in tokens))
    return blocks


def end_totals(text: str) -> list:
    ends = [line for line in text.split("\n") if line.startswith("end ")]
    if len(ends) != 1:
        raise ValueError("a record holds one end line")
    return [int(token) for token in ends[0].split(" ")[1:]]


def configuration_lines(text: str) -> list:
    return [line for line in text.split("\n") if line.split(" ")[0] in ("configuration", "configuration_sha256", "vertex_configuration", "vertex_configuration_sha256", "vertex_recipe")]


def order_defects(sources: dict, mixed: str, mapping: list) -> list:
    """sources: {name: record text of that file read alone}; mixed: the record of the interleaved file; mapping: (name, ordinal in that file) per mixed event."""
    defects = []
    blocks = {name: event_blocks(text) for name, text in sources.items()}
    mixed_blocks = event_blocks(mixed)
    if len(mixed_blocks) != len(mapping):
        defects.append(f"the interleaved record holds {len(mixed_blocks)} events, the file {len(mapping)}")
    if sorted(mapping) != sorted((name, ordinal) for name, items in blocks.items() for ordinal in range(len(items))):
        defects.append("the mapping does not take every event of every file once")
    for position, (block, (name, ordinal)) in enumerate(zip(mixed_blocks, mapping)):
        own = blocks.get(name, [])
        if ordinal >= len(own) or block != own[ordinal]:
            first = next((index for index, (a, b) in enumerate(zip(block, own[ordinal] if ordinal < len(own) else [])) if a != b), min(len(block), len(own[ordinal]) if ordinal < len(own) else 0))
            defects.append(f"interleaved event {position} ({name} event {ordinal}) differs from its own run at line {first}")
    totals = [sum(values) for values in zip(*(end_totals(text) for text in sources.values()))]
    if end_totals(mixed) != totals:
        defects.append(f"end totals {end_totals(mixed)}, the runs alone {totals}")
    if any(configuration_lines(text) != configuration_lines(mixed) for text in sources.values()):
        defects.append("the runs differ in configuration")
    return defects


def track_records(document: dict) -> dict:
    """Every record of each track of a product, by track key, without the product's identity: what a track's fit wrote."""
    records = {track["key"]: {"track": track} for track in document["tracks"]}
    for name in ("states", "parameters") + (native_product.R33_COLLECTIONS if document.get("format") == native_product.PRODUCT_FORMAT_R33 else ()):
        for item in document[name]:
            records[item["track_key"]].setdefault(name, []).append(item)
    return records


def per_track_defects(first: dict, second: dict) -> list:
    a, b = track_records(first), track_records(second)
    defects = [f"track {key} is in one product only" for key in sorted(set(a) ^ set(b))]
    defects += [f"track {key} differs" for key in sorted(set(a) & set(b)) if a[key] != b[key]]
    return defects


def sample_record(events: list, vertex: bool = True) -> str:
    """A record's event lines in the finder's layout: [(candidate count, number)] per event; enough for the judges, which read the layout only.
    Not a readable record: the candidate lines hold 15 tokens, not the finder's 14, and the event counters are placeholders. The judges read the
    line kind, the ordinal positions of ORDINAL_FIELD and the keys, and compare every line whole (review nit 12)."""
    lines = ["acts-tracking-finding-record/2", "configuration_sha256 " + "c" * 64, "configuration seed_window_sigma 3"]
    for ordinal, (count, number) in enumerate(events):
        lines.append(f"event {ordinal} 40 3 3 0 0 0 0 0 0 {count} {count} none")
        for index in range(count):
            lines.append(f"candidate event-{ordinal}-candidate-{index} {ordinal} 1,2,3 selected none 0 8 0 {number + index} 0.5 1.0 16 0,1,2,3,4,5,6,7")
        if vertex:
            lines.append(f"vertexing {ordinal} ok {count} 0 1")
            lines.append(f"vertex event-{ordinal}-vertex-0 {ordinal} 0 0 {number} 1 0 0 1 0 1 2.0 3.0 {count}")
            lines += [f"vertex-track event-{ordinal}-vertex-0 event-{ordinal}-candidate-{index} 1 0.1 0.2" for index in range(count)]
    vertices = len(events) if vertex else 0
    lines.append(f"end {len(events)} {sum(count for count, _ in events)}" + (f" {vertices}" if vertex else ""))
    return "\n".join(lines) + "\n"


class EventOrderJudge(unittest.TestCase):
    """A05's judge on hand-made records: honest interleaving passes, and each kind of contamination, loss or double count is named."""

    def setUp(self):
        self.clean = [(2, 1.25), (1, 2.5), (3, 0.75)]
        self.noise = [(4, 9.5), (2, 8.25)]
        self.sources = {"clean": sample_record(self.clean), "noise": sample_record(self.noise)}
        self.mapping = [("clean", 2), ("noise", 1), ("clean", 1), ("noise", 0), ("clean", 0)]
        self.mixed = sample_record([dict(clean=self.clean, noise=self.noise)[name][ordinal] for name, ordinal in self.mapping])

    def test_honest_interleaving_passes(self):
        self.assertEqual(order_defects(self.sources, self.mixed, self.mapping), [])

    def test_the_ordinal_is_taken_out_of_every_key_and_nowhere_else(self):
        block = event_blocks(self.sources["clean"])[1]
        self.assertTrue(all("event-1-" not in line for line in block))
        self.assertIn("candidate event-*-candidate-0 * 1,2,3 selected none 0 8 0 2.5 0.5 1.0 16 0,1,2,3,4,5,6,7", block)

    def test_a_number_carried_from_another_event_is_named(self):
        contaminated = self.mixed.replace(" 0 8 0 2.5 ", " 0 8 0 2.5000000000000004 ", 1)
        self.assertNotEqual(contaminated, self.mixed)
        self.assertEqual(order_defects(self.sources, contaminated, self.mapping), ["interleaved event 2 (clean event 1) differs from its own run at line 1"])

    def test_a_vertex_moved_is_named(self):
        moved = self.mixed.replace("vertex event-3-vertex-0 3 0 0 9.5 ", "vertex event-3-vertex-0 3 0 0 9.25 ", 1)
        self.assertNotEqual(moved, self.mixed)
        self.assertEqual(order_defects(self.sources, moved, self.mapping), ["interleaved event 3 (noise event 0) differs from its own run at line 6"])

    def test_an_event_dropped_or_taken_twice_is_named(self):
        dropped = sample_record([dict(clean=self.clean, noise=self.noise)[name][ordinal] for name, ordinal in self.mapping[:-1]])
        defects = order_defects(self.sources, dropped, self.mapping[:-1])
        self.assertIn("the mapping does not take every event of every file once", defects)
        self.assertTrue(any(defect.startswith("end totals") for defect in defects))
        twice = self.mapping[:-1] + [("clean", 1)]
        self.assertIn("the mapping does not take every event of every file once", order_defects(self.sources, self.mixed, twice))

    def test_a_candidate_counted_twice_is_named(self):
        lines = self.mixed.split("\n")
        at = next(index for index, line in enumerate(lines) if line.startswith("candidate event-0-candidate-0 "))
        doubled = "\n".join(lines[:at + 1] + [lines[at]] + lines[at + 1:])
        self.assertTrue(order_defects(self.sources, doubled, self.mapping))

    def test_a_line_under_the_wrong_event_is_refused(self):
        with self.assertRaises(ValueError):
            event_blocks(self.mixed.replace("vertexing 1 ok", "vertexing 2 ok", 1))

    def test_another_configuration_is_named(self):
        other = self.mixed.replace("configuration seed_window_sigma 3", "configuration seed_window_sigma 4", 1)
        self.assertEqual(order_defects(self.sources, other, self.mapping), ["the runs differ in configuration"])


class PerTrackJudge(unittest.TestCase):
    def test_a_reordered_product_has_the_same_tracks_and_a_changed_number_is_named(self):
        document = outputs_tests.sample_r33_document()
        reordered = native_product.reorder_tracks(document, ["1", "0"])
        self.assertEqual(per_track_defects(document, reordered), [])
        changed = native_product.parse_product(native_product.format_product(reordered).replace(" 0.69999999999999996", " 0.70000000000000007", 1))
        self.assertEqual(per_track_defects(document, changed), ["track 0 differs"])
        self.assertEqual(per_track_defects(document, native_product.subset_tracks(document, ["0"], "refit.part")), ["track 1 is in one product only"])


# ---- A17: a refit's result stays bound to the payload and the field it was fitted under.

def payload_case(shift_mm: float, tag: str) -> tuple:
    """A measured payload moving plane 4 along loc0, its R32 sidecar, and the product header line a refit that applied it writes."""
    text = alignment_payload.encode_payload({4: [shift_mm, 0.0, 0.0, 0.0, 0.0, 0.0]}, alignment_payload.nominal_geometry_id())
    parsed = alignment_payload.parse_payload(text)
    sidecar = alignment_payload.payload_sidecar(text, tag, "synthetic A17 case: a generated shift, no measurement")
    line = {"content_sha256": parsed["content_id"], "origin": parsed["origin"], "derived_against": parsed["derived_against"], "derived_from": parsed["derived_from"], "round": "none"}
    return text, sidecar, line


def refit_under(line: dict | None, product_id: str = "refit.r33", field_tesla: float = 1.0) -> dict:
    document = outputs_tests.sample_r33_document()
    header = dict(document["header"], product_id=product_id, field_tesla=field_tesla, qop_status="measured" if field_tesla else "assumed-not-measured")
    if line is not None:
        header["alignment_payload"] = line
    return dict(document, header=header)


class HypothesisBinding(unittest.TestCase):
    """A17 on the refit's products and their reconstruction-product/1 sidecars. No build."""

    def setUp(self):
        self.text, self.sidecar, self.line = payload_case(0.0625, "a17-plane-4-plus")
        self.other_text, self.other_sidecar, self.other_line = payload_case(-0.0625, "a17-plane-4-minus")

    def test_a_refit_under_a_payload_names_it_in_every_sidecar(self):
        document = refit_under(self.line)
        sidecars = native_product.sidecars_for_product(document, "refit.product", payload_sidecar=self.sidecar)
        expected = [{"slot": SLOT, "tag": "a17-plane-4-plus", "payload_id": self.sidecar["payload_id"], "origin": "measured", "round": None}]
        for sidecar in sidecars:
            with self.subTest(collection=sidecar["collection"]):
                self.assertEqual(sidecar["conditions_used"], expected)
                report = read_sidecar(sidecar)
                self.assertTrue(report.ok, [finding.as_dict() for finding in report.errors])
                self.assertTrue(check_used(sidecar, [self.sidecar]).ok)
                self.assertFalse(check_used(sidecar, [self.other_sidecar]).ok)  # another hypothesis is not this result's

    def test_a_product_that_applied_a_payload_is_never_mapped_as_if_it_applied_none(self):
        with self.assertRaises(native_product.ProductFormatError):
            native_product.sidecars_for_product(refit_under(self.line), "refit.product")

    def test_a_sidecar_of_another_payload_origin_or_geometry_is_refused(self):
        document = refit_under(self.line)
        wrong = {"another payload": self.other_sidecar,
                 "another origin": dict(self.sidecar, origin="nominal"),
                 "another geometry": dict(self.sidecar, derived_against={"geometry_id": "f" * 64})}
        for name, sidecar in wrong.items():
            with self.subTest(case=name), self.assertRaises(native_product.ProductFormatError):
                native_product.sidecars_for_product(document, "refit.product", payload_sidecar=sidecar)
        with self.subTest(case="a derived payload's sidecar for its parent"), self.assertRaises(native_product.ProductFormatError):
            child_text = alignment_payload.derive_subset(self.text, {4: ["shift-loc0"]})
            child_sidecar = alignment_payload.payload_sidecar(child_text, "a17-child", "synthetic A17 case", self.sidecar)
            native_product.sidecars_for_product(document, "refit.product", payload_sidecar=dict(child_sidecar, content_sha256=self.line["content_sha256"]))

    def test_a_sidecar_of_another_round_or_with_a_stored_identity_that_is_not_its_own_is_refused(self):
        """Review minor 7 (D1 stage 11 fix round 1): the round is compared with the sidecar's loop, and the payload_id is recomputed, not read."""
        with self.subTest(case="the product names round 2, the payload comes from no loop"), self.assertRaises(native_product.ProductFormatError):
            native_product.sidecars_for_product(refit_under(dict(self.line, round="2")), "refit.product", payload_sidecar=self.sidecar)
        with self.subTest(case="the product names no round, the sidecar a loop's round 1"), self.assertRaises(native_product.ProductFormatError):
            native_product.sidecars_for_product(refit_under(self.line), "refit.product", payload_sidecar=dict(self.sidecar, loop={"family": "a17", "round": 1}))
        with self.subTest(case="a stored payload_id that is not the content's"), self.assertRaises(native_product.ProductFormatError):
            native_product.sidecars_for_product(refit_under(self.line), "refit.product", payload_sidecar=dict(self.sidecar, payload_id="0" * 64))
        with self.subTest(case="a tag changed: the identity does not hold the tag, so the mapping stands and names the new tag"):
            retagged = dict(self.sidecar, tag="a17-retagged")
            self.assertEqual(native_product.sidecars_for_product(refit_under(self.line), "refit.product", payload_sidecar=retagged)[0]["conditions_used"][0]["tag"], "a17-retagged")

    def test_a_nominal_refit_states_that_it_consumed_none_and_takes_no_sidecar(self):
        document = refit_under(None)
        for sidecar in native_product.sidecars_for_product(document, "refit.product"):
            self.assertEqual(sidecar["conditions_used"], [])
        with self.assertRaises(native_product.ProductFormatError):
            native_product.sidecars_for_product(document, "refit.product", payload_sidecar=self.sidecar)

    def test_two_payloads_and_two_fields_never_overwrite_each_other(self):
        plus, minus = refit_under(self.line, "refit.plus"), refit_under(self.other_line, "refit.minus")
        plus_sidecars = native_product.sidecars_for_product(plus, "refit-plus.product", payload_sidecar=self.sidecar)
        minus_sidecars = native_product.sidecars_for_product(minus, "refit-minus.product", payload_sidecar=self.other_sidecar)
        self.assertNotEqual(plus_sidecars[0]["conditions_used"], minus_sidecars[0]["conditions_used"])
        self.assertNotEqual({item["product_id"] for item in plus_sidecars}, {item["product_id"] for item in minus_sidecars})
        with self.assertRaises(native_product.ProductFormatError):  # one header cannot describe both payloads (stage 9)
            native_product.merge_products(plus, native_product.subset_tracks(minus, ["1"], "refit.minus.part"), "refit.both")
        nominal = refit_under(None, "refit.nominal")
        with self.assertRaises(native_product.ProductFormatError):
            native_product.merge_products(nominal, native_product.subset_tracks(plus, ["1"], "refit.plus.part"), "refit.both")
        zero_field = native_product.subset_tracks(refit_under(None, "refit.zero", field_tesla=0.0), ["1"], "refit.zero.part")
        with self.assertRaises(native_product.ProductFormatError):  # the field is a hypothesis too
            native_product.merge_products(native_product.subset_tracks(nominal, ["0"], "refit.nominal.part"), zero_field, "refit.both")
        # The test above fails on a merge that forgets the field: shown on a copy of the rule without it.
        without_field = tuple(name for name in native_product.MERGE_IDENTITY_FIELDS if name not in ("field_tesla", "qop_status"))
        with mock.patch.object(native_product, "MERGE_IDENTITY_FIELDS", without_field):
            merged = native_product.merge_products(native_product.subset_tracks(nominal, ["0"], "refit.nominal.part"), zero_field, "refit.both")
        self.assertEqual(merged["header"]["field_tesla"], 1.0)  # what such a merge would do: the zero-field track under a 1 T header

    def test_a_part_of_a_product_keeps_its_hypothesis(self):
        part = native_product.subset_tracks(refit_under(self.line), ["0"], "refit.r33.part")
        self.assertEqual(part["header"]["alignment_payload"], self.line)
        self.assertEqual(native_product.parse_product(native_product.format_product(part))["header"]["alignment_payload"], self.line)
        for sidecar in native_product.sidecars_for_product(part, "refit-part.product", payload_sidecar=self.sidecar):
            self.assertEqual(sidecar["conditions_used"][0]["payload_id"], self.sidecar["payload_id"])


# ---- A05 on the built programs.

def read_events(path: Path) -> list:
    return [[(int(hit["plane"]), float(hit["loc0_mm"]), float(hit["loc1_mm"])) for hit in event["hits"]] for event in fixture_files.iter_data_events(path)]


def interleaved_order(clean_events: int, noise_events: int) -> list:
    """Clean events last to first, alternating with noise events in the order (ORDER_STEP i) mod n."""
    clean = [("clean", ordinal) for ordinal in reversed(range(clean_events))]
    noise = [("noise", (ORDER_STEP * index) % noise_events) for index in range(noise_events)]
    order = []
    for index in range(max(clean_events, noise_events)):
        order += ([clean[index]] if index < clean_events else []) + ([noise[index]] if index < noise_events else [])
    return order


def find_with_vertices(folder: Path, data_file: Path, name: str) -> str:
    record_file, product_file = folder / f"{name}.record", folder / f"{name}.product"
    finding_tests.run_program([finding_tests.FINDER, "--data-file", data_file, "--product-id", name, "--product-file", product_file, "--record-file", record_file,
                               "--product-events", 0, "--vertex-recipe", finding_record.VERTEX_RECIPE])
    text = record_file.read_text(encoding="utf-8")
    finding_record.parse_record(text)  # the record is whole and reads
    return text


class InterleavedOrder(unittest.TestCase):
    def test_the_order_takes_every_event_once(self):
        order = interleaved_order(ORDER_EVENTS, ORDER_EVENTS)
        self.assertEqual(sorted(order), sorted([("clean", n) for n in range(ORDER_EVENTS)] + [("noise", n) for n in range(ORDER_EVENTS)]))
        self.assertEqual(order[:4], [("clean", ORDER_EVENTS - 1), ("noise", 0), ("clean", ORDER_EVENTS - 2), ("noise", ORDER_STEP)])


@unittest.skipUnless(BUILT, NOT_BUILT)
class EventOrderRun(unittest.TestCase):
    """A05 on the built finder and driver, block 1 (tuning). Development check, not a gate (K09)."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        folder = Path(cls.folder.name)
        cls.files = {"clean": finding_tests.generate(folder, "clean", ORDER_CLEAN_STRATUM, ORDER_EVENTS), "noise": finding_tests.generate(folder, "noise", ORDER_NOISE_STRATUM, ORDER_EVENTS)}
        cls.events = {name: read_events(data_file) for name, (data_file, _) in cls.files.items()}
        cls.sigma = {name: fixture_files.read_data_header(data_file)["sigma_loc0_mm"] for name, (data_file, _) in cls.files.items()}
        cls.recoded = {name: fixture_files.encode_data_file(cls.sigma[name], events) for name, events in cls.events.items()}
        cls.order = interleaved_order(ORDER_EVENTS, ORDER_EVENTS)
        cls.mixed_file = folder / "interleaved.t07data"
        cls.mixed_file.write_bytes(fixture_files.encode_data_file(cls.sigma["clean"], [cls.events[name][ordinal] for name, ordinal in cls.order]))
        cls.alone = {name: find_with_vertices(folder, data_file, f"a05-{name}") for name, (data_file, _) in cls.files.items()}
        cls.mixed = find_with_vertices(folder, cls.mixed_file, "a05-interleaved")
        cls.defects = order_defects(cls.alone, cls.mixed, cls.order)
        print(f"A05-FINDER events {len(cls.order)} (clean stratum {ORDER_CLEAN_STRATUM} reversed, noise stratum {ORDER_NOISE_STRATUM} in order {ORDER_STEP} i mod {ORDER_EVENTS}): "
              f"end totals alone {[end_totals(text) for text in cls.alone.values()]}, interleaved {end_totals(cls.mixed)}, defects {len(cls.defects)}", flush=True)
        for defect in cls.defects[:20]:
            print(f"A05-FINDER-DEFECT {defect}", flush=True)
        # The refit: the clean file's truth hit sets, scoring side, in file order and reversed, at 1 T.
        data_file, truth_file = cls.files["clean"]
        hit_sets = []
        for ordinal, truth_event in enumerate(truth_files.iter_truth_events(truth_file)):
            for track in truth_event["tracks"]:
                keys = [int(key) for key in track["hit_keys"] if int(key) != truth_files.NO_HIT_KEY]
                hit_sets.append((f"event-{ordinal}-track-{int(track['particle_key'])}", ordinal, float(track["q_over_p"]), keys))
        cls.refits = {name: cls.refit(folder, data_file, sets, f"a05-refit-{name}") for name, sets in (("forward", hit_sets), ("reversed", list(reversed(hit_sets))))}
        cls.refit_defects = per_track_defects(cls.refits["forward"], cls.refits["reversed"])
        print(f"A05-REFIT tracks {len(hit_sets)} forward and reversed: defects {len(cls.refit_defects)}", flush=True)
        for defect in cls.refit_defects[:20]:
            print(f"A05-REFIT-DEFECT {defect}", flush=True)

    @staticmethod
    def refit(folder: Path, data_file: Path, hit_sets: list, product_id: str) -> dict:
        hit_sets_file, product_file = folder / f"{product_id}.hitsets", folder / f"{product_id}.product"
        hit_sets_file.write_text(fixture_files.hit_sets_text(fixture_files.file_sha256(data_file), hit_sets), encoding="utf-8")
        finding_tests.run_program([DRIVER, "refit", "--data-file", data_file, "--hit-sets", hit_sets_file, "--field-tesla", "1", "--product-id", product_id, "--product-file", product_file])
        return native_product.parse_product(product_file.read_text(encoding="utf-8"))

    def test_the_files_are_rewritten_exactly(self):
        # The control the interleaved file rests on: each file re-encoded in its own order gives its own bytes, so the hits reach the finder unchanged.
        for name, (data_file, _) in self.files.items():
            with self.subTest(file=name):
                self.assertEqual(self.recoded[name], data_file.read_bytes())
        self.assertEqual(self.sigma["clean"], self.sigma["noise"])

    def test_every_event_reads_as_it_does_alone(self):
        self.assertEqual(self.defects, [])

    def test_every_refit_track_is_the_same_in_either_order(self):
        self.assertEqual(len(self.refits["forward"]["tracks"]), ORDER_EVENTS * finding_tests.TRACKS_OF_LEVEL[0])
        self.assertEqual(self.refit_defects, [])


if __name__ == "__main__":
    unittest.main()
