# Atom Humanoid — Training Log

Chronological record of training runs, configuration changes, and qualitative observations.
Updated after every training run review.

---

> **CRITICAL FINDING (2026-03-12):** `--resume` is required to load checkpoint weights.
> Without it, `--load_run` is silently ignored (`train.py:177` checks `agent_cfg.resume`).
> All Phase 1–4 runs below used `--load_run` without `--resume` — they trained from scratch
> each time. Improvements came from config changes, not weight transfer.
> Correct command: `--resume --load_run <run_id>`. The iteration counter continues from the
> checkpoint (cosmetic TensorBoard issue — use wall time X-axis to separate phases).

---

## Phase 1 — Learn to Walk (Flat Terrain, Bent-Knee Init)

### Run 1 — 2026-03-08_23-56-07
**Config:** V0.6 URDF (pre-reorientation), 4096 envs, 1000 iterations
**Issue:** Coordinate frame wrong — robot walked side-to-side. Velocity arrow pointed backward.
**Outcome:** Discarded. Led to V0.7 URDF reorientation and virtual root joint fix.

### Run 2 — 2026-03-09_18-41-04
**Config:** V0.7_clean URDF, base_to_torso fixed joint, armature not yet set, position_range=(0.5,1.5), knee stiffness=100, joint_deviation_hip_roll=-3.0
**Metrics (1000 iter):** time_out=97%, root_height=2.6%, mean_reward=31.1, track_lin_vel_xy≈0.66
**Visual review:** Robot walks forward correctly. No lateral shuffle. Knees still largely straight — policy found a hip-dominant walking strategy. Stable and upright throughout.
**Assessment:** Strong Phase 1 result. Coordinate frame confirmed fixed. Knee bending remains a known limitation of flat terrain training — expected to improve with rough terrain curriculum.

### Run 3 — 2026-03-09_21-30-35 *(current Phase 1 baseline)*
**Config:** Same as Run 2 + knee URDF joint limits (min 0.15 rad bend), dof_pos_limits on knees + ankles, armature=0.005 (RS03 reflected inertia added mid-run), position_range=(0.5,1.5)
**Metrics (1000 iter):** time_out=95.8%, root_height=4.1%, mean_reward=22.1, track_lin_vel_xy≈0.66
**Visual review:** Robot walks forward. Knee limits enforcing minimum bend are visible — gait looks slightly more natural than Run 2. Mean reward lower than Run 2 (knee limits make the task harder — the optimizer has less freedom). Still stable and upright.
**Assessment:** Accepted as Phase 1 baseline for Phase 2 fine-tune. Lower reward vs Run 2 is expected — enforced knee bend is a constraint, not a regression.

---

## Phase 2 — Straight-Leg Adaptation

### Run 4 — 2026-03-09_22-57-32
**Starting from:** Phase 1 Run 3 checkpoint (model_999.pt, 2026-03-09_21-30-35)
**Changes:**
- Init pose: knee=±0.15 rad (URDF lower limit — straightest allowed), ankle=-0.05, spawn height=0.85m
- position_range: (0.0, 1.0)
- armature=0.005 kg·m² on all actuator groups (RS03 reflected inertia)
**Note:** Init pose originally set to ±0.05 rad; rejected at launch by Isaac Sim (outside URDF joint limits). Corrected to ±0.15 rad before run.

**Metrics (1000 iter):** time_out=97.1%, root_height=2.7%, mean_reward=27.3
**Visual review:** Gait improved over Phase 1 — more stable, better metrics across the board. Knees still somewhat stiff (minimum bend visible but not deep flexion). Arms flare side-to-side in counter-phase with steps — unnatural for human gait; arms acting as passive counterweights rather than actively swinging. No lateral shuffle. Forward motion clean and consistent.
**Assessment:** Accepted as Phase 2 baseline. Arm behavior and knee stiffness are known limitations — arm swing reward and rough terrain curriculum expected to address both in later phases.

---
## Phase 2.5 — Standing + Slow Walk Curriculum

### Run 5 — 2026-03-09_23-14-35 *(aborted)*
**Config:** Phase 2.5 first attempt — lin_vel_x=(0.0,1.0) + push_robot re-enabled simultaneously
**Metrics (iter 238):** time_out=0.7%, root_height=99.2%, mean_reward=-0.79
**Outcome:** Catastrophic collapse. Zero-velocity command completely out of distribution for Phase 2 policy; push disturbances compounded the problem. Gradient updates from failing zero-command episodes destroyed walking weights within ~200 iterations. Killed.

### Run 6 — 2026-03-09_23-18-49 *(aborted)*
**Config:** lin_vel_x=(0.0,1.0), no pushes, loaded from Phase 2
**Metrics (iter 134):** time_out=0%, root_height=100%, mean_reward=-3.66
**Outcome:** Still catastrophic. Even without pushes, jumping directly to (0.0,1.0) caused catastrophic forgetting. Killed.

### Run 7 — 2026-03-09_23-21-46 *(Phase 2.5a)*
**Config:** Gradual extension — lin_vel_x=(0.3,1.0), no pushes, loaded from Phase 2
**Metrics (1000 iter):** time_out=96.4%, root_height=3.3%, mean_reward=27.8
**Outcome:** Success. Gradual range extension prevented catastrophic forgetting. Policy adapted to slower speeds without losing walking ability.

### Run 8 — 2026-03-09_23-32-17 *(Phase 2.5b — current baseline)*
**Config:** lin_vel_x=(0.0,1.0), no pushes, loaded from Run 7
**Metrics (1000 iter):** time_out=98.6%, root_height=1.3%, mean_reward=26.0
**Visual review:** Walking gait clean and stable. Best survival metrics across all phases. Standing behavior not visually confirmed — play config fixes command at 1.0 m/s. User noted concern: policy may still walk in place at zero command despite feet_air_time being gated at cmd<0.1 m/s — no active penalty prevents foot lifting while standing.
**Assessment:** Accepted as Phase 2.5 baseline. feet_contact_at_rest penalty added for next run.

### Run 9 — 2026-03-10_19-00-39 *(Phase 2.5c)*
**Starting from:** Phase 2.5b checkpoint (2026-03-09_23-32-17)
**Changes:**
- New reward: `feet_contact_at_rest` weight=-0.5 (penalizes foot air time when cmd speed < 0.1 m/s)
- Custom mdp module: `atom_isaaclab/tasks/locomotion/velocity/mdp/rewards.py`

**Recovery curve:** Catastrophic collapse iter 1–~250 (mean_reward ≈ -5, root_height ~99%). Recovered to positive around iter 250, climbed steadily back to ~26 by iter 999.
**Metrics (1000 iter):** time_out=97.6%, root_height=2.2%, base_contact=0.0%, mean_reward=25.9, track_lin_vel_xy=0.813, feet_contact_at_rest=-0.004
**Assessment:** Policy recovered and essentially matched 2.5b metrics. `feet_contact_at_rest` penalty is active. Slight dip vs 2.5b due to ~250 wasted collapse iterations. Followed by 2.5d consolidation run.

### Run 10 — 2026-03-10_19-44-55 *(Phase 2.5d — current baseline)*
**Starting from:** Phase 2.5c checkpoint (2026-03-10_19-00-39)
**Changes:**
- Envs: 5120 (up from 4096)
- Iterations: 1500 (up from 1000) — consolidation, no config changes

**Recovery curve:** Same collapse-on-load pattern as 2.5c — iter 1–~250 catastrophic, recovered ~iter 300, climbed to 28+ by iter 900, stabilized 28–29 through iter 1500.
**Metrics (1500 iter):** time_out=98.8%, root_height=1.1%, base_contact=0.0%, mean_reward=29.2, track_lin_vel_xy=0.808, feet_contact_at_rest=-0.003, steps/s=~242k
**Assessment:** Best result across all phases. Extra iterations and 5120 envs both contributed — 242k steps/s vs 212k previously. feet_contact_at_rest shrinking (-0.004→-0.003), policy learning cleaner standing behavior. Accepted as Phase 2.5 final baseline. GPU VRAM peaked ~70% at 5120 envs — physics simulation is the throughput bottleneck, not compute; further env increases will have diminishing returns. Collapse-on-load pattern (2.5c and 2.5d both, but not 2.5a/b) suspected tied to feet_contact_at_rest changing optimizer landscape on resume — not blocking, recovery is consistent.

**Next:** Phase 3a — backwards walking, lin_vel_x=(-0.3, 1.0), load from 2026-03-10_19-44-55.

---

## Phase 3 — Backwards Walking

### Run 11 — 2026-03-10_21-38-58 *(Phase 3a)*
**Starting from:** Phase 2.5d checkpoint (2026-03-10_19-44-55)
**Changes:**
- lin_vel_x: (0.0, 1.0) → (-0.3, 1.0) — gradual backwards extension
- Envs: 6144

**Recovery curve:** Same collapse-on-load pattern — iter 1–~250 catastrophic, recovered ~iter 300, stabilized 27–27.5 from ~iter 900 through 1500.
**Metrics (1500 iter):** time_out=97.1%, root_height=2.8%, base_contact=0.0%, mean_reward=27.2, track_lin_vel_xy=0.825, feet_contact_at_rest=-0.006, steps/s=~266k
**Assessment:** Expected slight dip in survival metrics when introducing new command regime. track_lin_vel_xy improved to 0.825 — policy tracking velocity accurately across wider range. feet_contact_at_rest increased (-0.003→-0.006) suggesting more foot-lifting near zero command; worth watching in 3b. 6144 envs confirmed faster than 5120 (266k vs 242k steps/s). Accepted as Phase 3a baseline; proceeding to 3b.

**Next:** Phase 3b — full symmetric range, lin_vel_x=(-1.0, 1.0), 8192 envs, load from 2026-03-10_21-38-58.

### Run 12 — 2026-03-10_22-35-46 *(Phase 3b)*
**Starting from:** Phase 3a checkpoint (2026-03-10_21-38-58)
**Changes:**
- lin_vel_x: (-0.3, 1.0) → (-1.0, 1.0) — full symmetric range
- Envs: 8192

**Recovery curve:** Slower recovery than 3a — full range extension is a bigger adaptation. Barely positive at iter ~300 (vs iter ~300 for 3a too, but slower climb). Still trending upward at iter 1500 — not converged.
**Metrics (1500 iter):** time_out=96.9%, root_height=2.9%, base_contact=0.0%, mean_reward=21.5, track_lin_vel_xy=0.769, feet_contact_at_rest=-0.005, steps/s=~308k
**Assessment:** Policy still learning at cutoff — reward climbing steadily (14→18→20→22) with no plateau. track_lin_vel_xy drop (0.825→0.769) reflects backward gait still being refined. feet_contact_at_rest improved slightly (-0.006→-0.005), standing behavior holding. 8192 envs: 308k steps/s — another jump from 266k (6144 envs), more envs still helping. Consolidation run (3c) needed to let it fully converge.

**Next:** Phase 3c — same config, load from 2026-03-10_22-35-46, let reward plateau.

### Run 13 — 2026-03-10_22-54-02 *(Phase 3c — current baseline)*
**Starting from:** Phase 3b checkpoint (2026-03-10_22-35-46)
**Changes:** None — consolidation run, 8192 envs, same config
**Note:** Output went to TensorBoard events only (stdout empty) — metrics extracted from events file.

**Metrics (1500 iter, final 5-iter avg):** time_out=96.9%, root_height=3.0%, base_contact=0.0%, mean_reward=21.7, track_lin_vel_xy=0.772, feet_contact_at_rest=-0.005, feet_air_time=0.301
**Assessment:** Policy converged — 3c gave zero improvement over 3b (21.5→21.7, within noise). Full symmetric range (-1.0, 1.0) plateaued at ~21.5-22 mean reward vs 29.2 in 2.5d. Drop is expected: backward gait is harder and collapse-on-load wastes ~300 iterations per run. Fundamentals healthy: 96.9% survival, 0% body contact. Accepted as Phase 3 final baseline.

**Play review (randomized -1.0 to 1.0 commands):** Good gait mechanics across the board — forward and backward walking both present and recognizable. Standing robots observed bouncing in place rather than holding position cleanly.
**Play review (zero command):** Confirmed — bouncing/oscillation is a true standing issue, not a slow-command artifact. Policy lifts feet repeatedly at rest instead of holding still. Energetically wasteful and would look wrong on hardware. Phase 3.5 added to address this before Phase 4.

**Next:** Phase 3.5 — standing smoothness fine-tune. feet_contact_at_rest: -0.5→-2.0, action_rate_l2: -0.005→-0.02, dof_acc_l2: -1.25e-7→-5e-7. Load from 2026-03-10_22-54-02.

---

## Phase 5 — Rough Terrain Curriculum

### Run 20 — 2026-03-11_22-45-12 *(discarded)*
**Config:** Isaac-Velocity-Rough-Atom-v0, 4096 envs, loaded from Phase 4a
**Issue:** Observation dimension mismatch — flat policy was trained with height_scan=None (60 obs), rough terrain env has height scanner enabled (247 obs). RSL-RL silently initialized from scratch. Policy made zero progress over 202 iterations (mean_reward=-4.1, flat trend, time_out=0%).
**Decision:** Enable height scanner in flat terrain env too, so obs dim is consistent throughout the entire curriculum. Retraining from Phase 1 with full sensor suite.

---

## Phase 5 — Rough Terrain (First Attempt, Failed)

### Run 20 — 2026-03-11_22-41-40 / 2026-03-11_22-45-12 / 2026-03-11_22-54-51 *(discarded)*
**Starting from:** Phase 4a checkpoint (2026-03-11_00-26-43)
**Config:** Isaac-Velocity-Rough-Atom-v0, 4096 envs, terrain curriculum + height scanner enabled, push_robot ±0.75 m/s

**Issue: Observation dimension mismatch.** The flat policy was trained with `height_scan=None` (60 obs). The rough terrain env enables the height scanner, adding 187 raycast points (247 obs total). RSL-RL detected the architecture mismatch and silently initialized the network from scratch rather than loading the flat checkpoint weights. The policy was effectively random.

**Evidence:** mean_reward stuck at -4.2 for all 2256 iterations (longest run). Zero improvement — flat learning curve. time_out=0% (all robots falling immediately). Confirmed by inspecting model weights: `actor.0.weight` was [128, 60] in the flat checkpoint but [512, 247] in the rough run.

**Root cause:** `AtomFlatEnvCfg` set `height_scanner = None` and `height_scan = None`, removing the height scanner from the flat training observation space. This made flat and rough policies architecturally incompatible — weights can't transfer between different input dimensions.

---

## Retraining from Phase 1 — Full Sensor Suite

### Decision: Retrain everything with height scanner enabled from the start

**Motivation:**
1. **Architecture consistency** — obs dim must be 247 throughout the entire curriculum (flat → rough) so checkpoint weights transfer cleanly at every phase transition
2. **V1 hardware target** — the Atom Humanoid V1 targets a RealSense D435i (or similar depth sensor) for terrain perception. Training with the height scanner from the start matches the deployment sensor suite.
3. **Forward-only masking** — the D435i is forward-facing and cannot see behind the robot. A custom `height_scan_forward_only` observation function zeros the rear 8 columns (88 of 187 points, x < 0m) of the 17×11 height scan grid. The policy learns with partial height data from day one, eliminating any sim-to-real mismatch from missing rear coverage.
4. **Training investment is modest** — prior flat terrain training took ~2 days total. Retraining is worth the cost for a clean foundation.

**Config changes applied:**
- Removed `self.scene.height_scanner = None` and `self.observations.policy.height_scan = None` from `AtomFlatEnvCfg`
- Created `mdp/observations.py` with `height_scan_forward_only()` — zeros rear 8 columns of the 17×11 grid
- Overrode `self.observations.policy.height_scan` in `AtomRoughEnvCfg` to use `height_scan_forward_only` with ±0.1 uniform noise and [-1, 1] clipping (matching upstream)
- Hardware notes documented in `Docs/hardware-notes.md` (sensor candidates, rear camera gap options)

All prior Phase 1–4 runs are archived for reference but superseded.

### Run 21 — 2026-03-11_22-28-00 *(discarded — pre-masking)*
**Config:** Flat env with height scanner enabled, but BEFORE forward-only masking was added. Full 187-point scan (no rear zeroing).
**Outcome:** Killed at 474 iters (reward=-3.7) to add the forward-only masking before the policy learned to depend on rear data.

### Run 22 — 2026-03-11_23-39-16 *(discarded — pre-masking)*
**Config:** Same as Run 21. Killed at 874 iters (reward=0.86) — still pre-masking config.

### Run 23 — 2026-03-11_23-50-12 *(Phase 1, current baseline)*
**Config:** Flat env, height scanner enabled, forward-only masking active (rear 88 points zeroed). 4096 envs, 1500 iters, fresh start (no checkpoint).
**Metrics (1500 iter):** time_out=73.3%, root_height=25.1%, mean_reward=5.4, track_lin_vel_xy=0.66
**Play review:** Walking gait present but odd — general rightward drift over time. No major red flags for a first run with 247 obs (vs 60 previously). Metrics lower than original Phase 1 (97% time_out) — expected, larger obs space needs more training time.
**Assessment:** Accepted as Phase 1 baseline for continued training. Rightward drift should self-correct with more iterations.

### Run 24 — 2026-03-12_00-10-01 *(discarded — no --resume)*
**Config:** Flat env, 4096 envs, --load_run without --resume. Training from scratch (identical to Run 23). Discarded after discovering --resume requirement.

### Run 25 — 2026-03-12_00-15-58 *(Phase 2, first --resume fine-tune)*
**Starting from:** Run 23 checkpoint (2026-03-11_23-50-12), with --resume
**Metrics (steps 1499–2998):** time_out=84.6%, root_height=14.7%, mean_reward=10.3, track_lin_vel_xy=0.71
**Play review:** Walking improved over Phase 1. Leftward drift (previously rightward in Phase 1). No major issues.

### Run 26 — 2026-03-12_00-32-46 *(Phase 2 consolidation)*
**Starting from:** Run 25 (--resume)
**Metrics (steps 2998–4497):** time_out=84%, root_height=~15%, mean_reward=11.2 (last 100 avg), track_lin_vel_xy improving
**Assessment:** Still climbing slowly (+0.31 reward per 100 iters). Gradient positive but shallow. Not converged.

### Run 27 — 2026-03-12_00-32-46 *(Phase 2 overnight, part 1)*
**Starting from:** Run 26 (--resume)
**Config:** max_iterations bumped to 10,000. Run stopped at iter 4497 (~1500 iters).
**Metrics (steps 2998–4497):** time_out=84%, mean_reward=10.8, track_lin_vel_xy=0.717

### Run 28 — 2026-03-12_00-51-10 *(Phase 2 overnight consolidation, 10,000 iters)*
**Starting from:** Run 27 (--resume)
**Config:** 4096 envs, full 247-obs sensor suite (height scanner + forward-only masking), push ±0.75 m/s, lin_vel_x=(-1.0, 1.0), max_iterations=10,000.
**Metrics progression:**
| Point | time_out | mean_reward | track_vel_xy | bad_orient | root_height |
|-------|----------|-------------|--------------|------------|-------------|
| ~1000 iters | 84.9% | 11.7 | 0.713 | 0.7% | 14.4% |
| ~5000 iters | 90.0% | 15.6 | 0.752 | 2.7% | 7.5% |
| Final (10k) | 88.2% | 15.1 | 0.736 | 2.7% | 9.2% |

**Assessment:** Policy plateaued. Hit 90% time_out at midpoint but oscillates 88–90% in the second half. Root height terminations (~9%) are the main failure mode. No meaningful improvement after ~5000 iters. Flat terrain with full sensor suite is converged.

**Decision:** Proceed to Phase 5 (rough terrain). This is a solid flat-terrain baseline with 247 obs dims matching the rough terrain env.

---

## Phase 5 — Rough Terrain (From Scratch, [512,256,128] Network)

### Run 29 — 2026-03-12_10-49-04 *(failed — penalties too heavy)*
**Config:** Isaac-Velocity-Rough-Atom-v0, 4096 envs, [512,256,128] network, 3000 iters. From scratch (network size incompatible with flat [128,128,128] checkpoint). feet_air_time=0.25, flat_orientation=-5.0, hip_roll=-3.0, dof_torques=-1e-5, action_rate=-0.01, dof_acc=-2.5e-7.
**Metrics (3000 iters):** mean_reward=-4.3 (never went positive), time_out=10%, root_height=83%, track_vel=0.003.
**Assessment:** Policy couldn't learn to walk. 83% of robots fell below height threshold. Heavy penalty burden prevented exploration — the policy was punished for everything it tried before it could discover a walking gait.

### Run 30 — 2026-03-12_22-13-06 *(failed — still too heavy, only feet_air_time changed)*
**Config:** Same as Run 29 but feet_air_time bumped to 2.0. All other penalties unchanged.
**Metrics (872 iters before killed):** mean_reward=-4.3, time_out=15% (slight improvement), root_height=76%. Still not converging.
**Assessment:** feet_air_time alone wasn't the issue. The combination of heavy orientation (-5.0), hip roll (-3.0), torque cost (-1e-5), and 2x smoothness penalties created too much penalty burden for a from-scratch policy on rough terrain.

### Run 31 — 2026-03-12_22-56-57 *(H1-matched rewards, pushes still active)*
**Config changes (all relative to Runs 29-30):**
- `flat_orientation_l2`: -5.0 → **-1.0** (match H1)
- `joint_deviation_hip_roll`: -3.0 → **-0.2** (match H1; Atom has no hip yaw)
- `dof_torques_l2`: -1e-5 → **0.0** (match H1, disabled)
- `action_rate_l2`: -0.01 → **-0.005** (match H1)
- `dof_acc_l2`: -2.5e-7 → **-1.25e-7** (match H1)
- `feet_contact_at_rest`: -0.5 → **disabled** (standing uses separate policy)
- `lin_vel_x`: (-1.0, 1.0) → **(0.0, 1.0)** (forward only, match H1; add backward later)
- `feet_air_time`: **+2.0** (kept from Run 30)
- push_robot: still ±0.75 m/s (forgot to disable)
**Metrics (1500 iters):** mean_reward=-4.2, time_out=6%, root_height=82%, bad_orientation=14%.
**Assessment:** Worse than Run 30 — reducing orientation penalty without disabling pushes made bad_orientation spike. Push disturbances too much for a from-scratch policy.

### Run 32 — 2026-03-12_23-30-04 *(H1-matched rewards, pushes disabled)*
**Config changes (relative to Run 31):**
- `push_robot`: **disabled** (H1 also disables pushes)
**Metrics (1500 iters):** mean_reward=-4.2, time_out=18%, root_height=71%, bad_orientation=11%.
**Assessment:** Best rough terrain run so far. Time_out trending upward (0→18%). Root_height terminations down from 82% to 71%. Still not converging in 1500 iters but gradient positive. Play review: robots visibly learning — some managing short walks before falling. Extending to 10,000 iterations.

**Rationale for H1-matched config:** H1 converges on rough terrain with much lighter penalties and no pushes. Learn to walk first with loose constraints, tighten penalties in fine-tuning. Smoothness weights and pushes to be restored post-convergence.

### Run 33 — overnight *(resuming Run 32 to 10,000 iters)*
**Starting from:** Run 32 (--resume), max_iterations=10,000.
**Config:** Same as Run 32. H1-matched rewards, no pushes, forward only (0.0, 1.0), [512,256,128] network, 4096 envs.
**Status:** Running overnight. Review in the morning.

**Post-convergence fine-tuning plan:**
1. Tighten smoothness: action_rate_l2 → -0.01, dof_acc_l2 → -2.5e-7
2. Re-enable dof_torques_l2 → -1e-5
3. Tighten orientation: flat_orientation_l2 → -5.0
4. Tighten hip roll: joint_deviation_hip_roll → -0.5 to -1.0
5. Re-enable push_robot: start ±0.5 m/s, then ±0.75 m/s
6. Add backward walking: lin_vel_x → (-1.0, 1.0)

---

## Phase 3.5 — Standing Smoothness Fine-Tune

### Run 14 — 2026-03-10_23-23-36 *(Phase 3.5)*
**Starting from:** Phase 3c checkpoint (2026-03-10_22-54-02)
**Changes:** feet_contact_at_rest: -0.5→-2.0, action_rate_l2: -0.005→-0.02, dof_acc_l2: -1.25e-7→-5e-7. Threshold: 0.1 m/s (unchanged).

**Recovery curve:** Sluggish — heavier penalties made optimization harder. Barely positive at iter ~450. Still climbing at iter 1500 (reward trend: 4.9→10.9→12.2→13.3).
**Metrics (1500 iter):** time_out=88.4%, root_height=10.4%, base_contact=0.0%, mean_reward=13.3, track_lin_vel_xy=0.681, feet_contact_at_rest=-0.011, action_rate_l2=-0.51
**Play review (zero command):** Still bouncing/drifting — not converged yet. Additional issue identified: threshold=0.1 m/s too permissive; robots commanded at 0.05 m/s were being penalized for shuffling when they should be allowed to. Threshold needs to be near-zero (0.02 m/s) so penalty only fires at true standstill.
**Assessment:** Smoothness penalties working (action rate dropped, feet contact improved) but weights too aggressive combined with wrong threshold. Not converged. Proceeding to 3.5b with threshold=0.02 m/s, continuing from this checkpoint.

### Run 15 — 2026-03-10_23-53-23 *(Phase 3.5b)*
**Starting from:** Phase 3.5 checkpoint (2026-03-10_23-23-36)
**Changes:** feet_contact_at_rest threshold: 0.1→0.02 m/s. All weights unchanged from 3.5.

**Recovery curve:** Slow but better than 3.5 — threshold change helped. Still climbing at iter 1500 (6.8→8.5→10.8→14.5→15.8).
**Metrics (1500 iter):** time_out=91.7%, root_height=6.9%, base_contact=0.0%, mean_reward=15.8, track_lin_vel_xy=0.672, action_rate_l2=-0.47
**Play review (zero command):** Still marching in place — more obviously than before 3.5. Root issue identified: feet_air_time (+2.0) and feet_contact_at_rest (-2.0) are equal and opposite at zero command. Policy finds equilibrium by marching just enough to balance the two rewards. This tension is structural — not fixable by weight tuning.

**Decision: abandon unified standing-in-walking approach. Revert weights and adopt two-policy architecture.**

**Architecture decision:** Deploy a walking policy and a separate standing policy, switching at runtime based on |v_cmd| < 0.05 m/s. Each policy optimized independently — no reward tension. Walking policy: full (-1.0, 1.0) range, stepping rewards intact. Standing policy: zero command only, feet_air_time removed, heavy unconditional foot-plant penalty.

**Config changes applied:**
- Reverted: action_rate_l2 -0.02→-0.01 (2x baseline, moderate — protects gearboxes without killing gait)
- Reverted: dof_acc_l2 -5e-7→-2.5e-7 (2x baseline)
- Reverted: feet_contact_at_rest weight -2.0→-0.5, threshold kept at 0.02 m/s
- Added: AtomFlatStandingEnvCfg + AtomFlatStandingEnvCfg_PLAY (not yet trained)
- Registered: Isaac-Standing-Flat-Atom-v0, Isaac-Standing-Flat-Atom-Play-v0

**Resuming walking curriculum from Phase 3c baseline (2026-03-10_22-54-02). Next: Phase 4 — push recovery.**

---

## Phase 4 — Push Recovery

### Run 16 — 2026-03-11_00-26-43 *(Phase 4a)*
**Starting from:** Phase 3c checkpoint (2026-03-10_22-54-02)
**Changes:**
- push_robot re-enabled: ±0.5 m/s impulse, interval 10–15s (upstream default)
- All reward weights reverted to Phase 3c baseline (action_rate_l2=-0.01, dof_acc_l2=-2.5e-7, feet_contact_at_rest=-0.5/0.02)
- 8192 envs, 1500 iter

**Recovery curve:** Same collapse-on-load pattern — negative through iter ~375 (Q1 avg = -1.0), recovered to 11.2 by Q2, 15.7 by Q3, 18.0 at final iter. Still trending upward at iter 1500 — not fully converged.
**Metrics (1500 iter, final 5-iter avg):** time_out=91.9%, root_height=7.4%, bad_orientation=1.0%, base_contact=0.0%, mean_reward=17.5, track_lin_vel_xy=0.741, feet_contact_at_rest=-0.002, fps=307k steps/s
**Assessment:** Push recovery learning — survival lower than Phase 3c (91.9% vs 96.9%) as expected from disturbances, but trending upward. Policy not yet converged. The ±0.5 m/s pushes are the upstream default — modest disturbances. A consolidation run or slightly more aggressive pushing is next.

**Next:** Phase 4b — bump push to ±0.75 m/s / 10–15s, load from this checkpoint WITHOUT --resume, allow convergence.
**Future (Phase 4c, post-convergence):** Consider ±1.0 m/s / 8–12s (Unitree H1-level aggression) once 4b has plateaued.

### Runs 17–19 — 2026-03-11_13-06-36 / 2026-03-11_13-07-27 / 2026-03-11_18-36-01 *(discarded)*
**Issue:** Runs 17–18 used `--resume`, causing optimizer state regression (17.5→12.5 reward). Run 19 was a clean retry (no `--resume`) but produced a nearly identical curve — fixed random seed means same checkpoint + same config = near-deterministic trajectory. Policy not converged at 1500 iters (mean_reward=10.4, time_out=83.7%). Play review showed no visible gait difference vs 4a — push_robot is disabled in play config so recovery behavior isn't observable in play mode.
**Decision:** Accept Phase 4a (2026-03-11_00-26-43) as Phase 4 final baseline. ±0.75 m/s push training not worth additional runs — upstream ±0.5 m/s pushes were already active throughout all prior phases. Moving to Phase 5 rough terrain.
**Lesson:** `--resume` + changed hyperparameters = bad. Always use `--load_run` only for fine-tune phases.

---

## Phase 5 — Rough Terrain (Retrained from Scratch)

### Context
Flat terrain converged in Run 28 (mean_reward=15.1, time_out=88.2%). Phase 5 trains from scratch with [512,256,128] network (incompatible with flat's [128,128,128]) and height scanner observations (247 obs dims). Reward weights matched to H1 reference for initial convergence.

### Runs 29–31 — Failed convergence attempts
**Issue:** Penalties too heavy relative to H1 reference, push_robot active, feet_air_time too low (0.25 in Run 29). Incrementally fixed: bumped feet_air_time to 2.0 (Run 30), matched all penalties to H1 (Run 31), but pushes still active.
**Lesson:** Match H1 reference rewards for initial convergence, tighten post-convergence. H1 uses orientation=-1.0, hip_roll=-0.2, torques=0, action_rate=-0.005, dof_acc=-1.25e-7, no push_robot.

### Run 32 — 2026-03-12_23-30-04
**Changes:** H1-matched rewards, push_robot disabled, forward only (0.0–1.0 m/s).
**Metrics (1500 iter):** time_out=18%, root_height=71%, bad_orientation=6%. First real progress — gradient positive.

### Run 33 — 2026-03-12_23-58-16 *(overnight, resumed from Run 32)*
**Changes:** Extended to 10,000 iters via --resume.
**Metrics (10,000 iter):** mean_reward=-4.14, time_out=11.2%, root_height=76.9%, bad_orientation=11.3%, terrain_levels=0.87.
**Assessment:** Did NOT converge. Reward flat at ~-4.0 for all 10,000 iterations. time_out briefly peaked ~18% around iter 500, then declined. Terrain levels ratcheted up from stumbling-forward promotions without actual gait improvement. Policy stuck in local minimum.

### Run 34 — 2026-03-13_09-18-03 *(killed at ~5600 iters)*
**Changes:** Knee stiffness 100→200 Nm/rad (match H1 hip_pitch/knee stiffness).
**Metrics (~5600 iter):** time_out peaked ~23.6% at iter 2830, declined to ~14%. root_height=75%, terrain_levels=0.86. Same pattern as Run 33.
**Play observations (rough terrain):**
1. **Sitting timeout exploit:** Some robots fall and sit upright propped on arms, reaching timeout without walking. The `undesired_contacts` reward is disabled (set to None) — no penalty for arm/torso ground contact.
2. **Downhill promotion exploit:** Robots spawning at top of pyramid stairs fall/slide down, traveling >4m from spawn. This triggers promotion to harder terrain despite no walking ability.
3. **Stair-kicking:** Robots reaching the bottom of stairs kick at the stair face without lifting feet high enough to step up. feet_air_time encourages stepping but doesn't reward foot *height* during swing.

**Root causes identified:**
- Missing `undesired_contacts` penalty → sitting exploit
- Terrain curriculum promotion by distance is exploitable on stairs (falling = traveling far)
- No foot clearance reward → policy doesn't learn to lift feet high enough for stairs
- Hip pitch limit of -30° severely restricts backward leg extension for stride (opened to -90° in new URDF)
- Knee min bend of 8.6° prevents full leg extension (opened to 0° in new URDF)

### URDF Changes (applied after Run 34)
- Hip pitch backward extension: -30° → -90° (match H1)
- Knee minimum bend: 8.6° → 0° (full extension allowed)
- New URDF: `Atom_Humanoid_V0.7_clean_limits.urdf` (via `set_joint_limits.py` + `joint_limits.yaml`)
- Joint comparison documented in `Docs/joint-limits-comparison.md`

### Run 35 — (starting now)
**Plan:** Retrain on flat terrain with new URDF + joint limits, [512,256,128] network, ~1500 iters. Establish a walking baseline before returning to rough terrain.
**Config:** Same as flat env (AtomFlatEnvCfg), 4096 envs, 10,000 max iterations.

### Suggested Reward Functions for Rough Terrain (post-convergence)

Three new rewards to address the observed failure modes:

1. **`undesired_contacts`** (re-enable, was disabled):
   - Penalizes contact forces on non-foot bodies (arms, torso, thighs, shins)
   - Directly fixes the sitting exploit — robot can't prop itself on arms without penalty
   - Available in IsaacLab: `isaaclab.envs.mdp.undesired_contacts(threshold, sensor_cfg)`
   - Suggested: weight=-1.0, threshold=1.0 N, body_names covering all non-foot links

2. **`foot_clearance_reward`** (new — from Spot config):
   - Rewards swing feet for reaching a target height off the ground
   - Directly fixes stair-kicking — policy learns to lift feet higher during swing
   - Available in IsaacLab Spot config: `foot_clearance_reward(asset_cfg, target_height, std, tanh_mult)`
   - Would need to be adapted or copied for biped (Spot version is quadruped-specific)
   - Suggested: target_height=0.08–0.15m, moderate weight

3. **`base_height_l2`** (deferred):
   - User uncertain about robustness on rough terrain — deferred for now.

### H1/G1 Reward Comparison (reference for rough terrain matching)

See `Docs/joint-limits-comparison.md` for joint limit comparison. Key reward differences to resolve before rough terrain:

| Reward | H1 Rough | G1 Rough | Atom (current rough cfg) | Action needed |
|--------|----------|----------|--------------------------|---------------|
| feet_air_time | 0.25 | 0.25 | 0.25 | MATCHED |
| undesired_contacts | None | None | -1.0 | Keep (addresses sitting exploit) |
| foot_clearance | — | — | None (rough) | Correct — no humanoid uses it for rough |
| position_range | (1.0, 1.0) | (1.0, 1.0) | (1.0, 1.0) | MATCHED |
| ang_vel_z | (-1.0, 1.0) | (-1.0, 1.0) | (0.0, 0.0) | Add post-convergence |
| lin_vel_z_l2 | None | 0.0 | None | MATCHED |
| All others | — | — | — | Already matched in Run 32 |

**Plan for rough terrain:** Train from scratch (not flat-to-rough transfer) with all H1-matched values. Flat training is a sanity check on the new URDF + rewards before committing to a long rough run.

---

### Run 35 — 2026-03-13_11-21-44 *(killed at ~2200 iters)*
**Config:** Flat terrain, new URDF (hip pitch -90°, knee 0°), [512,256,128] network, 4096 envs.
**Changes from previous flat config:** New URDF with wider joint limits only. No new reward terms (pre-reward-update).
**Status:** Killed to add `undesired_contacts` and `foot_clearance` rewards.

### Run 36 — (failed to start)
**Issue:** `foot_clearance_reward` not exported in `mdp/__init__.py`. Fixed import, then killed to also apply `feet_air_time` and `position_range` changes.

### Run 37 — (training now)
**Config:** Flat terrain from scratch, new URDF, [512,256,128] network, 4096 envs, 10,000 max iter.
**Changes from Run 35:**
- `feet_air_time` weight: 2.0 → **0.25** (match H1/G1)
- `position_range`: (0.0, 1.0) → **(1.0, 1.0)** (no joint randomization, match H1)
- Added `undesired_contacts`: weight=-1.0, threshold=1.0N, all non-foot bodies
- Added `foot_clearance`: weight=0.5, target_height=0.10m (flat only, disabled for rough)
- Knee stiffness: 100 → 200 Nm/rad (from Run 34)

**Full flat reward table:**

| Reward | Weight | Notes |
|--------|--------|-------|
| track_lin_vel_xy_exp | 1.0 | |
| track_ang_vel_z_exp | 1.0 | |
| feet_air_time | 0.25 | threshold=0.4, matched H1/G1 |
| feet_slide | -0.25 | |
| flat_orientation_l2 | -5.0 | flat uses heavier penalty |
| dof_torques_l2 | -1e-5 | |
| action_rate_l2 | -0.01 | flat default |
| dof_acc_l2 | -2.5e-7 | flat default |
| dof_pos_limits | -1.0 | ankles + knees |
| joint_deviation_arms | -0.2 | |
| joint_deviation_hip_roll | -0.2 | |
| termination_penalty | -200.0 | |
| feet_contact_at_rest | -0.5 | threshold=0.02 |
| undesired_contacts | -1.0 | NEW — all non-foot bodies |
| foot_clearance | 0.5 | NEW — target 0.10m, flat only |

### Run 38 — 2026-03-13_13-10-40
**Config:** Flat terrain from scratch, [512,256,128] network, 4096 envs, 1500 iter.
**Changes from Run 37:**
- `effort_limit_sim`: legs 60→**300 Nm**, ankles 60→**100 Nm**, arms 60→**300 Nm** (match H1/G1 training — prevents PD saturation artifacts; real 60 Nm limit enforced via dof_torques_l2 post-convergence)
- Flat PPO network: [128,128,128] → **[512,256,128]** (match rough, consistent architecture)

**Reward table:** Same as Run 37 (no reward changes).

**Purpose:** Quick sanity check with raised effort limits before rough terrain attempt.

**Metrics (1500 iter):**
- mean_reward: 23.18
- time_out: 93.79%
- track_lin_vel_xy: 0.81
- bad_orientation: 0.68%
- root_height: 5.64%

**Visual review:** Gait looks functional. Notable **left-right asymmetry**: left arm swings actively (shoulder_roll VelRMS=0.77, shoulder_pitch mean=-0.15 rad) while right arm barely moves (shoulder_roll VelRMS=0.09, mean=-0.001 rad). Causes robots to walk in slightly curved paths rather than straight lines.

**Hardware analysis:**
- PD saturation massively reduced vs Run 37 (60 Nm limits): ankles/shoulders/elbows at 0% saturation. Hips still clip at 300 Nm 38-61% (PD stiffness=200 generates large torques for small errors).
- **Elbow torque anomaly**: elbow_pitch_left RMS=180 Nm despite joint barely moving (pos=0.001 rad). Policy commands target below joint limit, pressing elbow against mechanical stop as a rigid strut. Always-negative torque (-267 to -41 Nm). Root cause: `action_rate_l2` penalizes rate not magnitude; `dof_torques_l2=-1e-5` too small to matter. Will resolve naturally when dof_torques_l2 is increased post-convergence.
- RMS torques far exceed 20 Nm rated continuous (expected at this stage — torque efficiency not yet a training objective).

**Assessment:** Flat terrain sanity check passed. PD saturation resolved. Ready for rough terrain attempt.

---

## Phase 5 — Rough Terrain (H1-Matched Config, From Scratch)

### Run 39 — (training now)
**Config:** Rough terrain FROM SCRATCH (no --resume), [512,256,128] network, 4096 envs, 10000 max iter.
**Task:** Isaac-Velocity-Rough-Atom-v0

**Key config (AtomRoughEnvCfg):**
- effort_limit_sim: 300/100/300 Nm (legs/ankles/arms)
- Terrain curriculum enabled (promotes at >4m from spawn, demotes at <50% expected)
- Height scanner: 17×11 grid, forward-only masking (rear 8 cols zeroed)
- feet_air_time=0.25 (match H1), position_range=(1.0,1.0), no joint randomization
- undesired_contacts=-1.0 (all non-foot bodies), foot_clearance=None (disabled for rough)
- feet_contact_at_rest=None (disabled for rough)
- flat_orientation=-1.0, dof_torques=0.0, action_rate=-0.005, dof_acc=-1.25e-7
- Commands: lin_vel_x=(0.0,1.0), lin_vel_y=0, ang_vel_z=0 (forward only)
- No push_robot, no base mass randomization
- Terminations: base_contact, bad_orientation(1.0 rad), root_height(0.5m)

| Reward Term | Weight |
|---|---|
| track_lin_vel_xy_exp | 1.0 |
| track_ang_vel_z_exp | 1.0 |
| feet_air_time | 0.25 |
| feet_slide | -0.25 |
| flat_orientation_l2 | -1.0 |
| joint_deviation_arms | -0.2 |
| joint_deviation_hip_roll | -0.2 |
| dof_pos_limits | -1.0 |
| dof_torques_l2 | 0.0 |
| action_rate_l2 | -0.005 |
| dof_acc_l2 | -1.25e-7 |
| undesired_contacts | -1.0 |
| termination_penalty | -200.0 |

**Purpose:** First rough terrain attempt with fully H1-matched config — raised effort limits, corrected joint limits, proper reward weights. Training from scratch with terrain curriculum (starts on easy terrain, promotes progressively).

**Metrics (85 iter, killed):**
- mean_reward: -3.9 (stuck, no improvement)
- time_out: 0% — every robot falls immediately
- root_height termination: 77%, bad_orientation: 25%
- mean_episode_length: ~20 steps (0.4s)

**Root cause:** `root_height_below_minimum` uses **world Z** (not height above terrain). The IsaacLab docstring explicitly says: *"This is currently only supported for flat terrains."* Robots spawning on low-elevation terrain patches are terminated despite standing upright. This caused 77% of all terminations.

Secondary issue: `undesired_contacts=-1.0` while H1 explicitly disables it (`None`). May hinder early exploration on terrain.

**Fix:** Disabled `root_height` for rough terrain (kept for flat). Disabled `undesired_contacts` for rough (match H1). Re-enabled both in flat env.

---

### Run 40 — (training now)
**Config:** Rough terrain FROM SCRATCH, 4096 envs, 10000 max iter.
**Changes from Run 39:**
- `root_height` termination: **disabled** for rough terrain (uses world Z — broken on non-flat terrain)
- `undesired_contacts`: **disabled** for rough terrain (match H1 — re-enable post-convergence)

**Terminations (rough):** base_contact + bad_orientation(1.0 rad) only (match H1)

| Reward Term | Weight |
|---|---|
| track_lin_vel_xy_exp | 1.0 |
| track_ang_vel_z_exp | 1.0 |
| feet_air_time | 0.25 |
| feet_slide | -0.25 |
| flat_orientation_l2 | -1.0 |
| joint_deviation_arms | -0.2 |
| joint_deviation_hip_roll | -0.2 |
| dof_pos_limits | -1.0 |
| dof_torques_l2 | 0.0 |
| action_rate_l2 | -0.005 |
| dof_acc_l2 | -1.25e-7 |
| termination_penalty | -200.0 |

**Purpose:** Re-attempt rough terrain with corrected terminations. Now matches H1 exactly on terminations and reward structure. The terrain curriculum should allow the robot to learn on the easiest terrain (5cm bumps) and promote.

**Metrics (10000 iter):**
- Best: mean_reward=2.23, time_out=76.3%, terrain_levels=0.73 at iter ~5250
- Final: mean_reward=-2.44, time_out=53.9%, terrain_levels=0.84 — collapsed as curriculum pushed to hardest terrain
- bad_orientation stable at ~6-7% throughout

**Visual review:** Most robots laying on ground propped up on arms — arm-propping exploit returned. Root cause: `undesired_contacts` was disabled (matched H1), but our robot's proportions make arm-propping effective where H1's don't.

**Next:** Re-enable `undesired_contacts`, add yaw turning, bump to 6144 envs, corrected URDF (shoulder_pitch_left [-80°,180°], right [-180°,80°]).

---

### Run 41 — (training now)
**Config:** Rough terrain FROM SCRATCH, 6144 envs, 10000 max iter.
**Changes from Run 40:**
- `undesired_contacts`: **re-enabled** at -1.0 (arm-propping exploit clearly present in play review)
- `ang_vel_z`: **(−1.0, 1.0)** — yaw turning enabled (match H1, helps steer on terrain)
- `num_envs`: 4096 → **6144** (more curriculum coverage)
- URDF: shoulder_pitch_left **[-80°, 180°]**, shoulder_pitch_right **[-180°, 80°]** (confirmed in Isaac Sim — previously swapped)
- Elbow default: 0.2 rad slight bend; shoulder_roll default: 0.15 rad slight splay (away from joint stops)
- ankle_pitch_right: mirrored to [-30°, 70°] (was [-70°, 30°])

| Reward Term | Weight |
|---|---|
| track_lin_vel_xy_exp | 1.0 |
| track_ang_vel_z_exp | 1.0 |
| feet_air_time | 0.25 |
| feet_slide | -0.25 |
| flat_orientation_l2 | -1.0 |
| joint_deviation_arms | -0.2 |
| joint_deviation_hip_roll | -0.2 |
| dof_pos_limits | -1.0 |
| dof_torques_l2 | 0.0 |
| action_rate_l2 | -0.005 |
| dof_acc_l2 | -1.25e-7 |
| undesired_contacts | -1.0 |
| termination_penalty | -200.0 |

**Terminations:** base_contact + bad_orientation(1.0 rad) only (no root_height)

**Metrics (9541 iter):**
- Best: mean_reward=0.15, time_out=59.3%, terrain_levels=3.5 at iter ~7295
- Final: mean_reward=-1.61, time_out=52.9%, bad_orientation=47% — never recovered
- bad_orientation stuck at 45-67% from step 500 onward — far worse than Run 40
- Likely cause: yaw turning command destabilized the policy from scratch; robot tries to turn and falls

**Visual review:** Stiff-legged gait, minimal knee bend.

**Next:** Revert feet_air_time to 2.0, run 5000 iterations to isolate effect.

---

### Run 42 — 2026-03-13_20-48-41
**Config:** Rough terrain FROM SCRATCH, 6144 envs, 5000 max iter.
**Changes from Run 41:**
- `feet_air_time`: 0.25 → **2.0** (restored to original — insufficient stepping incentive at 0.25)

| Reward Term | Weight |
|---|---|
| track_lin_vel_xy_exp | 1.0 |
| track_ang_vel_z_exp | 1.0 |
| feet_air_time | **2.0** |
| feet_slide | -0.25 |
| flat_orientation_l2 | -1.0 |
| joint_deviation_arms | -0.2 |
| joint_deviation_hip_roll | -0.2 |
| dof_pos_limits | -1.0 |
| dof_torques_l2 | 0.0 |
| action_rate_l2 | -0.005 |
| dof_acc_l2 | -1.25e-7 |
| undesired_contacts | -1.0 |
| termination_penalty | -200.0 |

**Metrics (5000 iter):**
- Best: mean_reward=-0.44 at iter 4416, time_out=52%, bad_ori=47%
- Same failure pattern as Run 41 — bad_orientation 69% at step 500, never recovered
- feet_air_time=2.0 made no difference vs Run 41 — yaw turning confirmed as culprit

---

### Suggestions for future runs

1. **Raise `feet_air_time` threshold** (0.4 → 0.6s) — demands more deliberate foot lift per stride, forces deeper knee bend. Already approved.
2. **Loosen smoothness penalties** — zero or reduce `action_rate_l2` and `dof_acc_l2` during initial rough convergence. On stairs the robot needs quick corrective responses that the smoothness penalty may be suppressing. Re-tighten post-convergence. Can be applied as a resume from best checkpoint.
3. **Incentivize knee/hip motion directly** — robot kicks ledges without lifting feet; options:
   - `base_height_l2`: penalize robot for crouching below target height — indirectly requires knee extension during stance
   - Custom `swing_foot_height` reward relative to terrain (modified foot_clearance using terrain height under each foot rather than world Z) — directly rewards foot clearance on stairs
   - Increase `feet_air_time` threshold further (0.6→0.8s) to demand even longer steps

---

### Run 43 — 2026-03-13_20-48-41 (play review only — Run 42 checkpoint)
**Note:** Play session was running for Run 42 (2026-03-13_20-48-41) when this session began. Run 43 config changes were staged but Run 43 was not executed. Killed play session.

---

### Config comparison analysis — 2026-03-14

Full comparison of H1/G1 vs Atom rough terrain reward configs conducted. See `Docs/rough-terrain-config-comparison.md`.

**Two critical mismatches identified:**

**1. `feet_air_time` weight: 3.0 (Atom) vs 0.25 (H1/G1) — 12× too high**
`feet_air_time_positive_biped` rewards single-stance *timing symmetry*, clamped at threshold (0.4s). Max reward per step = `0.4 × weight`. At weight 3.0, stepping reward ceiling is 1.2 — 3× larger than the velocity tracking signal (weight 1.0). The policy optimizes stepping timing far ahead of learning to walk. Weight of 0.25 gives a ceiling of 0.1, keeping it as a secondary shaping signal rather than the dominant objective.

**2. `undesired_contacts`: enabled at -1.0 (Atom) vs disabled (H1/G1)**
Both H1 and G1 explicitly set `undesired_contacts = None` for rough terrain. Shin, thigh, and hip contact is expected and sometimes necessary on stairs and slopes; penalizing it prevents learning contact-rich traversal strategies. Note: Run 40 showed arm-propping without this penalty, but Run 41's bad_orientation=47% failure was concurrent with adding yaw turning — the two changes were not isolated. H1/G1 both converge without this penalty on rough terrain, suggesting it hinders early exploration more than it helps.

**Changes applied (2026-03-14):**
- `AtomRewards.feet_air_time.weight`: 3.0 → **0.25** (match H1/G1 exactly)
- `AtomRoughEnvCfg`: `self.rewards.undesired_contacts = None` (match H1/G1)
- `AtomFlatEnvCfg`: explicitly restores `undesired_contacts` at -1.0 (flat training benefits from it; rough disables via inheritance)

---

### Run 44 — (starting after H1 reference observation)
**Config:** Rough terrain FROM SCRATCH, 6144 envs, 10000 max iter.
**Changes from Run 43 (staged):**
- `feet_air_time`: 3.0 → **0.25** (match H1/G1 — see analysis above)
- `undesired_contacts`: **None** (match H1/G1 — see analysis above)
- Knee default, elbow default, shoulder defaults, spawn height: kept from Run 43 staged config (deeper init pose)

**Full rough reward table:**

| Reward Term | Weight |
|---|---|
| track_lin_vel_xy_exp | 1.0 |
| track_ang_vel_z_exp | 1.0 |
| feet_air_time | **0.25** |
| feet_slide | -0.25 |
| flat_orientation_l2 | -1.0 |
| joint_deviation_arms | -0.2 |
| joint_deviation_hip_roll | -0.2 |
| dof_pos_limits | -1.0 |
| dof_torques_l2 | 0.0 |
| action_rate_l2 | -0.005 |
| dof_acc_l2 | -1.25e-7 |
| undesired_contacts | **None** |
| termination_penalty | -200.0 |

**Additional change — URDF hip centering:**
- `center_hip_origin.py` applied to `Atom_Humanoid_V0.7_clean_limits.urdf`
- OnShape exporter placed torso origin at right hip (y=0) instead of midpoint between hips (y=±0.075m)
- Correction: `base_to_torso` origin adjusted from `xyz="0 0 0"` to `xyz="0 -0.075 0"`
- `base_link` (height scanner, policy obs reference) now centred over stance midpoint
- Script computes correction from actual hip positions — robust to future URDF changes
- Added as step 3 in the post-processing pipeline (see CLAUDE.md)

**Rationale for rewards/commands:** Full H1/G1 reward alignment. Yaw disabled based on evidence from Runs 41/42 that it causes immediate bad_orientation with Atom's morphology (no hip yaw DoF). H1 reference run at 1000 iterations observed — walked clearly on rough terrain.

---

### Run 45 — (in progress)
**Task:** Isaac-Velocity-Flat-Atom-v0 (flat terrain, from scratch)
**Config:** 6144 envs, 1000 max iter, [512,256,128] network.

**Changes from Run 38 (last flat):**
- Restored flat-specific overrides that were missing from `AtomFlatEnvCfg.__post_init__` (rough env was disabling them and flat wasn't re-enabling):
  - `flat_orientation_l2`: -1.0 → **-5.0**
  - `dof_torques_l2`: 0.0 → **-1e-5**
  - `action_rate_l2`: -0.005 → **-0.01**
  - `dof_acc_l2`: -1.25e-7 → **-2.5e-7**
  - `feet_contact_at_rest`: None → **-0.5** (threshold=0.02)
  - `foot_clearance`: None → **0.5** (target=0.10m)

**Full flat reward table:**

| Reward | Weight | Notes |
|--------|--------|-------|
| track_lin_vel_xy_exp | 1.0 | |
| track_ang_vel_z_exp | 1.0 | |
| feet_air_time | 0.25 | threshold=0.4 |
| feet_slide | -0.25 | |
| flat_orientation_l2 | -5.0 | flat-specific (rough uses -1.0) |
| dof_torques_l2 | -1e-5 | flat-specific (rough uses 0.0) |
| action_rate_l2 | -0.01 | flat-specific (rough uses -0.005) |
| dof_acc_l2 | -2.5e-7 | flat-specific (rough uses -1.25e-7) |
| dof_pos_limits | -1.0 | ankles + knees |
| joint_deviation_arms | -0.2 | |
| joint_deviation_hip_roll | -0.2 | |
| termination_penalty | -200.0 | |
| feet_contact_at_rest | -0.5 | threshold=0.02, flat only |
| undesired_contacts | -1.0 | threshold=1.0, flat only |
| foot_clearance | 0.5 | target=0.10m, flat only |

---

### Run 46 — 2026-03-16_09-46-19 *(3681 iters, rough terrain)*
**Config:** From scratch, 6144 envs, same H1-matched config as Run 44 (no leg_contact, no undesired_contacts, hip-centred URDF, box feet).
**Metrics (3681 iters):** mean_reward=4.71, time_out=88.3%, bad_orientation=3.4%, terrain_levels=0.0.
**Assessment:** Terrain curriculum stuck at level 0 (easiest terrain) — high survival is misleading. Policy never promoted. Not useful as a baseline.

### Run 47 — 2026-03-16_21-22-41 *(10,000 iters, rough terrain — best so far)*
**Config:** Same as Run 46. No leg_contact termination, no undesired_contacts.
**Metrics (10,000 iters):**
| Point | mean_reward | time_out | bad_orientation | terrain_levels | track_vel_xy |
|-------|-------------|----------|-----------------|----------------|-------------|
| 0 | 0.15 | 1.2% | 0% | 3.5 | 0.006 |
| 2500 | -2.68 | 67.9% | 13.3% | 0.85 | 0.42 |
| 5000 | -3.06 | 66.9% | 11.8% | 1.08 | 0.46 |
| 7500 | -2.86 | 65.9% | 10.4% | 1.18 | 0.46 |
| 10000 | -1.22 | 68.9% | 9.3% | 1.22 | 0.48 |
**Assessment:** Best rough terrain run. 69% survival with curriculum progressing to level 1.2. Reward still negative (penalties outweigh tracking) but trending upward in final quarter. bad_orientation declining steadily (13%→9%). No leg_contact termination — policy can use shin scrapes on terrain. arm-propping exploit may still be present (no undesired_contacts penalty).

### Run 48 — 2026-03-17_21-02-34 *(10,000 iters, rough terrain — leg_contact added)*
**Config:** Same as Run 47 + leg_contact termination (femur+shin, 50N threshold).
**Metrics (10,000 iters):**
| Point | mean_reward | time_out | bad_orientation | leg_contact | terrain_levels | track_vel_xy |
|-------|-------------|----------|-----------------|-------------|----------------|-------------|
| 0 | -0.47 | 1.2% | 0% | 0.1% | 3.5 | 0.006 |
| 2500 | -4.89 | 32.7% | 4.9% | 62.7% | 1.05 | 0.29 |
| 5000 | -2.69 | 37.2% | 5.3% | 58.3% | 1.42 | 0.35 |
| 7500 | -3.89 | 39.9% | 5.4% | 55.0% | 1.58 | 0.32 |
| 10000 | -3.09 | 39.5% | 5.3% | 55.9% | 1.74 | 0.37 |
**Assessment:** leg_contact at 50N dominates terminations (56%), killing episodes where shins brush steps. Survival dropped from 69% (Run 47) to 40%. However, bad_orientation improved (9%→5%) and terrain_levels higher (1.2→1.7) — the policy avoids falling over but can't avoid shin contact. The 50N threshold may be too strict for rough terrain from-scratch training.

---

## Phase 5 — Rough Terrain (Foot Clearance Reward)

### Run 49 — 2026-03-29_11-20-22 *(training now)*
**Config:** Rough terrain FROM SCRATCH, 6144 envs, 10,000 max iter.
**Changes from Run 48:**
- **NEW: `foot_clearance` reward** — terrain-relative foot clearance using height scanner
  - Estimates ground height under each foot by averaging the 6 nearest height scanner ray-hit points (by XY distance) — mirrors hardware where foot occludes terrain beneath it
  - Gaussian reward peaks at target clearance height during swing phase (tanh-gated by horizontal foot velocity)
  - weight=0.5, target_height=0.15m (stair steps up to 0.23m), std=0.05, tanh_mult=2.0, num_nearest=6

All other config unchanged from Run 48 (leg_contact 50N, no undesired_contacts, no pushes, forward only).

| Reward Term | Weight | Notes |
|---|---|---|
| track_lin_vel_xy_exp | 1.0 | |
| track_ang_vel_z_exp | 1.0 | |
| feet_air_time | 0.25 | threshold=0.4 |
| feet_slide | -0.25 | |
| flat_orientation_l2 | -1.0 | match H1 |
| joint_deviation_arms | -0.2 | |
| joint_deviation_hip_roll | -0.2 | |
| dof_pos_limits | -1.0 | ankles + knees |
| dof_torques_l2 | 0.0 | disabled |
| action_rate_l2 | -0.005 | match H1 |
| dof_acc_l2 | -1.25e-7 | match H1 |
| **foot_clearance** | **0.5** | **NEW — terrain-relative, 15cm target, 6 nearest points** |
| termination_penalty | -200.0 | |

**Terminations:** base_contact + bad_orientation (1.0 rad) + leg_contact (femur+shin, 50N)

**Purpose:** Test whether terrain-relative foot clearance reward helps the policy learn to lift feet over obstacles, addressing the stair-kicking failure mode from Run 34. The reward uses the existing height scanner grid — no new sensors — and matches the hardware constraint where the foot occludes terrain directly beneath it.

**Outcome:** NaN crash at ~5170 iters. `action_rate_l2` exploded to -1.3e19 — policy weights diverged. The foot_clearance reward itself was stable (~0.25 throughout). Before the crash: time_out=43%, leg_contact=49%, terrain_levels=1.5 — similar trajectory to Run 48. Root cause: Atom's morphology requires large corrective actions on rough terrain; `action_rate_l2` amplifies occasional spikes into gradient explosions.

### Run 50 — 2026-03-29_15-39-09 *(training now)*
**Config:** Rough terrain FROM SCRATCH, 6144 envs, 10,000 max iter.
**Changes from Run 49:**
- `action_rate_l2`: -0.005 → **0.0** (disabled — NaN trigger in Run 49; re-enable post-convergence)
- `leg_contact` termination: **disabled** (match H1 — was killing 56% of episodes, preventing exploration)

H1 reference comparison (1000 iters): H1 reaches 97% survival and terrain level 5.8; Atom reached 30% survival and level 0.8 with the same reward config. `leg_contact` (no H1 equivalent) and `action_rate_l2` instability were the main differences.

| Reward Term | Weight | Notes |
|---|---|---|
| track_lin_vel_xy_exp | 1.0 | |
| track_ang_vel_z_exp | 1.0 | |
| feet_air_time | 0.25 | threshold=0.4 |
| feet_slide | -0.25 | |
| flat_orientation_l2 | -1.0 | match H1 |
| joint_deviation_arms | -0.2 | |
| joint_deviation_hip_roll | -0.2 | |
| dof_pos_limits | -1.0 | ankles + knees |
| dof_torques_l2 | 0.0 | disabled |
| action_rate_l2 | **0.0** | **disabled — NaN fix** |
| dof_acc_l2 | -1.25e-7 | match H1 |
| foot_clearance | 0.5 | terrain-relative, 15cm target, 6 nearest |
| termination_penalty | -200.0 | |

**Terminations:** base_contact + bad_orientation (1.0 rad) only (match H1)

**Metrics (10,000 iters):**
| Point | mean_reward | time_out | bad_orient | base_contact | terrain_levels | track_vel_xy | foot_clearance | ep_length |
|-------|-------------|----------|------------|-------------|----------------|-------------|----------------|-----------|
| 0 | 0.49 | 1.2% | 0% | 0% | 3.5 | 0.006 | 0.006 | 16 |
| 2500 | 17.7 | 69.3% | 12.1% | 18.7% | 0.71 | 0.42 | 0.36 | 790 |
| 5000 | 20.0 | 70.2% | 10.0% | 19.9% | 0.83 | 0.46 | 0.38 | 822 |
| 7500 | 21.7 | 69.8% | 10.9% | 19.3% | 0.79 | 0.46 | 0.39 | 857 |
| 10000 | 19.3 | 73.6% | 10.8% | 15.6% | 0.79 | 0.45 | 0.39 | 787 |

**Assessment:** Best rough terrain run by a large margin. First time reward went positive on rough terrain (+19.3 vs -1.2 previous best). No NaN crash — disabling `action_rate_l2` fixed the instability. 74% survival, still climbing slightly. Foot clearance reward stable at 0.39 — policy actively lifting feet. base_contact (16%) is now the main non-timeout termination (was leg_contact at 56% in Run 48).

**Remaining gaps vs H1 (1000 iters):** H1 reaches 97% survival vs Atom's 74%; H1 terrain level 5.8 vs Atom's 0.8. Terrain curriculum not promoting — policy converging on easy terrain but not advancing to stairs/slopes. base_contact (16%) suggests arm-propping or face-planting on harder terrain attempts.

**Play review:** Leg-sitting exploit confirmed. Robots balance on femurs and sit on the ground without walking — surviving episodes through inaction. The +19.3 mean reward was the exploit, not real locomotion. Without `leg_contact` termination, there is nothing preventing this strategy. Discard Run 50 as a baseline.

### Run 51 — 2026-03-29_20-02-26 *(training now)*
**Config:** Rough terrain FROM SCRATCH, 6144 envs, 10,000 max iter.
**Changes from Run 50:**
- `leg_contact` termination: **re-enabled at 200N** (was disabled in Run 50, was 50N in Run 48)
  - 200N catches sitting (body weight ~300N ÷ 2 femurs = ~150N each, plus dynamic forces → triggers 200N) while allowing brief shin scrapes on step edges (~10-30N)
  - Run 48's 50N threshold killed 56% of episodes (too strict); Run 50's disabled threshold allowed leg-sitting exploit

All other config same as Run 50 (action_rate=0.0, foot_clearance=0.5 terrain-relative, no pushes, forward only).

| Reward Term | Weight | Notes |
|---|---|---|
| track_lin_vel_xy_exp | 1.0 | |
| track_ang_vel_z_exp | 1.0 | |
| feet_air_time | 0.25 | threshold=0.4 |
| feet_slide | -0.25 | |
| flat_orientation_l2 | -1.0 | match H1 |
| joint_deviation_arms | -0.2 | |
| joint_deviation_hip_roll | -0.2 | |
| dof_pos_limits | -1.0 | ankles + knees |
| dof_torques_l2 | 0.0 | disabled |
| action_rate_l2 | 0.0 | disabled (NaN fix) |
| dof_acc_l2 | -1.25e-7 | match H1 |
| foot_clearance | 0.5 | terrain-relative, 15cm target, 6 nearest |
| termination_penalty | -200.0 | |

**Terminations:** base_contact + bad_orientation (1.0 rad) + leg_contact (femur+shin, **200N**)

**Play review (partial, ~2k iters):** Robot standing tall with straight knees, shuffling/sliding feet forward without lifting them. Leg-sitting exploit gone (200N threshold works), but replaced by straight-leg shuffling. Both feet stay planted — `feet_air_time` and `foot_clearance` never activate because the robot never enters swing phase. `feet_slide` at -0.25 too weak vs velocity tracking at 1.0.

### Run 52 — 2026-03-29_21-51-30 *(training now)*
**Config:** Rough terrain FROM SCRATCH, 6144 envs, 10,000 max iter.
**Changes from Run 51:**
- `feet_slide`: -0.25 → **-1.0** (make shuffling as expensive as velocity tracking — robot can't profit from sliding)
- `feet_air_time`: 0.25 → **1.0** (stronger stepping incentive once shuffling is penalized)

All other config same as Run 51 (leg_contact 200N, action_rate=0.0, foot_clearance=0.5, no pushes, forward only).

| Reward Term | Weight | Notes |
|---|---|---|
| track_lin_vel_xy_exp | 1.0 | |
| track_ang_vel_z_exp | 1.0 | |
| **feet_air_time** | **1.0** | **bumped from 0.25 — anti-shuffle** |
| **feet_slide** | **-1.0** | **bumped from -0.25 — anti-shuffle** |
| flat_orientation_l2 | -1.0 | match H1 |
| joint_deviation_arms | -0.2 | |
| joint_deviation_hip_roll | -0.2 | |
| dof_pos_limits | -1.0 | ankles + knees |
| dof_torques_l2 | 0.0 | disabled |
| action_rate_l2 | 0.0 | disabled (NaN fix) |
| dof_acc_l2 | -1.25e-7 | match H1 |
| foot_clearance | 0.5 | terrain-relative, 15cm target, 6 nearest |
| termination_penalty | -200.0 | |

**Terminations:** base_contact + bad_orientation (1.0 rad) + leg_contact (femur+shin, 200N)

**Play review (~2k iters):** Bang-bang control exploit discovered. Hardware analysis showed commanded positions at ±37,000 rad, 97-99% torque saturation. Policy exploiting disabled action_rate_l2 to use PD controllers as pure torque sources.

---

## Phase 5b — Return to Flat (New Reward Terms + Simplification)

Rough terrain Runs 49-52 revealed an exploit progression (leg-sitting → shuffling → bang-bang control) driven by too many weak penalties failing to prevent degenerate gaits. Strategy shift: validate new reward terms on flat terrain first, then transfer to rough.

### Code Cleanup (/simplify review, 2026-03-30)
- Extracted body name constants (`FOOT_BODIES`, `LEG_BODIES`, `UNDESIRED_CONTACT_BODIES`)
- Eliminated define→null→re-create antipattern in reward config inheritance
- Extracted `_swing_clearance_reward()` shared helper for flat/rough foot clearance
- Extracted `_apply_play_defaults()` for play config boilerplate
- Removed dead `ATOM_HUMANOID_MINIMAL_CFG`, fixed stale V0.6→V0.7 references

### Run 53 — 2026-03-30_09-33-51
**Config:** Flat terrain FROM SCRATCH, 6144 envs, 3000 max iter.
**New reward terms added:**
- `knee_singularity`: -0.5 weight, exponential barrier exp(-20·|angle|) near full extension
- `base_height`: -1.0 weight, terrain-relative L2 penalty, target 0.80m

All other rewards reverted to pre-Run-52 values (feet_air_time=0.25, feet_slide=-0.25).

| Reward Term | Weight | Notes |
|---|---|---|
| track_lin_vel_xy_exp | 1.0 | |
| track_ang_vel_z_exp | 1.0 | |
| feet_air_time | 0.25 | threshold=0.4 |
| feet_slide | -0.25 | |
| flat_orientation_l2 | -5.0 | |
| joint_deviation_arms | -0.2 | |
| joint_deviation_hip_roll | -0.2 | |
| dof_pos_limits | -1.0 | ankles + knees |
| dof_torques_l2 | -1e-5 | |
| action_rate_l2 | -0.01 | |
| dof_acc_l2 | -2.5e-7 | |
| undesired_contacts | -1.0 | |
| feet_contact_at_rest | -0.5 | threshold=0.02 |
| foot_clearance | 0.5 | absolute Z, 10cm target |
| knee_singularity | -0.5 | NEW — steepness=20, soft_limit=0.15 |
| base_height | -1.0 | NEW — target=0.80m |
| termination_penalty | -200.0 | |

**Metrics (3000 iter):** mean_reward=33.4, time_out=96.2%, track_vel=0.87. Best flat result yet.

**Play review:** Waddling side-to-side gait with hips and arms splaying out during steps. Very little knee bend. Hardware analysis: knee mean angle ~10° (barely bent), hip roll splaying ±12°, arms locked at ±16.5°. Knee singularity barrier working at boundary but not encouraging deeper bend. base_height penalty tiny (-0.012) — robot achieving height target without meaningful knee flexion.

### Run 54 — 2026-03-30_10-25-12 *(aborted)*
**Config:** Same as Run 53 but base_height weight **-5.0**, target **0.75m**.
**Outcome:** Rewards oscillating wildly. Killed early. Weight too aggressive — squared error at -5.0 creates huge gradients.

### Run 55 — 2026-03-30_10-35-52
**Config:** Same as Run 53 but base_height weight **-2.0**, target **0.75m**.
**Metrics (3000 iter):** mean_reward=32.0, time_out=96.0%, track_vel=0.86.
**Play review:** Gait visually identical to Run 53 — still waddling with straight legs. Stronger base_height penalty had negligible effect on knee bend.

**Key insight:** Comparing Atom flat rewards to H1 flat revealed we were **massively over-penalizing**. H1 uses feet_air_time=**1.0** (4x ours), action_rate=-0.005 (half ours), orientation=-1.0 (1/5 ours), and has **none** of our custom penalties (no undesired_contacts, feet_contact_at_rest, foot_clearance, knee_singularity, base_height, torque penalty). The heavy penalty load constrains exploration and prevents the policy from discovering dynamic gaits.

### Run 56 — 2026-03-30 *(training now)*
**Config:** Flat terrain FROM SCRATCH, 6144 envs, 3000 max iter.
**Strategy:** Strip flat rewards to match H1 exactly. Custom terms preserved in rough config but zeroed/removed for flat.

**Changes from Run 55:**
- `feet_air_time`: 0.25 → **1.0**, threshold 0.4 → **0.6** (match H1 flat)
- `flat_orientation_l2`: -5.0 → **-1.0** (match H1)
- `dof_torques_l2`: -1e-5 → **0.0** (match H1)
- `action_rate_l2`: -0.01 → **-0.005** (match H1)
- `dof_acc_l2`: -2.5e-7 → **-1.25e-7** (match H1)
- `knee_singularity`: -0.5 → **0.0** (disabled for flat)
- `base_height`: -2.0 → **0.0** (disabled for flat)
- `undesired_contacts`: **removed** (match H1)
- `feet_contact_at_rest`: **removed** (only used in standing policy)
- `foot_clearance`: **removed** (match H1)

| Reward Term | Weight | H1 Match? |
|---|---|---|
| track_lin_vel_xy_exp | 1.0 | ✓ |
| track_ang_vel_z_exp | 1.0 | ✓ |
| feet_air_time | **1.0** | ✓ (threshold=0.6) |
| feet_slide | -0.25 | ✓ |
| flat_orientation_l2 | **-1.0** | ✓ |
| ang_vel_xy_l2 | -0.05 | ✓ |
| joint_deviation_arms | -0.2 | ✓ |
| joint_deviation_hip_roll | -0.2 | ✓ |
| dof_pos_limits | -1.0 | ✓ (ankles only in H1, ankles+knees in Atom) |
| dof_torques_l2 | **0.0** | ✓ |
| action_rate_l2 | **-0.005** | ✓ |
| dof_acc_l2 | **-1.25e-7** | ✓ |
| knee_singularity | **0.0** | ✓ (disabled) |
| base_height | **0.0** | ✓ (disabled) |
| termination_penalty | -200.0 | ✓ |

**Terminations:** base_contact + bad_orientation (1.0 rad) + root_height (0.5m) + leg_contact (200N)
**Commands:** lin_vel_x=(0.0, 1.0), lin_vel_y=(0,0), ang_vel_z=(0,0)

**Metrics (3000 iter):** Training was excellent until iter ~1600 (mean_reward=32.3, time_out healthy), then **catastrophic gradient explosion** at iter ~1700 (mean_reward → -6 billion). Policy weights corrupted, never fully recovered (final mean_reward=-3.4, 0% survival, 92% bad_orientation deaths).

**Root cause:** `action_rate_l2` at -0.005. Same failure mode as Run 49 (-0.005 crashed at iter 5170). With H1-matched rewards (fewer regularization terms), the policy makes larger action swings → action_rate penalty spikes → gradient explosion. H1 tolerates -0.005 because hip yaw provides smoother gait transitions.

**Key insight:** H1-matched reward *structure* works (32.3 mean reward pre-crash), but Atom needs a safer action_rate weight. The missing hip yaw DoF means Atom's actions are inherently jerkier during stance-swing transitions.

### Run 57 — 2026-03-30_22-07-28 *(aborted at ~650 iter)*
**Config:** Flat terrain FROM SCRATCH, 6144 envs, 3000 max iter.
**Changes from Run 56:**
- **Spawn pose**: knee 29° → **70°** (deep squat), spawn height 0.9m → 0.68m
- **Ankle dorsiflexion**: 30° → **45°** (URDF rebuilt — previous 30° limit prevented deep squats entirely)
- `action_rate_l2`: -0.005 → **-0.001** (prevent Run 56 crash)
- `root_height` termination: 0.5m → **0.4m** (accommodate lower spawn)

**Critical finding:** Previous ankle limit of 30° was the hard constraint preventing deep knee bends. At 70° knee bend, the balanced-stance formula requires 36° ankle dorsiflexion — exceeding the old 30° limit. The robot *physically could not* squat deeply with flat feet. This explains why all previous policies converged to straight-leg gaits regardless of reward shaping.

**Play review (~650 iter):** Wide-legged sumo sauntering — robot squats then swings each leg wide to step, turning as it walks. The 70° squat is too deep; from this position, swinging the leg *around* the stance leg is easier than swinging it *forward*. Humans stand up before walking from a deep squat; PPO can't discover this two-phase behavior easily.

### Run 58 — 2026-03-31 *(training now)*
**Config:** Flat terrain FROM SCRATCH, 6144 envs, 3000 max iter.
**Changes from Run 57:**
- **Spawn pose**: knee 70° → **50°**, spawn height 0.68m → **0.75m** (moderate squat — enough to bias knee bend exploration without forcing sumo gait)

All other settings same as Run 57 (H1-matched rewards, feet_air_time=1.0, action_rate=-0.001, 45° ankle limits).

| Reward Term | Weight | H1 Match? |
|---|---|---|
| track_lin_vel_xy_exp | 1.0 | ✓ |
| track_ang_vel_z_exp | 1.0 | ✓ |
| feet_air_time | 1.0 | ✓ (threshold=0.6) |
| feet_slide | -0.25 | ✓ |
| flat_orientation_l2 | -1.0 | ✓ |
| ang_vel_xy_l2 | -0.05 | ✓ |
| joint_deviation_arms | -0.2 | ✓ |
| joint_deviation_hip_roll | -0.2 | ✓ |
| dof_pos_limits | -1.0 | ✓ |
| dof_torques_l2 | 0.0 | ✓ |
| action_rate_l2 | -0.001 | ✗ (H1 uses -0.005, crashes for Atom) |
| dof_acc_l2 | -1.25e-7 | ✓ |
| knee_singularity | 0.0 | ✓ (disabled) |
| base_height | 0.0 | ✓ (disabled) |
| termination_penalty | -200.0 | ✓ |

**Terminations:** base_contact + bad_orientation (1.0 rad) + root_height (**0.4m**) + leg_contact (200N)
**Commands:** lin_vel_x=(0.0, 1.0), lin_vel_y=(0,0), ang_vel_z=(0,0)
**Spawn:** knee=50° (0.873 rad), hip=24.4°, ankle=25.6°, height=0.75m

**Metrics (3000 iter):** mean_reward=30.1, time_out=87.7%, track_vel=0.84, bad_orientation=5.5%, root_height=5.4%, leg_contact=2.3%. No crash — action_rate at -0.001 is stable. Survival lower than Run 53 (87.7% vs 96.2%) — the moderate squat spawn is harder to balance from. Reward still climbing at iter 3000 (25→30 over last 600 iters). May benefit from more iterations.

**Status:** Awaiting visual review of gait quality. Key questions:
1. Does the 50° squat spawn produce visibly different gait than Run 53's straight-leg waddling?
2. Does the H1-matched reward set (no foot_clearance, no orientation push, no torque cost) allow better dynamic balance?
3. Is the lower survival a transient (still converging) or structural (gait fundamentally less stable)?

**Play command:**
```bash
cd atom_isaaclab && conda activate env_isaaclab && MPLBACKEND=Agg /home/atoms/IsaacLab/isaaclab.sh -p scripts/play.py --task Isaac-Velocity-Flat-Atom-Play-v0 --num_envs 50 --load_run 2026-03-30_22-49-12
```
