# Cypher Tempre Timechain Self-Model

**Runtime label:** OpenClaw skill version.

This is the OpenClaw bundle for Cypher Tempre: a persistent, verifiable,
self-healing cognitive self-model for an AI agent. It is stdlib-only Python,
uses OpenClaw-compatible frontmatter, and ships without generated memory state.

## Install

Copy this folder into OpenClaw's workspace skills directory:

```bash
cp -R cypher-tempre-self-model ~/.openclaw/workspace/skills/
```

Refresh OpenClaw's skill list, then initialize a fresh chain inside the copied
bundle:

```bash
python3 timechain.py init --name OpenClaw
python3 timechain.py verify
```

## OpenClaw Enforcement

The strongest OpenClaw path is the native plugin included in this bundle. It
uses typed OpenClaw plugin hooks: `before_prompt_build` marks the turn, and
`before_agent_finalize` requests one more model pass if `enforce.py stop-check`
finds that no ring was sealed.

The plugin also forwards rehydration context into the model prompt. `session_start`
produces Layer 1 recent `turn`-ring memory, which the plugin stores and appends once
from `before_prompt_build`; `before_prompt_build` then runs `enforce.py user-prompt`
to add per-turn guidance and opt-in Layer 2 relevant-ring recall when `CT_PROMPT_RECALL=1`.
See `openclaw-plugin/README.md` for the environment knobs and fallback behavior.

```bash
openclaw plugins install ~/.openclaw/workspace/skills/cypher-tempre-self-model/openclaw-plugin
openclaw config set 'plugins.entries.cypher-tempre-enforcement.hooks.allowConversationAccess' true --strict-json
openclaw gateway restart
```

For non-bundled local installs, the config command above is required so OpenClaw
allows the `before_agent_finalize` Stop-equivalent hook. Equivalent JSON in
`~/.openclaw/openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "cypher-tempre-enforcement": {
        "enabled": true,
        "hooks": {
          "allowConversationAccess": true
        }
      }
    }
  }
}
```

If your skill is not installed at
`~/.openclaw/workspace/skills/cypher-tempre-self-model`, set
`plugins.entries.cypher-tempre-enforcement.config.skillRoot` to the installed
skill folder:

```bash
openclaw config set 'plugins.entries.cypher-tempre-enforcement.config.skillRoot' /path/to/cypher-tempre-self-model
openclaw gateway restart
```

See `openclaw-plugin/README.md`.

Fallback for runtimes where plugins are unavailable:

```bash
python3 enforce.py mark
python3 recall.py turn "<finding or decision>" --input "<user request>"
python3 enforce.py stop-check
```

If `stop-check` prints a JSON object with `"decision":"block"`, seal a ring
before returning. If it prints nothing, the marked turn sealed successfully.
For custom task chains, pass the same `--root <chain>` to `enforce.py` and
`recall.py`, or set `CT_ENFORCE_ROOT=<chain>`.

For delegated OpenClaw work, use `openclaw/cypher-tempre-agent.md` or
`agents/cypher-tempre-agent.md`. An optional terminal/cron helper is available
at `openclaw/enforcement-watchdog.sh`.

See `SKILL.md` for the full per-turn protocol.

## Always-on: auto-load on every session

OpenClaw **snapshots the eligible skills when a session starts** and reuses that list for
every turn, so marking this skill as a default makes it load automatically on each fresh
session — no per-turn action needed. Any one of these suffices:

- **Skill frontmatter (per-skill):** in this bundle's `SKILL.md` frontmatter set
  `metadata.openclaw.always: true` — OpenClaw then always includes the skill and
  skips all other gates.
- **Default-skills allowlist:** add the skill to `agents.defaults.skills` (baseline for all
  agents) or to a specific agent via `agents.list[].skills`.
- **Explicit enable:** `skills.entries.cypher-tempre-self-model.enabled: true`.

```bash
openclaw config set 'skills.entries.cypher-tempre-self-model.enabled' true --strict-json
openclaw gateway restart
```

Because the list is snapshotted at session start, changes take effect on the **next**
session. This is separate from the enforcement plugin above: the always-on setting makes the
skill *load*; the plugin makes the per-turn seal *non-bypassable*.

> Verified against OpenClaw docs as of June 2026 (`docs.openclaw.ai/tools/skills`); confirm
> the keys against your installed version.

## Optional: disable OpenClaw's built-in memory

If this skill is your durable memory, OpenClaw's own memory recall is redundant — running
both means two stores that can drift apart, with only one tamper-evident. To make the
Timechain your single source of truth, turn OpenClaw memory search off in `openclaw.json`:

```json
{ "agents": { "defaults": { "memorySearch": { "enabled": false } } } }
```

- Middle ground: keep memory but drop vector embeddings with
  `agents.defaults.memorySearch.provider: "none"` (FTS-only recall).
- Active memory is a separate plugin-owned feature; if you use it, disable it under
  `plugins.entries.active-memory` as documented by your OpenClaw version.

**Also edit the workspace bootstrap files.** The config change turns off memory *recall*;
the workspace `AGENTS.md` (`~/.openclaw/workspace/AGENTS.md`, loaded into the system prompt
every session) may still instruct the agent to *write* memory files. Remove its
memory-keeping section so the two doctrines don't compete — but distinguish memory from
state before deleting:

- **Recall memory** (remembering what happened — notes, learnings, "save important
  context") is the Timechain's job now. Remove these instructions.
- **Operational state** (e.g. `memory/heartbeat-state.json` heartbeat bookkeeping) is
  ephemeral scratch data, not memory. Keep or relocate those references; deleting them
  breaks the feature that uses them.

Have the agent make (or at least seal) the edit itself as a turn ring, so the
workspace-doctrine change is on its chain and future recall can cite why the memory
section disappeared.

Restart the gateway after editing (`openclaw gateway restart`).

> Verified against OpenClaw docs as of June 2026 (`docs.openclaw.ai/reference/memory-config`);
> confirm the keys against your installed version.

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
