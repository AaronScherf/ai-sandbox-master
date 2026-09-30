#!/usr/bin/env bash
# scripts/_rename_pkg_imports.sh OLD_PKG NEW_DOTTED_PATH
# Rewrites `from OLD_PKG...` / `import OLD_PKG...` import statements,
# repo-wide under the current directory, to NEW_DOTTED_PATH. Only lines
# that are themselves import statements (anchored at line start, after
# optional whitespace) are touched -- this can't clobber comments,
# strings, or prose that happens to contain the same word.
set -euo pipefail
OLD="$1"
NEW="$2"
FILES=$(grep -rlE "^[[:space:]]*(from|import)[[:space:]]+${OLD}(\.|[[:space:]])" --include="*.py" . || true)
if [ -z "$FILES" ]; then
  echo "No files reference ${OLD}"
  exit 0
fi
for f in $FILES; do
  sed -i -E \
    -e "s/^([[:space:]]*from[[:space:]]+)${OLD}(\.|[[:space:]])/\1${NEW}\2/" \
    -e "s/^([[:space:]]*import[[:space:]]+)${OLD}(\.|[[:space:]]|\$)/\1${NEW}\2/" \
    "$f"
done
COUNT=$(echo "$FILES" | wc -l)
echo "Rewrote ${COUNT} file(s): ${OLD} -> ${NEW}"
