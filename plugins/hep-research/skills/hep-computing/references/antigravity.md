# Antigravity Adapter

Discovery notes only - the authoring rules live in `SKILL.md` and
`references/`, not here.

- Install by copying the whole `task-authoring/` folder to
  `.agents/skills/task-authoring/` in the workspace, or
  `~/.gemini/config/skills/task-authoring/` for a global install (older
  installs may still read `.agent/skills/`).
- Antigravity reads every installed skill's `name`/`description` frontmatter
  at session start and loads the full `SKILL.md` automatically when a task
  matches - no explicit invocation command is needed.
- See the
  [Antigravity skills documentation](https://antigravity.google/docs/skills)
  for the general skill-discovery mechanism.
