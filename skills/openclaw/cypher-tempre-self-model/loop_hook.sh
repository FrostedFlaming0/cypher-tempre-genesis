#!/bin/bash
# Cypher Tempre — UserPromptSubmit hook (standing instruction set by cyberphysicsai).
# Two jobs, both fail-open (never block a prompt):
#   1. enforce.py mark  — record the chain head at turn start so the Stop hook can
#      tell whether THIS turn sealed a ring (turns the loop from advice into law).
#   2. inject a one-line reminder to run the per-turn loop (dormancy-aware).
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SKILL/dormancy.py" ] || exit 0
# 1. mark turn start (silent; consumes the UserPromptSubmit JSON on stdin).
[ -f "$SKILL/enforce.py" ] && python3 "$SKILL/enforce.py" mark >/dev/null 2>&1
# 2. inject the reminder.
if python3 "$SKILL/dormancy.py" status 2>/dev/null | grep -qi paused; then
  echo "[Cypher Tempre] DORMANT (paused): skip the self-model per-turn loop this turn — answer directly from base judgment. Resume with: python3 $SKILL/dormancy.py resume"
else
  echo "[Cypher Tempre] ACTIVE — standing instruction: run the self-model per-turn loop this turn (verify -> immune-screen -> recall relevant rings -> reason via modalities/senses -> PoQ-gate -> seal a labeled ring). One-call path: python3 $SKILL/recall.py turn \"<thought>\" --input \"<request>\". Pause anytime with: python3 $SKILL/dormancy.py pause"
fi
exit 0
