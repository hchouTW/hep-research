# Mathematical reasoning and proof

Use when evaluating or constructing a mathematical derivation or argument —
checking whether a paper's result actually follows from its stated assumptions,
or reasoning through one's own derivation before writing it up. Distinct from
`../../research-communication/references/equation-and-notation-auditing.md`, which checks the algebra's internal
consistency (dimensions, indices, sign/normalization conventions) once a
derivation is written down; this file checks the argument's *validity and
justified strength* — whether the assumptions are sound, whether the proof
status matches what's claimed, and how to verify the result independently of
the derivation itself. Also distinct from
`../../research-communication/references/logical-consistency-and-argument-uniformity.md`, which checks a paper's prose
argument for cross-section contradictions; this file is about a specific
mathematical derivation's own soundness.

## Table of contents
- [Reasoning workflow](#reasoning-workflow)
- [Proof status](#proof-status)
- [Approximation validity](#approximation-validity)
- [Mathematical checks](#mathematical-checks)
- [Counterexample search](#counterexample-search)
- [Separating derivation from verification](#separating-derivation-from-verification)
- [Evidence-strength ladder](#evidence-strength-ladder)

## Reasoning workflow

Work through a derivation in this order, and expect a rigorous paper to make
each step identifiable even if not explicitly labeled:

```text
Assumptions → Definitions → Intermediate results → Derivation → Result → Consistency checks
```

For each step, identify:

- **Explicit assumptions** the author states, and **implicit assumptions**
  the derivation actually relies on but doesn't name (smoothness,
  independence, a regime where a series converges).
- **Definitions** — is every symbol introduced before use, with a consistent
  meaning throughout (delegate the symbol-ledger mechanics to
  `../../research-communication/references/equation-and-notation-auditing.md`)?
- **Necessary vs. sufficient conditions** — does the argument establish that a
  condition is required for the result, or merely that the result holds when
  the condition is met (these are not interchangeable when the conclusion is
  later applied outside the stated condition)?
- **Approximation regime** — where in the derivation is an expansion,
  linearization, or asymptotic limit taken?
- **Intermediate dependencies** — does a later step silently reuse an earlier
  intermediate result outside the regime where that result was valid?
- **Final conclusion** — restate it in one sentence and check it doesn't say
  more than the chain of steps established.

## Proof status

Require every mathematical result to carry an explicit status, and never let
one silently become another when the result is reused later in the same paper
or in a summary of it:

- **Formal proof** — every step follows from stated axioms/premises with no
  unstated gap.
- **Analytic derivation** — an exact algebraic/calculus result under stated
  assumptions, not from first principles/axioms.
- **Perturbative argument** — valid to a stated order in an expansion
  parameter; the neglected terms are not shown to vanish, only to be small in
  some regime.
- **Asymptotic argument** — valid in a limit (large N, high energy, weak
  coupling); the rate of approach to the limit is a separate, often unstated,
  question.
- **Heuristic argument** — motivates a result without establishing it
  (dimensional-analysis scaling, a plausibility argument, an analogy to a
  solved case).
- **Numerical evidence** — a computed instance or scan consistent with the
  claim, not a general demonstration of it.
- **Empirical observation** — a pattern seen in data, with no claimed
  theoretical mechanism yet.
- **Conjecture** — an unproven claim offered as a research direction.

**Never silently upgrade a heuristic argument, numerical observation,
perturbative result, or empirical pattern into a proof.** The most common
version of this error is a perturbative or asymptotic result described in the
abstract or conclusion using unqualified language ("the result is X") that
reads as exact — check the Results/Methods section for the actual status
before accepting the abstract's phrasing.

## Approximation validity

For any approximation-based result, identify:

- The **expansion parameter** and its actual numeric value/range in the
  regime being applied.
- The **validity regime** — the condition under which the approximation is
  expected to hold (small parameter, large separation of scales, weak
  coupling).
- The **neglected terms** — what order was dropped, and is there a stated or
  computable bound on their size?
- The **expected order of corrections** — does the paper's own claimed
  precision match what the truncation order can actually support, or does it
  claim finer precision than the retained terms justify?

## Mathematical checks

Use the subset appropriate to the result — not every check applies to every
derivation:

- **Limiting and special cases**: does the result reduce to a known answer in
  a simple limit (zero coupling, one dimension, equal masses)?
- **Symmetry arguments and conservation laws**: does the result respect the
  symmetries the underlying theory/setup actually has (and correctly break
  the ones it explicitly breaks)?
- **Perturbative consistency and asymptotic behavior**: does the next order
  (if computable) actually shrink relative to the claimed order, and does the
  result behave sensibly as parameters go to their extreme values?
- **Order-of-magnitude estimate**: does a quick dimensional/scaling estimate
  land near the detailed result, catching a stray factor of the wrong scale?
- **Sign and normalization checks**: does a probability, rate, or cross
  section come out non-negative and correctly normalized?
- **Numerical spot check**: evaluate the symbolic result at a specific point
  and compare against a direct numerical computation of the same quantity.
- **Symbolic verification**: use a computer-algebra check of an algebraic
  step, especially a long or error-prone one.
- **Independent derivation**: re-derive the result via a different method or
  starting point (see below) — the strongest single check, when feasible.

A numerical spot check or symbolic simplification that succeeds *corroborates*
a derivation; it does not, by itself, establish a general proof. Report which
checks were actually performed and over what domain.

## Counterexample search

When evaluating a broad mathematical claim (holds "for all N," "in general,"
"for any coupling"), actively look for:

- Boundary cases (parameter at zero, at its physical limit).
- Singular or degenerate cases (a matrix losing rank, two masses becoming
  equal, a denominator approaching zero).
- Conditions under which the stated argument's assumptions plausibly fail.

**The absence of an immediately found counterexample is not proof that the
claim is general** — report a counterexample search as "no counterexample
found in {these cases}," not as confirmation.

## Separating derivation from verification

Generating a result and checking it should use partially independent
reasoning wherever the result matters enough to justify the extra effort —
reusing the exact same assumptions and transformation path as the only
verification just re-checks the arithmetic, not the argument.

```text
Derivation: symbolically derive the expression via method A

Verification: evaluate limiting cases, check dimensions
(equation-and-notation-auditing.md), perform a numerical spot check, and —
for an important or novel result — attempt an independent derivation via a
different method or starting point
```

Scale the number and independence of checks to the claim's importance,
novelty, numerical sensitivity, and the cost of being wrong — a routine
intermediate step doesn't need the same treatment as a paper's central result.
This is the general form of the cross-check hierarchy that
`../../hep-computing/references/numerical-and-computational-methods.md`'s validation workflow applies
specifically to numerical results, and that
`../../hep-statistics/references/statistical-inference-for-physics.md` applies to a statistical claim's
calibration — treat all three as instances of the same principle rather than
independent rules.

## Evidence-strength ladder

When recording a theoretical claim in `../../research-communication/references/claim-evidence-mapping.md`'s evidence
matrix, state its justified strength using the proof-status categories above
(formal proof, analytic derivation, perturbative argument, asymptotic
argument, heuristic argument, numerical evidence, empirical observation,
conjecture) rather than a bare "supported"/"unsupported" verdict — the verdict
answers whether the evidence matches the claim; this ladder answers how strong
that evidence actually is on its own terms.
