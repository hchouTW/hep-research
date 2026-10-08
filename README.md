# hep-research

**hep-research** is a Claude Code and Codex plugin for experimental and theoretical high-energy physics research:
seven core skills (analysis, detector response, theory, statistics, computing, physics ML, research communication)
plus optional experiment and theory-domain profiles. Not endorsed by AMS or any collaboration or institution.

- Plugin: [`plugins/hep-research/`](plugins/hep-research/) (install, usage and checks in its [README](plugins/hep-research/README.md))
- Marketplace `hep-research-dev`: [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) (Claude Code),
  [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json) (Codex)

```bash
claude plugin marketplace add hchouTW/hep-research
claude plugin install hep-research@hep-research-dev
```

Both marketplace manifests (Claude Code's and Codex's) also list `ams02-research`, an access-restricted companion
plugin for AMS Collaboration members. It lives in a separate private repository; without access its install fails and nothing else is affected.
hep-research does not depend on it: install and update each plugin separately. The companion checks its own
compatibility with the installed hep-research when its profile is used (see
[companion plugins](plugins/hep-research/docs/profile-authoring.md#companion-plugin)).

Checks: `python3 plugins/hep-research/tools/run_all_checks.py`

Live routing evaluation (paid model calls, outside the plugin): [`evals/routing/`](evals/routing/README.md).

## Contributing

Commits are checked by `.githooks/` (path allowlist) and by the `guard` workflow (path allowlist over the whole
history plus a secret scan). After cloning, run `git config core.hooksPath .githooks` once.

## License

Apache License 2.0; see [LICENSE](LICENSE).
