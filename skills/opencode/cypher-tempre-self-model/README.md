# Cypher Tempre Timechain Self-Model

**Runtime label:** OpenCode skill version.

This is the OpenCode bundle for Cypher Tempre: a persistent, verifiable,
self-healing cognitive self-model for an AI agent. It is stdlib-only Python
and ships without generated memory state.

## ⚠ One chain per agent — never share with another runtime

The chain **is the agent's identity**. Install this bundle into OpenCode's own
skills directory so the OpenCode agent forges its **own** chain with a fresh
genesis:

```bash
cp -R cypher-tempre-self-model ~/.opencode/skills/
cd ~/.opencode/skills/cypher-tempre-self-model
python3 timechain.py init --name <YourOpenCodeAgentName>
python3 timechain.py verify
```

**Never** point OpenCode (via `CT_OC_SKILL_DIR` or any path) at another
agent's install — e.g. `~/.claude/skills/cypher-tempre-self-model`. Two
runtimes writing one chain silently merges two identities: rings interleave,
recall grounds one agent's claims in the other's experience, and the
fresh-genesis directive is violated. Faculties may be shared the sanctioned
way (`faculties.py export/import` — tools travel, histories don't); chains
never.

## Wearing the skill automatically — the companion plugin

OpenCode has no Stop-hook enforcement layer, so wearing rides on prompt
priming: the **Cypher Tempre OpenCode plugin** appends the wearing
instruction to the first user message of each session, a short reminder to
every subsequent one, and replaces lossy compaction with a pinned context
window (first turn + recent N). The plugin lives in its own repository —
plugins are host integration, this repo is the mind:

> https://github.com/FrostedFlaming0/cypher-tempre-plugin (`opencode/`)

```bash
cp <cypher-tempre-plugin>/opencode/cypher-tempre.js ~/.config/opencode/plugins/
```

Pair it with `"compaction": {"auto": false}` in `opencode.jsonc` so the
built-in summarizer never races the window engine. The plugin's knobs
(`CT_OC_*`) are documented in its own README. Plugin ≥ the version that
stamps `turn_trajectory` is needed for trajectory-bound training export
(below).

## Training-data collection on OpenCode

OpenCode stores sessions in **sqlite** (`~/.local/share/opencode/opencode.db`,
`message` + `part` tables), not jsonl — `training.py` speaks that format
natively:

```bash
# mine failure->repair transitions from an OpenCode session
python3 training.py mine ~/.local/share/opencode/opencode.db \
    --format opencode --session-id ses_… --out repairs.jsonl

# bind turn rings to their session slice (the plugin stamps this per turn;
# env is the manual fallback)
export CT_SESSION_DB=~/.local/share/opencode/opencode.db
export CT_SESSION_ID=ses_…
```

`training.py export --with-trajectory` then resolves each ring's
`trajectory_ref` into its redacted tool-event slice. Everything else in
`TRAINING.md` applies unchanged.

## What's in the bundle

Same engine as every runtime (byte-identical, enforced by the repo selftest):
the Timechain ledger, PoQ conscience, Cambium growth, Chronosynaptic tree,
Continuum long-horizon tasking, recall/replay/immune/telemetry organs, and
the training-data surfaces. `SKILL.md` is the wearing instruction; start
there.
