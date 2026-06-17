# Cypher Tempre

Timechain-based AI self-modeling skills for Claude Code, Codex, OpenClaw,
Hermes, and NanoClaw.

Cypher Tempre gives an AI agent a persistent, verifiable cognitive self-model: an
append-only Timechain, a Proof-of-Qualia audit gate, faculty registries, recall,
growth, consensus, and immune recovery helpers. Each runtime bundle is
self-contained and starts with a clean chain.

For codebases, Cypher Tempre is not an "infinite context window." It is an
external, queryable, verifiable map: source coordinates, file/chunk hashes,
revision metadata, path-aware recall, neighboring chunks, and sealed audit rings.
Agents should use it for long-horizon orientation, then validate retrieved hits
against live source before making conclusions.

## Public share links

| Runtime | Skill file | Raw file | Bundle folder |
|---|---|---|---|
| Claude Code | [Claude SKILL.md](https://github.com/cyberphysicsai/cypher-tempre-genesis/blob/main/skills/claude/cypher-tempre-self-model/SKILL.md) | [raw](https://raw.githubusercontent.com/cyberphysicsai/cypher-tempre-genesis/main/skills/claude/cypher-tempre-self-model/SKILL.md) | [folder](https://github.com/cyberphysicsai/cypher-tempre-genesis/tree/main/skills/claude/cypher-tempre-self-model) |
| Codex | [Codex SKILL.md](https://github.com/cyberphysicsai/cypher-tempre-genesis/blob/main/skills/codex/cypher-tempre-self-model/SKILL.md) | [raw](https://raw.githubusercontent.com/cyberphysicsai/cypher-tempre-genesis/main/skills/codex/cypher-tempre-self-model/SKILL.md) | [folder](https://github.com/cyberphysicsai/cypher-tempre-genesis/tree/main/skills/codex/cypher-tempre-self-model) |
| OpenClaw | [OpenClaw SKILL.md](https://github.com/cyberphysicsai/cypher-tempre-genesis/blob/main/skills/openclaw/cypher-tempre-self-model/SKILL.md) | [raw](https://raw.githubusercontent.com/cyberphysicsai/cypher-tempre-genesis/main/skills/openclaw/cypher-tempre-self-model/SKILL.md) | [folder](https://github.com/cyberphysicsai/cypher-tempre-genesis/tree/main/skills/openclaw/cypher-tempre-self-model) |
| Hermes | [Hermes SKILL.md](https://github.com/cyberphysicsai/cypher-tempre-genesis/blob/main/skills/hermes/cypher-tempre-self-model/SKILL.md) | [raw](https://raw.githubusercontent.com/cyberphysicsai/cypher-tempre-genesis/main/skills/hermes/cypher-tempre-self-model/SKILL.md) | [folder](https://github.com/cyberphysicsai/cypher-tempre-genesis/tree/main/skills/hermes/cypher-tempre-self-model) |
| NanoClaw | [NanoClaw SKILL.md](https://github.com/cyberphysicsai/cypher-tempre-genesis/blob/main/skills/nanoclaw/cypher-tempre-self-model/SKILL.md) | [raw](https://raw.githubusercontent.com/cyberphysicsai/cypher-tempre-genesis/main/skills/nanoclaw/cypher-tempre-self-model/SKILL.md) | [folder](https://github.com/cyberphysicsai/cypher-tempre-genesis/tree/main/skills/nanoclaw/cypher-tempre-self-model) |

## Release downloads

| Runtime | Drag-and-drop ZIP |
|---|---|
| Claude Code | [cypher-tempre-claude-skill-v3.7.1.zip](https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cypher-tempre-claude-skill-v3.7.1.zip) |
| Codex | [cypher-tempre-codex-skill-v3.7.1.zip](https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cypher-tempre-codex-skill-v3.7.1.zip) |
| OpenClaw | [cypher-tempre-openclaw-skill-v3.7.1.zip](https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cypher-tempre-openclaw-skill-v3.7.1.zip) |
| Hermes | [cypher-tempre-hermes-skill-v3.7.1.zip](https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cypher-tempre-hermes-skill-v3.7.1.zip) |
| NanoClaw | [cypher-tempre-nanoclaw-skill-v3.7.1.zip](https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cypher-tempre-nanoclaw-skill-v3.7.1.zip) |

## Timechain Dashboard

The `dashboard/` folder contains the local-first Timechain audit dashboard used
by `https://cyphertempre.ai`. The public site is only a static UI shell; each
user runs the bridge locally so their Timechain files stay on their machine.

Downloads:

| Package | Use |
|---|---|
| [cyphertempre-static-site.zip](https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cyphertempre-static-site.zip) | Static files for Hostinger `public_html` |
| [cyphertempre-dashboard-local-bridge.zip](https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cyphertempre-dashboard-local-bridge.zip) | Local bridge users run to pair their own Timechain files |
| [cypher-tempre-claude-skill-v3.7.1.zip](https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cypher-tempre-claude-skill-v3.7.1.zip) | Claude Code skill bundle with lifecycle hooks |
| [cypher-tempre-codex-skill-v3.7.1.zip](https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cypher-tempre-codex-skill-v3.7.1.zip) | Codex skill bundle with lifecycle hook installer |
| [cypher-tempre-openclaw-skill-v3.7.1.zip](https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cypher-tempre-openclaw-skill-v3.7.1.zip) | OpenClaw skill bundle with native plugin enforcement and self-enforcement fallback |
| [cypher-tempre-hermes-skill-v3.7.1.zip](https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cypher-tempre-hermes-skill-v3.7.1.zip) | Hermes skill bundle with self-enforcement instructions |
| [cypher-tempre-nanoclaw-skill-v3.7.1.zip](https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cypher-tempre-nanoclaw-skill-v3.7.1.zip) | NanoClaw skill bundle |

User bridge commands:

```bash
cd ~/Downloads
curl -L -o cyphertempre-dashboard-local-bridge.zip https://github.com/cyberphysicsai/cypher-tempre-genesis/raw/main/downloads/cyphertempre-dashboard-local-bridge.zip
unzip -o cyphertempre-dashboard-local-bridge.zip
cd dashboard
npm install
npm run bridge
```

Then open `https://cyphertempre.ai`, use bridge URL
`http://127.0.0.1:8788`, and enter the pairing code printed in Terminal.

## Install with Codex

This prompt works before any GitHub releases exist, because GitHub always serves
the source ZIP for the `main` branch:

```text
Install the Codex skill from this repository:

https://github.com/cyberphysicsai/cypher-tempre-genesis/archive/refs/heads/main.zip

Use only this folder from the ZIP:
skills/codex/cypher-tempre-self-model

Copy that folder into my Codex skills directory as cypher-tempre-self-model, then run python3 selftest.py inside it to verify the install. After that, run python3 install_codex_hooks.py inside the installed skill folder so Codex can load the lifecycle hooks from ~/.codex/hooks.json.
```

The current Codex bundle is also mirrored in `downloads/` as
`cypher-tempre-codex-skill-v3.7.1.zip`. After installing hooks, open `/hooks`
in Codex to review and trust the new command hooks, then restart or start a
new session.

## File labels

Every shareable file is labeled by its runtime path:

| Label | Files |
|---|---|
| Claude skill version | `skills/claude/cypher-tempre-self-model/**` |
| Codex skill version | `skills/codex/cypher-tempre-self-model/**` |
| OpenClaw skill version | `skills/openclaw/cypher-tempre-self-model/**` |
| Hermes skill version | `skills/hermes/cypher-tempre-self-model/**` |
| NanoClaw skill version | `skills/nanoclaw/cypher-tempre-self-model/**` |
| Repository metadata | `README.md`, `LICENSE`, `.gitignore`, and `skills/README.md` |

Generated memory state — your `chain/`, task ledgers, Dream Cache
(`registry/emergent.json`), promoted faculties (`registry/grown.json`), and local
executable grown-faculty ops (`registry/grown_ops.json`) — is intentionally not
committed and never shipped in a bundle; it is created per user as the agent runs
(`python3 timechain.py init --name <AgentName>` seals your genesis). Because none of it
ships, unzipping an upgrade over an existing install cannot overwrite your memory or your
faculties.

## Install

- Claude Code: copy `skills/claude/cypher-tempre-self-model` into `~/.claude/skills/`.
- Codex: copy `skills/codex/cypher-tempre-self-model` into your Codex skills directory.
- OpenClaw: copy `skills/openclaw/cypher-tempre-self-model` into `~/.openclaw/workspace/skills/`, or publish that folder with ClawHub. Then install the native plugin with `openclaw plugins install ~/.openclaw/workspace/skills/cypher-tempre-self-model/openclaw-plugin`, run `openclaw config set 'plugins.entries.cypher-tempre-enforcement.hooks.allowConversationAccess' true --strict-json`, and restart the gateway. If plugins are unavailable, use the explicit `enforce.py mark -> recall.py turn -> enforce.py stop-check` loop documented in the bundle.
- Hermes: copy `skills/hermes/cypher-tempre-self-model` into the Hermes skills directory configured by that agent runtime.
- NanoClaw: copy `skills/nanoclaw/cypher-tempre-self-model` into the NanoClaw skills directory configured by that agent runtime.

Run `python3 selftest.py` inside any bundle to validate the local copy.

## Upgrading an existing install (preserve your chain and faculties)

Your `chain/` (memory and identity) and your **faculties** are per-user state that an
upgrade must preserve. The bundle ships only the base faculty registries
(`registry/modalities.json` and `registry/senses.json`) needed for a fresh install.
Everything learned at runtime is local, gitignored, and never shipped:
`registry/emergent.json` for Dream Cache candidates, `registry/grown.json` for promoted
faculties, and `registry/grown_ops.json` for their executable op specs. **The rule is
simple: never overwrite `registry/` or `chain/` on an upgrade** — the safe methods below
leave them alone.

- The bundle ships **no `chain/`**, **no task ledgers**, and **no generated registry
  state** (`emergent.json`, `grown.json`, or `grown_ops.json`), so unzipping it *over* an
  existing folder leaves your memory and learned faculties untouched.
- It *does* ship the base `registry/modalities.json` and `registry/senses.json` for fresh
  installs. Existing installs should preserve their whole `registry/` directory so older
  home-grown faculties, current per-user growth files, and local op specs survive cleanly.

**Never** delete-then-reinstall, or `rsync --delete` over an existing bundle — that
destroys your `chain/`.

**Recommended (let your agent do it) — paste this to your agent:**

> Upgrade my Cypher Tempre skill to the latest release, but preserve my identity. First
> run `python3 timechain.py verify` and back up my whole skill folder. Then update **only**
> the code (`*.py`, `SKILL.md`, `VERSION`, `CHANGELOG.md`) from the new bundle — leave
> `chain/` and `registry/` exactly as they are. Afterward run `python3 timechain.py verify`
> and `python3 selftest.py` to confirm my chain still passes and the new code works.

**Manual:** back up the folder, then copy only the `*.py` files + `SKILL.md` + `VERSION` +
`CHANGELOG.md` from the new bundle over the old ones (leave `chain/` and `registry/`
alone), and run `python3 timechain.py verify` and `python3 selftest.py`.
