"""pyproject.toml stays consistent with the plugin (T18): its version is the plugin's, its extras match the
requirements files, the CI lock pins every package of the core and test extras, and the tool configuration covers
the folders CI lints."""
import json
import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def requirement_lines(path: Path) -> list[str]:
    return [l.split("#")[0].strip() for l in path.read_text(encoding="utf-8").splitlines()
            if l.split("#")[0].strip() and not l.startswith("-r")]


# "Python 3.12", "Python >= 3.11", "Python ≥ 3.9", "Python 3.11.15": a Python version named in prose
PYTHON_MENTION = re.compile(r"Python\s*(?:>=|≥)?\s*3\.([0-9]+)")
# Dated history the capability matrix keeps on purpose: results measured on Pythons that are no longer supported.
# Each entry is the start of one paragraph or table row; it is excluded from the old-floor check, and must still exist.
CAPABILITY_MATRIX_HISTORY = ("Environment E1 ", "Environment E3 ", "Python floor (2026-10-15):",
                             "| ROOT, PyROOT tools | tested (E3 + ")


def statements(text: str) -> list[str]:
    """Paragraphs of a Markdown file, with each table row its own statement."""
    out = []
    for para in re.split(r"\n\s*\n", text):
        lines = [line for line in para.strip().splitlines() if line.strip()]
        if lines and all(line.startswith("|") for line in lines):
            out.extend(lines)
        elif lines:
            out.append(" ".join(lines))
    return out


def old_python_mentions(text: str, history: tuple[str, ...] = ()) -> list[str]:
    """Statements (outside `history`) that name a Python 3 version below the 3.13 floor."""
    return [st for st in statements(text) if not st.startswith(history)
            and any(int(minor) < 13 for minor in PYTHON_MENTION.findall(st))]


def name(req: str) -> str:
    return re.split(r"[<>=!~\[ ]", req, maxsplit=1)[0].lower()


class PyprojectTests(unittest.TestCase):
    def test_version_matches_the_plugin(self):
        for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            self.assertEqual(PYPROJECT["project"]["version"], json.loads((ROOT / manifest).read_text())["version"], manifest)

    def test_extras(self):
        extras = PYPROJECT["project"]["optional-dependencies"]
        self.assertEqual(set(extras), {"core", "pyhf", "root-uproot", "columnar", "hepdata", "torch", "pdg", "bdt", "diagrams", "test", "lint"})
        self.assertEqual(sorted(extras["core"]), sorted(requirement_lines(ROOT / "requirements-core.txt")))
        self.assertEqual(sorted(extras["test"]), sorted(requirement_lines(ROOT / "requirements-test.txt")))

    def test_lock_pins_the_core_and_test_extras(self):
        lock = {name(l): l.split("==")[1] for l in requirement_lines(ROOT / "requirements-ci.lock")}
        self.assertTrue(all("==" in l for l in requirement_lines(ROOT / "requirements-ci.lock")))
        for req in PYPROJECT["project"]["optional-dependencies"]["core"] + PYPROJECT["project"]["optional-dependencies"]["test"]:
            self.assertIn(name(req), lock, req)
        for bound in requirement_lines(ROOT / "requirements-ci-constraints.txt"):
            pkg, ceiling = bound.split("<")
            if pkg in lock:
                pinned = tuple(int(x) for x in lock[pkg].split(".")[:2])
                self.assertLess(pinned, tuple(int(x) for x in ceiling.split(".")[:2]), bound)

    def test_tool_configuration(self):
        self.assertEqual(PYPROJECT["tool"]["mypy"]["files"], ["core", "contracts"])
        self.assertIn("F", PYPROJECT["tool"]["ruff"]["lint"]["select"])
        self.assertEqual(PYPROJECT["tool"]["setuptools"]["packages"], [])  # the plugin is not an installable package

    def test_python_floor_is_313_everywhere(self):
        """requires-python, the Ruff and mypy targets and the interpreter finder's default name the same floor."""
        self.assertEqual(PYPROJECT["project"]["requires-python"], ">=3.13")
        self.assertEqual(PYPROJECT["tool"]["ruff"]["target-version"], "py313")
        self.assertEqual(PYPROJECT["tool"]["mypy"]["python_version"], "3.13")
        finder = (ROOT / "skills" / "hep-computing" / "scripts" / "find_python.py").read_text(encoding="utf-8")
        self.assertIn('MIN_PYTHON = "3.13"', finder)

    def test_readme_states_the_floor(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Python 3.13 or newer", readme)
        self.assertNotRegex(readme, r"Python (>= ?)?3\.1[12]( or newer)?\b")
        self.assertEqual(old_python_mentions(readme), [])

    def test_deployment_model_states_the_floor(self):
        text = (ROOT / "docs" / "deployment-model.md").read_text(encoding="utf-8")
        self.assertRegex(text, r"Python ≥ 3\.13\b")
        self.assertEqual(old_python_mentions(text), [])

    def test_capability_matrix_states_the_floor_and_keeps_its_history(self):
        """Current statements name no Python below 3.13; the dated E1/E3 environment lines, the dated floor note and
        the E3 ROOT row are history, excluded by name here and kept in the file."""
        text = (ROOT / "docs" / "capability-matrix.md").read_text(encoding="utf-8")
        self.assertIn("the plugin requires Python 3.13", text)
        for start in CAPABILITY_MATRIX_HISTORY:
            matching = [st for st in statements(text) if st.startswith(start)]
            self.assertEqual(len(matching), 1, f"historical statement {start!r} is missing or ambiguous")
        self.assertEqual(old_python_mentions(text, CAPABILITY_MATRIX_HISTORY), [])

    def test_old_python_mentions_finds_current_old_floor_statements(self):
        """The check itself: old floors in any spelling are found; the 3.13 floor and history are not."""
        for bad in ("needs Python 3.11 or newer", "Python >= 3.12", "Python ≥ 3.9 (tested on 3.11)",
                    "| Tool | tested under Python 3.12.4 |"):
            self.assertEqual(len(old_python_mentions(bad)), 1, bad)
        for good in ("Python 3.13 or newer", "Python ≥ 3.13 (tested on 3.13)", "Python 3.14.0",
                     "3.11 and 3.12 are no longer supported"):
            self.assertEqual(old_python_mentions(good), [], good)
        self.assertEqual(old_python_mentions("Environment E1 : Python 3.11.15", ("Environment E1 ",)), [])

    @unittest.skipUnless((ROOT.parents[1] / ".github" / "workflows" / "tests.yml").is_file(),
                         "repository checkout only (an installed plugin tree has no .github)")
    def test_ci_follows_the_floor(self):
        """CI tests the supported floor only (Python 3.13: the checks matrix and the reconciliation gate agree)."""
        workflow = (ROOT.parents[1] / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        matrix = re.search(r'python: \[([^\]]*)\]', workflow).group(1)
        self.assertEqual([v.strip(' "') for v in matrix.split(",")], ["3.13"])
        self.assertRegex(workflow, r"reconcile_check_runs\.py \S+ --python 3\.13 ")
        # the old-python job sets up a real 3.9 on purpose: it checks that the interpreter guard stops it
        old_job = re.search(r"(?ms)^  old-python:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", workflow)
        self.assertIsNotNone(old_job, "the old-python job (interpreter guard under a real 3.9) is missing")
        self.assertEqual(re.findall(r'python-version: "?([0-9.]+)', old_job.group(1)), ["3.9", "3.13"])
        rest = workflow[:old_job.start()] + workflow[old_job.end():]
        for v in re.findall(r'python-version: "?([0-9.]+)', rest):
            self.assertEqual(v, "3.13", "every other setup-python step uses the floor")


    @unittest.skipUnless((ROOT.parents[1] / ".github" / "workflows" / "tests.yml").is_file(),
                         "repository checkout only (an installed plugin tree has no .github)")
    def test_torch_backend_job_lists_every_module_with_pytorch_tests(self):
        """The required torch-backend job names its modules: every test module that marks a PyTorch test (a torch
        find_spec guard or a 'PyTorch not installed' / 'PyTorch is required' skip) must be listed, except the opt-in
        GPU module, which needs a CUDA device the CI runners do not have (and this module, which spells the markers)."""
        workflow = (ROOT.parents[1] / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        job = re.search(r"(?ms)^  torch-backend:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", workflow).group(1)
        listed = set(re.search(r"--modules (\S+)", job).group(1).split(","))
        marker = re.compile(r'find_spec\("torch"\)|PyTorch not installed|PyTorch is required')
        marked = {".".join(path.relative_to(ROOT).with_suffix("").parts) for path in (ROOT / "tests").rglob("test_*.py")
                  if marker.search(path.read_text(encoding="utf-8"))}
        self.assertEqual(listed, marked - {"tests.skills.hep_ml.test_gpu_real", "tests.tools.test_pyproject"})

    @unittest.skipUnless((ROOT.parents[1] / ".github" / "workflows" / "tests.yml").is_file(),
                         "repository checkout only (an installed plugin tree has no .github)")
    def test_bdt_backend_job_lists_every_module_with_bdt_tests(self):
        """The required bdt-backend job names its modules: every test module that marks an xgboost or scikit-learn
        test (a find_spec guard for xgboost or sklearn, or an 'xgboost ... not installed' / 'scikit-learn ... not
        installed' skip) must be listed (except this module, which spells the markers). A scikit-learn skip reason
        names sklearn, the import name run_required_backends.py matches, so such a skip fails the job; the job pins
        every package of the `bdt` extra, within the extra's range."""
        workflow = (ROOT.parents[1] / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        job = re.search(r"(?ms)^  bdt-backend:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", workflow).group(1)
        listed = set(re.search(r"--modules (\S+)", job).group(1).split(","))
        marker = re.compile(r'find_spec\("(?:xgboost|sklearn)"\)|(?:xgboost|scikit-learn)[^"\n]*not installed')
        marked = set()
        for path in (ROOT / "tests").rglob("test_*.py"):
            text = path.read_text(encoding="utf-8")
            if marker.search(text):
                marked.add(".".join(path.relative_to(ROOT).with_suffix("").parts))
                for reason in re.findall(r'"[^"\n]*scikit-learn[^"\n]*not installed[^"\n]*"', text):
                    self.assertIn("sklearn", reason, f"{path.name}: a scikit-learn skip reason must name sklearn")
        self.assertEqual(listed, marked - {"tests.tools.test_pyproject"})
        required = dict(x.split("==") for x in re.search(r"--require (\S+)", job).group(1).split(","))
        self.assertEqual(set(required), {"xgboost", "sklearn"})
        pinned = dict(re.findall(r'"([A-Za-z0-9_.-]+)==([0-9][^"]*)"', job))
        self.assertEqual(pinned["xgboost"], required["xgboost"])
        self.assertEqual(pinned["scikit-learn"], required["sklearn"])
        for req in PYPROJECT["project"]["optional-dependencies"]["bdt"]:
            name = re.match(r"[A-Za-z0-9_.-]+", req).group(0)
            self.assertIn(name, pinned, f"the bdt extra's {name} is not pinned in the job")
            lo, hi = re.search(r">=([0-9.]+),<([0-9.]+)", req).groups()
            version = tuple(int(x) for x in pinned[name].split("."))
            self.assertTrue(tuple(map(int, lo.split("."))) <= version < tuple(map(int, hi.split("."))),
                            f"{name}=={pinned[name]} outside the bdt extra {req}")

    @unittest.skipUnless((ROOT.parents[1] / ".github" / "workflows" / "tests.yml").is_file(),
                         "repository checkout only (an installed plugin tree has no .github)")
    def test_slow_tier_job_has_a_larger_module_timeout(self):
        """The weekly `latest` job runs the slow tier, where tests.examples.test_stats_benchmarks alone takes about
        525-545 s, near the default 600 s module limit: the job sets HEP_MODULE_TIMEOUT to at least 1800 s, and the
        maintenance notes say so."""
        workflow = (ROOT.parents[1] / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        job = re.search(r"(?ms)^  latest:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", workflow).group(1)
        self.assertRegex(job, r'HEP_SLOW_TESTS: "1"')
        timeout = re.search(r'HEP_MODULE_TIMEOUT: "?([0-9]+)"?', job)
        self.assertIsNotNone(timeout, "the latest job sets HEP_MODULE_TIMEOUT")
        self.assertGreaterEqual(int(timeout.group(1)), 1800)
        notes = " ".join((ROOT / "docs" / "maintenance.md").read_text(encoding="utf-8").split())
        self.assertIn(f"HEP_MODULE_TIMEOUT={timeout.group(1)}", notes)


if __name__ == "__main__":
    unittest.main()
