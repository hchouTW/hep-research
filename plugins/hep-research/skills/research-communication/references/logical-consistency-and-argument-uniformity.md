# Logical consistency and argument uniformity

Use for checking that a manuscript's reasoning is internally consistent —
that stated premises, definitions, and assumptions don't conflict with each
other across sections, and that each conclusion actually follows from what
was argued. This is distinct from the skill's other consistency modes:
`claim-evidence-mapping.md` checks whether *evidence* empirically supports
a claim; `manuscript-consistency-auditing.md` checks whether *numeric
values* match across locations. This file checks the logical structure
itself — a paper can have perfectly matching numbers and still contain a
contradiction, a dropped assumption, or a conclusion that doesn't follow.
Use the argument-restructuring section of `paper-structure.md` once a gap
is found and the fix requires reorganizing text, not just noting it.

## Table of contents
- [Scope and the inference ledger](#scope-and-the-inference-ledger)
- [What to check for](#what-to-check-for)
- [Distinguishing real defects from style](#distinguishing-real-defects-from-style)
- [Classifying and delivering findings](#classifying-and-delivering-findings)

## Scope and the inference ledger

Establish scope (full paper, a specific argument, or a disputed section)
before starting; report unchecked portions explicitly.

Build a compact inference ledger for the paper's central argument: each
major step's stated premises/assumptions, its location, and the claim it's
meant to establish. Trace the full chain from motivating question through
method, result, and interpretation.

## What to check for

- **Cross-section contradiction**: a definition, assumption, or claim
  stated in one section that conflicts with one stated elsewhere,
  independent of any specific number — e.g., an independence assumption
  used to justify a method in the Analysis section that the Discussion's
  interpretation implicitly requires *not* to hold.
- **Dropped or silently-changed assumptions**: an assumption introduced
  early (a regime, an approximation, a scope restriction) that later
  derivations or conclusions ignore without flagging the change, rather
  than an assumption that is deliberately relaxed and stated as such.
- **Fallacious inference patterns**: circular reasoning (the conclusion is
  smuggled into a premise rather than derived), affirming the consequent,
  false dichotomy, and generalizing from a single case presented as if
  representative. Correlation-vs-causation conflation is
  `claim-evidence-mapping.md`'s territory when it's about evidence
  strength — flag it here only when the *argument's logic* asserts
  causation as a premise for a later step, not when it's a phrasing issue.
- **Definitional drift ("uniformity")**: a term used with one meaning in
  one section (e.g., "significant," "efficiency," "background," "novel")
  and a different meaning elsewhere without acknowledging the shift. This
  is the argument-level counterpart to `manuscript-consistency-auditing.md`'s
  numeric-value checks — same failure mode, applied to concepts and
  definitions instead of quantities.
- **Scope mismatch between argument and conclusion**: a conclusion or
  abstract claim broader than what the chain of reasoning actually
  established (a specific-regime result stated as general), or a
  conclusion that answers a different question than the one the
  Introduction posed.
- **Chain completeness**: whether motivation → question → method → result
  → interpretation has a genuinely missing link — not weakly evidenced,
  but logically absent (a jump with no stated bridging premise at all).

## Distinguishing real defects from style

Distinguish a real logical defect from informal-but-resolvable phrasing —
colloquial shorthand that a careful reading disambiguates without changing
the argument's validity is not a finding; over-flagging rhetorical style as
fallacy wastes author time and erodes trust in real findings.

## Classifying and delivering findings

Classify each finding as: confirmed contradiction, named fallacy pattern,
dropped/changed assumption, definitional drift, scope mismatch, or missing
link. For each, give the location(s), the specific inconsistency, why it
matters to the paper's conclusion, and the minimal fix — an added qualifier,
an explicit statement that an assumption changed, or a flag for the author
to resolve a substantive interpretive conflict. Never silently resolve a
finding that changes what the paper claims; that is the author's decision.

Deliver a ledger (location, finding, classification, impact, proposed fix)
and the scope actually checked. If the fix requires moving or restructuring
text rather than a local edit, hand off to `paper-structure.md`'s
argument-restructuring section rather than patching in place.
