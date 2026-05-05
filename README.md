# Atom Humanoid

R&D repository for the **Atom Humanoid** — a 16-DoF, 5'6" (168 cm) humanoid robot powered by RS03 actuators and trained in NVIDIA Isaac Lab.

## What's in here

| Directory | Contents |
|-----------|----------|
| `ONSHAPE_URDF/` | CAD-to-URDF pipeline (`onshape-robotics-toolkit`), post-processing scripts, and versioned URDF outputs |
| `atom_isaaclab/` | Isaac Lab RL training package — env configs, reward functions, PPO hyperparameters, training/play scripts |
| `Actuators/` | RS02/RS03 specs and user manuals |
| `Robot_Arm/` | RS02-actuated arm bringup — CAN motor control scripts |
| `Docs/` | Kinematics specs, hardware notes, joint-limits comparison, early planning |
| `Training/` | Training log (`training_log.md`) and retraining plan |
| `Scripts/` | Utility scripts (`md_to_pdf.py`) |

## Robot specs

- **DoF:** 16 (8 legs, 8 arms)
- **Joints:** `dof_{joint}_{side}` — e.g. `dof_hip_pitch_left`
- **Legs:** hip pitch, hip roll, knee pitch, ankle pitch × L/R
- **Arms:** shoulder pitch, shoulder roll, upper arm yaw, elbow pitch × L/R
- **Actuators:** RobStride RS03, 60 Nm effort limit, 20 Nm rated continuous
- **URDF:** `ONSHAPE_URDF/Atom_Humanoid_V0.7/Atom_Humanoid_V0.7_clean_limits.urdf`

## Quick start

### 1. OnShape → URDF conversion

Requires `ONSHAPE_URDF/.env` with OnShape API credentials.

```bash
cd ONSHAPE_URDF && MPLBACKEND=Agg python3 convert.py
```

Then run the four post-processing steps (replace version as needed):

```bash
python3 ONSHAPE_URDF/clean_urdf.py          ONSHAPE_URDF/Atom_Humanoid_V0.7/Atom_Humanoid_V0.7.urdf
python3 ONSHAPE_URDF/set_joint_limits.py    ONSHAPE_URDF/Atom_Humanoid_V0.7/Atom_Humanoid_V0.7_clean.urdf
python3 ONSHAPE_URDF/center_hip_origin.py   ONSHAPE_URDF/Atom_Humanoid_V0.7/Atom_Humanoid_V0.7_clean_limits.urdf
python3 ONSHAPE_URDF/fix_foot_collision.py  ONSHAPE_URDF/Atom_Humanoid_V0.7/Atom_Humanoid_V0.7_clean_limits.urdf
```

> **Note:** STL meshes are not tracked in git (too large). Run `convert.py` to download them from OnShape, or copy the `meshes/` directory from an existing checkout.

### 2. Install Isaac Lab RL package

```bash
conda activate env_isaaclab
cd atom_isaaclab && pip install -e .
```

Requires [NVIDIA Isaac Lab](https://isaac-sim.github.io/IsaacLab/) installed at `~/IsaacLab/`.

### 3. Train

```bash
# Flat terrain (6144 envs, 10k iterations)
cd atom_isaaclab && conda run -n env_isaaclab bash -c \
  "MPLBACKEND=Agg /home/atoms/IsaacLab/isaaclab.sh -p scripts/train.py \
   --task Isaac-Velocity-Flat-Atom-v0 --num_envs 6144 --headless --max_iterations 10000"

# Resume from checkpoint
conda run -n env_isaaclab bash -c \
  "MPLBACKEND=Agg /home/atoms/IsaacLab/isaaclab.sh -p scripts/train.py \
   --task Isaac-Velocity-Flat-Atom-v0 --num_envs 6144 --headless --resume --load_run <run_id>"
```

> **Critical:** `--resume` is required when loading a checkpoint. `--load_run` alone is silently ignored.

### 4. Visualize

```bash
cd atom_isaaclab && conda activate env_isaaclab && \
  MPLBACKEND=Agg /home/atoms/IsaacLab/isaaclab.sh -p scripts/play.py \
  --task Isaac-Velocity-Flat-Atom-Play-v0 --num_envs 50 --load_run <run_id>
```

## Registered environments

| Task | Description |
|------|-------------|
| `Isaac-Velocity-Flat-Atom-v0` | Walking on flat terrain |
| `Isaac-Velocity-Rough-Atom-v0` | Walking on rough/stair terrain |
| `Isaac-Standing-Flat-Atom-v0` | Standing specialist policy |
| `*-Play-v0` variants | Visualization configs for each |

## Key source files

```
atom_isaaclab/source/atom_isaaclab/
├── robots/atom_humanoid.py              # ArticulationCfg — URDF path, actuator groups
└── tasks/locomotion/velocity/
    ├── atom_env_cfg.py                  # Flat, rough, and standing env configs
    ├── agents/rsl_rl_ppo_cfg.py         # PPO hyperparameters
    └── mdp/
        ├── rewards.py                   # Custom reward functions
        └── observations.py             # height_scan_forward_only (for D435i hardware)
```

## Training notes

See [`Training/training_log.md`](Training/training_log.md) for a full chronological record of all runs, config changes, and lessons learned (~58 runs across flat, rough, and standing terrain).

Key findings:
- Foot contact geometry matters: flat box collision (18×7×3 cm) vs STL curves — boxes give stable 2D patch contact
- `action_rate_l2=-0.005` crashes Atom at ~1700 iters (no hip yaw DoF makes action transitions jerkier than H1)
- 50° knee spawn is the sweet spot: 70° causes sumo-walking exploit, 29° causes straight-leg convergence
- Forward-only height scanner masking from day one matches the D435i hardware constraint

## Hardware

**GPU:** RTX 5080 (16 GB) — ~4.6 GB VRAM at 6144 envs. Bottleneck is CPU-side PhysX pipeline.

Close GPU-intensive apps (browser, IDE) during training. Kill stale Isaac processes before a new run:
```bash
ps aux | grep "env_isaaclab/bin/python"
```
