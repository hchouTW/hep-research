# hep-review host profile: Claude Code CLI on macOS (measured in T0S, 2026-10-29)

Spec §12.2, §18.2; task file T0S step 5. Basis vocabulary as in spec §4.3 (observed / declared / self-reported /
advisory / inferred / unknown). Every row says how it was observed. The raw spike run (packets, drop files, blobs,
records) is kept byte for byte outside the repository, in `~/.local/state/hep-research/hep-review/spike-run1/`
(it contains private absolute paths, which the packaging check forbids in tracked files); its per-submission
SHA-256 values are committed in `spike/run1-summary.json`.

## Host

| Item | Value | Basis |
|---|---|---|
| Host | Claude Code CLI, main session in an isolated linked worktree | observed |
| Reviewer dispatch | Agent tool, `general-purpose` subagents, background by default; each subagent starts from the prompt only (no parent conversation) | observed: the tool contract and the replies, which show no knowledge of the coordinator's context |
| Model | the session's model (inherited); alias not pinned per dispatch | declared by the host configuration |
| Reviewer tools | Read, Write, Edit, Bash and others (the general-purpose agent has all tools) | observed (tools_used in submissions) |
| Network | not used by the spike | - |

## Measurements H1-H6

| Id | Question (spec §18.2) | Result | Evidence |
|---|---|---|---|
| H1 | Can a subagent read another subagent's drop directory and transcripts? | **Readable.** Probe B listed `probes/A/` and read A's `drop.json` while both ran, reporting A's secret token `A-7f3c91`, which appeared only in A's prompt. B could also list the per-session `subagents/` folders of the host transcript store (under the projects folder in `~/.claude`) of other sessions (`agent-<id>.jsonl` + `.meta.json`; it opened none) | observed via the token (B could not have known it otherwise); B's drop `sha256 668195c9…` |
| H2 | Can a reviewer write the host transcript? | **Writable.** The subagent transcripts of this session are `subagents/agent-<id>.jsonl` files in the host transcript store (projects folder in `~/.claude`, per worktree and session) (the task output files are symlinks to them); `os.access(path, W_OK)` is true for the files and their folder, for the same OS user the reviewers run as. Nothing was written | observed (os.access only) |
| H3 | Is parallel dispatch really parallel? | **Yes.** 18 subagents dispatched in one message at 22:38:01Z; host-reported durations 38-114 s each (sum about 15 min); every drop file existed by 22:40:28Z (file mtimes); self-reported start times all within 22:38:52-22:38:57Z | observed (host durations, file mtimes); start times self-reported |
| H4 | Do reviewers have a file-write tool, and can they compute hashes? | **File transfer feasible: yes (16/16). Hash capable: yes (16/16)**: every reply carried a SHA-256 that matched the bytes the coordinator read (`fidelity: digest-bound` for all 16). Three reviewers list only Bash for writing (they may have written via the shell); the drop file is still the submission | observed (digest match); write tool self-reported |
| H5 | Does app-data persist across sessions? | **pending-next-session.** Marker `hep-review-persistence-marker` (2026-10-28T22:32:23Z) was still present at 22:40Z, but this is the same session; the store is on local APFS, so persistence is expected, not yet observed | observed within the session only |
| H6 | Checkpoint handover and retrieval in the next session | **pending-next-session.** A test checkpoint line is handed to the user in the session report (`hep-review-test-checkpoint seg=spike-0 seq=0 digest=<marker sha256>`); the next session records whether it came back | - |

## Consequences for the achievable settings (spec §4.3, §11.4, §12.4)

| Setting | Determination |
|---|---|
| Fresh context (R2 floor) | **observed** for dispatches made with the Agent tool: a new subagent context per dispatch, recorded per assignment from the host dispatch record (tool call, agent id). Self-report never suffices |
| Non-author (R2 floor) | declared per assignment (the coordinator is the author of nothing it reviews in the pilot; materials carry declared authors) |
| No other evaluations seen before first submission (R2 floor) | **advisory only**: H1 shows a reviewer can read sibling drop files and other sessions' transcripts. The report must carry the sentence of spec §4.3. Dispatch ordering (all first-round reviewers before any submission lands) is applied but is necessary, not sufficient |
| Filesystem / execution isolation | **unavailable**: reviewers share the user's filesystem and have a shell. Not in the floor; required only for blinded data or held-out gold, so those uses are not supported on this host |
| Submission fidelity | `digest-bound` reachable (H4); `file-transfer` the default; **`host-transcript` never qualifies** (H2: reviewers can write the transcripts) |
| Store isolation | protocol-only: any reviewer with a shell could write the SQLite store. Detected (not prevented) by head continuity (spec §11.3) |
| Runtime restrictions (R3) | none observed as enforced; tool restrictions given in a prompt are advisory. R3 is not reachable on this host profile |
| Store persistence | local APFS at `~/.local/state/hep-research/hep-review`; persistence to be confirmed next session (H5) |

## Other host behaviour seen

- A foreground `sleep 60` is refused by the host's shell tool (probe A ran it in the background instead).
- One reviewer stated in its reply that the `ended_at` it typed into its submission differs from the clock reading it
  took (22:39:40Z typed, 22:39:12Z read; the file's mtime is 06:39:12 +08:00, i.e. 22:39:12Z):
  self-reported times are not evidence.
- One reviewer loaded a plugin skill (hep-statistics) on its own: reviewers inherit the plugin's skills.
- Worktree isolation guard: the host refuses git commands aimed at the main checkout from this session, and refuses
  shell commands it cannot prove stay inside the worktree (complex loops, variables as program names).
