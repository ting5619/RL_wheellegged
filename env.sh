# Source this file: source /mnt/data/RL_wheellegged/env.sh
export RL_PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export ISAACLAB_PATH="$RL_PROJECT_ROOT/src/IsaacLab"
export UV_CACHE_DIR="$RL_PROJECT_ROOT/cache/uv"
export UV_PYTHON_INSTALL_DIR="$RL_PROJECT_ROOT/cache/python"
export PIP_CACHE_DIR="$RL_PROJECT_ROOT/cache/pip"
export XDG_CACHE_HOME="$RL_PROJECT_ROOT/cache/xdg"
export CUDA_CACHE_PATH="$RL_PROJECT_ROOT/cache/cuda"
export __GL_SHADER_DISK_CACHE_PATH="$RL_PROJECT_ROOT/cache/gl"
export TORCH_HOME="$RL_PROJECT_ROOT/cache/torch"
export HF_HOME="$RL_PROJECT_ROOT/cache/huggingface"
export WANDB_DIR="$RL_PROJECT_ROOT/logs"
export TMPDIR="$RL_PROJECT_ROOT/tmp"
export PYTHONNOUSERSITE=1
export OMNI_KIT_ACCEPT_EULA=YES
export OMP_NUM_THREADS=4
export PATH="$RL_PROJECT_ROOT/tools/uv-x86_64-unknown-linux-gnu:$PATH"
source "$RL_PROJECT_ROOT/envs/isaaclab/bin/activate"
