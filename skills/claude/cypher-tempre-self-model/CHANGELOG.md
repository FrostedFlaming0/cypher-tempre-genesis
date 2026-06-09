# Changelog

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
