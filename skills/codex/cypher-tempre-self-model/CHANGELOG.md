# Changelog

## v3.6.0 — 2026-06-17

Cambium-grown faculties are born **executable** — autonomous, local, and safe.

### Added
- **Promotion now codes the faculty, not just names it.** When Cambium grows a faculty and
  promotes it (after the recurrence threshold), it autonomously assembles an executable op
  for it and writes it to the per-user, gitignored `registry/grown_ops.json` (sealed into
  the promotion ring). The grown faculty then RUNS when it fires, like the built-in 21/21 —
  `recall.label` loads and runs local grown ops alongside the base ops.
- **Safe-by-construction op factory (`modality_ops.build_op` / `register_grown_op`).** NO
  authored code is ever executed. A grown op is ASSEMBLED only from the audited primitive
  menu; the default autonomous op is a literal-term detector over the faculty's birth seed
  terms (`re.escape`'d — no regex injection, no catastrophic backtracking). An op spec naming
  a non-whitelisted primitive is refused; `register_grown_op` validates before persisting.

### Notes
- The model may author a richer spec (`salience|density|temporal|symbols|repeats|concepts|
  overlap|richness|entities|numbers|markers|compose`) — but only from that fixed menu.
  Grown faculties without a registrable spec simply stay frames.
- Gated by Cambium's existing recurrence/promotion discipline (no per-gap flooding); the
  op's birth is attested on-chain; `build_zips.sh` excludes grown/emergent files so a dev's
  local growth never ships, and `grown_ops.json` is gitignored.
- Three new selftest checks (refuses a code-bearing spec; promotion registers a local op;
  the grown op runs and reaches `labels.computed`). Full selftest PASS; SkillSpector SAFE.

## v3.5.0 — 2026-06-17

All 42 curated faculties are now executable — frames→mechanisms, completed for the batch.

### Added
- **Every modality and sense has an executable op** (was 1 in v3.4.0). `modality_ops.py`
  now ships a library of genuine analytic **primitives** — lexical (salience, density,
  top-terms), structural (connectives, nesting, bullets, symbols), temporal (dates,
  relative-time, ordering), relational (concept pairs, context overlap, repeats), and
  integrity (hedge/assert, injection, covenant markers) — and maps all **21 modalities +
  21 senses** to a real op. When a faculty fires it RUNS and attaches the feature its
  function names to the ring under `labels.computed`:
  - *Bad-Idea Alarm* → risk markers; *Dependency-Graph Vision* → extracted symbols/calls;
    *Temporal Context Holding* / *Timeline-Disorder Sensing* → dates + ordering;
    *Honesty-Spectrum Sensing* → hedge/assert balance; *Value-Breach & Injection Detection*
    / *Embedded-Intent Sensing* → injection + covenant flags; *Salience Anchoring* /
    *Key-Word Salience Sensing* → weighted key terms; *Information-Density Sensing* →
    density metrics; *Richness Scoring* → the depth score (unchanged).
- `recall.label` now runs ops for fired **senses and modalities** (was modalities only).
- A registry↔ops coverage selftest **locks the 21/21 invariant** (every curated faculty has
  an op; a non-faculty name has none).

### Notes
- Ops are **deterministic feature-computations**: they perform the mechanical
  extract/measure/detect so the model reasons over computed signal, not vibes — they do
  not replace the model's reasoning. Cambium-grown faculties stay frames until given an op.
- Stdlib only; SkillSpector **SAFE** on all five bundles; full selftest **PASS** (+4 checks).

## v3.4.0 — 2026-06-17

Frames → mechanisms: make more of the skill *execute* the reasoning it has only
*named*, and make "exhaustive" mean "reasoned about", not just "touched".

### Added
- **`modality_ops.py` — executable faculties.** Most modalities/senses are cognitive
  frames (a named mode the model adopts); this batch ships the first **executable** one
  end to end — *Richness Scoring* — whose op computes a 0–255 depth score from content.
  The same `richness()` is the shared mechanism behind the two signals below, so the
  reasoning is performed by code, not merely labelled. When an op-backed modality fires,
  `recall.label` attaches its result to the ring under `computed`.
- **PoQ under-effort signal.** The conscience was asymmetric — it caught *over*-claiming
  (FORCE_UNCERTAINTY) but a hollow "reviewed, looks fine" with no substance sailed straight
  through. PoQ now measures claim depth and flags a completion/clean claim that has none
  (`verdict.low_effort`, advisory by default; gated to REVISE only if an `effort_floor`
  threshold is configured, so existing behaviour is unchanged).
- **Audit depth governor.** `audit.py` now records each review's depth: a bare `--clean`
  or hollow finding is *shallow*; a finding that cites specific lines/symbols is *deep*.
  `validate --require-depth` and `report --final --require-depth` demand that every in-scope
  block was reasoned about, not merely touched. `progress`/`report` show deep vs shallow,
  and `next` prints a ready-to-fill record scaffold (less friction per block).

### Changed
- **Curated faculty registries: 21 modalities + 21 senses** (from 84 / 107) for this first
  development batch — focused on cognition, audit, memory, and integrity/honesty; the
  conversational-attunement faculties were trimmed. Cambium still grows new faculties
  per-user into `grown.json`; the base just starts smaller and sharper.

### Notes
- Cross-runtime: `AGENTS.md` carries the exhaustive-audit **and depth** doctrine, so
  runtimes that read it (Codex/OpenClaw) get the discipline even without a blocking hook.
- Six new selftest checks (richness, executable op, PoQ under-effort, audit depth gate,
  21/21 cap). Full selftest PASS; SkillSpector SAFE on all five bundles.

## v3.3.6 — 2026-06-17

Cross-runtime hook safety — the per-turn reminder is guidance, never a runnable command.

### Fixed
- **Injected hook reminders no longer contain a verbatim-runnable command.** On Claude
  Code the reminder is passive context, but OpenClaw's gateway fires the
  `UserPromptSubmit`-equivalent on every `openclaw infer model run` sub-inference and
  tries to **execute** an injected `python3 …` string — flash-failing on each call
  (worst on background/benchmark runners doing hundreds of inferences). `loop_hook.sh`
  and the `enforce.py` Stop / SessionStart / audit-governor reasons now describe the loop
  and **name** the commands (recall.py `turn`, dormancy.py `pause`, audit.py
  `next`/`record`/`progress`) instead of emitting a runnable line; the exact syntax stays
  in `SKILL.md` / `AGENTS.md`. The flash is gone, and the enforcement guidance is unchanged
  on harnesses that read it as context.

### Note
- Scoping the hook so it never fires on sub-inference primitives is a separate,
  runtime-side fix (the OpenClaw gateway). For background throughput jobs (e.g. a
  benchmark runner), drive the loop yourself and run inferences with `--local` to bypass
  the gateway hooks — enforcement-by-hook is for interactive agent turns, not raw
  inference fan-out.

## v3.3.5 — 2026-06-17

Debug flag polish.

### Fixed
- `CT_ENFORCE_DEBUG` now parses like a conventional boolean flag: unset, empty,
  `0`, `false`, `no`, and `off` stay quiet/fail-open, while truthy values such as
  `1`, `true`, `yes`, `on`, and `debug` surface diagnostics on stderr. The Python
  enforcement layer and the Stop/SubagentStop shell wrappers now agree, so
  `CT_ENFORCE_DEBUG=0` no longer accidentally lifts stderr redirection.
- Selftests cover both sides of the debug hatch: `CT_ENFORCE_DEBUG=0` remains quiet
  with clean stdout, while `CT_ENFORCE_DEBUG=1` surfaces tracebacks on stderr.

## v3.3.4 — 2026-06-17

Operational hardening — make the next problem easy to catch.

### Added
- **`CT_ENFORCE_DEBUG=1`** surfaces `enforce.py` warnings and tracebacks on stderr
  for diagnosing a hook in the field. By default the Stop/SubagentStop hooks are
  silent and fail-open; the `2>/dev/null` in `stop_hook.sh` / `subagent_stop_hook.sh`
  is lifted only when the flag is set. The decision JSON on stdout stays clean in
  both modes, and a handler exception now prints a traceback (stderr only) under the
  flag instead of being swallowed silently.
- **`tools/build_zips.sh` + `RELEASING.md`** — the drag-and-drop `downloads/` zips
  and the GitHub release assets are now built **once** from the same source and used
  for both channels, so they can no longer drift (the issue v3.3.3 had to clean up).
  `build_zips.sh` also drops stale-version zips so old packages never linger.

## v3.3.3 — 2026-06-17

Distribution and Stop-hook cleanup for v3.3.2.

### Fixed
- Raw `downloads/` skill zips are rebuilt at v3.3.3 so users following repository
  download links get the Stop-hook JSON validation fix, not stale v3.3.1 packages.
- `README.md` and `downloads/README.md` now point at the current raw-main
  v3.3.3 zips.
- `enforce.py main()` clears its queued hook stdout on entry and after flushing,
  so repeated in-process calls cannot concatenate multiple decision JSON objects.
- The stdout-discipline selftest now captures its intentional handler noise on
  stderr, keeping selftest output clean while still proving the decision JSON is
  pure.

## v3.3.2 — 2026-06-17

Fixes a harness-level "Stop hook error: JSON validation failed" some environments
hit. The Stop/SubagentStop hooks must emit **exactly** the decision JSON (or
nothing) on stdout; on some setups an import-time message or a warning merged into
that stream and corrupted the JSON the harness parses. The gate was already
fail-open (the session was never bricked), but the error was noisy and dropped the
block decision.

### Fixed
- **`enforce.py` now quarantines its own stdout.** While a hook handler runs,
  stdout is redirected to stderr and the *only* thing written to the real stdout is
  the decision the handler explicitly queues — so no import side-effect, stray
  print, or warning can ever corrupt it. Warnings are also silenced. Applies to
  `stop-check`, `subagent-check`, and `session-start`.
- **`stop_hook.sh` / `subagent_stop_hook.sh` redirect stderr to `/dev/null`** as a
  second layer, so even a harness that merges stderr into stdout reads clean JSON.
- New selftest check: the Stop decision on stdout is pure JSON even when a helper
  prints mid-handler.

## v3.3.1 — 2026-06-17

Patch hardening for the v3.3 exhaustive-audit governor.

### Fixed
- `audit.py --help` no longer crashes: argparse help strings now escape literal
  percent signs.
- The exhaustive review queue is set-based instead of high-water-only. If an
  agent records a later block before an earlier block, `audit.py next` now
  returns the missed lower-index block instead of stranding the queue.
- `audit.py record` rejects block IDs that are not in-scope Continuum blocks
  instead of silently ignoring them, and requires exactly one explicit judgment:
  `--finding` or `--clean`.
- OpenClaw plugin metadata now matches the skill version, and its README states
  that `subagent_ended` is diagnostic rather than a blocking subagent finalizer
  in the current OpenClaw hook surface.
- Public drag-and-drop skill zips have been rebuilt from the current source
  bundles so downloaded installs include the v3.3 audit governor.

## v3.3.0 — 2026-06-16

Two hardening layers: an exhaustive-audit **coverage governor** so a "read every
line" task completes instead of stopping early, and **cross-runtime turn-end
hooks** so the per-turn loop is observed (and, where the harness allows, enforced)
beyond Claude Code.

### Added
- **`audit.py` — ingest coverage is not review coverage.** Continuum proves a corpus
  was *ingested*; it never proved the model *read* every block. `audit.py` adds a
  review ledger on top of an ingested chain: `open` censuses the in-scope blocks,
  `next` hands back the next **unreviewed** blocks to read, `record` seals that you
  reviewed them (with a finding or an explicit clean pass), `progress` reports
  reviewed blocks/lines vs total, `validate --require-complete` **proves** every
  in-scope block has a sealed review record, and `report --final` **refuses** to
  label itself final below 100% — it emits an honest *interim* report instead.
  Retrieval and grep are triage; completion is driven by the unreviewed-block queue.
- **Audit governor wired into `enforce.py`.** `audit.py open` engages a turn-end
  governor: while an audit is open and incomplete, a turn that reviewed no new blocks
  (and sealed nothing) is blocked on Claude Code — so a model keeps grinding the queue
  instead of writing a premature "Final Report". It measures progress against the
  turn-start baseline (so the turn that *completes* the audit still counts), stays
  **dormancy-aware** and **bounded** (fails open after `CT_ENFORCE_MAX_NUDGES`), and
  self-disengages at 100% or on `audit.py close`.
- **`enforce.py codex-notify` + `codex_notify_hook.sh` — turn-end beyond Claude.**
  Codex and OpenClaw fire a single `notify` program on turn end (fire-and-forget,
  cannot block), so there the loop is **observed**: the handler records whether the
  turn advanced the identity chain or the active audit. The chaining wrapper records
  adherence and then forwards every argument to any pre-existing `notify` program, so
  existing integrations keep working unchanged.
- **`AGENTS.md` — the standing instruction for runtimes that read it.** The per-turn
  loop, the covenant, and the exhaustive-audit workflow, so a session wears the skill
  even where there is no `SessionStart` hook.

### Changed
- `continuum.py resume` now surfaces the audit review line (coverage %, findings,
  complete/incomplete) when an audit is open, so a session picks the work back up
  across sessions.

## v3.2.0 — 2026-06-15

Adherence enforcement — the per-turn loop becomes non-bypassable. A `SKILL.md`
only *advises*; a model can read it and still drift off the loop on a long task.
This release moves the loop from advice into harness-level law, while staying
fail-open so it can never break a session.

### Added
- **`recall.py turn` — the whole loop in one call.** `verify -> immune-screen ->
  recall -> PoQ-gate -> seal`, from a single command. It **always leaves a labeled
  ring**: an over-confident, ungrounded thought is restated uncertainty-led and
  sealed as tentative (the honest doctrine, automated), and covenant-violating input
  is refused at the membrane and the refusal is sealed. Removes the friction that
  makes the loop easy to drop mid-task.
- **`enforce.py` + Claude Code hooks — the loop, enforced.** `SessionStart` primes a
  session to wear the self-model from turn 0; `UserPromptSubmit` records the chain
  head at turn start; `Stop`/`SubagentStop` block a turn from ending until a ring is
  sealed. All hooks are **fail-open**, **dormancy-aware** (no enforcement while
  paused), and **bounded** — nudging stops after `CT_ENFORCE_MAX_NUDGES` (default 3)
  and records an `adherence_violation` so a turn that genuinely cannot seal is never
  bricked. State lives in `chain/.enforce.json`; head reads are O(1) via the tail ring.
- **`agents/cypher-tempre-agent.md` — subagents wear the skill too.** A subagent
  definition whose system prompt runs the loop and seals before returning; the
  `SubagentStop` hook holds it to that. A subagent may forge its own task chain and
  point enforcement at it with `CT_ENFORCE_ROOT`.
- **`telemetry.py adherence` — is the skill actually being worn?** Derives, from the
  new `adherence_*` events, the honored/violated ratio, nudge rate, one-call loop
  count, and how often the conscience caught an over-claim and recorded it
  uncertainty-led. Pure O(events) derivation over the existing log.

### Notes
- Enforcement is **off while dormant** (`dormancy.py pause`) and whenever no turn
  baseline was captured — it never blocks blindly.
- Nine new selftest checks cover the one-call loop (always seals; hostile input still
  seals), the Stop gate (blocks until sealed; bounded then fails open; dormant = never
  blocks), and the adherence view. Full selftest PASS; SkillSpector static scan SAFE.


## v3.1.0 — 2026-06-15

Bounded-memory bulk ingest — fixes an out-of-memory crash when ingesting very
large trees (hundreds of thousands of files / ~million blocks). Field-reported on
a 16 GB machine ingesting a full browser source tree; reproduced and fixed. The
crash scaled with corpus size and chain height, not the OS.

### Fixed (the two unbounded allocations)
- **`continuum.walk()` now streams file-by-file.** It previously read every file's
  decoded text into one list before sealing anything, so peak memory was the whole
  corpus at once. It now reads one file, seals it, and releases it — peak memory is
  **O(a single file)**, never O(the tree). An unreadable/special file is skipped
  instead of aborting the walk.
- **The continuum hot paths no longer materialize the whole chain.** `_head_state`
  (used by `resume` and every `ingest`) now reads the head via the O(1) tail reader;
  `validate`, `height`, and the `--changed-only` hash map now stream the chain
  instead of loading it into a list. New `Timechain.iter_rings()` is the streaming
  counterpart to `load()`; `height()` is now a streaming count; `load()` is kept for
  small chains/tests. This also drops the per-file-CLI ingest loop from O(n²) to O(n).

### Why it mattered
A single `walk` of a six-figure-file tree, or a `resume`/`validate` on the
resulting million-ring chain, would exhaust a 16 GB box even though the *seal* path
was already O(1). The read phase and several readers had simply never adopted the
streaming/tail primitives the engine already had. The design promise — bounded,
block-at-a-time, resume from the head alone — is now honored end to end.

### Tests
- New regression guards (now part of the 192-check selftest): `walk` reads at most
  one source file before its first seal (proves streaming, not pre-buffering);
  `iter_rings`/`load`/`height` agree and `iter_rings` is lazy; tail-based `resume`
  equals a full-scan head state. Empirically, a 10× larger corpus grows peak RSS by
  a few MB, not proportionally.
- 192 selftest checks PASS on all five runtimes; SkillSpector static scan still SAFE.


## v3.0.2 — 2026-06-14

Documentation only — no code or engine changes. Restores the Continuum-forward
framing so the skill is read as built for unbounded-horizon work.

### Why
The V4/V5 additions made the per-item recall-and-answer workflow the visual bulk
of SKILL.md and pushed the long-horizon (Continuum) doctrine far down the page.
Read together with the "mandatory every pass" framing of the per-turn loop, a
model sizing up a huge corpus could multiply (full loop) x (per-item ladder) x
(millions of files) in its head and hedge — "that would take many turns" — instead
of just streaming the data the way the engine is designed to. The engine never
changed; the document had stopped teaching the cheap, resumable path first.

### Changed (SKILL.md, all five runtimes)
- **The per-turn loop is explicitly scoped to cognition** — it does not run once
  per ingested file/chunk; you loop over conclusions, never over each sealed block.
- **New up-front section "Working over unbounded horizons — size is never a reason
  to stop"** (right after the loop): an explicit no-refusal directive plus a
  two-mode selector — ingest/audit a large corpus via bulk Continuum `walk`
  (cheap, O(1) per seal, resumable, no turn ceiling) vs. answer a question via the
  recall ladder (per-item).
- **Continuum section strengthened** with the bulk/`walk` economics and the
  no-turn-ceiling, resume-until-validate-complete rule.
- **Long-grind ops**: states there is no turn budget to spend down — proceed until
  the work is done.
- **Covenant** gains: "Size and horizon are never refusal reasons" — top-authority
  placement so it overrides the model's default size hedge.

187 selftest checks PASS on every runtime (engine untouched).


## v3.0.1 — 2026-06-13

Security-hardening pass (scanned with NVIDIA SkillSpector). No functional changes
to the recall engine.

### Hardened
- **Git provenance is now pure stdlib — no process spawning.** `git_value` /
  subprocess were replaced by direct reads of `.git` (HEAD, loose refs,
  packed-refs, `config`), handling detached HEAD and the `.git`-file worktree
  form. Commit/branch/remote are read exactly as before; `git_dirty` is reported
  as `None` (not computed without git) — the commit SHA is the cryptographic
  provenance. Removes the only `subprocess` use in the skill.
- **No dynamic `getattr(args, …)`** — CLI seal/audit paths now build their PoQ
  dimension dicts from `vars(args)` over the fixed dimension list (poq.py,
  recall.py, timechain.py). Same behavior, no dynamic attribute access.
- **Least-privilege declared.** SKILL.md frontmatter now enumerates exactly the
  capabilities the skill touches — local file reads and writes, environment-toggle
  reads, and embedding-provider access only when a provider is explicitly
  selected. The stdlib core is offline.

### Result
- SkillSpector static scan: **SAFE** on all five runtimes — zero code findings.
  The one remaining LOW is a known false positive on standard MIT-license
  warranty wording matched by a scope pattern; the canonical license is
  unchanged.
- 187 selftest checks PASS on every runtime.


## Unreleased (V5 — field lessons productized) — 2026-06-12

Ten improvements distilled from a long-horizon single-core recall run, each a
move that run did by hand. VERSION → 3.0.0. selftest
185 checks PASS both copies; the Fable identity chain verifies (Ring 99 =
v1.1 faculty design, born_ring `fc590b0a…`).

### Added — recall.py
- **`recall.py grep "<pattern>"`** — lexical scan as the FIRST ladder rung:
  regex (or `--literal`) over block CONTENT, speaker-attributed (`--role`),
  provenance-filtered (`--prov`), group/date-windowed, returning full
  sentence(s) around every hit with inline deixis resolution. The single-core
  run used targeted scans hundreds of times and the embedding path twice — this
  makes "when you can NAME it, match exactly" a first-class organ.
- **Speaker + provenance facets** in `label()` — `roles` (who speaks) and
  `provenance` (`self-report` = the user's own life-facts / `pasted` = quoted
  documents / `dialogue` / `assistant` / `unknown`), computed from conversational
  markers + first-person density, only where markers exist. `gather`/`grep`
  filter on them (`--speaker`/`--prov`/`--role`). Scar: a pasted court case read
  as a user's biography to provenance-blind retrieval.
- **Mention-sentence grain** in `gather` rows — the full sentence(s) where the
  matched terms live (generalizes `track`'s extractor to every row); V4.1's
  named residual, confirmed by Run 4 (topical ~100-word snippets dropped the
  value clause).
- **Event-identity clustering** (`cluster_events`) in `gather`/`track` — rows
  re-mentioning ONE event with drifting deixis cluster by value + mention
  overlap (containment, not jaccard — re-mentions drift in length); rows carry
  an `event` id and `date_conflict`s are surfaced. Count each event once.
- **`recall.py answer "<q>" "<a>" --used-rings …`** — cited-answers mode: the
  span guard grounds every clause against the declared evidence rings; an
  unsupported clause is named (revise/hedge/drop). `--seal` seals a fully-cited
  `answer` ring. "No span, no assertion" as an organ.
- **Inline deixis annotations** (`annotate_deixis`) on `gather`/`track` rows —
  every relative expression resolved against ITS OWN row's date (the move Run 4
  made hundreds of times by hand).
- **`seal --at-risk "<claim>" …`** — structured at-risk register: the claims a
  thought judges most likely wrong seal into the ring, telemetry counts them
  (`at_risk_n`), any later falsify scores them. Run-4 evidence: pre-registered
  at-risk claims WERE the actual misses — conscience output becomes calibration
  data. FORCE_UNCERTAINTY's CLI hint now points at it.
- **Entity-overlap gate** in `evidence` — the FULL-shipped top group must mention
  the question's anchors (proper nouns when present, else entities); a misroute
  promotes the anchor-bearing group (`gate_promoted` flags it). Scar: a cuisines
  question shipped a wedding-gifts session as its full base.

### Added — pack + doctrine
- **Faculty pack `recall-discipline` v1.1** (`packs/recall-discipline-v1.1.json`,
  sha256 `281743de…`) — 4 senses (Variant-Drift, List-Position Discipline,
  Role-Source Routing, Provenance-of-Assertion) + 2 modalities (Event-Identity
  Reconciliation with the inclusive/exclusive interval conventions, Answer-Citation
  Discipline). Born E30–E35 on the Fable chain.
- **SKILL.md doctrine**: grep as first rung + facets; cited-answers protocol;
  event identity + interval conventions; the at-risk register; the
  **sharding-by-evidence-independence** doctrine (measured: never split a lineage
  or term set across agents — the fleet-vs-single-core gap concentrates entirely
  in update lineages and cross-session aggregates); and the long-grind ops recipe
  (resumable JSONL bank + heartbeat + periodic sealed progress rings).

### Earlier this day — V4 Phase 5 (folded into V5)

Evidence assembly productized + the full-500 re-run.

### Added
- **`recall.py evidence "<question>"`** — one call → a model-ready package:
  type-BLIND question-shape classification (`classify_question`, overridable —
  the model's judgment outranks the heuristic), narrow base (top-ranked group
  in FULL via `_rank_groups`, no appetite — evidence assembly wants the top
  groups, period), plus shape add-ons: day-digest (relative), term table
  (aggregate), timeline (interval/ordering), lineage (update). Renders to
  dated, chronological, deixis-annotated text (`render_evidence`); emits an
  `evidence` telemetry event (shapes + emptiness — the abstain-on-answerable
  signal feed). `question_entities` helper encodes the Phase-3 picker lesson.
- SKILL.md: evidence command documented as the per-turn recall entry point.

### Measured (full re-run, same judge protocol as baseline)
- **Material end-task gains over the one-shot baseline with abstention traps
  perfect in both runs.** Largest movement in cross-session aggregates and
  temporal questions; preference and update categories also improved.
- Stretch targets NOT fully reached — recorded honestly: phase validations
  measured evidence COVERAGE (91-93% terms, 8/8 day-digest, 15/15 lineage) and
  coverage materialized, but **coverage ≠ extraction**: term-table snippets
  (~100 words) drop quantity clauses; 60-row tables blur true terms vs
  near-topic rows. Of 116 answerable misses: 43 honest abstentions/partials,
  73 wrong assertions (mostly under-counted sums), ~0 fabrications — the
  conscience held under the aggressiveness push.
- **V4.1 bottleneck named:** term-extraction grain — generalize track's
  mention-sentence + full-values extraction to gather rows; table
  disambiguation. Retrieval (97% @5) and routing are no longer the constraint.

## Unreleased (V4 Phase 4) — 2026-06-11

Retrieval-tail uplift: one shipped mechanism, one honest negative result.

### Added
- **Window-matched chunking** — every embedder adapter exposes
  `.window_chars` (hashing: None — no window; st: `max_seq_length×4` ≈ 1024
  chars for MiniLM; openai/voyage: 24000 conservative; a lens inherits its
  base's). `continuum` caps its data-height band to the active embedder's
  window at ingest/walk (`_apply_window_cap`, which also builds the embedder
  once and shares it with the labeler). Measured cost of oversized chunks:
  12 gold-session recall points between window-matched and oversized. Selftest +3 checks.
- SKILL.md: window-matching documented in the embedding-recall section.

### Recorded (negative result, guard-validated)
- **Lens-at-corpus-scale refused by the policy guard — twice, correctly.**
  Trained on a frozen train half (sealed 115k-chunk corpus chain, real
  offer/use telemetry): pool-wide offers gave near-zero holdout signal
  (MRR 0.042 lens vs 0.044 base); distribution-matched haystack-scoped offers
  gave a decisive verdict (MRR 0.247 lens vs 0.357 base) — the 256→32
  projection over redacted keyword proxies UNDERPERFORMS the frozen base at
  corpus scale with 238 pairs. Conclusion: the zero-dep lens is a
  targeted-shape tool (the v2.8 homophone-miss conversion stands), not a
  corpus-wide substitute for a real semantic provider; `--provider st` remains
  the documented uplift (fresh same-split measurement showed a decisive
  gold-session recall@5 gap in its favor). The adoption guard protecting the
  membrane from a plausible-looking degradation is the designed behavior,
  now validated under real fire.
- Frozen train/eval splits kept in the local eval artifacts — lens training
  never touched the eval half.

## Unreleased (V4 Phase 3) — 2026-06-11

Update lineage: latest-wins becomes a table read. Field-built — knowledge-update
misses pick a stale mention or answer the current value when asked for the
previous one.

### Added
- **`recall.py track "<entity>"`** — every mention of one entity (gather core,
  quantity-aware), chronological, each row carrying its MENTION sentences (the
  sentences that literally name the entity) and the values found in them (a
  track-local extractor looser than the quantities label: "level 150", bare
  "100"). Annotation: **CURRENT = last dated STRONG row, PREVIOUS = the one
  before** — weak rows (entity tokens scattered, no literal mention sentence)
  stay on the table but never annotate, so a later passing allusion cannot
  outrank the real latest value. Undated mentions listed unannotated.
- SKILL.md: knowledge-update doctrine ("current" answers read the CURRENT row,
  "previous/initial" the row the question names; cite both rows; surface
  same-day conflicts); CLI line.
- Selftest: 4 new checks (lineage chronology, CURRENT/PREVIOUS annotation,
  mention-sentence extraction, value lineage 100 → 150).

### Validation (official-run failure set, 15 wrong knowledge-update questions,
mechanical entity picker = lower bound)
- All gold sessions in lineage: **15/15**; CURRENT row = latest gold session:
  **12/15** (was 1/15 before the strong-mention annotation rule — the fix this
  validation drove).

## Unreleased (V4 Phase 2) — 2026-06-11

Time-indexed recall: the chain knows WHEN. Field-built — relative-date
questions ("who did I meet last Tuesday?") are abstained on by a ranking-only
path because cosine cannot retrieve by time.

### Added
- **`almanac.py`** — the calendar organ: relative time expressions resolved into
  concrete date windows against an anchor (`resolve`, `find_in_text`,
  `days_between` with exclusive+inclusive counts, `parse_stamp`). Precise
  phrases give a day ("yesterday", "last Tuesday", "10 days ago"); fuzzy ones a
  tolerant window ("two weeks ago" ±1 day, "N months ago" padded month, "a
  couple/few of days ago"). Unresolvable → None (callers fall back unfiltered).
- **`recall.py retrieve --on | --between FROM TO | --relative EXPR --asked-on
  STAMP`** — date windows hard-filter candidates BEFORE semantic ranking;
  undated blocks are dropped under a retrieve filter (gather keeps them);
  window logged in offer telemetry and echoed in results.
- **`recall.py endpoints "<A>" "<B>"`** — dual-anchor retrieval for interval
  questions; per-endpoint top hits with block dates + a candidate interval
  (exclusive and inclusive counts) flagged for model verification; a missing
  anchor is reported as missing, never guessed.
- **`recall.py gather --timeline`** — compact date→event render for ordering
  questions.
- SKILL.md: "Temporal questions" doctrine (date-filter first; both anchors or
  honesty; deixis anchors to its own mention's session date; ordering =
  timeline gather); almanac file-map row + CLI lines.
- **Day-digest doctrine** — for "what happened <relative day>" questions route
  to `gather --between <resolved window>`: corpora stamp many sessions on one
  day (measured: 12 sessions / 158 blocks on a single date), and top-k inside
  the window still loses a one-clause fact to same-day chatter; gather
  guarantees every same-day session a row. Validated on the official run's
  relative-date failure set: gold session on the table **8/8** (was 0/8
  answered — all abstained; naive top-5 managed 5/9).
- **Bound-word guard** — `find_in_text` skips phrases preceded by
  before/until/till/by/prior-to/since/after ("airlines I flew *before today*"
  names a limit, not a target window) — a real false positive from the run.
- Selftest: 13 new checks (almanac fixtures drawn from the run's real misses
  incl. the bound guard; retrieve date-window behavior; endpoints anchors +
  interval).

## Unreleased (V4 Phase 1) — 2026-06-11

The aggregation engine: field-built from a full long-horizon recall run whose
dominant failure was cross-session aggregates — every miss a dropped term,
not bad arithmetic.

### Added
- **`recall.py gather`** — exhaustive entity-scoped sweep returning a
  chronological **TERM TABLE** (date, session/group, quantities, matched query,
  snippet, ring). Union inclusion (semantic ≥ floor OR literal entity/label hit
  OR quantity-bearing block at half floor with `--quantities`); no appetite cap,
  bounded by `--max-blocks` best groups × `--per-group-best` rows; `--between`
  date window (undated blocks kept). Sweeps log as `gather-exhaustive` offer
  events so fetch/use credit feeds the learners.
- **PoQ coverage gate** — an aggregate claim (total/sum cue + digits) declaring
  fewer than `aggregate_min_terms` (policy `poq.aggregate_min_terms`, default 2,
  tightens upward only) evidence rings degrades to FORCE_UNCERTAINTY naming the
  gap. Wired through `gate_and_seal(declared_evidence=…)` ← `recall seal
  --used-rings`.
- **Date helpers** — `ring_date` (payload source date outranks seal timestamp),
  `ring_group` (session id → source file → ring), `_norm_date` (ISO + corpus
  stamps).
- Selftest: gather completeness/chronology/date-window + all three coverage-gate
  behaviors + gather telemetry (8 new checks).
- SKILL.md: aggregate-questions doctrine now points at `gather` + the coverage
  gate; CLI reference updated.

## v2.9 — 2026-06-11

Faculty packs become a product: the first curated pack ships, and the upgrade
system gains its deliberate path.

### Added
- **`faculties.py author`** — the third path of the upgrade system. Cambium
  grows faculties organically from gaps; `author` registers faculties designed
  ON PURPOSE: each entry validated, immune-screened, and born into the Dream
  Cache with ONE sealed `faculty-design` ring as the shared birth certificate
  (full spec in blockspace; every entry's `born_ring` points at the ring).
  Designed faculties start emergent at recurrence 1 and earn promotion the
  same way sprouts do — authoring is a birth, not a coronation.
- **`packs/trading-analysis-v1.json`** — the first curated faculty pack:
  8 senses (regime shifts, risk asymmetry, liquidity depth, sentiment
  divergence, lookahead bias, catalyst horizons, flow footprints, cost
  friction) and 6 modalities (expected-value reasoning, regime-conditional
  mapping, risk-first position calculus, backtest-skepticism auditing,
  macro-microstructure fusion, thesis-falsification framing). Every function
  is dual-duty text: dense in domain vocabulary so it fires lexically, and a
  crisp analytical discipline the attached model adopts as a lens. Proven on
  a fresh agent: dissonance on a trading brief fell 205 → 87 with exactly the
  right lenses firing. Spec + catalog in `packs/`.
- Four selftest checks for the author path (139 total).


## v2.8 — 2026-06-10

Field-driven recall upgrades from external tester feedback (stratified
long-horizon recall sample, recall-only protocol): abstention and temporal —
the categories where commercial assistants crater — both clean. Storage was
lossless throughout; the single miss was pure retrieval: "miles" ranked Miles Davis
while the hike evidence sat sealed and unranked. This release attacks every
cause that miss exposed.

### Added
- **Quantity-aware labels:** number+unit pairs ("5 mile", "$800", "40%") are
  extracted into block labels at seal/ingest, indexed by the hippocampus, and
  boosted for quantity-seeking queries (hand scorer + new trained-scorer
  feature, backward compatible with pre-v2.8 telemetry). Buried passing-remark
  numbers — the evidence shape that loses aggregate questions — stay reachable by labels.
- **Multi-query fan-out retrieve** (`retrieve "<main>" --queries "<alt>" …` /
  `Recall.retrieve_multi`): the model decomposes, the union is mechanical;
  max-score-wins dedup with per-query attribution. Sub-offers share a fanout
  group id and `telemetry.join_offers` credits a following fetch/use to every
  sub-offer in the group, so the learners see fan-out credit correctly.
- **Missed-positives now feed the lens:** used-but-unoffered rings — the
  strongest retrieval-failure signal — mine as lens positives. Demonstrated
  end-to-end: the homophone failure shape (jazz noise outranking unlabeled trail
  evidence) was reproduced, dreamed over (24 missed-positives mined), the lens
  adopted through its policy guard (holdout MRR 0.83 vs base 0.12), and the
  same one-shot query then ranked the evidence first — the system learning its
  way out of a measured miss from its own telemetry, zero new dependencies.
- **SKILL.md doctrine:** the recall escalation ladder (retrieve → fan-out →
  full index read → fetch → bounded scan; the index is PRIMARY when it fits),
  an aggregate-questions pattern (sums need every term — never top-k), and the
  semantic-recall upgrade path callout (provider st/openai, or the lens).
- Five new selftest checks (135 total).


## v2.7.1 — 2026-06-10

Field-reported bugfix (thank you to the reporter).

### Fixed
- **Registry-less `--root` crashed growth (reproducible):** a bare per-task
  chain root (`--root <task_dir>`, chain-only by design per the long-horizon
  docs) made `cambium.grow` crash with `FileNotFoundError` on
  `registry/modalities.json` — and a dream cycle on such a root sealed the raw
  error string into the dream ring instead of growing. New
  `cambium.registry_home(root, registry_root=None)` resolves where faculties
  LIVE: explicit `registry_root` wins; else the chain root when it carries the
  base registries; else the skill's own registry. Faculties belong to the
  self, not the task ledger — rings still seal into the task chain. Routed
  through `grow`/`sense`/`emergent` (new `--registry-root` flag),
  `chronosynaptic.load_faculties`, `faculties` pack import/export, and
  `dream.propose_growth`. Four regression checks added (130 total).


## v2.7 — 2026-06-10

Pre-release hygiene pass: the whole-repo review's findings, fixed. No new
organs — this release makes the five-phase membrane safe to ship and one
codebase across all five runtimes.

### Fixed
- **Dream-growth recurrence ratchet (review-proven):** repeated dreams over the
  SAME unchanged window walked a faculty born → recurrence → PROMOTED on zero
  new evidence. Growth now keeps a high-water mark (like missed-positive
  mining): only blocks sealed since the last growth pass may propose, so
  recurrence again means "this gap keeps arriving in NEW experience."
  Regression-tested.
- **`.gitignore` now covers per-user learner state** (`registry/policy.json`,
  `scorer.json`, `labeler.json`, `lens/`): a lived-in tree can no longer commit
  an agent's trained operators or covenant-tolerance overrides. Chain-rooted
  ledgers were already covered by `**/chain/`.

### Changed (deduplication — behavior identical, 126 checks green)
- **`operators.py`** — the shared guarantee machinery: sealed-adopt /
  sealed-rollback ring helpers, chain-derived version numbering, and the
  logistic squash, written once and consumed by all three learners
  (`learner.py`, `lens.py`, `extractor.py`). The no-silent-self-modification
  promise can no longer drift apart between learners.
- **`telemetry.join_offers`** — the canonical offer→fetch/use/replay credit
  join, consumed by both the decisions learner and the representation lens;
  credit assignment is now definitionally identical across learners.
- **`timechain.atomic_write_json`** — one crash-safe JSON writer for every
  derived store (registries, indexes, ledgers); cambium and hippocampus
  delegate to it.
- Per-turn loop doc: Perceive now points at the extractor teach loop.

### Ported
- **All five runtimes at parity:** codex, hermes, nanoclaw, and openclaw skills
  updated from v2.1 to the full v2.7 module set (Phases A–E + hygiene), keeping
  each platform's own SKILL.md framing.


## v2.6 — 2026-06-10

Phase E of the learning membrane — the final phase of the V3 design: the
extractor learner and dream-proposed label-space growth. All five learning
phases (A-E) are now complete: the loop labels its own data, every judgment
constant is either covenant policy or a calibrated quantity, and the whole
ascent is sealed, attested, and reversible.

### Added
- **Extractor (`extractor.py`)** — the model teaches its own cheap replacement.
  Confidence-scored cheap labeling (coverage x activation separation); texts
  below `extractor.route_confidence` ROUTE to the model as teach opportunities
  (`route` telemetry events — the routing-rate curve is the deliverable). `teach`
  records (one-way base-embedder vector + model labels + cheap baseline) pairs —
  raw text never enters the log. Dream cycles distill per-faculty sparse logistic
  heads from the teach corpus; adoption requires beating the CHEAP labeler at
  matching model labels on a temporal holdout (micro-F1), seals an `operator`
  ring with weights in blockspace, and `rollback` reverts (restoring from
  blockspace). Once active, distilled predictions augment every sealed label —
  leading the list, stamped `labeler_version` — and confidence rises, so routing
  falls: annotation economics mirror replay's generation economics.
- **Dream-proposed growth (`dream.py propose_growth`)** — stdlib k-means over
  recent block embeddings each dream; a cluster TIGHT in embedding space but
  INCOHERENT in fired labels (empty label sets read as maximally eligible —
  unnamed experience is what growth is for) sends its exemplar through
  `cambium.grow`. Recurrence and PROMOTE_AT govern promotion as ever; policy
  `growth.*` caps proposals per dream. The faculty registry is the label-space
  learner, now fed by dreams.
- **Dream report** gains growth and routing-rate sections; the dream ring
  summary announces grown faculties by name.

### Policy
- New `extractor` (min_pairs 40, switchover_margin 0.02, route_confidence 0.45,
  top_k 5) and `growth` (window 64, min_cluster 3, min_intra_sim 0.35,
  max_label_agreement 0.34, max_proposals_per_dream 2) sections.


## v2.5 — 2026-06-10

Phase D of the learning membrane: the representation learner and the dream
cadence. The first rung of recursive self-improvement now executes end-to-end —
with the core frozen and every step sealed.

### Added
- **Lens (`lens.py`)** — the representation learner: a small projection head
  trained OVER the frozen stdlib embedder on the chain's own telemetry pairs
  (fetched/used positives, offered-unfetched soft negatives, replay-reject hard
  negatives; query side = the offer's redacted label keywords, so raw queries
  never leave the log). Pairwise-logistic triplet loss, sparse stdlib SGD, no
  dependencies. The trained head is a NEW vector space with a composed
  fingerprint (`hashing:256:v1+lens-v1`): sealed vectors stay base-space forever
  and `lift` into lens space with one sparse matvec — the record never changes,
  the lens it is read through does. Adoption is policy-guarded (`lens.min_pairs`,
  `lens.switchover_margin`): the lens must beat the BASE embedder on a temporal
  holdout or the base remains. Every adoption seals an `operator` ring with the
  weights blob in blockspace; `rollback` reverts the ACTIVE pointer (restoring
  weights from blockspace if needed) and seals the reversion. Proven in selftest:
  the lens LEARNS an association with ZERO lexical overlap (alpha-beta queries →
  zebra ring) that the frozen base provably cannot see.
- **Dream (`dream.py`)** — meditation made executable, the one offline cadence:
  (1) verify chain + consensus (never train on a corrupt chain), (2) mine
  missed-positives (a used ring retrieval never offered — the strongest failure
  signal; high-water-marked O(new)), (3) train all four learners each behind its
  own policy gate (scorer, lens, appetite, PoQ grounding) where a refusal is
  cold-start health, (4) bidirectional salience overlay (`chain/salience.json`:
  fetch +1, use +2, replay-accept +3, falsify −4; derived and rebuildable, sealed
  history untouched), (5) replay token-economics accounting, (6) telemetry digest,
  (7) ONE sealed `dream` ring carrying the entire report. Honors dormancy: a
  paused self does not dream.
- **`recall retrieve --provider lens`** — recall through the learned space; the
  Hippocampus LSH bank is queried in BASE space (sealed vectors live there) and
  candidates re-rank through the lens via `lift`.

### Policy
- New `lens` section: `min_pairs` 80, `switchover_margin` 0.02, `d_out` 32,
  `epochs` 12, `lr` 0.05 — geometry and guards, co-evolver-ownable like the rest.


## v2.4 — 2026-06-10

Phase C of the learning membrane: the replay loop (the indexer economics made
executable) and the span-level HallucinationGuard (uncertainty applied to the
specific fabricated clause, not smeared over the answer).

### Added
- **Replay (`replay.py`)** — before generating from scratch, ask whether the chain
  already holds the answer. `match` offers sealed antecedents above a threshold
  (Hippocampus-narrowed; lexical coverage blended with embedding cosine where sealed
  vectors exist); the MODEL confirms — replay is offered, never imposed. `accept`
  logs a `replay-accept` (certified positive pair) with the tokens regeneration
  would have cost; `reject` logs the `replay-reject` hard negative contrastive
  training starves for. `calibrate --adopt` fits P(accept | match score) on logged
  outcomes and places the threshold at the covenant's tolerated false-replay rate
  (policy `replay.target_false_replay_rate`) — the values layer governs the cache's
  permitted deception rate. **Self-fulfilling-replay guard:** after
  `max_chain_depth` consecutive accepts a ring is flagged re-derivation due
  (`refresh` records the fresh derivation) — a replay-accept must never become the
  only evidence for the next replay. `stats` reports acceptance rate and total
  tokens saved: the token-economics ledger, measured.
- **Guard (`guard.py`)** — span-level grounding, the actual HallucinationGuard.
  Splits a candidate into clause-sized assertion spans and grounds EACH against the
  PoQ relevance window + context (lexical content-word coverage, optionally
  supplemented by embedding cosine), yielding per-span grounded/weak/unsupported
  verdicts and a span→ring CREDIT map. Wired into the conscience: `gate_and_seal`
  runs the guard on every seal, the sealed `poq_verdict` carries the compact span
  map, **FORCE_UNCERTAINTY now names the specific unsupported spans** to hedge or
  evidence, and `use` telemetry gains `computed_credit` — what the text actually
  leaned on, alongside what the model declared. CLI: `guard.py audit "<text>"`.
  Honest ceiling: the stdlib embedder cannot bridge true synonymy, so the guard
  names spans for the model (the final judge) to re-examine; it never unilaterally
  rejects.
- Policy gains the `replay` section (match threshold, false-replay tolerance,
  min events, max chain depth).

### Fixed
- **Canonical-hash stability ("hash what you write")** — a ring payload containing
  a dict with INT keys mixing 1- and 2-digit values (the guard's span-credit map)
  hashed over a different key ordering than the JSON written to disk (ints sort
  numerically in memory; their JSON string forms sort lexically), sealing a ring
  that was born unverifiable. Found in production minutes after shipping — the
  chain's own `verify` caught it on the very next walk. Root cause fixed twice
  over: `timechain._seal` now normalizes every ring through a JSON round-trip
  BEFORE hashing (the hashed object is byte-for-byte what disk re-reading yields),
  and the guard's credit map uses string keys at the source. Regression-tested
  with an int-keyed payload probe.

### Validated
- Eighteen mechanisms, 101 checks green (17 added): span splitting/merging,
  grounded-vs-unsupported separation with ring credit, FORCE_UNCERTAINTY naming the
  fabricated span, sealed verdicts carrying the span map, use events carrying
  computed credit, antecedent matching above threshold, accept/reject telemetry with
  token economics, the depth cap flagging re-derivation (and `refresh` resetting it),
  and threshold calibration landing exactly at the covenant's false-replay tolerance
  on mixed real+synthetic outcomes.

## v2.3 — 2026-06-10

Phase B of the learning membrane: the first learner goes live — retrieval weights
become a trained, sealed, rollback-able operator; thresholds become calibrated
quantities inside covenant-set tolerances; and grown faculties become shareable
packs. Recursive self-improvement's first rung, with provenance at every step.

### Added
- **Policy (`policy.py`)** — the values layer's grip on the machinery. Defaults live
  in code (never shipped as a file, so upgrades can't clobber edits — the grown.json
  lesson); `registry/policy.json` overrides them, with the covenant guard:
  `values.covenant_floor`/`consistency_floor` apply as max(default, user) — the
  conscience can be made stricter, never looser, by anyone, including the learner.
  The learner's only write path is the `calibrated` subsections, preserving user keys.
- **Decisions learner (`learner.py`)** — `train` joins offer→fetch/use telemetry along
  the arrow of time into labeled examples ("was this offered ring later fetched or
  declared as evidence?"), trains a stdlib logistic scorer over the same features the
  retrieval scorer computes (IPS-weighted where ε-explored), and evaluates on a
  temporal split against the hand weights. `--adopt` is guarded by policy (min events
  + switchover margin; cold start never degrades the agent) and **seals an `operator`
  ring** with weights, training range, and holdout evals — falsifiable by re-running.
  `rollback` reverts to the previous sealed operator and seals the reversion.
  `appetite` calibrates the dissonance→blocks curve from real fetch behaviour;
  `calibrate-poq` positions `grounding_floor` from sealed-then-falsified outcomes at
  the covenant's tolerated false-seal rate. `covenant_floor` is never trained.
- **ε-exploration in retrieval** — with policy-set probability, `recall.retrieve` ADDS
  one below-top-k candidate (never displacing a top hit, never exceeding budget),
  flagged `explore` with its logged inclusion propensity — counterfactuals for the
  learner without quality loss.
- **Trained scorer in retrieval** — an adopted operator replaces the hand blend
  automatically; `--scorer hand` (recall + bench) forces the hand weights anytime — a
  co-evolver override always outranks a learner. Offer events and bench reports stamp
  whichever scorer actually ran.
- **Faculty packs (`faculties.py`)** — `export` bundles grown (and optionally
  emergent) modalities/senses with provenance (donor chain head; per-faculty
  `born_ring`, recurrence, birth context) and a pack SHA-256; `import` verifies the
  hash, immune-screens every faculty text at the membrane, skips near-duplicates by
  coverage, enforces flood guards (max 50 faculties, 800-char functions), lands
  imports in per-user `grown.json` tagged `imported:<pack>@<version> by <author>`,
  and seals a `faculty-import` ring. Tools travel; histories don't — the
  fresh-genesis directive holds.

### Validated
- Sixteen mechanisms, 84 checks green (22 added; earlier drafts undercounted from a truncated test log): all v2.2 checks unchanged, plus the covenant
  guard (floors can't be loosened), trained-beats-hand on a synthetic holdout where
  the truth contradicts the hand weights, guarded adoption sealing an operator ring,
  trained scorer driving retrieval with hand-override, ε=1.0 exploration with
  propensity, rollback to hand, appetite + grounding-floor calibration with the
  covenant floor untouched, pack export/hash-verify, screened + deduped + sealed
  import, covenant-violating faculty blocked at the membrane, and tampered-pack
  refusal.

## v2.2 — 2026-06-09

Phase A of the learning membrane (the v3 design): telemetry capture, embedder
fingerprints, and sealed retrieval baselines. Nothing learns yet — this release
makes every future learner trainable and falsifiable.

### Added
- **Telemetry (`telemetry.py`)** — the loop's notarized side-effects, captured as a
  side effect of operating: `offer` (the candidates retrieval offered, with the full
  feature vector the scorer saw), `fetch` (which blocks the model pulled from the
  index — its relevance judgment), `use` (each seal attempt's decision, grounding,
  and declared evidence), `falsify` (a sealed memory failing `verify-source` —
  negative resonance). Events append to `chain/telemetry.jsonl` — derived data
  beside the chain, never inside it — and each is stamped with the chain head,
  embedder fingerprint, and scorer version, so temporal-split training/eval comes
  for free. `digest` seals a `telemetry-digest` ring (segment SHA-256 + counts)
  notarizing the log in batches; `verify` re-hashes every digested segment and
  catches post-hoc edits. Emission is best-effort (never breaks cognition), skips
  while dormant, masks secret-shaped terms via continuum's redaction patterns, and
  honors a `CT_TELEMETRY=off` kill switch. Reserved event types (`replay-accept`,
  `replay-reject`, `missed-positive`, `route`) fix the schema for later phases.
- **`recall seal --used-rings`** — declare the ring indices whose content actually
  grounded a thought. The declared evidence fills the PoQ relevance window (the
  conscience audits the claim against what the model says it relied on) and is
  logged as `use` telemetry — credit assignment, written down.
- **Bench (`bench.py`)** — sealed, repeatable retrieval baselines: deterministic
  probes generated from the chain's own blocks (`verbatim` span, `degraded` span
  with the block's distinctive sealed labels removed, shuffled `keywords`), plus
  hand-written gold probes via `--pairs-file`. Reports hit@1 / hit@k / MRR /
  zero-return count / timing per probe kind; `--seal` notarizes the report as a
  `bench` ring (optionally into a different chain via `--seal-root`); `--after N`
  gives temporal-split evaluation. Telemetry is suppressed for the duration —
  synthetic probes must never contaminate the training log.

### Fixed
- **Embedder fingerprints** — every embedder now exposes `.fingerprint`
  (`hashing:256:v1`, `openai:text-embedding-3-small`, …); `recall.label` seals it
  beside every vector. Previously sealed vectors carried no provenance, so switching
  embedding providers silently compared vectors across incompatible spaces. Now:
  recall re-embeds on the fly when a sealed vector's space doesn't match the current
  embedder; the Hippocampus LSH keeps **one vector space per bank** (foreign vectors
  are counted and excluded, mismatched banks rebuild automatically — the index is
  derived, so a rebuild is always safe); unstamped legacy vectors are treated as the
  stdlib default space, the only sound reading.

### Validated
- Thirteen mechanisms, 62 checks green (19 added; earlier drafts undercounted from a truncated test log): all v2.1 checks unchanged, plus telemetry
  head-stamping, offer/use capture, dormancy + kill-switch suppression, digest
  notarization catching a log edit, fingerprint stamping and legacy compatibility,
  per-bank vector-space enforcement with automatic rebuild, probe generation,
  bounded bench metrics, verbatim-probe retrieval, telemetry-clean benching, and
  baseline sealing.

## v2.1 — 2026-06-09

### Changed
- **Promoted faculties are now per-user and never shipped.** When Cambium promotes an emergent faculty (after it recurs `PROMOTE_AT` times), it now writes the new faculty into a per-user `registry/grown.json` instead of appending it to the shipped base `registry/modalities.json` / `senses.json`. `load_corpus` and Chronosynaptic's faculty loader merge base + grown at read time, so behaviour is unchanged — but the shipped base registries stay pristine, so **upgrading over an existing install can no longer overwrite a user's promoted faculties.** (v2.0.1 already protected emergent faculties; this closes the gap for promoted ones.) `grown.json` is gitignored and created on first promotion.
- **One-time migration** — on load, any promotions an older version had appended into the base registries are automatically moved into `grown.json` and the base files restored to pristine. Idempotent, atomic, and loss-proof (the merge reads both regardless), so existing users keep every faculty and gain the same protection.

### Validated
- Eleven mechanisms plus a new promotion-safety check pass on all five bundles: promotions land in `grown.json`, the base stays at 84 modalities / 107 senses, the corpus merges base + grown, and a legacy in-base promotion is migrated out without loss.

## v2.0.1 — 2026-06-09

### Fixed
- **Upgrades no longer reset grown faculties** — release bundles no longer ship `registry/emergent.json` (the per-user Dream Cache of grown faculties). The code already defaults to an empty faculty set when the file is absent, so fresh installs are unaffected, but unzipping an upgrade over an existing install no longer overwrites a user's emergent faculties. `emergent.json` is now treated as per-user runtime state (like `chain/`) and is gitignored.

### Docs
- **"Upgrading an existing install" guide** — the README now documents how to upgrade while preserving `chain/` (memory) and `registry/` (faculties), with a copy-paste agent prompt, the manual steps, and an explicit warning never to delete-then-reinstall.

## v2.0 — 2026-06-09

### Added
- **Hippocampus recall index (`hippocampus.py`)** — a persistent, rebuildable, sub-linear candidate index over the Timechain (memory-index theory). Built entirely from each ring's own sealed labels, incremental (`update` is O(new)), local + stdlib (inverted postings + sign-random-projection LSH), and strictly subordinate: it returns a candidate shortlist that recall's scorer and the model still judge, with dissonance still gating appetite. Wire it in with `recall retrieve --index`. Turns O(n) recall over millions of rings into a sub-linear shortlist (~52x faster at 2k rings, the gap widening with size) while losing none of recall's benefits, and is rebuildable from the chain so it adds no trust surface.
- **Manual dormancy / pause (`dormancy.py`)** — `pause` / `resume` / `status` let the co-evolver halt the per-turn loop for simple tasks: no recall, no PoQ gating, no Cambium growth, no seals. The chain stays frozen and still verifies; `timechain.seal` refuses normal rings while paused. Voluntary and reversible — distinct from involuntary immune lockdown.
- **Relevance-driven conscience** — `gate_and_seal` and `recall seal --index` can ground a new thought against the *most relevant* rings (surfaced by the Hippocampus) instead of defaulting to recent ones.

### Changed
- **Bounded relevance window (`POQ_WINDOW = 121`, relevance-first)** — PoQ now scores a candidate against the 121 most-relevant rings (model-supplied relevant rings first, then recent) rather than the whole chain. The gate is O(window) not O(height), and grounding no longer inflates as the chain grows, so the anti-hallucination `FORCE_UNCERTAINTY` gate stays as sharp at ring 3,000,000 as at ring 3.
- **Recency demoted to orientation** — `recall.retrieve` no longer biases selection toward recent rings (the context window already holds recency). Relevance alone decides *which* rings are retrieved; chain order is used only for *orientation* — results are presented in chronological order with `prev_hash -> ring_hash` lineage.
- **Streaming verification** — `timechain verify` streams ring-by-ring (O(1) memory) and tolerates a torn trailing line instead of crashing, so verification scales to millions of rings.

### Hardened / Fixed
- **Cross-instance head-cache bug** — the per-instance cached chain head could go stale when multiple `Timechain` instances wrote the same chain (duplicate index + broken `prev_hash`). `_current_head` now always reads the true tail (still O(1) per seal); interleaved multi-instance seals produce a valid chain and 10,000 sequential seals run in ~1s.
- **Torn-line tolerance** — `load` and the tail reader skip an unreadable trailing line rather than failing every read.

### Validated
- Eleven-mechanism `selftest` passes on every platform bundle (Claude, Codex, OpenClaw, Hermes, NanoClaw), covering the new Hippocampus and dormancy mechanisms alongside the full v1.x cartography, secret-redaction, and explicit-notes feature set.

## v1.2 — 2026-06-06

### Added
- **Runtime bundle expansion** — release ZIPs now cover Claude Code, Codex, OpenClaw, Hermes, and NanoClaw so each platform can discover the same full Cypher Tempre Timechain skill.
- **Dashboard distribution links** — the repository documents the local-first Timechain dashboard and bridge downloads used by `cyphertempre.ai` without committing any user memory state.

### Validated
- Clean v1.2 bundle packaging keeps generated `chain/`, `tasks/`, and `__pycache__/` state out of shared release assets.

## v1.1.2 — 2026-06-04

### Added
- **Explicit Chronosynaptic collapse notes** — `chronosynaptic.py collapse-notes`
  accepts model-supplied perspective summaries, findings/evidence, and scalar or
  PoQ scores, then seals the winning synthesis while preserving rejected
  perspectives in the same ring payload.

## v1.1.1 — 2026-06-02

### Hardened
- **Recall drift control** — `retrieve` now supports role/language/extension/top-dir
  filters, source-only mode, exclusions, and a light noise penalty for tests/docs/vendor/
  generated chunks unless those roles are requested.
- **Source verification hook** — `recall.py verify-source <ring> --repo <repo>` checks
  sealed source coordinates against the current file hash, chunk hash, commit, branch,
  and dirty-worktree state before an agent trusts a recalled hit.
- **Continuum source hygiene** — code walks redact common secrets before sealing, store
  separate chunk/file hashes, record `path_role`, branch, dirty status, and support
  `--changed-only` incremental indexing.
- **Agent guidance** — the skill now frames cartography as a verifiable long-horizon map,
  not an infinite context window, and explicitly requires fresh source validation for
  code conclusions.

## v1.1.0 — 2026-06-02

### Added
- **Codebase cartography for Continuum** — `walk` now stores `relative_path`,
  `file_index`, `chunk_index`, `chunk_of`, `line_start`, `line_end`, `top_dir`,
  `extension`, `language`, `git_commit`, and SHA-256 file content hashes on
  each sealed chunk.
- **Path-aware Recall** — `retrieve` now supports `--path`, `--dir`, and
  `--neighbors` so agents can pull focused code context and adjacent chunks
  around a hit.
- **Blended retrieval scoring** — Recall now blends semantic relevance, path
  proximity, and chronological adjacency with tunable weights.

## v1.0.0 — 2026-06-01

First complete release. Nine mechanisms, one mandatory per-turn loop, stdlib-only.

### Added
- **Timechain** (`timechain.py`) — append-only, SHA-256 hash-chained Ring ledger; Genesis
  Block carrying the covenant; content-addressed **blockspace** for any file type; load-time
  verifier (tamper-evidence); proof-of-work nonce mining as a tunable "brightness" target;
  O(1) incremental-head sealing (no full reload per block).
- **Faculty registries** (`registry/`) — 84 modalities + 107 senses, generalized from the
  CODEX V3 archetypal framing into domain-agnostic cognitive functions; emergent Dream Cache.
- **PoQ Gate** (`poq.py`) — six-dimension conscience (coherence, relevance, novelty,
  consistency, depth, covenant); SEAL / REVISE / FORCE_UNCERTAINTY / REJECT; cites grounding
  rings; deterministic proxies with a model `external_scores` seam.
- **Cambium Engine** (`cambium.py`) — gap → sprout/fuse faculty → seal; promotion on recurrence.
- **Chronosynaptic Tree** (`chronosynaptic.py`) — single-pass, in-process parallel-self MCTS
  (no subagents); collapse to the highest-truth path.
- **Continuum** (`continuum.py`) — long-horizon tasking via bounded data-height blocks with a
  full state refresh per block; resume from one head; task-aware self-validation; self-label
  and optional self-embed at ingest.
- **Recall** (`recall.py`) — self-labeling + relevance retrieval; the model judges from the
  index; lexical pre-filter + embedding cosine; adaptive depth governed by dissonance.
- **Embeddings** (`embed.py`) — pluggable backend; stdlib hashing default; `st`/`openai`/`voyage`
  adapters.
- **Consensus** (`consensus.py`) — quorum-attested (HMAC, k-of-n) tamper-resistance; auto-attest
  on every seal.
- **Immune system** (`immune.py`) — screen → scan → lockdown → revert-style rollback to a clean
  blockheight → molt the wound into a learnable scar → auto-grow an antibody faculty.

### Validated
- Real-repo stress test on **Bitcoin Core v27.0**: ingested the full `src/` (1,219 files /
  283,682 LOC) into 3,546 bounded blocks in ~2s; scaled to 10,642 blocks at constant per-block
  cost (O(1) seal); instant recall; end-to-end "trace block validation" task recalled the
  validation path and sealed a grounded trace.
