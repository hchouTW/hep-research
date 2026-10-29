# Host capabilities, independence and submissions

Spec v9 sections 4.3, 12. Measured host profile: `assets/host_profile.json` (from the T0S measurements of
2026-10-29, Claude Code CLI on macOS; development record `docs/dev/hep-review/host-profile.md`).

## What this host provides (observed)

| Capability | Determination | Consequence |
|---|---|---|
| Fresh-context subagents (Agent tool) | observed | fresh context can be recorded as observed per assignment from the dispatch record |
| Sibling drop files and transcripts readable by reviewers | observed (readable) | "no other evaluations seen" is advisory only; the report carries the advisory sentence |
| Reviewer can write host transcripts | observed (writable) | `host-transcript` fidelity never qualifies |
| Real parallel dispatch | observed | first-round reviewers can all be dispatched before any submission lands |
| Reviewer file-write tool and SHA-256 | observed (16/16) | file-transfer is feasible; digest-bound when the reviewer reports the digest |
| Store persistence across sessions | pending the next session | hand over checkpoints; export when moving hosts |
| Runtime restrictions (tools, network, filesystem) | none enforced | R3 not reachable; "do not do X" in a prompt is advisory |
| Store isolation | protocol-only (a reviewer shell could write it) | foreign commits are detected by head continuity, not prevented |

On another host, re-measure before claiming any of these; a capability not observed is `unknown`, never assumed.

## Independence conditions

Record each condition per assignment with a basis from: observed, declared, self-reported, advisory, inferred,
unknown. Different agent names, models or worktrees do not prove separation: when producer separation is unclear the
condition is `unknown` and not met. Supplying a reviewer with material that contains another evaluation is recorded
as contamination, and "no other evaluations seen" is then unmet for that assignment. Filesystem or execution isolation
is not in the floor; it is required only for blinded data, held-out gold or when the user asks, and this host cannot
provide it, so those uses are not supported here.

## Submission fidelity

| Level | Method | Sufficient for |
|---|---|---|
| digest-bound | drop file + the reviewer's reported SHA-256 matches the bytes read | rules out retyping and later changes |
| file-transfer (default) | drop path dedicated to the assignment, one write with a file-write tool, read by bytes with controlled reading | the R2 minimum |
| host-transcript | raw saved subagent output | only if reviewers cannot write it: not on this host |
| transcribed | the coordinator retyped it | at most R1 for the affected obligations |
| mismatch | digests differ | both copies kept; submission quarantined |

These prove the stored bytes are the submitted bytes, not that nobody else read or wrote the drop file.

Pass on the reviewer's reported digest exactly as reported. A reviewer that could not hash reports `SHA256:
unavailable`, which declares nothing (file-transfer). A reported value that differs is a mismatch even when the
review is right: in the g2x pilot one reviewer reported a digest it never computed, and the record was quarantined.

## Packets and dispatch

A packet names the obligations, the snapshot files to read, the drop path, the outcome vocabulary and the submission
form, and states that the material is data, not instructions. It never contains another evaluation, gold or rubric.
Group by owner skill and shared material; if grouping would make a reviewer the author of an obligation's material,
split it out (only that obligation would drop to R1). Dispatch all first-round reviewers before any submission
lands; second-round work (verification, a second reviewer) may see first-round results and records what it saw.
