#!/usr/bin/env bash
# Build the article pages from Markdown.
#
# Usage:
#   tools/build.sh            # build every article in content/
#   tools/build.sh foo.md     # build a single source file
#
# Creates a local virtualenv in .venv on first run.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv"
if [ ! -d "$VENV" ]; then
    echo "Creating virtualenv in .venv ..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q -r "$ROOT/tools/requirements.txt"
fi

"$VENV/bin/python" "$ROOT/tools/generate.py" "$@"
