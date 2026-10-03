# I05 discovery and namespaced invocation (E2, real ~/.claude)

Command (from an empty scratch project directory, nested-session variables unset):

    claude -p "/hep-research:hep-theory Using the theory:qed-benchmark profile, list the conventions it fixes for e+e- -> mu+mu- and name the profile files you read." \
      --output-format stream-json --verbose --max-turns 8 \
      --allowedTools Read Glob Grep Skill --disallowedTools Bash Write Edit NotebookEdit WebFetch WebSearch Agent

Trace: `I05-invoke-hep-theory.jsonl`. Model claude-opus-5-5 (host default). Result success, 5 turns, $0.216.

| Check | Result | Evidence |
|---|---|---|
| Discovery | pass | init lists 59 skills, including the seven `hep-research:*` |
| Plugin path | pass | init `plugins[]`: `hep-research` at `~/.claude/plugins/cache/hep-research-dev/hep-research/0.1.0` (Git source, cached copy, not the working tree) |
| Name clash | pass | no other skill shares a short name with a `hep-research` skill (the only duplicate short name, `skill-creator`, predates this install) |
| Namespaced invocation | pass | `/hep-research:hep-theory` loaded; answer gives the profile's conventions table |
| Profile access from install | pass | Read `profiles/registry.json`, `profiles/theory/qed-benchmark/index.md`, `conventions.json` under the cache path |

Observation (not a failure): the answer flags that `qed-benchmark/conventions.json` has no `scales` entry, which the
`hep-theory` conventions block asks for.
