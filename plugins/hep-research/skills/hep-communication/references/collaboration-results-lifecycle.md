# Collaboration results lifecycle

How a collaboration result moves from an internal note to a paper and proceedings, what may be cited or shown at
each stage, and what to record so the frozen numbers can be traced. Collaboration rules differ and are the
collaboration's; this file says what to ask and record, never what a given collaboration has approved. Nothing here
implies endorsement by any collaboration (SKILL.md invariant).

## Stages

| Stage | Typical form | Citable outside the collaboration? | Status label of its numbers |
|---|---|---|---|
| Internal note | analysis note, internal wiki or meeting slides | no; never quoted or shown outside | internal, not a result |
| Approved preliminary | conference note (a CONF note, a physics analysis summary or the collaboration's equivalent) and approved plots | yes, as the note, with its identifier | `preliminary` |
| Paper | journal article with arXiv preprint (where the collaboration posts one) | yes; supersedes the preliminary result | published (`observed` for measured data) |
| Proceedings | conference proceedings summarising approved results | yes, but cite the paper or note it reports for the numbers | as the result it reports |

Rules that follow:

- A number moves to a later stage only after that stage's approval; a draft never upgrades a `preliminary` value to a
  published one, and a superseded preliminary value is not quoted next to the paper's as if both stood.
- Proceedings add no new results: each number in them points to the approved note or paper it comes from.
- Approved plots are used as approved: same binning, labels and "Preliminary" mark (`physics-plots.md`, "Status
  label on every figure"); a re-drawn version needs its own approval.

## Review rounds and sign-off

Large collaborations review a result in rounds: an analysis review committee (or equivalent) on the method, an
editorial board on the paper, and a collaboration-wide reading before submission; smaller collaborations may merge
these. Ask the user which rounds apply and who signs off. In the `communication` record keep:

- the **frozen numbers** (the values approved at sign-off) as claims linked to their result artifacts, with the
  approval date and the approving body in the assessment rationale;
- each later change to a frozen number as a revision (`revision-impact-tracking.md`), re-approved before it is used.

## Proceedings venues

Proceedings of physics conferences commonly appear in:

- *Proceedings of Science* (PoS, SISSA): for example ICRC 2021 is PoS volume 395 (37th International Cosmic Ray
  Conference, https://pos.sissa.it/395/) and ICHEP 2022 volume 414 (41st International Conference on High Energy
  Physics, https://pos.sissa.it/414/) (both opened 2026-10-14);
- *EPJ Web of Conferences* (EDP Sciences; its site refused automated access on 2026-10-14, so unverified here);
- *Journal of Physics: Conference Series* (IOP Publishing, https://iopscience.iop.org/journal/1742-6596, opened
  2026-10-14).

Take the template, page limit and deadline from the conference's own instructions; they differ by conference and
year.

## What to ask before drafting

1. Which stage is the text for, and which approved note or paper holds its numbers?
2. Which plots are approved, and may they be modified?
3. Who must sign off (speaker approval for a talk, editorial board, conference committee)?
4. Is any of the material internal? If so it stays out of anything public.

**Done when:** every number in the text points to an approved note or paper at the right stage with its status label,
the sign-off required for the stage is recorded in the `communication` record, and no internal material appears.
