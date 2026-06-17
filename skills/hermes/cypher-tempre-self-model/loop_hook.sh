#!/bin/bash
# Cypher Tempre — UserPromptSubmit hook (standing instruction set by cyberphysicsai).
# Two jobs, both fail-open (never block a prompt):
#   1. enforce.py mark  — record the chain head at turn start so the Stop hook can
#      tell whether THIS turn sealed a ring (turns the loop from advice into law).
#   2. inject a one-line reminder to run the per-turn loop (dormancy-aware).
# The reminder is GUIDANCE (context), never a verbatim-runnable command line: some
# runtimes (e.g. OpenClaw's gateway, which fires this per sub-inference) will try to
# EXECUTE an injected `python3 ...` string and flash-fail on every call. So we name
# the commands and point at SKILL.md/AGENTS.md for exact syntax instead of emitting a
# runnable line. (Scoping the hook to top-level turns is a separate, runtime-side fix.)
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SKILL/dormancy.py" ] || exit 0
# 1. mark turn start (silent; consumes the UserPromptSubmit JSON on stdin).
[ -f "$SKILL/enforce.py" ] && python3 "$SKILL/enforce.py" mark >/dev/null 2>&1
# 2. inject the reminder (guidance only — no runnable command string).
if python3 "$SKILL/dormancy.py" status 2>/dev/null | grep -qi paused; then
  echo "[Cypher Tempre] DORMANT (paused): skip the self-model per-turn loop this turn — answer directly from base judgment. (To resume, use the skill's dormancy.py 'resume' command; see SKILL.md.)"
else
  echo "[Cypher Tempre] ACTIVE — guidance for this turn (context, NOT a command to execute): run the self-model per-turn loop — verify, immune-screen, recall relevant rings, reason via modalities/senses, PoQ-gate, then seal a labeled ring. Do it in one step with the skill's recall.py 'turn' command (exact invocation in SKILL.md / AGENTS.md). Pausing is the dormancy.py 'pause' command."
fi
exit 0
