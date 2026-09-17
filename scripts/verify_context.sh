#!/usr/bin/env bash
# verify_context.sh
#
# Checks the recorded baseline hashes in context.md against the real files.
# Run from the project root (pcb-schematic-gen/), not from inside scripts/.
#
# Usage:
#   scripts/verify_context.sh            # check hashes, exit non-zero on mismatch
#   scripts/verify_context.sh --update   # print real current hashes to paste into context.md
#
# This script only flags drift. It does not fix context.md. The Sponsor reconciles,
# per PIPELINE.md section 17.

set -euo pipefail

CONTEXT_FILE="context.md"

if [ ! -f "$CONTEXT_FILE" ]; then
  echo "verify_context.sh: FAIL - context.md not found. Run this from the project root."
  exit 1
fi

# file name as it appears in context.md's hash block -> real path on disk
declare -A FILE_PATHS=(
  ["global.md"]="../global.md"
  ["instructions.md"]="instructions.md"
  ["conventions.md"]="conventions.md"
  ["skills/manifest.yaml"]="skills/manifest.yaml"
)

get_recorded_hash() {
  local name="$1"
  # matches a line like: instructions.md       v1  sha256:abc123...
  grep -E "^${name//./\\.}[[:space:]]" "$CONTEXT_FILE" | head -n1 | sed -E 's/.*sha256:([a-f0-9A-F]+|PENDING).*/\1/'
}

if [ "${1:-}" = "--update" ]; then
  echo "Real current hashes. Paste these into context.md's hash block, replacing PENDING or stale values:"
  echo ""
  for name in "${!FILE_PATHS[@]}"; do
    path="${FILE_PATHS[$name]}"
    if [ -f "$path" ]; then
      hash=$(sha256sum "$path" | awk '{print $1}')
      echo "$name  sha256:$hash"
    else
      echo "$name  MISSING at $path"
    fi
  done
  exit 0
fi

fail=0
for name in "${!FILE_PATHS[@]}"; do
  path="${FILE_PATHS[$name]}"
  if [ ! -f "$path" ]; then
    echo "MISSING: $name (expected at $path)"
    fail=1
    continue
  fi
  actual=$(sha256sum "$path" | awk '{print $1}')
  recorded=$(get_recorded_hash "$name")
  if [ -z "$recorded" ]; then
    echo "NOT FOUND IN context.md: $name"
    fail=1
    continue
  fi
  if [ "$recorded" = "PENDING" ]; then
    echo "UNSET HASH: $name - run 'scripts/verify_context.sh --update' and paste the real hash into context.md"
    fail=1
    continue
  fi
  if [ "$actual" != "$recorded" ]; then
    echo "MISMATCH: $name"
    echo "  recorded: $recorded"
    echo "  actual:   $actual"
    fail=1
  fi
done

if [ "$fail" -eq 1 ]; then
  echo ""
  echo "verify_context.sh: FAIL - baseline drift detected. Sponsor must reconcile context.md."
  exit 1
fi

echo "verify_context.sh: PASS - all baseline hashes match."
exit 0
