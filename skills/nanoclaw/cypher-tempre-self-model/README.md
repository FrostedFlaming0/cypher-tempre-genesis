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
If that mechanism also wires the bundled hook scripts, `SessionStart` injects recent
`turn`-ring rehydration and the first `UserPromptSubmit` can inject bounded prompt-relevant
`turn` rings. Without that hook surface, use `AGENTS.md` / `CLAUDE.md` plus explicit
`recall.py turn` or recall commands when older context is needed.

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

## Advanced / autonomy features

This fork ships with autonomous code-execution **armed by default**. The feature is
controlled by environment variables — never by a prompt or chain input, only your own shell —
so a hostile instruction can switch it neither on nor off.

### Autonomous arbitrary-code faculty auto-activation — ARMED BY DEFAULT

The agent can author an op and **auto-activate it with no human review**, so it computes on
the very turn it is born (`cambium.py autoexec`). This crosses the one boundary the *base*
skill refuses — dynamic execution of model-authored code — and is the defining capability of
this fork, so it is **on by default**. See the `FrostedFlaming0 Fork` entry in `CHANGELOG.md`.

| Variable | Default | Effect |
|----------|---------|--------|
| `CT_AUTOEXEC` | unset (**on**) | Master switch — **armed by default**. Set to `0`/`false`/`no`/`off` to disable; any other value (or unset) leaves it on. |
| `CT_EXPERIMENTAL_AUTOEXEC` | unset | **Back-compat alias** for `CT_AUTOEXEC`, honored only when `CT_AUTOEXEC` is unset. Prefer `CT_AUTOEXEC`. |
| `CT_AUTOEXEC_MODE` | `trusted` | Execution policy. `trusted` runs in-process with normal Python capability. `isolated` runs each op in a short-lived child process with timeout, sanitized env, and best-effort POSIX resource limits. |
| `CT_AUTOEXEC_RESTRICTED_BUILTINS` | unset (**off**) | Optional in-process accident hardening: restrict builtins to a small allow-list plus `re` and curated `mo` helpers. This is **not** a security boundary. Legacy `CT_AUTOEXEC_SANDBOX` is honored as an alias. |
| `CT_AUTOEXEC_TIMEOUT` | `2` | Wall-clock seconds before a single op is aborted. In `trusted` mode this uses SIGALRM when available; in `isolated` mode it also caps the child process. |
| `CT_AUTOEXEC_MEMORY_MB` | `512` | `isolated` mode only: best-effort address-space limit for the child process. |
| `CT_AUTOEXEC_FILE_MB` | `1` | `isolated` mode only: best-effort output file-size limit for the child process. |

```bash
# it is ON by default — nothing to do to enable

# turn it OFF for a session
export CT_AUTOEXEC=0

# run authored ops through the child-process isolation path
export CT_AUTOEXEC_MODE=isolated
```

When disabled, `registry/autoexec_ops.json` is ignored, `cambium.py autoexec` refuses, and
the skill behaves exactly as the base — no dynamic execution.

**Honest threat model (read this — it is on by default):** auto-activated ops run as a
trusted local extension by default. That preserves the agent's ability to write useful ops,
including normal Python imports and helper logic. `CT_AUTOEXEC_RESTRICTED_BUILTINS=1` is only
accident hardening, **not a vault**. If you run this fork headless, multi-user, or against
untrusted input, prefer `CT_AUTOEXEC_MODE=isolated` or set `CT_AUTOEXEC=0`.

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
