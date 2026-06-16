#!/bin/bash
# Optional Hermes watchdog for Cypher Tempre.
# Hermes has no native lifecycle hook that can block a response. This helper is
# for users who want an external check, for example from cron or a terminal tab.

set -euo pipefail

SKILL="${CT_SKILL_DIR:-$HOME/.hermes/skills/openclaw-imports/cypher-tempre-self-model}"

if [ ! -f "$SKILL/enforce.py" ]; then
  echo "Cypher Tempre skill not found at: $SKILL" >&2
  echo "Set CT_SKILL_DIR=/path/to/cypher-tempre-self-model and try again." >&2
  exit 2
fi

out="$(python3 "$SKILL/enforce.py" stop-check 2>&1 || true)"
if [ -n "$out" ]; then
  printf '%s\n' "$out"
else
  echo "Cypher Tempre watchdog: no pending marked Hermes turn is currently unsealed."
fi
