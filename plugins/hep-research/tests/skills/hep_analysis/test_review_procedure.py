"""ANA-P0-3: the generic measurement-review procedure. The template carries the three verdict values; the synthetic
defective spec fails the validator with exactly the defects the worked review ranks. Synthetic values only."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / 'skills' / 'hep-analysis'
sys.path.insert(0, str(ROOT))
from contracts.validate import validate_artifact  # noqa: E402

VERDICTS = ('blocked', 'needs-work', 'acceptable-with-open-inputs')


class ReviewProcedureTests(unittest.TestCase):
    def test_template_has_the_three_verdicts(self):
        text = (SKILL / 'assets' / 'measurement-review-template.md').read_text(encoding='utf-8')
        for v in VERDICTS:
            self.assertIn(f'`{v}`', text)

    def test_reference_defines_the_scale_once(self):
        text = (SKILL / 'references' / 'review-and-artifacts.md').read_text(encoding='utf-8')
        for v in VERDICTS:
            self.assertIn(f'- `{v}`:', text)

    def test_worked_review_lists_exactly_the_validator_findings(self):
        text = (SKILL / 'references' / 'review-and-artifacts.md').read_text(encoding='utf-8')
        listed = set(re.search(r'<!-- worked-review-codes: (.*?) -->', text).group(1).split())
        doc = json.loads((SKILL / 'assets' / 'review-example.synthetic.json').read_text(encoding='utf-8'))
        rep = validate_artifact(doc)
        self.assertFalse(rep.ok)
        found = {f.code for f in rep.findings if f.severity in ('error', 'unresolved')}
        self.assertEqual(found, listed)
        self.assertIn('Verdict: `blocked`', text)

    def test_skill_links_the_procedure(self):
        text = (SKILL / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('references/review-and-artifacts.md', text)

    def test_profile_module_links_the_generic_procedure(self):
        text = (ROOT / 'profiles' / 'experiments' / 'ams-02' / 'modules' / 'methods' / 'analysis-artifacts.md').read_text(
            encoding='utf-8')
        self.assertIn('skills/hep-analysis/references/review-and-artifacts.md', text)


if __name__ == '__main__':
    unittest.main()
