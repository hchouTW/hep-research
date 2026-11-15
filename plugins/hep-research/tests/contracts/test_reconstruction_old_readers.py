"""A41 and G04 of the reconstruction contracts (contract-map.md, K13): new semantic fields sent to an old closed reader
are refused clearly (the open response extension warns instead), and the integration goes through a versioned mapping that claims no tool support it does not have.
The first class pins existing behaviour; old readers are not changed. Synthetic documents only."""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import response_adapter, tool_contract  # noqa: E402
from contracts.reconstruction import check_response_free_of_semantics, check_tool_mapping, read_sidecar  # noqa: E402
from contracts.schema import validate  # noqa: E402
from contracts.validate import main as validate_main  # noqa: E402
from tests.contracts.reconstruction_fixtures import code_list, recipe  # noqa: E402

CONTRACT = json.loads((ROOT / "contracts/tool_contracts/tracker_resolution.json").read_text(encoding="utf-8"))
OLD_RECIPE = json.loads((ROOT / "contracts/semantics/recipes/flux_from_counts.json").read_text(encoding="utf-8"))
OLD_RESPONSE = json.loads((ROOT / "contracts/fixtures/artifacts/valid/response_v28.json").read_text(encoding="utf-8"))


def named_fields(result) -> str:
    return json.dumps(result)


class OldReadersRefuse(unittest.TestCase):
    def assert_refused(self, result, field):
        self.assertEqual(result["status"], "fail")
        self.assertIn(field, named_fields(result), "the refusal names the field, so it is clear")

    def test_tool_contract_refuses_a_new_top_level_key(self):
        contract = dict(copy.deepcopy(CONTRACT), typed_ports=[])
        self.assert_refused(tool_contract.check(contract, help_check=False), "typed_ports")

    def test_tool_contract_refuses_a_new_operation_key(self):
        contract = copy.deepcopy(CONTRACT)
        contract["operations"][0]["gpu_policy"] = "fast"
        self.assert_refused(tool_contract.check(contract, help_check=False), "gpu_policy")

    def test_tool_contract_entry_stays_a_python_file(self):
        contract = dict(copy.deepcopy(CONTRACT), entry="bin/native-backend")
        self.assertFalse(validate(contract, "tool_contract.json").ok, "G04: a native binary needs a wrapper or a registered description")

    def test_old_recipe_refuses_a_new_key(self):
        report = validate(dict(OLD_RECIPE, port_semantics={}), "recipe.json")
        self.assertIn("port_semantics", json.dumps(report.as_dict()))
        self.assertFalse(report.ok)

    def test_response_reader_says_it_does_not_read_a_new_key(self):
        """ext_response.json is open, so this reader warns rather than refuses, and only from contracts 2.8.0 on.
        Reconstruction semantics therefore stay in the sidecars and out of a response."""
        document = copy.deepcopy(OLD_RESPONSE)
        document["extension"]["transfer_operator"] = {}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "response.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                validate_main([str(path)])
        self.assertIn("response.unknown_key", printed.getvalue())
        self.assertIn("transfer_operator", printed.getvalue())

    def test_old_response_path_lets_a_block_through(self):
        """Minor 14, a known limit of old readers, which K13 keeps: exit 0 with a warning, and the adapter drops the keys
        with no message. So the check below, not the old path, enforces the rule."""
        document = copy.deepcopy(OLD_RESPONSE)
        document["extension"].update({"required_extensions": ["reconstruction:frames-v1"], "frames": {}})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "response.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(validate_main([str(path)]), 0)
        converted = response_adapter.to_validator_input(document["extension"], base_dir=ROOT, contract_version=document["contract_version"])
        self.assertTrue(converted["ok"])
        self.assertNotIn("frames", json.dumps(converted))

    def test_no_reconstruction_semantics_go_into_a_response(self):
        """Minor 14: the rule of contract-map.md is a check that T07 onward can call."""
        self.assertEqual(code_list(check_response_free_of_semantics(OLD_RESPONSE)), [])
        for field, value in (("frames", {}), ("required_extensions", ["reconstruction:frames-v1"]), ("reconstruction:estimate-v1", {})):
            document = copy.deepcopy(OLD_RESPONSE)
            document["extension"][field] = value
            self.assertEqual(code_list(check_response_free_of_semantics(document)), ["reconstruction.response.holds_semantics"], field)

    def test_the_check_reads_the_whole_artifact(self):
        """Re-review minor 4: the envelope is open at the top level too, and a key may sit one level down."""
        top_level = dict(copy.deepcopy(OLD_RESPONSE), frames={})
        nested = copy.deepcopy(OLD_RESPONSE)
        nested["extension"]["note"] = {"frames": {}}
        for document in (top_level, nested):
            self.assertEqual(code_list(check_response_free_of_semantics(document)), ["reconstruction.response.holds_semantics"])

    def test_every_shipped_response_is_clean(self):
        """No old response trips the check; a name an old schema declares stays allowed."""
        for pattern in ("contracts/fixtures/artifacts/valid/response*.json", "examples/*/output/artifacts/response*.json"):
            for path in sorted(ROOT.glob(pattern)):
                document = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(code_list(check_response_free_of_semantics(document)), [], path.name)

    def test_what_is_no_response_is_refused(self):
        """Re-review minor 2."""
        for document in ({"extension": None}, [{}], 3, None, {"artifact_type": "response"}, {"artifact_type": "response", "extension": 3}):
            self.assertEqual(code_list(check_response_free_of_semantics(document)), ["reconstruction.response.not_a_response"], document)

    def test_a_loose_sidecar_in_an_artifacts_dir_is_an_error(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "recipe.json").write_text(json.dumps(recipe()), encoding="utf-8")
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                exit_code = validate_main([folder])
        self.assertEqual(exit_code, 1)
        self.assertIn("artifacts_dir.not_artifact", printed.getvalue())


class VersionedMapping(unittest.TestCase):
    @staticmethod
    def mapped(**fields):
        mapping = {"tool_id": "tracker-resolution", "operation_id": CONTRACT["operations"][0]["operation_id"], "mapping_version": "1"}
        mapping.update(fields)
        return recipe(tool_contract=mapping)

    def test_mapping_to_a_shipped_operation_is_read(self):
        document = self.mapped()
        self.assertEqual(code_list(read_sidecar(document)), [])
        self.assertEqual(code_list(check_tool_mapping(document, CONTRACT)), [])

    def test_unknown_mapping_version_stops(self):
        self.assertIn("reconstruction.recipe.unknown_mapping_version", code_list(read_sidecar(self.mapped(mapping_version="2"))))

    def test_mapping_claims_no_operation_the_contract_lacks(self):
        self.assertIn("reconstruction.recipe.tool_operation_missing", code_list(check_tool_mapping(self.mapped(operation_id="native-run"), CONTRACT)))
        self.assertIn("reconstruction.recipe.tool_operation_missing", code_list(check_tool_mapping(self.mapped(tool_id="another-tool"), CONTRACT)))

    def test_recipe_without_a_mapping_claims_nothing(self):
        self.assertEqual(code_list(check_tool_mapping(recipe(), CONTRACT)), [])


if __name__ == "__main__":
    unittest.main()
