#!/bin/bash
# Cypher Tempre — SubagentStop hook: same block-until-seal pressure for spawned
# subagents, so a subagent wears the skill too (it must seal before returning).
# A subagent that forges its own task chain can point enforcement at it via
# CT_ENFORCE_ROOT; by default it enforces against the shared identity chain.
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SKILL/enforce.py" ] || exit 0
# stderr -> /dev/null so nothing can corrupt the stdout the harness parses as the
# decision JSON (enforce.py also quarantines its own stdout). Set CT_ENFORCE_DEBUG=1
# to surface enforce.py stderr for diagnosis. Fail-open: exit 0.
if [ -n "$CT_ENFORCE_DEBUG" ]; then
  python3 "$SKILL/enforce.py" subagent-check
else
  python3 "$SKILL/enforce.py" subagent-check 2>/dev/null
fi
exit 0
