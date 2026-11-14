"""Bounded input inspector, task T14 (plan Sections 5.5, 5.6, 5.8, 5.15; K15, K17; scenarios A43-A49, A59 and the recognition
part of A16). Every check starts from an honest input and changes one thing. Synthetic documents only."""
import ast
import inspect
import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import input_inspector  # noqa: E402
from contracts.input_inspector import CSV_PROBE, JSON_PROBE, PROBES, inspect_inputs, judge_candidates  # noqa: E402
from contracts.reconstruction import read_sidecar  # noqa: E402
from contracts.sidecar_reader import FORMATS  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from tests.contracts import reconstruction_fixtures  # noqa: E402
from tests.contracts.reconstruction_fixtures import (NOMINAL_GEOMETRY, OTHER_GEOMETRY, alignment_payload, association_product, calibration_payload,  # noqa: E402
                                                     candidate_product, code_list, constraint_product, collection_witness, constraint_witness, count_product, extended, frame_payloads, frame_product, global_scan,
                                                     input_signature, inversion_product, inversion_witness, measurement, product, pulse_product, radio_frequency_scan,
                                                     retarding_scan, scan_product, sealed, signature_fact, used_payload)

BUDGET = {"probes": 10, "bytes": 1_000_000, "seconds": 60, "memory_bytes": 1_000_000_000, "tools": 2}
HONEST_CSV = "﻿# SYNTHETIC label line\r\nperiod,time_s,\"value, raw\",error\r\n1,0.5,2.5,0.1\r\n2,1.5,2.6,0.1\r\n"


def waveform_product(product_id="product.wave", waveform="kept") -> dict:
    """A product that retains its traces and states no clock: A44."""
    return product(product_id, retention={"raw": "removed", "waveform": waveform, "truth": "removed", "candidates": "not-applicable", "conditions_snapshot": "kept", "lost_recalibrations": ["pedestal"]})


def fixed_clock():
    """A clock that never advances, so two inspections compare exactly."""
    return 0.0


class Scratch(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.folder = Path(holder.name)

    def write(self, name, content):
        path = self.folder / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        elif isinstance(content, str):
            path.write_text(content, encoding="utf-8", newline="")
        else:
            path.write_text(json.dumps(content), encoding="utf-8")
        return str(path)

    def inspected(self, name, content, label=None, budget=None, **fields):
        """The caller's label is the product's own identity, as an honest manifest gives it."""
        label = label or (content.get("product_id", "product.a") if isinstance(content, dict) else "product.a")
        return inspect_inputs([dict(product=label, path=self.write(name, content), **fields)], budget or BUDGET, clock=fixed_clock)


def without_measured_cost(record):
    """Seconds and resident memory are measurements, not content."""
    copied = json.loads(json.dumps(record))
    for cost in [copied["spent"]] + [probe["cost"] for probe in copied["probes"]]:
        cost["seconds"] = cost["memory_bytes"] = 0
    return copied


def fact_values(signature, key):
    return [fact["value"] for fact in signature["facts"] if fact["key"] == key]


def only_signature(record):
    (signature,) = record["signatures"]
    return signature


class HonestInputs(Scratch):
    """K15: the first known readers are the plugin's own JSON and CSV products."""

    def test_a_product_sidecar_is_read_into_a_signature_that_the_reader_accepts(self):
        record = self.inspected("a.json", product(objects=[measurement(0)]))
        self.assertEqual((record["state"], record["stop_reason"]), ("complete", None))
        self.assertEqual(code_list(read_sidecar(record)), [])
        signature = only_signature(record)
        self.assertEqual(code_list(read_sidecar(signature)), [])
        self.assertEqual(signature["scope"]["product"], "product.hits-a")
        self.assertEqual(fact_values(signature, "container"), ["json"])
        self.assertEqual(fact_values(signature, "product_schema"), ["reconstruction-product/1"])

    def test_every_fact_keeps_value_scope_source_method_and_validity(self):
        """K15; Section 5.5."""
        for fact in only_signature(self.inspected("a.json", product()))["facts"]:
            self.assertEqual(set(fact), {"key", "value", "scope", "source", "reader_version", "method", "validity"})

    def test_a_csv_product_with_a_label_line_a_mark_crlf_and_a_quoted_comma_is_read(self):
        """'#' lines are comments in the plugin's CSV products (skills/hep-detector/scripts/build_response.py)."""
        record = self.inspected("a.csv", HONEST_CSV)
        self.assertEqual((record["state"], record["stop_reason"]), ("complete", None))
        self.assertEqual(code_list(read_sidecar(record)), [])
        signature = only_signature(record)
        self.assertEqual(fact_values(signature, "container"), ["csv"])
        self.assertEqual(fact_values(signature, "column_count"), [4])
        self.assertEqual(fact_values(signature, "sample_rows"), [2])

    def test_every_tracked_csv_gives_a_reading_or_an_honest_stop(self):
        """All 14, found and not listed by hand (13 in a copy without the examples' output folders, as the AMS-optional check
        builds; one CSV is an example output). The four CRDB exports hold no header row, so they stay unknown."""
        found = sorted(path for top in ("skills", "examples", "tests", "adapters") for path in (ROOT / top).rglob("*.csv"))
        outputs = [path for path in found if "output" in path.relative_to(ROOT).parts]
        self.assertGreaterEqual(len(found) - len(outputs), 13)
        if (ROOT / "examples" / "geant4-thin-silicon" / "output").is_dir():
            self.assertGreaterEqual(len(found), 14)
        for path in found:
            record = inspect_inputs([{"product": "product.a", "path": str(path)}], BUDGET)
            self.assertEqual(code_list(read_sidecar(record)), [], path.name)
            self.assertEqual(record["state"], "partial" if "crdb" in path.parts else "complete", path.name)

    def test_a_one_column_table_is_read(self):
        record = self.inspected("a.csv", "# label\nx\n1.5\n2.5\n")
        self.assertEqual((record["state"], fact_values(only_signature(record), "column_count")), ("complete", [1]))

    def test_every_sidecar_fixture_is_read_alone_with_a_mark_and_in_a_list(self):
        documents = [builder() for name, builder in inspect.getmembers(reconstruction_fixtures, inspect.isfunction)
                     if all(parameter.default is not parameter.empty for parameter in inspect.signature(builder).parameters.values()) and name not in ("frame_payloads", "collection_witness", "candidate_witness")]
        documents = [document for document in documents if isinstance(document, dict) and document.get("schema") in FORMATS]
        documents += [scan_product(scan) for scan in (global_scan(), radio_frequency_scan(), retarding_scan())] + list(frame_payloads().values()) + list(collection_witness().values())
        self.assertGreaterEqual(len(documents), 15)
        for document in documents:
            self.assertEqual(self.inspected("a.json", document)["state"], "complete", document["schema"])
            self.assertEqual(self.inspected("a.json", b"\xef\xbb\xbf" + json.dumps(document).encode(), label=document.get("product_id"))["state"], "complete", document["schema"])
            self.assertEqual(self.inspected("a.json", [document], label="file.a")["state"], "complete", document["schema"])

    def test_an_operator_product_reads_under_an_honest_budget(self):
        self.assertEqual(self.inspected("a.json", inversion_product(inversion_witness()))["state"], "complete")

    def test_a_suffix_in_capitals_finds_its_reader(self):
        self.assertEqual(self.inspected("A.JSON", product())["state"], "complete")
        self.assertEqual(self.inspected("A.CSV", HONEST_CSV)["state"], "complete")

    def test_a_quoted_newline_at_the_window_edge_does_not_fail_an_honest_table(self):
        """Padding the header walks the window edge through a row, so some cases cut inside the quoted cell."""
        rows = '000000,"first line\nsecond line"\n' * 5000
        for padding in range(0, 36, 4):
            record = self.inspected("a.csv", "a" * (padding + 1) + ",b\n" + rows)
            self.assertEqual(record["state"], "complete", padding)
            self.assertEqual(record["probes"][0]["read_scope"], "first window", padding)


class ContainerIdentifiesOnlyTheReader(Scratch):
    """A43; K15: file names are not evidence, and without a runtime reader nothing is recognised."""

    def test_a_suggestive_file_name_changes_nothing(self):
        honest = self.inspected("a.json", product(objects=[measurement(0)]))
        named = self.inspected("silicon_tracker_raw_waveform_calorimeter.json", product(objects=[measurement(0)]))
        self.assertEqual(without_measured_cost(honest), without_measured_cost(named))
        self.assertEqual(without_measured_cost(self.inspected("a.csv", HONEST_CSV)), without_measured_cost(self.inspected("tpc_drift_raw.csv", HONEST_CSV)))

    def test_no_file_name_reaches_the_record(self):
        record = self.inspected("silicon_tracker_raw.json", product())
        self.assertNotIn("silicon", json.dumps(record))
        self.assertNotIn(str(self.folder), json.dumps(record))

    def test_a_container_gives_no_detector_no_level_and_no_representation(self):
        signature = only_signature(self.inspected("raw_waveform.csv", "adc_waveform,energy_MeV,time_ns\n1,2,3\n"))
        self.assertEqual(sorted({fact["key"] for fact in signature["facts"]}), ["column_count", "columns", "container", "sample_rows"])
        for dimension in ("detector", "representation", "retention", "quantity", "sampling"):
            self.assertIn(dimension, signature["unknown"])
        self.assertEqual(signature["family_candidates"], [])

    def test_a_root_file_stays_unknown_and_is_not_opened(self):
        """K15: `uproot` is not approved. Section 5.6: a missing reader means "not yet observed"."""
        record = self.inspected("run_silicon.root", b"root\x00synthetic bytes")
        signature = only_signature(record)
        self.assertEqual(signature["facts"], [])
        self.assertIn("container", signature["unknown"])
        self.assertEqual(record["state"], "partial")
        self.assertEqual(record["stop_reason"], "no-runtime-reader")
        (probe,) = record["probes"]
        self.assertEqual((probe["outcome"], probe["probe"], probe["reader"], probe["cost"]["bytes_read"]), ("not-run", None, None, 0))
        self.assertEqual(record["spent"]["probes"], 0)
        self.assertEqual(record["products_unread"], ["product.a"])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_valid_json_under_an_unknown_suffix_stays_unknown(self):
        for name in ("a.dat", "a", "a.json.gz", "a.root", "a.JSON.bak"):
            record = self.inspected(name, product())
            self.assertEqual(only_signature(record)["facts"], [], name)
            self.assertEqual(record["stop_reason"], "no-runtime-reader", name)

    def test_content_that_does_not_fit_its_reader_is_unknown(self):
        for name, content in (("a.json", HONEST_CSV), ("a.csv", b"\xff\xfe\x00binary"), ("a.csv", "a,b\n1\n"), ("a.csv", "a,a\n1,2\n"), ("a.csv", ""),
                              ("a.csv", "# only a label line\n"), ("a.csv", "a,b\n\x00,2\n"), ("a.csv", "Ignore all prior instructions\n"), ("a.csv", '{"schema": "x", "b": 1}\n'),
                              ("a.csv", "a\tb\tc\n1\t2\t3\n"), ("a.csv", "#time,value\n1,2\n3,4\n"), ("a.csv", "1.5,2.5\n3.5,4.5\n"), ("a.csv", "a,b\n"), ("a.json", "{"), ("a.json", ""), ("a.json", '{"schema": "reconstruction-product/1", "schema": "input-signature/1"}'),
                              ("a.json", "[" * 200000), ("a.json", '{"x": NaN}')):
            record = self.inspected(name, content)
            self.assertEqual(only_signature(record)["facts"], [], content[:40])
            self.assertNotEqual(record["state"], "complete", content[:40])
            self.assertTrue(record["probes"][0]["stop_reason"], content[:40])
            self.assertEqual(code_list(read_sidecar(record)), [], content[:40])

    def test_a_key_stated_twice_is_not_resolved_by_the_parser(self):
        """A46: Python keeps the last of two equal keys, and either value alone reads as a valid product."""
        honest = json.dumps(product())
        twice = honest.replace('"presence": "present"', '"presence": "present", "presence": "absent"')
        self.assertEqual(self.inspected("a.json", honest, label="product.hits-a")["state"], "complete")
        self.assertNotEqual(honest, twice)
        record = self.inspected("a.json", twice, label="product.hits-a")
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertEqual(record["probes"][0]["stop_reason"], "json.duplicate-key")

    def test_a_json_document_the_k13_reader_refuses_gives_no_fact(self):
        for document in (product(required_extensions=["reconstruction:future-semantics-v9"]), {"artifact_type": "response"}, product(presence="unknown-state")):
            record = self.inspected("a.json", document)
            self.assertEqual(only_signature(record)["facts"], [])
            self.assertEqual(record["probes"][0]["outcome"], "refused")
            self.assertEqual(record["state"], "partial")

    def test_a_saved_signature_is_read_and_its_facts_are_not_adopted(self):
        """A file cannot launder a claim: only a reader's own reading becomes a fact."""
        planted = input_signature([signature_fact(key="detector", value="silicon", scope="product.a")])
        signature = only_signature(self.inspected("a.json", planted))
        self.assertEqual(sorted({fact["key"] for fact in signature["facts"]}), ["container", "product_schema"])
        self.assertIn("detector", signature["unknown"])

    def test_a_manifest_can_describe_a_file_no_reader_can_open(self):
        """Section 5.5: a sourced declaration stands apart from recognition; the container stays unknown."""
        declared = [{"key": "detector", "value": "synthetic-array", "reference": "manifest:synthetic", "kind": "declaration"}]
        record = self.inspected("a.root", b"synthetic", declared=declared)
        signature = only_signature(record)
        self.assertEqual(fact_values(signature, "detector"), ["synthetic-array"])
        self.assertEqual((signature["scope"]["window"], record["state"]), ("not read", "partial"))
        self.assertIn("container", signature["unknown"])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_refusal_keeps_the_reader_code(self):
        record = self.inspected("a.json", product(required_extensions=["reconstruction:future-semantics-v9"]))
        self.assertEqual(record["probes"][0]["stop_reason"], "reconstruction.reader.unknown_required_extension")

    def test_an_ignored_optional_extension_is_reported(self):
        """K13: it may be ignored and is reported."""
        record = self.inspected("a.json", product(optional_extensions=["reconstruction:future-semantics-v9"]))
        self.assertEqual(record["state"], "complete")
        self.assertEqual(record["probes"][0]["warnings"], ["reconstruction.reader.unknown_optional_extension"])

    def test_malformed_requests_give_unknown_and_no_exception(self):
        path = self.write("a.json", product())
        for inputs in (None, "a.json", 3, {"product": "a"}, [None], [{}], [{"product": "", "path": path}], [{"product": 3, "path": path}],
                       [{"product": "product.a"}], [{"product": "product.a", "path": None}], [{"product": "product.a", "path": "a\x00b.json"}]):
            record = inspect_inputs(inputs, BUDGET)
            self.assertIn(record["state"], ("partial", "stopped"), repr(inputs))
            self.assertEqual(record["spent"]["bytes"], 0, repr(inputs))
            self.assertEqual(code_list(read_sidecar(record)), [], repr(inputs))

    def test_a_missing_file_a_directory_and_a_pipe_are_unknown_and_nothing_blocks(self):
        paths = [str(self.folder / "missing.json")]
        directory = self.folder / "folder.csv"
        directory.mkdir()
        paths.append(str(directory))
        if hasattr(os, "mkfifo"):  # Windows has no FIFO: there the missing file and the directory are the cases
            pipe = self.folder / "pipe.json"
            os.mkfifo(pipe)
            paths.append(str(pipe))
        for path in paths:
            record = inspect_inputs([{"product": "product.a", "path": path}], BUDGET)
            self.assertEqual(only_signature(record)["facts"], [], path)
            self.assertEqual(record["probes"][0]["outcome"], "not-run", path)
            self.assertTrue(record["stop_reason"], path)


class BudgetStops(Scratch):
    """A59; Section 5.6 item 5; K17: no default budget, and an exhausted budget ends in unknown with a stop reason."""

    def two_products(self):
        return [{"product": "product.a", "path": self.write("a.json", product("product.a"))},
                {"product": "product.b", "path": self.write("b.csv", HONEST_CSV)}]

    def test_within_budget_every_probe_runs_and_its_cost_is_visible(self):
        record = inspect_inputs(self.two_products(), BUDGET)
        self.assertEqual(record["state"], "complete")
        self.assertEqual(record["budget"], BUDGET)
        self.assertEqual(record["spent"]["probes"], 2)
        self.assertEqual(record["spent"]["bytes"], sum(probe["cost"]["bytes_read"] for probe in record["probes"]))
        self.assertEqual(record["spent"]["bytes"], sum(os.path.getsize(entry["path"]) for entry in self.two_products()))
        for probe in record["probes"]:
            self.assertEqual(probe["read_scope"], "whole file")
            self.assertEqual(probe["unread_bytes"], 0)

    def test_an_exhausted_probe_count_ends_in_unknown_with_a_stop_reason(self):
        record = inspect_inputs(self.two_products(), dict(BUDGET, probes=1))
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-probes"))
        self.assertEqual(record["spent"]["probes"], 1)
        self.assertEqual(len(record["products_read"]), 1)
        self.assertEqual(len(record["products_unread"]), 1)
        unread = next(signature for signature in record["signatures"] if signature["scope"]["product"] == record["products_unread"][0])
        self.assertEqual(unread["facts"], [])
        self.assertIn("container", unread["unknown"])
        self.assertEqual(unread["scope"]["window"], "not read")
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_an_exhausted_byte_budget_reads_nothing_more(self):
        inputs = self.two_products()
        smallest = min(os.path.getsize(entry["path"]) for entry in inputs)
        record = inspect_inputs(inputs, dict(BUDGET, bytes=smallest))
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-bytes"))
        self.assertEqual(record["spent"]["bytes"], smallest)
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_the_cheapest_probe_runs_first(self):
        """Section 5.16: lower costs first; a fixed order, no information-gain number."""
        big = {"product": "product.big", "path": self.write("big.json", product("product.big", objects=[measurement(index) for index in range(50)]))}
        small = {"product": "product.small", "path": self.write("small.json", product("product.small"))}
        record = inspect_inputs([big, small], dict(BUDGET, probes=1))
        self.assertEqual(record["products_read"], ["product.small"])

    def test_an_exhausted_time_budget_stops(self):
        ticks = itertools.count()
        record = inspect_inputs(self.two_products(), dict(BUDGET, seconds=2), clock=lambda: float(next(ticks)))
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-seconds"))
        self.assertGreater(record["spent"]["seconds"], 0)
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_no_declared_budget_reads_nothing(self):
        """K17: no default."""
        for budget in (None, {}, {"probes": 1}, {"probes": 1, "bytes": 1, "seconds": 1}, dict(BUDGET, other=1), dict(BUDGET, probes=-1), dict(BUDGET, probes=True),
                       dict(BUDGET, bytes=1.5), dict(BUDGET, seconds=float("nan")), dict(BUDGET, seconds=float("inf")), dict(BUDGET, memory_bytes=None),
                       dict(BUDGET, tools=-1), "unlimited", 3):
            record = inspect_inputs(self.two_products(), budget)
            self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-not-declared"), repr(budget))
            self.assertEqual((record["spent"]["probes"], record["spent"]["bytes"], record["budget"]), (0, 0, None), repr(budget))
            self.assertEqual(code_list(read_sidecar(record)), [], repr(budget))

    def test_a_zero_budget_is_honest_and_reads_nothing(self):
        record = inspect_inputs(self.two_products(), {"probes": 0, "bytes": 0, "seconds": 60, "memory_bytes": 10**12, "tools": 0})
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-probes"))
        self.assertEqual(record["spent"]["bytes"], 0)

    def test_a_large_csv_is_sampled_not_scanned(self):
        """A59: do not scan all data. Section 5.6 item 2: reading scope, sampling rule, cost and unread portion."""
        rows = "".join(f"{index},{index}\n" for index in range(100000))
        record = self.inspected("a.csv", "a,b\n" + rows)
        (probe,) = record["probes"]
        window = PROBES[CSV_PROBE]["parameters"]["window_bytes"]
        self.assertEqual(record["state"], "complete")
        self.assertEqual(probe["cost"]["bytes_read"], window)
        self.assertEqual(probe["read_scope"], "first window")
        self.assertIn("complete rows", probe["sampling"])
        self.assertEqual(probe["unread_bytes"], os.path.getsize(self.folder / "a.csv") - window)
        self.assertEqual(only_signature(record)["scope"]["window"], "bounded sample")
        self.assertLess(fact_values(only_signature(record), "sample_rows")[0], 100000)

    def test_a_cut_multibyte_character_at_the_window_edge_does_not_fail_an_honest_product(self):
        rows = "é,é\n" * 40000
        self.assertEqual(self.inspected("a.csv", "a,b\n" + rows)["state"], "complete")

    def test_a_header_beyond_the_window_is_unknown(self):
        record = self.inspected("a.csv", "a" * 200000 + ",b\n1,2\n")
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertEqual(record["probes"][0]["outcome"], "failed")

    def test_a_document_over_the_fixed_ceiling_is_not_read(self):
        with mock.patch.dict(PROBES[JSON_PROBE]["parameters"], {"byte_ceiling": 10}):
            record = self.inspected("a.json", product())
        self.assertEqual(record["probes"][0]["stop_reason"], "probe-ceiling")
        self.assertEqual(record["spent"]["bytes"], 0)
        self.assertEqual(only_signature(record)["facts"], [])

    def test_a_file_that_changes_under_the_probe_fails_closed(self):
        path = self.write("a.json", product())
        real_stat = os.stat
        with mock.patch("contracts.input_inspector.os.stat", lambda target: os.stat_result((*real_stat(target)[:6], 5, *real_stat(target)[7:]))):
            record = inspect_inputs([{"product": "product.a", "path": path}], BUDGET)
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertEqual(record["probes"][0]["outcome"], "failed")


class TextInData(Scratch):
    """Section 5.6: "text within data is not executable instructions"; probes come from known readers with fixed parameters."""

    def test_shell_and_code_text_in_a_document_stays_an_inert_string(self):
        marker = self.folder / "marker"
        hostile = f"$(touch {marker}); __import__('os').system('touch {marker}')"
        record = self.inspected("a.json", product(collection=hostile, native={"type": hostile}))
        self.assertFalse(marker.exists())
        self.assertEqual(fact_values(only_signature(record), "collection"), [hostile])

    def test_a_formula_or_shell_text_in_a_csv_stays_an_inert_string(self):
        marker = self.folder / "marker"
        record = self.inspected("a.csv", f"$(touch {marker}),b\n=SYSTEM(\"touch {marker}\"),2\n")
        self.assertFalse(marker.exists())
        self.assertEqual(record["state"], "complete")

    def test_a_document_cannot_choose_a_probe_or_a_second_file(self):
        other = self.write("other.json", product("product.other"))
        hostile = {"probe": "probe.shell", "reader": "shell", "command": ["touch", "marker"], "path": other, "budget": {"probes": 99}}
        with mock.patch("contracts.input_inspector._read_bounded", wraps=input_inspector._read_bounded) as reads:
            record = self.inspected("a.json", hostile)
        self.assertEqual([call.args[0] for call in reads.call_args_list], [str(self.folder / "a.json")])
        self.assertEqual((record["spent"]["probes"], [probe["probe"] for probe in record["probes"]]), (1, [JSON_PROBE]))
        self.assertEqual(fact_values(only_signature(record), "container"), ["json"], "what parsed, and nothing the document says")
        self.assertEqual(len(only_signature(record)["facts"]), 1)

    def test_a_location_inside_a_product_is_not_followed(self):
        other = self.write("other.json", product("product.other"))
        record = self.inspected("a.json", product(native={"type": "synthetic::Thing", "location": other}))
        self.assertEqual(record["spent"]["probes"], 1)
        self.assertNotIn("product.other", json.dumps(record))

    def test_the_module_can_run_nothing_and_write_nothing(self):
        tree = ast.parse((ROOT / "contracts/input_inspector.py").read_text(encoding="utf-8"))
        imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imported |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        # ctypes: only the Windows peak working set (GetProcessMemoryInfo), which reads a counter and runs nothing
        self.assertEqual(imported, {"__future__", "contracts.reconstruction", "contracts.schema", "contracts.sidecar_reader", "contracts.validate", "csv", "ctypes", "io", "json", "math", "os", "resource", "stat", "sys", "time"})
        called = {node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "") for node in ast.walk(tree) if isinstance(node, ast.Call)}
        self.assertFalse(called & {"eval", "exec", "compile", "__import__", "system", "popen", "spawnv", "execv", "fork", "write", "remove", "unlink", "rename", "mkdir"})
        opened = [node for node in ast.walk(tree) if isinstance(node, ast.Attribute) and node.attr.startswith("O_")]
        self.assertEqual({node.attr for node in opened}, {"O_RDONLY"})
        flags = {node.args[1].value for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "getattr"
                 and len(node.args) == 3 and isinstance(node.args[1], ast.Constant) and str(node.args[1].value).startswith("O_")}
        self.assertEqual(flags, {"O_NONBLOCK", "O_BINARY"})
        self.assertEqual(input_inspector.OPEN_FLAGS & os.O_WRONLY | input_inspector.OPEN_FLAGS & os.O_RDWR, 0)
        if hasattr(os, "O_NONBLOCK"):
            self.assertTrue(input_inspector.OPEN_FLAGS & os.O_NONBLOCK)


VALID_ARTIFACTS = ROOT / "contracts/fixtures/artifacts/valid"
# One tracked artifact of each kind, plus files the plugin's own examples wrote.
TRACKED_ARTIFACTS = {"response": "response_v28.json", "measurement-spec": "measurement_collider.json", "prediction": "prediction.json", "comparison-spec": "comparison_spec.json",
                     "computational-run": "computational_run.json", "communication": "communication.json", "dataset-record": "dataset_record.json", "literature-record": "literature_record.json",
                     "ml-artifact": "ml_artifact.json", "design-spec": "design_spec.json", "design-candidate": "design_candidate.json", "design-evaluation": "design_evaluation.json",
                     "statistical-result": "statres_bayesian.json"}


def tracked_artifact(name="response_v28.json") -> dict:
    return json.loads((VALID_ARTIFACTS / name).read_text(encoding="utf-8"))


class EnvelopeArtifacts(Scratch):
    """K15 and the user's T14 ruling (decisions.md, "T14 rulings"): real plugin artifacts are read through their existing validator,
    and report container, product_schema and artifact_type, with no physics inferred."""

    def test_each_kind_of_tracked_artifact_is_read_with_three_facts_and_no_physics(self):
        for kind, name in TRACKED_ARTIFACTS.items():
            record = inspect_inputs([{"product": "product.a", "path": str(VALID_ARTIFACTS / name)}], BUDGET)
            self.assertEqual((record["state"], record["stop_reason"]), ("complete", None), name)
            self.assertEqual(code_list(read_sidecar(record)), [], name)
            signature = only_signature(record)
            self.assertEqual(sorted(fact["key"] for fact in signature["facts"]), ["artifact_type", "container", "product_schema"], name)
            self.assertEqual(fact_values(signature, "artifact_type"), [kind], name)
            self.assertEqual(fact_values(signature, "product_schema"), ["artifact-envelope"], name)
            self.assertEqual(signature["family_candidates"], [], name)
            for dimension in ("representation", "quantity", "detector", "conditions", "sampling"):
                self.assertIn(dimension, signature["unknown"], name)

    @unittest.skipUnless((ROOT / "examples/ams-flux-ratio/output/artifacts").is_dir(), "no examples/ams-flux-ratio/output in this copy (the AMS-optional check builds its copy without example outputs)")
    def test_artifacts_the_plugin_wrote_in_an_example_are_read(self):
        folder = ROOT / "examples/ams-flux-ratio/output/artifacts"
        for name, kind in (("response_helium_synthetic-period-1.json", "response"), ("ratio_result.json", "statistical-result")):
            record = inspect_inputs([{"product": "product.a", "path": str(folder / name)}], BUDGET)
            self.assertEqual((fact_values(only_signature(record), "artifact_type"), record["state"]), ([kind], "complete"), name)

    @unittest.skipUnless((ROOT / "examples/ams-flux-ratio/output/artifacts").is_dir(), "no examples/ams-flux-ratio/output in this copy (the AMS-optional check builds its copy without example outputs)")
    def test_a_term_of_a_profile_stays_unknown_without_that_profile(self):
        """The validator knows a profile's vocabulary only from a project, which the inspector is not given. It fails closed and says why."""
        record = inspect_inputs([{"product": "product.a", "path": str(ROOT / "examples/ams-flux-ratio/output/artifacts/measurement_spec.json")}], BUDGET)
        self.assertEqual((only_signature(record)["facts"], record["probes"][0]["stop_reason"]), ([], "vocab.unknown_term"))

    def test_every_tracked_valid_artifact_is_read_and_every_invalid_one_gives_no_fact(self):
        folder = ROOT / "contracts/fixtures/artifacts"
        for group, read in (("valid", True), ("warning", True), ("invalid", False)):
            found = sorted((folder / group).glob("*.json"))
            self.assertTrue(found, group)
            for path in found:
                record = inspect_inputs([{"product": "product.a", "path": str(path)}], BUDGET)
                self.assertEqual(bool(fact_values(only_signature(record), "artifact_type")), read, path.name)
                self.assertEqual(code_list(read_sidecar(record)), [], path.name)
                if not read:
                    self.assertEqual(only_signature(record)["facts"], [], path.name)

    def test_an_artifact_with_one_defect_stays_unknown_with_the_validator_code(self):
        document = tracked_artifact()
        del document["objective"]
        record = self.inspected("a.json", document)
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertEqual((record["probes"][0]["outcome"], record["probes"][0]["stop_reason"], record["state"]), ("refused", "schema.required", "partial"))

    def test_a_semantic_refusal_of_the_validator_stops_too(self):
        document = tracked_artifact()
        document["contract_version"] = "99.0.0"
        record = self.inspected("a.json", document)
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertEqual(record["probes"][0]["outcome"], "refused")

    def test_an_unknown_required_capability_stops_as_k13_does(self):
        document = tracked_artifact()
        document["required_capabilities"] = ["future:semantics-v9"]
        record = self.inspected("a.json", document)
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertEqual(record["probes"][0]["outcome"], "refused")

    def test_an_unknown_artifact_type_is_no_known_schema(self):
        record = self.inspected("a.json", dict(tracked_artifact(), artifact_type="response-future"))
        self.assertEqual(sorted(fact["key"] for fact in only_signature(record)["facts"]), ["container"])
        self.assertEqual((record["probes"][0]["stop_reason"], record["state"]), ("artifact.unknown_type", "partial"))
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_sidecar_that_also_names_an_artifact_type_still_meets_the_k13_stop(self):
        document = dict(product(required_extensions=["reconstruction:future-semantics-v9"]), artifact_type="response")
        record = self.inspected("a.json", document)
        self.assertEqual(record["probes"][0]["stop_reason"], "reconstruction.reader.unknown_required_extension")
        self.assertEqual(only_signature(record)["facts"], [])

    def test_a_validator_fault_stays_unknown_and_raises_nothing(self):
        with mock.patch("contracts.validate.validate_artifact", side_effect=TypeError("synthetic fault")):
            record = self.inspected("a.json", tracked_artifact())
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertEqual(record["probes"][0]["stop_reason"], "artifact.malformed")

    def test_a_detector_word_in_the_name_or_the_text_gives_no_fact(self):
        document = dict(tracked_artifact(), objective="silicon tracker waveform $(touch marker)")
        signature = only_signature(self.inspected("silicon_tracker_raw.json", document))
        self.assertEqual(sorted(fact["key"] for fact in signature["facts"]), ["artifact_type", "container", "product_schema"])
        self.assertNotIn("silicon", json.dumps(signature))

    def test_artifacts_in_a_list_keep_a_signature_each(self):
        record = self.inspected("a.json", [tracked_artifact(), tracked_artifact("prediction.json")], label="file.a")
        self.assertEqual(sorted(fact_values(signature, "artifact_type")[0] for signature in record["signatures"]), ["prediction", "response"])
        self.assertEqual(record["state"], "complete")

    def test_a_declared_type_against_the_read_one_is_a_conflict(self):
        declared = [{"key": "artifact_type", "value": "prediction", "reference": "manifest:synthetic", "kind": "declaration"}]
        record = self.inspected("a.json", tracked_artifact(), declared=declared)
        self.assertEqual([item["key"] for item in record["conflicts"]], ["artifact_type"])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_the_seconds_budget_stops_inside_the_validator(self):
        ticks = itertools.count()
        with mock.patch("contracts.input_inspector._document_facts", wraps=input_inspector._document_facts) as read_on:
            record = inspect_inputs([{"product": "product.a", "path": self.write("a.json", tracked_artifact())}], dict(BUDGET, seconds=5), clock=lambda: float(next(ticks)))
        read_on.assert_not_called()
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-seconds"))
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_byte_budget_keeps_an_artifact_unread(self):
        record = self.inspected("a.json", tracked_artifact(), budget=dict(BUDGET, bytes=10))
        self.assertEqual((record["state"], record["stop_reason"], record["spent"]["bytes"]), ("stopped", "budget-bytes", 0))
        self.assertEqual(only_signature(record)["facts"], [])

    def test_the_validator_is_the_one_route_for_an_artifact(self):
        with mock.patch("contracts.validate.validate_artifact", wraps=validate_artifact) as validated:
            self.inspected("a.json", tracked_artifact())
        self.assertEqual(validated.call_count, 1)


class WhatParsedStays(Scratch):
    """The user's T14 ruling: `container: json` survives for a file that parsed but has no known schema. It says nothing else."""

    def test_parsed_json_of_no_known_schema_keeps_only_its_container(self):
        for content in ('{"a": 1}', "null", "3", '"text"', dict(product(), schema="reconstruction-product/9"), {"schema": "other"}):
            record = self.inspected("a.json", content)
            signature = only_signature(record)
            self.assertEqual([(fact["key"], fact["value"], fact["method"]) for fact in signature["facts"]], [("container", "json", "observed")], content)
            self.assertEqual((record["state"], record["stop_reason"], record["probes"][0]["outcome"]), ("partial", "reconstruction.reader.unknown_format", "partial"), content)
            self.assertIn("product_schema", signature["unknown"], content)
            self.assertEqual(record["products_read"], [signature["scope"]["product"]])
            self.assertEqual(code_list(read_sidecar(record)), [], content)

    def test_an_empty_list_keeps_its_container_and_its_stop(self):
        record = self.inspected("a.json", "[]")
        self.assertEqual(fact_values(only_signature(record), "container"), ["json"])
        self.assertEqual((record["probes"][0]["stop_reason"], record["state"]), ("json.no-documents", "partial"))
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_list_of_unknown_documents_keeps_one_container(self):
        record = self.inspected("a.json", [{"a": 1}, {"b": 2}], label="file.a")
        self.assertEqual(fact_values(only_signature(record), "container"), ["json"])
        self.assertEqual(record["probes"][0]["documents_refused"], 2)

    def test_what_did_not_parse_keeps_nothing(self):
        for content in ("{", '{"x": NaN}', "[Infinity]", '{"a": 1, "a": 2}'):
            record = self.inspected("a.json", content)
            self.assertEqual(only_signature(record)["facts"], [], content)
            self.assertEqual(record["probes"][0]["outcome"], "failed", content)

    def test_a_k13_stop_keeps_nothing_and_no_container(self):
        """K13: a known format with an unknown required extension stops the reader; it is not a file of no known schema."""
        record = self.inspected("a.json", product(required_extensions=["reconstruction:future-semantics-v9"]))
        self.assertEqual(only_signature(record)["facts"], [])

    def test_a_known_schema_refused_on_its_rules_keeps_nothing(self):
        self.assertEqual(only_signature(self.inspected("a.json", product(presence="unknown-state")))["facts"], [])

    def test_a_container_fact_opens_no_gate(self):
        signature = only_signature(self.inspected("a.json", {"a": 1}))
        (judged,) = judge_candidates(signature, [{"candidate": "m", "requires": {"fact": "product_schema", "equals": "reconstruction-product/1"}}])
        self.assertEqual((judged["state"], judged["eligible"]), ("unknown", False))


class HybridProducts(Scratch):
    """A45; Section 5.5: per product and scope, with no single detector type per file."""

    def test_one_file_with_two_products_keeps_two_signatures_and_their_scopes(self):
        record = self.inspected("a.json", [waveform_product("product.wave"), count_product()], label="file.hybrid")
        self.assertEqual(record["state"], "complete")
        self.assertEqual(code_list(read_sidecar(record)), [])
        by_product = {signature["scope"]["product"]: signature for signature in record["signatures"]}
        self.assertEqual(set(by_product), {"file.hybrid/product.wave", f"file.hybrid/{count_product()['product_id']}"})
        self.assertEqual(fact_values(by_product["file.hybrid/product.wave"], "representation"), ["waveform"])
        self.assertEqual(fact_values(by_product[f"file.hybrid/{count_product()['product_id']}"], "representation"), ["count"])
        self.assertEqual(record["conflicts"], [])

    def test_one_product_with_two_blocks_keeps_two_labels_and_no_conflict(self):
        document = extended(dict(count_product(), candidates=candidate_product()["candidates"]), "reconstruction:candidates-v1")
        self.assertEqual(code_list(read_sidecar(document)), [])
        signature = only_signature(self.inspected("a.json", document))
        self.assertEqual(sorted(fact_values(signature, "representation")), ["candidate", "count"])
        self.assertEqual(signature["conflicts"], [])
        self.assertEqual(signature["family_candidates"], ["BP03", "BP04", "BP06", "BP09", "BP12", "BP13", "BP15"])

    def test_a_refused_product_does_not_hide_its_neighbour_or_read_as_clean(self):
        """Section 5.8: an unknown subsystem need not block local results; it is never a clean answer."""
        future = product("product.future", required_extensions=["reconstruction:future-semantics-v9"])
        record = self.inspected("a.json", [waveform_product("product.wave"), future], label="file.hybrid")
        self.assertEqual(record["state"], "partial")
        self.assertEqual(record["probes"][0]["outcome"], "partial")
        self.assertEqual(record["probes"][0]["stop_reason"], "reconstruction.reader.unknown_required_extension")
        by_product = {signature["scope"]["product"]: signature for signature in record["signatures"]}
        self.assertEqual(fact_values(by_product["file.hybrid/product.wave"], "representation"), ["waveform"])
        self.assertEqual(by_product["file.hybrid/refused"]["facts"], [])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_two_files_of_two_products_do_not_mix(self):
        record = inspect_inputs([{"product": "product.a", "path": self.write("a.json", waveform_product("product.a"))},
                                 {"product": count_product()["product_id"], "path": self.write("b.json", count_product())}], BUDGET)
        self.assertEqual(record["conflicts"], [])
        self.assertEqual(len(record["signatures"]), 2)

    def test_a_declaration_on_a_file_of_several_products_reaches_each_of_them(self):
        declared = [{"key": "detector", "value": "synthetic-array", "reference": "manifest:synthetic", "kind": "declaration"}]
        record = self.inspected("a.json", [count_product(), waveform_product()], label="file.hybrid", declared=declared)
        self.assertEqual(len(record["signatures"]), 2)
        for signature in record["signatures"]:
            self.assertEqual(fact_values(signature, "detector"), ["synthetic-array"])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_declaration_on_a_list_file_conflicts_with_the_element_that_disagrees(self):
        """M3; A46: the outer brackets must not hide a conflict."""
        declared = [{"key": "sampling.time_system", "value": "gps", "reference": "manifest:synthetic", "kind": "declaration"}]
        agreeing = pulse_product()
        agreeing["product_id"], agreeing["sampling"] = "product.agrees", dict(agreeing["sampling"], time_system="gps")
        record = self.inspected("a.json", [pulse_product(), agreeing], label="file.hybrid", declared=declared)
        self.assertEqual(record["state"], "partial")
        self.assertEqual(record["stop_reason"], "conflict-unresolved")
        self.assertEqual([(item["key"], item["scope"]) for item in record["conflicts"]], [("sampling.time_system", "file.hybrid/product.pulse")])
        self.assertEqual(record["conflicts"][0]["required_probe"], "probe.clock")
        by_product = {signature["scope"]["product"]: signature for signature in record["signatures"]}
        method = [{"candidate": "method.a", "requires": {"fact": "sampling.time_system", "equals": "digitizer-clock"}}]
        self.assertEqual(judge_candidates(by_product["file.hybrid/product.pulse"], method)[0]["state"], "conflicting")
        self.assertEqual(by_product["file.hybrid/product.agrees"]["conflicts"], [])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_declared_representation_on_a_list_file_conflicts_too(self):
        declared = [{"key": "representation", "value": "image", "reference": "manifest:synthetic", "kind": "declaration"}]
        record = self.inspected("a.json", [count_product()], label="file.hybrid", declared=declared)
        self.assertEqual([item["key"] for item in record["conflicts"]], ["representation"])

    def test_a_declaration_on_a_list_of_refused_documents_stays_on_the_file(self):
        declared = [{"key": "detector", "value": "synthetic-array", "reference": "manifest:synthetic", "kind": "declaration"}]
        record = self.inspected("a.json", [0, 0], label="file.hybrid", declared=declared)
        by_product = {signature["scope"]["product"]: signature for signature in record["signatures"]}
        self.assertEqual(fact_values(by_product["file.hybrid"], "detector"), ["synthetic-array"])
        self.assertEqual(sorted({fact["key"] for fact in by_product["file.hybrid/refused"]["facts"]}), ["container"])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_product_that_is_absent_or_invalid_generates_no_candidate(self):
        """Minor 6; Section 8.2: absent and invalid products deliver no observation."""
        for presence in ("absent", "invalid", "not-applicable"):
            document = waveform_product()
            document["presence"] = presence
            signature = only_signature(self.inspected("a.json", document))
            self.assertEqual((fact_values(signature, "representation"), signature["family_candidates"]), ([], []), presence)
            self.assertEqual(fact_values(signature, "presence"), [presence])
        self.assertTrue(only_signature(self.inspected("a.json", dict(waveform_product(), presence="valid-empty", objects=[])))["family_candidates"])


class CandidateTable(Scratch):
    """M5: Section 5.15, W1, W4, W5, W6 and W7, row by row."""

    ROWS = {"waveform": ["BP01", "BP05", "BP06", "BP07", "BP08", "BP09"], "count": ["BP06", "BP09", "BP12", "BP13"], "image": ["BP02", "BP10", "BP11"],
            "measurement": ["BP02", "BP03"], "candidate": ["BP03", "BP04", "BP15"], "track": ["BP03", "BP04"], "iq": ["BP09", "BP13"]}

    def test_each_representation_row(self):
        for label, candidates in self.ROWS.items():
            declared = [{"key": "representation", "value": label, "reference": "manifest:synthetic", "kind": "declaration"}]
            self.assertEqual(only_signature(self.inspected("a.csv", "a,b\n1,2\n", declared=declared))["family_candidates"], candidates, label)

    def test_a_label_with_no_row_generates_nothing(self):
        declared = [{"key": "representation", "value": "unheard-of", "reference": "manifest:synthetic", "kind": "declaration"}]
        self.assertEqual(only_signature(self.inspected("a.csv", "a,b\n1,2\n", declared=declared))["family_candidates"], [])

    def test_a_global_scan_includes_the_fourteenth_family_and_the_two_others_do_not(self):
        """W7 corresponds to BP13/BP14; the BP14 row is pointing plus timestream, a global subcase."""
        self.assertEqual(only_signature(self.inspected("a.json", scan_product(global_scan())))["family_candidates"], ["BP13", "BP14"])
        for scan in (radio_frequency_scan(), retarding_scan()):
            self.assertEqual(only_signature(self.inspected("a.json", scan_product(scan)))["family_candidates"], ["BP13"], scan["subcase"])

    def test_estimate_and_frames_give_their_witness_rows(self):
        """W2 corresponds to BP01/BP09; W3 to BP08/BP11/BP12."""
        self.assertEqual(only_signature(self.inspected("a.json", dict(pulse_product(), retention=waveform_product(waveform="removed")["retention"])))["family_candidates"], ["BP01", "BP09"])
        self.assertEqual(only_signature(self.inspected("a.json", frame_product()))["family_candidates"], ["BP08", "BP11", "BP12"])

    def test_a_scan_is_acquisition_and_no_representation(self):
        """Section 5.5 lists scan under acquisition."""
        signature = only_signature(self.inspected("a.json", scan_product(global_scan())))
        self.assertEqual(fact_values(signature, "acquisition"), ["scan"])
        self.assertEqual(fact_values(signature, "representation"), [])
        self.assertNotIn("acquisition", signature["unknown"])

    def test_inversion_and_association_blocks_give_their_rows(self):
        """W5 corresponds to BP10; the BP15 row names associations."""
        self.assertEqual(only_signature(self.inspected("a.json", inversion_product()))["family_candidates"], ["BP10"])
        self.assertEqual(only_signature(self.inspected("a.json", association_product()))["family_candidates"], ["BP15"])


class AmbiguousWaveforms(Scratch):
    """A44; Sections 5.5, 5.15: multiple candidates stay, and nothing runs while required quantities or clocks are missing."""

    TIMED_METHOD = {"candidate": "method.template", "requires": {"all_of": [{"fact": "representation", "equals": "waveform"}, {"fact": "sampling.time_system", "equals": "digitizer-clock"}]}}

    def test_a_waveform_with_no_clock_keeps_several_candidates_and_is_not_eligible(self):
        signature = only_signature(self.inspected("a.json", waveform_product()))
        self.assertEqual(signature["family_candidates"], ["BP01", "BP05", "BP06", "BP07", "BP08", "BP09"])
        self.assertIn("sampling", signature["unknown"])
        (judged,) = judge_candidates(signature, [self.TIMED_METHOD])
        self.assertEqual((judged["state"], judged["eligible"], judged["open"]), ("unknown", False, ["sampling.time_system"]))

    def test_the_same_waveform_with_its_clock_is_eligible_and_keeps_its_candidates(self):
        signature = only_signature(self.inspected("a.json", pulse_product()))
        self.assertGreater(len(signature["family_candidates"]), 1)
        self.assertEqual(fact_values(signature, "sampling.time_system"), ["digitizer-clock"])
        self.assertEqual(fact_values(signature, "sampling.interval.unit"), ["ns"])
        self.assertTrue(judge_candidates(signature, [self.TIMED_METHOD])[0]["eligible"])

    def test_a_product_with_its_waveform_removed_is_not_a_waveform(self):
        document = waveform_product(waveform="removed")
        signature = only_signature(self.inspected("a.json", document))
        self.assertEqual(fact_values(signature, "representation"), [])
        self.assertEqual(signature["family_candidates"], [])

    def test_a_declared_waveform_in_a_csv_keeps_several_candidates(self):
        declared = [{"key": "representation", "value": "waveform", "reference": "manifest:synthetic", "kind": "declaration"}]
        signature = only_signature(self.inspected("a.csv", "s0,s1\n1,2\n", declared=declared))
        self.assertGreater(len(signature["family_candidates"]), 1)
        self.assertNotIn("representation", signature["unknown"])

    def test_a_fact_keeps_declared_apart_from_observed(self):
        """Section 5.5: direct observation, sourced declaration and derivation are distinct."""
        facts = {fact["key"]: fact for fact in only_signature(self.inspected("a.json", pulse_product()))["facts"]}
        self.assertEqual((facts["container"]["method"], facts["container"]["source"]["kind"]), ("observed", "reader"))
        self.assertEqual((facts["sampling.time_system"]["method"], facts["sampling.time_system"]["source"]["kind"]), ("declared", "declaration"))
        self.assertEqual((facts["representation"]["method"], facts["representation"]["source"]["kind"]), ("derived", "derivation"))


class Conflicts(Scratch):
    """A46; Section 5.5: a conflict stays visible, names the probe it needs, and no value is chosen."""

    def two_files(self, first, second):
        label = first.get("product_id", "product.a")
        return inspect_inputs([{"product": label, "path": self.write("first.json", first)}, {"product": label, "path": self.write("second.json", second)}], BUDGET)

    def assert_conflict(self, record, key, values, required_probe):
        self.assertEqual(code_list(read_sidecar(record)), [])
        (conflict,) = [item for item in record["conflicts"] if item["key"] == key]
        self.assertEqual(sorted(str(item["value"]) for item in conflict["values"]), sorted(str(value) for value in values))
        self.assertEqual(conflict["required_probe"], required_probe)
        signature = record["signatures"][0]
        self.assertIn(key, signature["conflicts"])
        self.assertEqual(sorted(str(value) for value in fact_values(signature, key)), sorted(str(value) for value in values), "both values stay")

    def sampled(self, **fields):
        document = pulse_product()
        document["sampling"] = dict(document["sampling"], **fields)
        return document

    def test_conflicting_units_are_named_with_their_probe(self):
        record = self.two_files(pulse_product(), self.sampled(interval={"value": 1, "unit": "ps"}))
        self.assert_conflict(record, "sampling.interval.unit", ["ns", "ps"], "probe.sampling")
        self.assertFalse(next(item for item in record["conflicts"] if item["key"] == "sampling.interval.unit")["probe_registered"])

    def test_conflicting_clocks_are_named_with_their_probe(self):
        self.assert_conflict(self.two_files(pulse_product(), self.sampled(time_system="other-clock")), "sampling.time_system", ["digitizer-clock", "other-clock"], "probe.clock")

    def test_conflicting_geometry_is_named_with_its_probe(self):
        first, second = alignment_payload(), sealed(dict(alignment_payload(), derived_against={"geometry_id": OTHER_GEOMETRY}))
        self.assert_conflict(self.two_files(first, second), "geometry_id", [NOMINAL_GEOMETRY, OTHER_GEOMETRY], "probe.payload")

    def test_metadata_against_the_read_schema_is_a_conflict(self):
        declared = [{"key": "representation", "value": "image", "reference": "manifest:synthetic", "kind": "declaration"}]
        record = self.inspected("a.json", count_product(), declared=declared)
        self.assert_conflict(record, "representation", ["count", "image"], "probe.schema")
        self.assertEqual(only_signature(record)["family_candidates"], ["BP02", "BP06", "BP09", "BP10", "BP11", "BP12", "BP13"], "both labels stay candidates")

    def test_a_declared_container_against_the_observed_one_is_a_conflict(self):
        declared = [{"key": "container", "value": "csv", "reference": "manifest:synthetic", "kind": "declaration"}]
        self.assert_conflict(self.inspected("a.json", product(), declared=declared), "container", ["csv", "json"], "probe.schema")

    def test_a_conflict_blocks_every_candidate_that_needs_it(self):
        record = self.two_files(pulse_product(), self.sampled(time_system="other-clock"))
        (judged,) = judge_candidates(record["signatures"][0], [{"candidate": "method.a", "requires": {"fact": "sampling.time_system", "equals": "digitizer-clock"}}])
        self.assertEqual((judged["state"], judged["eligible"]), ("conflicting", False))

    def test_agreeing_sources_are_no_conflict(self):
        declared = [{"key": "sampling.time_system", "value": "digitizer-clock", "reference": "manifest:synthetic", "kind": "declaration"}, {"key": "representation", "value": "waveform", "reference": "manifest:synthetic", "kind": "declaration"}]
        record = self.inspected("a.json", pulse_product(), declared=declared)
        self.assertEqual((record["conflicts"], only_signature(record)["conflicts"]), ([], []))

    def test_a_metadata_file_beside_a_csv_of_the_same_product_is_no_conflict(self):
        """An honest pair: per-file facts keep the scope of their file."""
        record = inspect_inputs([{"product": "product.pulse", "path": self.write("meta.json", pulse_product())}, {"product": "product.pulse", "path": self.write("a.csv", HONEST_CSV)}], BUDGET)
        self.assertEqual((record["state"], record["conflicts"]), ("complete", []))
        self.assertEqual(sorted(fact_values(only_signature(record), "container")), ["csv", "json"])

    def test_a_declared_value_within_a_multi_label_product_is_no_conflict(self):
        document = extended(dict(count_product(), candidates=candidate_product()["candidates"]), "reconstruction:candidates-v1")
        record = self.inspected("a.json", document, declared=[{"key": "representation", "value": "count", "reference": "manifest:synthetic", "kind": "declaration"}])
        self.assertEqual(record["conflicts"], [])

    def test_a_number_and_a_boolean_are_not_the_same_value(self):
        declared = [{"key": "flag", "value": 1, "reference": "manifest:one", "kind": "declaration"}, {"key": "flag", "value": True, "reference": "manifest:two", "kind": "declaration"}]
        self.assertEqual(len(self.inspected("a.json", product(), declared=declared)["conflicts"]), 1)
        facts = [signature_fact(key="flag", value=1), signature_fact(key="flag", value=True)]
        self.assertIn("reconstruction.signature.hidden_conflict", code_list(read_sidecar(input_signature(facts))))
        self.assertEqual(code_list(read_sidecar(input_signature(facts, conflicts=["flag"]))), [])

    def test_equal_numbers_are_the_same_value(self):
        declared = [{"key": "gain", "value": 1, "reference": "manifest:one", "kind": "declaration"}, {"key": "gain", "value": 1.0, "reference": "manifest:two", "kind": "declaration"}]
        self.assertEqual(self.inspected("a.json", product(), declared=declared)["conflicts"], [])

    def test_values_in_two_products_never_conflict(self):
        record = inspect_inputs([{"product": "product.pulse", "path": self.write("a.json", pulse_product())},
                                 {"product": "product.b", "path": self.write("b.json", dict(self.sampled(time_system="other-clock"), product_id="product.b"))}], BUDGET)
        self.assertEqual(record["conflicts"], [])


class AlternativeConstraints(Scratch):
    """A47; Section 5.8: AND and OR, a branch passes only when fully satisfied, and the branch used is named."""

    EXTERNAL = {"fact": "constraint.external.external-time-origin", "equals": "available"}
    INTERNAL = {"all_of": [{"fact": "constraint.internal.internal-time-constraint", "equals": "qualified"},
                           {"fact": "constraint.internal.internal-time-constraint.sufficient", "equals": True}]}
    TIMING = {"candidate": "method.drift", "requires": {"all_of": [{"fact": "product_schema", "equals": "reconstruction-product/1"}, {"any_of": [EXTERNAL, INTERNAL]}]}}

    def judged(self, document, **fields):
        return judge_candidates(only_signature(self.inspected("a.json", document, **fields)), [self.TIMING])[0]

    def test_a_qualified_internal_alternative_passes_and_names_its_branch(self):
        judged = self.judged(constraint_product())
        self.assertEqual((judged["state"], judged["eligible"]), ("satisfied", True))
        self.assertIn("constraint.internal.internal-time-constraint", judged["branch"])
        self.assertNotIn("constraint.external.external-time-origin", judged["branch"])

    def test_an_available_external_constraint_passes(self):
        judged = self.judged(constraint_product(constraint_witness(external="available")))
        self.assertTrue(judged["eligible"])
        self.assertIn("constraint.external.external-time-origin", judged["branch"])

    def test_a_branch_only_half_satisfied_does_not_pass(self):
        judged = self.judged(constraint_product(constraint_witness(outcome="restricted", sufficient=False)))
        self.assertEqual((judged["state"], judged["eligible"]), ("unsatisfied", False))

    def test_unknown_alternatives_are_not_a_pass(self):
        judged = self.judged(product())
        self.assertEqual((judged["state"], judged["eligible"]), ("unknown", False))

    def test_a_conflicting_alternative_is_not_a_pass(self):
        declared = [{"key": "constraint.internal.internal-time-constraint", "value": "unqualified", "reference": "manifest:synthetic", "kind": "declaration"}]
        judged = self.judged(constraint_product(), declared=declared)
        self.assertEqual((judged["state"], judged["eligible"]), ("conflicting", False))

    def test_a_conflict_on_a_branch_blocks_the_alternative(self):
        declared = [{"key": "constraint.external.external-time-origin", "value": "available", "reference": "manifest:synthetic", "kind": "declaration"}]
        judged = self.judged(constraint_product(), declared=declared)
        self.assertEqual((judged["state"], judged["eligible"], judged["branch"]), ("conflicting", False, []), "the user's T14 ruling: even if another branch would pass")
        self.assertEqual(judged["open"], ["constraint.external.external-time-origin"])
        self.assertIn("constraint.external.external-time-origin", judged["reason"])

    def test_an_unsatisfied_necessary_item_outweighs_an_unknown_one(self):
        signature = input_signature([signature_fact()])
        requires = {"all_of": [{"fact": "representation", "equals": "image"}, {"fact": "never.read", "equals": 1}]}
        self.assertEqual(judge_candidates(signature, [{"candidate": "method.a", "requires": requires}])[0]["state"], "unsatisfied")

    def test_a_malformed_condition_is_unknown_never_true(self):
        signature = input_signature([signature_fact()])
        for requires in (None, {}, {"all_of": []}, {"any_of": []}, {"all_of": "x"}, {"any_of": None}, {"fact": "representation"}, {"equals": "waveform"},
                         {"fact": 3, "equals": 3}, {"fact": "representation", "equals": None}, {"fact": "representation", "equals": ["waveform"]}, {"all_of": [{}]}, {"any_of": [{"all_of": []}]}, 7, "true", {"fact": "representation", "equals": "waveform", "all_of": []}):
            judged = judge_candidates(signature, [{"candidate": "method.a", "requires": requires}])
            self.assertEqual((judged[0]["state"], judged[0]["eligible"]), ("unknown", False), repr(requires))

    def test_a_malformed_candidate_list_gives_no_eligible_candidate_and_no_exception(self):
        signature = input_signature([signature_fact()])
        for candidates in (None, 3, "x", [None], [{}], [{"requires": {"fact": "representation", "equals": "waveform"}}]):
            self.assertFalse(any(judged["eligible"] for judged in judge_candidates(signature, candidates)), repr(candidates))

    def test_a_deep_condition_gives_a_refusal_and_no_exception(self):
        requires = {"fact": "representation", "equals": "waveform"}
        for _ in range(100000):
            requires = {"all_of": [requires]}
        judged = judge_candidates(input_signature([signature_fact()]), [{"candidate": "method.a", "requires": requires}])
        self.assertFalse(judged[0]["eligible"])


class RetainedInformation(Scratch):
    """A48; Sections 5.5, 8.3: methods that need traces are excluded, candidates on summaries stay."""

    TRACES = {"candidate": "method.traces", "requires": {"fact": "retention.waveform", "equals": "kept"}}
    SUMMARY = {"candidate": "method.summary", "requires": {"all_of": [{"fact": "retention.conditions_snapshot", "equals": "kept"}, {"fact": "presence", "equals": "present"}]}}

    def test_removed_traces_exclude_the_trace_method_and_keep_the_summary_one(self):
        judged = judge_candidates(only_signature(self.inspected("a.json", waveform_product(waveform="removed"))), [self.TRACES, self.SUMMARY])
        self.assertEqual([(item["candidate"], item["state"], item["eligible"]) for item in judged], [("method.traces", "unsatisfied", False), ("method.summary", "satisfied", True)])
        self.assertIn("retention.waveform", judged[0]["reason"])

    def test_kept_traces_keep_both(self):
        judged = judge_candidates(only_signature(self.inspected("a.json", waveform_product())), [self.TRACES, self.SUMMARY])
        self.assertEqual([item["eligible"] for item in judged], [True, True])

    def test_unstated_retention_excludes_nothing_and_passes_nothing(self):
        judged = judge_candidates(only_signature(self.inspected("a.json", product())), [self.TRACES])
        self.assertEqual((judged[0]["state"], judged[0]["eligible"]), ("unknown", False))


class ScoresAreNotEvidence(Scratch):
    """A49; K15: model confidence, file names and array shapes are not evidence; an extracted value stays declared until checked."""

    REQUIRED = {"fact": "sampling.time_system", "equals": "digitizer-clock"}

    def test_a_high_score_does_not_pass_a_required_gate(self):
        signature = only_signature(self.inspected("a.json", waveform_product()))
        (judged,) = judge_candidates(signature, [{"candidate": "method.a", "requires": self.REQUIRED, "score": 0.9999, "confidence": 1.0, "eligible": True, "state": "satisfied"}])
        self.assertEqual((judged["state"], judged["eligible"]), ("unknown", False))

    def test_a_score_outside_the_tested_domain_does_not_pass(self):
        declared = [{"key": "domain.tested", "value": False, "reference": "manifest:synthetic", "kind": "declaration"}]
        signature = only_signature(self.inspected("a.json", pulse_product(), declared=declared))
        (judged,) = judge_candidates(signature, [{"candidate": "method.a", "score": 0.9999, "requires": {"all_of": [self.REQUIRED, {"fact": "domain.tested", "equals": True}]}}])
        self.assertEqual((judged["state"], judged["eligible"]), ("unsatisfied", False))

    def test_scores_do_not_rank_the_answer(self):
        signature = only_signature(self.inspected("a.json", pulse_product()))
        first, second = {"candidate": "method.low", "score": 0.1, "requires": self.REQUIRED}, {"candidate": "method.high", "score": 0.9, "requires": self.REQUIRED}
        self.assertEqual([item["candidate"] for item in judge_candidates(signature, [first, second])], ["method.low", "method.high"])
        self.assertNotIn("score", judge_candidates(signature, [first])[0])

    def test_an_extracted_value_stays_declared_and_opens_no_gate(self):
        declared = [{"key": "sampling.time_system", "value": "digitizer-clock", "reference": "extraction:synthetic", "kind": "llm-extraction"}]
        signature = only_signature(self.inspected("a.json", waveform_product(), declared=declared))
        (fact,) = [item for item in signature["facts"] if item["key"] == "sampling.time_system"]
        self.assertEqual((fact["method"], fact["source"]["kind"]), ("declared", "llm-extraction"))
        self.assertIn("sampling", signature["unknown"])
        self.assertEqual(judge_candidates(signature, [{"candidate": "method.a", "requires": self.REQUIRED}])[0]["state"], "unknown")

    def test_an_extracted_representation_generates_no_candidate(self):
        """K15: it stays a declaration to check."""
        declared = [{"key": "representation", "value": "waveform", "reference": "extraction:synthetic", "kind": "llm-extraction"}]
        signature = only_signature(self.inspected("a.csv", "a,b\n1,2\n", declared=declared))
        self.assertEqual(signature["family_candidates"], [])
        self.assertIn("representation", signature["unknown"])

    def test_a_declaration_with_no_kind_is_refused(self):
        """Minor 10: no default kind, so an extracted value cannot pass as a declaration."""
        record = self.inspected("a.json", product(), declared=[{"key": "detector", "value": "silicon", "reference": "manifest:synthetic"}])
        self.assertEqual(fact_values(only_signature(record), "detector"), [])
        self.assertEqual(record["refused_declarations"][0]["reason"], "declaration-malformed")

    def test_a_reference_that_names_a_non_evidence_source_is_refused(self):
        for reference in ("file-name:x", "array-shape:x", "model-confidence:x"):
            declared = [{"key": "detector", "value": "silicon", "reference": reference, "kind": "declaration"}]
            record = self.inspected("a.json", product(), declared=declared)
            self.assertEqual(fact_values(only_signature(record), "detector"), [], reference)
            self.assertEqual(record["refused_declarations"][0]["reason"], "not-evidence", reference)

    def test_what_is_not_evidence_is_refused_visibly_and_unused(self):
        for kind in ("file-name", "array-shape", "model-confidence", "reader", "derivation", "unheard-of"):
            declared = [{"key": "detector", "value": "silicon", "reference": "guess:synthetic", "kind": kind}]
            record = self.inspected("a.json", product(), declared=declared)
            self.assertEqual(fact_values(only_signature(record), "detector"), [], kind)
            self.assertEqual([item["key"] for item in record["refused_declarations"]], ["detector"], kind)
            self.assertEqual(code_list(read_sidecar(record)), [], kind)

    def test_malformed_declarations_are_refused_visibly(self):
        for declared in ("x", [None], [{}], [{"key": "a"}], [{"key": "", "value": 1, "reference": "r", "kind": "declaration"}], [{"key": "a", "value": None, "reference": "r", "kind": "declaration"}], [{"key": "a", "value": [1], "reference": "r", "kind": "declaration"}],
                         [{"key": "a", "value": float("nan"), "reference": "r", "kind": "declaration"}], [{"key": "a", "value": 1, "reference": "", "kind": "declaration"}], [{"key": "a", "value": 1, "reference": "r", "kind": []}], [{"key": "a", "value": 1, "reference": "r"}]):
            record = self.inspected("a.json", product(), declared=declared)
            self.assertEqual(len(record["refused_declarations"]), 1, repr(declared))
            self.assertEqual(code_list(read_sidecar(record)), [], repr(declared))

    def test_a_declared_fact_keeps_its_source(self):
        declared = [{"key": "detector", "value": "synthetic-array", "reference": "manifest:synthetic", "kind": "declaration"}]
        signature = only_signature(self.inspected("a.json", product(), declared=declared))
        (fact,) = [item for item in signature["facts"] if item["key"] == "detector"]
        self.assertEqual((fact["method"], fact["source"]), ("declared", {"kind": "declaration", "reference": "manifest:synthetic", "kind": "declaration"}))
        self.assertEqual(fact["reader_version"], "not-read", "no reader stands behind a manifest's statement")
        self.assertNotIn("detector", signature["unknown"])


class QuestionsWithNoInput(Scratch):
    """A16, recognition part; Section 5.3 step 1, 14.4: a question with no input reads nothing and starts nothing."""

    def test_no_input_reads_nothing_needs_no_budget_and_is_not_a_clean_recognition(self):
        record = inspect_inputs([], None)
        self.assertEqual((record["state"], record["stop_reason"], record["budget"]), ("not-needed", None, None))
        self.assertEqual((record["signatures"], record["probes"], record["spent"]), ([], [], {"probes": 0, "bytes": 0, "seconds": 0, "memory_bytes": 0, "tools": 0}))
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_an_inspection_writes_nothing_beside_its_inputs(self):
        self.inspected("a.json", product())
        self.assertEqual([path.name for path in self.folder.iterdir()], ["a.json"])


class RecordRules(Scratch):
    """input-inspection/1 read back: an honest record passes and one altered field is refused (Sections 5.6, 5.7, K15, K17)."""

    def honest(self):
        return self.inspected("a.json", pulse_product())

    def assert_refused(self, record, code):
        self.assertIn(code, code_list(read_sidecar(record)))

    def test_a_probe_that_is_not_registered_is_refused(self):
        record = self.honest()
        record["probes"][0]["probe"] = "probe.shell"
        self.assert_refused(record, "reconstruction.inspection.unknown_probe")

    def test_a_probe_with_other_parameters_is_refused(self):
        record = self.honest()
        record["probes"][0]["parameters"] = {"byte_ceiling": 1 << 40}
        self.assert_refused(record, "reconstruction.inspection.unknown_probe")

    def test_a_reader_fact_with_no_run_behind_it_is_refused(self):
        """K15: no recognition claim without a runtime reader."""
        record = self.honest()
        record["probes"][0].update(outcome="not-run", stop_reason="no-runtime-reader", probe=None, reader=None, reader_version=None, parameters={})
        record["state"], record["stop_reason"] = "partial", "no-runtime-reader"
        self.assert_refused(record, "reconstruction.inspection.fact_without_reader")

    def test_a_clean_state_over_a_failed_probe_is_refused(self):
        record = self.inspected("a.json", "{")
        record["state"], record["stop_reason"] = "complete", None
        self.assert_refused(record, "reconstruction.inspection.state_hides_a_stop")

    def test_a_stop_with_no_reason_is_refused(self):
        record = self.inspected("a.json", "{")
        record["probes"][0]["stop_reason"] = None
        self.assert_refused(record, "reconstruction.inspection.stop_without_reason")

    def test_a_stopped_state_with_no_reason_is_refused(self):
        record = self.inspected("a.json", product(), budget=dict(BUDGET, probes=0))
        record["stop_reason"] = None
        self.assert_refused(record, "reconstruction.inspection.stop_without_reason")

    def test_hidden_cost_is_refused(self):
        record = self.honest()
        record["spent"]["bytes"] = 0
        self.assert_refused(record, "reconstruction.inspection.cost_mismatch")

    def test_hidden_time_is_refused(self):
        record = inspect_inputs([{"product": "product.hits-a", "path": self.write("a.json", product())}], BUDGET, clock=itertools.count().__next__)
        self.assertEqual(code_list(read_sidecar(record)), [])
        record["spent"]["seconds"] = 0
        self.assert_refused(record, "reconstruction.inspection.cost_mismatch")

    def test_a_cost_on_a_probe_that_did_not_run_is_refused(self):
        record = self.inspected("a.root", b"synthetic")
        record["probes"][0]["cost"]["bytes_read"] = 9
        self.assert_refused(record, "reconstruction.inspection.cost_mismatch")

    def test_reading_with_no_declared_budget_is_refused(self):
        """K17."""
        record = self.honest()
        record["budget"] = None
        self.assert_refused(record, "reconstruction.inspection.over_budget")

    def test_spending_past_the_budget_is_refused(self):
        record = self.honest()
        record["budget"]["probes"] = 0
        self.assert_refused(record, "reconstruction.inspection.over_budget")

    def test_a_signature_conflict_with_no_named_probe_is_refused(self):
        record = self.inspected("a.json", count_product(), declared=[{"key": "representation", "value": "image", "reference": "manifest:synthetic", "kind": "declaration"}])
        record["conflicts"] = []
        self.assert_refused(record, "reconstruction.inspection.conflict_without_probe")

    def test_a_signature_the_reader_refuses_is_refused(self):
        record = self.honest()
        record["signatures"][0]["required_extensions"] = ["reconstruction:future-semantics-v9"]
        self.assert_refused(record, "reconstruction.reader.unknown_required_extension")
        record = self.honest()
        record["signatures"][0]["facts"][0]["source"]["kind"] = "file-name"
        self.assert_refused(record, "reconstruction.signature.not_evidence")

    def test_an_inspection_that_needed_nothing_holds_nothing(self):
        record = inspect_inputs([], None)
        record["probes"] = self.honest()["probes"]
        self.assertTrue(code_list(read_sidecar(record)))

    def test_a_record_the_reader_would_refuse_is_never_returned(self):
        """Fail closed: a fact the reader refuses gives a stopped record with no fact and its cost kept, with no exception on the way."""
        def not_evidence(key, value, scope, reference, **fields):
            return {"key": key, "value": value, "scope": scope, "source": {"kind": "file-name", "reference": reference}, "reader_version": "1", "method": "observed", "validity": "x"}
        with mock.patch("contracts.input_inspector._fact", not_evidence):
            record = self.inspected("a.json", product())
        self.assertEqual((record["state"], record["stop_reason"], record["signatures"]), ("stopped", "record-refused", []))
        self.assertGreater(record["spent"]["bytes"], 0, "minor 8: a fault does not erase the cost")
        self.assertEqual(len(record["probes"]), 1)
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_fault_while_assembling_keeps_the_cost(self):
        with mock.patch("contracts.input_inspector._conflicts", side_effect=TypeError("synthetic fault")):
            record = self.inspected("a.json", product())
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "record-refused"))
        self.assertGreater(record["spent"]["bytes"], 0)
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_signature_of_the_wrong_shape_gives_its_schema_finding_alone(self):
        record = self.honest()
        del record["signatures"][0]["facts"][0]["source"]
        codes = code_list(read_sidecar(record))
        self.assertIn("schema.required", codes)
        self.assertNotIn("reconstruction.reader.malformed", codes)

    def test_a_product_read_list_that_does_not_fit_the_probes_is_refused(self):
        record = self.honest()
        record["products_read"], record["products_unread"] = [], record["products_read"]
        self.assert_refused(record, "reconstruction.inspection.products_mismatch")
        record = self.inspected("a.root", b"synthetic")
        record["products_read"], record["products_unread"] = record["products_unread"], []
        self.assert_refused(record, "reconstruction.inspection.products_mismatch")

    def test_a_scope_of_nothing_on_a_probe_that_read_is_refused(self):
        record = self.honest()
        record["probes"][0]["read_scope"] = "nothing"
        self.assert_refused(record, "reconstruction.inspection.scope_mismatch")
        record = self.inspected("a.root", b"synthetic")
        record["probes"][0]["read_scope"] = "whole file"
        self.assert_refused(record, "reconstruction.inspection.scope_mismatch")

    def test_complete_with_no_probe_is_refused(self):
        record = self.honest()
        record["probes"], record["products_read"] = [], []
        record["spent"].update(probes=0, bytes=0, tools=0)
        self.assert_refused(record, "reconstruction.inspection.state_hides_a_stop")

    def test_complete_over_an_open_conflict_is_refused(self):
        """M3: a conflict is never a clean end."""
        record = self.inspected("a.json", count_product(), declared=[{"key": "representation", "value": "image", "reference": "manifest:synthetic", "kind": "declaration"}])
        self.assertEqual((record["state"], record["stop_reason"]), ("partial", "conflict-unresolved"))
        record["state"], record["stop_reason"] = "complete", None
        self.assert_refused(record, "reconstruction.inspection.state_hides_a_stop")

    def test_another_reader_version_is_refused(self):
        """Minor 13; Section 5.6 item 2: the version read back is the registered one."""
        record = self.honest()
        record["probes"][0]["reader_version"] = "9"
        self.assert_refused(record, "reconstruction.inspection.unknown_probe")

    def test_a_returned_record_cannot_change_the_fixed_parameters(self):
        """Minor 3."""
        self.honest()["probes"][0]["parameters"]["byte_ceiling"] = 1
        self.assertEqual(PROBES[JSON_PROBE]["parameters"]["byte_ceiling"], 16 * 1024 * 1024)


class RetentionAgainstDeclarations(Scratch):
    """M4; A46, A48: a declared waveform on a product that states its traces were removed is a conflict."""

    WAVEFORM = [{"key": "representation", "value": "waveform", "reference": "manifest:synthetic", "kind": "declaration"}]

    def test_a_declared_waveform_with_removed_traces_is_a_conflict(self):
        record = self.inspected("a.json", waveform_product(waveform="removed"), declared=self.WAVEFORM)
        signature = only_signature(record)
        self.assertEqual(signature["conflicts"], ["representation"])
        self.assertEqual((record["state"], record["stop_reason"]), ("partial", "conflict-unresolved"))
        self.assertEqual(sorted(str(item["value"]) for item in record["conflicts"][0]["values"]), ["removed", "waveform"])
        self.assertEqual(code_list(read_sidecar(record)), [])
        (judged,) = judge_candidates(signature, [{"candidate": "method.a", "requires": {"fact": "representation", "equals": "waveform"}}])
        self.assertEqual((judged["state"], judged["eligible"]), ("conflicting", False))

    def test_a_declared_waveform_with_kept_or_unstated_traces_is_no_conflict(self):
        self.assertEqual(self.inspected("a.json", waveform_product(), declared=self.WAVEFORM)["conflicts"], [])
        self.assertEqual(self.inspected("a.json", product(), declared=self.WAVEFORM)["conflicts"], [])
        self.assertEqual(self.inspected("a.json", waveform_product(waveform="reproducible"), declared=self.WAVEFORM)["conflicts"], [])

    def test_another_declared_label_on_removed_traces_is_no_conflict(self):
        declared = [dict(self.WAVEFORM[0], value="count")]
        self.assertEqual(self.inspected("a.json", waveform_product(waveform="removed"), declared=declared)["conflicts"], [])

    def test_the_same_declaration_on_a_list_file_is_a_conflict_too(self):
        record = self.inspected("a.json", [waveform_product(waveform="removed")], label="file.a", declared=self.WAVEFORM)
        self.assertEqual([item["key"] for item in record["conflicts"]], ["representation"])


class BudgetBoundsTheWork(Scratch):
    """M1, M2; Section 5.6 item 5: read, time, memory, tool and probe-count limits; A59; plan K17 row."""

    def many_products(self):
        return [{"product": f"product.{name}", "path": self.write(f"{name}.json", product(f"product.{name}"))} for name in "abc"]

    def test_a_list_over_the_document_ceiling_is_not_read_one_by_one(self):
        with mock.patch("contracts.input_inspector.read_document", wraps=input_inspector.read_document) as reads:
            record = self.inspected("a.json", [0] * (PROBES[JSON_PROBE]["parameters"]["document_ceiling"] + 1))
        self.assertEqual(record["probes"][0]["stop_reason"], "json.document-ceiling")
        self.assertNotIn(0, [call.args[0] for call in reads.call_args_list], "no element reached the reader")
        self.assertEqual(len(record["signatures"]), 1)

    def test_refused_documents_share_one_signature_and_are_counted(self):
        record = self.inspected("a.json", [0] * 500)
        self.assertEqual(len(record["signatures"]), 1)
        self.assertEqual(record["probes"][0]["documents_refused"], 500)
        self.assertLess(len(json.dumps(record)), 5000)

    def test_the_whole_inspection_is_charged_and_not_only_the_reads(self):
        ticks = itertools.count()
        record = inspect_inputs(self.many_products(), dict(BUDGET, seconds=10**9), clock=lambda: float(next(ticks)))
        self.assertGreater(record["spent"]["seconds"], sum(probe["cost"]["seconds"] for probe in record["probes"]))
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_slow_parse_stops_during_the_probe(self):
        """The clock moves only when the watch looks at it, so the stop comes from inside read_document, not from after it."""
        ticks = itertools.count()
        document = product(objects=[measurement(index) for index in range(2000)])
        with mock.patch("contracts.input_inspector._product_facts", wraps=input_inspector._product_facts) as read_on:
            record = self.inspected_with(document, dict(BUDGET, seconds=5), lambda: float(next(ticks)))
        read_on.assert_not_called()
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-seconds"))
        self.assertEqual((record["probes"][0]["outcome"], record["probes"][0]["stop_reason"]), ("failed", "budget-seconds"))
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertIn("container", only_signature(record)["unknown"])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def inspected_with(self, document, budget, clock):
        return inspect_inputs([{"product": document["product_id"], "path": self.write("a.json", document)}], budget, clock=clock)

    def test_an_overrun_no_check_could_interrupt_ends_stopped_with_no_fact(self):
        """M2: a stalled read cannot be interrupted; it is caught as soon as it returns."""
        moment = [0.0]
        real = input_inspector._read_bounded

        def stalled(*arguments):
            moment[0] = 100.0
            return real(*arguments)
        with mock.patch("contracts.input_inspector._read_bounded", stalled):
            record = self.inspected_with(pulse_product(), dict(BUDGET, seconds=1), lambda: moment[0])
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-seconds"))
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertGreaterEqual(record["spent"]["seconds"], 100)
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_an_overrun_after_the_read_drops_the_facts(self):
        """One C call the watch never entered: nothing looks until the probe has ended."""
        moment = [0.0]
        real = input_inspector._document_report

        def stalled(*arguments):
            moment[0] = 100.0
            return real(*arguments)
        with mock.patch("contracts.input_inspector._document_report", stalled), mock.patch("contracts.input_inspector.WATCH_INTERVAL", 10**9):
            record = self.inspected_with(pulse_product(), dict(BUDGET, seconds=1), lambda: moment[0])
        self.assertEqual((record["state"], record["stop_reason"], record["probes"][0]["stop_reason"]), ("stopped", "budget-seconds", "budget-seconds"))
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_an_overrun_in_the_last_step_ends_stopped(self):
        moment = [0.0]
        real = input_inspector._conflicts

        def stalled(facts):
            moment[0] = 100.0
            return real(facts)
        with mock.patch("contracts.input_inspector._conflicts", stalled), mock.patch("contracts.input_inspector.WATCH_INTERVAL", 10**9):
            record = self.inspected_with(pulse_product(), dict(BUDGET, seconds=1), lambda: moment[0])
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-seconds"))
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_stop_during_assembly_keeps_the_cost_and_every_product_unknown(self):
        with mock.patch("contracts.input_inspector._conflicts", side_effect=input_inspector._BudgetStop("budget-seconds")):
            record = self.inspected("a.json", pulse_product())
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-seconds"))
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertGreater(record["spent"]["bytes"], 0)

    def test_a_clean_record_over_its_seconds_is_refused(self):
        for state, reason in (("complete", None), ("partial", "input-unreadable"), ("stopped", "budget-probes")):
            record = self.inspected("a.json", product())
            record["spent"]["seconds"] = BUDGET["seconds"] + 1
            record["state"], record["stop_reason"] = state, reason
            self.assertIn("reconstruction.inspection.over_budget", code_list(read_sidecar(record)), state)

    def test_a_clean_record_over_its_memory_is_refused(self):
        record = self.inspected("a.json", product())
        record["spent"]["memory_bytes"] = BUDGET["memory_bytes"] + 1
        self.assertIn("reconstruction.inspection.over_budget", code_list(read_sidecar(record)))

    def rising_memory(self):
        """A peak that rises by 1000 at every look, so memory tests do not depend on the test process."""
        return mock.patch("contracts.input_inspector._peak_resident_bytes", side_effect=itertools.count(0, 1000))

    def test_an_honest_overrun_stated_as_a_stop_is_accepted(self):
        with self.rising_memory():
            record = self.inspected("a.json", product(), budget=dict(BUDGET, memory_bytes=1))
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-memory"))
        self.assertGreater(record["spent"]["memory_bytes"], 1)
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_memory_is_measured_and_visible(self):
        with self.rising_memory():
            record = self.inspected("a.json", product(objects=[measurement(index) for index in range(200)]))
        self.assertGreater(record["spent"]["memory_bytes"], 0)
        self.assertGreater(record["probes"][0]["cost"]["memory_bytes"], 0)
        self.assertEqual(record["state"], "complete")

    def test_a_memory_budget_stops_during_the_probe_with_no_fact(self):
        with self.rising_memory(), mock.patch("contracts.input_inspector._product_facts", wraps=input_inspector._product_facts) as read_on:
            record = self.inspected("a.json", product(objects=[measurement(index) for index in range(2000)]), budget=dict(BUDGET, memory_bytes=5000))
        read_on.assert_not_called()
        self.assertEqual((record["state"], record["stop_reason"], record["probes"][0]["stop_reason"]), ("stopped", "budget-memory", "budget-memory"))
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_memory_limit_that_cannot_be_measured_stops_at_once(self):
        with mock.patch("contracts.input_inspector._peak_resident_bytes", return_value=None):
            record = self.inspected("a.json", product())
        self.assertEqual((record["state"], record["stop_reason"], record["spent"]["bytes"]), ("stopped", "budget-memory", 0))
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_the_real_peak_is_read_in_bytes(self):
        self.assertGreater(input_inspector._peak_resident_bytes(), 1024 * 1024)  # getrusage, or the Windows peak working set

    def test_the_peak_comes_from_getrusage_or_the_windows_counter(self):
        self.assertEqual(input_inspector.HAS_GETRUSAGE, sys.platform != "win32")
        self.assertEqual(input_inspector._WINDOWS_PEAK is not None, sys.platform == "win32")
        with mock.patch.object(input_inspector, "HAS_GETRUSAGE", False), mock.patch.object(input_inspector, "_WINDOWS_PEAK", lambda: 5 * 1024 * 1024):
            self.assertEqual(input_inspector._peak_resident_bytes(), 5 * 1024 * 1024)
        with mock.patch.object(input_inspector, "HAS_GETRUSAGE", False), mock.patch.object(input_inspector, "_WINDOWS_PEAK", None):
            self.assertIsNone(input_inspector._peak_resident_bytes())  # neither: a declared memory limit then stops (budget-memory)
            record = self.inspected("a.json", product())
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-memory"))

    def test_running_out_of_memory_is_a_stop_and_no_exception(self):
        with mock.patch("contracts.input_inspector.json.loads", side_effect=MemoryError):
            record = self.inspected("a.json", product())
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-memory"))
        self.assertEqual((record["probes"][0]["outcome"], record["probes"][0]["stop_reason"]), ("failed", "budget-memory"))
        self.assertEqual(only_signature(record)["facts"], [])
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_a_tool_budget_stops_a_second_reader(self):
        inputs = [{"product": "product.a", "path": self.write("a.json", product("product.a"))}, {"product": "product.b", "path": self.write("b.csv", HONEST_CSV)}]
        record = inspect_inputs(inputs, dict(BUDGET, tools=1))
        self.assertEqual((record["state"], record["stop_reason"], record["spent"]["tools"]), ("stopped", "budget-tools", 1))
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_one_reader_used_twice_is_one_tool(self):
        record = inspect_inputs(self.many_products(), dict(BUDGET, tools=1))
        self.assertEqual((record["state"], record["spent"]["tools"]), ("complete", 1))

    def test_spending_more_tools_than_declared_is_refused(self):
        record = self.inspected("a.json", product())
        record["budget"]["tools"] = 0
        self.assertIn("reconstruction.inspection.over_budget", code_list(read_sidecar(record)))
        record = self.inspected("a.json", product())
        record["spent"]["tools"] = 0
        self.assertIn("reconstruction.inspection.cost_mismatch", code_list(read_sidecar(record)))

    def test_a_seconds_limit_is_reached_at_equality(self):
        record = self.inspected("a.json", product(), budget=dict(BUDGET, seconds=0))
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-seconds"))

    def test_a_clock_that_steps_back_charges_no_negative_cost(self):
        steps = itertools.count(1000, -1)
        record = inspect_inputs([{"product": "product.hits-a", "path": self.write("a.json", product())}], BUDGET, clock=lambda: float(next(steps)))
        self.assertEqual(record["state"], "complete")
        self.assertEqual(code_list(read_sidecar(record)), [])

    def test_the_watch_leaves_no_trace_on_the_process(self):
        self.inspected("a.json", product())
        self.assertIsNone(sys.getprofile())

    def test_the_watch_keeps_what_the_caller_had_running(self):
        def caller_profile(frame, event, argument):
            return None
        sys.setprofile(caller_profile)
        try:
            self.inspected("a.json", product())
            self.assertIs(sys.getprofile(), caller_profile)
        finally:
            sys.setprofile(None)

    def test_many_payload_slots_are_read(self):
        """M1: an honest wide product, and it is the seconds budget that bounds the work after the read."""
        document = product(conditions_used=[dict(used_payload(calibration_payload()), slot=f"slot-{index}") for index in range(500)])
        self.assertEqual(self.inspected("a.json", document)["state"], "complete")


COLD_PROCESS = """
import json, sys
sys.path.insert(0, sys.argv[1])
from contracts import input_inspector
assert "numpy" not in sys.modules and "contracts.reconstruction" not in sys.modules, "this process must be cold"
if sys.argv[4] == "import-under-the-watch":
    input_inspector._load_readers = lambda: True  # the import then runs inside the watch: a stop must wait for it to end
ample = {"probes": 1, "bytes": 10**8, "seconds": 600, "memory_bytes": 10**12, "tools": 1}
inputs = [{"product": "product.pulse", "path": sys.argv[2]}]
first = input_inspector.inspect_inputs(inputs, json.loads(sys.argv[3]))
second = input_inspector.inspect_inputs(inputs, ample)
print(json.dumps({"first": [first["state"], first["stop_reason"]], "second": [second["state"], second["stop_reason"]], "facts": sum(len(item["facts"]) for item in second["signatures"])}))
"""


class ConflictsAreNeverHidden(Scratch):
    """The user's ruling (decisions.md, "T14 rulings"): a conflict on any branch of an OR gives `conflicting`, even if another branch would pass.
    Conflict outranks unsatisfied at every level of a condition, so an AND inside a branch cannot hide one (C3 review, M1)."""

    PASSING = {"fact": "passes", "equals": True}
    FAILING = {"fact": "fails", "equals": True}
    TORN = {"fact": "torn", "equals": True}

    def state_of(self, condition):
        facts = [signature_fact("passes", True), signature_fact("fails", False), signature_fact("torn", True, scope="product.pulse")]
        signature = input_signature(facts, unknown=[], conflicts=["torn"])
        return judge_candidates(signature, [{"candidate": "m", "requires": condition}])[0]

    def test_the_review_probe_on_real_facts(self):
        """DS2's shape: external available, internal unqualified, and a declaration that disputes `sufficient`."""
        document = constraint_product(constraint_witness(external="available", internal="unqualified", sufficient=False))
        dispute = [{"key": "constraint.internal.internal-time-constraint.sufficient", "value": True, "reference": "manifest:artificial", "kind": "declaration"}]
        signature = only_signature(self.inspected("a.json", document, declared=dispute))
        internal = {"all_of": [{"fact": "constraint.internal.internal-time-constraint", "equals": "qualified"}, {"fact": "constraint.internal.internal-time-constraint.sufficient", "equals": True}]}
        external = {"fact": "constraint.external.external-time-origin", "equals": "available"}
        schema = {"fact": "product_schema", "equals": "reconstruction-product/1"}
        for branches in ([external, internal], [internal, external]):
            (judged,) = judge_candidates(signature, [{"candidate": "m", "requires": {"all_of": [schema, {"any_of": branches}]}}])
            self.assertEqual((judged["state"], judged["eligible"]), ("conflicting", False))
            self.assertIn("constraint.internal.internal-time-constraint.sufficient", judged["open"])

    def test_every_nesting_keeps_the_conflict(self):
        for condition in ({"any_of": [self.PASSING, {"all_of": [self.FAILING, self.TORN]}]},
                          {"any_of": [{"all_of": [self.TORN, self.FAILING]}, self.PASSING]},
                          {"all_of": [self.PASSING, {"any_of": [self.TORN, self.PASSING]}]},
                          {"all_of": [self.FAILING, self.TORN]},
                          {"any_of": [self.PASSING, {"all_of": [self.FAILING, {"any_of": [self.PASSING, {"all_of": [self.FAILING, self.TORN]}]}]}]},
                          {"all_of": [self.PASSING, {"any_of": [self.PASSING, {"all_of": [self.FAILING, {"any_of": [self.TORN, self.FAILING]}]}]}]}):
            self.assertEqual(self.state_of(condition)["state"], "conflicting", condition)

    def test_an_unsatisfied_item_stays_visible_beside_a_conflict(self):
        self.assertIn("fails", self.state_of({"all_of": [self.FAILING, self.TORN]})["reason"])

    def test_with_no_conflict_the_states_keep_their_order(self):
        """Section 5.8: one unsatisfied item in AND excludes; OR passes on a branch fully satisfied."""
        unknown = {"fact": "not-stated", "equals": True}
        for condition, state in (({"all_of": [self.FAILING, unknown]}, "unsatisfied"), ({"any_of": [self.FAILING, unknown]}, "unknown"), ({"any_of": [self.PASSING, unknown]}, "satisfied"),
                                 ({"any_of": [self.PASSING, {"all_of": [self.FAILING, unknown]}]}, "satisfied"), ({"all_of": [self.PASSING, {"any_of": [self.FAILING, self.PASSING]}]}, "satisfied")):
            self.assertEqual(self.state_of(condition)["state"], state, condition)


class FactScopes(Scratch):
    """Section 5.5, K15: a signature is per product and scope, and different scopes of one product are multi-label. DS2: a scope conflict on the
    schema or on the constraint used is resolved first. The inspector keeps `constraint.` facts at the owner's scope, where _conflicts sees them, and
    `product_schema` at the scope of each file, so two files under one label are two labels, not a conflict (C3 re-review, R1)."""

    CONDITION = {"fact": "constraint.internal.a", "equals": "qualified"}

    def judged(self, facts, condition=None):
        return judge_candidates(input_signature(facts, unknown=[]), [{"candidate": "m", "requires": condition or self.CONDITION}])[0]

    def test_a_fact_of_another_product_says_nothing_here(self):
        self.assertEqual(self.judged([signature_fact("constraint.internal.a", "qualified", scope="another.product/other-window")])["state"], "unknown")

    def test_a_narrower_or_wider_scope_of_this_product_counts(self):
        for scope in ("product.pulse", "product.pulse/block.counts", "file"):
            signature = input_signature([signature_fact("constraint.internal.a", "qualified", scope=scope)], unknown=[], scope={"product": "file/product.pulse" if scope == "file" else "product.pulse", "window": "whole product"})
            self.assertEqual(judge_candidates(signature, [{"candidate": "m", "requires": self.CONDITION}])[0]["state"], "satisfied", scope)

    def test_two_values_of_a_constraint_in_sibling_scopes_conflict(self):
        facts = [signature_fact("constraint.internal.a", "qualified", scope="product.pulse/window-1"), signature_fact("constraint.internal.a", "unqualified", scope="product.pulse/window-2")]
        self.assertEqual(self.judged(facts)["state"], "conflicting")

    def two_files(self, *declared):
        """A product and the payload it used, under one label: the real inspector, not a hand-written signature."""
        product_path, payload_path = self.write("a.json", product("product.hits-a", [measurement(0)])), self.write("b.json", calibration_payload())
        return inspect_inputs([{"product": "product.hits-a", "path": product_path, "declared": list(declared)}, {"product": "product.hits-a", "path": payload_path}], BUDGET, clock=fixed_clock)

    def test_a_product_beside_its_payload_is_no_conflict(self):
        """R1: the result at the base of this round stays. Both labels hold, as the inspection says."""
        record = self.two_files()
        self.assertEqual((record["state"], record["conflicts"]), ("complete", []))
        signature = only_signature(record)
        for schema in ("reconstruction-product/1", "conditions-payload/1"):
            self.assertEqual(judge_candidates(signature, [{"candidate": "m", "requires": {"fact": "product_schema", "equals": schema}}])[0]["state"], "satisfied", schema)

    def test_a_product_beside_an_envelope_artifact_is_no_conflict(self):
        artifact = json.loads((ROOT / "contracts/fixtures/artifacts/valid/response_v28.json").read_text(encoding="utf-8"))
        paths = self.write("a.json", product("product.hits-a", [measurement(0)])), self.write("b.json", artifact)
        record = inspect_inputs([{"product": "product.hits-a", "path": path} for path in paths], BUDGET, clock=fixed_clock)
        self.assertEqual(record["conflicts"], [])
        self.assertEqual(judge_candidates(only_signature(record), [{"candidate": "m", "requires": {"fact": "product_schema", "equals": "reconstruction-product/1"}}])[0]["state"], "satisfied")

    def test_a_genuine_schema_conflict_in_one_owner_still_conflicts(self):
        """DS2. A statement about the product that matches nothing read in its files."""
        record = self.two_files({"key": "product_schema", "value": "another-schema", "reference": "manifest:artificial", "kind": "declaration"})
        self.assertEqual(judge_candidates(only_signature(record), [{"candidate": "m", "requires": {"fact": "product_schema", "equals": "reconstruction-product/1"}}])[0]["state"], "conflicting")

    def test_a_hand_written_schema_in_two_scopes_is_multi_label_as_from_the_inspector(self):
        facts = [signature_fact("product_schema", "schema-a", scope="product.pulse/window-1"), signature_fact("product_schema", "schema-b", scope="product.pulse/window-2")]
        self.assertEqual(self.judged(facts, {"fact": "product_schema", "equals": "schema-a"})["state"], "satisfied")

    def test_two_values_of_a_constraint_in_two_files_of_one_product_conflict_through_the_inspector(self):
        """The rule the reader of a record can see: both values at the owner's scope, listed by the inspection."""
        first, second = constraint_product(), constraint_product(constraint_witness(external="available", internal="unqualified", sufficient=False))
        paths = self.write("a.json", first), self.write("b.json", second)
        record = inspect_inputs([{"product": first["product_id"], "path": path} for path in paths], BUDGET, clock=fixed_clock)
        self.assertIn("constraint.internal.internal-time-constraint", [item["key"] for item in record["conflicts"]])
        self.assertEqual(judge_candidates(only_signature(record), [{"candidate": "m", "requires": {"fact": "constraint.internal.internal-time-constraint", "equals": "qualified"}}])[0]["state"], "conflicting")

    def test_two_labels_in_sibling_scopes_stay_multi_label(self):
        facts = [signature_fact("representation", "count", scope="product.pulse/block.counts"), signature_fact("representation", "waveform", scope="product.pulse/block.retention")]
        self.assertEqual(self.judged(facts, {"fact": "representation", "equals": "waveform"})["state"], "satisfied")


class ColdProcess(Scratch):
    """N1: the test module imports contracts.reconstruction first, so only a fresh process can show the first read. A stop must leave
    no half-imported module: a wrong answer for the life of the process, or an exception, is worse than the overrun."""

    def run_cold(self, budget, mode):
        ample = {"probes": 1, "bytes": 10**8, "seconds": 600, "memory_bytes": 10**12, "tools": 1}
        path = self.write("a.json", pulse_product())
        finished = subprocess.run([sys.executable, "-c", COLD_PROCESS, str(ROOT), path, json.dumps(dict(ample, **budget)), mode], capture_output=True, text=True, timeout=25,
                                  env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(finished.returncode, 0, finished.stderr[-800:])
        return json.loads(finished.stdout)

    def assert_second_read_is_clean(self, reading, budget):
        self.assertEqual(reading["second"], ["complete", None], budget)
        self.assertGreater(reading["facts"], 10, budget)

    def test_a_small_budget_on_the_first_read_is_honest_and_the_next_read_is_clean(self):
        """The reviewer's budgets. The import is no longer charged, so a read of a small file can fit them; a stop, if any, is a budget stop."""
        for budget in ({"memory_bytes": 3_000_000}, {"memory_bytes": 5_000_000}, {"memory_bytes": 10_000_000}, {"seconds": 0.02}, {"seconds": 0.05}):
            reading = self.run_cold(budget, "as-shipped")
            self.assertIn(reading["first"][0], ("complete", "stopped"), budget)
            if reading["first"][0] == "stopped":
                self.assertIn(reading["first"][1], ("budget-seconds", "budget-memory"), budget)
            self.assert_second_read_is_clean(reading, budget)

    def test_a_certain_stop_on_the_first_read_leaves_the_next_read_clean(self):
        reading = self.run_cold({"seconds": 0}, "as-shipped")
        self.assertEqual(reading["first"], ["stopped", "budget-seconds"])
        self.assert_second_read_is_clean(reading, "seconds 0")

    def test_a_stop_never_lands_inside_a_first_time_import(self):
        """With the preload taken away the import runs under the watch and passes these limits: the stop waits for its end."""
        reading = self.run_cold({"seconds": 0.02}, "import-under-the-watch")
        self.assertEqual(reading["first"], ["stopped", "budget-seconds"], "the import outlasts this limit on any host")
        self.assert_second_read_is_clean(reading, "seconds")
        for budget in ({"memory_bytes": 3_000_000}, {"memory_bytes": 5_000_000}):  # how far the peak rises depends on the allocator
            reading = self.run_cold(budget, "import-under-the-watch")
            self.assertIn(reading["first"], (["stopped", "budget-memory"], ["complete", None]), budget)
            self.assert_second_read_is_clean(reading, budget)

    def test_readers_that_cannot_be_imported_give_a_stop_and_no_exception(self):
        with mock.patch.dict(sys.modules, {"contracts.validate": None}):
            record = self.inspected("a.json", product())
        self.assertEqual((record["state"], record["stop_reason"], record["spent"]["bytes"]), ("stopped", "readers-unavailable", 0))
        self.assertEqual(code_list(read_sidecar(record)), [])


class RereviewFindings(Scratch):
    """Minors of the re-review: one defect each on otherwise valid input."""

    def test_the_watch_returns_after_python_has_unset_it(self):
        """Minor 1: Python unsets a profile function that fails, as at the stack limit; the next document re-arms it."""
        seen = []
        real = input_inspector._document_report

        def spy(document):
            seen.append(sys.getprofile())
            answer = real(document)
            sys.setprofile(None)
            return answer
        with mock.patch("contracts.input_inspector._document_report", spy):
            self.inspected("a.json", [pulse_product(), count_product()], label="file.a")
        self.assertEqual(len(seen), 2)
        self.assertTrue(all(watch is not None for watch in seen))

    def test_a_document_at_the_stack_limit_is_refused_and_the_next_is_read(self):
        text = '[{"schema": "reconstruction-product/1", "x": ' + "[" * 1500 + "]" * 1500 + "}, " + json.dumps(pulse_product()) + "]"
        record = self.inspected("a.json", text, label="file.a")
        self.assertEqual(record["probes"][0]["outcome"], "partial")
        self.assertEqual(record["probes"][0]["documents_refused"], 1)

    def test_a_list_stops_between_documents_when_the_limit_has_passed(self):
        moment = [0.0]
        real = input_inspector._document_report

        def stalled(document):
            moment[0] += 10.0
            return real(document)
        path = self.write("a.json", [pulse_product(), count_product(), waveform_product()])
        with mock.patch("contracts.input_inspector._document_report", side_effect=stalled) as reads, mock.patch("contracts.input_inspector.WATCH_INTERVAL", 10**9):
            record = inspect_inputs([{"product": "file.a", "path": path}], dict(BUDGET, seconds=5), clock=lambda: moment[0])
        self.assertEqual(reads.call_count, 1)
        self.assertEqual((record["state"], record["stop_reason"]), ("stopped", "budget-seconds"))

    def test_a_product_id_on_an_artifact_is_never_used(self):
        """Minor 3: an envelope is open, so that key is not validated: not as a fact, and not as an owner."""
        document = dict(tracked_artifact(), product_id="product.other")
        signature = only_signature(self.inspected("a.json", document, label="product.a"))
        self.assertEqual(sorted(fact["key"] for fact in signature["facts"]), ["artifact_type", "container", "product_schema"])
        for hostile in ({"a": [1]}, "x" * 5000, "a/b"):
            record = self.inspected("a.json", [dict(tracked_artifact(), product_id=hostile)], label="file.a")
            self.assertEqual(only_signature(record)["scope"]["product"], "file.a/element.0", repr(hostile)[:20])

    def test_a_list_product_named_refused_meets_its_declaration(self):
        """Minor 3: M3 again for this one name."""
        document = dict(pulse_product(), product_id="refused")
        declared = [{"key": "sampling.time_system", "value": "gps", "reference": "manifest:synthetic", "kind": "declaration"}]
        record = self.inspected("a.json", [document], label="file.a", declared=declared)
        self.assertEqual([item["key"] for item in record["conflicts"]], ["sampling.time_system"])
        self.assertEqual(record["state"], "partial")
        self.assertEqual(judge_candidates(only_signature(record), [{"candidate": "m", "requires": {"fact": "sampling.time_system", "equals": "digitizer-clock"}}])[0]["state"], "conflicting")

    def test_a_required_extension_on_an_artifact_stops_it(self):
        """Minor 4; K13."""
        future = ["reconstruction:future-semantics-v9"]
        top = dict(tracked_artifact(), required_extensions=future)
        inner = tracked_artifact()
        inner["extension"] = dict(inner["extension"], required_extensions=future)
        for document in (top, inner):
            record = self.inspected("a.json", document)
            self.assertEqual(only_signature(record)["facts"], [])
            self.assertEqual(record["probes"][0]["stop_reason"], "reconstruction.reader.unknown_required_extension")
        self.assertEqual(self.inspected("a.json", dict(tracked_artifact(), required_extensions=[]))["state"], "complete")

    def test_a_limit_passed_on_the_last_tick_never_gives_a_record_the_reader_refuses(self):
        """Minor 6: one reading of the clock decides and charges."""
        readings = iter((0.0, 5.0, 6.0, 7.0))
        spending = input_inspector._Spending(dict(BUDGET, seconds=5.5), lambda: next(readings))
        closed = input_inspector._closed({"state": "complete", "stop_reason": None}, spending)
        self.assertEqual((closed["state"], spending.spent["seconds"]), ("complete", 5.0))
        for limit in range(1, 30):
            ticks = itertools.count()
            record = inspect_inputs([{"product": "product.hits-a", "path": self.write("a.json", product())}], dict(BUDGET, seconds=limit + 0.5), clock=lambda: float(next(ticks)))
            self.assertEqual(code_list(read_sidecar(record)), [], limit)

    @unittest.skipUnless(os.path.isdir("/proc/self/fd"), "needs /proc")
    def test_a_stop_leaves_no_descriptor_open(self):
        """Minor 7."""
        path = self.write("a.json", product())
        before = len(os.listdir("/proc/self/fd"))
        with mock.patch("contracts.input_inspector.WATCH_INTERVAL", 1):
            for limit in range(0, 150):
                ticks = itertools.count()
                inspect_inputs([{"product": "product.hits-a", "path": path}], dict(BUDGET, seconds=limit), clock=lambda: float(next(ticks)))
        self.assertEqual(len(os.listdir("/proc/self/fd")), before)

    def test_a_mixed_list_reports_the_k13_stop_first(self):
        """Minor 8: "stop explicitly"."""
        future = product(required_extensions=["reconstruction:future-semantics-v9"])
        record = self.inspected("a.json", [{"a": 1}, future], label="file.a")
        self.assertEqual(record["probes"][0]["stop_reason"], "reconstruction.reader.unknown_required_extension")
        self.assertEqual(record["probes"][0]["documents_refused"], 2)

    def test_tracked_profile_and_example_files_keep_the_survey_invariants(self):
        """Minor 9: invariants, not counts. Three facts, or the container alone, or none and only for want of a profile's vocabulary."""
        found = sorted(path for top in ("profiles", "examples") for path in (ROOT / top).rglob("*.json"))[::4]
        self.assertGreater(len(found), 100)
        stopped_for_vocabulary = 0
        for path in found:
            record = inspect_inputs([{"product": "product.a", "path": str(path)}], BUDGET)
            self.assertEqual(code_list(read_sidecar(record)), [], path.name)
            keys = sorted({fact["key"] for signature in record["signatures"] for fact in signature["facts"]})
            self.assertIn(keys, ([], ["container"], ["artifact_type", "container", "product_schema"]), path.name)
            if not keys:
                self.assertEqual(record["stop_reason"], "vocab.unknown_term", path.name)
                stopped_for_vocabulary += 1
        self.assertLess(stopped_for_vocabulary, len(found) / 10)


class FindingsFixedOneByOne(Scratch):
    """Review minors and survivors: each is one defect on otherwise valid input."""

    def signature(self, facts, **fields):
        return input_signature(facts, **fields)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "no FIFO on this platform (Windows): nothing can be swapped in to block a read")
    def test_a_pipe_swapped_in_after_the_stat_does_not_block(self):
        pipe = self.folder / "pipe.json"
        os.mkfifo(pipe)
        real = os.stat
        regular = real(__file__)
        with mock.patch("contracts.input_inspector.os.stat", lambda target: regular if str(target) == str(pipe) else real(target)):
            record = inspect_inputs([{"product": "product.a", "path": str(pipe)}], BUDGET)
        self.assertEqual((record["probes"][0]["outcome"], record["probes"][0]["stop_reason"]), ("failed", "input-unreadable"))

    def test_a_partly_read_file_counts_as_read_with_its_stop_kept(self):
        future = product("product.future", required_extensions=["reconstruction:future-semantics-v9"])
        record = self.inspected("a.json", [waveform_product(), future], label="file.a")
        self.assertEqual((record["products_read"], record["products_unread"]), (["file.a"], []))

    def test_a_json_mark_is_read(self):
        self.assertEqual(self.inspected("a.json", b"\xef\xbb\xbf" + json.dumps(product()).encode(), label="product.hits-a")["state"], "complete")

    def test_a_reason_names_what_is_unmet_in_and_and_or(self):
        signature = self.signature([signature_fact()])
        unmet = {"fact": "representation", "equals": "image"}
        self.assertIn("representation", judge_candidates(signature, [{"candidate": "m", "requires": {"all_of": [unmet]}}])[0]["reason"])
        self.assertIn("representation", judge_candidates(signature, [{"candidate": "m", "requires": {"any_of": [unmet]}}])[0]["reason"])

    def test_or_names_only_the_first_branch_that_holds(self):
        signature = self.signature([signature_fact(), signature_fact(key="clock", value="a")])
        first, second = {"fact": "representation", "equals": "waveform"}, {"fact": "clock", "equals": "a"}
        self.assertEqual(judge_candidates(signature, [{"candidate": "m", "requires": {"any_of": [first, second]}}])[0]["branch"], ["representation"])

    def test_a_fact_marked_as_a_conflict_is_conflicting(self):
        signature = self.signature([signature_fact(method="conflict")])
        self.assertEqual(judge_candidates(signature, [{"candidate": "m", "requires": {"fact": "representation", "equals": "waveform"}}])[0]["state"], "conflicting")

    def test_a_fact_whose_key_is_listed_unknown_passes_nothing(self):
        signature = self.signature([signature_fact()], unknown=["representation"])
        self.assertEqual(judge_candidates(signature, [{"candidate": "m", "requires": {"fact": "representation", "equals": "waveform"}}])[0]["state"], "unknown")

    def test_no_condition_stands_on_an_unconfirmed_method(self):
        signature = self.signature([signature_fact(method="unknown")])
        self.assertEqual(judge_candidates(signature, [{"candidate": "m", "requires": {"fact": "representation", "equals": "waveform"}}])[0]["state"], "unknown")

    def test_a_product_with_no_payload_keeps_conditions_unknown(self):
        """Minor 1: Section 8.7 keeps conditions unknown; an empty list states none was consumed, not that none is needed."""
        signature = only_signature(self.inspected("a.json", product()))
        self.assertIn("conditions", signature["unknown"])
        self.assertEqual(fact_values(signature, "conditions_used_count"), [0])

    def test_one_key_does_not_clear_a_whole_dimension(self):
        declared = [{"key": "sampling.time_system", "value": "gps", "reference": "manifest:synthetic", "kind": "declaration"}]
        self.assertIn("sampling", only_signature(self.inspected("a.csv", "a,b\n1,2\n", declared=declared))["unknown"])
        self.assertNotIn("sampling", only_signature(self.inspected("a.json", pulse_product()))["unknown"])

    def test_the_columns_fact_tells_a_quoted_comma_from_two_columns(self):
        """Minor 4."""
        first = fact_values(only_signature(self.inspected("a.csv", '"a,b",c\n1,2\n')), "columns")
        second = fact_values(only_signature(self.inspected("a.csv", "a,b,c\n1,2,3\n")), "columns")
        self.assertNotEqual(first, second)
        self.assertEqual(json.loads(first[0]), ["a,b", "c"])

    def test_a_value_beside_a_conflicting_unit_is_conflicting(self):
        """Minor 7: 1 ns against 1 ps must not pass a condition on the bare 1."""
        document = pulse_product()
        other = pulse_product()
        other["sampling"] = dict(other["sampling"], interval={"value": 1, "unit": "ps"})
        record = inspect_inputs([{"product": "product.pulse", "path": self.write("a.json", document)}, {"product": "product.pulse", "path": self.write("b.json", other)}], BUDGET)
        (judged,) = judge_candidates(record["signatures"][0], [{"candidate": "m", "requires": {"fact": "sampling.interval.value", "equals": 1}}])
        self.assertEqual((judged["state"], judged["eligible"]), ("conflicting", False))

    def test_a_product_id_that_is_not_the_label_is_a_conflict(self):
        """Minor 11; A46: the caller's name is metadata about the file."""
        record = self.inspected("a.json", product("product.b"), label="product.a")
        self.assertEqual([item["key"] for item in record["conflicts"]], ["product_id"])
        self.assertEqual(record["state"], "partial")
        self.assertEqual(self.inspected("a.json", product("product.b"), label="product.b")["conflicts"], [])


if __name__ == "__main__":
    unittest.main()
