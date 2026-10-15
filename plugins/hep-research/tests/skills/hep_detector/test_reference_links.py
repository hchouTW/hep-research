"""DR-WP3 step 1: every relative link and anchor in skills/hep-detector/**/*.md resolves, so moving a duplicated
section to its single home cannot leave a dangling pointer (pattern of tests/skills/hep_measurement/test_reference_links.py)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / 'skills' / 'hep-detector'
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)\)')
FENCE = re.compile(r'^```.*?^```', re.S | re.M)


def slug(heading: str) -> str:
    """GitHub-style anchor: lower case, punctuation dropped (hyphens and underscores kept), spaces to hyphens."""
    text = re.sub(r'[`*]', '', heading.strip().lower())
    text = re.sub(r'[^\w\- ]', '', text)
    return text.replace(' ', '-')


def anchors(path: Path) -> set:
    text = FENCE.sub('', path.read_text(encoding='utf-8'))
    return {slug(m.group(1)) for m in re.finditer(r'^#{1,6}\s+(.*)$', text, re.M)}


def links(path: Path):
    text = FENCE.sub('', path.read_text(encoding='utf-8'))
    text = re.sub(r'`[^`\n]*`', '', text)
    for m in LINK.finditer(text):
        target = m.group(1)
        if re.match(r'^[a-z]+:', target):  # http:, https:, mailto:
            continue
        yield target


class ReferenceLinkTests(unittest.TestCase):
    def test_every_relative_link_and_anchor_resolves(self):
        files = sorted(SKILL.rglob('*.md'))
        self.assertTrue(files)
        broken = []
        for path in files:
            for target in links(path):
                file_part, _, anchor = target.partition('#')
                dest = (path.parent / file_part).resolve() if file_part else path
                if not dest.exists():
                    broken.append(f'{path.relative_to(ROOT)} -> {target} (no file)')
                elif anchor and dest.suffix == '.md' and anchor not in anchors(dest):
                    broken.append(f'{path.relative_to(ROOT)} -> {target} (no anchor)')
        self.assertEqual(broken, [])

    def test_summary_points_to_the_single_homes(self):
        text = (SKILL / 'references' / 'detector-principles-summary.md').read_text(encoding='utf-8')
        self.assertNotIn('| # | Relation |', text)  # the equation table lives in core-detector-equations.md
        self.assertNotIn('particle & interaction -> detector response', text)  # the chain lives in the framework
        self.assertIn('core-detector-equations.md', text)
        self.assertIn('detector-measurement-framework.md#the-chain', text)

if __name__ == '__main__':
    unittest.main()
