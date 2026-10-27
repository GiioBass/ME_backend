#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

# Si existe el entorno virtual, usar su python; sino usar python3 del sistema
if [ -f "$DIR/venv/bin/python" ]; then
    PYTHON_BIN="$DIR/venv/bin/python"
else
    PYTHON_BIN="$(command -v python3 || command -v python)"
fi

exec "$PYTHON_BIN" "$DIR/start.py" "$@"
