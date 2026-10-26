# Writing an adapter

An adapter connects the plugin to an external tool (pyhf, CMS Combine, ROOT, uproot, a generator, a recasting
framework). It is optional: no skill or core module may require one, and everything mandatory works without it.

## Layout

```
adapters/<name>/
  adapter.json   # declaration, checked by tests/adapters/test_adapter_declarations.py
  assets/        # templates and starting points
  tests/         # tests that run the tool (needed before any status above "proposed")
```

## adapter.json

| Field | Content |
|---|---|
| `id` | `adapter:<name>`, the name profiles use in `adapters.required` / `adapters.optional` |
| `version` | SemVer of the adapter |
| `status` | a capability state from `contracts/vocab/core.json` (`proposed`, `documented`, `demonstrated-on-synthetic-data`, `tested-in-declared-environment`, `unavailable`) |
| `purpose` | one sentence |
| `tools` | each tool with its own `status` and the versions it was actually run with (`tested_versions`, empty until run) |
| `environment` | where the tests ran (OS, Python, tool builds), or "none declared" |
| `assets`, `tests` | relative paths; every listed file must exist |
| `owner_skill` | the core skill that owns the method the adapter executes |
| `provider` | optional (contracts 3.14.0): one cr-provider/1 declaration or a list (schema `contracts/schemas/cr_provider.json#/$defs/declaration`): `id`, `entrypoint` (relative to the adapter folder), `protocol` `cr-provider/1`, `domain` (canonical parameter names, each `{min, max}`), optional `axis_ranges`, `observables`, `axes` (`rigidity`, `ekn`), `decomposable`, `deterministic`, `output_units`, optional `version` (default: the adapter's). A `profile.json` takes the same field. `tools/provider_registry.py` builds the registry from these fields; the declaration test checks them |

## Provider entrypoints (cr-provider/1)

A propagation provider (a closed form, an external code, an emulator) answers requests of the protocol
`cr-provider/1`: parameter points in the canonical parameter names, observables with bins on the `rigidity` (GV) or
`ekn` (GeV/n) axis, and `want` limited to `lis` and `components` (providers never modulate). The entrypoint is a
Python script that declares itself and calls `core.provider.entrypoint.provider_main(declaration, evaluate_point)`;
that gives it `--request R --response S`, `--serve` (JSON Lines) and `--allow-outside-validated-range`, and applies
the protocol's refusals (out-of-domain, unsupported-want, ...) before `evaluate_point` runs. Callers never search for
providers: they pass the registry written by `python3 tools/provider_registry.py --write "$CRPROP_OUT/registry.json"`
(not committed) to `core.provider.runner.ProviderRunner` or `python3 core/provider/runner.py --provider-registry`;
only listed entrypoints run, a cache under a caller-given folder is keyed by the point hash, and a crash is reported
as `failed` with the reason. The closed-form provider of the `cr-secondary-ratio` theory profile
(`scripts/provider.py`) is the worked example.

Conformance (PRV-1, PRV-2) is the same for every provider. An adapter's test module adds one class:

```python
from tests.core.provider_conformance import ProviderConformance

class UsineProviderConformance(ProviderConformance, unittest.TestCase):
    PROVIDER_ID = "usine"            # the id in the adapter.json provider field
    REQUEST = {...}                  # one small in-domain request at the registered provider_version
    def unavailable_reason(self):    # skip, with the reason, when the external code is not installed
        return None if os.environ.get("HEP_USINE_BIN") else "HEP_USINE_BIN unset"
```

It writes a fresh registry, runs `core/provider/conformance.py` (direct single-shot and `--serve` calls, the
unsupported-want, out-of-domain and outside-validated-range cases, the unregistered refusal and the runner) and
validates every response against the contract schema. The same checks run from the command line:
`python3 core/provider/conformance.py --provider-registry R --provider ID --request REQUEST.json` (exit 0 pass,
1 a check failed). A profile's tests may not import the plugin's `tests` package, so they call
`core.provider.conformance.run_conformance` and the schema directly (see that profile's `tests/test_provider.py`).

## Honesty rules

- A tool status above `documented` needs tests that run the tool, a declared environment, and tested versions; a
  tool not run lists no versions. The adapter status is the lowest of its tools' statuses. The declaration test
  fails otherwise.
- Never name a tool, version or feature as supported unless a test ran it. Untested names stay `proposed`.
- A missing tool at run time yields an artifact with status `failed` and the reason, never a silent fallback.
- Outputs pass through the plugin's contracts (`contracts/validate.py`), so the comparison gate and status labels
  apply to adapter results like any other.
- Keep the capability matrix row (`docs/capability-matrix.md`) in step with `adapter.json`; a test compares them.

## Changing an adapter

Bump its version, rerun its tests in the declared environment, record the run in `VALIDATION.md` (date, commit,
environment, command, result), and update the matrix. A tool upgrade that changes numbers beyond the declared
tolerance is a breaking change.

`adapters/pyhf-combine` is `demonstrated-on-synthetic-data`: its pyhf part with pyhf 0.7.6 and its Combine part with
Combine 11.1.0 (conda-forge, ROOT 6.40.04 and 6.36.14 builds), which the Combine test reaches through `HEP_COMBINE_WRAPPER`. `adapters/root-uproot` is `demonstrated-on-synthetic-data`
(ROOT 6.40.04, uproot 5.7.6, awkward 2.14.0); its ROOT tests find ROOT through `HEP_ROOT_PYTHON` or `HEP_ROOT_CONFIG`.

`adapters/batch-schedulers` is `demonstrated-on-synthetic-data`: HTCondor 24.12.16 (CERN) and Slurm 24.05.1 (NSTCCore)
each ran synthetic campaigns; the fake schedulers in `tests/adapters/batch_shims/` alone cannot raise a tool above
`documented`; real-tool tests are gated by `HEP_SLURM_TEST=1` / `HEP_HTCONDOR_TEST=1` plus `HEP_SLURM_CONFIG` /
`HEP_HTCONDOR_CONFIG` naming a user-reviewed configuration. `adapters/literature-lookup` (owned by hep-citations) opens
network connections: it states the hosts in `environment`, reaches them only when run live
(never under `--replay` or in its offline tests, which patch `urlopen` to fail), reads the ADS token from the
environment and never records it; its live smoke test runs only with `HEP_LIVE_LOOKUP_TEST=1`. `adapters/crdb` (owned by hep-theory, `tested-in-declared-environment` on CRDB V4.2) also opens network
connections, to `lpsc.in2p3.fr` and only in its `fetch` command; it has no default experiment filter (an experiment profile
passes its own), labels every row secondary and writes a provenance sidecar. CRDB is a secondary compilation: HEPData
records or the paper's tables are primary, and a CRDB value is a cross-check or a fallback labelled secondary. `adapters/cr-propagation` (owned by hep-computing) is `proposed` because GALPROP and USINE are; its DRAGON2 tool is `tested-in-declared-environment` (commit cd588707 built from source on E2): `dragon2_run.py` builds a run directory from a JSON spec without touching the DRAGON2 tree and records the run as a `computational-run`, and `dragon2_to_prediction.py` turns each run into one grid-node `prediction`; its offline tests replay recorded runs and the live rerun needs `HEP_DRAGON2_LIVE_TEST=1` with `HEP_DRAGON2_BIN` and `HEP_DRAGON2_DATA`. Python code in an adapter may import only `core` and `contracts`.
