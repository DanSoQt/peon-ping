#!/usr/bin/env bash
# peon-ping CLI wrapper
PEON_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CLAUDE_PLUGIN_ROOT="$PEON_ROOT"
python3 "$PEON_ROOT/hooks/scripts/peon.py" "$@"
