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
- Paths to plugin files use `<plugin root>`; never rely on the current directory or a repository checkout.
- General mechanism: [Claude Code plugins](https://code.claude.com/docs/en/plugins) and
  [skills](https://code.claude.com/docs/en/skills).

## Codex CLI (tested on macOS)

- The plugin ships a Codex manifest, `.codex-plugin/plugin.json` (`"skills": "./skills/"`), and the repository root a
  Codex marketplace, `.agents/plugins/marketplace.json`, beside the Claude Code files. Both name the marketplace
  `hep-research-dev`.
- Install: `codex plugin marketplace add <path>` then `codex plugin add hep-research@hep-research-dev`. Remove with
  `codex plugin remove hep-research@hep-research-dev` and `codex plugin marketplace remove hep-research-dev`. Codex
  copies the whole plugin into `$CODEX_HOME/plugins/cache/<marketplace>/hep-research/<version>/`.
- Plugin skills are namespaced like in Claude Code (`hep-research:hep-computing`). Codex has no Skill tool: ask for a
  skill by name in the prompt, and the model reads its `SKILL.md`. Codex lists each skill with the path of its
  `SKILL.md`, which is how `<plugin root>` (two levels above it) resolves. Claude Code's plugin-root variable is not
  set in Codex, which is why skill text never uses it.
- Codex also reads standalone skills from `~/.agents/skills/`, whatever `CODEX_HOME` says; they do not clash by
  name with `hep-research:*`.
- `codex exec` waits for stdin unless stdin is closed (`< /dev/null`), which matters for scripts.
- Measured with Codex CLI 0.160.0 on macOS (VALIDATION.md, MULTIHOST). Not tested on Linux.

## Claude apps: Chat and Cowork (documented, not tested)

- From Anthropic's documentation (read 2026-10-04): **Customize > Plugins > Add > Add marketplace** with
  `hchouTW/hep-research`, or **Add > Upload plugin** with a `.zip` holding one `.claude-plugin/plugin.json`. The
  plugin is saved to the account and synced to Chat, Cowork and signed-in Claude Code. Steps are in the plugin
  README, "Install and remove".
- Chat cannot reach the user's computer: no project config, private profiles or local data, and scripts run only in
  the code-execution sandbox. Whether `<plugin root>` folders outside `skills/` are reachable there is not verified.
- Cowork works on a local folder, so project configuration should behave as in Claude Code (not verified).

## ChatGPT (documented, not tested)

- From OpenAI's documentation (read 2026-10-04): the plugin directory shared with Codex lists only published
  plugins; only workspace admins can import a GitHub marketplace, and whether that import reads
  `.agents/plugins/marketplace.json` is not verified.
- Fallback: upload each skill folder as a `.zip` under **Skills > Create > Upload from your computer**. The skills
  lose the `hep-research:` namespace and the shared plugin folders, so `<plugin root>` paths and scripts that import
  `core` fail; only the Markdown methods carry over.

## Other hosts (Antigravity, Cursor, Copilot, custom agents: not tested)

The plugin is built and tested for Claude Code and Codex CLI only. Installing it, or the task-authoring material inside
`hep-computing`, in another host is **not tested** in v1: no install path, discovery behavior or invocation syntax
is claimed here.

- What carries over without a host: the Markdown references and the standard-library scripts (run them with
  `python3 <script> --help`). Paths in the skill text use `<plugin root>`; another host must substitute
  the plugin's install directory.
- What does not: plugin manifests and namespaced skill invocation are written for Claude Code and Codex.
- An agent without skill discovery can be pointed at `SKILL.md` directly (as an attachment or an initial message)
  and told to read it first, then the references it routes to. The workflow itself depends on no vendor feature.
- If you need support for another host, record it as an adapter request; it stays `proposed` until it is executed
  in a declared environment.
