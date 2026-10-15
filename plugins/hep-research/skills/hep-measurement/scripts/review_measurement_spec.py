#!/usr/bin/env python3
"""Draft a verdict-first review of a measurement-spec from the contract validator's findings.

Purpose: the first pass of the review procedure in <plugin root>/skills/hep-measurement/references/review-and-artifacts.md.
It runs contracts/validate.py's rules (strict: the measurement-spec rules of every contract version), ranks the
findings by their impact on the result, and drafts the verdict on the three-value scale: `blocked` (a defect that
changes the result beyond its uncertainty or breaks blinding), `needs-work` (other defects), or
`acceptable-with-open-inputs` (only unresolved inputs, or none). It is a draft: a passing validator checks consistency,
not physics, and a human review still writes the physics judgement and may raise the verdict.

Usage: python3 review_measurement_spec.py SPEC.json [--profiles-from hep-research.project.json] [--markdown]
       [--status S]
Output: JSON {"status", "verdict", "reason", "defects": [...ranked...], "unresolved": [...], "warnings": [...],
"note"}; --markdown prints the review in the order of assets/measurement-review-template.md instead.
Exit codes: 0 verdict acceptable-with-open-inputs; 1 verdict blocked or needs-work (a finding); 2 unreadable or
invalid input (not JSON, not a measurement-spec, malformed project config). Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root, also under python3 -I
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope')  # contracts/vocab/core.json artifact_statuses
# Defects that move the central value beyond its quoted uncertainty or break blinding, in impact order.
BLOCKING = ('measurement.normalization_double_counted', 'measurement.duplicate_correction',
            'measurement.correction_category_repeated', 'measurement.correction_in_observable_and_chain',
            'measurement.blinding_mask_missing', 'measurement.blinded_observed', 'measurement.zero_value',
            'measurement.shape_only_value', 'measurement.ratio_self', 'measurement.ratio_block_missing',
            'measurement.background_constraint_missing', 'measurement.background_estimator_missing',
            'measurement.backgrounds_empty', 'status.conflict', 'status.not_propagated')
OWNER = {'measurement.blinding_mask_missing': 'hep-measurement (mask from the collaboration policy)',
         'status.conflict': 'hep-measurement', 'measurement.normalization_double_counted': 'hep-measurement'}
NOTE = ('draft from the contract validator: it checks consistency, not physical validity; a human review writes the '
        'physics judgement and may raise the verdict')


def _reject_constant(token):
    raise ValueError(f'non-finite number {token} in the input')


def draft(doc: dict, vocab: Vocabulary | None = None) -> dict:
    if not isinstance(doc, dict) or doc.get('artifact_type') != 'measurement-spec':
        raise ValueError('input is not a measurement-spec artifact')
    rep = validate_artifact(doc, vocab, strict=True)
    errors = [f for f in rep.findings if f.severity == 'error']
    rank = {c: i for i, c in enumerate(BLOCKING)}
    errors.sort(key=lambda f: (rank.get(f.code, len(BLOCKING)), f.path))
    defects = [{'rank': i + 1, 'code': f.code, 'evidence': f.path, 'why': f.message,
                'blocking': f.code in rank, 'owner': OWNER.get(f.code, 'hep-measurement')} for i, f in enumerate(errors)]
    unresolved = [{'code': f.code, 'field': f.path, 'message': f.message} for f in rep.findings if f.severity == 'unresolved']
    warnings = [{'code': f.code, 'field': f.path, 'message': f.message} for f in rep.findings if f.severity == 'warning']
    if any(d['blocking'] for d in defects):
        verdict = 'blocked'
        reason = f"{defects[0]['code']} at {defects[0]['evidence']}: {defects[0]['why']}"
    elif defects:
        verdict = 'needs-work'
        reason = f"{len(defects)} defect(s), none moving the central value beyond its uncertainty by itself"
    else:
        verdict = 'acceptable-with-open-inputs'
        reason = (f"no defect; {len(unresolved)} unresolved input(s) remain" if unresolved
                  else 'no defect and no unresolved input found by the validator')
    return {'verdict': verdict, 'reason': reason, 'defects': defects, 'unresolved': unresolved,
            'warnings': warnings, 'note': NOTE}


def markdown(review: dict, name: str, status: str) -> str:
    lines = [f'# Measurement review: {name}', '', f'Status of the reviewed material: {status}.', '', '## Verdict', '',
             f"`{review['verdict']}` - {review['reason']}.", '', '## Defects, largest impact first', '',
             '| # | Evidence | Why it moves the result | Owner |', '|---|---|---|---|']
    lines += [f"| {d['rank']} | `{d['evidence']}` ({d['code']}) | {d['why']} | {d['owner']} |" for d in review['defects']]
    lines += ['', '## Unresolved inputs', '']
    lines += [f"- `{u['field']}`: {u['message']}" for u in review['unresolved']] or ['- none']
    lines += ['', '## Not reviewed', '', f"- {review['note']}", '']
    return '\n'.join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec', type=Path, help='measurement-spec JSON artifact')
    ap.add_argument('--profiles-from', type=Path, dest='profiles_from', help='project config whose profiles extend the vocabulary')
    ap.add_argument('--markdown', action='store_true', help='print the review as Markdown')
    ap.add_argument('--status', choices=STATUSES, default='unvalidated', help='status label, echoed as status')
    args = ap.parse_args(argv)
    try:
        doc = json.loads(args.spec.read_text(encoding='utf-8'), parse_constant=_reject_constant)
        vocab = None
        if args.profiles_from:
            from contracts.project import load_project
            vocab = Vocabulary.with_profiles(load_project(args.profiles_from).profiles)
        review = draft(doc, vocab)
    except (OSError, ValueError) as exc:
        print(f'review_measurement_spec.py: error: {exc}', file=sys.stderr)
        return 2
    if args.markdown:
        print(markdown(review, doc.get('artifact_id', args.spec.name), args.status))
    else:
        print(json.dumps({'status': args.status, **review}, indent=1))
    return 0 if review['verdict'] == 'acceptable-with-open-inputs' else 1


if __name__ == '__main__':
    sys.exit(main())
