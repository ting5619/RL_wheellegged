# 环境与复现

本机已完成环境安装，优先直接 `source /mnt/data/RL_wheellegged/env.sh` 使用。所有环境、源码依赖、缓存、临时文件和日志保存在项目数据盘目录，Git 只保存工程、模型与可复现配置。

## 固定版本

Python 3.11，Isaac Sim 5.1.0，Isaac Lab v2.3.0（`3c6e67bb5c7ada942a6d1884ab69338f57596f77`），PyTorch 2.7.0+cu128，RSL-RL 3.0.1。主机已有 NVIDIA 驱动；运行这些预编译包不要求额外安装系统 CUDA Toolkit。

安装脚本使用 `constraints.txt`、`isaacsim-constraints.txt` 和 `build-constraints.txt`，避免 Sim 与 Lab 的传递依赖冲突。本机曾发现 Lab v2.3.2 的 Starlette 依赖与此 Sim 版本的 FastAPI 依赖不一致，因此使用已通过 `pip check` 和运行验收的官方 v2.3.0，不改写上游依赖要求。

## 新检出目录的准备步骤

以下是新环境复现说明，不需要在已有安装上重做。先准备 Linux x86_64 的 `uv` 命令和兼容 NVIDIA 驱动，`uv` 安装方法见[官方文档](https://docs.astral.sh/uv/getting-started/installation/)。本机的 uv 位于 `tools/uv-x86_64-unknown-linux-gnu/uv`。

在检出的项目根目录运行：

```bash
mkdir -p cache/uv cache/python cache/pip cache/xdg cache/cuda cache/gl \
  cache/torch cache/huggingface tmp logs runtime/kit src envs
export UV_CACHE_DIR="$PWD/cache/uv"
export UV_PYTHON_INSTALL_DIR="$PWD/cache/python"
export TMPDIR="$PWD/tmp"
uv python install 3.11
uv venv --python 3.11 --seed envs/isaaclab

git clone --branch v2.3.0 --depth 1 https://github.com/isaac-sim/IsaacLab.git src/IsaacLab
bash scripts/install_environment.sh
source env.sh
python -m pip install --no-deps -e .
```

安装脚本会校验 Isaac Lab 提交、安装约束版本、执行 `pip check` 并记录环境冻结清单。下载需联网；Isaac 许可接受通过 `env.sh` 的 `OMNI_KIT_ACCEPT_EULA=YES` 配置，使用者需阅读并接受相应许可。本项目使用独立的构建环境及 `packaging==24.2` 解析许可证元数据，不升级 Isaac 运行环境中受约束的 `packaging==23.0`。完整参考仓库不是运行本地模型的依赖。

## 验收

```bash
source env.sh
python -m pip check
python scripts/check_torch.py
python scripts/sim_robot.py --headless --device cuda:0
python scripts/sim_robot.py --headless --device cuda:0 --fixed_base \
  --report logs/robot-fixed-1.json
```

已有 `scripts/smoke_sim.py` 可验证简单 GPU 刚体落地，`scripts/train_cartpole.sh` 可运行 64 环境、5 次 PPO 更新的环境通用检查。这些脚本沿用环境搭建阶段的验收用途。

训练规模从小开始。模型无视觉可减少显存开销，但不会消除 Kit、PhysX、地形、接触缓冲区和训练网络的资源需求；当前物理验收显存快照不代表 PPO 训练峰值。
