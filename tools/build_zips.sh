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

for r in claude codex hermes nanoclaw openclaw; do
  ( cd "$ROOT/skills/$r" && zip -rq \
      "$DEST/cypher-tempre-$r-skill-v$VERSION.zip" cypher-tempre-self-model \
      -x "*/chain/*" "*/tasks/*" "*/__pycache__/*" "*.pyc" "*/.active_audit" "*/.DS_Store" \
         "*/registry/grown.json" "*/registry/grown_ops.json" "*/registry/emergent.json" )
  echo "built downloads/cypher-tempre-$r-skill-v$VERSION.zip"
done

echo
echo "downloads/ rebuilt at v$VERSION. Upload the SAME files to the release:"
echo "  gh release create v$VERSION $DEST/cypher-tempre-*-skill-v$VERSION.zip \\"
echo "    --title \"v$VERSION — ...\" --notes \"...\""
