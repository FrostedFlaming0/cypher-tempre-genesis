#!/bin/bash
# Cypher Tempre — SessionStart hook: prime the session so it WEARS the self-model
# from turn 0 even if the model never opens SKILL.md. enforce.py session-start emits the
# ACTIVE/DORMANT context as a hook-JSON envelope ({"hookSpecificOutput":{...}}): the harness
# parses SessionStart hook stdout as JSON (the Codex CLI rejects plain text), and enforce.py
# writes ONLY that JSON to stdout. Set CT_ENFORCE_DEBUG=1 to surface stderr. Fail-open.
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SKILL/enforce.py" ] || exit 0
if [ -n "$CT_ENFORCE_DEBUG" ]; then
  python3 "$SKILL/enforce.py" session-start
else
  python3 "$SKILL/enforce.py" session-start 2>/dev/null
fi
exit 0
