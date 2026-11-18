"""CHK-AT-12-02 (S2): the F4 bound of the tof kit's time resolution.

Defect: contracts/rules/design_geometry/tof.json declared the figure of merit time-resolution "tail_sensitive": false,
so contracts/design.py check_f4 (and evaluate_design.py f4) labelled an F4 time resolution an `estimate` whatever tail
sources the study simulated. The kit's time is the truth crossing time plus one Gaussian smear.

Oracle (basis locator, expected label fixed here before the fix):
- skills/hep-detector/references/geant4-study-protocol.md (F4 study paragraph): "An F4 resolution is an `estimate` only
  with all four tail sources simulated, else `optimistic`"; contracts/schemas/design_geometry.json tail_sensitive
  $comment (FID-03): "resolution, confusion rate and rejection stay optimistic unless the study simulated every tail
  source".
- PDG RPP 2025, sec. 35 Particle Detectors at Accelerators (scifix:S03): sec. 35.4, p. 16, the timing precision of a
  scintillation detector "generally depends on five parameters: the rise and decay times of the scintillator, the time
  dispersion of optical photons in the scintillator, the time response and jitter of the photodetector signal for
  single photons, and the number of photons"; sec. 35.8.4, eq. (35.25), p. 73, "The achievable time resolution has
  several contributions" (time walk, noise jitter, arrival-time fluctuations, signal distortion, digitisation). A time
  resolution is therefore a resolution figure of merit whose non-Gaussian terms a truth-plus-one-Gaussian study does
  not simulate: tail-sensitive, so `optimistic` unless all four tail sources are simulated.
Expected: tails {} -> optimistic, one tail source -> optimistic, all four -> estimate.
Negative control (emulates the pre-fix mapping): the same check_f4 run with a copy of the mapping whose time-resolution
says tail_sensitive false gives `estimate` with no tail source, which the oracle rejects.

Tolerances: none. The comparisons are exact labels.

Run from the plugin root: python3 -m unittest tests.contracts.test_f_s12_misc_tof_tail_sensitive -v
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import design  # noqa: E402

MAPPING = ROOT / "contracts" / "rules" / "design_geometry" / "tof.json"
EXAMPLE = ROOT / "examples" / "design-minimal-spectrometer" / "output" / "artifacts"
CANDIDATE = "j15-v1:cand-N4"
FOM = "time-resolution"
# The four tail sources of the protocol (geant4-study-protocol.md), written here from its text.
ALL_TAILS = ["alignment", "calibration-non-uniformity", "noise-digitization", "pattern-recognition"]


def expected_bound(tails) -> str:
    """The protocol rule for a tail-sensitive resolution: estimate only with all four tail sources simulated."""
    return "estimate" if set(ALL_TAILS) <= set(tails) else "optimistic"


@unittest.skipUnless(EXAMPLE.exists(), "example outputs not present in this copy")
class TofTimeResolutionBound(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.artifacts = Path(self.folder.name) / "artifacts"
        shutil.copytree(EXAMPLE, self.artifacts)
        for name in ("cand-N4", "cand-N6"):  # cand-N6 is cand-N4's base: a derived candidate inherits the kind
            path = self.artifacts / f"candidates/{name}.json"
            doc = json.loads(path.read_text(encoding="utf-8"))
            doc["extension"]["geometry_kind"] = "tof"
            path.write_text(json.dumps(doc), encoding="utf-8")

    def bound(self, tails) -> str:
        study = {"artifact_type": "computational-run", "status": ["unvalidated"],
                 "extension": {"study": {"results": {FOM: {"value": 0.1}}, "tail_sources_simulated": list(tails)}}}
        (self.artifacts / "studies/S-TOF.json").write_text(json.dumps(study), encoding="utf-8")
        project = design.Project(self.artifacts, None)
        evaluation = design.Evaluation(Path("."), ".", {"extension": {
            "candidate": CANDIDATE, "figure_of_merit": FOM, "study_ref": "studies/S-TOF.json", "value": 0.1,
            "bound": "estimate", "denominator": {}}})
        design.check_f4(project, evaluation)
        return evaluation.bound

    def test_mapping_marks_time_resolution_tail_sensitive(self):
        self.assertEqual(design.geometry_mapping("tof").resolve(), MAPPING.resolve())
        doc = json.loads(MAPPING.read_text(encoding="utf-8"))
        self.assertIs(doc["figures_of_merit"][FOM]["tail_sensitive"], True)

    def test_f4_bound_follows_the_protocol_rule(self):
        for tails in ([], ["alignment"], ALL_TAILS[:3], ALL_TAILS):
            with self.subTest(tails=tails):
                self.assertEqual(self.bound(tails), expected_bound(tails))

    def test_negative_control_pre_fix_mapping_is_rejected_by_the_oracle(self):
        doc = json.loads(MAPPING.read_text(encoding="utf-8"))
        doc["figures_of_merit"][FOM]["tail_sensitive"] = False
        copy = Path(self.folder.name) / "tof-pre-fix.json"
        copy.write_text(json.dumps(doc), encoding="utf-8")
        with mock.patch.object(design, "geometry_mapping", lambda kind: copy):
            got = self.bound([])
        self.assertEqual(got, "estimate")
        self.assertNotEqual(got, expected_bound([]))


if __name__ == "__main__":
    unittest.main()
