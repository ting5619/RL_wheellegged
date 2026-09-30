# RL_wheellegged

面向 RoboMaster 轮腿机器人的运动控制强化学习工程，使用 **Isaac Lab + Isaac Sim**。当前以华南理工 Wheelbipe V14.2 建立物理模型基线，复旦工程继续作为控制与训练设计参考。目标使用本体状态，不配置相机或视觉算法。

项目代码与公开文档保存在本仓库，运行路径由各自的检出位置决定。

最终目标是自研轮腿机器人的真机部署。自研机械与执行器参数按最终装配和实测结果配置。机械装配与建模定型前，使用华南理工方案验证算法及训练—导出—跨仿真—部署链路；自研模型定型后重新辨识、训练和验收。分阶段安排见 [项目规划 PLAN.md](PLAN.md)。

## 参考资料与来源声明

本工程在开源工作基础上进行环境适配、策略接入、验证及后续自研机器人迁移。当前采用的 Wheelbipe V14.2 模型、基础资产配置与 13k 预训练策略来自 **华南理工 SCUTRobotLab**；原作者贡献不归为本项目原创，也不将参考预训练权重描述成本项目训练成果。

| 来源 | 在本工程中的用途与当前采用情况 |
| --- | --- |
| [复旦大学轮腿 RL：fudan_rl_wheel_leg](https://github.com/yly-true/fudan_rl_wheel_leg) | 主要算法与轮腿控制参考；本轮未移植其 Isaac Gym 训练入口或策略 |
| [华南理工：wheeled-legged_RL](https://github.com/scutrobotlab/wheeled-legged_RL) | 当前直接采用的 SCUT V14.2 USD、基础资产配置、任务代码和 13k ONNX；任务源码按固定版本加载 |
| [华南理工：wheelbipe_ros2_sim2sim](https://github.com/scutrobotlab/wheelbipe_ros2_sim2sim) | 配套 ROS 2 / MuJoCo sim2sim 与 sim2real 部署参考；已核对同一 ONNX，部署链路尚未验收 |
| [XYEGA RM2026 WheelLeg RLdeploy](https://github.com/chushanxiaodaoshi/XYEGA_RM2026_WheelLeg_Infatry_RLdeploy) | 次要部署实现参考，未接入运行链路 |
| [MuJiCa](https://hyzenthlayer.github.io/mujica/) | 后续研究参考，当前运行不依赖该项目 |
| [arXiv:2605.13058](https://arxiv.org/pdf/2605.13058) | 论文参考，待进一步评审，当前不据此声明算法复现 |
| [ATRos 轮腿混合运动](https://baoziweiyuebing.github.io/ATRos-Wheeled_legged-robot-hybrid-locomotion/) | 后续研究参考，当前运行不依赖该项目 |

SCUT 训练/任务源码固定于 [`b8ff79f`](https://github.com/scutrobotlab/wheeled-legged_RL/tree/b8ff79f3df855faf9dc92f4a282bd80c42649466)，部署参考固定于 [`dd367bf`](https://github.com/scutrobotlab/wheelbipe_ros2_sim2sim/tree/dd367bf78c7e393d811595edeb4affe253156c95)。完整来源与版本见 [参考清单](docs/references.md)；移植资产和策略的逐文件 SHA-256 分别见 [模型来源](source/rl_wheellegged/assets/wheelbipe_v14_2/provenance.json)及[策略来源](source/rl_wheellegged/policies/scut_flat_13k/provenance.json)。

SCUT 采用内容保留 `Copyright (c) 2026 SCUTRobotLab` 与 [上游 MIT 许可证](licenses/SCUTRobotLab-MIT.txt)。本项目新增代码使用 [MIT](LICENSE)；其余参考项目与外部 Isaac Lab / Isaac Sim 依赖仍遵循各自许可证，不因列入参考表而改用本项目许可证。完整参考仓库、论文快照和运行环境保存在本地数据盘，不随本仓库推送。

## 当前范围

- 已移植 SCUT 原始 USD 模型及其闭环约束、质量、惯量、碰撞几何；保留机械云台，没有相机传感器。
- 已适配本地 Isaac Lab 资产配置，保留上游基础 IdealPD 执行器参数。
- 提供自由机身接触检查、悬空固定机身驱动检查和可视化入口。
- 已接入 SCUT 预训练 13k ONNX 策略及固定版本的完整 V14 任务，支持站立、前进、转向、停止和多机器人回放。
- 已保留环境安装约束、原始来源和许可证；环境、缓存、训练日志和完整参考仓库不进入 Git。

`play_scut_policy.py` 已完成参考策略闭环试运行；`sim_robot.py` 仍用于关节保持/驱动的物理基线检查。当前使用上游已有权重，尚未训练本工程轮腿策略，也未验证 MuJoCo sim2sim 或实机接口。环境通用 PPO 验收使用 Cartpole，不能当作轮腿训练结果。接入方式、接口及实测结果见 [策略接入记录](docs/policy-integration.md)。

## 快速运行

先按 [环境文档](docs/environment.md) 准备依赖，再在仓库根目录执行以下命令；已有环境无需重复安装。

```bash
# 在本仓库根目录执行
source env.sh

# RL 策略：站立→0.3 m/s 前进→0.3 rad/s 转向→停止，每段 5 秒
python scripts/play_scut_policy.py --headless --device cuda:0

# 可视化同一策略；按仿真时间节流，20 秒仿真后自动退出
python scripts/play_scut_policy.py --device cuda:0 --real_time

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

策略回放自动创建独立的 `logs/policy-时间戳/`，保存配置、网络输入输出、轨迹和验收摘要；失败或提前关闭窗口会报错。首次新机器配置须按 [策略文档](docs/policy-integration.md) 获取固定版 SCUT 任务并安装 ONNX Runtime。

以下为 `sim_robot.py` 物理基线的验收说明：需同时确认进程成功退出、报告 `status: PASS`、步数完成。报告包含 CUDA 设备、关节名称、质量、接触力、关节响应和末端整卡显存占用；默认写入 `logs/robot-check.json`。报告中的整卡显存包含桌面等其他进程，不是峰值，也不能推算大型训练显存。

## 环境

| 组件 | 固定版本 |
| --- | --- |
| Python | 3.11 |
| Isaac Sim | 5.1.0 |
| Isaac Lab | v2.3.0，`3c6e67bb5c7ada942a6d1884ab69338f57596f77` |
| PyTorch | 2.7.0 + CUDA 12.8 |
| RSL-RL | 3.0.1 |
| ONNX Runtime（CPU 推理） | 1.20.1 |

本工程已完成无视觉、小批量物理与策略接入检查；实际显存和训练吞吐需按目标硬件、模型、地形和并行数量测量。Isaac Sim 5.1 官方配置要求见[系统要求](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html)。

新机器安装方法见 [docs/environment.md](docs/environment.md)。依赖已有 Isaac 环境时可用 `python -m pip install --no-deps -e .` 安装本项目；脚本也支持从仓库直接运行。

## 工程结构

```text
PLAN.md                         # 阶段规划、当前进度与验收条件
source/rl_wheellegged/
  robot.py                       # Isaac Lab 资产配置、明确的六通道运动关节顺序
  assets/wheelbipe_v14_2/         # 原始 USD 与来源/哈希清单
  policies/scut_flat_13k/         # 参考 ONNX、历史训练配置与哈希清单
scripts/play_scut_policy.py       # 完整 SCUT 任务中的闭环策略回放与轨迹记录
scripts/fetch_scut_reference.sh   # 获取/核验固定版本的 SCUT 任务依赖
scripts/sim_robot.py              # 有限步数的物理与驱动验收、可视化
scripts/install_environment.sh    # 约束依赖安装（先按环境文档准备 uv/venv/Lab）
docs/                            # 模型说明、环境、参考资料和验收摘要
licenses/                        # 上游许可证
```

`references/` 是完整上游只读参考副本，`src/IsaacLab/` 是固定版本依赖，`envs/`、`cache/`、`runtime/`、`logs/`、`checkpoints/` 均留在数据盘并由 `.gitignore` 排除。

## 后续接入顺序

1. 在已接入的参考策略上补充长时间、反向和高度变化评测，并完成 MuJoCo 对照；现有短时试跑不等于完整 P1 验收。
2. 从少量并行环境训练平地站立、前进和转向，再扩展地形与随机化。
3. 固定策略接口后接入 MuJoCo sim2sim，核对关节顺序、符号、单位、归一化和 PD 参数。
4. 最后适配实际机器人电机、编码器、IMU 与控制周期，开展 sim2real。

本次实测结果见 [docs/validation.md](docs/validation.md)。模型结构和当前边界见 [docs/model.md](docs/model.md)，所有参考链接见 [docs/references.md](docs/references.md)。本项目代码使用 MIT；SCUT 模型和适配代码的署名及许可证见 [licenses/SCUTRobotLab-MIT.txt](licenses/SCUTRobotLab-MIT.txt)。
