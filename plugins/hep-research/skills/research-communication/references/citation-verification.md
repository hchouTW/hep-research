# Citation verification

Use for a reference audit, questionable attribution, or checking the evidence
behind manuscript claims. For export and formatting, use
`citations-and-bibliography.md`.

## Table of contents
- [Verification steps](#verification-steps)
- [Deliverable](#deliverable)
- [Tooling note](#tooling-note)

## Verification steps

1. Establish scope: all references, a specified section, or selected consequential
   claims. If sampling, report the selection and do not certify the whole paper.
2. Resolve each reference against the publisher, original repository, or relevant
   scholarly index. Compare title, authors, year, DOI/arXiv identifier, and version;
   do not accept a plausible title or a search snippet as verification. This
   includes an AI-generated summary of a fetched page: a summarization pass can
   misreport a count, date, or list length even when the page was fetched
   correctly — treat it the same as a search snippet, not as having checked the
   source. For anything numeric or enumerable (a publication count, a list of
   entries), get the itemized content or the raw page/record directly, or
   cross-check two independent passes, rather than trusting one summarized answer.
3. Read the relevant passage, equation, table, or figure in the primary source.
   Check the population/dataset, conditions, uncertainty, and qualifiers against
   the citing sentence. Separate direct support from inference and secondary
   attribution; locate the original source for priority claims when possible.
4. Check current publisher/repository records for corrections, retractions, and
   version changes. Record the lookup date and sources consulted. If access or
   network limits prevent a check, mark it unverified rather than inferring that
   no notice exists. A notice requires assessing its effect on the specific claim,
   not silently deleting the citation.
5. Propose the smallest correction: narrow the claim, fix metadata, cite the
   relevant version, or supply a verified replacement. Preserve citation keys
   unless renaming is necessary; update their callers together if changed.

## Deliverable

Deliver a ledger with: manuscript location and claim; citation key and stable
identifier/version; evidence locator and source link; metadata/status findings;
support verdict (supported, partial, unsupported, or unverified); proposed fix.
Keep metadata correctness separate from evidentiary support. Report unresolved
items explicitly, including sources available only as abstracts.

## Tooling note

`check_manuscript.py` checks local reference consistency; it does not establish
that a source exists, remains current, or supports a scientific claim.
