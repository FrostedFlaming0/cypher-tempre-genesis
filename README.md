# Cypher Tempre

Timechain-based AI self-modeling skills for Claude Code, Codex, and OpenClaw.

Cypher Tempre gives an AI agent a persistent, verifiable cognitive self-model: an
append-only Timechain, a Proof-of-Qualia audit gate, faculty registries, recall,
growth, consensus, and immune recovery helpers. Each runtime bundle is
self-contained and starts with a clean chain.

## Public share links

| Runtime | Skill file | Raw file | Bundle folder |
|---|---|---|---|
| Claude Code | [Claude SKILL.md](https://github.com/cyberphysicsai/cyphertempre/blob/main/skills/claude/cypher-tempre-self-model/SKILL.md) | [raw](https://raw.githubusercontent.com/cyberphysicsai/cyphertempre/main/skills/claude/cypher-tempre-self-model/SKILL.md) | [folder](https://github.com/cyberphysicsai/cyphertempre/tree/main/skills/claude/cypher-tempre-self-model) |
| Codex | [Codex SKILL.md](https://github.com/cyberphysicsai/cyphertempre/blob/main/skills/codex/cypher-tempre-self-model/SKILL.md) | [raw](https://raw.githubusercontent.com/cyberphysicsai/cyphertempre/main/skills/codex/cypher-tempre-self-model/SKILL.md) | [folder](https://github.com/cyberphysicsai/cyphertempre/tree/main/skills/codex/cypher-tempre-self-model) |
| OpenClaw | [OpenClaw SKILL.md](https://github.com/cyberphysicsai/cyphertempre/blob/main/skills/openclaw/cypher-tempre-self-model/SKILL.md) | [raw](https://raw.githubusercontent.com/cyberphysicsai/cyphertempre/main/skills/openclaw/cypher-tempre-self-model/SKILL.md) | [folder](https://github.com/cyberphysicsai/cyphertempre/tree/main/skills/openclaw/cypher-tempre-self-model) |

## Install with Codex

This prompt works before any GitHub releases exist, because GitHub always serves
the source ZIP for the `main` branch:

```text
Install the Codex skill from this repository:

https://github.com/cyberphysicsai/cyphertempre/archive/refs/heads/main.zip

Use only this folder from the ZIP:
skills/codex/cypher-tempre-self-model

Copy that folder into my Codex skills directory as cypher-tempre-self-model, then run python3 selftest.py inside it to verify the install.
```

After a GitHub Release exists, you can also share a one-file release asset URL
such as `https://github.com/cyberphysicsai/cyphertempre/releases/download/v1.0.0/cypher-tempre-codex-skill.zip`.
Release URLs return 404 until the tag and asset are published.

## File labels

Every shareable file is labeled by its runtime path:

| Label | Files |
|---|---|
| Claude skill version | `skills/claude/cypher-tempre-self-model/**` |
| Codex skill version | `skills/codex/cypher-tempre-self-model/**` |
| OpenClaw skill version | `skills/openclaw/cypher-tempre-self-model/**` |
| Repository metadata | `README.md`, `LICENSE`, `.gitignore`, and `skills/README.md` |

Generated memory state is intentionally not committed. A user creates their own
`chain/` and task ledgers by running `python3 timechain.py init --name <AgentName>`
inside the copied skill bundle.

## Install

- Claude Code: copy `skills/claude/cypher-tempre-self-model` into `~/.claude/skills/`.
- Codex: copy `skills/codex/cypher-tempre-self-model` into your Codex skills directory.
- OpenClaw: copy `skills/openclaw/cypher-tempre-self-model` into `~/.openclaw/workspace/skills/`, or publish that folder with ClawHub.

Run `python3 selftest.py` inside any bundle to validate the local copy.
