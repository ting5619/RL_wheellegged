"""Bounded ONNX replay in the pinned SCUT V14 Isaac Lab task (no training/hardware)."""
import argparse
import csv
from datetime import datetime
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "references/scut_wheeled-legged_RL"
EXPECTED_COMMIT = "b8ff79f3df855faf9dc92f4a282bd80c42649466"
POLICY_DIR = ROOT / "source/rl_wheellegged/policies/scut_flat_13k"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--num_envs", type=int, default=1)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--scenario", choices=["sequence", "stand", "forward", "turn"], default="sequence")
parser.add_argument("--segment_seconds", type=float, default=5.0)
parser.add_argument("--report_dir", type=Path)
parser.add_argument("--real_time", action="store_true", help="Pace GUI playback to simulated time.")
from isaaclab.app import AppLauncher
AppLauncher.add_app_launcher_args(parser)
parser.set_defaults(kit_args=f"--portable-root {ROOT / 'runtime/kit'}")
args = parser.parse_args()
if not 1 <= args.num_envs <= 16 or not 2.0 <= args.segment_seconds <= 120.0:
    parser.error("Use 1..16 robots and 2..120 seconds per segment.")
if args.enable_cameras:
    parser.error("This reference replay does not enable camera sensors.")
if not REFERENCE.is_dir():
    parser.error("Pinned SCUT task source missing; run bash scripts/fetch_scut_reference.sh")
commit = subprocess.check_output(["git", "-C", str(REFERENCE), "rev-parse", "HEAD"], text=True).strip()
if commit != EXPECTED_COMMIT:
    parser.error(f"Unexpected SCUT source commit: {commit}")
if subprocess.run(["git", "-C", str(REFERENCE), "diff", "--quiet", "HEAD"]).returncode:
    parser.error("SCUT reference has tracked modifications; preserve it and restore a clean pinned checkout.")
manifest = json.loads((POLICY_DIR / "provenance.json").read_text())
for name, sha in manifest["files"].items():
    if hashlib.sha256((POLICY_DIR / name).read_bytes()).hexdigest() != sha:
        parser.error(f"Policy artifact hash mismatch: {name}")
args.report_dir = (args.report_dir or ROOT / "logs" / datetime.now(ZoneInfo("Asia/Shanghai")).strftime("policy-%Y%m%d-%H%M%S")).resolve()
args.report_dir.mkdir(parents=True, exist_ok=False)
print(f"POLICY_REPORT_DIR={args.report_dir}", flush=True)
for path in [REFERENCE, REFERENCE / "source/agent_world", REFERENCE / "source/agent_tasks"]:
    sys.path.insert(0, str(path))
app = AppLauncher(args).app


def main():
    import numpy as np
    import onnxruntime as ort
    import torch
    import yaml
    from agent_tasks.direct.wheelbipe.wheelbipe_V14.env_cfg import WheelbipeV14FlatEnvCfg_Play
    from agent_tasks.direct.wheelbipe.wheelbipe_V14.env import WheelbipeV14Env
    from isaaclab.utils.math import euler_xyz_from_quat, wrap_to_pi

    commands = {"stand": (0.0, 0.0), "forward": (0.3, 0.0), "turn": (0.0, 0.3), "stop": (0.0, 0.0)}
    phases = ["stand", "forward", "turn", "stop"] if args.scenario == "sequence" else [args.scenario]
    cfg = WheelbipeV14FlatEnvCfg_Play()
    saved = yaml.load((POLICY_DIR / "training_env.yaml").read_text(), Loader=yaml.BaseLoader)
    # Compare historically saved values to the current pinned task; never execute YAML tags.
    compare_keys = ["decimation", "observation_space", "action_space", "spring_settings", "leg_action_scale",
                    "wheel_vel_action_scale", "max_wheel_vel", "obs_input_clip_cfg", "obs_input_scale_cfg",
                    "use_obs_delay", "use_act_delay", "obs_delay_cfg", "act_delay_cfg"]
    comparison = {key: {"checkpoint": saved.get(key), "current_task": getattr(cfg, key, None)} for key in compare_keys}
    (args.report_dir / "checkpoint-config-comparison.json").write_text(json.dumps(comparison, indent=2, default=str) + "\n")
    cfg.seed = args.seed
    cfg.scene.num_envs = args.num_envs
    cfg.scene.replicate_physics = False
    cfg.sim.device = args.device
    cfg.episode_length_s = len(phases) * args.segment_seconds + 10.0
    cfg.robot_cfg.spawn.usd_path = str(ROOT / "source/rl_wheellegged/assets/wheelbipe_v14_2/wheelbipeV14_2.usd")
    cfg.commands.heading_command = False
    cfg.commands.ranges.heading = None
    cfg.commands.ranges.lin_vel_x = (0.0, 0.0)
    cfg.commands.ranges.lin_vel_y = (0.0, 0.0)
    cfg.commands.ranges.ang_vel_z = (0.0, 0.0)
    cfg.commands.resampling_time_range = (1000000.0, 1000000.0)
    cfg.commands.rel_standing_envs = 0.0
    cfg.commands.rel_heading_envs = 0.0
    cfg.commands.special_modes = {}
    cfg.commands.debug_vis = False
    cfg.height_range = [0.22, 0.22]
    cfg.gimbal_yaw_velocity_range = (0.0, 0.0)
    cfg.play_keep_done_reset = True
    # Keep termination checks; remove unsolicited random external pushes for this first command trial.
    cfg.events.push_robot = None
    cfg.events.base_external_force_torque_xyz = None
    for name in vars(cfg):
        if name.startswith("play_") and ("debug" in name or name.endswith("_vis")):
            setattr(cfg, name, False)
    assert cfg.height_scanner is None and cfg.use_absolute_height
    assert cfg.observation_space == 35 and cfg.action_space == 6
    assert abs(cfg.sim.dt * cfg.decimation - 0.02) < 1e-9
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(POLICY_DIR / "policy.onnx"), sess_options=options, providers=["CPUExecutionProvider"])
    assert [(v.name, v.shape, v.type) for v in session.get_inputs()] == [("obs", [1, 35], "tensor(float)")]
    assert [(v.name, v.shape, v.type) for v in session.get_outputs()] == [("actions", [1, 6], "tensor(float)")]
    (args.report_dir / "runtime-config.json").write_text(json.dumps(cfg.to_dict(), indent=2, default=str) + "\n")
    env = None
    observations, actions, inference_ms, samples = [], [], [], []
    done_count = timeout_count = completed_steps = 0
    error = None
    steps_per_phase = round(args.segment_seconds / 0.02)
    summary = {"status": "RUNNING", "source_commit": commit,
               "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "runtime_versions": {name: version(name) for name in ["isaacsim", "isaaclab", "torch", "onnxruntime"]}, "policy_sha256": manifest["files"]["policy.onnx"],
               "seed": args.seed, "num_envs": args.num_envs, "scenario": args.scenario,
               "segment_seconds": args.segment_seconds, "policy_hz": 50, "physics_hz": 200,
               "task_class": "WheelbipeV14FlatEnvCfg_Play", "actor_inputs": 35, "actions": 6,
               "overrides": ["fixed command schedule and 0.22m target", "no special command modes", "zero gimbal yaw target",
                             "interval external pushes disabled", "local USD", "debug markers disabled", "episode timeout extended"],
               "retained": ["task spring forces", "upstream sensor noise and delays", "upstream actuator delays",
                            "upstream startup/reset randomization", "leg torque cap 40Nm; wheel torque cap 5Nm"],
               "scope": "Reference ONNX integration trial; not a reproduction of the historical training run or hardware validation."}
    try:
        env = WheelbipeV14Env(cfg)
        obs, _ = env.reset()
        actual_names = [env.robot.joint_names[i] for i in env._actuate_idx]
        assert actual_names == manifest["action_order"], actual_names
        summary["action_order"] = actual_names
        summary["joint_indices"] = list(env._actuate_idx)
        summary["effective_wheel_velocity_limit_rad_s"] = env.max_wheel_vel
        summary["body_mass_kg"] = env.robot.root_physx_view.get_masses().sum(dim=1).cpu().tolist()
        for step in range(steps_per_phase * len(phases)):
            tick = time.perf_counter()
            if not app.is_running():
                raise RuntimeError("Application closed before the requested trial completed")
            phase_id = step // steps_per_phase
            phase = phases[phase_id]
            vx, wz = commands[phase]
            env.command_generator.vel_command_b[:] = torch.tensor([vx, 0.0, wz], device=env.device)
            env.height_cmd.fill_(0.22)
            # Commands are exogenous; replace their slots for this tick without appending sensor history twice.
            policy_obs = obs["policy"].clone()
            policy_obs[:, :3] = torch.tensor([vx, 0.0, wz], device=env.device)
            policy_obs[:, 3] = 1.1
            assert policy_obs.shape == (args.num_envs, 35) and torch.isfinite(policy_obs).all()
            expected_mode = torch.tensor([1., 0., 0., 0., 0., 0., 0.], device=env.device)
            assert torch.allclose(policy_obs[:, 28:35], expected_mode.expand(args.num_envs, -1)), "Non-normal policy mode"
            values = policy_obs.cpu().numpy().astype(np.float32)
            before = time.perf_counter()
            # Exported batch size is fixed at one; evaluate each robot explicitly.
            output = np.concatenate([session.run(["actions"], {"obs": row[None, :]})[0] for row in values], axis=0)
            inference_ms.append((time.perf_counter() - before) * 1000.0)
            assert output.shape == (args.num_envs, 6) and np.isfinite(output).all()
            observations.append(values.copy())
            actions.append(output.copy())
            obs, reward, terminated, truncated, _ = env.step(torch.as_tensor(output, device=env.device))
            completed_steps += 1
            done_count += int(terminated.sum())
            timeout_count += int(truncated.sum())
            if terminated.any() or truncated.any():
                raise RuntimeError(f"Environment terminated at control step {step}: done={terminated.tolist()}, timeout={truncated.tolist()}")
            robot = env.robot
            for state in [robot.data.root_state_w, robot.data.joint_pos, robot.data.joint_vel, robot.data.applied_torque, reward]:
                assert torch.isfinite(state).all(), "Non-finite physical state/reward"
            if hasattr(env, "_obs_raw_policy_has_nonfinite"):
                assert not env._obs_raw_policy_has_nonfinite.any(), "Raw observation was non-finite before upstream sanitation"
            assert torch.all(robot.data.root_pos_w[:, 2] > 0.1), "Chassis height below trial boundary"
            rpy = torch.stack([wrap_to_pi(v) for v in euler_xyz_from_quat(robot.data.root_quat_w)], dim=1).cpu().numpy()
            states = torch.cat([robot.data.root_pos_w, robot.data.root_lin_vel_b, robot.data.root_ang_vel_b], dim=-1).cpu().numpy()
            torque = robot.data.applied_torque[:, env._actuate_idx].cpu().numpy()
            for index in range(args.num_envs):
                samples.append({"time_s": (step + 1) * 0.02, "env_id": index, "phase": phase,
                    "phase_time_s": (step % steps_per_phase + 1) * 0.02,
                    "command_vx": vx, "command_wz": wz, "height_command": 0.22,
                    "x": float(states[index, 0]), "y": float(states[index, 1]), "z": float(states[index, 2]),
                    "vx": float(states[index, 3]), "vy": float(states[index, 4]), "wz": float(states[index, 8]),
                    "roll_rad": float(rpy[index, 0]), "pitch_rad": float(rpy[index, 1]),
                    **{f"torque_{j}_Nm": float(torque[index, j]) for j in range(6)}})
            if step % 250 == 0:
                print(f"POLICY_STEP {step} phase={phase} z={states[:, 2].tolist()} vx={states[:, 3].tolist()} wz={states[:, 8].tolist()}", flush=True)
            if args.real_time:
                time.sleep(max(0.0, 0.02 - (time.perf_counter() - tick)))
        summary["status"] = "PASS"
    except BaseException as exc:
        error = exc
        summary["status"] = "FAIL"
        summary["error"] = repr(exc)
        traceback.print_exc()
    finally:
        if env is not None:
            env.close()
        np.savez_compressed(args.report_dir / "network-io.npz", observations=np.asarray(observations), actions=np.asarray(actions))
        if samples:
            with (args.report_dir / "trajectory.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(samples[0]))
                writer.writeheader()
                writer.writerows(samples)
        metrics = []
        for index in range(args.num_envs):
            for phase in phases:
                rows = [r for r in samples if r["env_id"] == index and r["phase"] == phase and r["phase_time_s"] > 1.0]
                if rows:
                    metrics.append({"env_id": index, "phase": phase, "samples": len(rows),
                        "vx_rmse_m_s": float(np.sqrt(np.mean([(r["vx"]-r["command_vx"])**2 for r in rows]))),
                        "wz_rmse_rad_s": float(np.sqrt(np.mean([(r["wz"]-r["command_wz"])**2 for r in rows]))),
                        "height_rmse_m": float(np.sqrt(np.mean([(r["z"]-.22)**2 for r in rows]))),
                        "max_abs_roll_pitch_rad": max(max(abs(r["roll_rad"]), abs(r["pitch_rad"])) for r in rows)})
        summary.update({"control_steps": completed_steps, "physics_steps": completed_steps * cfg.decimation,
                        "inference_steps": len(actions),
                        "completed_state_samples": len(samples), "terminations": done_count, "timeouts": timeout_count,
                        "inference_batch_p99_ms": float(np.percentile(inference_ms, 99)) if inference_ms else None,
                        "metrics_after_1s_each_phase": metrics,
                        "tracking_within_initial_targets": summary["status"] == "PASS" and len(metrics) == args.num_envs * len(phases) and all(m["vx_rmse_m_s"]<=.15 and m["wz_rmse_rad_s"]<=.20 for m in metrics)})
        if samples:
            torques = np.array([[r[f"torque_{j}_Nm"] for j in range(4)] for r in samples])
            summary["leg_torque_peak_sampled_Nm"] = np.max(np.abs(torques), axis=0).tolist()
            summary["leg_over_20Nm_fraction_sampled"] = np.mean(np.abs(torques) > 20, axis=0).tolist()
            summary["torque_sampling_note"] = "End of each 20ms policy step only; not 5ms peak or thermal validation."
        (args.report_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print("POLICY_TRIAL_" + summary["status"] + " " + str(args.report_dir / "summary.json"), flush=True)
    if error is not None:
        raise RuntimeError("Policy integration trial failed; see saved evidence") from error


try:
    main()
except BaseException as exc:
    if not (args.report_dir / "summary.json").exists():
        (args.report_dir / "summary.json").write_text(json.dumps({"status": "FAIL", "error": repr(exc)}, indent=2) + "\n")
    traceback.print_exc()
    app.app.post_quit(1)
    raise
finally:
    app.close()
