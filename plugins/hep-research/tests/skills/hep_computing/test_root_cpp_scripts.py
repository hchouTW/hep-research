"""Argument handling of the ROOT C++ helper shell scripts in skills/hep-computing/scripts (no ROOT needed)."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / 'skills' / 'hep-computing' / 'scripts'


@unittest.skipUnless(shutil.which('bash'), 'bash not available')
class RootCppScriptArgsTests(unittest.TestCase):
    def run_in(self, cwd, script, *args):
        return subprocess.run(['bash', str(SCRIPTS / script), *args], cwd=cwd, capture_output=True, text=True, timeout=600)

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

    def test_new_project_refuses_to_overwrite(self):
        """CMP-09: a second run silently overwrote an edited project."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.run_in(tmp, 'new_root_cpp_project.sh', 'demo').returncode, 0)
            src = Path(tmp) / 'demo' / 'src' / 'analysis.cpp'
            src.write_text('// edited by hand\n')
            proc = self.run_in(tmp, 'new_root_cpp_project.sh', 'demo')
            self.assertEqual(proc.returncode, 2)
            self.assertIn('not empty', proc.stderr)
            self.assertEqual(src.read_text(), '// edited by hand\n')
            self.assertEqual(self.run_in(tmp, 'new_root_cpp_project.sh', '--force', 'demo').returncode, 0)
            self.assertNotEqual(src.read_text(), '// edited by hand\n')

    def test_new_project_name_is_validated_before_cmake(self):
        for bad in ('bad name', '../x', '/abs/x', 'a) set(EVIL ON', '9lives'):
            with self.subTest(name=bad), tempfile.TemporaryDirectory() as tmp:
                proc = self.run_in(tmp, 'new_root_cpp_project.sh', bad)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_new_project_dir_option_json_and_outputs_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.run_in(tmp, 'new_root_cpp_project.sh', '--dir', 'nested/place', '--json', 'demo')
            self.assertEqual(proc.returncode, 0, proc.stderr)
            doc = json.loads(proc.stdout)
            self.assertEqual((doc['status'], doc['project'], doc['dir']), ('created', 'demo', 'nested/place'))
            cmake = (Path(tmp) / 'nested/place/CMakeLists.txt').read_text()
            self.assertIn('project(demo LANGUAGES CXX)', cmake)
            self.assertIn('ROOT::ROOTDataFrame', cmake)
            self.assertNotIn('ROOT_LIBRARIES', cmake)
            cpp = (Path(tmp) / 'nested/place/src/analysis.cpp').read_text()
            self.assertIn('outDir / "pt.pdf"', cpp)
            self.assertIn('outDir / "output.root"', cpp)
            proc = self.run_in(tmp, 'new_root_cpp_project.sh', '--dir', 'nested/place', '--json', 'demo')
            self.assertEqual((proc.returncode, json.loads(proc.stdout)['status']), (2, 'error'))

    @unittest.skipUnless(shutil.which('cmake') and shutil.which('root-config'), 'cmake and ROOT needed')
    def test_generated_project_configures_and_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.run_in(tmp, 'new_root_cpp_project.sh', 'demo').returncode, 0)
            conf = subprocess.run(['cmake', '-S', 'demo', '-B', 'demo/build'], cwd=tmp, capture_output=True, text=True, timeout=600)
            self.assertEqual(conf.returncode, 0, conf.stdout[-2000:] + conf.stderr[-2000:])
            build = subprocess.run(['cmake', '--build', 'demo/build', '-j'], cwd=tmp, capture_output=True, text=True, timeout=1200)
            self.assertEqual(build.returncode, 0, build.stdout[-2000:] + build.stderr[-2000:])

    def test_env_check_help_exits_zero_without_checking(self):
        for flag in ('-h', '--help'):
            with tempfile.TemporaryDirectory() as tmp:
                proc = self.run_in(tmp, 'check_root_cpp_env.sh', flag)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn('Usage:', proc.stdout)
                self.assertNotIn('Checking CERN ROOT', proc.stdout)


if __name__ == '__main__':
    unittest.main()
