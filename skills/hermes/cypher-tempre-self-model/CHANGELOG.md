# Changelog

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
