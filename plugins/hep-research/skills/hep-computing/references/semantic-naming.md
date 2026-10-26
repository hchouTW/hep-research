# Semantic naming: charter, engine and procedure

Read this page before adding, changing or deleting any name a skill produces: code identifiers, files, ROOT objects,
columns, configuration keys and flags, jobs, samples, selections, variations, nuisances and channels, calibration tags,
models and features, theory parameters, figure and LaTeX labels, BibTeX keys, plugin vocabulary and literature record
IDs. Every surface uses one data model, one rule format, one engine, one disposition rule, one procedure and one report;
a surface supplies only its extractor and its rule data. The surface owners keep a short section each (index at the end).

Tools: `<plugin root>/contracts/naming_check.py` (`check`, `annotate-template`, `validate`, `validate-change-set`,
`surfaces`) and the extractors `skills/<owner>/scripts/extract_names.py`. Registries: `contracts/naming/surfaces.json`
and `contracts/naming/rules.json` (checked by `contracts/naming_registry.py check`). Engine: `core/naming/`.

## 1. Precedence

A higher layer always wins:

1. **No-rename restrictions.** A C4 name (decided outside the project) is never renamed, even with the user's approval:
   propose an alias or a mapping layer, and name the external owner if the outside name itself must change. A surface
   with rename policy `never` is never renamed; `dedup-only` renames only to remove a duplicate; `deprecate` renames
   only by adding the new name and keeping the old one as a deprecated alias for at least one minor version.
2. **The disposition matrix** (section 6).
3. **Request scope.** A fix outside the current request becomes a proposal.
4. **Severity settings** (`naming.strict`, waivers, known gaps) change only the severity and the exit code, never
   whether a name may change.

Tools never infer scientific intent: whether two names should be one is read from a declaration (for example the
correlation inventory of hep-measurement), never from their spelling. Similar names give `unverified`, never a finding
that they must merge. No evidence means no pass: unsearched references, a review below high confidence, a missing
extractor or zero scanned inputs give `unverified` or `unsupported`, and the check does not exit 0.

## 2. Shared principles

| # | Principle | Example |
|---|---|---|
| P1 | Name the physics or analysis meaning, not the container role | `dimuon_mass_sr`, not `hist1` |
| P2 | Use the project's terms: the glossary first, then the bound profile; never load an unrelated profile to name something | glossary term `acceptance` |
| P3 | The name matches the content or behaviour; review it again when they change | a function that only applies cuts: `apply_selection_cuts` |
| P4 | Quantities with units carry the unit; a name never hides a status label | `rigidity_gv`, `livetime_s`; a `synthetic` product is not `final_*` |
| P5 | Only standard abbreviations, those the vocabulary chain resolves | `pt`, `eta`, `chi2`, `p4` |
| P6 | Follow the surface's conventions and the external tools' requirements | `data_obs`; `<process>_<nuisance>Up` |
| P7 | Clarity over brevity; short names are fine when local and conventional | `i`, `mu`, `sigma`, `E_l` |
| P8 | A name others depend on is handled by its contract level | nuisance names are C3 |

Forbidden as whole names: `data`, `temp`, `tmp`, `obj`, `stuff`, `thing`, `foo`, `bar`, `test1`, `new`, `final`,
`final2`, `manager`, `helper`, `handler`, `process_data`, `do_something`, `plugin1`, `output.root`, `plot.pdf`. A name
made only of generic words (`tmp_data`) is forbidden too; generic words next to domain words are not
(`mass_dimuon_sr_data`). The table is `core/naming/data/forbidden.json`; a glossary never overrides it, only an explicit
waiver does.

## 3. The named entity

An extractor writes `naming_inventory.json` (schema `contracts/schemas/naming_inventory.json`) with every name of its
surface inside the scanned folders, plus the names removed in this change; `--changed REV` marks names `added`,
`modified` (same name, other content) or `removed` and never shrinks the inventory. Each entity has an `entity_id`
`<surface>:<path>#<container>/<name>@<line>` (two declarations of one name in one container differ), its kind, scope,
`source` (`project`, or `external` for anything an outside tool, dataset record or API fixes), meaning
(`concept_id`, `unit`, `status_label`), references with the ranges searched (`search_coverage`), change and content
digest. The engine, never the extractor, adds the tokens, `references_status` (`complete`, `partial`,
`not_searched`), the contract level and its basis.

## 4. Contract levels

| Level | Meaning | Disposition of a violation |
|---|---|---|
| C0 local | used only inside its scope | fix |
| C1 internal | referenced only in its own file | fix |
| C2 referenced | other project files use it by name | fix with a complete change set |
| C3 semantic | carries model or analysis meaning, or is a public interface of the plugin | propose; after the user's approval, change set and handoff to the owner |
| C4 external | decided outside the project | never rename; propose an alias or a mapping layer |

The level is the highest of: the kind's floor in the surface registry; C4 for an external source; the evidence (all
references in scope C0, all in the same file C1, other files C2, and C2 whenever the references are not completely
searched); C3 when a declaration lists the name as analysis-bearing.

## 5. Rules, tokenizer, vocabulary, waivers

A rule (`contracts/naming/rules.json`, keyed by `rule_id` and version) uses one of ten predicates and maps each reason
code to one of the five states `satisfied`, `violated`, `not_applicable`, `unverified`, `unsupported`:

| Predicate | Judges | Kind |
|---|---|---|
| `forbidden` | the forbidden table, whole names and generic-only names | deterministic |
| `pattern` | the kind's format, or a pattern a name must not match (a version in a file name) | deterministic |
| `vocabulary` | every token resolves in the vocabulary chain | deterministic |
| `uniqueness` | no second declaration of one kind in the same container; or one record (a DOI) under two names | deterministic |
| `pairing` | paired names exist (`Up` with `Down`), also the histograms a nuisance derives on N3 | deterministic |
| `reference` | no reference to a removed name; every target (a `\ref`'s label, an included file) exists | deterministic |
| `declared-match` | names agree with a declaration: the correlation inventory (same source, same name; different sources, different names) or the glossary's `identifiers` | deterministic |
| `status-honesty` | a `synthetic`, `asimov` or `preliminary` product is not named `final`, `observed` or `approved` | deterministic |
| `similarity` | near-duplicates (`lumi2018`, `lumi_2018`): a question, never `violated` | heuristic |
| `semantic` | the annotation's verdict, only at high confidence | review |

Code that changes needs a new rule version: the registry records the source digest of each predicate.

**Names across surfaces.** An entity may list `targets`: names it refers to on its own or another surface (a label
reference targets its label, an included figure its N2 file, a process its nominal template). A target that no
supplied inventory holds is `violated`; one on a surface whose inventory was not supplied is `unverified`. A
`derived` target is built from the entity's own name: Combine reads a shape nuisance `jes` as
`<process>_jesUp`/`Down` through the datacard's shapes lines, so the N10 extractor lists those N3 histograms, the
pairing rule needs the N3 inventory, and a change set that renames `jes` must rename them too. The engine adds each
resolved target to the target's references, so its level and change sets see the referrer.

**Declarations.** The correlation inventory is passed to `check --declaration`: either the explicit form
`{"declaration": "correlation-inventory", "sources": [{"id", "correlated", "members"}]}` (a member is an entity id,
`<container>/<name>` or a bare name) or the measurement-spec itself, whose systematics ledger already holds it: one
source per `correlation_key` (else per name), members its `nuisance_names` (else its name), uncorrelated when
`era_correlation` is `uncorrelated`; `partial` entries are left out until their decomposition is written as members.
A glossary entry's `identifiers` declare how one concept is spelled in names: `naming.cross.glossary-identifier`
finds every other spelling of that concept on every surface (`muon_transverse_momentum` where the glossary says `pt`).

**Tokenizer.** Strip prefixes (`ns:`, `fig:`/`eq:`/`tab:`/`sec:`, ROOT `k` and `h_`, flag dashes, underscores), match
protected words longest first (framework names, HEP abbreviations and units, fixed names, glossary identifiers), then
split at separators, case and letter-digit boundaries: `kElectronMassGeV` gives `electron`, `mass`, `GeV`.

**Vocabulary chain**, first match wins: the project glossary (preferred terms, aliases, abbreviations, `identifiers`);
the bound profile's namespace vocabulary (experiment abbreviations live only there); the defaults in
`core/naming/data/`; English, approximated by word shape (three or more letters with a vowel), so a short or
vowel-less token must be listed. Shadowing between layers is noted in the report.

**Waivers** sit in the optional `naming` block of `hep-research.project.json` (schema 1.3.0): `{rule_id, entity_ids,
reason, recorded_by}` with explicit ids (the `@line` may be left out when the name is declared once), no patterns, for
waivable rules only: style rules, never a correctness rule (declared-match, reference, pairing, uniqueness,
status-honesty), whose violations stay errors. A waived result is `not_applicable` with `naming.waived`.

## 6. Disposition and severity

| State | Action |
|---|---|
| `violated` | by level and policy (section 4 and section 1) |
| `unverified` | gather the missing evidence and judge again; if impossible, report it and do not claim completion |
| `unsupported` | report what is missing: extractor, inventory, declaration, tool or input |
| `satisfied`, `not_applicable` | nothing |

| Rule class | User project | Plugin gate |
|---|---|---|
| Correctness violated (`declared-match`, `reference`, `pairing`, `uniqueness`, `status-honesty`) | error | error |
| Style violated (`forbidden`, `pattern`, `vocabulary`) | warning; error with `strict` | error |
| Semantic violated | warning; error with `strict` | not run |
| Any `unverified` or `unsupported` | unresolved (incomplete, exit 3) | failure |

Status and exit code follow the audit report: input error (2) over any error (fail, 1) over any unresolved
(incomplete, 3) over pass (0). By default the report covers the names added, modified or removed and the names whose
relational judgement involves them (a removed name still referenced from an unchanged file); `--all` covers every
name.

## 7. The procedure

Every step's files live in `<project>/naming/`, never in `artifacts_dir` (they are working files, not artifacts).

1. **Inventory.** Run the extractor of each surface involved with `--root` at the project root (narrow with
   `--scope`; a subfolder root is refused) and `--changed` (alone: the merge base of `HEAD` and the main branch).
   A revision that already holds commits of this branch would show their names unchanged: the check then reports
   every name and cannot pass without their review. Pass `--expect N<k>` for each surface to the check, so an
   inventory left out is `unsupported`, not silent. A surface whose
   inputs cannot be read (N3 and N4 without uproot or PyROOT) or that scans zero inputs is `unsupported`; continue
   with the others.
2. **Classify** and 3. **resolve the vocabulary**: done by the engine.
4. **Judge**: `naming_check.py check --inventory ... [--glossary] [--declaration] [--project DIR]`.
5. **Review semantics** of added and modified names: read the implementation or content, its side effects and every
   referrer; write the annotations (`annotate-template` gives the entries). Referrers not readable: at most `medium`.
6. **Judge again** with `--annotations`.
7. **Decide** each finding's action (section 6); build a change set for C2 and C3.
8. **Validate and apply**: `validate-change-set`; C3 only after the user's approval, then hand back to the owner, who
   records the handoff in its own artifact in `artifacts_dir` (for example a note in a `computational-run` citing the
   change set's sha256).
9. **Run steps 1 to 6 again** and attach the report table to the reply.

**Confidence.** `high`: the implementation was read, references are complete and every referrer was read and listed;
`medium`: read, references not complete; `low`: guessed from the name, never described as verified.

## 8. The naming table and the change set

Attach to every reply that adds, changes or deletes a name (`naming_check.py check --format table`):

| Surface | Level | Rule | Predicate | State | Current | Proposed | Issue | Evidence | Confidence | Action |
|---|---|---|---|---|---|---|---|---|---|---|

When no name was added, changed or deleted, write the single line "No names added, changed or deleted." The table
names the revision compared against; without change marks an unchanged name may be new, so the line is never written
for an inventory made without `--changed`.

A change set (`naming_change_set.json`) holds the entity, the current and proposed names, the level and policy, every
replacement `{location, old, new}`, the digests of the inventories and of every affected file, the checks to run after
applying it, and for C3 the approval `{required, by, at, proposed}` (for the name proposed, not another) and the handoff
`{owner, rerun}` to the surface's owner; for `deprecate`, the alias kept and the version that removes it; on a
`dedup-only` surface the `trigger` names the uniqueness finding. `validate-change-set` stops at the first failing check:
renaming allowed, with the level recomputed from the inventory and the new name judged (not forbidden, in the kind's
format, not already another entity's name: on N10 anywhere, since one name is one parameter; on N15 the duplicate's
name) (exit 1),
references complete (exit 3), inventories of every referring surface and of every surface holding a derived name
supplied (exit 3), files unchanged since the inventory (exit 3), every reference and every derived name replaced
(exit 1), approval or alias recorded (exit 1). A reference from another surface is matched by that entity's id or its
`file:line`.

## 9. Surface index

`naming_check.py surfaces` lists owners, kinds and extractors (every surface has one). Owner sections (anchor
`naming-n<k>`):

| ID | Surface | Owner | Policy | Section |
|---|---|---|---|---|
| N1 | Code identifiers | hep-computing | matrix; `deprecate` for the plugin's core API | [python design](python-balanced-design-guidelines.md#naming-n1) |
| N2 | Files and directories | hep-computing | matrix | [pipelines](analysis-data-pipelines.md#naming-n2) |
| N3 | Objects inside ROOT files | hep-computing | matrix | [ROOT usage](root-usage-patterns.md#naming-n3) |
| N4 | Branches and columns | hep-computing | matrix | [Python HEP](python-hep-coding-patterns.md#naming-n4) |
| N5 | Configuration keys, environment variables, CLI flags | hep-computing | matrix; `deprecate` for plugin flags | [environments](environments-and-containers.md#naming-n5) |
| N6 | Batch jobs, workflow rules, chunks | hep-computing | matrix | [batch scheduling](batch-scheduling.md#naming-n6) |
| N7 | Samples, datasets, run ranges | hep-measurement | matrix | [analysis design](../../hep-measurement/references/analysis-design.md#naming-n7) |
| N8 | Selections, cutflows, regions | hep-measurement | matrix | [analysis design](../../hep-measurement/references/analysis-design.md#naming-n8) |
| N9 | Systematic variations | hep-measurement | matrix | [systematics](../../hep-measurement/references/systematics.md#naming-n9) |
| N10 | Nuisances, POIs, channels, processes | hep-statistics | matrix | [nuisance modeling](../../hep-statistics/references/nuisance-modeling.md#naming-n10) |
| N11 | Calibrations, conditions tags, efficiency maps | hep-detector | matrix | [calibration](../../hep-detector/references/calibration-and-alignment.md#naming-n11) |
| N12 | Models, checkpoints, features | hep-ml | matrix | [reproducibility](../../hep-ml/references/reproducibility.md#naming-n12) |
| N13 | Theory parameters, scheme labels | hep-theory | matrix | [schemes](../../hep-theory/references/regularization-and-schemes.md#naming-n13) |
| N14 | Figure and table files, LaTeX labels, macros | hep-authoring | matrix | [LaTeX](../../hep-authoring/references/latex-mechanics-and-tooling.md#naming-n14) |
| N15 | BibTeX keys | hep-authoring | `dedup-only` | [bibliography](../../hep-authoring/references/citations-and-bibliography.md#naming-n15) |
| N16 | Plugin contract vocabulary | hep-computing | `deprecate` | [engineering playbook](engineering-playbook.md#naming-n16) |
| N17 | Literature record IDs | hep-citations | `never` | [citation verification](../../hep-citations/references/citation-verification.md#naming-n17) |

The plugin checks its own names with `tools/check_naming.py` (N1, N5, N16; deterministic rules only; the names that
predate the gate are listed in `tools/naming_known_gaps.json`, which only shrinks: an entry that grew since
`origin/main` for a rule that existed there fails, and unverified or unsupported results are never listed).
