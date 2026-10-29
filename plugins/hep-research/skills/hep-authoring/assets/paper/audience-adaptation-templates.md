# Audience adaptation templates

Agent-executable skeletons for deriving a manuscript paragraph, a meeting abstract, a short talk outline, poster content
or a public-facing summary from a verified communication record, and for a referee response letter. Every derived draft
travels with a companion manifest (`adaptation-manifest-template.json`) and is checked with
`<plugin root>/skills/hep-authoring/scripts/check_adaptation.py RECORD --project-root ROOT --manifest M --draft D`.
All examples are synthetic placeholders.

## Workflow

1. Write the brief first: audience, format, length or time budget, the central claim (one claim id), the record
   version (its sha256), and the limitations that must survive whatever the length (indispensable: they change the
   scientific meaning; a public summary of a synthetic or preliminary result says so).
2. Draft from the draft-ready facts of `audit_claims.py` (value, unit, uncertainties, status, source locator): one
   manifest statement per quantitative statement or scientific conclusion, with its claim id. Context sentences need
   no claim id. Keep numbers and status labels exactly as the record gives them; put a missing number in a
   `[VALUE NEEDED: ...]` slot and its request in `unresolved_inputs`.
3. Record intentional omissions with the reason they do not change the meaning for this audience. Compression removes
   detail, never a condition.
4. Run the check; fix every error; then read the draft against the claim matrix and record the semantic review in the
   manifest (keyword overlap is not a semantic check).

Slide numbers, the time budget and similar layout numbers carry no claim but raise `adaptation.unmapped_number`
warnings: record the line that holds them as a `context` statement (no claim id), or keep the warning and say in the
semantic review why it carries no scientific content.

Which template: a manuscript paragraph, meeting abstract, short talk, poster or public summary of one result; a review
talk when the talk compares or synthesizes several studies or sources; a referee response letter for replies.

## Manuscript paragraph

```
<Topic sentence: what was measured, in which sample and regime.> <Result sentence with the value, unit and
uncertainties as recorded, with the status label where the record carries one.> <Comparison or interpretation sentence,
stating what is compared and the caveats that qualify it.> <Limitation sentence: the conditions the result holds for.>
```

## Meeting abstract (120-250 words)

```
Context (1-2 sentences). Method and sample (1-2 sentences: dataset, period, selection in words). Result (the central
claim with value, uncertainties and status). Interpretation (1 sentence, with its caveat). Outlook (optional, 1 sentence;
planned work is described as planned).
```

## Short talk outline (10-15 minutes)

```
1. Why (1 slide): the question and what a result would mean.
2. Setup (1-2 slides): sample, selection, method; status labels on every number shown.
3. Result (2-3 slides): the central claim; the figure with its caption claim ids; the uncertainty breakdown.
4. Checks (1-2 slides): what was validated and what was not.
5. Summary (1 slide): the central claim as recorded, its scope, the limitations, what is next.
```

## Review talk outline (several studies or sources, 15-25 minutes)

One communication record holds one claim per study, each with its own evidence edge to the result artifact or
literature source it comes from, and a synthesis claim (what the comparison shows, with the conditions that make the
studies comparable) whose edges point to all of them. The synthesis claim is the brief's central claim.

```
1. Question (1 slide): the physics question the studies answer and why it matters now.
2. Comparison conditions (1-2 slides): what each study measured or computed, in which range and with which model or
   method; the conditions that make results comparable or not.
3. Results side by side (2-4 slides): one statement per study with its value, uncertainty and status as recorded and
   its source; no number without its source.
4. Synthesis (1-2 slides): the synthesis claim; where the studies agree, where they disagree and why (range, model,
   data), and what is the speaker's own judgement.
5. Open questions (1 slide): what would resolve the disagreement; planned work described as planned.
```

## Poster content

```
Title | Authors and affiliations as approved
Motivation (3 bullets) | Method (3 bullets + 1 figure) | Result (the central claim, its figure and caption, status
label) | Limitations (2-3 bullets: scope, uncertainty definition, what is preliminary) | Contact
```

## Public-facing summary (80-150 words)

```
What was studied and why it matters (2 sentences, no jargon). What was found (the central claim in words, with the
number if it carries meaning for the audience, with its status: "in a simulated test", "a preliminary result"). What it
does not show (1 sentence: the tested regime, the open questions). Who did it and where to read more.
```

## Referee response letter

Build the action table from the record (`check_adaptation.py RECORD --project-root ROOT --responses`): each comment
with its claims, revision items and their states, locators and completion evidence. Paste the generated wording and
edit the tone, not the facts: a completed, checked change is described in the past tense with its locator; a pending
rerun or regeneration stays explicit ("is pending"; "will be updated once ... is completed and checked"); a reasoned
decision not to change the manuscript is stated with its reason. Several comments may map to one change and one
comment to several; the table keeps the links so the replies agree with each other.
