"""S7: the uniform --allow-outside-validated-range override of the core/stats caps, the outside-validated-range label and
the publication gate, the pyhf conversion on the asymptotic path, the input format in every --help, and the runtime
notice of long toy runs. Oracle: a 72-bin model run with the override agrees with pyhf asymptotics to 1% (pyhf
optional). Inputs are SYNTHETIC."""
import argparse
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
from core.stats import _caps  # noqa: E402

LL = PLUGIN / "core" / "stats" / "likelihood_limits.py"
OPTION = "--allow-outside-validated-range"
BINS72 = {"bins": [{"n": 5, "b": 5.0, "s": 0.4 + 0.01 * i} for i in range(72)], "cl": 0.95}


def run(script, *args):
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True, timeout=600)
    out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else None
    return p.returncode, out, p.stderr


def write(d, name, doc):
    p = Path(d) / name
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


class Override(unittest.TestCase):
    def test_refused_without_and_labeled_with_the_override(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "b72.json", BINS72)
            code, out, _ = run(LL, "multibin-limit", "--input", p, "--seed", "1")
            self.assertEqual(code, 2)
            self.assertIn(OPTION, out["error"])
            code, out, err = run(LL, "multibin-limit", "--input", p, "--seed", "1", OPTION)
        self.assertEqual(code, 0, err)
        self.assertEqual(out["range_label"], "outside-validated-range")
        self.assertIn({"cap": "multibin-limit bins", "value": 72, "limit": 50}, out["outside_validated_range"])

    def test_inside_the_caps_the_option_changes_nothing(self):
        small = {"bins": BINS72["bins"][:5], "cl": 0.95}
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "b5.json", small)
            _, a, _ = run(LL, "multibin-limit", "--input", p, "--seed", "1")
            _, b, _ = run(LL, "multibin-limit", "--input", p, "--seed", "1", OPTION)
        self.assertEqual(a, b)
        self.assertNotIn("range_label", b)

    def test_every_overridable_cap_takes_the_same_option(self):
        cases = [
            ("template_fit", ["bb-fit"], {"data": [3] * 61, "templates": {"a": [5] * 61}}, "template_fit bins"),
            ("statistical_toys", ["unfold-scan", "--toys", "20", "--seed", "1"],
             {"response": [[1.0 if i == j else 0.0 for j in range(61)] for i in range(61)], "truth": [10.0] * 61,
              "max_iterations": 2}, "unfold-scan bins"),
            ("likelihood_limits", ["shape-limit", "--seed", "1"],
             {"bins": [{"n": 3, "b": 3.0, "s": 1.0}] * 4, "nuisances": [{"kind": "background_norm", "sigma": 0.1}] * 9},
             "shape-limit nuisances"),
        ]
        for module, args, doc, cap in cases:
            with self.subTest(module=module), tempfile.TemporaryDirectory() as d:
                p = write(d, "in.json", doc)
                script = PLUGIN / "core" / "stats" / f"{module}.py"
                code, out, _ = run(script, *args[:1], "--input", p, *args[1:])
                self.assertEqual(code, 2, out)
                self.assertIn(OPTION, out["error"])
                code, out, err = run(script, *args[:1], "--input", p, *args[1:], OPTION)
                self.assertIn(code, (0, 1), err)
                self.assertIn(cap, [e["cap"] for e in out["outside_validated_range"]])

    def test_library_context_manager_resets(self):
        class E(ValueError):
            pass
        with self.assertRaises(E):
            _caps.exceed("x", 2, 1, E, "x too large")
        with _caps.outside_validated_range():
            _caps.exceed("x", 2, 1, E, "x too large")
            self.assertEqual(_caps.report()["range_label"], "outside-validated-range")
        with self.assertRaises(E):
            _caps.exceed("x", 2, 1, E, "x too large")


class LabelAndGate(unittest.TestCase):
    def base(self):
        return json.loads((PLUGIN / "examples" / "collider-angular" / "output" / "artifacts" / "result.json").read_text())

    def test_vocabulary(self):
        vocab = json.loads((PLUGIN / "contracts" / "vocab" / "core.json").read_text())["vocabularies"]
        self.assertIn("outside-validated-range", vocab["artifact_statuses"])

    def test_gate_refuses_the_label_without_a_validation_record(self):
        from contracts.validate import publication_gate
        doc = self.base()
        doc["status"] = doc["status"] + ["outside-validated-range"]
        g = publication_gate(doc)
        self.assertIn("gate.outside_validated_range", [r["code"] for r in g["reasons"] if r["level"] == "failed"])
        doc["extension"]["validation_record"] = {
            "validation_record_version": "1.0.0",
            "claim": {"effect": "multibin-limit beyond its 50-bin cap", "relation": "correlated"},
            "subjects": [{"root": doc["artifact_id"], "version": "1"}, {"root": "pyhf asymptotic CLs", "version": "0.7.6"}],
            "method": "the same 72-bin model in core (override) and in pyhf, asymptotic CLs (qtilde)",
            "tolerance": "1% relative on the observed limit", "scope": "72 bins, no nuisances",
            "conclusion": "agree within 1%"}
        g2 = publication_gate(doc)
        codes = [r["code"] for r in g2["reasons"]]
        self.assertNotIn("gate.outside_validated_range", codes)
        doc["extension"]["validation_record"] = {"claim": "missing fields"}
        g3 = publication_gate(doc)
        self.assertIn("gate.validation_record_invalid", [r["code"] for r in g3["reasons"] if r["level"] == "failed"])


class ResultArtifactCarriesTheLabel(unittest.TestCase):
    def test_label_travels_into_the_statistical_result_and_fails_the_gate(self):
        from contracts.validate import publication_gate
        ra = PLUGIN / "skills" / "hep-statistics" / "scripts" / "result_artifact.py"
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "b72.json", BINS72)
            code, out, err = run(LL, "multibin-limit", "--input", p, "--seed", "1", OPTION)
            self.assertEqual(code, 0, err)
            cli = write(d, "cli.json", out)
            res = Path(d) / "res.json"
            code, _, err = run(ra, "--cli-output", cli, "--poi", "mu", "--construction", "asymptotic",
                               "--test-statistic", "q_mu_tilde", "--label", "synthetic", "--artifact-id", "s7-72-bins",
                               "--model", p, "--out", res)
            self.assertEqual(code, 0, err)
            doc = json.loads(res.read_text())
        self.assertIn("outside-validated-range", doc["status"])
        self.assertIn("gate.outside_validated_range", [r["code"] for r in publication_gate(doc)["reasons"]])


class CapsTableAdditions(unittest.TestCase):
    def test_nuisance_and_tsvd_caps_are_in_the_table(self):
        guide = (PLUGIN / "skills" / "hep-statistics" / "references" / "core-stats-guide.md").read_text(encoding="utf-8")
        table = guide[guide.index("| Where | Cap | Beyond it |"):]
        self.assertRegex(table, r"shape-limit` with toys[^\n]*nuisances <= 8")
        self.assertRegex(table, r"tsvd[^\n]*truth bins <= 20")
        self.assertRegex(table, r"tsvd[^\n]*bins <= 15")
        self.assertIn(OPTION, guide)


class HelpStatesTheInputFormat(unittest.TestCase):
    def test_every_input_option_describes_its_json(self):
        for m in ("likelihood_limits", "statistical_toys", "template_fit", "unfolding_diagnostics"):
            parser = importlib.import_module(f"core.stats.{m}").build_parser()
            sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
            for name, sp in sub.choices.items():
                for action in sp._actions:
                    if "--input" in action.option_strings:
                        with self.subTest(module=m, subcommand=name):
                            self.assertTrue(action.help and "JSON" in action.help and "{" in action.help, action.help)


class RuntimeNotice(unittest.TestCase):
    def test_long_runs_print_an_estimate_first_and_short_runs_do_not(self):
        t = [0.0]

        def clock():
            t[0] += 0.1  # every call advances the fake clock
            return t[0]
        buf = io.StringIO()
        self.assertEqual(list(_caps.timed_range(500, "toys", clock=clock, stream=buf)), list(range(500)))
        self.assertIn("estimated runtime", buf.getvalue())
        t[0], buf2 = 0.0, io.StringIO()
        list(_caps.timed_range(30, "toys", clock=clock, stream=buf2))
        self.assertEqual(buf2.getvalue(), "")


class PyhfAgreement(unittest.TestCase):
    """72 bins (beyond the multibin-limit cap of 50) with the override, against pyhf asymptotic CLs (qtilde)."""

    def setUp(self):
        try:
            import pyhf  # noqa: F401
        except ImportError:
            self.skipTest("pyhf is optional (pip install pyhf)")

    def test_72_bins_agree_with_pyhf_to_one_percent(self):
        import pyhf
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "b72.json", BINS72)
            code, out, err = run(LL, "multibin-limit", "--input", p, "--seed", "1", OPTION)
        self.assertEqual(code, 0, err)
        core = out["asymptotic_observed_cls_upper_limit"]
        spec = {"channels": [{"name": "c", "samples": [
            {"name": "sig", "data": [b["s"] for b in BINS72["bins"]],
             "modifiers": [{"name": "mu", "type": "normfactor", "data": None}]},
            {"name": "bkg", "data": [b["b"] for b in BINS72["bins"]], "modifiers": []}]}]}
        model = pyhf.Model(spec, poi_name="mu")
        data = [b["n"] for b in BINS72["bins"]]
        obs, _ = pyhf.infer.intervals.upper_limits.upper_limit(data, model, scan=None, level=0.05,
                                                               test_stat="qtilde", calctype="asymptotics")
        self.assertLess(abs(core / float(obs) - 1.0), 0.01, (core, float(obs)))

    def test_backend_comparison_converts_72_bins_on_the_asymptotic_path(self):
        shape = {"bins": BINS72["bins"], "cl": 0.95}
        with tempfile.TemporaryDirectory() as d:
            p = write(d, "s72.json", shape)
            code, out, err = run(PLUGIN / "adapters" / "pyhf-combine" / "assets" / "backend_comparison.py", "--model", p)
        self.assertEqual(code, 0, (out, err[-500:]))
        self.assertLess(abs(out["limits"]["relative_difference"]), 0.01)


if __name__ == "__main__":
    unittest.main()
