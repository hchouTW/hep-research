"""Reader rules and typed ports of the reconstruction sidecars (contract-map.md "Rules for readers"; K13; K05; plan
Sections 8.1, 8.2, 8.4). A reader stops at an unknown required extension, reports an unknown optional one, and a
connection is refused when field names or units match but the meaning does not. Synthetic documents only."""
import functools
import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import conditions, input_inspector, reconstruction, sidecar_reader  # noqa: E402
from contracts.reconstruction import check_connection, read_sidecar  # noqa: E402
from tests.contracts.reconstruction_fixtures import (binding_evidence, calibration_payload, candidate_product, code_list,  # noqa: E402
                                                     collection_witness, consumer, count_product, frame_payloads, frame_product, input_signature,
                                                     measurement, port, product, pulse_estimate, pulse_product, quantity, recipe,
                                                     reference, sealed, used_payload)

FUTURE = ["reconstruction:future-semantics-v9"]
STOPPED = ["reconstruction.reader.unknown_required_extension"]
# Parameters that hold no document, by function: a new parameter must be read, or be listed here with its reason.
NOT_A_DOCUMENT = {("judge_candidates", "candidates"): "conditions on a signature, judged in the function", ("check_binding", "context"): "the caller's binding context", ("check_validation_claim", "constraint"): "a constraint name",
                  ("dereference", "reference"): "a reference inside a document already read", ("can_recompute", "level"): "a level name",
                  ("iov_holds", "point"): "coordinates", ("affected_payloads", "changed"): "identities, judged in the function",
                  ("reuse_decision", "unknown_dependencies"): "a flag", ("check_connection", "known_extensions"): "the reader's list",
                  ("read_sidecar", "known_extensions"): "the reader's list"}
READ_BY_THEIR_OWN_SCHEMA = {("check_connection", "converter"), ("check_tool_mapping", "contract")}
READER_MODULES = {"reconstruction.py", "conditions.py", "sidecar_reader.py", "input_inspector.py"}
NOT_DRIVEN = {"matrix_rank": "a number table, no document", "payload_identity": "the digest of a payload's content, needed to seal one, reads no meaning",
              "recipe_identity": "the digest evidence binds to, reads no meaning", "read_document": "driven through read_sidecar, which is this function",
              "reader_path": "the decorator itself"}


def refusal_report(answer):
    return bool(answer.errors)


def refusal_false(answer):
    return answer is False


def refusal_none(answer):
    return answer is None


def refusal_empty(answer):
    return answer == []


def present_product():
    return product(objects=[measurement(0)])


def gain_payload():
    return calibration_payload()


def used_gain_product():
    return consumer(used_payload(gain_payload()))


def inspected_from_a_file(document):
    """T14: the document as an input file, driven through the inspector."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "input.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        label = document.get("product_id", "product.a")
        return input_inspector.inspect_inputs([{"product": label, "path": str(path)}], {"probes": 1, "bytes": 1_000_000, "seconds": 60, "memory_bytes": 1_000_000_000, "tools": 1})


def inspection_refused(record):
    """K13 through the inspector: unknown, and nothing the document says becomes a fact. A file of no known schema keeps only its
    container, which the parser saw (the user's T14 ruling)."""
    return record["state"] != "complete" and {fact["key"] for signature in record["signatures"] for fact in signature["facts"]} <= {"container"}


def judged_on(signature):
    return input_inspector.judge_candidates(signature, [{"candidate": "method.a", "requires": {"fact": "representation", "equals": "waveform"}}])


def old_response():
    return json.loads((ROOT / "contracts/fixtures/artifacts/valid/response_v28.json").read_text(encoding="utf-8"))


TOOL = json.loads((ROOT / "contracts/tool_contracts/tracker_resolution.json").read_text(encoding="utf-8"))
BINDING = {"origin": "measured", "upstream_chain": []}
# One row per document parameter of each public function: the call, a valid document, and how its refusal looks. A valid
# document must not be refused, so each row shows that the stop is what refused the others.
ENTRY_POINTS = [
    ("reconstruction", "read_sidecar", "document", lambda d: reconstruction.read_sidecar(d), present_product, refusal_report),
    ("reconstruction", "check_connection", "source_port", lambda d: check_connection(d, port("input")), port, refusal_report),
    ("reconstruction", "check_connection", "target_port", lambda d: check_connection(port(), d), lambda: port("input"), refusal_report),
    ("reconstruction", "object_count", "product", reconstruction.object_count, present_product, refusal_none),
    ("reconstruction", "dereference", "products", lambda d: reconstruction.dereference(reference(d.get("product_id", "none"), key=0), [d]), present_product, refusal_none),
    ("reconstruction", "check_products", "products", lambda d: reconstruction.check_products([d]), present_product, refusal_report),
    ("reconstruction", "can_recompute", "product", lambda d: reconstruction.can_recompute(d, "waveform"), pulse_product, refusal_false),
    ("reconstruction", "check_frame_conditions", "product", lambda d: reconstruction.check_frame_conditions(d, list(frame_payloads().values())), frame_product, refusal_report),
    ("reconstruction", "check_frame_conditions", "payloads", lambda d: reconstruction.check_frame_conditions(frame_product(), [d, frame_payloads()["after"]]), lambda: frame_payloads()["before"], refusal_report),
    ("reconstruction", "same_observable_domain", "first", lambda d: not reconstruction.same_observable_domain(d, frame_product()) or None, frame_product, lambda answer: answer is True),
    ("reconstruction", "same_observable_domain", "second", lambda d: not reconstruction.same_observable_domain(frame_product(), d) or None, frame_product, lambda answer: answer is True),
    ("reconstruction", "selected_objects", "product", reconstruction.selected_objects, candidate_product, refusal_empty),
    ("reconstruction", "check_candidate_links", "product", lambda d: reconstruction.check_candidate_links(d, list(collection_witness().values())), candidate_product, refusal_report),
    ("reconstruction", "check_candidate_links", "products", lambda d: reconstruction.check_candidate_links(candidate_product(), list(collection_witness().values()) + [d]), lambda: product("product.extra", [measurement(0)]), refusal_report),
    ("reconstruction", "observed_intervals", "product", reconstruction.observed_intervals, count_product, refusal_empty),
    ("reconstruction", "runnable", "recipe", reconstruction.runnable, recipe, refusal_false),
    ("reconstruction", "check_rebinding", "first", lambda d: reconstruction.check_rebinding(d, recipe()), recipe, lambda answer: "reconstruction.reader" in str(code_list(answer))),
    ("reconstruction", "check_rebinding", "second", lambda d: reconstruction.check_rebinding(recipe(), d), recipe, lambda answer: "reconstruction.reader" in str(code_list(answer))),
    ("reconstruction", "check_recipe_evidence", "recipe", lambda d: reconstruction.check_recipe_evidence(d, binding_evidence()), recipe, refusal_report),
    ("reconstruction", "check_recipe_evidence", "evidence", lambda d: reconstruction.check_recipe_evidence(recipe(), d), binding_evidence, refusal_report),
    ("reconstruction", "check_tool_mapping", "recipe", lambda d: reconstruction.check_tool_mapping(d, TOOL), recipe, refusal_report),
    ("reconstruction", "check_connection", "converter", lambda d: check_connection(port(), port("input"), d), lambda: Converters.converter(input=quantity(), output=quantity()), refusal_report),
    ("reconstruction", "check_tool_mapping", "contract", lambda d: reconstruction.check_tool_mapping(recipe(), d), lambda: dict(TOOL), refusal_report),
    ("reconstruction", "check_response_free_of_semantics", None, reconstruction.check_response_free_of_semantics, old_response, refusal_report),
    ("input_inspector", "inspect_inputs", None, inspected_from_a_file, present_product, inspection_refused),
    ("input_inspector", "judge_candidates", "signature", judged_on, input_signature, lambda answer: not answer[0]["eligible"]),
    ("conditions", "iov_holds", "payload", lambda d: conditions.iov_holds(d, {"position-key": 1}), gain_payload, refusal_false),
    ("conditions", "iov_intersection", "payloads", lambda d: conditions.iov_intersection([d]), gain_payload, refusal_none),
    ("conditions", "check_binding", "payload", lambda d: conditions.check_binding(d, BINDING), gain_payload, refusal_report),
    ("conditions", "check_validation_claim", "payload", lambda d: conditions.check_validation_claim(d, "validation.survey"), gain_payload, refusal_report),
    ("conditions", "check_used", "product", lambda d: conditions.check_used(d, [gain_payload()]), used_gain_product, refusal_report),
    ("conditions", "check_used", "payloads", lambda d: conditions.check_used(consumer(), [d]), gain_payload, refusal_report),
    ("conditions", "reuse_decision", "product", lambda d: conditions.reuse_decision(d, {"gain": gain_payload()}), used_gain_product, lambda answer: not answer["reuse"]),
    ("conditions", "reuse_decision", "current", lambda d: conditions.reuse_decision(used_gain_product(), {"gain": d}), gain_payload, lambda answer: not answer["reuse"]),
    ("conditions", "affected_payloads", "payloads", lambda d: conditions.affected_payloads([], [d]), gain_payload, lambda answer: answer != []),
]


def public_functions():
    for module in (reconstruction, conditions, sidecar_reader, input_inspector):
        for name, function in inspect.getmembers(module, inspect.isfunction):
            if function.__module__ == module.__name__ and not name.startswith("_"):
                yield name, function


def unknown_format_copy(document):
    if "artifact_type" in document:
        return dict(document, artifact_type="response-future")
    changed = dict(document, schema=f"{document.get('schema', 'unknown')}-future")
    return sealed(changed) if "payload_id" in document else changed


def future_extension_copy(document):
    changed = dict(document, required_extensions=FUTURE)
    return sealed(changed) if "payload_id" in document else changed


class ReaderRules(unittest.TestCase):
    def test_valid_port_is_read(self):
        self.assertEqual(code_list(read_sidecar(port())), [])

    def test_unknown_required_extension_stops_the_reader(self):
        document = port(required_extensions=["reconstruction:future-semantics-v9"], port_id=None)
        report = read_sidecar(document)
        self.assertEqual(code_list(report), ["reconstruction.reader.unknown_required_extension"],
                         "the reader stops: nothing else in the document is read, not even the bad port_id")

    def test_unknown_optional_extension_is_ignored_and_reported(self):
        document = port(optional_extensions=["reconstruction:presentation-hints-v1"],
                        extensions={"reconstruction:presentation-hints-v1": {"colour": "blue"}})
        report = read_sidecar(document)
        self.assertEqual(code_list(report), [])
        self.assertEqual([f.code for f in report.findings if f.severity == "warning"],
                         ["reconstruction.reader.unknown_optional_extension"])

    def test_known_required_extension_is_read(self):
        self.assertEqual(code_list(read_sidecar(pulse_product())), [])

    def test_declared_extension_with_nothing_behind_it_is_refused(self):
        self.assertIn("reconstruction.extension.block_missing",
                      code_list(read_sidecar(product(objects=[measurement(0)], required_extensions=["reconstruction:estimate-v1"]))))

    def test_a_block_extension_means_nothing_on_another_format(self):
        """Re-review 2 minor 2, K13."""
        for document in (port(required_extensions=["reconstruction:frames-v1"]), recipe(required_extensions=["reconstruction:frames-v1"]),
                         recipe(inputs=[port("input", required_extensions=["reconstruction:frames-v1"])])):
            self.assertEqual(code_list(read_sidecar(document)), ["reconstruction.extension.not_for_this_format"])

    def test_fields_of_a_known_extension_are_not_dropped_silently(self):
        document = pulse_product()
        document["extensions"] = {"reconstruction:estimate-v1": {"note": "held outside the block"}}
        report = read_sidecar(document)
        self.assertEqual([f.code for f in report.findings if f.severity == "warning"], ["reconstruction.reader.extension_fields_unread"])

    def test_extension_field_outside_the_declared_list_is_refused(self):
        self.assertIn("reconstruction.reader.undeclared_extension",
                      code_list(read_sidecar(port(extensions={"reconstruction:unlisted-v1": {}}))))

    def test_unknown_format_stops_the_reader(self):
        self.assertEqual(code_list(read_sidecar({"schema": "reconstruction-port/2"})), ["reconstruction.reader.unknown_format"])
        self.assertEqual(code_list(read_sidecar({"artifact_type": "response"})), ["reconstruction.reader.unknown_format"])

    def test_malformed_lists_are_findings_not_crashes(self):
        recipe_like = {"schema": "reconstruction-recipe/1", "inputs": 3, "required_extensions": "none"}
        self.assertTrue(code_list(read_sidecar(recipe_like)))

    def test_every_malformed_document_gives_a_report(self):
        """M10: the review's inputs, and a few of the same families."""
        not_a_number, infinite = pulse_estimate(), pulse_estimate()
        not_a_number["observation"][0] = float("nan")
        infinite["model"]["design"][0][0] = float("inf")
        cases = {"list as an extension": port(required_extensions=[["x"]]), "list as an optional extension": port(optional_extensions=[["x"]]),
                 "list as a format": {"schema": ["x"]}, "NaN": pulse_product(not_a_number), "infinity": pulse_product(infinite),
                 "number as a document": 3, "list as a document": [port()], "null": None}
        for name, document in cases.items():
            report = read_sidecar(document)
            self.assertIsInstance(report, type(read_sidecar(port())), name)
            self.assertTrue(code_list(report), name)

    def test_not_a_number_is_named(self):
        estimate = pulse_estimate()
        estimate["observation"][0] = float("nan")
        self.assertIn("reconstruction.reader.not_finite", code_list(read_sidecar(pulse_product(estimate))))

    def test_undeclared_key_is_refused(self):
        self.assertIn("schema.additional", code_list(read_sidecar(port(gpu_policy="fast"))))


class EveryReaderPathStops(unittest.TestCase):
    """K13, Section 8.1: "unknown required semantics stop automatic connection". Every public function is driven, not flagged."""

    def test_every_public_function_has_a_row_for_each_document_it_reads(self):
        rows = {(name, parameter) for _, name, parameter, _, _, _ in ENTRY_POINTS}
        for name, function in public_functions():
            if name in NOT_DRIVEN:
                continue
            for parameter in getattr(function, "document_parameters", (None,)):
                if name != "read_sidecar":
                    self.assertIn((name, parameter), rows, f"{name} has no driven row for {parameter}")
        self.assertIn(("read_sidecar", "document"), rows)

    def test_every_parameter_is_read_or_named_as_no_document(self):
        """Re-review 2, section 2: a new document parameter cannot escape by not being listed in reader_path."""
        for name, function in public_functions():
            if name in NOT_DRIVEN:
                continue
            read = set(getattr(function, "document_parameters", ()))
            for parameter in inspect.signature(function).parameters:
                key = (name, parameter)
                self.assertTrue(parameter in read or key in NOT_A_DOCUMENT or key in READ_BY_THEIR_OWN_SCHEMA or (name, None) in {(n, p) for _, n, p, _, _, _ in ENTRY_POINTS} or name == "read_sidecar",
                                f"{name}({parameter}) is neither read nor named")

    def test_no_entry_point_hides_in_a_class_a_partial_or_a_new_module(self):
        """Re-review 2, section 2."""
        for module in (reconstruction, conditions, sidecar_reader, input_inspector):
            for name, member in vars(module).items():
                if name.startswith("_"):
                    continue
                self.assertNotIsInstance(member, functools.partial, name)
                if inspect.isclass(member) and member.__module__ == module.__name__:
                    self.assertTrue(issubclass(member, Warning), f"{name}: a public class would escape the rows")
        importers = {path.name for path in (ROOT / "contracts").glob("*.py") if "sidecar_reader" in path.read_text(encoding="utf-8")}
        self.assertEqual(importers - {"__init__.py"}, READER_MODULES - {"sidecar_reader.py"})

    def test_a_valid_document_is_not_refused(self):
        for _, name, parameter, call, valid, refused in ENTRY_POINTS:
            self.assertFalse(refused(call(valid())), f"{name}.{parameter}")

    def test_an_unknown_format_is_refused_on_every_path(self):
        for _, name, parameter, call, valid, refused in ENTRY_POINTS:
            self.assertTrue(refused(call(unknown_format_copy(valid()))), f"{name}.{parameter}")

    def test_a_document_with_an_unknown_required_extension_is_refused_on_every_path(self):
        for _, name, parameter, call, valid, refused in ENTRY_POINTS:
            self.assertTrue(refused(call(future_extension_copy(valid()))), f"{name}.{parameter}")

    def test_a_product_with_an_unknown_required_extension_is_refused_on_every_path(self):
        unknown = product(objects=[measurement(0)], required_extensions=FUTURE)
        for _, name, parameter, call, _, refused in ENTRY_POINTS:
            self.assertTrue(refused(call(unknown)), f"{name}.{parameter}")

    def test_a_document_the_reader_refuses_is_not_acted_on(self):
        """Re-review RB1: a routine recipe with no evidence, a block with no declared extension."""
        self.assertFalse(reconstruction.runnable(recipe(status="routine")))
        document = candidate_product()
        document["required_extensions"] = []
        self.assertEqual(reconstruction.selected_objects(document), [])

    def test_a_port_held_in_a_mapping_does_not_escape_the_stop(self):
        """Re-review RB1."""
        self.assertFalse(reconstruction.runnable(recipe(inputs={"a": port("input", required_extensions=FUTURE)})))

    def test_an_ignored_optional_extension_is_reported_on_a_path_with_no_report(self):
        """Re-review minor 1, K13: "ignored and reported"."""
        with self.assertWarns(sidecar_reader.IgnoredExtensionWarning):
            self.assertTrue(reconstruction.runnable(recipe(optional_extensions=["reconstruction:presentation-hints-v1"])))

    def test_no_malformed_argument_raises(self):
        """Re-review minor 2."""
        self.assertFalse(conditions.reuse_decision(None, None)["reuse"])
        self.assertIsNone(conditions.affected_payloads([], None), "unknown input never reads as nothing affected")
        self.assertTrue(code_list(read_sidecar(port(required_extensions=["reconstruction:frames-v1"]), None)))
        deep = []
        for _ in range(5000):
            deep = [deep]
        self.assertTrue(code_list(read_sidecar(port(native=deep))))

    def test_runnable(self):
        self.assertTrue(reconstruction.runnable(recipe()))
        self.assertFalse(reconstruction.runnable(recipe(required_extensions=FUTURE)))
        self.assertFalse(reconstruction.runnable(recipe(inputs=[port("input", required_extensions=FUTURE)])))

    def test_reuse_decision(self):
        payload = calibration_payload()
        unknown = calibration_payload(required_extensions=FUTURE)
        decision = conditions.reuse_decision(consumer(used_payload(unknown)), {"gain": unknown})
        self.assertFalse(decision["reuse"])
        self.assertIn("future-semantics", decision["reason"])
        self.assertTrue(conditions.reuse_decision(consumer(used_payload(payload)), {"gain": payload})["reuse"])

    def test_check_binding(self):
        context = {"origin": "measured", "upstream_chain": []}
        self.assertEqual(code_list(conditions.check_binding(calibration_payload(required_extensions=FUTURE), context)), STOPPED)

    def test_check_used(self):
        unknown = calibration_payload(required_extensions=FUTURE)
        self.assertEqual(code_list(conditions.check_used(consumer(used_payload(unknown)), [unknown])), STOPPED)

    def test_check_products(self):
        self.assertEqual(code_list(reconstruction.check_products([product(objects=[measurement(0)], required_extensions=FUTURE)])), STOPPED)

    def test_dereference(self):
        document = product(objects=[measurement(0)], required_extensions=FUTURE)
        self.assertIsNone(reconstruction.dereference(reference("product.hits-a", key=0), [document]))

    def test_other_paths(self):
        unknown_recipe, unknown_product = recipe(required_extensions=FUTURE), product(objects=[measurement(0)], required_extensions=FUTURE)
        unknown_payload = calibration_payload(required_extensions=FUTURE)
        evidence = dict(binding_evidence(), required_extensions=FUTURE)
        contract = {"tool_id": "tool", "operations": []}
        for name, report in (("check_recipe_evidence", reconstruction.check_recipe_evidence(recipe(), evidence)),
                             ("check_rebinding", reconstruction.check_rebinding(recipe(), unknown_recipe)),
                             ("check_tool_mapping", reconstruction.check_tool_mapping(unknown_recipe, contract)),
                             ("check_validation_claim", conditions.check_validation_claim(unknown_payload, "validation.survey")),
                             ("check_frame_conditions", reconstruction.check_frame_conditions(frame_product(), [unknown_payload])),
                             ("check_candidate_links", reconstruction.check_candidate_links(candidate_product(), [unknown_product]))):
            self.assertEqual(code_list(report), STOPPED, name)
        unknown_frames = dict(frame_product(), required_extensions=FUTURE)
        self.assertIsNone(reconstruction.object_count(unknown_product))
        self.assertFalse(reconstruction.can_recompute(dict(pulse_product(), required_extensions=FUTURE), "waveform"))
        self.assertEqual(reconstruction.selected_objects(dict(candidate_product(), required_extensions=FUTURE)), [])
        self.assertEqual(reconstruction.observed_intervals(dict(count_product(), required_extensions=FUTURE)), [])
        self.assertFalse(reconstruction.same_observable_domain(unknown_frames, frame_product()))
        self.assertEqual(conditions.affected_payloads([], [unknown_payload]), [unknown_payload["payload_id"]], "unknown meaning broadens invalidation")

    def test_malformed_document_refuses_on_every_path(self):
        self.assertFalse(reconstruction.runnable({"schema": "reconstruction-recipe/1", "required_extensions": []}))
        self.assertFalse(reconstruction.runnable(3))
        self.assertIsNone(reconstruction.dereference(reference("product.hits-a", key=0), [{"product_id": "product.hits-a", "required_extensions": []}]))
        self.assertTrue(code_list(reconstruction.check_products([3])))
        self.assertFalse(conditions.reuse_decision(consumer(), {"gain": {"required_extensions": []}})["reuse"])


class QuantitySemantics(unittest.TestCase):
    """K05: every port states quantity kind, unit, basis or surface, reference hypothesis and observation level."""

    def test_every_field_is_required(self):
        for field in ("kind", "unit", "basis", "reference_hypothesis", "observation_level"):
            semantics = quantity()
            del semantics[field]
            self.assertTrue(code_list(read_sidecar(port(quantity=semantics))), field)

    def test_kind_comes_from_the_vocabulary(self):
        self.assertTrue(code_list(read_sidecar(port(quantity=quantity(kind="energy")))),
                        "an unqualified energy is refused; the kinds stay separate")

    def test_periodic_angle_states_period_and_axis(self):
        angle = quantity(kind="angle", unit="rad", basis="axis:beam")
        self.assertIn("reconstruction.port.angle_without_period", code_list(read_sidecar(port(quantity=angle))))
        angle["period"] = {"value": 6.283185307179586, "unit": "rad"}
        self.assertEqual(code_list(read_sidecar(port(quantity=angle))), [])


class Connections(unittest.TestCase):
    def connect(self, source=None, target=None, converter=None):
        return code_list(check_connection(source or port(), target or port("input"), converter))

    def test_matching_ports_connect(self):
        self.assertEqual(self.connect(), [])

    def test_same_unit_with_different_kind_is_refused(self):
        for kinds in (("energy-deposited", "energy-visible"), ("energy-recoil", "energy-incident")):
            source, target = port(quantity=quantity(kinds[0])), port("input", quantity=quantity(kinds[1]))
            self.assertIn("reconstruction.connect.quantity_kind_mismatch", self.connect(source, target))

    def test_electron_count_is_not_energy_and_power_is_not_counts(self):
        source = port(quantity=quantity("electron-count", "1"))
        self.assertIn("reconstruction.connect.quantity_kind_mismatch", self.connect(source))
        target = port("input", quantity=quantity("count", "1"))
        self.assertIn("reconstruction.connect.quantity_kind_mismatch",
                      self.connect(port(quantity=quantity("spectral-power", "1")), target))

    def test_score_is_not_a_calibrated_probability(self):
        source, target = port(quantity=quantity("score", "1")), port("input", quantity=quantity("calibrated-probability", "1"))
        self.assertIn("reconstruction.connect.quantity_kind_mismatch", self.connect(source, target))

    def test_each_semantic_field_must_agree(self):
        for field, code in (("basis", "basis"), ("reference_hypothesis", "hypothesis"), ("observation_level", "observation_level"),
                            ("unit", "unit")):
            semantics = quantity()
            semantics[field] = "other"
            self.assertIn(f"reconstruction.connect.{code}_mismatch", self.connect(port(quantity=semantics)), field)

    def test_sample_interval_must_agree(self):
        """M1: Section 8.4, check 2."""
        one, four = {"value": 1, "unit": "ns"}, {"value": 4, "unit": "ns"}
        self.assertIn("reconstruction.connect.sample_interval_mismatch", self.connect(port(sample_interval=one), port("input", sample_interval=four)))
        self.assertIn("reconstruction.connect.sample_interval_mismatch", self.connect(port(), port("input", sample_interval=four)))
        self.assertEqual(self.connect(port(sample_interval=one), port("input", sample_interval=dict(one))), [])

    def test_angle_period_must_agree(self):
        """M1: K05, an axis of period pi is not a direction of period 2 pi."""
        full, half = quantity("angle", "rad", "axis:beam"), quantity("angle", "rad", "axis:beam")
        full["period"], half["period"] = {"value": 6.28, "unit": "rad"}, {"value": 3.14, "unit": "rad"}
        self.assertIn("reconstruction.connect.period_mismatch", self.connect(port(quantity=full), port("input", quantity=half)))

    def test_sample_interval_through_a_converter(self):
        """Re-review minor 5, Section 8.4 check 2; contract map: a converter has its own input and output semantics."""
        one, four = {"value": 1, "unit": "ns"}, {"value": 4, "unit": "ns"}
        source, target = port(sample_interval=one), port("input", sample_interval=four)
        same_kind = Converters.converter(input=quantity(), output=quantity())
        self.assertTrue(self.connect(port(), port("input"), {"information_loss": False, "input": quantity(), "output": quantity(), "schema": "converter/9"}), "a converter is read by its schema")
        self.assertEqual(self.connect(source, target, same_kind), ["reconstruction.connect.sample_interval_mismatch"])
        resampling = dict(same_kind, input_sample_interval=one, output_sample_interval=four)
        self.assertEqual(self.connect(source, target, resampling), [])
        self.assertEqual(self.connect(source, port("input", sample_interval=one), resampling), ["reconstruction.connect.sample_interval_mismatch"])

    def test_one_interval_in_two_units_agrees(self):
        """Re-review 2 minor 10, K05: matching meaning, not spelling."""
        self.assertEqual(self.connect(port(sample_interval={"value": 1, "unit": "ns"}), port("input", sample_interval={"value": 0.001, "unit": "us"})), [])
        self.assertEqual(self.connect(port(sample_interval={"value": 2, "unit": "ns"}), port("input", sample_interval={"value": 0.001, "unit": "us"})),
                         ["reconstruction.connect.sample_interval_mismatch"])

    def test_native_type_must_agree(self):
        source = port(native={"type": "synthetic::Other", "schema_ref": "synthetic/other/1"})
        self.assertIn("reconstruction.connect.native_type_mismatch", self.connect(source))

    def test_output_presence_must_be_accepted(self):
        source = port(presence=["present", "valid-empty", "absent"])
        self.assertIn("reconstruction.connect.presence_not_accepted", self.connect(source))

    def test_cardinality_must_be_compatible(self):
        target = port("input", cardinality="one")
        self.assertIn("reconstruction.connect.cardinality_mismatch", self.connect(target=target))

    def test_port_direction_is_checked(self):
        self.assertIn("reconstruction.connect.direction", self.connect(port("input"), port("input")))

    def test_unknown_required_extension_stops_a_connection(self):
        source = port(required_extensions=["reconstruction:future-semantics-v9"])
        self.assertEqual(self.connect(source), ["reconstruction.reader.unknown_required_extension"])

    def test_unsafe_execution_is_refused(self):
        source = port(execution={"concurrency": "serialized"})
        target = port("input", execution={"concurrency": "reentrant"})
        self.assertIn("reconstruction.connect.unsafe_execution", self.connect(source, target))
        self.assertEqual(self.connect(source, port("input", execution={"concurrency": "serialized"})), [])


class Converters(unittest.TestCase):
    """Contract map, "Converter responsibilities": a converter is a declared step, and loss is never a format change."""

    @staticmethod
    def converter(**fields):
        document = {"converter_id": "converter.charge-to-energy", "version": "1.0.0",
                    "input": quantity("charge", "fC"), "output": quantity("energy-deposited", "MeV"),
                    "uncertainty_handling": "propagated", "association_handling": "kept",
                    "cost": "one multiplication per object", "information_loss": False}
        document.update(fields)
        return document

    def test_declared_converter_connects_two_kinds(self):
        source = port(quantity=quantity("charge", "fC"))
        self.assertIn("reconstruction.connect.quantity_kind_mismatch", code_list(check_connection(source, port("input"))))
        self.assertEqual(code_list(check_connection(source, port("input"), self.converter())), [])

    def test_converter_must_match_both_ends(self):
        source = port(quantity=quantity("time", "ns"))
        self.assertIn("reconstruction.connect.quantity_kind_mismatch",
                      code_list(check_connection(source, port("input"), self.converter())))

    def test_information_loss_goes_into_retention_or_response(self):
        source = port(quantity=quantity("charge", "fC"))
        lossy = self.converter(information_loss=True)
        self.assertIn("reconstruction.converter.loss_unrecorded", code_list(check_connection(source, port("input"), lossy)))
        lossy["retention_ref"] = "retention.after-compression"
        self.assertEqual(code_list(check_connection(source, port("input"), lossy)), [])


if __name__ == "__main__":
    unittest.main()
