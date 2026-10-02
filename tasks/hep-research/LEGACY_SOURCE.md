# Legacy source (read-only)

The seven legacy skills are **not** in this repository. They are read from
<https://github.com/hchouTW/agentic-ai-skills> at commit `3e995a49a89fad8e0e9d52130ee1fd93a3a0f4f9`.
Per the user's instruction (2026-10-02), nothing is ever written to agentic-ai-skills again.

Fetch a local, gitignored, read-only copy:

```bash
tasks/hep-research/scripts/fetch_legacy.sh        # -> .legacy/agentic-ai-skills at the pinned commit
```

Dev scripts read `$LEGACY_REPO` (default `.legacy/agentic-ai-skills`). Every migrated file records
`source_path` + `source_commit` in `plugins/hep-research/docs/migration-map.csv`.

The M0/M1 history was first committed on `feat/hep-research-plugin` in agentic-ai-skills and moved
here with legacy files filtered out; that old branch is left as is and is no longer updated.
