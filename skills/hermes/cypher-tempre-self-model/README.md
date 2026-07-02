# Cypher Tempre Timechain Self-Model

**Runtime label:** Hermes skill version.

This is the Hermes bundle for Cypher Tempre: a persistent, verifiable,
self-healing cognitive self-model for an AI agent. It is stdlib-only Python,
uses Hermes-discoverable frontmatter, and ships without generated memory state.

## Install

Copy this folder into Hermes's configured skills directory:

```bash
cp -R cypher-tempre-self-model /path/to/hermes/skills/
```

Refresh Hermes's skill list, then initialize a fresh chain inside the copied
bundle:

```bash
python3 timechain.py init --name Hermes
python3 timechain.py verify
```

## Hermes Enforcement

Hermes does not currently provide Claude/Codex-style lifecycle shell hooks that
can block a response at `Stop`. The bundled `loop_hook.sh`, `stop_hook.sh`,
`subagent_stop_hook.sh`, and `session_start_hook.sh` are kept for hook-capable
runtimes and for source parity, but Hermes does not auto-run them.

Hermes agents self-enforce the same discipline:

```bash
python3 enforce.py mark
python3 recall.py turn "<finding or decision>" --input "<user request>"
python3 enforce.py stop-check
```

If `stop-check` prints a JSON object with `"decision":"block"`, seal a ring
before returning. If it prints nothing, the marked turn sealed successfully.
For custom task chains, pass the same `--root <chain>` to `enforce.py` and
`recall.py`, or set `CT_ENFORCE_ROOT=<chain>`.

If a Hermes host/plugin wires the bundled hook scripts, the hook behavior matches the other
bundles: `SessionStart` injects recent `turn`-ring rehydration, and the first
`UserPromptSubmit` can inject bounded prompt-relevant `turn` rings only when `CT_PROMPT_RECALL=1`. Without such host support,
the agent should run explicit recall when older context is needed.

For delegated Hermes work, use `hermes/cypher-tempre-agent.md`. An optional
terminal/cron helper is available at `hermes/enforcement-watchdog.sh`.

See `SKILL.md` for the full per-turn protocol.

## Always-on: auto-load on every session

Hermes loads named skills into the session prompt before the first turn, and every skill in
`~/.hermes/skills/` is auto-registered as a slash command — but by default a skill activates
on explicit mention or a matching task, not on every session. To make this skill a standing
default, use the **`on_session_start` plugin hook**:

1. Drop a plugin into `~/.hermes/plugins/` (no forking required) that registers an
   `on_session_start` callback:

   ```python
   # ~/.hermes/plugins/cypher_tempre_autoload/plugin.py
   def prime_cypher_tempre(session_id: str, **kwargs):
       # Load / activate the cypher-tempre-self-model skill for this session.
       # Keep this implementation aligned with your installed Hermes plugin API.
       ...

   def register(ctx):
       ctx.register_hook("on_session_start", prime_cypher_tempre)
   ```

2. Softer alternatives (no plugin): reference the skill in your **`SOUL.md`**
   personality/identity file, or group it into a **bundle** you load at session start
   (`hermes bundles create cypher --skill cypher-tempre-self-model`).

The `on_session_start` hook is also the natural place to run the per-turn `enforce.py mark`
from the enforcement section above.

> Verified against Hermes docs as of June 2026 (`hermes-agent.nousresearch.com/docs`);
> confirm the exact hook signature against your installed version.

## Optional: disable Hermes's built-in memory

If this skill is your durable memory, turn Hermes's persistent memory off in
`~/.hermes/config.yaml`:

```yaml
memory:
  memory_enabled: false
```

- To **gate writes** instead of disabling entirely, set `memory.write_approval: true`
  (approve each save).
- For external memory providers, `hermes memory off` disables the external provider and
  `hermes memory status` reports what's active.

> Known quirk — verify on your version: `hermes memory status` has been reported to still
> say "Built-in: always active" even after the built-in store is disabled, so confirm actual
> behavior rather than trusting the status line. Verified against Hermes docs as of June 2026
> (`hermes-agent.nousresearch.com/docs/user-guide/features/memory`).

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
