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
