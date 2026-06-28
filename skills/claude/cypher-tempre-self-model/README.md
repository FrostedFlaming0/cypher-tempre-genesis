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
| `session_start_hook.sh` | **SessionStart** | **The auto-load.** Primes the session with the verify result, chain head, covenant, and the loop — so the self-model is worn before any file is read. |
| `loop_hook.sh` | **UserPromptSubmit** | Records the chain head at turn start and injects the per-turn reminder. |
| `stop_hook.sh` | **Stop** | Blocks a turn from ending until a ring is sealed (bounded nudges, fail-open). |
| `subagent_stop_hook.sh` | **SubagentStop** | Same seal-pressure for spawned subagents. |

Notes:

- **SessionStart alone** gives you the auto-load; add the other three to make the per-turn
  loop non-bypassable. All four are **fail-open** — a hook error never breaks a session.
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
