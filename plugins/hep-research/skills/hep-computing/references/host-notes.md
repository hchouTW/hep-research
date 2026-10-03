# Host notes

Discovery and install notes only. The task-authoring rules live in
[task-authoring-guide.md](task-authoring-guide.md) and the other references of this skill.

## Claude Code (tested)

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

## Other hosts (Codex, Antigravity, Cursor, Copilot, custom agents: not tested)

The plugin is built and tested for Claude Code only. Installing it, or the task-authoring material inside
`hep-computing`, in another host is **not tested** in v1: no install path, discovery behavior or invocation syntax
is claimed here.

- What carries over without a host: the Markdown references and the standard-library scripts (run them with
  `python3 <script> --help`). Paths in the skill text use `${CLAUDE_PLUGIN_ROOT}`; another host must substitute
  the plugin's install directory.
- What does not: plugin manifests, namespaced skill invocation, and the generated context stanza assume Claude Code.
- An agent without skill discovery can be pointed at `SKILL.md` directly (as an attachment or an initial message)
  and told to read it first, then the references it routes to. The workflow itself depends on no vendor feature.
- If you need support for another host, record it as an adapter request; it stays `proposed` until it is executed
  in a declared environment.
