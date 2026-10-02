# Codex Adapter

Discovery notes only - the authoring rules live in `SKILL.md` and
`references/`, not here.

- Install by copying the whole `task-authoring/` folder to the skill
  directory used by your Codex environment, commonly `~/.codex/skills/`, or
  import it through whichever mechanism your Codex version supports.
- Reload skills and invoke with `$task-authoring`.
- `agents/openai.yaml` supplies optional Codex UI metadata (`display_name`,
  `short_description`, `default_prompt`) - it is a thin descriptor, not a copy
  of the workflow itself.
- As with any skill folder, keep `SKILL.md`, `templates/`, `references/`, and
  `examples/` together - Codex resolves the relative links between them from
  the folder's own root.
