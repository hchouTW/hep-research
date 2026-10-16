"""v6.3 G-ENFORCE step 1: recipe_semantics.py refuses an upstream artifact that requires a capability it does not
implement (semantics.upstream_unknown_capability) and still reads the correction keys under the one it implements.
Synthetic artifacts only."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import recipe_semantics as rs  # noqa: E402

TABLE = json.loads((ROOT / "contracts" / "semantics" / "tables" / "differential_flux.json").read_text())
RECIPE = json.loads((ROOT / "contracts" / "semantics" / "recipes" / "flux_from_counts.json").read_text())
KEY = {"target_scope": "species:proton", "calibration_digest": "none", "variation_id": "nominal", "stage": "estimator"}


def upstream(caps):
    return {"required_capabilities": caps, "extension": {"corrections": [dict(effect_id="efficiency", **KEY)]}}


def codes(art):
    res = rs.check_recipe(RECIPE, {TABLE["table_id"]: TABLE}, [art], contracts=[])
    return {f["code"] for f in res["findings"]}


class UpstreamCapabilities(unittest.TestCase):
    def test_unknown_capability_is_refused(self):
        found = codes(upstream(["measurement:correction-keys-v9"]))
        self.assertIn("semantics.upstream_unknown_capability", found)
        self.assertNotIn("semantics.repeat_undetermined", found, "nothing is read from a refused artifact")

    def test_known_capability_is_read(self):
        found = codes(upstream(["measurement:correction-keys-v1"]))
        self.assertIn("semantics.repeat_undetermined", found)
        self.assertNotIn("semantics.upstream_unknown_capability", found)


if __name__ == "__main__":
    unittest.main()
