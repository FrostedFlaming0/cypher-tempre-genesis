# Cypher Tempre Timechain Self-Model

**Runtime label:** NanoClaw skill version.

This is the NanoClaw bundle for Cypher Tempre: a persistent, verifiable,
self-healing cognitive self-model for an AI agent. It is stdlib-only Python,
uses NanoClaw-discoverable frontmatter, and ships without generated memory state.

## Install

Copy this folder into NanoClaw's configured workspace skills directory:

```bash
cp -R cypher-tempre-self-model /path/to/nanoclaw/skills/
```

Refresh NanoClaw's skill list, then initialize a fresh chain inside the copied
bundle:

```bash
python3 timechain.py init --name NanoClaw
python3 timechain.py verify
```

See `SKILL.md` for the full per-turn protocol.

## Always-on: auto-load on every session

NanoClaw has two skill surfaces:

- **Host skills** in `.claude/skills/` are Claude Code workflows that you invoke as slash
  commands from the NanoClaw checkout. As of this writing, NanoClaw does **not** document a
  dedicated always-on frontmatter field or session-start hook for these host workflows.
- **Container skills** in `container/skills/` are mounted read-only into agent containers at
  `/app/skills`. These are controlled per agent group by the container config `skills`
  field: `"all"` or a pinned list of skill names.

For a container/runtime skill, make sure the relevant group includes it in `skills`. The
default is `"all"`, so newly added container skills are picked up on the next container
spawn; if the group pins a list, add this skill name to that list. Restart the group to
force a respawn:

```bash
ncl groups config get --id <group-id>
ncl groups restart --id <group-id>
```

For behavior that must happen on every meaningful turn, also add a standing instruction to
the agent group's `CLAUDE.md`:

1. In the relevant agent group's `CLAUDE.md` (e.g. `groups/<group>/CLAUDE.md`), add a line
   such as: *"Always use the `cypher-tempre-self-model` skill on every meaningful turn — run
   its `recall.py turn` loop and seal a ring before finishing."*
2. Or run `/customize` and tell the agent to always wear the skill.

The container `skills` field controls availability. The `CLAUDE.md` instruction controls the
agent's default behavior; by itself, it is a strong nudge rather than platform enforcement.
If a future NanoClaw version adds a real always-on host-skill mechanism, prefer it.

> Based on the public NanoClaw docs/README as of June 2026. Verify against
> `reference/container-config.md`, `extend/overview.md`, or the source for your version.

## Optional: disable NanoClaw's built-in memory

NanoClaw's memory is **file-based**: per-group `CLAUDE.md` files that the Claude Agent SDK
auto-loads into the system prompt — `groups/global/CLAUDE.md` (shared across groups) and
`groups/<folder>/CLAUDE.md` (per group). Conversation history is stored separately in
`store/messages.db` and JSONL transcripts under `data/sessions/<folder>/.claude/`.

There is **no documented dedicated disable switch**. The practical approach is to keep the
`CLAUDE.md` memory files empty and instruct the agent not to write to them — which *minimizes*
memory rather than turning the subsystem off. Since the Timechain ledger is your durable
memory here, an empty `CLAUDE.md` (plus the always-on instruction above) keeps the two from
competing.

> Based on the public NanoClaw docs as of June 2026; no dedicated memory-off toggle was
> documented. Verify against the source for your version.

## Experimental features & toggles

These features are **off by default** and controlled by environment variables, so nothing
in a prompt or in chain input can switch them on — only your own shell can.

### Autonomous arbitrary-code faculty auto-activation

When enabled, the agent can author an op and **auto-activate it with no human review**, so
it computes on the very turn it is born (`cambium.py autoexec`). This crosses the one
boundary the skill otherwise refuses — dynamic execution of model-authored code — so it is
env-gated and documented as experimental. See the `FrostedFlaming0 Fork` entry in
`CHANGELOG.md`.

| Variable | Default | Effect |
|----------|---------|--------|
| `CT_EXPERIMENTAL_AUTOEXEC` | unset (**off**) | Master switch. Set to `1` (or any value other than `0`/`false`/`no`/`off`) to enable auto-activation; unset it or set `0` to disable. |
| `CT_AUTOEXEC_SANDBOX` | `1` (**on**) | Run auto-activated ops in a restricted namespace (safe builtins + `re` + curated `mo` text helpers only; no `os`/`open`/`__import__`/`eval`/`exec`). Set `0` to run with full builtins — not recommended. |
| `CT_AUTOEXEC_TIMEOUT` | `2` | Wall-clock seconds (SIGALRM) before a single op is aborted. |

```bash
# turn it ON for a session
export CT_EXPERIMENTAL_AUTOEXEC=1

# turn it OFF again (either form works)
unset CT_EXPERIMENTAL_AUTOEXEC
export CT_EXPERIMENTAL_AUTOEXEC=0
```

When off, `registry/autoexec_ops.json` is ignored, `cambium.py autoexec` refuses, and the
skill behaves exactly as the shipped base — no dynamic execution.

**Honest threat model:** the restricted namespace + timeout are a robustness and *speed-bump*
layer, not a vault. Keep this off unless you are deliberately experimenting and accept that
the agent is executing code it wrote itself.

## Data retention & third-party transmission

This skill is a **persistent memory system**. By design it records each turn — your
request and the agent's decision — into an append-only, hash-chained ledger under
`chain/` that is **never deleted** (history is immutable; that tamper-evidence is the
point). Treat it like a local journal:

- **Everything is stored locally, in cleartext.** Do not feed it secrets, credentials,
  or PII you would not want retained indefinitely. The chain is tamper-EVIDENT, not
  encrypted, and there is no built-in redaction or expiry.
- **It stays on your machine by default.** The core engine is stdlib-only and the
  default embedder is local; nothing is transmitted off-machine.
- **Optional embedding providers send text to a third party.** If you explicitly enable
  the OpenAI / Voyage / sentence-transformers backends (they need an API key or extra
  library and are OFF by default), the text being embedded — which may include memory
  chunks, source excerpts, or other chain contents — is sent to that provider. Keep the
  default local `hashing` embedder if that is a concern.
