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
| `tools` | each tool with the versions it was actually run with (`tested_versions`, empty until run) |
| `environment` | where the tests ran (OS, Python, tool builds), or "none declared" |
| `assets`, `tests` | relative paths; every listed file must exist |
| `owner_skill` | the core skill that owns the method the adapter executes |

## Honesty rules

- A status above `documented` needs tests that run the tool, a declared environment, and tested versions for every
  tool. The declaration test fails otherwise.
- Never name a tool, version or feature as supported unless a test ran it. Untested names stay `proposed`.
- A missing tool at run time yields an artifact with status `failed` and the reason, never a silent fallback.
- Outputs pass through the plugin's contracts (`contracts/validate.py`), so the comparison gate and status labels
  apply to adapter results like any other.
- Keep the capability matrix row (`docs/capability-matrix.md`) in step with `adapter.json`; a test compares them.

## Changing an adapter

Bump its version, rerun its tests in the declared environment, record the run in `VALIDATION.md` (date, commit,
environment, command, result), and update the matrix. A tool upgrade that changes numbers beyond the declared
tolerance is a breaking change.

The two shipped adapters, `adapters/pyhf-combine` and `adapters/root-uproot`, are `proposed`: their tools were not
installed in the v1 checks.
