"""RC-D7: every relative link and anchor in skills/research-communication/**/*.md resolves, and every reference file
named in backticks (`name.md`) exists, so moves of rules between references cannot leave dangling pointers."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / 'skills' / 'research-communication'
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)\)')
FENCE = re.compile(r'^```.*?^```', re.S | re.M)
NAMED = re.compile(r'`([a-z0-9][a-z0-9\-]*\.md)`')


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

    def test_every_reference_named_in_backticks_exists(self):
        known = {p.name for p in SKILL.rglob('*.md')}
        missing = []
        for path in sorted((SKILL / 'references').glob('*.md')) + [SKILL / 'SKILL.md', SKILL / 'README.md']:
            for name in NAMED.findall(path.read_text(encoding='utf-8')):
                if name not in known and name not in ('README.md', 'SKILL.md', 'CHANGELOG.md', 'VALIDATION.md', 'index.md'):
                    missing.append(f'{path.relative_to(ROOT)} -> {name}')
        self.assertEqual(missing, [])

    def test_slug_matches_github(self):
        self.assertEqual(slug("Checking a collaboration's publication pattern"), 'checking-a-collaborations-publication-pattern')


if __name__ == '__main__':
    unittest.main()
