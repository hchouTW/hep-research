# core/naming

The engine of the semantic naming charter (`skills/hep-computing/references/semantic-naming.md`): every naming surface
shares this data model, these predicates and this engine; a surface brings only its extractor
(`skills/<owner>/scripts/extract_names.py`) and its rule data (`contracts/naming/`). The report shape, the severities
and the command line are in `contracts/naming_check.py`. Standard library only; imports only `core`.

| File | What |
|---|---|
| `model.py` | `NamedEntity` and inventory constructors, entity ids, the shared enums (states, levels, actions) |
| `tokens.py` | the tokenizer: prefixes, protected words longest first, separator, case and digit splits |
| `vocab.py` | the vocabulary chain (glossary, profile, defaults, English word shape) and the forbidden table |
| `predicates.py` | the ten predicates; each returns a reason code the rule's outcome contract maps to a state |
| `engine.py` | references status, contract levels, judgement over the whole inventory, reporting scope, disposition, change-set validation |
| `data/` | `forbidden.json`, `hep-abbreviations.json`, `symbols.json`, `framework-names.json` (no experiment names) |
