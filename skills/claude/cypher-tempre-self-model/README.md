# Cypher Tempre Timechain Self-Model

**Runtime label:** Claude skill version.

This is the Claude Code bundle for Cypher Tempre: a persistent, verifiable,
self-healing cognitive self-model for an AI agent. It is stdlib-only Python and
ships without generated memory state.

## Install

Copy this folder into Claude Code's skills directory:

```bash
cp -R cypher-tempre-self-model ~/.claude/skills/
```

Start a new Claude Code session so the skill list refreshes. Initialize a fresh
chain inside the copied bundle:

```bash
python3 timechain.py init --name Claude
python3 timechain.py verify
```

See `SKILL.md` for the full per-turn protocol.

## Always-on: auto-load on every session

By default you have to invoke the skill each session (e.g. "use the
cypher-tempre-self-model skill"). To wear the self-model **automatically from turn 0 of
every fresh session** — with no manual prompt — wire the bundled hooks into Claude Code's
`settings.json`. The scripts ship in this folder; they are just not registered until you
add a `hooks` block.

Add this to `~/.claude/settings.json` (global — applies to every project) or to a
project's `.claude/settings.json` (that repo only). Merge it alongside any keys you
already have; **replace `/home/you` with your real home path**:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "/home/you/.claude/skills/cypher-tempre-self-model/session_start_hook.sh" } ] }
    ],
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "/home/you/.claude/skills/cypher-tempre-self-model/loop_hook.sh" } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "/home/you/.claude/skills/cypher-tempre-self-model/stop_hook.sh" } ] }
    ],
    "SubagentStop": [
      { "hooks": [ { "type": "command", "command": "/home/you/.claude/skills/cypher-tempre-self-model/subagent_stop_hook.sh" } ] }
    ]
  }
}
```

What each hook does:

| Hook | Event | Role |
|------|-------|------|
| `session_start_hook.sh` | **SessionStart** | **The auto-load.** Primes the session with the verify result, chain head, covenant, loop, and recent `turn`-ring memory — so the self-model is worn and rehydrated before any file is read. |
| `loop_hook.sh` | **UserPromptSubmit** | Records the chain head at turn start, injects the per-turn reminder, and can inject bounded prompt-relevant `turn` rings only when `CT_PROMPT_RECALL=1`. |
| `stop_hook.sh` | **Stop** | Blocks a turn from ending until a ring is sealed (bounded nudges, fail-open). |
| `subagent_stop_hook.sh` | **SubagentStop** | Same seal-pressure for spawned subagents. |

Notes:

- **SessionStart alone** gives you the auto-load; add the other three to make the per-turn
  loop non-bypassable. All four are **fail-open** — a hook error never breaks a session.
- Rehydration is deliberately bounded. SessionStart injects recent `turn` rings only.
  UserPromptSubmit prompt-relevant `turn` recall is off by default because the loop already
  recalls relevant rings. Enable it with `CT_PROMPT_RECALL=1`; when enabled it injects only
  once per session by default. Tune with
  `CT_PROMPT_RECALL_TOP_K`, `CT_PROMPT_RECALL_SCAN_LIMIT`, and `CT_PROMPT_RECALL_MAX_CHARS`;
  enable with `CT_PROMPT_RECALL=1`. Use `CT_PROMPT_RECALL_EVERY_TURN=1` only in a runtime
  that gives the model fresh context every turn.
- After editing `settings.json`, **start a new session** for the hooks to take effect
  (validate the file with `python3 -m json.tool ~/.claude/settings.json`).
- To rest the loop for a throwaway session, the hooks honor dormancy: run
  `python3 dormancy.py pause --confirm` and all enforcement goes quiet until you `resume`.
- Set `CT_ENFORCE_DEBUG=1` to surface hook warnings/tracebacks on stderr when diagnosing;
  the decision JSON on stdout stays clean regardless.

## Optional: disable Claude Code's built-in auto-memory

If you let this skill be your durable memory, Claude Code's own **auto-memory** feature is
redundant — it maintains a *separate*, unverified memory store alongside the hash-chained
ledger this skill seals. Running both means two memories that can drift apart, with only one
of them tamper-evident. To make the Timechain your single source of truth, turn auto-memory
off.

Add this key to `~/.claude/settings.json` (global) — it sits alongside the `hooks` block
above:

```json
{
  "autoMemoryEnabled": false
}
```

What it does, and the caveats (verified):

- When `false`, Claude **neither reads from nor writes to** the auto-memory store — it stops
  *both* recording new memories *and* surfacing existing ones into context.
- There is **no "Memory" permission to deny** — this settings key is the lever. An env-var
  alternative, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, takes precedence if you prefer setting it
  in your shell profile; the settings key is cleaner.
- Takes effect on the **next session** (no documented mid-session hot-reload) — the current
  session keeps whatever memory it already loaded until you restart.
- Your existing `memory/` files are **left on disk**; the setting governs read/write, not
  deletion. Remove that directory by hand if you also want the old store gone.

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
