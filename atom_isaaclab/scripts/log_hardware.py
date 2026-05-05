# Copyright (c) 2022-2026, The Isaac Lab Project Developers.
# SPDX-License-Identifier: BSD-3-Clause

"""Log joint torques and reaction forces during a play session for hardware suitability analysis.

Records:
  1. Per-joint motor torques (applied + commanded/pre-clipping) for actuator sizing
  2. Per-joint 6-DOF reaction wrenches (fx, fy, fz, tx, ty, tz) for bearing analysis

Usage (from atom_isaaclab/):
    conda activate env_isaaclab
    MPLBACKEND=Agg /home/atoms/IsaacLab/isaaclab.sh -p scripts/log_hardware.py \
        --task Isaac-Velocity-Flat-Atom-Play-v0 --num_envs 1 --load_run <run_id> \
        --steps 1000 --headless

Outputs (into the run's log directory):
    hardware_stats.txt      — combined torque + force statistics
    torque_log.csv          — per-step, per-joint applied + commanded torques
    joint_force_log.csv     — per-step, per-body 6-DOF reaction wrenches
"""

import argparse
import sys

from isaaclab.app import AppLauncher

import cli_args  # isort: skip

parser = argparse.ArgumentParser(description="Log joint torques and forces for hardware analysis.")
parser.add_argument("--num_envs", type=int, default=1, help="Number of environments (default: 1 for clean traces).")
parser.add_argument("--task", type=str, default=None, help="Name of the task.")
parser.add_argument("--steps", type=int, default=1000, help="Number of simulation steps to record.")
parser.add_argument("--seed", type=int, default=None, help="Seed used for the environment")
parser.add_argument(
    "--agent", type=str, default="rsl_rl_cfg_entry_point", help="Name of the RL agent configuration entry point."
)
cli_args.add_rsl_rl_args(parser)
AppLauncher.add_app_launcher_args(parser)
args_cli, hydra_args = parser.parse_known_args()

sys.argv = [sys.argv[0]] + hydra_args

app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import csv
import os

import gymnasium as gym
import torch
from rsl_rl.runners import OnPolicyRunner

from isaaclab.envs import ManagerBasedRLEnvCfg, DirectRLEnvCfg, DirectMARLEnvCfg
from isaaclab.utils.assets import retrieve_file_path

from isaaclab_rl.rsl_rl import RslRlBaseRunnerCfg, RslRlVecEnvWrapper

import isaaclab_tasks  # noqa: F401
from isaaclab_tasks.utils import get_checkpoint_path
from isaaclab_tasks.utils.hydra import hydra_task_config

import atom_isaaclab  # noqa: F401

# Joint rotation axes in parent body frame (from URDF joint definitions).
# Used to decompose the 6-DOF wrench into axial, radial, and moment components.
JOINT_AXIS_MAP = {
    "pitch": 1,  # Y axis
    "roll": 0,   # X axis
    "yaw": 2,    # Z axis
}


def get_joint_axis(joint_name: str) -> int:
    """Infer the rotation axis index from the joint name."""
    name_lower = joint_name.lower()
    for keyword, axis in JOINT_AXIS_MAP.items():
        if keyword in name_lower:
            return axis
    return 2  # default to Z if unknown


@hydra_task_config(args_cli.task, args_cli.agent)
def main(env_cfg: ManagerBasedRLEnvCfg | DirectRLEnvCfg | DirectMARLEnvCfg, agent_cfg: RslRlBaseRunnerCfg):
    """Record joint torques and reaction forces from a trained policy."""
    task_name = args_cli.task.split(":")[-1]
    train_task_name = task_name.replace("-Play", "")

    agent_cfg = cli_args.update_rsl_rl_cfg(agent_cfg, args_cli)
    env_cfg.scene.num_envs = args_cli.num_envs
    env_cfg.seed = agent_cfg.seed
    env_cfg.sim.device = args_cli.device if args_cli.device is not None else env_cfg.sim.device

    # find checkpoint
    log_root_path = os.path.join("logs", "rsl_rl", agent_cfg.experiment_name)
    log_root_path = os.path.abspath(log_root_path)
    if args_cli.checkpoint:
        resume_path = retrieve_file_path(args_cli.checkpoint)
    else:
        resume_path = get_checkpoint_path(log_root_path, agent_cfg.load_run, agent_cfg.load_checkpoint)
    log_dir = os.path.dirname(resume_path)
    env_cfg.log_dir = log_dir

    # create environment
    env = gym.make(args_cli.task, cfg=env_cfg)
    env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)

    # load policy
    print(f"[INFO] Loading checkpoint: {resume_path}")
    runner = OnPolicyRunner(env, agent_cfg.to_dict(), log_dir=None, device=agent_cfg.device)
    runner.load(resume_path)
    policy = runner.get_inference_policy(device=env.unwrapped.device)

    # get robot info
    robot = env.unwrapped.scene["robot"]
    joint_names = robot.joint_names
    body_names = robot.body_names
    num_joints = len(joint_names)
    num_bodies = len(body_names)
    effort_limits = robot.data.joint_effort_limits[0].cpu()

    print(f"[INFO] Recording {args_cli.steps} steps across {args_cli.num_envs} env(s)...")
    print(f"[INFO] Joints ({num_joints}): {joint_names}")
    print(f"[INFO] Bodies ({num_bodies}): {body_names}")

    # storage
    all_torques = torch.zeros(args_cli.steps, args_cli.num_envs, num_joints)
    all_commanded = torch.zeros(args_cli.steps, args_cli.num_envs, num_joints)
    all_wrenches = torch.zeros(args_cli.steps, args_cli.num_envs, num_bodies, 6)
    all_joint_pos = torch.zeros(args_cli.steps, args_cli.num_envs, num_joints)
    all_joint_vel = torch.zeros(args_cli.steps, args_cli.num_envs, num_joints)

    obs = env.get_observations()
    for step in range(args_cli.steps):
        with torch.inference_mode():
            actions = policy(obs)
            obs, _, _, _ = env.step(actions)
            all_torques[step] = robot.data.applied_torque.cpu()
            all_commanded[step] = robot.data.computed_torque.cpu()
            all_wrenches[step] = robot.data.body_incoming_joint_wrench_b.cpu()
            all_joint_pos[step] = robot.data.joint_pos.cpu()
            all_joint_vel[step] = robot.data.joint_vel.cpu()

    # =====================================================================
    # TORQUE ANALYSIS
    # =====================================================================
    flat_torques = all_torques.reshape(-1, num_joints)
    flat_commanded = all_commanded.reshape(-1, num_joints)

    t_peak_abs = flat_torques.abs().max(dim=0).values
    t_rms = (flat_torques ** 2).mean(dim=0).sqrt()
    t_mean_abs = flat_torques.abs().mean(dim=0)
    t_min = flat_torques.min(dim=0).values
    t_max = flat_torques.max(dim=0).values

    cmd_peak_abs = flat_commanded.abs().max(dim=0).values
    cmd_rms = (flat_commanded ** 2).mean(dim=0).sqrt()
    saturated_steps = (flat_commanded.abs() > effort_limits.unsqueeze(0) * 0.99).float().mean(dim=0)

    # =====================================================================
    # JOINT FORCE ANALYSIS
    # =====================================================================
    flat_wrenches = all_wrenches.reshape(-1, num_bodies, 6)
    forces = flat_wrenches[:, :, :3]
    torques_wrench = flat_wrenches[:, :, 3:]

    force_mag = forces.norm(dim=2)
    torque_mag = torques_wrench.norm(dim=2)

    # =====================================================================
    # WRITE STATS
    # =====================================================================
    stats_path = os.path.join(log_dir, "hardware_stats.txt")
    lines = []

    lines.append("=" * 80)
    lines.append("HARDWARE SUITABILITY REPORT")
    lines.append(f"Steps: {args_cli.steps}, Envs: {args_cli.num_envs}, "
                 f"Samples: {flat_torques.shape[0]}, Duration: {args_cli.steps * 0.02:.1f}s")
    lines.append("=" * 80)

    # --- Motor torques ---
    lines.append("")
    lines.append("SECTION 1: MOTOR TORQUES")
    lines.append("")
    lines.append("=== Applied Torques (clipped to effort limit) ===")
    header = f"{'Joint':<30s} {'Peak':>8s} {'RMS':>8s} {'MeanAbs':>8s} {'Min':>8s} {'Max':>8s} {'Limit':>8s} {'%Peak':>7s} {'%RMS':>7s}"
    sep = "-" * len(header)
    lines.append(header)
    lines.append(sep)
    for j in range(num_joints):
        lim = effort_limits[j].item()
        pct_peak = 100 * t_peak_abs[j].item() / lim if lim > 0 else 0
        pct_rms = 100 * t_rms[j].item() / lim if lim > 0 else 0
        lines.append(
            f"{joint_names[j]:<30s} "
            f"{t_peak_abs[j].item():>8.2f} "
            f"{t_rms[j].item():>8.2f} "
            f"{t_mean_abs[j].item():>8.2f} "
            f"{t_min[j].item():>8.2f} "
            f"{t_max[j].item():>8.2f} "
            f"{lim:>8.1f} "
            f"{pct_peak:>6.1f}% "
            f"{pct_rms:>6.1f}%"
        )

    lines.append("")
    lines.append("=== Commanded Torques (raw PD output, before clipping) ===")
    header2 = f"{'Joint':<30s} {'CmdPeak':>8s} {'CmdRMS':>8s} {'Limit':>8s} {'%Saturated':>11s}"
    lines.append(header2)
    lines.append(sep)
    for j in range(num_joints):
        lim = effort_limits[j].item()
        lines.append(
            f"{joint_names[j]:<30s} "
            f"{cmd_peak_abs[j].item():>8.2f} "
            f"{cmd_rms[j].item():>8.2f} "
            f"{lim:>8.1f} "
            f"{100 * saturated_steps[j].item():>10.1f}%"
        )

    rated_continuous = 20.0
    lines.append("")
    over_rated = [joint_names[j] for j in range(num_joints) if t_rms[j].item() > rated_continuous]
    if over_rated:
        lines.append(f"WARNING: RMS torque exceeds {rated_continuous} Nm rated continuous: {', '.join(over_rated)}")
    else:
        lines.append(f"OK: All joints within {rated_continuous} Nm rated continuous (RMS).")

    over_peak = [joint_names[j] for j in range(num_joints) if t_peak_abs[j].item() > effort_limits[j].item()]
    if over_peak:
        lines.append(f"WARNING: Peak torque exceeds effort limit: {', '.join(over_peak)}")

    saturated_joints = [joint_names[j] for j in range(num_joints) if saturated_steps[j].item() > 0.05]
    if saturated_joints:
        lines.append(f"WARNING: >5% saturation: {', '.join(saturated_joints)}")
    else:
        lines.append("OK: No joints exceeding 5% saturation.")

    # --- Joint angles ---
    lines.append("")
    lines.append("=" * 80)
    lines.append("SECTION 2: JOINT ANGLES (rad)")
    lines.append("=" * 80)
    lines.append("")

    flat_pos = all_joint_pos.reshape(-1, num_joints)
    flat_vel = all_joint_vel.reshape(-1, num_joints)
    joint_limits_lo = robot.data.joint_pos_limits[0, :, 0].cpu()
    joint_limits_hi = robot.data.joint_pos_limits[0, :, 1].cpu()

    header_ang = f"{'Joint':<30s} {'Min':>8s} {'Max':>8s} {'Mean':>8s} {'Std':>8s} {'LimLo':>8s} {'LimHi':>8s} {'VelRMS':>8s}"
    sep_ang = "-" * len(header_ang)
    lines.append(header_ang)
    lines.append(sep_ang)
    for j in range(num_joints):
        pos_min = flat_pos[:, j].min().item()
        pos_max = flat_pos[:, j].max().item()
        pos_mean = flat_pos[:, j].mean().item()
        pos_std = flat_pos[:, j].std().item()
        vel_rms = (flat_vel[:, j] ** 2).mean().sqrt().item()
        lo = joint_limits_lo[j].item()
        hi = joint_limits_hi[j].item()
        lines.append(
            f"{joint_names[j]:<30s} "
            f"{pos_min:>8.3f} {pos_max:>8.3f} {pos_mean:>8.3f} {pos_std:>8.3f} "
            f"{lo:>8.3f} {hi:>8.3f} {vel_rms:>8.2f}"
        )

    # --- Joint reaction forces ---
    lines.append("")
    lines.append("=" * 80)
    lines.append("SECTION 3: JOINT REACTION FORCES (for bearing analysis)")
    lines.append("=" * 80)
    lines.append("")

    lines.append("=== Per-Body Total Force and Torque Magnitudes ===")
    lines.append("Forces in Newtons (N), Torques in Newton-meters (Nm)")
    lines.append("")
    header3 = f"{'Body':<35s} {'F_peak':>8s} {'F_rms':>8s} {'F_mean':>8s} {'T_peak':>8s} {'T_rms':>8s} {'T_mean':>8s}"
    sep3 = "-" * len(header3)
    lines.append(header3)
    lines.append(sep3)
    for b in range(num_bodies):
        f_peak = force_mag[:, b].max().item()
        f_rms = (force_mag[:, b] ** 2).mean().sqrt().item()
        f_mean = force_mag[:, b].mean().item()
        t_peak = torque_mag[:, b].max().item()
        t_rms = (torque_mag[:, b] ** 2).mean().sqrt().item()
        t_mean = torque_mag[:, b].mean().item()
        lines.append(
            f"{body_names[b]:<35s} "
            f"{f_peak:>8.1f} {f_rms:>8.1f} {f_mean:>8.1f} "
            f"{t_peak:>8.1f} {t_rms:>8.1f} {t_mean:>8.1f}"
        )

    lines.append("")
    lines.append("=== Decomposed Joint Loads (Axial / Radial / Moment) ===")
    lines.append("Axial:  force along joint rotation axis (thrust load)")
    lines.append("Radial: force perpendicular to rotation axis (main bearing load)")
    lines.append("Moment: torque perpendicular to rotation axis (bending — crossed rollers handle this)")
    lines.append("")

    header4 = (
        f"{'Body (Joint)':<35s} {'Axis':>4s} "
        f"{'Ax_pk':>7s} {'Ax_rms':>7s} "
        f"{'Rd_pk':>7s} {'Rd_rms':>7s} "
        f"{'Mo_pk':>7s} {'Mo_rms':>7s}"
    )
    sep4 = "-" * len(header4)
    lines.append(header4)
    lines.append(sep4)

    for b in range(1, num_bodies):  # skip root
        joint_idx = b - 1
        if joint_idx < len(joint_names):
            jname = joint_names[joint_idx]
            axis_idx = get_joint_axis(jname)
        else:
            jname = "unknown"
            axis_idx = 2

        axis_label = ["X", "Y", "Z"][axis_idx]
        radial_indices = [i for i in range(3) if i != axis_idx]

        f_axial = forces[:, b, axis_idx]
        f_radial = forces[:, b, radial_indices].norm(dim=1)
        t_moment = torques_wrench[:, b, radial_indices].norm(dim=1)

        ax_peak = f_axial.abs().max().item()
        ax_rms = (f_axial ** 2).mean().sqrt().item()
        rd_peak = f_radial.max().item()
        rd_rms = (f_radial ** 2).mean().sqrt().item()
        mo_peak = t_moment.max().item()
        mo_rms = (t_moment ** 2).mean().sqrt().item()

        body_label = f"{body_names[b]} ({jname})"
        lines.append(
            f"{body_label:<35s} {axis_label:>4s} "
            f"{ax_peak:>7.1f} {ax_rms:>7.1f} "
            f"{rd_peak:>7.1f} {rd_rms:>7.1f} "
            f"{mo_peak:>7.1f} {mo_rms:>7.1f}"
        )

    lines.append("")
    lines.append(sep4)
    lines.append("High radial loads and bending moments indicate joints that may need external bearings.")
    lines.append("Compare against RS03 internal bearing ratings and candidate bearings (SKF 61805, IKO CRBT505AC1).")

    stats_text = "\n".join(lines)
    print(f"\n{stats_text}")

    with open(stats_path, "w") as f:
        f.write(stats_text + "\n")
    print(f"\n[INFO] Stats written to: {stats_path}")

    # =====================================================================
    # WRITE CSVs
    # =====================================================================

    # Torque CSV
    csv_torque_path = os.path.join(log_dir, "torque_log.csv")
    applied_cols = [f"{name}_applied" for name in joint_names]
    commanded_cols = [f"{name}_commanded" for name in joint_names]
    pos_cols = [f"{name}_pos" for name in joint_names]
    vel_cols = [f"{name}_vel" for name in joint_names]
    with open(csv_torque_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["step", "env"] + applied_cols + commanded_cols + pos_cols + vel_cols)
        for step in range(args_cli.steps):
            for e in range(args_cli.num_envs):
                applied = [f"{all_torques[step, e, j].item():.4f}" for j in range(num_joints)]
                commanded = [f"{all_commanded[step, e, j].item():.4f}" for j in range(num_joints)]
                pos = [f"{all_joint_pos[step, e, j].item():.4f}" for j in range(num_joints)]
                vel = [f"{all_joint_vel[step, e, j].item():.4f}" for j in range(num_joints)]
                writer.writerow([step, e] + applied + commanded + pos + vel)
    print(f"[INFO] Torque CSV written to: {csv_torque_path}")

    # Force CSV
    csv_force_path = os.path.join(log_dir, "joint_force_log.csv")
    wrench_labels = ["fx", "fy", "fz", "tx", "ty", "tz"]
    with open(csv_force_path, "w", newline="") as f:
        writer = csv.writer(f)
        cols = ["step", "env"]
        for b in range(num_bodies):
            for wl in wrench_labels:
                cols.append(f"{body_names[b]}_{wl}")
        writer.writerow(cols)
        for step in range(args_cli.steps):
            for e in range(args_cli.num_envs):
                row = [step, e]
                for b in range(num_bodies):
                    for w in range(6):
                        row.append(f"{all_wrenches[step, e, b, w].item():.4f}")
                writer.writerow(row)
    print(f"[INFO] Force CSV written to: {csv_force_path}")

    print(f"\n[INFO] Done. {args_cli.steps} steps × {args_cli.num_envs} envs recorded.")

    env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
