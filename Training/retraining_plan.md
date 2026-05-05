# Atom Humanoid — Retraining Plan

This document is the step-by-step gameplan for retraining after significant design changes
(new motor mounts, cable management, structural changes, mass redistribution, etc.).

---

## Step 1: Export New URDF

```bash
cd ONSHAPE_URDF && MPLBACKEND=Agg python3 convert.py
```

**After export, immediately verify:**

- [ ] Kinematic tree is correct (`Torso → Hip → Femur → Shin → Foot` each side)
- [ ] 16 revolute joints present with correct names (`dof_hip_pitch_left`, etc.)
- [ ] Hip joints separated along **Y axis** (left at y≈-0.15, right at y≈0) — confirms forward = +X
- [ ] `frame_foot_right` parented to `Foot_Right_1`, `frame_foot_left` to `Foot_Left_1` (OnShape sometimes swaps these)
- [ ] Same for hand frames

```bash
grep "dof_hip_pitch" ONSHAPE_URDF/Atom_Humanoid_VX.X/Atom_Humanoid_VX.X.urdf
# hip_left xyz should have x=0, hip_right xyz should have x=0 — both separated in Y
```

---

## Step 2: URDF Post-Processing

These are manual fixes applied after every export.

### 2a. Strip frame_ reference links (always)

Run the cleanup script to remove OnShape reference frames (IMU, foot, hand) that are
not needed for simulation. Always use the `_clean.urdf` for training.

```bash
python3 ONSHAPE_URDF/clean_urdf.py ONSHAPE_URDF/Atom_Humanoid_VX.X/Atom_Humanoid_VX.X.urdf
# Output: Atom_Humanoid_VX.X_clean.urdf (shares same meshes/ folder)
```

### 2b. Add virtual root joint (coordinate frame fix)

If the robot's chest still faces world **-X** (verified in GUI — velocity arrow points backward),
add a 180° fixed joint at the base. Insert after `<robot name="...">`:

```xml
<link name="base_link"/>
<joint name="base_to_torso" type="fixed">
  <origin xyz="0 0 0" rpy="0 0 3.14159265"/>
  <parent link="base_link"/>
  <child link="Torso_With_Motors_1"/>
</joint>
```

**Note:** When this is present, Isaac Sim merges `base_link` + `Torso_With_Motors_1` into
a single body named `base_link`. All env config references must use `base_link`, not
`Torso_With_Motors_1`.

### 2c. Add reflected rotor inertia *(do this once motor specs are available)*

> ⚠️ **PENDING — waiting on motor spec sheets (gear ratio, rotor inertia)**

For each joint, add reflected inertia to the child link's `<inertial>` block:

```
reflected_inertia = I_rotor × gear_ratio²
```

Add along the motor spin axis (typically ixx or izz depending on joint orientation).
This is critical for sim-to-real transfer — without it the sim robot responds far too fast.

### 2d. Add joint friction & damping *(do this once motor characterization is done)*

> ⚠️ **PENDING — waiting on motor characterization data (Coulomb friction, viscous damping)**

Add `<dynamics>` to each `<joint>` block:

```xml
<dynamics damping="0.5" friction="0.3"/>
```

Values come from motor characterization:
- `damping` = measured viscous coefficient (Nm·s/rad)
- `friction` = measured Coulomb friction (Nm)

---

## Step 3: Update Isaac Lab Config

### 3a. Point to new URDF

`atom_isaaclab/source/atom_isaaclab/robots/atom_humanoid.py`:
```python
ATOM_URDF_PATH = "/home/atoms/Documents/Robots/ONSHAPE_URDF/Atom_Humanoid_VX.X/Atom_Humanoid_VX.X.urdf"
```

### 3b. Recalibrate spawn height

The spawn height must place feet just above the ground at the init joint pose.
FK rule of thumb: start at 0.85m (near-straight legs) and adjust up for deeper knee bend.

Run a quick GUI test (16–64 envs) to confirm feet land cleanly, not hovering or clipping.

### 3c. Check joint names haven't changed

If any joint was renamed in OnShape, update regex patterns in:
- `atom_humanoid.py` — actuator `joint_names_expr` and `init_state.joint_pos`
- `atom_env_cfg.py` — any `SceneEntityCfg` joint/body name references

### 3d. Re-verify body names

If structural bodies were added/removed, check:
- Contact sensor body: currently `base_link`
- Height scanner prim path: currently `base_link`
- External force target: currently `base_link`

---

## Step 4: GUI Sanity Check (before any full run)

Launch with 64 envs, no headless:
```bash
cd atom_isaaclab && conda activate env_isaaclab && MPLBACKEND=Agg \
  /home/atoms/IsaacLab/isaaclab.sh -p scripts/train.py \
  --task Isaac-Velocity-Flat-Atom-v0 --num_envs 64
```

**Check these before proceeding:**

- [ ] Robots spawn upright, feet touching or just above ground
- [ ] Green velocity arrow points **forward** (out of robot's chest)
- [ ] No immediate falls on spawn
- [ ] Joints move plausibly on first policy steps (not frozen, not exploding)
- [ ] No Isaac Sim errors in terminal (body name mismatches, missing joints, etc.)

---

## Step 5: Review Reward Table

**Always review and confirm before launching a full training run:**

| Term | Weight | Purpose |
|---|---|---|
| `track_lin_vel_xy_exp` | +1.0 | Forward/lateral velocity tracking |
| `track_ang_vel_z_exp` | +1.0 | Yaw rate tracking |
| `feet_air_time` | +2.0 | Alternating bipedal stepping (threshold 0.4s) |
| `feet_contact_at_rest` | **disabled** (rough) / -0.5 (flat) | Standing uses separate policy; hurts rough terrain balance |
| `flat_orientation_l2` | -1.0 | Match H1 — terminations handle falls; tighten post-convergence |
| `joint_deviation_hip_roll` | -0.2 | Match H1 (H1 penalizes yaw+roll at -0.2; Atom has no hip yaw) |
| `joint_deviation_arms` | -0.2 | Keep arms near zero (early training) |
| `termination_penalty` | -200 | Penalize falls |
| `feet_slide` | -0.25 | Penalize foot sliding |
| `dof_pos_limits` | -1.0 | Ankle+knee joint limit violations |
| `action_rate_l2` | -0.005 | Match H1 — tighten to -0.01 post-convergence |
| `dof_acc_l2` | -1.25e-7 | Match H1 — tighten to -2.5e-7 post-convergence |
| `dof_torques_l2` | 0.0 (disabled) | Match H1 — re-enable at -1e-5 post-convergence |

Adjust weights if mass/inertia has changed significantly — a heavier robot will need
proportionally stronger orientation and velocity tracking incentives.

---

## Step 5b: GPU Monitoring

Run this in a separate terminal during training to verify the GPU is being pushed to its limits:

```bash
watch -n 1 nvidia-smi
```

**Key metrics to watch:**
- **GPU Util %** — target ≥ 90% during training iterations. If consistently < 70%, the physics simulation or data pipeline is the bottleneck, not compute — try increasing `--num_envs`
- **Memory-Usage** — target 12–15 GB of 16 GB used. If < 10 GB at 4096 envs, bump to 5120
- **Power Draw** — RTX 5080 TDP is 360 W; near-TDP draw means the GPU is fully loaded

For a richer interactive view, install nvitop once:
```bash
pip install nvitop
```
Then during training:
```bash
nvitop
```
Shows per-process VRAM, utilization, power, and temperature in a live dashboard.

**VRAM reality (RTX 5080, 16 GB):**
- Isaac uses only ~4.6 GB VRAM at 6144 envs — VRAM is not the binding constraint
- The bottleneck is the CPU-side PhysX data pipeline; GPU util ~65%, power ~34% TDP
- Close desktop apps (Firefox, VSCode, Obsidian) during training to reduce GPU scheduler contention
- Try 8192 envs — VRAM headroom is substantial, and more envs means more diverse experience per wall-clock second even if per-iteration throughput plateaus

**`--num_envs` is a CLI override** — no code change needed to experiment:
```bash
# Try 5120 for a short run to check VRAM before committing
conda run -n env_isaaclab bash -c "MPLBACKEND=Agg /home/atoms/IsaacLab/isaaclab.sh -p scripts/train.py \
  --task Isaac-Velocity-Flat-Atom-v0 --num_envs 5120 --headless"
```

---

## Step 6: Training Phases

> **CRITICAL:** When loading from a previous checkpoint, `--resume` is required alongside
> `--load_run`. Without `--resume`, the checkpoint is silently ignored and training starts
> from scratch. The iteration counter continues from the loaded checkpoint — this is expected.
> See `train.py:177`: checkpoint path is only computed when `agent_cfg.resume` is true.

### Phase 1 — Learn to Walk (Flat Terrain, Bent-Knee Init)

```bash
cd atom_isaaclab && conda run -n env_isaaclab bash -c \
  "MPLBACKEND=Agg /home/atoms/IsaacLab/isaaclab.sh -p scripts/train.py \
  --task Isaac-Velocity-Flat-Atom-v0 --num_envs 4096 --headless"
```

- **Init pose**: knees bent ~0.3 rad, ankles -0.15 rad
- **Joint reset range**: (0.5, 1.5) — variety within bent regime
- **Commands**: forward only, lin_vel_x=(0.5, 1.0), no turning
- **Target**: `time_out > 80%`, `track_lin_vel_xy > 0.7`, `root_height termination < 15%`
- **Duration**: ~1000 iterations

**Watch for degenerate gaits:**
- Hip-roll lateral shuffle → increase `joint_deviation_hip_roll` weight
- Straight-leg hopping → increase `joint_deviation_knees` weight
- Torso flopping → increase `flat_orientation_l2` weight

### Phase 2 — Straight-Leg Adaptation (Fine-Tune for Sim-to-Real)

Load Phase 1 checkpoint, revert to straight-leg init pose, run 300–500 iterations:

```bash
# First: update atom_humanoid.py init pose to straight knees (0.05 rad)
# Then:
conda run -n env_isaaclab bash -c \
  "MPLBACKEND=Agg /home/atoms/IsaacLab/isaaclab.sh -p scripts/train.py \
  --task Isaac-Velocity-Flat-Atom-v0 --num_envs 4096 --headless \
  --resume --load_run <phase1_run_id>"
```

- **Purpose**: robot learns to recover from the harness-lowering starting condition
- **Joint reset range**: (0.0, 1.0) — covers straight through moderately bent
- **Duration**: 300–500 iterations (fine-tune, not full retrain)

### Phase 2.5 — Standing + Slow Walk (Fine-Tune, 3 sub-phases)

**Purpose**: extend command range down to zero without catastrophic forgetting.

> ⚠️ **Lesson learned**: jumping directly from (0.5,1.0) to (0.0,1.0) causes catastrophic forgetting.
> Never change the lin_vel_x lower bound by more than ~0.3 m/s per sub-phase.

**Sub-phase A** — `lin_vel_x=(0.3, 1.0)`, load from Phase 2, ~500 iter
**Sub-phase B** — `lin_vel_x=(0.0, 1.0)`, load from 2.5a, ~1000 iter
**Sub-phase C** — same range, add `feet_contact_at_rest` reward (weight=-2.0, threshold=0.02 m/s), load from 2.5b, ~1000 iter

```python
# atom_env_cfg.py changes per sub-phase:
self.commands.base_velocity.ranges.lin_vel_x = (0.0, 1.0)
# Phase 2.5c only — feet_contact_at_rest already wired in atom_env_cfg.py
```

- **Standing behavior**: policy will take slight micro-steps at zero command — this is normal for compliant humanoids. The `feet_contact_at_rest` penalty in 2.5c discourages excessive foot lifting.
- The slight forward shuffle at 0 m/s that remains after 2.5c is addressed by Phase 3 (backwards walking).
- If 2.5c takes >~250 iterations to recover from collapse, run a 2.5d consolidation pass (same config, load from 2.5c).

### Phase 3 — Backwards Walking (Fine-Tune)

**Purpose**: symmetric command range eliminates forward bias at zero command and enables backwards motion.

> ⚠️ Same gradual extension rule applies — never jump more than ~0.3 m/s per sub-phase.

**Sub-phase A** — `lin_vel_x=(-0.3, 1.0)`, load from Phase 2.5c, ~500 iter
**Sub-phase B** — `lin_vel_x=(-1.0, 1.0)`, load from 3a, ~500 iter

```python
self.commands.base_velocity.ranges.lin_vel_x = (-1.0, 1.0)
```

- Symmetric distribution forces the policy to truly stand at 0 m/s rather than shuffling forward.
- No other config changes needed — `feet_contact_at_rest` and `feet_air_time` are gait-agnostic.

### Phase 3.5 — Standing Smoothness (ABANDONED — see notes)

Attempted to tune unified policy for clean standing via heavier smoothness penalties. Root issue: `feet_air_time` (+2.0) and `feet_contact_at_rest` create equal-and-opposite tension at zero command — policy marches in place as equilibrium. Not fixable by weight tuning. Abandoned in favor of two-policy architecture.

**Final smoothness weights for walking policy** (moderate, protects gearboxes):
- `action_rate_l2`: **-0.01** (2× baseline)
- `dof_acc_l2`: **-2.5e-7** (2× baseline)
- `feet_contact_at_rest`: **-0.5**, threshold=**0.02 m/s** (near-zero only)

### Phase 4 — Push Recovery (Fine-Tune)

Load Phase 3b checkpoint. Re-enable push disturbances:

```python
self.events.push_robot = ...  # re-enable with moderate impulse
```

- **Duration**: ~500 iterations
- Increase push impulse gradually across runs if recovery is poor.

### Phase 5 — Rough Terrain Curriculum

> **Forward-only height scan masking** is already implemented — rear 8 columns of the 17×11
> grid are zeroed in `height_scan_forward_only` (mdp/observations.py). Matches forward-camera
> deployment (RealSense D435i). No observation dropout needed.

Train from scratch on `Isaac-Velocity-Rough-Atom-v0` with [512, 256, 128] network.

> **Why from scratch (not loading flat checkpoint):** The rough terrain PPO config uses a larger
> network [512, 256, 128] than flat [128, 128, 128]. Weight dimensions are incompatible, so
> `--resume` would fail. The terrain curriculum starts on easy terrain anyway, so the policy
> re-learns walking as part of the curriculum. Training from scratch is standard practice.

**Reward tuning for convergence** — match H1 reference values to reduce penalty burden during
initial learning. All relaxed penalties should be tightened in fine-tuning after convergence:

| Change | Initial (converge) | Post-convergence |
|--------|-------------------|-----------------|
| `flat_orientation_l2` | -1.0 (H1) | -5.0 |
| `joint_deviation_hip_roll` | -0.2 (H1) | -0.5 to -1.0 |
| `dof_torques_l2` | 0.0 (H1, disabled) | -1e-5 |
| `action_rate_l2` | -0.005 (H1) | -0.01 |
| `dof_acc_l2` | -1.25e-7 (H1) | -2.5e-7 |
| `feet_contact_at_rest` | disabled | keep disabled (standing uses separate policy) |
| `feet_air_time` | +2.0 | +2.0 (unchanged — standing uses separate policy) |
| `lin_vel_x` | (0.0, 1.0) forward only | (-1.0, 1.0) add backward in fine-tuning |

**Lesson from failed Run 29:** Training with heavy penalties (orientation -5.0, hip_roll -3.0,
torques -1e-5, smoothness 2× H1) prevented convergence — 83% of robots fell after 3000 iters.
Matching H1's lighter penalties lets the policy discover walking first, then tighten for quality.

**Domain randomization** (enable after initial convergence, in fine-tuning):
- `add_base_mass`: ±2 kg
- `base_com`: ±3 cm
- `push_robot`: ±0.75 m/s (already active)
- Motor strength randomization: ±15%
- **Ground friction range**:
  ```python
  "static_friction_range": (0.4, 1.2)   # dry rubber → wet tile
  "dynamic_friction_range": (0.3, 0.9)
  ```

**Terrain types** (procedurally generated by Isaac Lab): flat, rough, stairs up/down, discrete obstacles, stepping stones. The height scan (2D raycast grid from `base_link`) gives the policy terrain awareness.

- **Duration**: 1500 iterations initial; resume to 10,000 once convergence confirmed
- **Envs**: 4096
- **Network**: [512, 256, 128] actor+critic (larger capacity for terrain features)

### Phase 6 — Standing Policy (Train After Rough Terrain)

**Architecture**: Two-policy deployment. Switch between walking and standing policies at runtime:
```
if |v_cmd| < 0.05 m/s:   run standing_policy(obs)
else:                       run walking_policy(obs)
```
Both policies share the same observation space and action space — switching is just swapping network weights mid-inference. Optional: linearly blend policy outputs over ~0.5s near the threshold to avoid joint position discontinuities at transition.

**Training**: Load from the final rough terrain walking checkpoint.

**Gym env**: `Isaac-Standing-Flat-Atom-v0` / `Isaac-Standing-Flat-Atom-Play-v0` (already registered)

**Key config differences from walking** (in `AtomFlatStandingEnvCfg`):
- `lin_vel_x = (0.0, 0.0)` — zero command only
- `feet_air_time.weight = 0.0` — removed; eliminates reward tension with standing penalty
- `feet_contact_at_rest.weight = -5.0`, `threshold = 0.0` — unconditional, heavy
- `flat_orientation_l2.weight = -10.0` — stricter upright requirement

**On backward walking**: Backward capability (Phase 3, symmetric range) is retained in the walking policy. Speed is not a priority — the robot just needs to back away safely under teleoperation or autonomous control. The walking policy handles this; no separate backward policy needed.

### Phase 7 — Motor Friction Domain Randomization

Add after rough terrain is complete, immediately before sim-to-real transfer.

Train with a *range* around measured motor friction values (from motor characterization), not a single value. This is one of the dominant sources of sim-to-real gap.

**Requires**: motor characterization data (Coulomb friction, viscous damping from RS03 bench tests). Add joint `<dynamics>` to URDF and randomize the range in Isaac Lab via `ImplicitActuatorCfg` friction parameters.

---

## Step 7: Evaluate Checkpoint

```bash
cd atom_isaaclab && conda activate env_isaaclab && MPLBACKEND=Agg \
  /home/atoms/IsaacLab/isaaclab.sh -p scripts/play.py \
  --task Isaac-Velocity-Flat-Atom-Play-v0 --num_envs 50 \
  --load_run <run_id>
```

**Qualitative checks:**
- [ ] Bipedal stride with visible knee bend
- [ ] Arms roughly at sides (not flailing)
- [ ] Forward motion aligned with velocity arrow
- [ ] Stable at commanded speed, no oscillation

**Quantitative targets (flat terrain, 1000 iter):**
- `track_lin_vel_xy_exp` > 0.70
- `Episode_Termination/time_out` > 85%
- `Episode_Termination/root_height` < 10%
- `Episode_Termination/base_contact` ≈ 0%

---

## Sim Measurement Points → Real Sensor Mapping

Every quantity the policy observes in sim must map to a real sensor on the physical robot.
The sim measures from specific locations — the real sensor must be mounted at or near the
same location, or a coordinate transform must be applied.

| Sim Measurement | Sim Source Location | Real Sensor | Notes |
|---|---|---|---|
| Base angular velocity | `base_link` frame origin | IMU (gyroscope) | Mount IMU as close to torso COM as possible. If offset, apply lever arm correction in state estimator. |
| Base linear velocity | `base_link` frame origin | **Estimated** — not directly measurable | Fuse IMU integration + leg FK + contact timing. This is the hardest sim-to-real mapping. |
| Projected gravity vector | `base_link` orientation | IMU (accelerometer + filter) | Use Madgwick or EKF to get orientation from accel + gyro. |
| Joint positions | Each joint axis | Motor encoders | Direct mapping. Ensure encoder zero = URDF joint zero. |
| Joint velocities | Each joint axis | Motor encoders (differentiated) | Apply low-pass filter — raw differentiated encoders are noisy. |
| Foot contact state | `Foot_Left_1`, `Foot_Right_1` bodies | Foot FSRs or motor current sensing | Threshold contact force. Binary contact is sufficient for current reward structure. |
| Height scan (rough terrain) | Raycasts from `base_link`, 2D grid | Depth camera point cloud | Camera must be mounted so its FOV covers the same grid region used in sim. Match grid resolution and range exactly. |

### IMU Placement

The sim measures base state at `base_link`, which after the `base_to_torso` fixed joint
is effectively at the center of `Torso_With_Motors_1`. Mount the IMU as close to this
point as physically possible. If the IMU is offset (e.g. mounted on a bracket), the
angular velocity measurement will include a centripetal term that must be corrected:

```
v_corrected = v_imu - ω × r_offset
```

### Depth Camera Placement (Rough Terrain)

The height scan in sim is a 2D grid of raycasts fired downward from `base_link`.
When integrating the depth camera:
- Mount position relative to torso must match the sim prim path offset
- Verify the camera FOV covers the full scan grid at typical walking speed
- The point cloud must be projected into the robot's base frame before being fed to the policy

### State Estimator (Future Work)

A lightweight onboard state estimator will be needed to produce the base linear velocity
observation, which cannot be measured directly. Recommended approach:
1. Extended Kalman Filter fusing IMU + leg kinematics + contact detection
2. Train with observation noise randomization in sim to make policy robust to estimator error
3. Validate estimator accuracy before attempting real-world deployment

---

## Step 8: Onboard Deployment

### Policy Network Size

The trained policy is a small MLP — compute is not a concern on any modern edge hardware:

| Policy | Architecture | Obs | Params | Inference @ 50 Hz |
|---|---|---|---|---|
| Walking (rough) | [512, 256, 128] | 247 | ~292k | < 1 ms |
| Standing | [512, 256, 128] | 247 | ~292k | < 1 ms |

Control frequency: 50 Hz (decimation=4 × sim_dt=5ms). The MLP forward pass is a negligible fraction of the 20ms budget.

### Hardware Options (Decision Pending)

| Board | AI Perf | RAM | Power | Notes |
|---|---|---|---|---|
| Jetson Orin Nano 4GB | 20 TOPS | 4 GB | 7–10 W | Workable for flat terrain only; tight for full perception stack |
| Jetson Orin Nano 8GB | 40 TOPS | 8 GB | 10–15 W | Sufficient for flat + rough with careful memory management |
| Jetson Orin NX 8GB | 70 TOPS | 8 GB | 10–20 W | Recommended minimum for full stack (policy + EKF + depth processing) |
| Jetson Orin NX 16GB | 70 TOPS | 16 GB | 10–25 W | Comfortable headroom; allows SLAM or visual odometry alongside policy |
| Jetson AGX Orin | 275 TOPS | 32 GB | 15–60 W | Overkill for inference; useful if running perception-heavy tasks |

The binding constraint is not inference — it is memory for the full ROS 2 + librealsense + EKF + motor control stack running simultaneously.

### TensorRT Export (Before Deployment)

Export trained policy from PyTorch → ONNX → TensorRT for 5–10× speedup on Jetson Tensor Cores:

```python
# RSL-RL provides ONNX export — run after training completes
# (exact call depends on rsl_rl version; check rsl_rl/runners/on_policy_runner.py)
runner.save_onnx("policy.onnx")
```

Then on the Jetson:
```bash
trtexec --onnx=policy.onnx --saveEngine=policy.trt --fp16
```

Use FP16 — sufficient precision for MLP locomotion policies and roughly 2× faster than FP32 on Ampere Tensor Cores.

### Intel RealSense D435i Integration

The D435i provides depth + RGB + IMU (BMI055, 6-DOF).

**IMU use:**
- Gyroscope: adequate for attitude estimation at 200–400 Hz
- Accelerometer: adequate; noise is higher than dedicated IMUs
- Known limitation: D435i IMU noise is higher than industrial-grade IMUs (e.g. VectorNav VN-100, Bosch BMI088). If base velocity estimation is poor in practice, a dedicated IMU mounted close to `base_link` is the fix.

**Depth → height scan pipeline (Extreme Parkour approach):**
- Sim height scan: 17×11 grid (187 points), forward-only (rear 8 cols zeroed)
- **Learned estimator**: train a small CNN on paired (D435i depth image, ray-cast height scan) data collected in sim
- At deployment: D435i depth → CNN → 187-dim height scan → policy
- CNN runs at 10–30 Hz on Orin Nano; policy interpolates between updates at 50 Hz
- A separate **velocity estimator** (small MLP/RNN) maps proprioceptive history → base linear velocity
- See `TODO.md` for training pipeline tasks

**Encoder zero calibration:**
Motor encoder zeros must match URDF joint zeros exactly. Establish a known calibration pose (all joints at 0 rad per URDF definition) and record encoder offsets at manufacturing/assembly time.

### Deployment Checklist

- [ ] TensorRT engine built and tested on target hardware
- [ ] Motor encoder zeros calibrated against URDF joint zeros
- [ ] IMU mounted as close to `base_link` COM as possible; lever arm offset measured
- [ ] EKF state estimator implemented and validated (base linear velocity estimate)
- [ ] D435i depth → height grid pipeline implemented and latency measured (target < 10 ms)
- [ ] Policy control loop verified at 50 Hz with real sensor inputs
- [ ] Robot suspended in harness for first power-on test (same as the straight-leg init condition trained in Phase 2)

---

## Known Issues & Gotchas

- `joint_drive=None` required in `UrdfFileCfg` when using `ImplicitActuatorCfg`
- Right-side joints use **negative** sign convention in `init_state.joint_pos`
- `reset_joints_by_scale` with straight-leg init + range including 0 causes ground interpenetration — keep minimum scale > 0, or raise spawn height to accommodate
- `play.py` must be run from `atom_isaaclab/` directory (log path resolves relative to CWD)
- Always kill stale Isaac processes before launching: `ps aux | grep "env_isaaclab/bin/python"`
- `MPLBACKEND=Agg` required on all commands to prevent tkinter crash
- VRAM is not the training bottleneck — Isaac uses ~4.6 GB at 6144 envs; CPU PhysX pipeline is the ceiling
