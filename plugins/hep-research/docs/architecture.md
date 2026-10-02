# hep-research Architecture (M0 stub: verified host facts only)

Full architecture is written in M1. This file currently records Section 5.1 host facts.

## Verified Claude Code plugin facts (task Section 5.1)

Source for "verified locally": Claude Code CLI **2.1.287**, `claude plugin --help` and subcommand help, plus
`claude plugin validate --json` run on a throwaway probe plugin in a scratch directory, 2026-10-02.
Network documentation was read after G0 approval (sources below the table).

| # | Question | Status | Finding and source |
|---|---|---|---|
| 1 | Manifest location / required fields | `[Confirmed]` CLI | `.claude-plugin/plugin.json`. Only `name` is required (missing `name` = error; missing `version`, `description`, `author` = warnings); kebab-case. `--strict` turns warnings into errors, so we include `author`. |
| 2 | Skill discovery, description limit, always-loaded cost | `[Confirmed]` layout and cost model; limit not documented | One `skills/<name>/SKILL.md` per skill (docs: plugins/manifest-reference; CLI validator scans it). Always-on cost = each component's name + `description` + `when_to_use` (docs: skills, "The always-on figure counts each component's name plus its `description` and `when_to_use` frontmatter"). No maximum description length is documented, and a 1,100-character description raised no validator warning. **Budget decision:** measure with `claude plugin details` and keep each description under 1,024 characters `[Proposal]` (the common Agent Skills limit; not a verified Claude Code limit). |
| 3 | Namespacing | `[Confirmed]` docs | "Command name: `/<plugin>:<directory>`, so `skills/review/SKILL.md` in `my-plugin` is `/my-plugin:review`" (plugins/components). Plugin skills therefore appear as `hep-research:hep-analysis`, distinct from a personal `hep-analysis` skill. Live coexistence is still tested at G5. |
| 4 | Install cache, plugin root, base directory | `[Confirmed]` cache + variable; base directory not documented | Installed marketplace plugins live in `cache/<marketplace>/<plugin>/<version>/` and `${CLAUDE_PLUGIN_ROOT}` points there (plugins/loading). `${CLAUDE_PLUGIN_ROOT}` resolves inline in skill/command/agent content (plugins/manifest-reference, environment variables table). Whether the model is told a skill's base directory is not documented. **Consequence:** the whole plugin root is copied, so skills can read shared `core/`, `contracts/`, `profiles/` via `${CLAUDE_PLUGIN_ROOT}/...` paths in SKILL.md; the per-skill-copy fallback is not needed. Nothing outside the plugin root may be referenced. Scripts still resolve the root from `__file__` (works with or without the variable). |
| 5 | Local marketplace + install/remove | `[Confirmed]` CLI + docs | `.claude-plugin/marketplace.json` at the marketplace root; relative `source` resolves from the root, not from `.claude-plugin/` (plugins/marketplace-reference). Commands: `claude plugin marketplace add <path>`, `claude plugin install <plugin>@<marketplace> [-s user|project|local]`, `claude plugin uninstall <plugin> [--scope]`. Executed only at G5. |
| 6 | Non-interactive validator | `[Confirmed]` CLI | `claude plugin validate <path> [--json] [--strict]` on a plugin dir, marketplace root, or skills dir; exit 0/1. |
| 7 | Headless traces | `[Unresolved]` | `claude -p --output-format stream-json` exists; the docs do not say whether loaded skills are reported. Must be observed in a live run (paid; needs approval at M5). If skills are not visible, load traces come from tool-use events (Read of plugin files) in the stream. |
| 8 | Commands vs skills | `[Confirmed]` docs | "Commands are the older format, and skills supersede them for new work" (plugins/components). Frontmatter `disable-model-invocation: true` / `user-invocable: false` control invocation (skills). **Decision:** no `commands/` in v1 (D10). |

Docs read 2026-10-02 (network approved at G0): code.claude.com/docs/en/plugins/{manifest-reference,components,loading,marketplace-reference,cli-reference,plugin-evals}, code.claude.com/docs/en/skills. Quotes are from those pages as fetched that day.

## Additional host facts found

- `claude --plugin-dir <path>` loads a plugin from a directory or .zip for one session, without installing. `[Confirmed]` from help. This gives a low-risk first step for G5 (no change to the user's installed plugins).
- `claude plugin eval [target]` runs `evals/**/prompt.md + graders/*.md` cases against a plugin with a no-plugin baseline arm. `[Confirmed]` from help. This matches the existing `hep-analysis/evals/` layout and is a candidate mechanism for the M5 live routing check (paid; needs approval).
- `claude plugin tag` creates `{name}--v{version}` git tags after checking plugin.json and marketplace agree. Relevant to versioning (7.13), not used in v1.
