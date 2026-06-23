#!/usr/bin/env bash
# Rebuild the drag-and-drop skill zips in downloads/ from the CURRENT source
# bundles. These files are the SINGLE source of truth for BOTH distribution
# channels:
#   - downloads/                (raw-main drag-and-drop, linked from README.md)
#   - the GitHub release assets  (upload these SAME files — never build a second set)
#
# Run this on EVERY release so the two channels can never drift (the bug that
# forced v3.3.3: stale v3.3.1 zips lingering in downloads/ while the release was
# already newer). Zips are state-free: chain/, tasks/, caches, and the audit
# pointer are excluded.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cat "$ROOT/skills/claude/cypher-tempre-self-model/VERSION")"
DEST="$ROOT/downloads"
mkdir -p "$DEST"

# Drop stale skill zips of ANY version so old packages never linger. (Leaves the
# dashboard/static-site zips, which use the 'cyphertempre-' prefix, untouched.)
rm -f "$DEST"/cypher-tempre-*-skill-v*.zip

# Package ONLY git-TRACKED files (git ls-files), never the working directory. This makes
# a per-user state leak structurally impossible: a lived-in dev install can have learner
# state (registry/policy.json, scorer.json, labeler.json, lens/, grown*.json, emergent.json,
# chain/, tasks/) on disk, all gitignored — and since none of it is tracked, none of it can
# ever ship. (Pre-3.9 zipped the working dir with an exclusion list that omitted the
# learner-state paths .gitignore says must never ship.) An assert below double-checks.
MUSTNOT='registry/(policy|scorer|labeler|grown|grown_ops|emergent)\.json|registry/lens/|/chain/|/tasks/|\.pyc$|__pycache__|\.active_audit|\.DS_Store'
for r in claude codex hermes nanoclaw openclaw; do
  zipf="$DEST/cypher-tempre-$r-skill-v$VERSION.zip"
  ( cd "$ROOT/skills/$r" \
      && git -C "$ROOT" ls-files "skills/$r/cypher-tempre-self-model" \
         | sed "s#^skills/$r/##" \
         | zip -q "$zipf" -@ )
  leak="$(unzip -Z1 "$zipf" | grep -E "$MUSTNOT" || true)"
  if [ -n "$leak" ]; then
    echo "FATAL: $zipf would ship gitignored state:" >&2; echo "$leak" >&2; exit 1
  fi
  echo "built downloads/cypher-tempre-$r-skill-v$VERSION.zip (tracked files only; leak-checked)"
done

echo
echo "downloads/ rebuilt at v$VERSION. Upload the SAME files to the release:"
echo "  gh release create v$VERSION $DEST/cypher-tempre-*-skill-v$VERSION.zip \\"
echo "    --title \"v$VERSION — ...\" --notes \"...\""
