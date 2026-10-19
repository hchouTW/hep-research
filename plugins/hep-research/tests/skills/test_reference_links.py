"""RC-D7, extended for the communication split (plan G7, G15): in hep-citations and hep-authoring every relative
link and anchor resolves, including links into another skill or a profile; every reference named in backticks
(`name.md` in the skill, or a relative path such as `../../hep-citations/references/name.md`) exists; every
reference ends its task with a 'Done when' line. That no maintained file names a retired skill (or its folder) is
tools/check_retired_names.py's check (tests/tools/test_check_retired_names.py)."""
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS = [ROOT / 'skills' / 'hep-citations', ROOT / 'skills' / 'hep-authoring']
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)\)')
FENCE = re.compile(r'^```.*?^```', re.S | re.M)
NAMED = re.compile(r'`([a-z0-9][a-z0-9\-]*\.md)`')
NAMED_PATH = re.compile(r'`((?:\.\./)+[\w./-]+\.md)`')
ALWAYS_KNOWN = ('README.md', 'SKILL.md', 'CHANGELOG.md', 'VALIDATION.md', 'index.md')


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


def broken_links(skills, root):
    """'<file> -> <target> (why)' for every relative link or anchor in the skills' Markdown that does not resolve."""
    broken = []
    for skill in skills:
        for path in sorted(skill.rglob('*.md')):
            for target in links(path):
                file_part, _, anchor = target.partition('#')
                dest = (path.parent / file_part).resolve() if file_part else path
                if not dest.exists():
                    broken.append(f'{path.relative_to(root)} -> {target} (no file)')
                elif anchor and dest.suffix == '.md' and anchor not in anchors(dest):
                    broken.append(f'{path.relative_to(root)} -> {target} (no anchor)')
    return broken


def missing_named(skills, root):
    """'<file> -> <name>' for every reference named in backticks that exists neither in the skill nor at its path."""
    missing = []
    for skill in skills:
        known = {p.name for p in skill.rglob('*.md')}
        for path in sorted((skill / 'references').glob('*.md')) + [skill / 'SKILL.md', skill / 'README.md']:
            text = path.read_text(encoding='utf-8')
            for name in NAMED.findall(text):
                if name not in known and name not in ALWAYS_KNOWN:
                    missing.append(f'{path.relative_to(root)} -> {name}')
            for rel in NAMED_PATH.findall(text):
                if not (path.parent / rel).resolve().exists():
                    missing.append(f'{path.relative_to(root)} -> {rel}')
    return missing


class ReferenceLinkTests(unittest.TestCase):
    def test_every_relative_link_and_anchor_resolves(self):
        self.assertTrue(all((s / 'SKILL.md').is_file() for s in SKILLS))
        self.assertEqual(broken_links(SKILLS, ROOT), [])

    def test_every_reference_named_in_backticks_exists(self):
        self.assertEqual(missing_named(SKILLS, ROOT), [])

    def test_every_reference_has_a_completion_condition(self):
        """RC-D2: each reference ends its task with a checkable 'Done when' line."""
        missing = [str(p.relative_to(ROOT)) for s in SKILLS for p in sorted((s / 'references').glob('*.md'))
                   if 'Done when' not in p.read_text(encoding='utf-8')]
        self.assertEqual(missing, [])

    def test_slug_matches_github(self):
        self.assertEqual(slug("Checking a collaboration's publication pattern"), 'checking-a-collaborations-publication-pattern')

    def test_planted_broken_cross_skill_link_is_found(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            a, b = root / 'skills' / 'a', root / 'skills' / 'b'
            for s in (a, b):
                (s / 'references').mkdir(parents=True)
                (s / 'SKILL.md').write_text('# s\n', encoding='utf-8')
                (s / 'README.md').write_text('# r\n', encoding='utf-8')
            (b / 'references' / 'there.md').write_text('# There\n\n## Part one\n', encoding='utf-8')
            good = '[ok](../../b/references/there.md#part-one) and `../../b/references/there.md`\n'
            (a / 'references' / 'here.md').write_text(good, encoding='utf-8')
            self.assertEqual((broken_links([a, b], root), missing_named([a, b], root)), ([], []))
            bad = ('[gone](../../b/references/moved.md), [anchor](../../b/references/there.md#part-two), '
                   '`../../b/references/moved.md`\n')
            (a / 'references' / 'here.md').write_text(bad, encoding='utf-8')
            self.assertEqual(broken_links([a, b], root),
                             ['skills/a/references/here.md -> ../../b/references/moved.md (no file)',
                              'skills/a/references/here.md -> ../../b/references/there.md#part-two (no anchor)'])
            self.assertEqual(missing_named([a, b], root), ['skills/a/references/here.md -> ../../b/references/moved.md'])


if __name__ == '__main__':
    unittest.main()
