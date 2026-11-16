"""CLI input fuzz of the simulator-calibration scripts, first half (`CALIB_A` of `test_cli_input_fuzz.py`,
by name): that module's tests (malformed JSON inputs, out-of-range numbers, `--help` without NumPy and SciPy) over
these scripts only, split off so that each module stays within the 600 s module limit on CI runners. All inputs
SYNTHETIC."""
import unittest

from tests.skills.hep_statistics.test_cli_input_fuzz import CALIB_A, FuzzCases


class CalibCliInputFuzzA(FuzzCases, unittest.TestCase):
    TARGETS = CALIB_A


if __name__ == "__main__":
    unittest.main()
