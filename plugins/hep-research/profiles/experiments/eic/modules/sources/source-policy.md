# Source policy: EIC profile

> Method owner: [hep-citations](../../../../../skills/hep-citations/SKILL.md) for literature verification and citation practice; this module fixes the tiers and rules for EIC and ePIC material.

## Tiers

| Tier | Class | Use |
|---|---|---|
| 1 | Peer-reviewed papers signed by the whole ePIC Collaboration or by the EIC project | ePIC or EIC results, design values and methods |
| 2 | Official EIC project and laboratory documents and pages (CDR, preliminary design report, project requirements pages, BNL/JLab pages), official ePIC collaboration pages and software documentation, the EIC User Group Yellow Report, the ePIC Early Science Report (an official report, not peer reviewed), and peer-reviewed ePIC subsystem papers signed by a subset of the collaboration | Facility requirements and design targets, ePIC design values (construction parameters), experiment identity, detector concept, software entry points; from the Early Science Report only proposed run plans |
| 3 | Public talks, proceedings, preprints not yet published in a journal, and theses by collaboration authors | Context, labelled preliminary (`third_party_context`); supports no primary claim alone and, outside the geometry-case claims, no number |
| 4 | PDG, textbooks, peer-reviewed methodology | General principles (owned by the skills, not this profile) |
| 5 | Other experiments (HERA, LHC) | Methodological comparison only; never EIC or ePIC practice |
| 6 | Reviews, press, slides, secondary articles | Navigation only, labeled secondary |

## Rules

- Three dates: the **current date**, the **publication date** of a source, and its **verification date** (the day it was read at the stated level) are separate fields. Never present a verification date as today's date.
- A source published after the last verification date is **unverified, not nonexistent**; it enters the ledger at the level actually read.
- Kinds of number: design target, design value, simulation projection, test-beam result, measurement. Each claim's `scope.text` and `limitations` say which. Modules quote numbers only from numeric claims that carry a `scope.number_kind`:
  - `requirement`: a project requirement on a facility parameter (centre-of-mass energy range, luminosity, species, polarization); scope `EIC facility:`, atlas block with experiment "EIC";
  - `design-target`: a facility design parameter from the CDR or the Yellow Report; scope `EIC facility:`, atlas block with experiment "EIC";
  - `design-value`: an ePIC construction parameter only (dimensions, positions, angular or pseudorapidity coverage, materials, radiator media, segmentation, channel counts, magnetic field); scope `ePIC:`, atlas block with experiment "ePIC";
  - `proposal`: a run configuration proposed by ePIC (Early Science Report); scope `ePIC:`, no atlas block, and never presented as a facility value.
- Numeric claims are typed `detector_fact`. No number states performance, whatever the source calls it (goal, specification or requirement): no numeric claim, atlas quantity or module line near a number uses the words resolution, separation, efficiency, rejection, purity, acceptance, precision, accuracy, timing precision, noise or misidentification. An angular range is a coverage, never an acceptance. The geometry-case claims (eic:C10 to eic:C37) predate these rules, carry no `number_kind`, and source no number in a module.
- Read levels: a numeric claim is read at `full-text` when any of its sources is a paper or report, and at `page` only when every source is a web page (`formal_status` "web page").
- Derived numbers (for example the centre-of-mass energy of a configuration) get no claim of their own: a module writes them as a `derived:` bullet that names the cited inputs and the exact command of the plugin script that computes them, with the proton mass written in full from `core.constants`.
- A subsystem with no written source gets an `absence_search` claim: `claim_types` `["published_result"]`, scope text that says "search-limited, not a proof of absence", the queries and their date in `location`, and no number. Sources of Tier 3 to 6 support only `third_party_context` or `absence_search` claims.
- A number may be quoted only from a claim whose `numeric_quotation_allowed` is true, which the validator allows only at `page` level or better.
- "Latest": say what the ledger's newest verification date is and that anything later is unverified; do not guess.
- Unsupported: when no claim covers a statement, say "not in the profile's evidence" and name the source class that would (Tier 1 or 2), or ask the user for the document.
