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

For delegated Hermes work, use `hermes/cypher-tempre-agent.md`. An optional
terminal/cron helper is available at `hermes/enforcement-watchdog.sh`.

See `SKILL.md` for the full per-turn protocol.
