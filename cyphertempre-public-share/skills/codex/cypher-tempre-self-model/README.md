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

See `SKILL.md` for the full per-turn protocol.
