# v6.3 M0 — loading budget and evidence query (D02)

Status: measurement record for work package D02 of the v6.3 analysis-check programme (Phase M0). Measured
2026-10-16 on branch `v63/d02-evidence-query` (base `main` 982af52, plugin 0.11.0), Python 3.13.2, macOS.
Labels: **Confirmed** (measured or checked here), **Inferred** (a conclusion from measured numbers), **Unresolved**.

## Method

One method for every number, inside this checkout only (no companion profile, nothing outside the plugin root):

- **Bytes** are file sizes in bytes (`wc -c`, or `stat` through `tools/measure_entrypoints.py`) and, for query
  pages, the UTF-8 length of the JSON the CLI prints (including its final newline).
- **Tokens** are reported only where the host measures them: `tools/measure_entrypoints.py` asks
  `claude --plugin-dir <root> plugin details hep-research` (Claude Code 2.1.301) for its always-on estimate. No
  bytes-to-tokens ratio is assumed anywhere else.
- **Activation set** is de-duplicated along the read path the skill text prescribes: always-on skill descriptions,
  then the activated `SKILL.md`, then (context-resolution stanza) `profiles/registry.json` and one profile `index.md`
  when a profile is needed, then the reference the workflow names for the task. Each file counts once.

Commands (from the plugin root):

```text
python3 tools/measure_entrypoints.py
wc -c skills/hep-measurement/references/review-and-artifacts.md skills/hep-measurement/assets/measurement-review-template.md
python3 core/evidence/query.py --sources <ledger>/sources.json --claims <ledger>/claims.json --today 2026-10-16
```

The paging totals below come from following `next_cursor` until it is null, with the default page size and cap.

## Measurements (Confirmed)

**Entry points** (`tools/measure_entrypoints.py`, all within budget, `over_budget: []`):

| Item | Bytes | Host tokens (always-on estimate) |
| --- | ---: | ---: |
| hep-communication `SKILL.md` | 8145 | 340 |
| hep-computing `SKILL.md` | 8034 | 330 |
| hep-detector `SKILL.md` | 7558 | 330 |
| hep-measurement `SKILL.md` | 7877 | 300 |
| hep-ml `SKILL.md` | 7692 | 340 |
| hep-statistics `SKILL.md` | 7734 | 350 |
| hep-theory `SKILL.md` | 7960 | 340 |
| all seven `SKILL.md` | 55000 | 2332 always-on in total |
| skill descriptions (characters) | 6821 | (in the always-on figure) |
| `profiles/registry.json` | 2264 | — |
| `experiment:ams-02` `index.md` (largest index) | 2983 | — |

The host's always-on figure covers the descriptions it keeps loaded, not the `SKILL.md` bodies.

**Activation set of a measurement-spec review with the public AMS-02 profile** (the D17 entry point candidate):

| Read | Bytes |
| --- | ---: |
| hep-measurement `SKILL.md` | 7877 |
| `profiles/registry.json` | 2264 |
| `profiles/experiments/ams-02/index.md` | 2983 |
| `skills/hep-measurement/references/review-and-artifacts.md` | 7245 |
| `skills/hep-measurement/assets/measurement-review-template.md` | 732 |
| **total on top of the always-on descriptions** | **21101** |

**Evidence query pages** (`core/evidence/query.py`, defaults 20 rows and 16384 bytes):

| Ledger | Ledger bytes (sources + claims) | Rows | Pages | Largest page | Sum of pages | Empty page |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `docs/evidence/statistics` | 40186 | 18 | 1 | 15042 | 15042 | 527 |
| `profiles/experiments/eic/evidence` | 15350 | 9 | 1 | 9521 | 9521 | 527 |
| `profiles/experiments/ams-02/evidence` | 399523 | 209 | 24 | 16345 | 357651 | 527 |

One row of the AMS-02 ledger (`--page-size 1`) prints 1629 bytes; the first default page holds 13 rows, so the byte
cap binds before the row cap on that ledger.

## Findings

- **Inferred.** The candidate 8 KiB target is below what a single activated `SKILL.md` already costs (7558–8145
  bytes); a review activation set is about 21 KB before any evidence row. An agent summary (D17) sharing "8 KiB"
  with the rest of the activation set is therefore not met by the current entry points; D17 has to state its own
  share, measured the same way.
- **Inferred.** Paging bounds the cost of a *targeted* evidence read (one claim or source: about 1.6 KB) and of
  each page (≤ 16 KiB), not the cost of reading a whole ledger: paging through the AMS-02 ledger prints 358 KB, close
  to its 400 KB on disk. Filters (`--claim`, `--source`, `--match`, `--min-strength`) carry the saving.
- **Unresolved (O05).** The query cap (16 KiB) and the summary budget are product defaults, not measurements of
  what a task needs; no number here is a budget that is "met".

## What was not measured

- Token counts other than the host's always-on estimate (no per-file token count is available from the host).
- Companion-supplied profiles and anything outside the checkout (out of scope by the brief).
- Reference files beyond the one the hep-measurement workflow names for a review; other tasks read other references.
