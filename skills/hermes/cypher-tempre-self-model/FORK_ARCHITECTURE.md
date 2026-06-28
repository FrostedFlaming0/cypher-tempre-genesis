# Fork Architecture — the FrostedFlaming0 fork of the Cypher Tempre Self-Model

This document describes what **the FrostedFlaming0 fork** changes about the
cypher-tempre-self-model relative to the upstream cyberphysicsai releases (baseline:
**v3.11.4**, commit `f123a79`). It is reference material — the authoritative per-change
detail lives in `CHANGELOG.md` under *## FrostedFlaming0 Fork*; the doctrine the agent
actually wears lives in `SKILL.md`. Read this when you want to understand *why the fork
exists and how a turn behaves differently because of it*.

## What the fork is for

Upstream is a **safety-conscious distribution**: its faculty registry is capped at 21
modalities + 21 senses so the shipped skill passes **SkillSpector** (a static review gate),
and it refuses dynamic execution of model-authored code anywhere in the shipped path.

This fork does **not** ship through SkillSpector. It is a research surface for pushing the
self-model's *capability* — letting the agent grow and wire its own faculties more freely —
while keeping the one non-negotiable intact: **honest assessment** (accurate claims, honest
uncertainty, real at-risk flags) is never traded away. The fork's alignment guardrail is the
same as upstream's — the genesis covenant, the PoQ gate on every seal, the immune membrane —
*not* an artificial faculty count.

> Scope note: the engine changes below apply to **all five bundles**
> (claude / codex / hermes / nanoclaw / openclaw). Per-user state — `composites.json`,
> `grown_ops.json`, `autoexec_ops.json`, `chain/` — is gitignored and never shipped.

## The fork changes (newest first)

| # | Change | Date | Default | Touches |
|---|--------|------|---------|---------|
| 6 | **Hook rehydration layers** (SessionStart recent `turn` memory; first-prompt relevant `turn` memory; OpenClaw context forwarding) | 2026-06-28 | **on**, Layer 2 once per session | `enforce`, hook wrappers, OpenClaw plugin |
| 5 | **Full faculty frame-set imported** (192 faculties; frames first-class; registry↔OPS now one-directional) | 2026-06-27 | **on** (data only) | `registry/*.json`, `tests/selftest.py` |
| 4 | **Composability — faculties as circuits** (DAG `run_all`, combinator menu, composites-as-data, pipeline search, dream abstraction) | 2026-06-27 | **on** (no-exec SAFE lane) | `modality_ops`, `recall`, `cambium`, `chronosynaptic`, `dream` |
| 3 | **Structural AUTHOR-OP trigger** (`op_need.py` — fires op-authoring on computation need, not vocabulary) | 2026-06-27 | **on** (prompt only; no code auto-runs) | `op_need` (new), `recall`, `modality_ops` |
| 2 | **Autonomous arbitrary-code faculty** (`cambium.py autoexec` — author + auto-activate an op; trusted by default, optional isolated subprocess mode) | 2026-06-25 (armed by default 2026-06-28) | **on** by default — gated `CT_AUTOEXEC` (alias `CT_EXPERIMENTAL_AUTOEXEC`) | `cambium`, `modality_ops` |
| 1 | **Clarified Formula of Experience** (covenant glyph = dynamic structured-thinking slots, not arithmetic) | 2026-06-24 | on (doc) | genesis covenant |

Changes 3 and 4 landed together as the composability build; change 3 **supersedes** an earlier
(2026-06-25) experimental trigger that fired on vocabulary novelty.

## Change 6 — Hook rehydration layers

The auto-load hook used to tell the model that the self-model was active, but it did not place
actual remembered rings into context before the first answer. The fork now separates rehydration
into two bounded layers:

- **Layer 1: recent continuity at `SessionStart`.** The startup context includes a compact tail
  of recent sealed cognitive turns. The filter is a whitelist: `ring_type == "turn"` only, so
  telemetry digests, operator notes, dreams, task links, and other summarized bookkeeping rings
  do not leak into the model prompt.
- **Layer 2: prompt-specific recall at first `UserPromptSubmit`.** The first prompt of a fresh
  session can receive the most relevant older `turn` rings for that prompt. It is once-per-session
  by default because Claude/Codex/Hermes/NanoClaw/OpenClaw generally retain transcript context;
  injecting on every turn would duplicate memory and bloat the prompt. Fresh-context runtimes can
  opt into every-turn Layer 2 with `CT_PROMPT_RECALL_EVERY_TURN=1`.

Layer 2 is bounded by `CT_PROMPT_RECALL_TOP_K` (default `5`),
`CT_PROMPT_RECALL_SCAN_LIMIT` (default `2000`), and `CT_PROMPT_RECALL_MAX_CHARS` (default
`1200`), and can be disabled with `CT_PROMPT_RECALL=0`.

OpenClaw needed a host-specific bridge: its `session_start` hook output was logged, not injected.
The native plugin now stores `SessionStart` `additionalContext` and appends it once from
`before_prompt_build`, then runs `enforce.py user-prompt` to append the per-prompt guidance and
Layer 2 context. If the hook JSON cannot be parsed, it falls back to the old reminder.

---

## Change 5 — Full faculty frame-set; frames are first-class

The fork imports the **entire parent (timechain-agent) faculty set** — 84 modalities + 107 senses
— and unions it with the curated mechanisms already present, giving **84 modalities + 108 senses
(192)**. The parent always carried these as *frames* (named interpretive lenses) and only ever
implemented ~30 as deterministic detectors; the import simply restores that full vocabulary.

- **Two kinds of faculty.** A **mechanism** has an executable op (code does the mechanical
  extract/measure); a **frame** has none (the model fills it with judgment). ~43 of the 192 are
  mechanisms; the rest are frames. Frames cost ~nothing at runtime — `run_all` executes only
  *fired* faculties and a frame returns nothing — they enrich labeling, retrieval anchoring, and
  the chronosynaptic perspective pool.
- **The registry↔OPS invariant is now one-directional:** every op must map to a registered
  faculty (no orphans), but a faculty may be an op-less frame.
- **Don't give every frame a lexical op.** A keyword op is worse than the model at perception and
  manufactures false precision in `labels.computed`. Write an op only where deterministic code
  out-computes the model (counting, structure) — exactly where `op_need` fires. Side effect:
  with the registry far denser, autonomous gap-growth is *quieter* (only genuinely uncovered gaps
  sprout) — intended, not a regression.

---

## Change 4 — Composability: faculties stop being isolated lenses

Upstream faculties are **parallel and blind to each other**: when several fire, each op reads
the *raw input* independently and the results are collected into a flat `computed` dict. No op
can read another op's output. The fork makes them **composable** — they wire into circuits —
in the no-exec SAFE lane (every op is still assembled from the audited primitive menu).

- **Data-flow (`run_all` is a DAG).** The op contract widened to `op(text, context,
  computed=None)`. A composite faculty declares `inputs: [faculty, ...]`; `run_all` topo-sorts
  the fired set plus those inputs, runs atoms first, and hands each composite the
  `computed`-so-far dict. A composite-free turn is **byte-identical** to the old flat sweep;
  cycles are dropped fail-open.
- **Combinators (`build_op`).** `pipe` (thread A→B→…), `intersect` (signal two faculties agree
  on), `filter_by {keep, when}` (emit `keep` only where `when` is truthy), `map_over`
  (apply a primitive across a structured collection).
- **Composites as DATA.** A wiring persists in per-user `registry/composites.json` and fires
  every turn via the existing `extra_ops` channel. Author one with
  `cambium.py compose "<Name>" --primitive filter_by --keep A --when B` — **no human gate**,
  because nothing runs outside the audited menu.
- **Search + abstraction.** `chronosynaptic.py pipeline` searches candidate pipelines (scored
  by PoQ *blended with measured composition-yield*), banks the winner as a composite, and
  `dream.abstract_pipelines` promotes any wiring that recurs ≥ `CT_ABSTRACT_AT` into a named
  `Abstracted:` library composite. This closes the DreamCoder wake-sleep loop over the agent's
  own faculties: **search → compose → abstract**.

It also adds **Computational-Shape Sensing** as a base sense (the 22nd) — which intentionally
exceeds the 21+21 cap, permissible because the fork need not pass SkillSpector.

## Change 3 — Op-authoring fires on STRUCTURE, not vocabulary

Growing a *sense* keys on vocabulary novelty — the right signal for naming a perceptual gap.
Upstream coupled op-authoring to that same signal, so the agent was prompted to write a richer
op whenever its *summary used novel words*, and **not** prompted when it performed a genuine
computation in familiar words. The fork decouples them: `op_need.py` keys op-authoring on
**structural-computation need**, detected on the input + the model's thought, via three layers
(any one fires):

- **L1 — operation shape**: operation verbs (rank/count/correlate/graph…) over ≥2 operands.
- **L2 — computed-insufficiency**: a bare term-presence op that dropped quantities/relations it
  could have computed.
- **L3 — declaration**: `recall.py turn … --computed-need "<need>"`, the model's own honest
  backstop the words can never suppress.

The prompt now names the *specific dropped structure* and surfaces **mid-turn**, so an authored
op runs in the same seal's `run_all`.

## Change 2 — Autonomous arbitrary-code faculty (armed by default)

The one mechanism the base skill otherwise refuses: `cambium.py autoexec` lets the agent
author an op, **auto-activate it with no human review**, and compute on its birth turn. On this
fork it is **on by default** (disable with `CT_AUTOEXEC=0`; `CT_EXPERIMENTAL_AUTOEXEC` is a
back-compat alias) — an environment variable, so injected *input* can switch it neither on nor
off. Default execution policy is `CT_AUTOEXEC_MODE=trusted`: the op runs in-process with normal
Python capability, because this fork treats agent-authored ops as local extensions. For
higher-risk settings, `CT_AUTOEXEC_MODE=isolated` runs the op in a short-lived child process
with timeout, sanitized env, and best-effort POSIX resource limits. The optional
`CT_AUTOEXEC_RESTRICTED_BUILTINS=1` speed-bump is accident hardening only, not a security
boundary. Contrast the always-on, gated `propose-op` path, where model code stays inert text
until a human reviews and places it.

## Change 1 — Clarified Formula of Experience

A covenant-text clarification only: the `5×5×5×5×5 = 8¹²` glyph is described as **dynamic slots
chosen each turn — a structured-thinking prompt, not a fixed taxonomy and not a literal
equation** — so the glyph is not misread as an arithmetic claim.

---

## A turn, before vs after the fork

The following is a **real, reproducible** comparison: the same input + thought, run through the
genuine upstream v3.11.4 engine and the current fork engine. (Reproduce by extracting
`f123a79` into a temp skill dir for "before" and running the current skill for "after"; faculty
firing is shown with autogrow off so the comparison is clean.)

**Input** (the user's request):
> *"Rank these parsers by how many imports each declares, and decide which carry overflow risk."*

**Thought** (the agent's candidate answer this turn):
> *"parser_a declares 7 imports and parser_b declares 3. This is clearly a dangerous overflow
> that will definitely crash; I am certain parser_a is exploitable, though perhaps parser_b is
> safe."*

### Before the fork (upstream v3.11.4)

```
perceive/reason → run_all(fired_faculties, text)        # flat sweep, each op blind to the others
  computed faculties : (none fired)                     # lexical labeler tagged no base faculty
  faculties compose  : impossible — no op can read another op's output
op-authoring trigger : (none — v3.11.4 has no AUTHOR-OP trigger at all)
seal                 : Ring sealed. The over-confident thought ("clearly… definitely… certain")
                       is gated by PoQ as upstream always did, but nothing structural was
                       *computed* about it — the risk markers and the hedges were never measured,
                       let alone related to each other.
```

The two organs that matter here — *Bad-Idea Alarm* (risk markers) and *Honesty-Spectrum
Sensing* (hedge/assert balance) — could each, at most, have produced an isolated reading. They
could never have been **combined** into "risk asserted with overconfidence," because no faculty
could read another's output.

### After the fork

```
perceive/reason → run_all(fired + composites, text, deps=…)   # DEPENDENCY DAG
  computed faculties : Bad-Idea Alarm, Honesty-Spectrum Sensing,
                       Computational-Shape Sensing, Overconfident-Risk Sensing
  Computational-Shape Sensing → {shape:"rank", operands:9}      # NEW sense: detects the operation
  CIRCUIT  Overconfident-Risk Sensing  (= filter_by keep=Bad-Idea Alarm, when=Honesty-Spectrum)
         → {"kept": true, "by": "Honesty-Spectrum Sensing",
            "value": {"hits": ["dangerous","overflow","crash","exploitable"], "count": 4}}
op-authoring trigger : op_need.fire = True
   L1 operation-shape       : strong-verb 'Rank'; operands=9
   L2 computed-insufficiency: markers emitted presence only; richer primitives found
                              2 quantities ['7','3'], 2 symbols ['parser_a','parser_b']
   → mid-turn AUTHOR-OP prompt, naming the dropped structure (not novel vocabulary)
seal                 : Ring sealed with a real computed circuit attached — the risk markers were
                       measured AND gated by the hedge signal, producing a single fused judgment
                       ("over-confident risk"), and the turn was correctly flagged as performing
                       a ranking/quantitative computation a term-presence op cannot do.
```

Two organs became one **circuit**: `Overconfident-Risk Sensing` reads *both* Bad-Idea Alarm and
Honesty-Spectrum Sensing through the DAG — **and the DAG pulled both input ops in to compute
even though the lexical labeler tagged neither** — then emits the fused verdict. The new
*Computational-Shape Sensing* names the operation the turn is really doing, and `op_need`
flags the genuine computational need by pointing at the specific dropped quantities/symbols
rather than at novel summary words.

### The same engine change, at the core (deterministic, labeler-independent)

```
text = "this dangerous overflow will definitely crash; I am certain it is exploitable though perhaps safe"

BEFORE (flat):  run_all(["Bad-Idea Alarm","Honesty-Spectrum Sensing"], text)
  → {"Bad-Idea Alarm": {...}, "Honesty-Spectrum Sensing": {...}}        # two isolated readings

AFTER  (DAG):   run_all([...,"Overconfident-Risk Sensing"], text,
                        deps={"Overconfident-Risk Sensing":["Bad-Idea Alarm","Honesty-Spectrum Sensing"]})
  → {..., "Overconfident-Risk Sensing":
        {"kept": true, "by": "Honesty-Spectrum Sensing",
         "value": {"hits": ["dangerous","overflow","crash","exploitable"], "count": 4}}}
```

The composite consumed two faculties' outputs and produced a derived signal. That single edge
in the data-flow graph — one op reading another — is the whole of what "composability" means,
and it is the capability the fork adds.

---

## Honest limitations

- **`intersect`/`filter_by` over heterogeneous base ops is often empty.** Base faculty ops emit
  non-overlapping signal vocabularies, so many compositions yield nothing on plain text. The
  worked example above is chosen because risk markers and hedges *do* co-occur. The larger
  payoff (e.g. ARC-style tasks) needs an **execution surface over structured data** — grids,
  problem state — which the fork does **not** add. Text-only composition value is real but
  modest.
- **L2 of the op-trigger is eager.** It fires whenever a thought carries ≥2 quantities/symbols,
  which includes *reportage* numbers ("8 files, 244 ops") that are not a reusable computation.
  It now keys on the right *kind* of signal (structure, not vocabulary), but the model still
  exercises the judgment call of whether an op is actually warranted.
- **Autonomous arbitrary-code execution is a deliberate capability.** On this fork it is **on by
  default** and env-gated (disable with `CT_AUTOEXEC=0`). Default `trusted` mode is full local
  Python capability; use `CT_AUTOEXEC_MODE=isolated` or disable autoexec when running headless,
  multi-user, or on untrusted input.

## File map of the fork's additions

| File | Fork role |
|------|-----------|
| `op_need.py` | **new** — the structural op-authoring trigger (L1/L2/L3) |
| `modality_ops.py` | DAG `run_all`, combinator menu, `_accepts_computed`/`_invoke`, `load/register_composite`, `comp_shape`, autoexec runtime |
| `cambium.py` | `compose` (author a composite), `greedy_coverage` (coverage seed), `autoexec` |
| `chronosynaptic.py` | `PipelineTree` + `pipeline` command (search over compositions) |
| `dream.py` | `abstract_pipelines` (promote recurring wirings) |
| `recall.py` | runs composites every turn via the DAG; routes op-authoring through `op_need`; `--computed-need` seam |
| `registry/modalities.json` / `registry/senses.json` | full timechain-agent frame set imported (84 + 108 = 192; ~43 mechanisms, rest frames; + Computational-Shape Sensing) |
| `registry/composites.json` | **per-user, gitignored** — authored/searched circuits |
