# M2 skill redistribution: worker brief

You move legacy skill content into the plugin's seven core skills. This is a **move**: content stays
verbatim except the edits listed under "Allowed edits". Scientific or wording improvements are out of
scope (they come later as separate commits).

## Paths

- Repo: `/home/claude/hep-research-plugin`. Plugin root `P = plugins/hep-research`.
- Legacy source (read-only, never modify): `.legacy/agentic-ai-skills/` (pinned agentic-ai-skills@3e995a4).
- Placement table: `tasks/hep-research/m2/redistribution/plan.csv` (`destination` is relative to `P`).
  Use it for **where each file goes** and for **rewriting links** to files owned by other workers.
- Python: `/home/claude/hep-research-plugin/.venv-hep/bin/python` (numpy, scipy, matplotlib, sympy).
  ROOT, torch, pyhf, uproot, awkward are not installed: tests needing them must skip exactly as in legacy.

## Hard rules

- Write only under the destinations of your legacy skills in plan.csv, `P/tests/skills/<skill_underscore>/`
  (packages already exist with `__init__.py`), and your record file `tasks/hep-research/m2/redistribution/<legacy-skill>.csv`.
- Never edit: any `SKILL.md` under `P/skills/`, `P/core`, `P/contracts`, `P/profiles`, `P/tools`, `P/docs`,
  `tasks/hep-research/*.md`, plan.csv, `.legacy/`, `~/.claude/`. Do not run git commands that change state
  (no add/commit/checkout/stash). No network access. No installs.
- If a destination file already exists, do not overwrite it: stop and report the collision.
- Never fabricate data, values or results. Do not invent test outcomes: report what ran.
- English only.

## Allowed edits (each must be listed in your record's note column)

1. **Legacy SKILL.md** → `skills/<skill>/references/<legacy-skill>-guide.md`: drop the YAML frontmatter; first
   heading `# <Legacy title> (guide)`; add a short `## When to read this file` saying it is the migrated
   routing/rules of the legacy `<legacy-skill>` skill. Replace "this skill" with "this guide" only where needed for sense.
2. **Links and paths** in moved text (markdown links, backticked paths, script usage lines, docstrings):
   - a link to another legacy file → the relative path from the new location to that file's plan.csv destination;
   - `scripts/x.py` → `${CLAUDE_PLUGIN_ROOT}/<destination of x>` in prose; in Python, compute paths from
     `__file__` (no reliance on cwd);
   - a link to something not shipped (VALIDATION.md, TODO.md, README.md of a legacy skill, tests, evals,
     agents/) → plain text "legacy <path> at agentic-ai-skills@3e995a4" (no link);
   - ams-analysis script paths moved to core: `ams_kinematics.py`→`core/kinematics/relativistic.py`;
     `validate_response|validate_covariance|poisson_diagnostics|unfolding_diagnostics|template_fit|statistical_toys|likelihood_limits.py`→`core/stats/<same>.py`;
     `validate_evidence_ledger.py`→`core/evidence/ledger.py`; `render_source_index.py`→`core/evidence/render_index.py`;
     ams-analysis references → `profiles/experiments/ams-02/modules/...` (see that folder).
3. **Scripts**: keep code identical. Only change sibling-import bootstrapping and paths that pointed into the
   legacy skill folder (e.g. `ROOT / "assets"`), so the script runs from its new folder with any cwd.
   A script may import only its own skill's sibling scripts, `core`, `contracts` (the layering check enforces this).
4. **Tests**: classify every legacy test file:
   - unit/behavior tests of scripts or shipped assets → **port** to `P/tests/skills/<skill_underscore>/test_<legacy_skill_underscore>_<rest>.py`
     (legacy `test_<rest>.py`). Fix only imports/paths. Keep seeds, tolerances and assertions. Run them with
     `cd P && <venv python> -m unittest discover -s tests -t .` (or the single module) and report run/pass/fail/skip.
     A failing ported test is reported, not edited to pass (unless the failure is only a path).
   - test parts that check the legacy bundle itself (SKILL.md wording/size, references listing, bundle validator) →
     **retire** (reason: the bundle no longer exists; plugin checks replace it). If a test file mixes the two, port the
     script parts and list the retired test names in the note.
   - model-evaluation material (`prompts*.md`, `*_eval.py`, `run_prompts.py`, `trigger_queries*.json`, eval-only fixtures) →
     **retain-outside** (not shipped; grading material). Note `trigger_queries*.json` as "input for M5 routing cases".
   - test fixtures used by ported tests → `P/tests/skills/<skill_underscore>/fixtures/<legacy-skill>/...`.

## Record file

`tasks/hep-research/m2/redistribution/<legacy-skill>.csv` with header
`source_path,destination,disposition,note` and one row per legacy file of your skills (including tests,
retired and retained ones). `disposition` ∈ move, move+path-edit, port, retire, retain-outside, deferred.

## Experiment names

Leave experiment names in moved text as they are (a later mechanical step marks them as examples).
Report the files that contain them.

## Final report (your last message)

Counts by disposition; test results (run/pass/fail/skip, with skip reasons); collisions; files with experiment
names; any link you could not resolve; anything that looked scientifically wrong (report only, do not fix).
