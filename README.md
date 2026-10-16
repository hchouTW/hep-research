# hep-research

**hep-research** is a Claude Code and Codex plugin for experimental and theoretical high-energy physics research.
- **Seven core skills:** `hep-measurement`, `hep-detector`, `hep-theory`, `hep-statistics`, `hep-computing`, `hep-ml`
  and `hep-communication`.
- **Optional profiles** for experiments and theory domains.
- **An opt-in cross-artifact analysis check.** It runs in shadow mode and is advisory only.

Not endorsed by AMS or any collaboration or institution.

- Plugin: [`plugins/hep-research/`](plugins/hep-research/) (install, usage and checks in its [README](plugins/hep-research/README.md))
- Marketplace `hep-research-dev`: [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) (Claude Code),
  [`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json) (Codex)

```bash
claude plugin marketplace add hchouTW/hep-research
claude plugin install hep-research@hep-research-dev
```

This marketplace lists hep-research only. Companion plugins, such as the access-restricted `ams02-research` for AMS
Collaboration members, are not listed here; they come from their own sources and are installed and updated separately.
hep-research does not depend on any of them (see
[companion plugins](plugins/hep-research/docs/profile-authoring.md#companion-plugin)). A companion already installed
from this marketplace stays installed but no longer receives updates through it (see
[companion plugins](plugins/hep-research/README.md#companion-plugins)).

Checks: `python3 plugins/hep-research/tools/run_all_checks.py`

Design and decision records of the v6.3 analysis-check programme:
[`plugins/hep-research/docs/dev/v6.3/`](plugins/hep-research/docs/dev/v6.3/README.md).

Live routing evaluation (paid model calls, outside the plugin): [`evals/routing/`](evals/routing/README.md).

## Contributing

Commits are checked by `.githooks/` (path allowlist) and by the `guard` workflow (path allowlist over the whole
history plus a secret scan). After cloning, run `git config core.hooksPath .githooks` once.

## License

Apache License 2.0; see [LICENSE](LICENSE).
