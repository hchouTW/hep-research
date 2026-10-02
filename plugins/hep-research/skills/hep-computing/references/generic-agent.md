# Generic Agent Adapter

Discovery notes only - the authoring rules live in `SKILL.md` and
`references/`, not here.

For any repository-aware agent not covered by a dedicated adapter (Cursor
Agents, GitHub Copilot Coding Agent, a custom LLM-based coding agent, or
anything else):

- Point the agent at `SKILL.md` directly and instruct it to read that file
  first, then follow its "When to Load References" routing into
  `templates/`, `references/`, and `examples/` as needed.
- If the environment has no automatic skill-discovery mechanism, provide the
  file path explicitly (e.g. as a system prompt attachment or an initial
  message) rather than relying on the agent to find it on its own.
- No agent-specific configuration is required beyond locating and reading
  `SKILL.md` - the workflow itself does not depend on any vendor-specific
  feature.
