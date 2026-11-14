"""Tests of scripts/check_eic_conventions.py (the EIC configuration checker): two positive fixtures, one negative case
per rule code, the deprecated-key hint, --profiles-from vocabulary handling and non-JSON input. Every negative case
is a positive fixture with one documented change, written to a temporary folder and run as a subprocess.
Run from the profile folder: python3 -m unittest discover -s tests -t tests -v"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT.parents[2]
SCRIPT = ROOT / "scripts" / "check_eic_conventions.py"
FIXTURES = ROOT / "tests" / "fixtures"
MEASUREMENT = json.loads((FIXTURES / "measurement_spec_positive.json").read_text(encoding="utf-8"))
THEORY = json.loads((FIXTURES / "theory_spec_positive.json").read_text(encoding="utf-8"))
PROFILE_VERSION = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))["version"]
RULE_CODES = ("eic.configuration_missing", "eic.frame_conflated", "eic.ion_normalization_missing",
              "eic.polarization_convention_missing", "eic.azimuth_convention_missing", "eic.crossing_angle_undeclared",
              "eic.beam_value_unsourced", "eic.projection_unlabelled", "eic.scope_mixing")


def conventions(spec):
    return spec["extension"]["observable"]["conventions"]


def beams(spec):
    return spec["extension"]["experiment_fields"]["eic:beams"]


def without_configuration(spec):
    del conventions(spec)["eic:beam_energy_configuration"]


def without_rapidity_frame(spec):
    del conventions(spec)["rapidity_frame"]


def gold_without_mass_number(spec):
    beams(spec)["hadron"] = {"species": "Au", "Z": 79, "energy_per_nucleon_GeV": {"value": 110, "source": "eic:C46"},
                             "polarization": None}


def polarized_without_convention(spec):
    del conventions(spec)["polarization_convention"]


def azimuthal_without_convention(spec):
    spec["objective"] += "; Sivers and Collins modulations in the Trento frame"
    del conventions(spec)["azimuth_convention"]


def without_crossing_angle_treatment(spec):
    del conventions(spec)["eic:crossing_angle_treatment"]


def unsourced_energy(spec):
    beams(spec)["electron"]["energy_GeV"] = {"value": 19, "source": "eic:C44"}


def projection_without_release(spec):
    spec["status"] = spec["status"] + ["projection"]


def facility_and_detector_merged(spec):
    spec["objective"] += "; resolution of the " + " ".join(("EIC", "detector")) + " assumed"  # phrase built at run time


NEGATIVE_CASES = {
    "eic.configuration_missing": without_configuration,
    "eic.frame_conflated": without_rapidity_frame,
    "eic.ion_normalization_missing": gold_without_mass_number,
    "eic.polarization_convention_missing": polarized_without_convention,
    "eic.azimuth_convention_missing": azimuthal_without_convention,
    "eic.crossing_angle_undeclared": without_crossing_angle_treatment,
    "eic.beam_value_unsourced": unsourced_energy,
    "eic.projection_unlabelled": projection_without_release,
    "eic.scope_mixing": facility_and_detector_merged,
}


class CheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workdir = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.workdir.name)

    @classmethod
    def tearDownClass(cls):
        cls.workdir.cleanup()

    def run_checker(self, spec_path, *extra):
        proc = subprocess.run([sys.executable, str(SCRIPT), str(spec_path), *extra], capture_output=True, text=True,
                              timeout=120, cwd=PLUGIN)
        return proc.returncode, (json.loads(proc.stdout) if proc.stdout.strip() else {})

    def write_spec(self, name, spec):
        path = self.folder / f"{name}.json"
        path.write_text(json.dumps(spec, indent=1), encoding="utf-8")
        return path

    def codes(self, report, level=None):
        return [d["code"] for d in report["defects"] if level is None or d["level"] == level]

    def test_positive_fixtures_pass_the_checker_and_the_contract(self):
        for name in ("measurement_spec_positive.json", "theory_spec_positive.json"):
            with self.subTest(name):
                code, report = self.run_checker(FIXTURES / name)
                self.assertEqual(code, 0, report)
                self.assertEqual(report["verdict"], "acceptable-with-open-inputs")
                self.assertEqual(self.codes(report), [])
                proc = subprocess.run([sys.executable, str(PLUGIN / "contracts" / "validate.py"), str(FIXTURES / name)],
                                      capture_output=True, text=True, timeout=120, cwd=PLUGIN)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_user_supplied_values_are_unresolved(self):
        _, report = self.run_checker(FIXTURES / "theory_spec_positive.json")
        self.assertEqual(sorted(u["path"].rsplit(".", 1)[-1] for u in report["unresolved"]),
                         ["crossing_angle_mrad", "energy_GeV", "energy_per_nucleon_GeV"])

    def test_each_negative_case_reports_only_its_own_code(self):
        self.assertEqual(sorted(NEGATIVE_CASES), sorted(RULE_CODES))
        for rule_code, change in NEGATIVE_CASES.items():
            with self.subTest(rule_code):
                spec = copy.deepcopy(MEASUREMENT)
                change(spec)
                code, report = self.run_checker(self.write_spec(rule_code, spec))
                self.assertEqual(code, 1, report)
                self.assertEqual(sorted(set(self.codes(report))), [rule_code], report)
                levels = {d["level"] for d in report["defects"]}
                self.assertEqual(report["verdict"], "blocked" if "error" in levels else "needs-work")

    def test_two_level_codes_use_the_error_level_in_their_negative_case(self):
        for rule_code in ("eic.polarization_convention_missing", "eic.projection_unlabelled"):
            spec = copy.deepcopy(MEASUREMENT)
            NEGATIVE_CASES[rule_code](spec)
            _, report = self.run_checker(self.write_spec(rule_code + "-level", spec))
            self.assertEqual(self.codes(report, "error"), [rule_code], report)

    def test_warning_levels(self):
        spec = copy.deepcopy(THEORY)
        spec["objective"] += "; a double-spin asymmetry projection"
        del spec["extension"]["conventions"]["polarization_convention"]
        _, report = self.run_checker(self.write_spec("warnings", spec))
        self.assertEqual(sorted(self.codes(report, "warning")), ["eic.polarization_convention_missing", "eic.projection_unlabelled"])
        self.assertEqual(report["verdict"], "needs-work")

    def test_lab_equals_cm_frame_is_conflated(self):
        spec = copy.deepcopy(MEASUREMENT)
        conventions(spec)["frame"] = "lab frame = CM"
        _, report = self.run_checker(self.write_spec("lab-cm", spec))
        self.assertEqual(self.codes(report), ["eic.frame_conflated"])

    def test_polarization_fraction_matches_a_percentage_claim(self):
        spec = copy.deepcopy(MEASUREMENT)
        beams(spec)["electron"]["polarization"] = {"value": 0.07, "source": "eic:C43"}
        _, report = self.run_checker(self.write_spec("polarization-fraction", spec))
        self.assertEqual(self.codes(report), ["eic.beam_value_unsourced"])

    def test_frozen_or_non_numeric_claim_cannot_source_a_value(self):
        for source in ("eic:C17", "eic:C06"):
            spec = copy.deepcopy(MEASUREMENT)
            beams(spec)["crossing_angle_mrad"] = {"value": 25, "source": source}
            _, report = self.run_checker(self.write_spec("source-" + source[-3:], spec))
            self.assertEqual(self.codes(report), ["eic.beam_value_unsourced"], source)

    def test_proposal_citation_is_a_scope_mixing_reminder(self):
        spec = copy.deepcopy(MEASUREMENT)
        beams(spec)["electron"]["energy_GeV"] = {"value": 9, "source": "eic:C82"}
        code, report = self.run_checker(self.write_spec("proposal", spec))
        self.assertEqual(code, 1)
        self.assertEqual(self.codes(report), ["eic.scope_mixing"])

    def test_deprecated_key_is_an_info_hint(self):
        spec = copy.deepcopy(MEASUREMENT)
        conventions(spec)["eic:polarization_sign"] = "helicity sign as in the analysis note"
        code, report = self.run_checker(self.write_spec("deprecated", spec))
        self.assertEqual(code, 0, report)
        self.assertEqual(report["verdict"], "acceptable-with-open-inputs")
        self.assertEqual([(d["code"], d["level"]) for d in report["defects"]], [("eic.deprecated_key", "info")])
        self.assertIn("polarization_convention", report["defects"][0]["message"])

    def test_profiles_from_reports_only_unknown_keys(self):
        project = self.folder / "project"
        project.mkdir(exist_ok=True)
        config = project / "hep-research.project.json"
        config.write_text(json.dumps({"schema_version": "1.0.0", "plugin_version": ">=0.1,<1.0",
                                      "experiments": [{"profile": "experiment:eic", "version": PROFILE_VERSION}],
                                      "theory": []}), encoding="utf-8")
        code, report = self.run_checker(FIXTURES / "measurement_spec_positive.json", "--profiles-from", str(config))
        self.assertEqual(code, 0, report)
        self.assertEqual(self.codes(report), [], "core keys such as rapidity_frame and the eic: keys are known")
        spec = copy.deepcopy(MEASUREMENT)
        conventions(spec)["eic:unknown_convention"] = "not declared by the profile"
        code, report = self.run_checker(self.write_spec("unknown-key", spec), "--profiles-from", str(config))
        self.assertEqual(code, 0, report)
        self.assertEqual([(d["code"], d["level"]) for d in report["defects"]], [("eic.unknown_key_info", "info")])

    def test_invalid_project_config_exits_two(self):
        config = self.folder / "bad" / "hep-research.project.json"
        config.parent.mkdir(exist_ok=True)
        config.write_text(json.dumps({"schema_version": "1.0.0", "plugin_version": ">=0.1,<1.0",
                                      "experiments": [{"profile": "experiment:eic", "version": "9.9.9"}], "theory": []}),
                          encoding="utf-8")
        code, report = self.run_checker(FIXTURES / "measurement_spec_positive.json", "--profiles-from", str(config))
        self.assertEqual(code, 2, report)

    def test_non_json_and_non_spec_inputs_exit_two(self):
        text_file = self.folder / "not-json.json"
        text_file.write_text("this is not JSON", encoding="utf-8")
        self.assertEqual(self.run_checker(text_file)[0], 2)
        self.assertEqual(self.run_checker(self.write_spec("not-a-spec", {"artifact_type": "statistical-result"}))[0], 2)

    def test_fixtures_and_script_do_not_contain_the_prohibited_phrase(self):
        phrase = " ".join(("EIC", "detector")).lower()
        for path in [SCRIPT, Path(__file__)] + sorted(FIXTURES.glob("*.json")):
            self.assertNotIn(phrase, path.read_text(encoding="utf-8").lower(), path.name)


if __name__ == "__main__":
    unittest.main()
