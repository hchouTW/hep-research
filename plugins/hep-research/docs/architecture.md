# hep-research Architecture (M0 stub: verified host facts only)

Full architecture is written in M1. This file currently records Section 5.1 host facts.

## Verified Claude Code plugin facts (task Section 5.1)

Source for "verified locally": Claude Code CLI **2.1.287**, `claude plugin --help` and subcommand help, plus
`claude plugin validate --json` run on a throwaway probe plugin in a scratch directory, 2026-10-02.
No network documentation was read (needs user approval).

| # | Question | Status | Finding |
|---|---|---|---|
| 1 | Manifest location / required fields | `[Confirmed]` locally | `.claude-plugin/plugin.json`. Only `name` is required (missing `name` = error; missing `version`, `description`, `author` = warnings). `name` must be kebab-case (no spaces). `--strict` turns warnings into errors, so we will include `author`. |
| 2 | Skill discovery, description limit, always-loaded cost | Partial | `skills/<name>/SKILL.md` is scanned by the validator; missing frontmatter is a warning. A skill without a frontmatter `name` raised nothing. A 1,100-character description raised no warning, so the validator does not reveal a limit. `claude plugin details <name>` reports "projected token cost" for installed plugins (useful for AC04). Description limit and context-loading behavior: `[To verify]` from docs. |
| 3 | Namespacing `hep-research:<skill>` | `[To verify]` | Not observable without docs or an install + model run. |
| 4 | Install cache, base directory, `${CLAUDE_PLUGIN_ROOT}` | `[To verify]` | Not observable offline. Design keeps the `core/bootstrap.py` approach (resolve root from `__file__`), which works either way. |
| 5 | Local marketplace + install/remove | `[Confirmed]` format; commands from help | `.claude-plugin/marketplace.json` with `name`, `owner`, `plugins[{name, source: "./plugins/<p>"}]` validates. Commands: `claude plugin marketplace add <path>`, `claude plugin install <plugin>@<marketplace> [-s user|project|local]`, `claude plugin uninstall <plugin>`. Not executed (G5). |
| 6 | Non-interactive validator | `[Confirmed]` | `claude plugin validate <path> [--json] [--strict]`, works on a plugin dir, a marketplace root, or a skills dir. Exit 0 on success, 1 on failure. |
| 7 | Headless traces | Partial | `claude -p --output-format stream-json` exists. Whether it exposes loaded skills/files is unverified (requires a paid model call). |
| 8 | Commands vs skills | `[To verify]` | Help text says "Skills still resolve via /skill-name" and `--disable-slash-commands` "Disable all skills", which suggests `[Inferred]` that slash commands and user-invocable skills are merged. Needs docs. |

## Additional host facts found

- `claude --plugin-dir <path>` loads a plugin from a directory or .zip for one session, without installing. `[Confirmed]` from help. This gives a low-risk first step for G5 (no change to the user's installed plugins).
- `claude plugin eval [target]` runs `evals/**/prompt.md + graders/*.md` cases against a plugin with a no-plugin baseline arm. `[Confirmed]` from help. This matches the existing `hep-analysis/evals/` layout and is a candidate mechanism for the M5 live routing check (paid; needs approval).
- `claude plugin tag` creates `{name}--v{version}` git tags after checking plugin.json and marketplace agree. Relevant to versioning (7.13), not used in v1.
