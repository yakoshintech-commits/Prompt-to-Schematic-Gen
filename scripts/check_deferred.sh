#!/usr/bin/env bash
# check_deferred.sh
#
# Optional, non-authoritative helper for the Trigger Review ritual (PIPELINE.md
# section 11.1). Pre-counts rows by status so the review goes faster. Does not
# decide anything on its own, and does not modify deferred.md.
#
# Usage: scripts/check_deferred.sh

set -euo pipefail

DEFERRED_FILE="deferred.md"

if [ ! -f "$DEFERRED_FILE" ]; then
  echo "check_deferred.sh: deferred.md not found. Run this from the project root."
  exit 1
fi

echo "Deferred Register status summary:"
echo ""
for status in armed fired building built shelved; do
  count=$(grep -c "| $status |" "$DEFERRED_FILE" || true)
  echo "  $status: $count"
done

echo ""
echo "Rows currently fired (need a Work Item written this session, per section 11.1):"
grep "| fired |" "$DEFERRED_FILE" || echo "  none"

echo ""
echo "This is a count only. The Sponsor still reads deferred.md directly to judge whether any armed row's trigger has actually fired."
