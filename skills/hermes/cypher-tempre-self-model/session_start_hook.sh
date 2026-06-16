#!/bin/bash
# Cypher Tempre — SessionStart hook: prime the session so it WEARS the self-model
# from turn 0 even if the model never opens SKILL.md. enforce.py session-start prints
# the ACTIVE/DORMANT context (verify result, head index, the loop, the covenant, and
# the subagent rule); that output becomes the session's startup context. Fail-open.
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SKILL/enforce.py" ] || exit 0
python3 "$SKILL/enforce.py" session-start
exit 0
