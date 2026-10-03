# Implementation Discipline

How to behave while making the change, as distinct from how to scope it
([product-framing.md](product-framing.md)) or how to check it
([validation-and-done.md](validation-and-done.md)). These are the failure modes that
show up in the diff rather than in the plan: guessing instead of asking, writing more
code than the problem needs, editing more than the request touches, and calling
something done without a definition of done.

## Ask or assume: decide by cost, not by comfort

Ambiguity is not one situation, and a single default handles it badly. Both reflexes
fail in a predictable way: always assuming produces confident work on the wrong
problem, and always asking stalls on questions the repository could have answered.

Decide by what being wrong costs:

**Ask before proceeding** when a wrong guess is expensive or hard to undo. Asking means
stopping: end your reply with the questions (and a recommended default for each) and do
not go on to implement, or write a plan that implements, in the same turn:

- Schema, migration, or anything that writes to persistent data.
- A published API contract, wire format, or anything other code depends on.
- User-visible behavior, copy, or defaults.
- Anything outward-facing: sending, publishing, deleting, or spending.
- Work large enough that the wrong interpretation wastes substantial effort.

Ask at most four questions, most costly first, and only ones whose answer would change
what you build. Fold everything else into a stated default ("unless you say otherwise, I
will ...") rather than a further question.

These apply to what the request leaves open. If it already states the behavior, contract,
or scope you would have asked about, take it as given and do not ask again.

**Assume and say so** when a wrong guess is cheap to correct: internal naming, file
placement, test structure, and anything the repository's existing conventions already
imply. State the assumption in the response so it can be corrected in one line.

If you cannot ask (a non-interactive run, or no one is reachable): for the "assume and
say so" cases, proceed and state the assumption. For the "ask before proceeding" cases,
never assume the destructive or irreversible option. Do the read-only work (find what
the repository already answers), stop before any irreversible or outward-facing step,
and report the questions you would have asked. If something must ship, take the
reversible option (for example soft-delete over hard-delete) as a clearly labeled draft.

Two related habits, independent of which branch applies:

- **Present competing interpretations instead of silently picking one.** If the request
  reads two ways, name both and say which you took and why. Picking silently hides a
  decision the requester would have made differently.
- **Push back when a simpler approach exists.** Say so in a sentence, then proceed with
  what was asked unless told otherwise. Raising it once is useful; relitigating after a
  decision is not - see [status-updates-and-completion.md](status-updates-and-completion.md).

Do not hide confusion. If the request cannot be interpreted well enough to act on,
naming exactly what is unclear is faster than producing something plausible and wrong.

## Simplicity: the minimum code that solves the problem

Scope slicing decides *what* to build; this decides *how much code* to write for the
slice. They are different, and a correctly-scoped change can still be twice the code it
needs.

Write nothing speculative:

- No features beyond what was asked.
- No abstraction for code with a single caller. An interface with one implementation is
  indirection, not design.
- No configurability, flags, or extension points that were not requested.
- No error handling for states that cannot occur. Handling an impossible case is dead
  code that implies a possibility that does not exist.
- No premature generalization from a single example.

The test: **would an experienced engineer reading this call it overcomplicated?** If the
answer is yes, rewrite it. If a 200-line implementation could be 50, the 50-line version
is the deliverable.

This is a bias, not an absolute. Genuine complexity in the problem justifies complexity
in the solution; what it does not justify is complexity added in anticipation of
requirements that have not arrived. When a simplification would lose behavior the
request depends on, keep the behavior and say why.

## Surgical changes: every changed line traces to the request

Touch only what the request requires. Specifically, when editing existing code:

- Do not "improve" adjacent code, comments, or formatting.
- Do not refactor what is not broken and not in scope.
- Match the surrounding style even where you would write it differently. Consistency
  with the file beats consistency with your preference.
- Reformatting churn makes a diff unreviewable and hides the real change inside it.

**The orphan asymmetry.** These two cases look similar and are not:

| Situation | Action |
|---|---|
| Your change left an import, variable, or function unused | **Remove it.** You created it; clean it up. |
| Dead code that was already there | **Mention it, don't delete it.** It is not your change, and removing it makes your diff hard to review and may break something you cannot see. |

Discovered problems get reported, not fixed in passing - the same rule as noting
follow-up work rather than silently expanding scope.

**The test:** every changed line should trace directly to the request. A line you cannot
justify that way is scope you added without being asked.

## Goal-driven execution: define done before starting

A task with weak success criteria needs constant clarification. A task with strong ones
can be worked to completion and verified independently. Convert the request into
something checkable before writing code:

| Vague request | Verifiable goal |
|---|---|
| "Add validation" | Write tests for the invalid inputs, then make them pass |
| "Fix the bug" | Write a test that reproduces it, then make it pass |
| "Refactor X" | Confirm the tests pass before and after, with behavior unchanged |
| "Make it faster" | Measure it, state the target, measure again |

For work with three or more steps, state the plan with a verification attached to each step:

```
1. <step>  -> verify: <the check that proves it>
2. <step>  -> verify: <the check that proves it>
3. <step>  -> verify: <the check that proves it>
```

A step whose verification is "it looks right" is not verified. The check should be a
command that runs, a test that fails before and passes after, or an observation someone
else could repeat - see [validation-and-done.md](validation-and-done.md) for the
validation ladder, and `${CLAUDE_PLUGIN_ROOT}/skills/hep-computing/scripts/validate_agile_notes.py --require-plan-verification`
to check a written note for this structure.

## Applying proportionally

These guidelines bias toward caution, and caution has a cost. For a one-line fix,
"present competing interpretations" and a numbered verification plan are overhead, not
discipline. Scale to the change: the smaller and more reversible it is, the more of this
collapses into simply doing it and saying what you did.

---

*Derived from the MIT-licensed `karpathy-guidelines` skill, itself based on
[Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) on
common LLM coding failures. Rewritten and restructured here to fit this package's
conventions and to resolve conflicts with its existing guidance; any errors are this
package's own.*
