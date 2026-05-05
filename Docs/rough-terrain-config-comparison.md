# Rough Terrain Config Comparison: H1 vs G1 vs Atom

Generated 2026-03-14. Source files:
- H1: `IsaacLab/.../config/h1/rough_env_cfg.py`
- G1: `IsaacLab/.../config/g1/rough_env_cfg.py`
- Atom: `atom_isaaclab/.../atom_env_cfg.py` (`AtomRoughEnvCfg`)
- Base defaults: `IsaacLab/.../velocity_env_cfg.py` (`RewardsCfg`, `EventCfg`)

---

## Reward Terms

| Term | Base Default | H1 Rough | G1 Rough | Atom Rough | Notes |
|------|-------------|----------|----------|------------|-------|
| `termination_penalty` | — | -200 | -200 | -200 | All match |
| `track_lin_vel_xy_exp` | 1.0 (exp, std=√0.25) | 1.0 (yaw_frame_exp, std=0.5) | 1.0 (yaw_frame_exp, std=0.5) | 1.0 (yaw_frame_exp, std=0.5) | All use yaw-frame variant |
| `track_ang_vel_z_exp` | 0.5 (exp, std=√0.25) | 1.0 (world_exp, std=0.5) | **2.0** (world_exp, std=0.5) | 1.0 (world_exp, std=0.5) | G1 prioritizes turning 2× more |
| `lin_vel_z_l2` | -2.0 | **None** | **0.0** | **None** | Both suppress it; Atom matches H1 |
| `ang_vel_xy_l2` | -0.05 | -0.05 (inherited) | -0.05 (inherited) | -0.05 (inherited) | All inherit base |
| `dof_torques_l2` | -1e-5 | **0.0** | **-1.5e-7** (legs+ankles only) | **0.0** | H1/Atom disable; G1 uses light version on key joints |
| `dof_acc_l2` | -2.5e-7 | **-1.25e-7** | **-1.25e-7** (legs only) | **-1.25e-7** | All halve vs base |
| `action_rate_l2` | -0.01 | **-0.005** | **-0.005** | **-0.005** | All halve vs base |
| `flat_orientation_l2` | 0.0 | **-1.0** | **-1.0** | **-1.0** | All enable |
| `feet_air_time` | 0.125 (`feet_air_time`) | **0.25** (`positive_biped`, thresh=0.4) | **0.25** (`positive_biped`, thresh=0.4) | **⚠️ 3.0** (`positive_biped`, thresh=0.4) | **Atom is 12× H1/G1** |
| `feet_slide` | — | -0.25 | **-0.1** | -0.25 | Atom matches H1; G1 lighter |
| `dof_pos_limits` | 0.0 | **-1.0** (ankles only) | **-1.0** (ankles+knees) | **-1.0** (ankles+knees) | Atom matches G1 |
| `undesired_contacts` | -1.0 (THIGHs) | **None** | **None** | **⚠️ -1.0** (thighs, shins, arms, hips, shoulders) | **Atom keeps active; H1/G1 disable** |
| `joint_deviation_hip` | — | -0.2 (yaw+roll) | -0.1 (yaw+roll) | -0.2 (roll only) | Atom has no hip yaw; weight matches H1 |
| `joint_deviation_arms` | — | -0.2 | -0.1 | -0.2 | Atom matches H1 |
| `joint_deviation_torso` | — | -0.1 | -0.1 | **None** | Atom has no torso joint |
| `feet_contact_at_rest` | — | — | — | **None** (flat: -0.5) | Correctly disabled for rough |
| `foot_clearance` | — | — | — | **None** | Correctly disabled for rough |

---

## Understanding `feet_air_time_positive_biped`

This is **not** a simple air-time counter. It rewards:
- Being in **single stance** (exactly one foot touching ground)
- The *minimum* of (`current_contact_time`, `current_air_time`) across both feet
- Clamped at `threshold` (0.4 s) — so the max possible reward per step per env is `0.4 × weight`

| Config | Max reward/step | Fraction of total reward |
|--------|----------------|--------------------------|
| H1 | 0.4 × 0.25 = **0.10** | Small component |
| G1 | 0.4 × 0.25 = **0.10** | Small component |
| Atom | 0.4 × 3.0 = **1.20** | **12× larger** |

The Atom `feet_air_time` weight of 3.0 was set to "encourage higher foot clearance and more dynamic stepping" but **`feet_air_time_positive_biped` does not reward foot clearance height** — it rewards timing symmetry (equal single-stance dwell time). The 12× over-weighting almost certainly causes the policy to hyper-focus on stepping at the expense of stability and velocity tracking.

---

## Randomization / Events

| Setting | H1 | G1 | Atom |
|---------|----|----|------|
| `push_robot` | None | None | None |
| `add_base_mass` | None | None | None |
| `base_com` | None | None | None |
| `reset_robot_joints` position_range | **(1.0, 1.0)** | **(1.0, 1.0)** | **(1.0, 1.0)** |
| `reset_base` velocity_range | **(0,0) all** | **(0,0) all** | **(0,0) all** |
| `physics_material` friction | inherited (0.8/0.6) | inherited (0.8/0.6) | explicitly set (0.8/0.6) |

All three disable the same domain randomization for initial convergence. Atom explicitly sets friction to the same values as the base default.

---

## Commands

| Setting | H1 | G1 | Atom |
|---------|----|----|------|
| `lin_vel_x` | (0.0, 1.0) | (0.0, 1.0) | (0.0, 1.0) |
| `lin_vel_y` | **(0.0, 0.0)** | **(0.0, 0.0)** | **(0.0, 0.0)** |
| `ang_vel_z` | (-1.0, 1.0) | (-1.0, 1.0) | (-1.0, 1.0) |

All match. No lateral velocity during rough terrain training.

---

## Terminations

| Setting | H1 | G1 | Atom |
|---------|----|----|------|
| `base_contact` body | `.*torso_link` | `torso_link` | `base_link` |
| `bad_orientation` | — (inherited?) | — | **enabled** (limit=1.0 rad) |
| `root_height` | — | — | **None** (disabled for rough) |

Atom has an extra explicit `bad_orientation` termination (~57° tilt). This is reasonable and may help — a robot that's fallen but not yet torso-contacting gets terminated.

---

## Network Architecture (PPO)

| Setting | H1 Rough | Atom Rough |
|---------|----------|------------|
| Actor/critic dims | [512, 256, 128] | [512, 256, 128] |
| Activation | elu | elu |
| `init_noise_std` | 1.0 | 1.0 |
| `num_learning_epochs` | 5 | 5 |
| `num_mini_batches` | 4 | 4 |
| `learning_rate` | 1e-3 | 1e-3 |
| `clip_param` | 0.2 | 0.2 |
| `entropy_coef` | 0.01 | 0.01 |
| `desired_kl` | 0.01 | 0.01 |
| `max_iterations` | 3000 | 10000 |

PPO configs are identical. Max iterations differ (Atom set higher for rough convergence).

---

## Critical Issues in Atom Rough Config

### 1. `feet_air_time` weight: 3.0 → should be 0.25

**This is almost certainly the primary cause of Atom's rough terrain training difficulties.**

At weight 3.0, the stepping reward signal is 12× larger than the velocity tracking reward (weight 1.0), which is itself the primary task. The policy will optimize stepping timing far ahead of actually walking in the commanded direction. On rough terrain where single-stance is harder to achieve and maintain, this over-weighting creates a reward landscape that's hard to optimize.

**Fix**: Set `feet_air_time.weight = 0.25` (match H1/G1 exactly).

### 2. `undesired_contacts` enabled on rough terrain

H1 and G1 **both disable `undesired_contacts` for rough terrain**. The reason: shin, thigh, and hip contact is a natural consequence of traversing stairs, slopes, and obstacles. Penalizing it prevents the policy from learning contact-rich locomotion strategies appropriate for rough terrain.

At weight -1.0 across many body parts (thighs, shins, upper/mid/lower arms, hip housings, shoulder housings), this creates a strong avoidance pressure that may cause the robot to contort awkwardly or even fall to avoid contact rather than just walking through it.

**Fix**: Set `self.rewards.undesired_contacts = None` in `AtomRoughEnvCfg.__post_init__()`.

### 3. Minor: `dof_torques_l2` — already correctly set to 0.0

Atom already matches H1 here (disabled). G1 has a light version; can add post-convergence.

---

## Summary: What to Change for Next Rough Terrain Run

```python
# In AtomRoughEnvCfg.__post_init__():
self.rewards.feet_air_time.weight = 0.25      # was 3.0 — match H1/G1
self.rewards.undesired_contacts = None         # was -1.0 — match H1/G1
```

These two changes align Atom with the H1/G1 reference configurations. Everything else is already matched or intentionally adapted to Atom's morphology (no hip yaw, no torso joint, different foot body names).
