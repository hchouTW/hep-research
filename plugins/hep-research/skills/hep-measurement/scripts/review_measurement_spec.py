#!/usr/bin/env python3
"""Draft a verdict-first review of a measurement-spec from the contract validator's findings.

Purpose: the first pass of the review procedure in <plugin root>/skills/hep-measurement/references/review-and-artifacts.md.
It runs contracts/validate.py's rules (strict: the measurement-spec rules of every contract version), ranks the
findings by their impact on the result, and drafts the verdict on the three-value scale: `blocked` (a defect that
changes the result beyond its uncertainty or breaks blinding), `needs-work` (other defects), or
`acceptable-with-open-inputs` (only unresolved inputs, or none). It is a draft: a passing validator checks consistency,
not physics, and a human review still writes the physics judgement and may raise the verdict.

Usage: python3 review_measurement_spec.py SPEC.json [--profiles-from hep-research.project.json] [--markdown]
       [--status S] [--check-bundle BUNDLE --check-root DIR]
Eras (M3): when the spec declares `eras` ([{id, start, end, kind, source, ...}]), four review rules run:
era.bin_straddles_boundary (error: a period or a time-variable bin crosses an era boundary), era.correction_missing
(warning: a correction neither determined for an era nor listed in its shared_corrections), era.correlation_undeclared
(warning: with two or more eras, a systematic without era_correlation) and era.version_mismatch (warning: eras with
different versions where the later era is not a declared software or calibration change). Times are numbers or ISO
dates; values that cannot be compared are not checked. Specs without eras are reviewed as before.
Coupled backgrounds (M4): when the spec declares `coupled_backgrounds` ([{background, species, treatment, source}]),
coupled.fixed_subtraction (warning) flags one subtracted as a fixed amount: the other species is measured at the same
time, so fit them jointly or iterate (references/backgrounds.md, "Coupled species").
--check-bundle (opt-in) adds "analysis_check": the bounded summary of contracts/analysis_check.py on a v2 analysis
bundle (violated and unverified obligations, missing bindings, next steps); it never changes the verdict or exit code.
Output: JSON {"status", "verdict", "reason", "defects": [...ranked...], "unresolved": [...], "warnings": [...],
"note"}; --markdown prints the review in the order of assets/measurement-review-template.md instead.
Exit codes: 0 verdict acceptable-with-open-inputs; 1 verdict blocked or needs-work (a finding); 2 unreadable or
invalid input (not JSON, not a measurement-spec, a malformed project config or one with errors, such as a
profile that did not load cleanly). Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # the plugin root, also under python3 -I
from contracts.validate import validate_artifact  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402

STATUSES = ('failed', 'unvalidated', 'preliminary', 'synthetic', 'asimov', 'observed', 'user-supplied',
            'validated-in-scope', 'projection', 'outside-validated-range')  # contracts/vocab/core.json artifact_statuses
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


def _time(value):
    """A comparable time: a number, or an ISO date or date-time string; None otherwise."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return ('n', float(value))
    if isinstance(value, str):
        try:
            return ('d', datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None))
        except ValueError:
            return None
    return None


def _inside(lo, b, hi) -> bool:
    return lo is not None and hi is not None and b is not None and lo[0] == b[0] == hi[0] and lo[1] < b[1] < hi[1]


def era_findings(ext: dict) -> list[tuple[str, str, str, str]]:
    """(severity, code, field, message) of the M3 era rules; empty when the spec declares no eras."""
    eras = ext.get('eras')
    if not isinstance(eras, list) or not eras:
        return []
    eras = [e for e in eras if isinstance(e, dict)]
    out = []
    bounds = sorted({(e.get('start'), e.get('id')) for e in eras[1:]} | {(e.get('end'), e.get('id')) for e in eras[:-1]},
                    key=str)
    intervals = []
    periods = ext.get('period')
    for i, per in enumerate(periods if isinstance(periods, list) else [periods]):
        if isinstance(per, dict):
            intervals.append((f'$.extension.period[{i}]', per.get('start'), per.get('end')))
    obs = ext.get('observable') if isinstance(ext.get('observable'), dict) else {}
    for j, var in enumerate(obs.get('variables') or []):
        if isinstance(var, dict) and 'time' in str(var.get('name', '')).lower() and isinstance(var.get('edges'), list):
            edges = var['edges']
            for k, (a, b) in enumerate(zip(edges, edges[1:])):
                intervals.append((f'$.extension.observable.variables[{j}].edges[{k}]', a, b))
    for field, a, b in intervals:
        for bound, era_id in bounds:
            if _inside(_time(a), _time(bound), _time(b)):
                out.append(('error', 'era.bin_straddles_boundary', field,
                            f'[{a}, {b}] crosses the boundary {bound} of era {era_id}: split it at the boundary so '
                            'that each bin belongs to one era'))
    effects = [c.get('effect_id') for c in ext.get('corrections') or [] if isinstance(c, dict) and c.get('effect_id')]
    if len(eras) > 1:
        for i, e in enumerate(eras):
            covered = set(e.get('corrections') or []) | set(e.get('shared_corrections') or [])
            for eff in effects:
                if eff not in covered:
                    out.append(('warning', 'era.correction_missing', f'$.extension.eras[{i}]',
                                f"correction '{eff}' is neither determined for era {e.get('id')} (corrections) nor "
                                'declared valid across eras (shared_corrections)'))
        for i, syst in enumerate(ext.get('systematics') or []):
            if isinstance(syst, dict) and not syst.get('era_correlation'):
                out.append(('warning', 'era.correlation_undeclared', f'$.extension.systematics[{i}]',
                            f"systematic '{syst.get('name')}' does not say how it is correlated across the "
                            f'{len(eras)} eras (era_correlation: correlated, uncorrelated or partial)'))
        for i, (prev, cur) in enumerate(zip(eras, eras[1:]), start=1):
            pv, cv = prev.get('versions') or {}, cur.get('versions') or {}
            changed = sorted(k for k in set(pv) & set(cv) if pv[k] != cv[k])
            if changed and cur.get('kind') not in ('software', 'calibration'):
                out.append(('warning', 'era.version_mismatch', f'$.extension.eras[{i}].versions',
                            f"era {cur.get('id')} uses other {', '.join(changed)} versions than era {prev.get('id')} "
                            f"but is a '{cur.get('kind')}' era: reprocess, or declare the software or calibration change"))
    return out


def coupled_findings(ext: dict) -> list[tuple[str, str, str, str]]:
    """(severity, code, field, message) of the M4 rule; empty when the spec declares no coupled backgrounds."""
    out = []
    for i, cb in enumerate(ext.get('coupled_backgrounds') or []):
        if isinstance(cb, dict) and cb.get('treatment') == 'fixed-subtraction':
            out.append(('warning', 'coupled.fixed_subtraction', f'$.extension.coupled_backgrounds[{i}]',
                        f"background '{cb.get('background')}' comes from {cb.get('species')}, which is measured at the "
                        'same time, but is subtracted as a fixed amount: its uncertainty and its dependence on the '
                        'result are lost; fit the species jointly or iterate'))
    return out


def draft(doc: dict, vocab: Vocabulary | None = None, era_checks: bool = True, coupled_checks: bool = True) -> dict:
    if not isinstance(doc, dict) or doc.get('artifact_type') != 'measurement-spec':
        raise ValueError('input is not a measurement-spec artifact')
    rep = validate_artifact(doc, vocab, strict=True)
    found = [(f.severity, f.code, f.path, f.message) for f in rep.findings]
    if era_checks and isinstance(doc.get('extension'), dict):
        found += era_findings(doc['extension'])
    if coupled_checks and isinstance(doc.get('extension'), dict):
        found += coupled_findings(doc['extension'])
    rank = {c: i for i, c in enumerate(BLOCKING)}
    errors = sorted((f for f in found if f[0] == 'error'), key=lambda f: (rank.get(f[1], len(BLOCKING)), f[2]))
    defects = [{'rank': i + 1, 'code': c, 'evidence': p, 'why': m,
                'blocking': c in rank, 'owner': OWNER.get(c, 'hep-measurement')} for i, (_, c, p, m) in enumerate(errors)]
    unresolved = [{'code': c, 'field': p, 'message': m} for sev, c, p, m in found if sev == 'unresolved']
    warnings = [{'code': c, 'field': p, 'message': m} for sev, c, p, m in found if sev == 'warning']
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


def check_summary(bundle: Path, root: Path) -> dict:
    """The bounded summary of the cross-artifact check on a v2 bundle (a diagnostic: it never changes the review's
    verdict or exit code); a failure of the check is reported in the summary, not hidden."""
    from contracts import analysis_check as ac
    try:
        view, diags = ac.load_subject(bundle, root)
    except (OSError, ValueError) as exc:
        return {'status': 'usage', 'error': str(exc)}
    return ac.summary_page(ac.evaluate(view, diags))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec', type=Path, help='measurement-spec JSON artifact')
    ap.add_argument('--profiles-from', type=Path, dest='profiles_from', help='project config whose profiles extend the vocabulary')
    ap.add_argument('--markdown', action='store_true', help='print the review as Markdown')
    ap.add_argument('--status', choices=STATUSES, default='unvalidated', help='status label, echoed as status')
    ap.add_argument('--check-bundle', type=Path, dest='check_bundle',
                    help='opt-in: a v2 analysis bundle; adds the cross-artifact check summary (contracts/analysis_check.py)')
    ap.add_argument('--check-root', type=Path, dest='check_root', help='project root of --check-bundle')
    args = ap.parse_args(argv)
    if (args.check_bundle is None) != (args.check_root is None):
        ap.error('--check-bundle and --check-root go together')
    try:
        doc = json.loads(args.spec.read_text(encoding='utf-8'), parse_constant=_reject_constant)
        vocab = None
        if args.profiles_from:
            from contracts.project import load_project
            proj = load_project(args.profiles_from)
            if not proj.report.ok:  # a profile that did not load cleanly must not shape the review
                raise ValueError('invalid project config: ' + '; '.join(f'{f.code}: {f.message}' for f in proj.report.errors))
            vocab = Vocabulary.with_profiles(proj.profiles)
        review = draft(doc, vocab)
    except (OSError, ValueError) as exc:
        print(f'review_measurement_spec.py: error: {exc}', file=sys.stderr)
        return 2
    extra = {} if args.check_bundle is None else {'analysis_check': check_summary(args.check_bundle, args.check_root)}
    if args.markdown:
        print(markdown(review, doc.get('artifact_id', args.spec.name), args.status))
        if extra:
            print('\n## Cross-artifact check (diagnostic)\n\n```json\n' + json.dumps(extra['analysis_check'], indent=1) + '\n```')
    else:
        print(json.dumps({'status': args.status, **review, **extra}, indent=1))
    return 0 if review['verdict'] == 'acceptable-with-open-inputs' else 1


if __name__ == '__main__':
    sys.exit(main())
