"""Plot hardware log data from log_hardware.py output.

Produces three subplots sharing a time axis:
  1. Applied torques per joint (Nm)
  2. Joint positions per joint (rad)
  3. Joint reaction force magnitudes per body (N)

Usage:
    python3 scripts/plot_hardware.py <run_dir>

Example:
    python3 scripts/plot_hardware.py logs/rsl_rl/atom_flat/2026-03-13_11-53-50
"""

import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Plot hardware log data.")
    parser.add_argument("run_dir", help="Path to the run directory containing CSVs.")
    parser.add_argument("--env", type=int, default=0, help="Environment index to plot (default: 0).")
    parser.add_argument("--dt", type=float, default=0.02, help="Sim timestep in seconds (default: 0.02).")
    parser.add_argument("--window", type=float, default=None, help="Time window in seconds (e.g. 2.5). Centers on mid-recording.")
    parser.add_argument("--start", type=float, default=None, help="Start time in seconds for the window.")
    args = parser.parse_args()

    torque_csv = os.path.join(args.run_dir, "torque_log.csv")
    force_csv = os.path.join(args.run_dir, "joint_force_log.csv")

    if not os.path.exists(torque_csv):
        print(f"[ERROR] {torque_csv} not found.")
        sys.exit(1)
    if not os.path.exists(force_csv):
        print(f"[ERROR] {force_csv} not found.")
        sys.exit(1)

    # --- Load data ---
    df_torque = pd.read_csv(torque_csv)
    df_force = pd.read_csv(force_csv)

    # Filter to requested env
    df_torque = df_torque[df_torque["env"] == args.env].copy()
    df_force = df_force[df_force["env"] == args.env].copy()

    time = df_torque["step"].values * args.dt

    # --- Apply time window ---
    if args.window is not None:
        if args.start is not None:
            t_start = args.start
        else:
            t_mid = time[-1] / 2
            t_start = max(0, t_mid - args.window / 2)
        t_end = t_start + args.window
        mask_t = (time >= t_start) & (time <= t_end)
        df_torque = df_torque[mask_t].copy()
        time = time[mask_t]
        mask_f = (df_force["step"].values * args.dt >= t_start) & (df_force["step"].values * args.dt <= t_end)
        df_force = df_force[mask_f].copy()

    # --- Identify columns ---
    applied_cols = [c for c in df_torque.columns if c.endswith("_applied")]
    pos_cols = [c for c in df_torque.columns if c.endswith("_pos")]
    joint_names = [c.replace("_applied", "") for c in applied_cols]

    # Force magnitude per body (skip step, env columns)
    force_data_cols = [c for c in df_force.columns if c not in ("step", "env")]
    # Group by body: extract unique body names
    body_names = []
    seen = set()
    for c in force_data_cols:
        body = c.rsplit("_", 1)[0]  # strip _fx, _fy, etc.
        if body not in seen:
            seen.add(body)
            body_names.append(body)

    # Compute force magnitude per body
    force_mags = {}
    for body in body_names:
        fx = df_force.get(f"{body}_fx")
        fy = df_force.get(f"{body}_fy")
        fz = df_force.get(f"{body}_fz")
        if fx is not None and fy is not None and fz is not None:
            force_mags[body] = (fx.values**2 + fy.values**2 + fz.values**2) ** 0.5

    # --- Plot ---
    fig, axes = plt.subplots(3, 1, figsize=(16, 14), sharex=True)

    # Subplot 1: Applied torques
    ax1 = axes[0]
    for jname, col in zip(joint_names, applied_cols):
        ax1.plot(time, df_torque[col].values, label=jname, linewidth=0.7)
    ax1.set_ylabel("Applied Torque (Nm)")
    ax1.set_title("Joint Applied Torques")
    ax1.legend(loc="upper right", fontsize=7, ncol=4)
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=60, color="r", linestyle="--", alpha=0.5, linewidth=0.8)
    ax1.axhline(y=-60, color="r", linestyle="--", alpha=0.5, linewidth=0.8)

    # Subplot 2: Joint positions
    ax2 = axes[1]
    for jname, col in zip(joint_names, pos_cols):
        ax2.plot(time, df_torque[col].values, label=jname, linewidth=0.7)
    ax2.set_ylabel("Joint Position (rad)")
    ax2.set_title("Joint Angles")
    ax2.legend(loc="upper right", fontsize=7, ncol=4)
    ax2.grid(True, alpha=0.3)

    # Subplot 3: Force magnitudes
    ax3 = axes[2]
    time_force = df_force["step"].values * args.dt
    for body, mag in force_mags.items():
        ax3.plot(time_force, mag, label=body, linewidth=0.7)
    ax3.set_ylabel("Force Magnitude (N)")
    ax3.set_xlabel("Time (s)")
    ax3.set_title("Joint Reaction Force Magnitudes")
    ax3.legend(loc="upper right", fontsize=7, ncol=3)
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    suffix = f"_{args.window}s" if args.window else ""
    out_path = os.path.join(args.run_dir, f"hardware_plot{suffix}.png")
    plt.savefig(out_path, dpi=150)
    print(f"[INFO] Saved: {out_path}")
    plt.close()


if __name__ == "__main__":
    main()
