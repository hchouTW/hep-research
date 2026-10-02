# Codex host notes

The `hep-research` plugin is built and tested for Claude Code only. Installing it, or the task-authoring material
inside `hep-computing`, in Codex is **not tested** in v1: no install path, discovery behavior or invocation syntax
is claimed here.

- What carries over without a host: the Markdown references and the standard-library scripts (run them with
  `python3 <script> --help`). Paths in the skill text use `${CLAUDE_PLUGIN_ROOT}`; another host must substitute
  the plugin's install directory.
- What does not: plugin manifests, namespaced skill invocation, and the generated context stanza assume Claude Code.
- If you need Codex support, record it as an adapter request; it stays `proposed` until it is executed in a
  declared environment.
