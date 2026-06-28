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

Restart the gateway after editing (`openclaw gateway restart`).

> Verified against OpenClaw docs as of June 2026 (`docs.openclaw.ai/reference/memory-config`);
> confirm the keys against your installed version.

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
