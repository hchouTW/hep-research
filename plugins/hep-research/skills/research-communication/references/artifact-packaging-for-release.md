# Artifact packaging for release

Use when preparing the user's own code and data for public release alongside
a paper — the writing/production side. Use `reproducibility-auditing.md`
instead when the task is inspecting an *existing* artifact (someone else's,
or the user's own before release) for what it actually supports; use the
availability-statements section of `citations-and-bibliography.md` for the
manuscript-facing statement text once the artifact itself is ready to
describe.

1. Scope what's being released: full pipeline, analysis code only, a subset
   of data (privacy/size/licensing permitting), trained model weights, or
   some combination. Confirm with the user what can legally and practically
   be released — collaboration data-sharing agreements, human-subjects
   restrictions, and third-party dataset licenses can all block a full
   release even when the user wants one.
2. Make the headline result reproducible from the release, not just the
   general method. At minimum: the exact code path, configuration/
   hyperparameters, and data (or a documented way to obtain it) needed to
   regenerate the paper's central figure or number — a repository that
   "implements the method" but can't reproduce the reported result invites
   the exact criticism `reproducibility-auditing.md` is written to catch.
3. Pin the environment: dependency versions (lockfile, `environment.yml`,
   `requirements.txt` with pins, or container definition), and the exact
   code version (a tagged release or commit hash) referenced from the paper
   — "works with the current version of X" rots as soon as X updates.
4. Write the README to answer, in order: what this is, how to install it,
   how to reproduce the paper's key result with one command or a short
   documented sequence, and what's NOT included (excluded data, manual
   steps, compute requirements). Do not let installation instructions bury
   the reproduction command.
5. Attach a license (code and data may need different licenses) and, for
   collaboration papers, follow the collaboration's existing release policy
   rather than defaulting to one — ask rather than assume when no policy is
   supplied.
6. Before calling it release-ready, verify against a clean checkout: install
   from the documented steps and confirm the headline reproduction command
   runs as written — README claims that were never executed are exactly the
   failure mode `reproducibility-auditing.md` looks for in other people's
   artifacts.

Deliver the packaged repository structure (or a concrete plan for one),
README content, and the availability-statement text ready to hand to
`citations-and-bibliography.md`. Flag anything claimed as reproducible that
was not actually verified end-to-end.
