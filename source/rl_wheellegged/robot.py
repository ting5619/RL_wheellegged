# =============================================================================
# Copyright (c) 2026 SCUTRobotLab
# SPDX-License-Identifier: MIT
#
# Part of the wheeled-legged_RL project.
# See LICENSE for full license terms.
#
# Authors:
#     Zhang Zhirui <2231625449@qq.com>
#     Cui Yu       <ctty694@gmail.com>
# =============================================================================

# Adapted for RL_wheellegged: local asset path and stock actuator dependencies.
from pathlib import Path
import isaaclab.sim as sim_utils
from isaaclab.assets import ArticulationCfg
from isaaclab.actuators import IdealPDActuatorCfg

USD_PATH = Path(__file__).parent / "assets/wheelbipe_v14_2/wheelbipeV14_2.usd"

DM8009_ARMATURE = 1.95e-04*9.0*9.0

WHEELBIPE_CFG = ArticulationCfg(
    spawn=sim_utils.UsdFileCfg(
        usd_path=str(USD_PATH),
        activate_contact_sensors=True,
        copy_from_source=True,
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            disable_gravity=False,
            retain_accelerations=False,
            linear_damping=0.0,
            angular_damping=0.0,
            max_linear_velocity=1000.0,
            max_angular_velocity=1000.0,
            max_depenetration_velocity=1.0,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            fix_root_link=False,
            enabled_self_collisions=False,
            solver_position_iteration_count=12,
            solver_velocity_iteration_count=6,
        ),
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        pos=(0.0, 0.0, 0.38),
        joint_pos={
            ".*_rear1_joint": 0.0,
            ".*_rear2_joint": 0.0,
            ".*_front1_joint": 0.0,
            ".*_front2_joint": 0.0,
            ".*_front3_joint": 0.0,
            ".*_front4_joint": 0.0,
            ".*_spring1_joint": 0.0,
            ".*_spring2_joint": 0.0,
            "gimbal_yaw_joint": 0.0,
            "gimbal_pitch_joint": 0.0,
        },
        joint_vel={".*": 0.0},
    ),
    actuators={
        "legs_act": IdealPDActuatorCfg(
            joint_names_expr=[
                ".*_rear1_joint",
                ".*_front1_joint",
            ],
            stiffness={
                ".*_rear1_joint": 60.0,
                ".*_front1_joint": 60.0,
            },
            damping={
                ".*_rear1_joint": 2.0,
                ".*_front1_joint": 2.0,
            },
            effort_limit={
                ".*_rear1_joint": 40.0,
                ".*_front1_joint": 40.0,
            },
            velocity_limit={
                ".*_rear1_joint": 17,
                ".*_front1_joint": 17,
            },
            armature=DM8009_ARMATURE,
        ),
        "legs_inact": IdealPDActuatorCfg(
            joint_names_expr=[
                ".*_rear2_joint",
                ".*_front2_joint",
                ".*_front3_joint",
                ".*_front4_joint",
                ".*_spring1_joint",
                ".*_guide_joint",
            ],
            stiffness=0.0,
            damping=0.01,
            armature=0.0001,
            effort_limit=50.0,
            velocity_limit=300.0,
        ),
        "wheel": IdealPDActuatorCfg(
            joint_names_expr=[".*_wheel_joint"],
            stiffness=0.0,
            damping=0.2,
            effort_limit=5.0,
            velocity_limit=60.0,
            armature=0,
        ),
        "spring": IdealPDActuatorCfg(
            joint_names_expr=[".*_spring2_joint"],
            stiffness=0.0,
            damping=50.,
            effort_limit=1000.0,
            velocity_limit=50.0,
            armature=0.0001,
        ),
        "gimbal_yaw": IdealPDActuatorCfg(
            joint_names_expr=["gimbal_yaw_joint"],
            stiffness=0.0,
            damping=0.5,
            effort_limit=2.0,
            velocity_limit=30.0,
            armature=0.0001,
        ),
        "gimbal_pitch": IdealPDActuatorCfg(
            joint_names_expr=["gimbal_pitch_joint"],
            stiffness=20.0,
            damping=0.5,
            effort_limit=10.0,
            velocity_limit=30.0,
            armature=0.0001,
        ),
    },
)

# Stable action order for this project; deployment mappings must be checked separately.
LEG_JOINTS = ("left_front1_joint", "left_rear1_joint", "right_front1_joint", "right_rear1_joint")
WHEEL_JOINTS = ("left_wheel_joint", "right_wheel_joint")
