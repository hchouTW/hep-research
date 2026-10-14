# Tool-contract scopes

Each file is a scope for `contracts/tool_contract.py --scope` (task P5.4): every listed `<tool_id>:<operation_id>` needs
a passing contract in `contracts/tool_contracts/` that declares the purpose. CI runs both. `fixed-execution` covers the
tool of every shipped recipe (`contracts/semantics/recipes/`) and the blinding and release-preparation tools a custodian
runs; `validation` adds the output audit. A scope states coverage; it authorizes nothing.
