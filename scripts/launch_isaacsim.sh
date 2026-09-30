#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/env.sh"
cd "$RL_PROJECT_ROOT"
exec isaacsim --portable-root "$RL_PROJECT_ROOT/runtime/kit" "$@"
