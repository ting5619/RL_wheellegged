"""Bounded physics/actuator checks for the imported SCUT model; no trained policy."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--steps", type=int, default=400)
parser.add_argument("--fixed_base", action="store_true", help="Suspend the chassis to check leg/wheel actuation.")
parser.add_argument("--report", type=Path, default=ROOT / "logs/robot-check.json")
AppLauncher.add_app_launcher_args(parser)
parser.set_defaults(kit_args=f"--portable-root {ROOT / 'runtime/kit'}")
args = parser.parse_args()
if not 1 <= args.num_envs <= 64 or args.steps < 200:
    parser.error("Use 1..64 environments and at least 200 steps for the bounded check.")
if args.enable_cameras:
    parser.error("This locomotion baseline has no camera sensors.")
app = AppLauncher(args).app

import torch
from pxr import Usd, UsdPhysics, UsdUtils
import isaacsim
import isaaclab.sim as sim_utils
from isaaclab.assets import AssetBaseCfg
from isaaclab.scene import InteractiveScene, InteractiveSceneCfg
from isaaclab.sensors import ContactSensorCfg
from isaaclab.utils import configclass
from rl_wheellegged.robot import LEG_JOINTS, WHEEL_JOINTS, USD_PATH, WHEELBIPE_CFG


def audit_asset():
    manifest = json.loads((USD_PATH.parent / "provenance.json").read_text())
    for relative, digest in manifest["files"].items():
        assert hashlib.sha256((USD_PATH.parent / relative).read_bytes()).hexdigest() == digest, relative
    # OmniPBR is a bundled Kit MDL, not a missing mesh or external download.
    mdl_dir = Path(isaacsim.__file__).parent / "kit/mdl/core/Base"
    assert (mdl_dir / "OmniPBR.mdl").is_file(), "Kit material library missing"
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(USD_PATH))
    # USD dependency scanning does not use the Kit MDL search path.
    missing = [name for name in unresolved if name != "OmniPBR.mdl"]
    assert not missing, f"Unresolved asset dependencies: {missing}"
    stage = Usd.Stage.Open(str(USD_PATH))
    joints = [p for p in stage.Traverse() if p.IsA(UsdPhysics.Joint)]
    loops = [str(p.GetPath()) for p in joints if UsdPhysics.Joint(p).GetExcludeFromArticulationAttr().Get()]
    cameras = [str(p.GetPath()) for p in stage.Traverse() if p.GetTypeName() == "Camera"]
    assert not cameras, f"Unexpected cameras: {cameras}"
    return {"source_commit": manifest["commit"], "verified_usd_files": len(manifest["files"]),
            "resolved_layers": len(layers), "resolved_assets": len(assets),
            "kit_bundled_materials": ["OmniPBR.mdl"],
            "usd_joints": len(joints), "loop_constraint_paths": loops, "camera_prims": cameras}


@configclass
class RobotSceneCfg(InteractiveSceneCfg):
    ground = AssetBaseCfg(
        prim_path="/World/Ground",
        spawn=sim_utils.CuboidCfg(size=(40.0, 40.0, 0.2),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            physics_material=sim_utils.RigidBodyMaterialCfg(static_friction=1.0, dynamic_friction=1.0)),
        init_state=AssetBaseCfg.InitialStateCfg(pos=(0.0, 0.0, -0.1)),
    )
    light = AssetBaseCfg(prim_path="/World/Light", spawn=sim_utils.DomeLightCfg(intensity=2000.0))
    robot = WHEELBIPE_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
    contacts = ContactSensorCfg(prim_path="{ENV_REGEX_NS}/Robot/.*", update_period=0.0, history_length=1)


def main():
    audit = audit_asset()
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=0.005, device=args.device))
    scene = None
    robot = None
    try:
        cfg = RobotSceneCfg(num_envs=args.num_envs, env_spacing=3.0, replicate_physics=False)
        if args.fixed_base:
            cfg.robot.spawn.articulation_props.fix_root_link = True
            cfg.robot.init_state.pos = (0.0, 0.0, 1.0)
        scene = InteractiveScene(cfg)
        sim.set_camera_view((2.5, 2.5, 1.7), (0.0, 0.0, 0.4))
        sim.reset()
        robot = scene["robot"]
        leg_ids, leg_names = robot.find_joints(list(LEG_JOINTS), preserve_order=True)
        wheel_ids, wheel_names = robot.find_joints(list(WHEEL_JOINTS), preserve_order=True)
        assert leg_names == list(LEG_JOINTS) and wheel_names == list(WHEEL_JOINTS)
        masses = robot.root_physx_view.get_masses()
        inertias = robot.root_physx_view.get_inertias().reshape(args.num_envs, -1, 3, 3)
        assert torch.isfinite(masses).all() and (masses > 0).all(), "Invalid mass"
        assert torch.isfinite(inertias).all() and (torch.linalg.eigvalsh(inertias) > 0).all(), "Invalid inertia"
        root = robot.data.default_root_state.clone()
        root[:, :3] += scene.env_origins
        robot.write_root_pose_to_sim(root[:, :7])
        robot.write_root_velocity_to_sim(root[:, 7:])
        robot.write_joint_state_to_sim(robot.data.default_joint_pos.clone(), robot.data.default_joint_vel.clone())
        scene.reset()
        peak_contact = torch.zeros(args.num_envs, device=sim.device)
        peak_wheel = torch.zeros((args.num_envs, 2), device=sim.device)
        peak_leg = torch.zeros((args.num_envs, 4), device=sim.device)
        initial = root[:, :3].clone()
        z_min, z_max = float(initial[:, 2].min()), float(initial[:, 2].max())
        steps = 0
        for step in range(args.steps):
            if not app.is_running():
                raise RuntimeError("Simulation closed before the bounded check completed")
            positions = robot.data.default_joint_pos.clone()
            velocities = torch.zeros_like(robot.data.default_joint_vel)
            if args.fixed_base:
                positions[:, leg_ids] += 0.03 * math.sin(2.0 * math.pi * step * sim.get_physics_dt())
                velocities[:, wheel_ids] = 1.0
            robot.set_joint_position_target(positions)
            robot.set_joint_velocity_target(velocities)
            scene.write_data_to_sim()
            sim.step(render=not args.headless)
            scene.update(sim.get_physics_dt())
            state = robot.data.root_state_w
            assert torch.isfinite(state).all() and torch.isfinite(robot.data.joint_pos).all()
            assert torch.isfinite(robot.data.joint_vel).all() and torch.isfinite(robot.data.applied_torque).all()
            relative = state[:, :3] - scene.env_origins
            assert (relative[:, 2] > -0.2).all() and (relative.abs() < 5.0).all(), "Body escaped bounded scene"
            z_min = min(z_min, float(relative[:, 2].min()))
            z_max = max(z_max, float(relative[:, 2].max()))
            forces = scene["contacts"].data.net_forces_w
            assert torch.isfinite(forces).all()
            peak_contact = torch.maximum(peak_contact, forces.norm(dim=-1).amax(dim=-1))
            peak_wheel = torch.maximum(peak_wheel, robot.data.joint_vel[:, wheel_ids].abs())
            peak_leg = torch.maximum(peak_leg, (robot.data.joint_pos[:, leg_ids] - robot.data.default_joint_pos[:, leg_ids]).abs())
            steps += 1
        if args.fixed_base:
            assert (peak_wheel > 0.2).all(), "One or more wheels did not respond"
            assert (peak_leg > 0.003).all(), "One or more active leg joints did not respond"
            assert torch.max(torch.abs(robot.data.root_pos_w - initial)) < 0.001, "Fixed chassis moved"
        else:
            assert (peak_contact > 1.0).all(), "One or more robots never contacted the ground"
        assert robot.data.root_state_w.is_cuda if args.device.startswith("cuda") else True
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, check=False).stdout.strip()
        result = {"status": "PASS", "test": "fixed_base_actuation" if args.fixed_base else "free_base_contact",
            "steps": steps, "dt": sim.get_physics_dt(), "num_envs": args.num_envs,
            "device": str(robot.data.root_state_w.device), "audit": audit,
            "body_count": robot.num_bodies, "joint_count": robot.num_joints,
            "joint_names": robot.joint_names, "leg_action_order": leg_names, "wheel_action_order": wheel_names,
            "mass_kg": masses.sum(dim=1).cpu().tolist(), "root_height_range_m": [z_min, z_max],
            "final_root_position": robot.data.root_pos_w.cpu().tolist(),
            "peak_contact_force_N": peak_contact.cpu().tolist(),
            "peak_wheel_speed_rad_s": peak_wheel.cpu().tolist(), "peak_leg_excursion_rad": peak_leg.cpu().tolist(),
            "gpu_memory_used_total_MiB_at_end_including_other_processes": gpu,
            "policy": "None; default joint hold or suspended actuator test. No balance claim."}
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n")
        print("ROBOT_CHECK_PASS " + json.dumps(result), flush=True)
    finally:
        # Release PhysX views/callbacks before closing Kit, matching the Lab environment lifecycle.
        del robot
        del scene
        sim.clear_all_callbacks()
        sim.clear_instance()


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        import traceback
        traceback.print_exc()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"status": "FAIL", "error": repr(exc)}, indent=2) + "\n")
        print("ROBOT_CHECK_FAIL " + repr(exc), flush=True)
        app.app.post_quit(1)
        raise
    finally:
        app.close()
