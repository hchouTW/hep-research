---
role: Theorist turning a review section into a conference talk
skill: hep-authoring
archetype: contrast
use_case: a 20-minute review talk built from the three synthetic EFT fits of example 02, checked against its record
---

Illustrative example: the fits and numbers are the invented ones of
[02-contrast-review-synthesis.md](02-contrast-review-synthesis.md). The talk follows the review-talk outline of
[the adaptation templates](../../assets/paper/audience-adaptation-templates.md) and is checked with
`check_adaptation.py`; the reports quoted below were produced by running it on the record, drafts and manifests
described here (2026-10-29).

## Scenario

The author of example 02 has a 20-minute conference slot to present what is known about the coefficient c. There is
no paper of their own: the material is the communication record of the review section, with one claim per fit (each
with an evidence edge to its literature record, status `synthetic` in this example) and a synthesis claim whose edges
point to all three. The audience knows EFT fits but not these three analyses.

## Common Weak Approach

The author reuses the single-result talk template and makes the most precise fit the central claim:

```text
Talk (20 min): the coefficient c
Fit B gives the most precise value, c/Lambda^2 = 0.18 +/- 0.09 TeV^-2 (synthetic).
All three fits agree; the average is c/Lambda^2 = 0.23 +/- 0.07 TeV^-2.
```

The manifest names `claim:FB` as the central claim and maps the second line to the synthesis claim. The check fails
(exit 1):

```text
error   adaptation.status_dropped   statement st:avg draws on claim:SYN labeled ['synthetic'] but carries no such label
error   adaptation.number_mismatch  number 0.23 in statement st:avg matches no value, uncertainty or display value of ['claim:SYN']
error   adaptation.number_mismatch  number 0.07 in statement st:avg matches no value, uncertainty or display value of ['claim:SYN']
error   adaptation.caveat_dropped   indispensable limitation 'the fits differ in truncation and energy range' does not appear in the draft
warning adaptation.unmapped_number  number 20 in the draft is outside every mapped statement
```

The report also lists the exponents 2 and -2 of the second line as unmatched, because the synthesis claim carries no
value with units. The substance is what a reader would miss: an average that exists in no source, a talk centred on
one study when the question is the spread between three, and the truncation condition gone.

## Expert-Level Best Practice

The brief takes the synthesis claim as the central claim and the condition that explains the spread as the
indispensable limitation. Each fit gets one statement with its value, uncertainty, conditions and status; the title
line and the open question carry layout or context numbers (20 minutes, dimension-8) and are recorded as `context`
statements.

```text
Review talk (20 min): what sets the spread in the coefficient c (synthetic fits)

Question: what sets the spread in c?
Comparison conditions: truncation (linear or quadratic) and the highest energy used.
Fit A, linear in c with data up to 1 TeV, gives c/Lambda^2 = 0.42 +/- 0.15 TeV^-2 (synthetic).
Fit B, with quadratic terms and data up to 2 TeV, gives c/Lambda^2 = 0.18 +/- 0.09 TeV^-2 (synthetic).
Fit C, with quadratic terms and data up to 1 TeV, gives c/Lambda^2 = 0.21 +/- 0.12 TeV^-2 (synthetic).
The spread follows from the truncation of the EFT expansion: the quadratic fits agree and the linear fit sits higher (synthetic).
We do not average the three values; in our judgement the quadratic fits are the better guide below 1 TeV.
Open question: the size of dimension-8 terms near 2 TeV.
```

The manifest's brief and statements:

```json
{"brief": {"audience": "conference", "format": "talk-outline", "length_budget": "20 minutes",
           "central_claim": "claim:SYN", "record_ref": "artifacts/comm_review.json",
           "indispensable_limitations": [{"text": "the fits differ in truncation and energy range",
                                          "as_written": "truncation (linear or quadratic) and the highest energy used"}]},
 "statements": [
  {"id": "st:ctx", "claim_ids": [], "kind": "context", "text": "Review talk (20 min): what sets the spread in the coefficient c (synthetic fits)"},
  {"id": "st:a", "claim_ids": ["claim:FA"], "kind": "quantitative", "text": "Fit A, linear in c with data up to 1 TeV, gives c/Lambda^2 = 0.42 +/- 0.15 TeV^-2 (synthetic)."},
  {"id": "st:b", "claim_ids": ["claim:FB"], "kind": "quantitative", "text": "Fit B, with quadratic terms and data up to 2 TeV, gives c/Lambda^2 = 0.18 +/- 0.09 TeV^-2 (synthetic)."},
  {"id": "st:c", "claim_ids": ["claim:FC"], "kind": "quantitative", "text": "Fit C, with quadratic terms and data up to 1 TeV, gives c/Lambda^2 = 0.21 +/- 0.12 TeV^-2 (synthetic)."},
  {"id": "st:s", "claim_ids": ["claim:SYN"], "kind": "conclusion", "text": "The spread follows from the truncation of the EFT expansion: the quadratic fits agree and the linear fit sits higher (synthetic)."},
  {"id": "st:open", "claim_ids": [], "kind": "context", "text": "Open question: the size of dimension-8 terms near 2 TeV."}]}
```

The check passes with no finding (exit 0; coverage: 6 statements declared and located, 4 with a claim, 1 of 1
indispensable limitation present). Before the open question was recorded as a context statement, the same draft
passed with one warning, `number 8 in the draft is outside every mapped statement`, from "dimension-8".

The check is mechanical: it confirms numbers, labels, the limitation and the claim ids. The author still reads the
outline against the claim matrix and records the semantic review (who, when, verdict) in the manifest, and adds a
backup slide per fit with its literature record and read level.

Limits of this example: an outline, not slides; the 20-minute timing, speaker notes and a Q&A bank are written only if
asked for, and no rehearsal or audience effect is claimed.

## Key Takeaways

- A talk about several studies is a review talk: its central claim is the synthesis, with one claim per study, each
  traced to its own source; centring it on the most precise study changes the question.
- The condition that explains the spread is an indispensable limitation and survives every cut, however short the slot.
- A number that no source gives (here an average) is caught as a mismatch; a combination belongs to hep-statistics
  before it can appear on a slide.
- Layout numbers (slot length, slide numbers) and context numbers go into `context` statements, so the remaining
  warnings point at real gaps.
