#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

uv run python add-submission.py

git add -A

if git diff --cached --quiet; then
  echo "No changes to commit."
  exit 0
fi

# e.g. "May 04, 2026" (BSD date; day may be zero-padded)
DATE_STR="$(date '+%B %d, %Y')"
git commit -m "Leetcode submission: ${DATE_STR}"

git push
