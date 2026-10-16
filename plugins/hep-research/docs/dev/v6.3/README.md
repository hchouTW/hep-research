# v6.3 analysis-check programme: development records

Design and decision records of the v6.3 programme (opt-in cross-artifact checks). These are records for maintainers,
not instructions for the agent, and nothing in them authorizes any use: agent-run checks are advisory (HC-05).

| File | Work package | Content |
| --- | --- | --- |
| `m0-baseline.md` | D01 | checkout identity, facts table, gap runs, consumer inventory |
| `m0-budget.md` | D02 | loading-budget and evidence-query measurements, with the method |
| `decision-m0.md` | G-M0 | the M0 decision record |
| `decision-m2a.md` | G-M2a | the M2a decision record with the measured context cost |
| `decision-m2b.md` | after M2b ratio and D11b | what comes next: M3, the model part or a pause |
| `m2a-design.md` | M2a | data model of the chain slice |
| `o16-agent-interface.md` | D17 | who calls the check, when, where the summary goes |
| `refusal-matrix.md` | D09 | what old readers do with each new format; release blockers |
| `shadow-review.md` | D09 | legacy-versus-new difference review per case |
| `crflux-review.md` | D03b | term-by-term review of the cosmic-ray level terms; companion public-interface matrix |

## Decision-record convention (D12b)

Each gate of the programme (G-M0, G-M2a, G-SCHEMA, G-ENFORCE) has one record, `decision-<gate>.md`, written by the
implementer before stopping and completed by the maintainer. A record states:

1. the analysis question the gate answers;
2. testable counterexamples found, each with the committed test that reproduces it;
3. cost per remaining phase, with what the estimate rests on;
4. the owner (a named person; "Requires Confirmation" until the maintainer names one);
5. the options of the gate, the recommended one, and the scope dropped under each;
6. a label on every statement: **Confirmed** (checked in the checkout, evidence named), **Inferred**, or
   **Unresolved**;
7. a *Decision* section the maintainer fills in (option chosen, date, conditions). A gate is passed only by that
   entry or an explicit maintainer instruction, never by the implementer.

A record is never rewritten after its decision; a changed decision is a new dated section.

## Companion transition

The programme stays at companion transition stage 1 (inventory and report only, C15): no companion field becomes
required, missing new fields are unverified, and existing compatibility paths stay. Stages 2 and 3 need a maintainer
decision (O11).
