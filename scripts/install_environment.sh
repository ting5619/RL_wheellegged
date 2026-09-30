#!/usr/bin/env bash
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/env.sh"
cd "$RL_PROJECT_ROOT"
[[ "$(git -C "$ISAACLAB_PATH" rev-parse HEAD)" == "3c6e67bb5c7ada942a6d1884ab69338f57596f77" ]] || { echo "Expected Isaac Lab v2.3.0 source commit" >&2; exit 1; }
export UV_CONSTRAINT="$RL_PROJECT_ROOT/docs/constraints.txt $RL_PROJECT_ROOT/docs/isaacsim-constraints.txt"
export UV_BUILD_CONSTRAINT="$RL_PROJECT_ROOT/docs/build-constraints.txt"
uv pip install 'isaacsim[all,extscache]==5.1.0' --extra-index-url https://pypi.nvidia.com --index-strategy unsafe-best-match
uv pip install 'torch==2.7.0+cu128' 'torchvision==0.22.0+cu128' 'torchaudio==2.7.0+cu128' --index-url https://download.pytorch.org/whl/cu128
uv pip install -r "$RL_PROJECT_ROOT/docs/constraints.txt" \
  -e "$ISAACLAB_PATH/source/isaaclab" \
  -e "$ISAACLAB_PATH/source/isaaclab_assets" \
  -e "$ISAACLAB_PATH/source/isaaclab_tasks" \
  -e "$ISAACLAB_PATH/source/isaaclab_rl[rsl_rl]" \
  -e "$ISAACLAB_PATH/source/isaaclab_mimic"
python -m pip check | tee "$RL_PROJECT_ROOT/logs/pip-check.txt"
python -m pip freeze > "$RL_PROJECT_ROOT/docs/requirements-frozen.txt"
git -C "$ISAACLAB_PATH" rev-parse HEAD > "$RL_PROJECT_ROOT/docs/isaaclab-commit.txt"
