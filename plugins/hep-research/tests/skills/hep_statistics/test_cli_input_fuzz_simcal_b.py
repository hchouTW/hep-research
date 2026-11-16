"""CLI input fuzz of the simulator-calibration scripts, second half (`CALIB_B` of `test_cli_input_fuzz.py`,
by name): that module's tests (malformed JSON inputs, out-of-range numbers, `--help` without NumPy and SciPy) over
these scripts only, split off so that each module stays within the 600 s module limit on CI runners. All inputs
SYNTHETIC."""
import unittest

from tests.skills.hep_statistics.test_cli_input_fuzz import CALIB_B, FuzzCases


class CalibCliInputFuzzB(FuzzCases, unittest.TestCase):
    TARGETS = CALIB_B


if __name__ == "__main__":
    unittest.main()
