# SCUT 预训练策略接入与短时闭环验证

日期：2026-09-30。已接入现成策略，在 Isaac Sim 中控制 SCUT 参考机器人运动；未进行本项目轮腿训练或真机控制。

## 参考中有什么

华南理工训练仓库包含任务代码、奖励/终止条件、PPO 配置、训练 checkpoint 及已导出的 ONNX 网络。配套 ROS 2 / MuJoCo 部署仓库包含同一策略文件和部署控制器，因此可以直接建立参考闭环，无需先从零训练。

本次选用平地/旋转的 **13k ONNX**：

- 训练来源：`scutrobotlab/wheeled-legged_RL`，提交 `b8ff79f3df855faf9dc92f4a282bd80c42649466`。
- 路径：`pretrained/26_infantry/flat_and_rotation/2026-07-19_09-14-50/exported/2026-07-19_09-14-50_13k.onnx`。
- 部署仓库提交：`dd367bf78c7e393d811595edeb4affe253156c95`；`V14-35-flat-and-rotation-13k.onnx` 与上述文件逐字节相同。
- SHA-256：`a1244761f7ede02f8c80d076d4315a25f014df43df3f7f0d20c2ca5bcd518719`。
- 项目内副本：`source/rl_wheellegged/policies/scut_flat_13k/`，同时保留历史 `training_env.yaml`、`training_agent.yaml`、哈希与 MIT 来源信息。

保存的 agent 配置是 PPO / ActorCritic，actor 隐层 256/128/64、ELU，无经验观测归一化。实际 ONNX 接口经 ONNX Runtime 检查为 `obs: float32[1,35] → actions: float32[1,6]`，没有额外循环状态输入。该目录含 `model_8000.pt`，没有与 13k 同名的原始训练 checkpoint；本次直接运行 13k ONNX，不能声称已验证它与原始 13k PyTorch checkpoint 的数值一致性。

## 本项目怎样接入

入口是 `scripts/play_scut_policy.py`。它核验参考源码提交和已跟踪文件是否被修改、策略资产哈希、网络输入输出及六关节顺序，再调用固定版本的 `WheelbipeV14Env` / `WheelbipeV14FlatEnvCfg_Play`。资产使用本工程的原始 SCUT USD，完整任务负责弹簧力、PD、观测/执行延迟及随机化。

完整任务代码仍依赖 `references/scut_wheeled-legged_RL`；本项目没有复制或安装上游整个算法包，也没有改写当前 RSL-RL。运行时仅新增 CPU ONNX Runtime 及其必要依赖，物理计算仍在 GPU 上。ONNX 的 batch 固定为 1，多机器人逐个推理，不假定支持动态 batch。

### 输入输出约定

以下下标从 0 开始。最终网络输入由原 SCUT 任务构造，命令切换当步更新指令槽位，不重复调用观测函数以免重复更新延迟历史。

| 输入下标 | 内容 | 缩放/处理 |
| --- | --- | --- |
| 0–2 | 机体系目标速度 vx、vy、wz | 比例 1；本轮 vy=0 |
| 3 | 目标高度 | 米 × 5；本轮 0.22 → 1.1 |
| 4–6 | 机体系角速度 | × 0.5 |
| 7–9 | 机体系投影重力 | 原任务定义 |
| 10–13 | 四个主动腿关节相对默认位置 | 原任务零位与顺序 |
| 14–15 | 轮位置占位 | 先置零，上游仍可能叠加位置噪声 |
| 16–21 | 四腿及两轮关节角速度 | × 0.1 |
| 22–27 | 上一策略动作 | 沿用任务缓存与裁剪 |
| 28–34 | normal 控制模式标志 | 本轮固定 `[1,0,0,0,0,0,0]` |

六动作顺序：左前腿、左后腿、右前腿、右后腿、左轮、右轮；实际 PhysX 下标 `[6,8,15,17,28,32]`，通过名称核对。四腿输出经 `0.5 rad` 缩放加默认位置，进入位置 PD；两轮输出经 `10 rad/s` 缩放进入速度 PD。网络原始输出没有擅自裁剪到 `[-1,1]`。

策略 50 Hz，物理步进 200 Hz。无相机输入或视觉算法；接触传感器和仿真真值供环境奖励、终止及评测使用，未作为额外 actor 输入。

### 配置保留与覆盖

保留上游传感器噪声、观测延迟 1–4 个物理步、执行延迟 1–3 个物理步、启动/重置质量、摩擦、PD 等随机化；保留线性弹簧作用力和腿/轮 40/5 N·m 瞬时限幅。质量随机化后每个实例不必等于原资产约 23.30 kg。

本轮覆盖：固定命令序列、固定 0.22 m 高度、关闭特殊动作模式、云台偏航目标为零、关闭周期性随机外推力、延长 episode 时间以避免正常超时；保留跌倒等终止检查。任意实例终止或提前关闭应用都会判失败，不把自动重置后的恢复当作连续通过。

历史配置与当前任务关键项对照保存为 `checkpoint-config-comparison.json`，运行配置另存 `runtime-config.json`。历史 YAML 只作为数据用 `BaseLoader` 读取，不执行其中 Python 标签。**轮速配置值 100 rad/s 与保存配置相同，但当前上游代码在初始化时乘 1.5，实际限值为 150 rad/s**；本次保留该生效行为，最终运行摘要也记录它。历史训练代码的完整状态尚未重建，因此这里验证的是固定版本任务中的策略接入，不宣称严格复现历史训练过程。

## 运行

本机已准备好依赖，可直接执行：

```bash
# 在本仓库根目录执行
source env.sh

# 无窗口：四段各 5 秒，总计 20 秒仿真时间
python scripts/play_scut_policy.py --headless --device cuda:0

# 可视化，最多按实际时间节流；物理/渲染较慢时墙钟时间会超过 20 秒
python scripts/play_scut_policy.py --device cuda:0 --real_time

# 四实例，各自保留随机化，固定随机种子
python scripts/play_scut_policy.py --headless --device cuda:0 --num_envs 4 --seed 43

# 单一站立场景 10 秒
python scripts/play_scut_policy.py --headless --device cuda:0 --scenario stand --segment_seconds 10
```

默认生成独立 `logs/policy-时间戳/`；也可指定尚不存在的 `--report_dir`，拒绝覆盖旧尝试。每次保存：

- `summary.json`：状态、实际步数、终止次数、跟踪指标、推理耗时、力矩采样统计、来源及运行版本。
- `trajectory.csv`：每个机器人每个 20 ms 的指令、位姿、速度和六关节力矩。
- `network-io.npz`：每步每实例真正送入 ONNX 的 35 维输入与 6 维输出。
- 两份配置 JSON：历史关键项对照及当前实际覆盖后的任务配置。

进程退出码为 0、`status=PASS`、步数完整共同表示短时接入检查完成；`tracking_within_initial_targets` 另外评价排除每段前 1 秒后的 vx RMSE ≤0.15 m/s、wz RMSE ≤0.20 rad/s。启动和切换过程的全部原始数据仍在 CSV 中。

新检出环境须先按 [环境文档](environment.md) 配好 Isaac，再执行：

```bash
source env.sh
bash scripts/fetch_scut_reference.sh
uv pip install --constraint docs/constraints.txt \
  --constraint docs/isaacsim-constraints.txt --requirement docs/policy-requirements.txt
python -m pip check
```

获取脚本需要网络，只在目标目录不存在时克隆；已有目录版本不符或有已跟踪修改会退出，保留原文件。策略资产已进入 wheel 包；回放脚本和固定源码依赖仍需项目检出目录。

## 2026-09-30 实测

场景统一为站立 5 s、前进 0.3 m/s 5 s、原地转向 0.3 rad/s 5 s、停止 5 s，高度目标 0.22 m。物理使用 CUDA，网络使用 CPU 推理，未进行训练更新。具体测试主机配置保存在本地记录；下述耗时仅对应本次测试，不代表其他平台性能。

| 测试 | 种子 | 环境数 | 每实例控制/物理步 | 终止/超时 | 结果 |
| --- | --- | --- | --- | --- | --- |
| 无窗口单实例 | 42 | 1 | 1000 / 4000 | 0 / 0 | PASS |
| 无窗口并行 | 43 | 4 | 1000 / 4000 | 0 / 0 | PASS |
| 有窗口、按时间节流 | 42 | 1 | 1000 / 4000 | 0 / 0 | PASS |

所有实例各阶段均通过上述初始跟踪门槛。单实例前进阶段 vx RMSE **0.0495 m/s**；转向阶段 wz RMSE **0.0956 rad/s**；各阶段高度 RMSE 约 **4.9–6.4 mm**。四实例前进 vx RMSE **0.0461–0.0679 m/s**，转向 wz RMSE **0.0860–0.1183 rad/s**。这些指标均排除每段前 1 秒，不能代表切换瞬态或正式长时成功率。

CPU 单实例 ONNX 推理 p99 约 0.103 ms；四实例一批依次推理 p99 约 0.171 ms；GUI 单实例约 0.169 ms。计时仅涵盖 ONNX 调用，不含观测拷贝、物理步进和控制通信，不能当作真机端到端周期。

20 ms 采样记录中的腿部峰值达到 **40 N·m**。并行测试四个腿通道超过 20 N·m 统计阈值的样本比例约 0.45%–0.625%。这些是各环境汇总的稀疏采样，遗漏物理子步峰值，未验证热模型、连续负载和峰值允许持续时间。

原始证据保留于 `logs/policy-sequence-attempt1/`、`logs/policy-sequence-4env-attempt1/`、`logs/policy-gui-sequence-attempt1/`，对应 stdout 在同名 `.log`。小型摘要归档于 [evidence/scut-policy-2026-09-30](evidence/scut-policy-2026-09-30/)。首次 2 秒探测记录为 `logs/scut-policy-probe-1.log`。

## 当前边界与下一步

已证明既有策略可以在本机 Isaac 环境接入并完成上述有限时长动作。尚未完成规划中的每类 5×60 s 参考评测，尚未覆盖反向、变高、抗扰、复杂地形和长期运行。GUI 入口已正常完成并退出；该记录不构成渲染外观逐帧验收。

下一步沿 [部署规划](deployment-plan.md) 扩展冻结评测，再用相同策略建立 MuJoCo 对照并核对预处理、执行器与时序差异。自研 CAD、电机曲线、弹簧参数及通信链路确定后再迁移模型和训练；当前 SCUT 策略不能直接视为自研真机部署包。
