# Source policy: EIC profile

> Method owner: [research-communication](../../../../../skills/research-communication/SKILL.md) for literature verification and citation practice; this module fixes the tiers and rules for EIC and ePIC material.

## Tiers

| Tier | Class | Use |
|---|---|---|
| 1 | Peer-reviewed ePIC Collaboration or EIC project papers | ePIC or EIC results and methods |
| 2 | Official EIC project and laboratory documents and pages (CDR, BNL/JLab pages), official ePIC collaboration pages and software documentation, the EIC User Group Yellow Report | Facility design targets, experiment identity, detector concept, software entry points |
| 3 | Public talks, proceedings and theses by collaboration authors | Context, labeled preliminary; supports no primary claim alone |
| 4 | PDG, textbooks, peer-reviewed methodology | General principles (owned by the skills, not this profile) |
| 5 | Other experiments (HERA, LHC) | Methodological comparison only; never EIC or ePIC practice |
| 6 | Reviews, press, slides, secondary articles | Navigation only, labeled secondary |

## Rules

- Three dates: the **current date**, the **publication date** of a source, and its **verification date** (the day it was read at the stated level) are separate fields. Never present a verification date as today's date.
- A source published after the last verification date is **unverified, not nonexistent**; it enters the ledger at the level actually read.
- Kinds of number: design target, design value, simulation projection, test-beam result, measurement. Each claim's `scope.text` and `limitations` say which. This profile ships only design targets and design values.
- A number may be quoted only from a claim whose `numeric_quotation_allowed` is true, which the validator allows only at `page` level or better.
- "Latest": say what the ledger's newest verification date is and that anything later is unverified; do not guess.
- Unsupported: when no claim covers a statement, say "not in the profile's evidence" and name the source class that would (Tier 1 or 2), or ask the user for the document.
