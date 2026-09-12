#!/usr/bin/env bash
# Synchronize the authoring templates into the wheel package; --check is read-only.
set -euo pipefail
exec python3 "$(dirname "$0")/templates_sync.py" "$@"
