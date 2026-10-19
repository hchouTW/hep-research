"""Com6: paper blueprints (assets/paper-blueprints.json) and check_manuscript.py --blueprint TYPE. Oracles: a search
draft without a systematics table is listed as missing it; a complete draft lists nothing; the blueprint never changes
the exit code (advisory); every entry names a public author guideline it was read from, or says to-verify; length
limits are not restated (they live in latex-venue-setup.md). All drafts are SYNTHETIC."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-authoring" / "scripts" / "check_manuscript.py"
BLUEPRINTS = PLUGIN / "skills" / "hep-authoring" / "assets" / "paper-blueprints.json"
GENRES = PLUGIN / "skills" / "hep-authoring" / "references" / "paper-genre-variants.md"

SYST_TABLE = r"""
\begin{table}
\caption{Systematic uncertainties on the expected background yield (SYNTHETIC).}
\begin{tabular}{lc} Source & Uncertainty \\ Jet energy scale & 3\% \\ \end{tabular}
\end{table}
"""
SEARCH = r"""\documentclass{article}
\begin{document}
\begin{abstract}A SYNTHETIC search for a new resonance.\end{abstract}
\section{Introduction}
This work extends previously published searches.
\section{Signal model}
The benchmark model predicts a narrow resonance.
\section{Event selection}
The selection requires two jets.
\section{Background estimation}
The background is estimated in a control region.
\section{Systematic uncertainties}
%SYST%
\section{Results}
The observed yield agrees with the expected background. Upper limits are set at 95\% confidence level with the CLs method.
Data availability: the results are provided in HEPData.
\section{Conclusion}
No excess is found.
\end{document}
"""


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=600)
    return p.returncode, p.stdout, p.stderr


class Blueprints(unittest.TestCase):
    def draft(self, d, with_table=True):
        (Path(d) / "main.tex").write_text(SEARCH.replace("%SYST%", SYST_TABLE if with_table else ""), encoding="utf-8")
        return Path(d)

    def test_search_without_a_systematics_table_is_listed(self):
        with tempfile.TemporaryDirectory() as d:
            self.draft(d, with_table=False)
            code0, _, _ = run(d)
            code, out, _ = run(d, "--blueprint", "search", "--format", "json")
            self.assertEqual(code, code0)  # advisory: the exit code does not change
            rep = json.loads(out)
            bp = rep["blueprint"]
            self.assertEqual(bp["type"], "search")
            self.assertIn("systematics-table", bp["missing"])
            self.assertTrue(any(f["code"] == "manuscript.blueprint_missing" and f["severity"] == "advisory"
                                for f in rep["findings"]))

    def test_complete_search_draft_lists_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            self.draft(d)
            code0, _, _ = run(d)
            code, out, _ = run(d, "--blueprint", "search", "--format", "json")
            self.assertEqual(code, code0)
            self.assertEqual(json.loads(out)["blueprint"]["missing"], [])
            code, text, _ = run(d, "--blueprint", "search")
            self.assertEqual(code, code0)
            self.assertIn("advisory", text)

    def test_every_entry_is_sourced_or_to_verify_and_types_are_documented(self):
        doc = json.loads(BLUEPRINTS.read_text(encoding="utf-8"))
        self.assertEqual(set(doc["types"]), {"search", "precision-measurement", "instrumentation", "letter"})
        text = GENRES.read_text(encoding="utf-8")
        for name, bp in doc["types"].items():
            self.assertIn(bp["genre_section"], text, name)
            for item in bp["items"]:
                with self.subTest(type=name, item=item["id"]):
                    src = item["source"]
                    self.assertTrue(src == "to-verify" or src in doc["sources"], src)
                    self.assertTrue(item["detect"])
        for sid, s in doc["sources"].items():
            self.assertTrue(s["url"].startswith("https://") and s["read"], sid)
        self.assertNotIn("3,750", json.dumps(doc))  # limits stay in latex-venue-setup.md

    def test_unknown_type_is_bad_usage(self):
        with tempfile.TemporaryDirectory() as d:
            self.draft(d)
            code, _, _ = run(d, "--blueprint", "novel")
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
