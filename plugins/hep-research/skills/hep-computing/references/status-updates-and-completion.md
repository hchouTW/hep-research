# Communication

Use this reference for concise Agile collaboration, status updates, and completion summaries.

## During Work

- Be concise, concrete, and oriented to user outcomes.
- Surface important discovered constraints or risks as soon as they affect direction.
- State assumptions that materially shape implementation.
- Use repository terminology and filenames accurately.
- Avoid claiming certainty where repository evidence or validation does not support it.
- Do not overwhelm the user with routine internal operations.

## Stakeholder Feedback

- Treat feedback as new information about the desired outcome, constraints, or usability.
- Distinguish defects from preference changes and new scope.
- Reconfirm acceptance criteria when feedback changes behavior or priority.
- Prefer a follow-up slice when feedback is valuable but not required for the current increment.
- Explain trade-offs in concrete terms: user impact, maintenance cost, risk, and validation effort.

## Completion Summary

Use this structure when it fits the task:

```md
## Summary
- Implemented: <user-visible behavior or maintenance outcome>
- Changed: <key files or components>

## Verification
- Passed: `<command>`
- Not run: `<command>` - <reason>

## Notes
- Assumption: <only when material>
- Follow-up: <only when relevant and outside scope>
```

For small tasks, collapse this into one or two short paragraphs plus a verification line.

## Useful Phrases

- "I found the relevant path in `<file>` and the local convention is `<pattern>`."
- "The smallest slice that satisfies this is `<behavior>`; `<larger behavior>` is follow-up scope."
- "Validation passed for `<command>`. I did not run `<command>` because `<reason>`."
- "This change assumes `<assumption>`. If that is wrong, the affected behavior is `<impact>`."
- "The remaining risk is `<risk>`, bounded by `<evidence or validation>`."

## Anti-Patterns

- Do not present speculation as repository fact.
- Do not bury failing validation under a broad positive summary.
- Do not describe internal file edits without connecting them to user-visible value.
- Do not silently expand scope to satisfy ambiguous feedback.
