"""Bounded Isaac Lab GPU test using local procedural geometry (no cloud assets)."""
import argparse
from pathlib import Path
from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser()
AppLauncher.add_app_launcher_args(parser)
parser.set_defaults(kit_args=f"--portable-root {Path(__file__).resolve().parents[1] / 'runtime/kit'}")
args = parser.parse_args()
app = AppLauncher(args).app

import json
import torch
import isaaclab.sim as sim_utils
from isaaclab.assets import RigidObject, RigidObjectCfg

sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=1.0 / 120.0, device=args.device))
try:
    ground_cfg = sim_utils.CuboidCfg(size=(10.0, 10.0, 0.2),
        collision_props=sim_utils.CollisionPropertiesCfg())
    ground_cfg.func('/World/Ground', ground_cfg, translation=(0.0, 0.0, -0.1))
    cube = RigidObject(RigidObjectCfg(
        prim_path='/World/Cube',
        spawn=sim_utils.CuboidCfg(size=(0.2, 0.2, 0.2),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(),
            mass_props=sim_utils.MassPropertiesCfg(mass=1.0),
            collision_props=sim_utils.CollisionPropertiesCfg()),
        init_state=RigidObjectCfg.InitialStateCfg(pos=(0.0, 0.0, 1.0)),
    ))
    sim.reset()
    start = cube.data.root_pos_w.clone()
    heights = []
    for _ in range(240):
        sim.step(render=False)
        cube.update(sim.get_physics_dt())
        heights.append(float(cube.data.root_pos_w[0, 2]))
    end = cube.data.root_pos_w.clone()
    assert torch.isfinite(end).all(), 'Non-finite physics state'
    assert start[0, 2] - end[0, 2] > 0.5, 'Body did not fall'
    assert 0.07 < end[0, 2] < 0.15, 'Body did not settle on ground'
    result = {'test': 'isaaclab_gpu_rigid_body', 'steps': 240,
              'device': str(end.device), 'initial_position': start.cpu().tolist(),
              'final_position': end.cpu().tolist(), 'min_height': min(heights), 'status': 'PASS'}
    assert end.is_cuda, 'Physics output is not on CUDA'
    (Path(__file__).resolve().parents[1] / 'logs/simulation-check.json').write_text(json.dumps(result, indent=2) + '\n')
    print('SIMULATION_SMOKE_PASS ' + json.dumps(result), flush=True)
finally:
    print("SIMULATION_CLOSING", flush=True)
    # Match ManagerBasedEnv.close(): release assets before clearing callbacks.
    if "cube" in globals():
        del cube
    sim.clear_all_callbacks()
    sim.clear_instance()
    app.close()
