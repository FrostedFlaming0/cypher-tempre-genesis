#!/bin/bash
# Cypher Tempre — Stop hook: HARD block turn-end until a ring is sealed this turn.
# enforce.py emits the Stop-hook JSON contract on stdout:
#   block -> {"decision":"block","reason":"..."}  (Claude must continue and seal)
#   allow -> (no output)                          (turn may end)
# Bounded (MAX_NUDGES) and fail-open: a model that genuinely cannot seal is freed
# after a few nudges and an adherence_violation is recorded — never bricked.
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SKILL/enforce.py" ] || exit 0
# stderr -> /dev/null so a warning or import message can NEVER bleed into the
# stdout the harness parses as the decision JSON (enforce.py also quarantines its
# own stdout to guarantee this). exit 0 always: the gate is fail-open by design.
python3 "$SKILL/enforce.py" stop-check 2>/dev/null
exit 0
