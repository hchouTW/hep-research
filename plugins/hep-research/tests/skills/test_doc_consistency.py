"""F-11: documentation that repeats a list or a fact agrees with its source.

1. The nine derivation statuses: hep-theory SKILL.md, its README and the proof-status ladder of
   references/mathematical-reasoning-and-proof.md list the same statuses as contracts/vocab/core.json.
2. The hep-computing README says uproot only of the ROOT inspection tool that has an uproot backend.
3. The capability-matrix row of the communication evaluation names the latest live run recorded in VALIDATION.md.
4. The SKILL.md size record in docs/maintenance.md names every skill, within the budget.
5. The hep-measurement cosmic-ray invariants state a rule to look the solar cycle up in SILSO, not a remembered chronology.
6. train_classifier.py reports no accuracy (its reference advises the analysis metric instead).
7. Every mention of RooFit's AsymptoticError in likelihood-fitting.md and sweighted_fit.py says it treats the weights
   as known constants, not that it is the asymptotically correct covariance for sWeights.
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def text(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(s):
    return " ".join(s.split())


VOCAB = list(json.loads(text("contracts/vocab/core.json"))["vocabularies"]["derivation_statuses"])
WORDS = {"formal-proof": "formal", "analytic-derivation": "analytic", "perturbative-argument": "perturbative",
         "asymptotic-argument": "asymptotic", "heuristic-argument": "heuristic", "numerical-evidence": "numerical",
         "empirical-observation": "empirical", "conjecture": "conjecture", "not-derived": "not derived"}


class DerivationStatuses(unittest.TestCase):
    def test_vocabulary_has_nine(self):
        self.assertEqual(len(VOCAB), 9)
        self.assertEqual(set(WORDS), set(VOCAB))

    def test_skill_md(self):
        line = re.search(r"derivation status from the core vocabulary: ([^.]*)\.", text("skills/hep-theory/SKILL.md"))
        names = [re.sub(r"\s*\(.*\)", "", x).strip() for x in line.group(1).split(",")]
        self.assertEqual(names, [v.replace("-", " ") for v in VOCAB])

    def test_readme_ladder(self):
        ladder = re.search(r"proof-status ladder \(([^)]*)\)", text("skills/hep-theory/README.md")).group(1)
        self.assertEqual([x.strip() for x in ladder.split(",")], [WORDS[v] for v in VOCAB])

    def test_reference_ladder(self):
        ref = text("skills/hep-theory/references/mathematical-reasoning-and-proof.md")
        section = ref[ref.index("Require every mathematical result to carry an explicit status"):ref.index("**Never silently")]
        bold = re.findall(r"^- \*\*([A-Z][a-z]+(?: [a-z]+)?)\*\* —", section, re.M)
        self.assertEqual([b.lower() for b in bold], [v.replace("-", " ") for v in VOCAB])
        ladder = re.search(r"proof-status categories above \(([^)]*)\)", flat(ref)).group(1)
        self.assertEqual([x.strip() for x in ladder.split(",")], [v.replace("-", " ") for v in VOCAB])


class ComputingReadmeUproot(unittest.TestCase):
    TOOLS = ("inspect_root_file.py", "compare_root_histograms.py", "summarize_histogram_statistics.py",
             "roofit_workspace_summary.py", "audit_histograms.py")

    def test_only_the_uproot_backend_is_described_with_uproot(self):
        with_backend = [t for t in self.TOOLS
                        if re.search(r"^\s*import uproot", text(f"skills/hep-computing/scripts/{t}"), re.M)]
        self.assertEqual(with_backend, ["compare_root_histograms.py"])
        readme = flat(text("skills/hep-computing/README.md"))
        self.assertNotIn("(PyROOT or uproot when installed", readme)
        line = next(x for x in text("skills/hep-computing/README.md").splitlines() if "inspect ROOT files" in x)
        for clause in re.split(r";", line):
            if "uproot" in clause:
                named = [t for t in self.TOOLS if f"`{t}`" in clause]
                self.assertTrue(set(named) <= set(with_backend), clause)


class CommunicationEvalRow(unittest.TestCase):
    def test_row_names_the_latest_recorded_run(self):
        runs = sorted(set(re.findall(r"`(live-\d{8}(?:-\d{4})?-[a-z0-9]+)`", text("VALIDATION.md"))))
        self.assertTrue(runs)
        row = next(r for r in text("docs/capability-matrix.md").splitlines() if r.startswith("| Behavioral evaluation"))
        status = row.split("|")[3]
        self.assertIn(runs[-1], status)


class SizeRecord(unittest.TestCase):
    def test_record_names_every_skill_within_budget(self):
        from tools.measure_entrypoints import BUDGET
        cap = BUDGET.get("skill_bytes_max", BUDGET.get("skill_bytes"))
        record = flat(text("docs/maintenance.md"))
        m = re.search(r"Measured on (\d{4}-\d{2}-\d{2})[^:]*: (.*?) bytes\.", record)
        self.assertIsNotNone(m)
        sizes = dict(re.findall(r"(hep-[a-z]+) ([\d,]+)", m.group(2)))
        skills = sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file())
        self.assertEqual(sorted(sizes), skills)
        for skill, size in sizes.items():
            self.assertLessEqual(int(size.replace(",", "")), cap, skill)


class SolarCycleRule(unittest.TestCase):
    def test_guide_states_a_lookup_rule(self):
        # the cosmic-ray invariants moved from the analysis guide to cosmic-ray-measurements.md (B-03)
        rule = flat(text("skills/hep-measurement/references/cosmic-ray-measurements.md"))
        self.assertIn("SILSO", rule)
        self.assertIn("never from memory", rule)
        for rel in ("skills/hep-measurement/references/cosmic-ray-measurements.md",
                    "skills/hep-measurement/references/hep-measurement-guide.md"):
            for remembered in ("Dec 2008", "Apr 2014", "Nov 2011"):
                self.assertNotIn(remembered, flat(text(rel)), rel)


class NoAccuracyMetric(unittest.TestCase):
    def test_train_classifier_reports_no_accuracy(self):
        self.assertNotIn("accuracy_weighted", text("skills/hep-ml/assets/train_classifier.py"))


class AsymptoticErrorWording(unittest.TestCase):
    def test_every_mention_says_known_weights(self):
        for rel in ("skills/hep-statistics/references/likelihood-fitting.md", "skills/hep-statistics/scripts/sweighted_fit.py",
                    "skills/hep-statistics/references/roofit-and-roostats-methods.md"):
            body = flat(text(rel))
            sentences = re.split(r"(?<=\.)\s", body)
            hits = [s for s in sentences if "AsymptoticError" in s]
            self.assertTrue(hits, rel)
            for s in hits:
                with self.subTest(file=rel, sentence=s[:120]):
                    self.assertRegex(s, r"known|weights treated as")
                    self.assertNotRegex(s, r"asymptotically correct covariance[^.]*\(([^)]*;)?\s*RooFit `?AsymptoticError")


if __name__ == "__main__":
    unittest.main()
