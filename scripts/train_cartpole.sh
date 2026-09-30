#!/usr/bin/env bash
# Small environment validation, not wheel-legged robot training.
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/env.sh"
cd "$RL_PROJECT_ROOT"
exec python "$ISAACLAB_PATH/scripts/reinforcement_learning/rsl_rl/train.py" \
  --task Isaac-Cartpole-v0 --num_envs 64 --max_iterations 5 --headless \
  --device cuda:0 --seed 42 --logger tensorboard \
  --kit_args "--portable-root $RL_PROJECT_ROOT/runtime/kit" "$@"
