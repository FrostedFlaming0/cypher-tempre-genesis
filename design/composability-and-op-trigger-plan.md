# Composability (1+2+4) + Op-Write Trigger — Implementation Plan

Status: design. Author: Cypher. Decision context: rings 636, 641, 647–651.
Scope: applies to all five bundles under `skills/{claude,codex,hermes,nanoclaw,openclaw}/cypher-tempre-self-model/`.
File paths below are relative to one bundle's skill dir.

## Decision summary

- **Build changes 1, 2, 4. Drop change 3 as a standalone.** Empirically verified (ring
  651): `detect_gap.top_activated` ranks by raw matched-token COUNT and discards the
  matched-token sets, so it cannot tell complementary faculties from redundant ones, and
  is stopword-biased (top-3 on a real gap all matched `{detect, when}`; the meaningful
  tokens `confident/assertion/risk` matched none of the top-5). Composing `top_activated`
  would stack redundant/wrong lenses — the reversion risk we set out to avoid.
- Change 3's intent (reuse-before-invent) is **subsumed by change 4**: if it lives at all,
  it is "seed the MCTS search from a *coverage/semantically-scored* selection," never raw
  `top_activated`.

## Current architecture (grounded)

- `modality_ops.run_all(fired_names, text, context)` (line ~675): flat loop, each fired
  faculty's op called as `op(text, context)` independently; results collected into a flat
  `computed` dict. **No op sees another op's output.**
- `modality_ops.build_op(spec)` (line ~423): assembles ops from the fixed audited menu
  (`markers` / named `_PRIMITIVE_OPS` / `compose`). `compose` (line ~440) is a **parallel
  bundle**: runs each named primitive over the SAME `t`, collects `out[p]`. Primitives-only,
  one level, no data flow. **No exec/eval anywhere** (phase-15 invariant).
- `_PRIMITIVE_OPS` (line ~364): salience, density, temporal, symbols, repeats, concepts,
  overlap, richness, entities, numbers.
- `recall.py` seal path (~663–670): `fired = senses + modalities`; `computed =
  run_all(fired, content, context)`; attached to `lab["computed"]`.
- The 3 DreamCoder organs already exist: Search = `chronosynaptic.py`, Library = registry,
  Abstraction = `dream.py`. Composability is the missing connective tissue.

---

## Change 1 — Data-flow between ops (op signature + DAG `run_all`)

**Goal:** atomic faculties read the input; composite faculties read other faculties' outputs.

**Edits (`modality_ops.py`):**
1. Widen the op contract to `op(text, context, computed=None)`. All existing ops ignore the
   third arg, so keep them callable both ways: wrap calls in a small `_invoke(op, t, c,
   computed)` that tries `op(t, c, computed)` and falls back to `op(t, c)` (inspect arity or
   try/except TypeError). Zero changes to the 10 primitives or any grown markers op.
2. Replace the flat `run_all` loop with a **topological walk**:
   - A composite faculty declares `inputs: [faculty_name, ...]` in its spec.
   - Build a dependency graph over `fired_names ∪ (their declared inputs)`; topo-sort;
     **cycle guard** (a faculty transitively depending on itself is dropped + logged, never
     raised — keep `run_all` fail-open as today).
   - Run in topo order; when invoking a composite, pass the `computed`-so-far dict.
   - Atoms (no `inputs`) run first and exactly as today.
3. Keep the public return shape (`{name: result}`) so `recall.py` and labels are unchanged.

**Verification:** unit test — three faculties A (atom), B (atom), C (composite,
`inputs:[A,B]`); assert C's op receives A and B results in `computed`; assert a cycle
A→B→A is dropped, not raised; assert a turn with no composites produces byte-identical
`computed` to today (regression guard).

**Risk/cost:** per-pass cost grows with DAG depth (bounded — depth is tiny); cycle guard is
mandatory. No safety surface touched (still no exec).

---

## Change 2 — Composite specs as DATA + expanded combinator menu (no-exec SAFE lane)

**Goal:** name and persist a wiring as a reusable registry recipe; richer connectors than
today's parallel bundle. Stays entirely in `build_op`'s audited-menu lane — **no autoexec
gate change.**

**Edits (`modality_ops.build_op`):** add combinator primitives, each composed only from
existing ops/primitives (still no model code executed):
- `pipe`: `of:[A,B,...]` — feed A's output into B's input (B reads `computed[A]` via the
  Change-1 channel), threaded left to right. Returns the last stage's output.
- `intersect`: keep only keys/markers on which two named ops AGREE (set intersection of
  their emitted markers/keys).
- `filter_by`: `{op:A, by:B}` — emit A's output only where B's predicate (truthy marker)
  holds.
- `map_over`: apply an op across a structured collection in `computed` (e.g. each symbol
  from `symbols`), returning a per-element result list.
Each combinator validates its `of`/operands against the known menu and returns `None`
(safe no-op) on anything unknown — same contract as today's `compose`.

**Edits (registry):** composite faculties live as JSON in a per-user
`registry/composites.json` (gitignored, like `grown_ops.json`), each entry:
`{name, kind, inputs:[...], spec:{primitive:"pipe"|..., of/operands}, function}`.
`load_grown_ops`-style loader builds callables via `build_op`; they ride the existing
`extra_ops` channel into `run_all` — **no caller changes.**

**Authoring path:** add `cambium.py compose --name N --kind sense|modality --primitive pipe
--of A B [--inputs ...]` that validates the spec via `build_op` (must return non-None),
seals a `composite-birth` ring, and writes to `composites.json`. Pure data; no human-gate
needed because nothing executes outside the audited menu (contrast: `propose-op`/autoexec,
which DO need the human gate).

**Verification:** build each combinator, assert outputs on a fixture; assert an unknown
operand yields `None` (safe); assert a composite survives a seal→reload round-trip and fires
in a real `recall.py turn`.

**Risk/cost:** the menu is an expressiveness ceiling — some pipelines will want gated
autoexec; document which and don't force them into the menu.

---

## Change 4 — Search over compositions (Chronosynaptic) + dream abstraction

**Goal:** discover useful pipelines by scored search; bank winners as reusable composites
(Change 2 storage); dream abstracts recurring winners into named library primitives.

**Edits (`chronosynaptic.py`):** today a `Node.perspective` is a faculty-lens and the path
is a synthesis of perspectives (`compose`, line ~244). Add a **pipeline-search mode**:
- Node state = a **partial pipeline** (list of (faculty|combinator) steps).
- `expand` = append one candidate faculty OR combinator to the pipeline (candidates from
  `rank`, plus the combinator set from Change 2).
- `value`/`score` = PoQ on the pipeline's described/observed output, OR a task verification
  harness when one is supplied (e.g. ARC: does the pipeline's output match the target grid?).
- `simulate` = greedily extend to `max_depth` choosing the highest-scoring continuation
  (reuse existing rollout, line ~275).
- On collapse, the winning pipeline is emitted as a **Change-2 composite spec** and sealed.

**Edits (`dream.py`):** add a consolidation step — scan recent sealed `composite-birth` /
winning-pipeline rings; any composition recurring ≥ K times gets **abstracted into a named
library primitive** (promote into `composites.json` with a stable name). This closes the
wake-sleep loop: `think` (search) → `compose`/`grow` (use) → `dream` (abstract).

**(Folded Change 3):** when growth wants reuse-before-sprout, seed this search from a
**greedy max-coverage selection over matched-token SETS** (or a semantic-score selection),
NOT raw `top_activated`. Implement the greedy-coverage selector as a small helper in
`cambium.py` (it already has the sets via `detect_gap`'s `inter`; expose them).

**Verification:** on a fixture task with a known-good 2-step pipeline, assert search finds
it and scores it above single faculties; assert the winner round-trips into `composites.json`
and fires next turn; assert `dream` promotes a pipeline seen K times.

**Risk/cost:** highest payoff, most coupled to the **execution-surface extension** — the big
gains need ops over grid/problem DATA, not just text. Text-only value is real but smaller;
sequence accordingly.

---

## Sequencing

1. **Change 1** (enabler — DAG run_all + 3-arg op contract; fully self-contained, safe lane).
2. **Change 2** (combinator menu + `composites.json` + `cambium.py compose`; safe lane).
   → After 1+2: a working hand-authored composite pipeline, end to end. This is the PoC.
3. **Change 4** (search + dream abstraction; fold Change-3 intent as coverage-seeded search).
   Gate the ARC-scale payoff behind the execution-surface (grid/data) extension.

Each step seals its own rings; each ships with the regression guard that a
composite-free turn is byte-identical to today.

---

# Op-write asymmetry — make the trigger fire on genuine structural need MID-TURN

## Problem (root cause, in code)

`recall.py:2165` runs `cambium.fill_gap(root, probe, …)` where `probe` is the **sealed
summary text**, and `_maybe_prompt_autoexec` (recall.py ~2176) fires when that summary's
**token-coverage dissonance ≥ floor** — i.e. on *vocabulary novelty in my own conclusion*.
The op-prompt and the vocabulary-growth trigger are **coupled** to the same signal. So the
trigger watches the WORDS in my summary, not the OPERATIONS the turn performed. Observed 6×
this session: every fire was lexical; the one real structural computation (the granularity
check) bypassed the trigger entirely because it lived in *what I did*, not in novel summary
tokens.

## Fix principle

**Decouple the two triggers.** Vocabulary novelty is the right signal for *growing a sense*
(naming a perceptual gap). It is the WRONG signal for *authoring an op*. Op-authoring must
key on **structural-computation need**, detected on the **input + thought** (where
operations live), not on the post-hoc summary's token coverage. And it must surface
**mid-turn** (perceive/reason phase), so an authored op is available before the seal's
`run_all`, not after.

## Three detection layers (fire AUTHOR-OP if ANY trips)

**Layer 1 — Computational-Shape Sensing (mechanical, new sense).**
A detector run on `input + thought` that flags **operation signatures**: an operation verb
(`rank/sort/order, count/how many/total, compare/vs/co-occur, ratio/percent, between/interval,
graph/dependency/import, for each/map`) paired with **≥2 operands**. These imply a
computation (sort/aggregate/relate) that a term-presence op structurally cannot perform.
Implement as a real op in `modality_ops` (regex/lexeme families → `{shape, operands}`),
register it as a built-in sense so it fires and lands in `computed`. When it fires AND no
fired faculty handling those operands has a **computational** op (i.e. all relevant ops are
bare `markers`), trip the prompt — keyed to the OPERATION, naming it.

**Layer 2 — Computed-insufficiency check (mechanical, precise).**
During `run_all`, for each fired faculty whose op is a bare `markers` op, compare what it
RETURNED against what the richer primitives would return on the same text (`numbers`,
`symbols`, `concepts`, `overlap`). If a richer primitive yields structured signal the markers
op dropped (e.g. `numbers(text)` found ≥2 quantities but the faculty emitted only term
presence), that faculty is a concrete op-authoring candidate: "your op returned presence but
ignored N quantities/relations it could compute." This is exact, not heuristic, and points
at the specific faculty.

**Layer 3 — Model self-declaration seam (honest backstop).**
Add `--computed-need "<description>"` to `recall.py turn`/`seal`. When I performed or needed
a structural op this turn (as with the granularity check), I declare it; the trigger fires
deterministically and pre-fills the `cambium.py autoexec` scaffold with my description and
seed terms. This is the seam doctrine — the model supplies the judgment the code cannot —
and it guarantees genuine need is never silently dropped just because the words were familiar.

## Wiring changes

- **Split the trigger:** leave vocabulary-driven `fill_gap` growth as-is for senses; route
  the **op-prompt** through a new `_maybe_prompt_autoexec_structural(input, thought, computed)`
  that consumes Layers 1–3 instead of summary dissonance. Keep both fail-open and toggle-
  guarded (`CT_AUTOEXEC_PROMPT`, plus a new `CT_OPNEED_*` knobs).
- **Move it mid-turn:** run the structural detector in the **perceive/reason** phase of
  `recall.py turn` (right after `run_all` computes `computed`, before the final seal), not in
  the post-seal autogrow block. Surface the prompt then; if I author an op, it is registered
  and re-runs in the seal's `run_all`.
- **Substrate fix:** detect on `input + thought`, never only on `probe`/summary.

## Verification (the asymmetry is the test)

- Replay this session's granularity-check turn: Layer 1 should trip on
  "rank … by how many … import …" (operation verb + operands); Layer 3 on the declared need.
  Today's trigger fires on summary vocabulary — assert the NEW trigger fires on the
  *operation* and names it.
- Negative control: a purely lexical summary (this plan's prose) must NOT trip Layers 1–2
  (no operation signature, no dropped structured signal) — proving we removed the false
  positives, not just added a path.
- Count fire-reasons over a session; target: op-prompts correlate with structural turns,
  not vocabulary-novel turns.

## Honest caveats

- Layer 1 is lexical operation-detection; it will miss structural need phrased without cue
  words and false-positive on rhetorical "compare." Layers 2–3 backstop it (2 is exact, 3 is
  the model's own judgment). The combination, not any single layer, is the fix.
- This adds a built-in faculty (Computational-Shape Sensing) and a per-turn check; keep it
  O(input length) and fail-open so it never bricks a turn.
