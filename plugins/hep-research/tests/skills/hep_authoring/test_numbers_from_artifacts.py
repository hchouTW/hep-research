"""Com7: numbers from artifacts. Oracles: the PDG rounding rule (Review of Particle Physics, Introduction 5.3):
0.827 +- 0.119 -> 0.83 +- 0.12; 0.827 +- 0.367 -> 0.8 +- 0.4; 1.2345 +- 0.0961 -> 1.23 +- 0.10; render_results.py
macros round-trip to the artifact (each annotated with its id and sha256); synthetic values sit in a watermark macro
that a final build refuses (compiled when LaTeX is installed); a one-bin dataset-record for HEPData validates and
exports; check_manuscript.py --numbers catches a planted 1.23 vs 1.24 mismatch between abstract and body;
audit_claims.py --compare catches "evidence for" changed to "observation of", a changed number and a dropped status
word between two versions (English and Chinese). All inputs are SYNTHETIC."""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SC = PLUGIN / "skills" / "hep-authoring" / "scripts"
RENDER, MANUSCRIPT, AUDIT = SC / "render_results.py", SC / "check_manuscript.py", SC / "audit_claims.py"
EXPORT = PLUGIN / "adapters" / "hepdata" / "assets" / "hepdata_export.py"
sys.path.insert(0, str(SC))
sys.path.insert(0, str(PLUGIN))
PDFLATEX = shutil.which("pdflatex")


def run(script, *args):
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True, timeout=600)
    return p.returncode, p.stdout, p.stderr


def stat_result(path, mu=1.2345, sigma=0.0961, label="synthetic"):
    from contracts import CONTRACTS_VERSION
    doc = {"contract_version": CONTRACTS_VERSION, "artifact_id": "synthetic-signal-strength", "artifact_type": "statistical-result",
           "objective": "SYNTHETIC signal strength", "bindings": {"experiments": [], "theory": []},
           "versions": {"plugin": "0.0.0", "contracts": CONTRACTS_VERSION, "profiles": {}},
           "provenance": {"producer_skill": "hep-statistics", "created": "2026-10-17", "evidence_ids": []},
           "inputs": [], "outputs": [], "status": [label], "unresolved_inputs": [],
           "required_capabilities": ["stats:result-semantics"],
           "extension": {"paradigm": "frequentist", "likelihood": {"form": "SYNTHETIC"}, "parameters_of_interest": ["mu"],
                         "nuisances": [], "test_statistic": "q_mu", "construction": "asymptotic",
                         "coverage": {"check": "not-checked", "method": "not studied"}, "fit_status": "converged",
                         "results": {"mu_hat": mu, "sigma_mu": sigma}}}
    Path(path).write_text(json.dumps(doc), encoding="utf-8")
    return doc


class PdgRounding(unittest.TestCase):
    def test_card_and_pdg_examples(self):
        from communication_lib.claims import pdg_round
        self.assertEqual(pdg_round("0.827", "0.119"), ("0.83", "0.12"))
        self.assertEqual(pdg_round("0.827", "0.367"), ("0.8", "0.4"))
        self.assertEqual(pdg_round("1.2345", "0.0961"), ("1.23", "0.10"))
        self.assertEqual(pdg_round("125.13", "0.11"), ("125.13", "0.11"))
        self.assertEqual(pdg_round("1776.93", "0.0849"), ("1776.93", "0.08"))
        self.assertEqual(pdg_round("80.3625", "0.0077"), ("80.363", "0.008"))  # 770: one significant digit

    def test_asymmetric_errors(self):
        from communication_lib.claims import pdg_round_asymmetric
        # differ by less than 10% of their average: the average sets the rounding
        self.assertEqual(pdg_round_asymmetric("1.0", "0.119", "0.121"), ("1.00", "0.12", "0.12"))
        # otherwise the narrower one sets the rounding of both
        self.assertEqual(pdg_round_asymmetric("1.0", "0.5", "0.119"), ("1.00", "0.50", "0.12"))

    def test_rule_name_is_accepted(self):
        from communication_lib.claims import _round, parse_rounding
        self.assertEqual(parse_rounding("pdg")[0], "pdg")
        self.assertEqual(_round("0.827", "pdg", uncertainty="0.367"), "0.8")
        self.assertIsNone(_round("0.827", "pdg"))  # the PDG rule needs the uncertainty


class Render(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.doc = stat_result(self.d / "result.json")

    def tearDown(self):
        self.tmp.cleanup()

    def render(self, *extra):
        return run(RENDER, "--quantity", f"Mu={self.d / 'result.json'}:mu_hat:sigma_mu", "--out", self.d / "numbers.tex",
                   "--manifest", self.d / "manifest.json", *extra)

    def test_macros_round_trip_and_are_annotated(self):
        code, out, err = self.render()
        self.assertEqual(code, 0, (out, err))
        tex = (self.d / "numbers.tex").read_text(encoding="utf-8")
        sha = hashlib.sha256((self.d / "result.json").read_bytes()).hexdigest()
        self.assertIn("synthetic-signal-strength", tex)
        self.assertIn(sha, tex)
        self.assertIn(r"\newcommand{\MuValue}{1.23}", tex)
        self.assertIn(r"\newcommand{\MuUnc}{0.10}", tex)
        self.assertIn(r"\hepSynthetic", tex)  # synthetic values are watermarked
        man = json.loads((self.d / "manifest.json").read_text())
        q = man["quantities"]["Mu"]
        self.assertEqual((q["source_value"], q["source_uncertainty"]), (1.2345, 0.0961))
        self.assertEqual((q["value"], q["uncertainty"], q["rounding"]), ("1.23", "0.10", "pdg"))
        self.assertEqual(q["artifact_sha256"], sha)

    def test_preliminary_and_observed_labels(self):
        stat_result(self.d / "result.json", label="observed")
        code, out, _ = self.render()
        self.assertEqual(code, 0, out)
        self.assertNotIn(r"\hepSynthetic{", (self.d / "numbers.tex").read_text().split("% ---")[-1])

    def test_one_bin_dataset_record_validates_and_exports(self):
        code, out, err = self.render("--hepdata-record", f"Mu={self.d / 'mu_record.json'}", "--record-quantity",
                                     "Mu=parameter", "--record-level", "detector", "--record-normalization",
                                     '{"kind": "integrated-luminosity", "value": 20.0, "unit": "pb^-1"}',
                                     "--record-process", "SYNTHETIC signal", "--record-uncertainty-kind", "statistical")
        self.assertEqual(code, 0, (out, err))
        from contracts.validate import validate_artifact
        rec = json.loads((self.d / "mu_record.json").read_text())
        self.assertTrue(validate_artifact(rec).ok, validate_artifact(rec).as_dict())
        self.assertEqual(rec["extension"]["data"]["values"], [1.2345])
        code, out, err = run(EXPORT, "--artifact", self.d / "mu_record.json", "--out", self.d / "hepdata")
        self.assertEqual(code, 0, (out, err))
        table = next((self.d / "hepdata").glob("*.yaml"))
        self.assertTrue(table.exists())

    @unittest.skipUnless(PDFLATEX, "no pdflatex: the watermark rule is checked at the macro level only")
    def test_draft_builds_and_final_build_fails_on_synthetic(self):
        code, out, err = self.render()
        self.assertEqual(code, 0, (out, err))
        body = r"\documentclass{article}\begin{document}%s\input{numbers.tex}$\mu = \Mu$\end{document}"
        (self.d / "draft.tex").write_text(body % "", encoding="utf-8")
        (self.d / "final.tex").write_text(body % r"\def\hepfinalbuild{}", encoding="utf-8")
        for name, ok in (("draft", True), ("final", False)):
            p = subprocess.run([PDFLATEX, "-interaction=nonstopmode", "-halt-on-error", f"{name}.tex"], cwd=self.d,
                               capture_output=True, text=True, timeout=600)
            self.assertEqual(p.returncode == 0, ok, (name, p.stdout[-800:]))


class ManuscriptNumbers(unittest.TestCase):
    TEX = r"""\documentclass{article}
\begin{document}
\begin{abstract}We measure $\mu = %s \pm 0.10$ (SYNTHETIC).\end{abstract}
\section{Results}
The fit gives $\mu = 1.23 \pm 0.10$.
\section{Conclusion}
The signal strength is $\mu = 1.23 \pm 0.10$.
\end{document}
"""

    def check(self, abstract_value):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "main.tex").write_text(self.TEX % abstract_value, encoding="utf-8")
            return run(MANUSCRIPT, d, "--numbers", "--format", "json")

    def test_consistent_numbers_pass(self):
        code, out, _ = self.check("1.23")
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["numbers"]["mismatches"], [])

    def test_planted_mismatch_is_caught(self):
        code, out, _ = self.check("1.24")
        self.assertEqual(code, 1)
        mm = json.loads(out)["numbers"]["mismatches"]
        self.assertEqual(mm[0]["quantity"], r"\mu")
        self.assertEqual(sorted({o["value"] for o in mm[0]["occurrences"]}), ["1.23", "1.24"])


class CompareVersions(unittest.TestCase):
    EN = "We report evidence for a SYNTHETIC excess with a local significance of 3.1 sigma; mu = 1.23 +- 0.10 (synthetic)."
    ZH = "我們報告一個合成(synthetic)超出的證據，局部顯著性 3.1 sigma；mu = 1.23 +- 0.10。"

    def compare(self, a, b):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.txt").write_text(a, encoding="utf-8")
            (Path(d) / "b.txt").write_text(b, encoding="utf-8")
            code, out, err = run(AUDIT, "--compare", Path(d) / "a.txt", Path(d) / "b.txt")
            return code, (json.loads(out) if out.strip().startswith("{") else out), err

    def test_faithful_translation_passes(self):
        code, out, err = self.compare(self.EN, self.ZH)
        self.assertEqual(code, 0, (out, err))

    def test_strength_change_is_caught(self):
        code, out, _ = self.compare(self.EN, self.EN.replace("evidence for", "observation of"))
        self.assertEqual(code, 1)
        self.assertIn("claim-strength", [d["check"] for d in out["differences"]])

    def test_number_and_status_changes_are_caught(self):
        code, out, _ = self.compare(self.EN, self.EN.replace("1.23", "1.24"))
        self.assertEqual(code, 1)
        self.assertIn("numbers", [d["check"] for d in out["differences"]])
        code, out, _ = self.compare(self.EN, self.EN.replace(" (synthetic)", "").replace("SYNTHETIC ", ""))
        self.assertEqual(code, 1)
        self.assertIn("status-words", [d["check"] for d in out["differences"]])


if __name__ == "__main__":
    unittest.main()
