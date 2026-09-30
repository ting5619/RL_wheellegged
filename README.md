# RL_wheellegged

面向 RoboMaster 轮腿机器人的运动控制强化学习工程，使用 **Isaac Lab + Isaac Sim**。当前以华南理工 Wheelbipe V14.2 建立物理模型基线，复旦工程继续作为控制与训练设计参考。目标使用本体状态，不配置相机或视觉算法。

实际工程位于 `/mnt/data/RL_wheellegged`；Git 远端为 <https://github.com/ting5619/RL_wheellegged>。

## 当前范围

- 已移植 SCUT 原始 USD 模型及其闭环约束、质量、惯量、碰撞几何；保留机械云台，没有相机传感器。
- 已适配本地 Isaac Lab 资产配置，保留上游基础 IdealPD 执行器参数。
- 提供自由机身接触检查、悬空固定机身驱动检查和可视化入口。
- 已保留环境安装约束、原始来源和许可证；环境、缓存、训练日志和完整参考仓库不进入 Git。

当前入口使用关节默认位置保持或小幅驱动测试，**没有训练好的平衡策略，也尚未移植轮腿 RL 任务、策略导出和实机接口**。自由机身运行时机器人可能倾倒，这是基线检查的预期边界。环境通用 PPO 验收使用 Cartpole，不能当作轮腿训练结果。

## 快速运行

本机环境已经安装，无需重复下载。

```bash
cd /mnt/data/RL_wheellegged
source env.sh

# 默认姿态保持、落地接触：400 步，2 秒仿真时间
python scripts/sim_robot.py --headless --device cuda:0

# 小规模并行：16 个机器人
python scripts/sim_robot.py --headless --device cuda:0 --num_envs 16 \
  --report logs/robot-free-16.json

# 悬空固定机身：四个主动腿关节和两个轮子的响应检查
python scripts/sim_robot.py --headless --device cuda:0 --fixed_base \
  --report logs/robot-fixed-1.json

# 显示模型并观察驱动（不使用 headless；20 秒仿真时间）
python scripts/sim_robot.py --device cuda:0 --fixed_base --steps 4000
```

验收需同时确认进程成功退出、报告 `status: PASS`、步数完成。报告包含 CUDA 设备、关节名称、质量、接触力、关节响应和末端整卡显存占用；默认写入 `logs/robot-check.json`。报告中的整卡显存包含桌面等其他进程，不是峰值，也不能推算大型训练显存。

## 环境

| 组件 | 固定版本 |
| --- | --- |
| Python | 3.11 |
| Isaac Sim | 5.1.0 |
| Isaac Lab | v2.3.0，`3c6e67bb5c7ada942a6d1884ab69338f57596f77` |
| PyTorch | 2.7.0 + CUDA 12.8 |
| RSL-RL | 3.0.1 |

本机为 Ubuntu 24.04、32 GB 内存、RTX 4060 Laptop 8 GB，使用已有驱动。8 GB 用于无视觉、小批量物理基线已有实测；后续训练仍需根据模型、地形和并行数量测量。Isaac Sim 5.1 官方配置要求见[系统要求](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html)。

新机器安装方法见 [docs/environment.md](docs/environment.md)。依赖已有 Isaac 环境时可用 `python -m pip install --no-deps -e .` 安装本项目；脚本也支持从仓库直接运行。

## 工程结构

```text
source/rl_wheellegged/
  robot.py                       # Isaac Lab 资产配置、明确的六通道运动关节顺序
  assets/wheelbipe_v14_2/         # 原始 USD 与来源/哈希清单
scripts/sim_robot.py              # 有限步数的物理与驱动验收、可视化
scripts/install_environment.sh    # 约束依赖安装（先按环境文档准备 uv/venv/Lab）
docs/                            # 模型说明、环境、参考资料和验收摘要
licenses/                        # 上游许可证
```

`references/` 是完整上游只读参考副本，`src/IsaacLab/` 是固定版本依赖，`envs/`、`cache/`、`runtime/`、`logs/`、`checkpoints/` 均留在数据盘并由 `.gitignore` 排除。

## 后续接入顺序

1. 在现有模型上定义速度跟踪任务，核对观测、动作缩放、控制周期、奖励与终止条件。
2. 从少量并行环境训练平地站立、前进和转向，再扩展地形与随机化。
3. 固定策略接口后接入 MuJoCo sim2sim，核对关节顺序、符号、单位、归一化和 PD 参数。
4. 最后适配实际机器人电机、编码器、IMU 与控制周期，开展 sim2real。

本次实测结果见 [docs/validation.md](docs/validation.md)。模型结构和当前边界见 [docs/model.md](docs/model.md)，所有参考链接见 [docs/references.md](docs/references.md)。本项目代码使用 MIT；SCUT 模型和适配代码的署名及许可证见 [licenses/SCUTRobotLab-MIT.txt](licenses/SCUTRobotLab-MIT.txt)。
