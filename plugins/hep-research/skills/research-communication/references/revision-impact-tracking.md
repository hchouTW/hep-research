# Revision-impact tracking

Use when a result, interpretation, dataset, or reviewer request changes during
revision. This tracks dependencies while edits are made; use
`manuscript-consistency-auditing.md` to check the resulting snapshot and
`submission-and-peer-review.md` to write the response.

## Establish the change and affected artifacts

Identify the baseline and revised versions, the trigger (reviewer/comment ID,
corrected analysis output, or author decision), and the verified source of the
change. If the new result is not established, track it as pending rather than
propagating a guessed value. Preserve existing edits and version history.

Trace direct and interpretive dependencies as appropriate:

- Changed numbers: tables, plots and their source data/scripts, captions, abstract,
  result statements, uncertainty/significance claims, and comparisons.
- Changed methods/data: selections, definitions, sample counts, normalization,
  reproducibility details, limitations, and any result that needs rerunning.
- Changed interpretation: title, contribution statement, Introduction, conclusion,
  related-work comparison, and cover/response letters.
- Moved or added material: labels, cross-references, bibliography, supplements,
  numbering, page/length limits, and response-letter locations.

Search for quantities, labels, terminology, and paraphrases; literal text matches
alone miss conceptual dependencies. Distinguish artifacts that require editing
from those inspected and confirmed unaffected. Do not regenerate an analysis
simply because its result is mentioned; identify necessary reruns and route them
to the relevant domain skill within the authorized scope.

## Maintain a compact change ledger

For each change record: ID and trigger, old/new fact or decision, source/version,
affected artifacts and locators, required action, dependency/blocker, status, and
validation evidence. Useful statuses are pending evidence, ready to edit, edited,
and verified. One reviewer comment can map to several changes; several comments
can map to the same change. Retain those links rather than duplicating inconsistent
responses. Record a justified decision not to change the paper explicitly.

Use an existing revision log when available. Keep the record proportional to the
revision; a single correction may need only one row, not a separate tracking system.

## Close changes with evidence

After editing, inspect affected text and regenerated figures, check consistency
and references, and render/compile when layout or numbering could have changed.
Track blocked regeneration separately from prose edits. Mark a change verified
only after its listed dependencies have been checked, with any remaining limits
stated explicitly.

Write response-letter assertions from completed changes, using locators from the
final revised version. Do not say an experiment was run, a figure regenerated, or
a concern resolved when it remains planned. Preserve open items and factual
disagreements for the user. Deliver the updated artifacts, change ledger, and
unresolved dependencies; submission or sending the response is a separate action.
