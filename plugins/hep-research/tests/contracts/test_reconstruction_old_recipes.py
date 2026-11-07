"""Old-recipe comparison of the detector reconstruction contract map (docs/dev/detector-reconstruction/contract-map.md;
K13): the old recipes, tool contracts and response examples keep their result. Each result is digested with
canonical_sha256, floats rounded to ten significant digits, and compared with tests/contracts/old_recipe_results.json, recorded on the tree before the
reconstruction sidecars were added. Regenerate that file only for a change that means to alter an old result."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import recipe_semantics, response_adapter, tool_contract  # noqa: E402
from contracts.recipe_semantics import canonical_sha256  # noqa: E402
from core.stats.validate_response import validate_response  # noqa: E402

RECORDED = Path(__file__).with_name("old_recipe_results.json")
RESPONSE_GLOBS = ("contracts/fixtures/artifacts/valid/response*.json", "examples/*/output/artifacts/response*.json")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def recipe_results() -> dict:
    tables = {t["table_id"]: t for t in map(load, sorted((ROOT / "contracts/semantics/tables").glob("*.json")))}
    contracts = [load(p) for p in sorted((ROOT / "contracts/tool_contracts").glob("*.json"))]
    return {p.name: recipe_semantics.check_recipe(load(p), tables, [], contracts=contracts)
            for p in sorted((ROOT / "contracts/semantics/recipes").glob("*.json"))}


def tool_contract_results() -> dict:
    return {p.name: tool_contract.check(load(p), help_check=False)
            for p in sorted((ROOT / "contracts/tool_contracts").glob("*.json"))}


def response_results() -> dict:
    found = {}
    for pattern in RESPONSE_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            doc = load(path)
            converted = response_adapter.to_validator_input(doc["extension"], base_dir=path.parent,
                                                            contract_version=doc.get("contract_version"))
            found[path.relative_to(ROOT).as_posix()] = {
                "converted": converted,
                "validation": validate_response(converted["input"]) if converted["ok"] else None}
    return found


def rounded(node):
    """Floats to ten significant digits, so a last-bit difference between platforms is not a changed result."""
    if isinstance(node, float):
        return float(f"{node:.9e}")
    if isinstance(node, dict):
        return {key: rounded(value) for key, value in node.items()}
    return [rounded(value) for value in node] if isinstance(node, list) else node


def digests(results: dict) -> dict:
    return {name: canonical_sha256(rounded(result)) for name, result in results.items()}


def current_results() -> dict:
    return {"recipes": digests(recipe_results()), "tool_contracts": digests(tool_contract_results()),
            "responses": digests(response_results())}


class OldItemsKeepTheirResult(unittest.TestCase):
    def test_every_old_item_is_covered(self):
        results = current_results()
        self.assertEqual(len(results["tool_contracts"]), 16)
        self.assertIn("flux_from_counts.json", results["recipes"])
        self.assertGreaterEqual(len(results["responses"]), 4)

    def test_results_hold_no_host_path(self):
        for results in (recipe_results(), tool_contract_results(), response_results()):
            self.assertNotIn(str(ROOT), json.dumps(results))

    def test_results_match_the_record(self):
        results = current_results()
        self.assertTrue(RECORDED.is_file(), "no record yet; current results:\n" + json.dumps(results, indent=1, sort_keys=True))
        self.assertEqual(results, load(RECORDED))


if __name__ == "__main__":
    unittest.main()
