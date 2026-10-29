"""The capability measurement:correction-keys-v1 of a measurement spec (V36): with it the R4 correction keys and
application_id are known and checked by contracts/validate.py; without it the legacy warnings stay. (Kept from the
cross-artifact check's D05a tests when the check was retired; the capability is an artifact contract.) Synthetic data
only."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

FIX = ROOT / "contracts" / "fixtures" / "artifacts" / "valid"
CAP = "measurement:correction-keys-v1"
R4 = ("target_scope", "calibration_digest", "variation_id", "stage", "application_id")


def keyed_spec(capability=True):
    spec = json.loads((FIX / "measurement_ratio.json").read_text())
    spec["extension"]["corrections"][0].update(target_scope="species:proton/period:p1", calibration_digest="none",
                                               variation_id="nominal", stage="estimator", application_id="exposure")
    if capability:
        spec["required_capabilities"] = [CAP]
    return spec


class V36SpecKeys(unittest.TestCase):
    """V36: with the capability the R4 keys and application_id are known; without it the legacy warnings stay."""

    def test_capability_makes_the_keys_known(self):
        rep = validate_artifact(keyed_spec(), Vocabulary(), strict=True)
        self.assertFalse([f for f in rep.findings if f.code in ("measurement.unknown_key", "contract.unknown_capability")],
                         [f.as_dict() for f in rep.findings])

    def test_without_capability_the_legacy_threshold_holds(self):
        rep = validate_artifact(keyed_spec(capability=False), Vocabulary(), strict=True)
        flagged = {f.path.rsplit(".", 1)[-1] for f in rep.findings if f.code == "measurement.unknown_key"}
        self.assertEqual(flagged, set(R4))

    def test_malformed_keys_are_errors(self):
        spec = keyed_spec()
        spec["extension"]["corrections"][0]["calibration_digest"] = "not-a-digest"
        rep = validate_artifact(spec, Vocabulary(), strict=True)
        self.assertIn("measurement.bad_correction_key", {f.code for f in rep.errors})


if __name__ == "__main__":
    unittest.main()
