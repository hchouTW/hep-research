# Claude Code Adapter

Discovery notes only - the authoring rules live in `SKILL.md` and
`references/`, not here.

- Install by copying the whole `task-authoring/` folder to
  `.claude/skills/task-authoring/` (project-scoped) or
  `~/.claude/skills/task-authoring/` (personal/global).
- Claude Code reads every installed skill's YAML frontmatter (`name`,
  `description`) at session start and loads the full `SKILL.md` when a
  request matches the `description`. It can also be invoked explicitly with
  `/task-authoring`.
- Relative links inside `SKILL.md` (`templates/...`, `references/...`,
  `examples/...`) resolve against the skill's own folder, so the folder must
  be copied as a whole, not split apart.
- See the official
  [Claude Code skill documentation](https://code.claude.com/docs/en/skills)
  for the general skill-discovery mechanism.
