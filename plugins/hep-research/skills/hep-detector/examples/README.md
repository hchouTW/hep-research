# Worked examples

Illustrative: the dialogues, notes and numbers are constructed and name no experiment. They show when to ask before
running Geant4, and when to refuse to upgrade a label. The tools they name are real; run them on real inputs before
relying on an answer. The protocol is [the Geant4 study protocol](../references/geant4-study-protocol.md); a worked
journey with real runs is [examples/geant4-thin-silicon](../../../examples/geant4-thin-silicon/run.py).

| File | Case | Takeaway |
|---|---|---|
| [01-geant4-elicitation.md](01-geant4-elicitation.md) | "simulate a silicon detector with Geant4 for me" | ask for the observable, particle and energy, geometry and material source, and precision target before any run; end with a study spec |
| [02-geant4-adversarial-audit.md](02-geant4-adversarial-audit.md) | a Geant4 note that calls its results validated | each flaw maps to a rule, the convergence gate or a benchmark; the highest usable label is `unvalidated` |
