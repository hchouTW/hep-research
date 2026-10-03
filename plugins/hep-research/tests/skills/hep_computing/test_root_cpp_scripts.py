"""Argument handling of the ROOT C++ helper shell scripts in skills/hep-computing/scripts (no ROOT needed)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / 'skills' / 'hep-computing' / 'scripts'


@unittest.skipUnless(shutil.which('bash'), 'bash not available')
class RootCppScriptArgsTests(unittest.TestCase):
    def run_in(self, cwd, script, *args):
        return subprocess.run(['bash', str(SCRIPTS / script), *args], cwd=cwd, capture_output=True, text=True)

    def test_new_project_help_prints_usage_and_creates_nothing(self):
        for flag in ('-h', '--help'):
            with tempfile.TemporaryDirectory() as tmp:
                proc = self.run_in(tmp, 'new_root_cpp_project.sh', flag)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn('Usage:', proc.stdout)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_new_project_rejects_name_starting_with_dash(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.run_in(tmp, 'new_root_cpp_project.sh', '-foo')
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("must not start with '-'", proc.stderr)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_new_project_with_name_still_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.run_in(tmp, 'new_root_cpp_project.sh', 'demo')
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((Path(tmp) / 'demo' / 'CMakeLists.txt').is_file())
            self.assertTrue((Path(tmp) / 'demo' / 'src' / 'analysis.cpp').is_file())

    def test_env_check_help_exits_zero_without_checking(self):
        for flag in ('-h', '--help'):
            with tempfile.TemporaryDirectory() as tmp:
                proc = self.run_in(tmp, 'check_root_cpp_env.sh', flag)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn('Usage:', proc.stdout)
                self.assertNotIn('Checking CERN ROOT', proc.stdout)


if __name__ == '__main__':
    unittest.main()
