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
   cross-check two passes that reach the source by different routes (two summaries of the same page by the same
   model are not independent), rather than trusting one summarized answer.
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

## Reusing previously verified records

A ledger entry or a `sources_read` record from an earlier session is reused as it
is: keep its verification date, version (arXiv version, DOI version), read level
and locators. It stays a statement about what was read on that date. Never
relabel an old read event as a new one, and never raise its read level without
reading again. Recheck before quoting when the claim is time-sensitive ("the
latest result", "still the best limit", "no correction has appeared"), when the
record's version differs from the version cited, or when the manuscript now cites
a passage the old locators do not cover; otherwise the old record supports the
same claim it supported before. A recheck is a new read event with its own date
beside the old one, not a replacement of it.

## Deliverable

Deliver a ledger with: manuscript location and claim; citation key and stable
identifier/version; evidence locator and source link; metadata/status findings;
support verdict (supported, partial, unsupported, or unverified); proposed fix.
Keep metadata correctness separate from evidentiary support. Report unresolved
items explicitly, including sources available only as abstracts.

## Tooling note

`check_manuscript.py` checks local reference consistency; it does not establish
that a source exists, remains current, or supports a scientific claim.
