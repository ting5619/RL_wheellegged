# 参考资料与来源固定

记录日期：2026-09-30。下列 SHA 固定本次查看的源码，不自动跟随上游更新。

| 用途 | 来源 | 本地副本 | 提交 |
| --- | --- | --- | --- |
| 当前物理模型、任务与预训练策略来源 | [SCUT wheeled-legged_RL](https://github.com/scutrobotlab/wheeled-legged_RL) | `references/scut_wheeled-legged_RL` | `b8ff79f3df855faf9dc92f4a282bd80c42649466` |
| 配套 sim2sim / sim2real 部署参考 | [SCUT wheelbipe_ros2_sim2sim](https://github.com/scutrobotlab/wheelbipe_ros2_sim2sim) | `references/scut_wheelbipe_ros2_sim2sim` | `dd367bf78c7e393d811595edeb4affe253156c95` |
| 主要算法与轮腿控制参考 | [复旦 fudan_rl_wheel_leg](https://github.com/yly-true/fudan_rl_wheel_leg) | `references/fudan_rl_wheel_leg` | `8204e853dfd2ed06d85a322e1a998c3d20a3be2c` |
| 其他部署参考 | [XYEGA RM2026](https://github.com/chushanxiaodaoshi/XYEGA_RM2026_WheelLeg_Infatry_RLdeploy) | `references/XYEGA_RM2026_WheelLeg_Infatry_RLdeploy` | `fcfdd3959be5c9b00893ec0701a591ddbf55b830` |

选择 SCUT 作为首个模型来源：其训练仓库明确使用 Isaac Lab / Isaac Sim，并给出 Sim 5.1、Lab 2.3.x 的兼容环境，仓库内已有 Wheelbipe V14.2 USD。复旦工程基于 Isaac Gym Preview 4，迁移其训练入口的工作更多。

已移植 SCUT 基础资产配置和一组 USD 文件，并接入 13k ONNX 预训练策略；完整 V14 任务从固定版本参考副本加载，没有安装其完整定制算法包。模型与策略均保留 MIT 署名。逐文件 SHA-256 分别位于 `source/rl_wheellegged/assets/wheelbipe_v14_2/provenance.json` 与 `source/rl_wheellegged/policies/scut_flat_13k/provenance.json`；策略目录同时保存对应历史训练配置。接入结果见 [策略记录](policy-integration.md)。

SCUT 部署仓库的说明基于 Ubuntu 22.04 / ROS 2 Humble、MuJoCo 3.5.0 和 CPU ONNX Runtime。它作为后续接口参考保存在数据盘，尚未安装或启动；本机现有 Ubuntu 24.04 / ROS 环境未因此更换。已在 Isaac 回放中核验选定 ONNX 的 35 维 normal-only 输入、6 维动作和关节顺序；MuJoCo / ROS 2 端预处理、执行器与时序尚未闭环验证，因此不宣称部署接口已完全兼容。

其他用户提供资料（保留为后续研究参考，当前模型不依赖它们）：

- [MuJiCa 项目](https://hyzenthlayer.github.io/mujica/)
- [arXiv:2605.13058](https://arxiv.org/pdf/2605.13058)
- [ATRos 轮腿混合运动](https://baoziweiyuebing.github.io/ATRos-Wheeled_legged-robot-hybrid-locomotion/)

本地网页、论文和完整仓库快照位于被 Git 排除的 `docs/references/` 和 `references/`；正式仓库保存来源说明、实际采用的模型和小型参考 ONNX，其他来源不因此视为已采用或已复现。
