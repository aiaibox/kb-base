#!/usr/bin/env bash
# Create a note with a fresh ULID and correct frontmatter.
#
#   scripts/newnote.sh <path/slug> "<title>" [template]
#
# <path/slug> is relative to the repo root and takes no .md suffix:
#   scripts/newnote.sh living/turtle-heater-setpoint "Turtle tank heater setpoint" note
#
# Never hand-write an id; always come through here.
set -euo pipefail

# One copy, in kb-base. The target repo is the git work tree this is run in.
BASE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "newnote.sh: run it inside a vault repo" >&2; exit 1; }
REPO_NAME="$(basename "$REPO_ROOT")"

if [ $# -lt 2 ]; then
  echo "usage: scripts/newnote.sh <path/slug> \"<title>\" [template]" >&2
  echo "templates: $(cd "$(dirname "${BASH_SOURCE[0]}")/../_templates" 2>/dev/null && ls *.md 2>/dev/null | sed 's/\.md$//' | tr '\n' ' ')" >&2
  exit 2
fi

SLUG_PATH="${1%.md}"
TITLE="$2"
TEMPLATE="${3:-note}"

TEMPLATE_FILE="$BASE_ROOT/_templates/$TEMPLATE.md"
if [ ! -f "$TEMPLATE_FILE" ]; then
  echo "no such template: $TEMPLATE (looked in _templates/$TEMPLATE.md)" >&2
  exit 1
fi

TARGET="$REPO_ROOT/$SLUG_PATH.md"
if [ -e "$TARGET" ]; then
  echo "refusing to overwrite existing note: $SLUG_PATH.md" >&2
  exit 1
fi

# ULID: 48-bit millisecond timestamp + 80 bits of randomness, Crockford base32.
# Lexicographically sortable by creation time, and collision-safe in practice.
ULID="$(python3 -c '
import os, time
A = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
n = (int(time.time() * 1000) << 80) | int.from_bytes(os.urandom(10), "big")
print("".join(A[(n >> s) & 31] for s in range(125, -1, -5)))
')"
TODAY="$(date +%F)"

mkdir -p "$(dirname "$TARGET")"

# Placeholders are substituted with awk rather than sed so that / and | pass
# through intact. awk's gsub still treats & and \ specially in the replacement
# — "Fish & chips" would come out as "Fish {{title}} chips" — so both are
# escaped first. Double quotes would break the quoted YAML title; they become
# single quotes.
TITLE="${TITLE//\\/\\\\}"
TITLE="${TITLE//&/\\&}"
TITLE="${TITLE//\"/\'}"
ULID="$ULID" TITLE="$TITLE" REPO_NAME="$REPO_NAME" TODAY="$TODAY" \
awk '{
  gsub(/\{\{id\}\}/,      ENVIRON["ULID"])
  gsub(/\{\{title\}\}/,   ENVIRON["TITLE"])
  gsub(/\{\{repo\}\}/,    ENVIRON["REPO_NAME"])
  gsub(/\{\{created\}\}/, ENVIRON["TODAY"])
  gsub(/\{\{updated\}\}/, ENVIRON["TODAY"])
  print
}' "$TEMPLATE_FILE" > "$TARGET"

echo "$SLUG_PATH.md  ($TEMPLATE, id=$ULID)"
