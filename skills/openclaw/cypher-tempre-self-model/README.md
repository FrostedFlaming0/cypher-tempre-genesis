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
python3 selftest.py
```

## OpenClaw Enforcement

The per-turn loop is enforced in two compatible ways:

- If your OpenClaw runtime exposes lifecycle shell hooks, wire the bundled
  `session_start_hook.sh`, `loop_hook.sh`, `stop_hook.sh`, and
  `subagent_stop_hook.sh` wrappers to the matching session, prompt-start,
  turn-stop, and subagent-stop events.
- If lifecycle hooks are unavailable, run the same verifier explicitly:

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
