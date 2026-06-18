# Cypher Tempre Timechain Self-Model

**Runtime label:** Codex skill version.

This is the Codex bundle for Cypher Tempre: a persistent, verifiable,
self-healing cognitive self-model for an AI agent. It is stdlib-only Python,
includes `agents/openai.yaml` UI metadata, and ships without generated memory
state.

## Install

Copy this folder into your Codex skills directory:

```bash
cp -R cypher-tempre-self-model ~/.codex/skills/
```

Restart or refresh Codex so the skill list updates. Initialize a fresh chain
inside the copied bundle:

```bash
python3 timechain.py init --name Codex
python3 selftest.py
```

Enable Codex lifecycle hooks for the installed skill:

```bash
python3 install_codex_hooks.py
```

The installer merges `SessionStart`, `UserPromptSubmit`, `Stop`, and
`SubagentStop` hook entries into `~/.codex/hooks.json` using absolute paths to
this skill folder. It preserves unrelated hooks and writes a backup before
replacing an existing file. Open `/hooks` in Codex to review and trust the new
command hooks, then restart or start a new session.

### Codex CLI hook checklist

The app and CLI use the same hook scripts, but they can differ in **activation
state**: the app may already have the hooks installed and trusted, while a fresh
CLI install only has the skill folder. For the CLI, the lifecycle hooks must be
present in `~/.codex/hooks.json` and trusted by Codex before Stop/SubagentStop can
block reliably.

If the CLI reports a Stop hook or invalid JSON issue:

```bash
cd ~/.codex/skills/cypher-tempre-self-model
python3 selftest.py
python3 install_codex_hooks.py
```

Then run `codex`, open `/hooks`, trust the four Cypher Tempre hooks, and restart
the CLI session. For one-off automation only, Codex also exposes
`--dangerously-bypass-hook-trust`, but normal users should trust the hooks through
`/hooks` instead.

The hook stdout contract is strict:

- `SessionStart` and `UserPromptSubmit` emit hook-JSON context envelopes.
- `Stop` and `SubagentStop` emit either exactly `{"decision":"block",...}` or
  nothing.
- Incidental warnings stay off stdout. To debug field issues, set
  `CT_ENFORCE_DEBUG=1`; `0`, `false`, `no`, and `off` keep the hooks quiet.

Or ask Codex to install it from the repository source ZIP:

```text
Install the Codex skill from this repository:

https://github.com/cyberphysicsai/cypher-tempre-genesis/archive/refs/heads/main.zip

Use only this folder from the ZIP:
skills/codex/cypher-tempre-self-model

Copy that folder into my Codex skills directory as cypher-tempre-self-model, then run python3 selftest.py inside it to verify the install.
```

Then ask Codex:

```text
Run python3 install_codex_hooks.py inside the installed cypher-tempre-self-model skill folder, then help me review the hooks with /hooks.
```

See `SKILL.md` for the full per-turn protocol.
