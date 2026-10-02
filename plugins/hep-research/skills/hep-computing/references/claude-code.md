# Claude Code host notes

Discovery and install notes only. The task-authoring rules live in `task-authoring-guide.md` and the other
references of this skill.

- The task-authoring material ships inside the `hep-research` plugin (skill `hep-computing`). It is not a separate
  skill folder any more, so it is not copied into `~/.claude/skills/`.
- Install the plugin from its marketplace, for example the development marketplace at the repository root:
  `claude plugin marketplace add <path-or-repo>` then `claude plugin install hep-research@hep-research-dev`
  (`--scope user|project|local`). Remove with `claude plugin uninstall hep-research@hep-research-dev` and
  `claude plugin marketplace remove hep-research-dev`. These commands were read from Claude Code 2.1.287 help;
  the native install test (gate G5) records the host and version where they were actually run.
- Claude Code reads each skill's `name` and `description` at session start and loads the full `SKILL.md` when a
  request matches. Plugin skills are namespaced, for example `/hep-research:hep-computing`.
- Paths to plugin files use `${CLAUDE_PLUGIN_ROOT}`; never rely on the current directory or a repository checkout.
- General mechanism: [Claude Code plugins](https://code.claude.com/docs/en/plugins) and
  [skills](https://code.claude.com/docs/en/skills).
