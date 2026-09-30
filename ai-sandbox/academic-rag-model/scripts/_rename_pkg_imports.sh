#!/usr/bin/env bash
# scripts/_rename_pkg_imports.sh OLD_PKG NEW_DOTTED_PATH
# Rewrites `from OLD_PKG...` / `import OLD_PKG...` import statements,
# repo-wide under the current directory, to NEW_DOTTED_PATH. Only lines
# that are themselves import statements (anchored at line start, after
# optional whitespace) are touched -- this can't clobber comments,
# strings, or prose that happens to contain the same word.
# Note: comma-separated imports (import a, OLD_PKG, b) are not supported.
set -euo pipefail
OLD="$1"
NEW="$2"
# Use NUL-delimited output to safely handle filenames with spaces
mapfile -t -d '' files < <(grep -rlZE "^[[:space:]]*(from|import)[[:space:]]+${OLD}(\.|[[:space:]]|\$)" --include="*.py" . || true)
if [ ${#files[@]} -eq 0 ]; then
  echo "No files reference ${OLD}"
  exit 0
fi
for f in "${files[@]}"; do
  sed -i -E \
    -e "s/^([[:space:]]*from[[:space:]]+)${OLD}(\.|[[:space:]])/\1${NEW}\2/" \
    -e "s/^([[:space:]]*import[[:space:]]+)${OLD}(\.|[[:space:]]|\$)/\1${NEW}\2/" \
    "$f"
done
COUNT=${#files[@]}
echo "Rewrote ${COUNT} file(s): ${OLD} -> ${NEW}"
