"""CLI input fuzz for the statistics command-line tools (STH-T3.1): core/stats/*.py and skills/hep-statistics/scripts/*.py.

Every subcommand is driven with malformed inputs of a few classes: a JSON list or an empty object where an object
with fields is expected, NaN inside the input, negative counts, a confidence level outside (0, 1), zero widths or
bins and empty arrays. Each must be refused with exit 2 (the validators may also answer 1, their 'errors' verdict)
and a JSON message on stdout, never a traceback. A second test runs `--help` with NumPy and SciPy hidden: every
script must still print its help. Kept separate from tests/skills/test_cli_robustness.py (missing files, owned by the
hep-computing plan). All inputs SYNTHETIC."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
CORE = sorted(p for p in (PLUGIN / "core" / "stats").glob("*.py") if not p.name.startswith("_") and p.name != "__init__.py")
SCRIPTS = sorted((PLUGIN / "skills" / "hep-statistics" / "scripts").glob("*.py"))
HIDE = ("import runpy, sys; sys.modules['numpy'] = None; sys.modules['scipy'] = None; "
        "sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')")
VALIDATORS = {"validate_covariance.py", "validate_response.py"}
# Modules without a CLI (helpers) are skipped.
NO_CLI = {"broken_power_law.py", "fit_diagnostics.py", "tail_estimation.py", "toy_ensemble.py"}
# Values used for required options that are not under test.
FILL = {"--seed": "1", "--toys": "100", "--method": None, "--param": "2", "--cl": "0.95", "--n": "3", "--b": "2",
        "--on": "10", "--off": "20", "--alpha": "0.5", "--n-data": "100", "--f": "0.2", "--mc-sig": "100",
        "--mc-bkg": "100", "--n1": "100", "--n2": "200", "--s": "2", "--k": "3", "--y": "5", "--x": "3",
        "--label": "observed", "--poi": "mu", "--construction": "asymptotic", "--test-statistic": "q_mu",
        "--artifact-id": "fuzz", "--out": str(Path(tempfile.gettempdir()) / "hep-fuzz-never-written.json")}
# (option, value) pairs that are valid inputs: they must still give JSON and no traceback, but may succeed
VALID_EDGE = {("--y", "0")}  # pcl_efficiency_ratio.py ratio: the Fieller set exists for y = 0 (no point estimate)


def run(args, timeout=300, hide=False):
    cmd = [sys.executable, "-c", HIDE] + [str(a) for a in args] if hide else [sys.executable] + [str(a) for a in args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(PLUGIN))


def help_text(script, sub=None):
    return run([script] + ([sub] if sub else []) + ["--help"]).stdout


def subcommands(script):
    m = re.search(r"usage: \S+(?: \[-h\])? \{([a-z0-9,-]+)\}", re.sub(r"\s+", " ", help_text(script).split("\n\n")[0]))
    return m.group(1).split(",") if m else [None]


def options(script, sub):
    """(required options with a metavar, all option names, choices of --method) from the usage text."""
    text = help_text(script, sub)
    usage = text.split("\n\n")[0]
    flat = re.sub(r"\s+", " ", usage)
    # strip optional groups [ ... ] (one nesting level is enough here)
    req_part = re.sub(r"\[[^\[\]]*\]", "", re.sub(r"\[[^\[\]]*\[[^\[\]]*\][^\[\]]*\]", "", flat))
    required = re.findall(r"(--[a-z0-9-]+)(?: ([A-Z_{}0-9,.-]+))?", req_part)
    names = set(re.findall(r"(--[a-z0-9-]+)", text))
    m = re.search(r"--method \{([a-z0-9,-]+)\}", flat)
    return required, names, (m.group(1).split(",") if m else None)


def base_args(script, sub, required, methods, input_path):
    args = [script] + ([sub] if sub else [])
    positional = sub is None and script.name in VALIDATORS
    if positional:
        return args + [input_path]
    for name, meta in required:
        if name == "--help":
            continue
        if name in ("--input", "--cli-output"):
            args += [name, input_path]
        elif name == "--method":
            args += [name, (methods or ["tikhonov"])[-1 if methods and "tikhonov" not in methods else methods.index("tikhonov")]]
        elif meta == "" or meta is None:
            args += [name]
        else:
            args += [name, FILL.get(name) or "1"]
    return args


class CliInputFuzz(unittest.TestCase):
    def check(self, cp, label, allow_one=False):
        self.assertNotIn("Traceback", cp.stderr, (label, cp.stderr[-1500:]))
        ok_codes = (1, 2) if allow_one else (2,)
        self.assertIn(cp.returncode, ok_codes, (label, cp.stdout[-600:], cp.stderr[-600:]))
        try:
            json.loads(cp.stdout)
        except ValueError:
            self.fail(f"{label}: stdout is not JSON: {cp.stdout[-400:]!r} {cp.stderr[-400:]!r}")

    def test_malformed_json_inputs_are_refused(self):
        try:
            import numpy  # noqa: F401
            import scipy  # noqa: F401
        except ImportError:
            self.skipTest("NumPy and SciPy needed to reach the input checks of every script")
        bad_docs = {"json_list": [1, 2, 3], "empty_object": {}, "nan_inside": {"bins": [{"n": float("nan"), "b": 1, "s": 1}],
                                                                              "matrix": [[float("nan")]], "labels": ["a"],
                                                                              "kind": "absolute", "y": [float("nan")],
                                                                              "response": [[float("nan")]], "truth": [1.0]}}
        with tempfile.TemporaryDirectory() as td:
            paths = {}
            for k, d in bad_docs.items():
                p = Path(td) / f"{k}.json"
                p.write_text(json.dumps(d))
                paths[k] = str(p)
            for script in CORE + SCRIPTS:
                if script.name in NO_CLI:
                    continue
                for sub in subcommands(script):
                    required, names, methods = options(script, sub)
                    takes_file = script.name in VALIDATORS or any(n in ("--input", "--cli-output") for n, _ in required)
                    if not takes_file:
                        continue
                    for k, p in paths.items():
                        with self.subTest(script=script.name, sub=sub, case=k):
                            cp = run(base_args(script, sub, required, methods, p))
                            self.check(cp, f"{script.name} {sub} {k}", allow_one=script.name in VALIDATORS)

    def test_out_of_range_numbers_are_refused(self):
        try:
            import numpy  # noqa: F401
            import scipy  # noqa: F401
        except ImportError:
            self.skipTest("NumPy and SciPy needed")
        mutations = {"--cl": ["1.5", "0", "nan"], "--n": ["-1"], "--b": ["-2", "nan"], "--bins": ["0"], "--y": ["0"],
                     "--toys": ["-5"], "--width": ["0"]}
        for script in CORE + SCRIPTS:
            if script.name in NO_CLI or script.name in VALIDATORS:
                continue
            for sub in subcommands(script):
                required, names, methods = options(script, sub)
                if any(n in ("--input", "--cli-output") for n, _ in required):
                    continue  # covered by the JSON-input fuzz (and by the module tests)
                base = base_args(script, sub, required, methods, None)
                for opt, values in mutations.items():
                    if opt not in names:
                        continue
                    for v in values:
                        args = list(base)
                        if opt in args:
                            args[args.index(opt) + 1] = v
                        else:
                            args += [opt, v]
                        with self.subTest(script=script.name, sub=sub, opt=opt, value=v):
                            cp = run(args)
                            if (opt, v) in VALID_EDGE and cp.returncode == 0:
                                self.assertNotIn("Traceback", cp.stderr)
                                json.loads(cp.stdout)
                            else:
                                self.check(cp, f"{script.name} {sub} {opt}={v}")

    def test_confirmed_audit_crashes(self):
        """The crashes the audit confirmed: pcl ratio --y 0 (ZeroDivisionError), sbc --bins 0 (modulo by zero),
        a zero signal width in sweighted_fit, a JSON list into result_artifact (AttributeError)."""
        try:
            import numpy  # noqa: F401
            import scipy  # noqa: F401
        except ImportError:
            self.skipTest("NumPy and SciPy needed")
        sc = PLUGIN / "skills" / "hep-statistics" / "scripts"
        cp = run([sc / "pcl_efficiency_ratio.py", "ratio", "--x", "3", "--sx", "1", "--y", "0", "--sy", "1"])
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        out = json.loads(cp.stdout)
        self.assertIsNone(out["delta_method"]["interval"])
        self.assertIn(out["fieller"]["kind"], ("complement", "unbounded"))
        self.check(run([sc / "bayes_calibration.py", "sbc", "--bins", "0", "--reps", "10"]), "sbc --bins 0")
        with tempfile.TemporaryDirectory() as td:
            ev = Path(td) / "ev.json"
            ev.write_text(json.dumps({"m": [i / 100 for i in range(100)], "t": [1.0] * 100, "signal": {"mean": 0.5, "width": 0}}))
            self.check(run([sc / "sweighted_fit.py", "fit", "--input", ev, "--bootstrap", "0"]), "sweighted width 0")
            lst = Path(td) / "l.json"
            lst.write_text("[1, 2]")
            self.check(run([sc / "result_artifact.py", "--cli-output", lst, "--poi", "mu", "--construction", "asymptotic",
                            "--test-statistic", "q_mu", "--label", "observed", "--artifact-id", "x",
                            "--out", Path(td) / "o.json"]), "result_artifact list")

    def test_help_without_numpy(self):
        for script in CORE + SCRIPTS:
            if script.name in NO_CLI:
                continue
            with self.subTest(script.name):
                cp = run([script, "--help"], hide=True)
                self.assertEqual(cp.returncode, 0, (script.name, cp.stdout[-300:], cp.stderr[-600:]))
                self.assertTrue(cp.stdout.strip(), script.name)


if __name__ == "__main__":
    unittest.main()
