# Hardware Notes — Atom Humanoid V1

Design considerations and open questions for sensor and actuator selection.

---

## Depth / Perception

### Height Scanner Sim Spec
The simulated height scanner (used in RL training) is a **17×11 raycast grid**:
- Resolution: 0.1m (10cm per point)
- Coverage: 1.6m × 1.0m centered on `base_link` (±0.8m fore/aft, ±0.5m lateral)
- 187 observation values fed directly into the policy network
- Top-down raycasts — equivalent to a perfect local elevation map

### RealSense D435i (primary candidate)
- Stereo depth + RGB + IMU
- FOV: ~87° × 58° horizontal/vertical
- Best depth accuracy: 0.5–3m range
- **Problem:** Forward-facing only — cannot see the rear ±0.8m of the height scan grid
- Close-range floor accuracy at 0.3–0.8m (hip-mount height) is marginal

### RealSense D405 (close-range variant)
- Optimised for 0.07–0.5m — better suited for floor-level scanning from a hip mount
- Narrower FOV than D435i
- Still forward-facing only

### Livox Mid-360 (LiDAR alternative)
- 360° horizontal FOV, ~59° vertical
- Full coverage of the height scan grid in all directions
- Maps cleanly to the simulated raycast pattern
- More expensive; adds weight
- No RGB — perception tasks need a separate camera anyway

### Recommendation (open)
A **hip-mounted D405 (front) + D405 (rear)** pair covers the full grid cheaply.
A **Livox Mid-360** is the cleanest single-sensor solution if budget/weight allows.
Decision pending: finalise robot CoM and hip geometry before committing to mount position.

---

## Handling the Rear Camera Gap in Training

Three viable approaches — not mutually exclusive:

### Option A: Observation dropout (easiest, recommended for V1)
Randomly zero out the rear portion of the height scan during training (e.g., the rear 8×11 = 88 points). The policy learns to walk with partial height information. At deployment, rear points are simply zeroed — no mismatch.
- **Pros:** No extra hardware, no perception pipeline, policy is robust to missing data
- **Cons:** Slightly reduced rough terrain performance vs full coverage

### Option B: Elevation mapping with memory
Maintain a persistent local elevation map (e.g., ETH's `elevation_mapping` ROS package). As the robot walks forward, terrain that was ahead is now behind — and already in the map buffer. New sensor data only needed for the leading edge.
- **Pros:** Full grid coverage with one forward camera; standard industry approach (ANYmal, etc.)
- **Cons:** Requires real-time mapping pipeline; adds latency and compute; map drift on long runs

### Option C: Two cameras
Mount one D405 forward, one rear. Full grid coverage, no software complexity.
- **Pros:** Direct sim-to-real match, simple pipeline
- **Cons:** Extra weight, wiring, cost, and USB bandwidth

### Current training approach
**Forward-only masking** is already implemented in training: rear 8 columns of the 17×11 height scan grid are zeroed (see `height_scan_forward_only` in `mdp/observations.py`). The policy trains with only the forward 9 columns of real data.

**Deployment pipeline (Extreme Parkour approach):** Train a supervised CNN to predict the 187-dim height scan from D435i depth images. The CNN is trained on paired (depth image, ray-cast height scan) data collected in sim. At deployment: D435i depth → CNN → 187-dim height scan → policy. Runs on Orin Nano at 10–30Hz (policy MLP runs at 50Hz, height scan is interpolated between updates).

A separate **velocity estimator** (small MLP/RNN) maps proprioceptive history → base linear velocity, since ground-truth velocity is unavailable on hardware.

---

## IMU

Integrated in RealSense D435i/D405 (BMI055). Adequate for orientation and angular velocity.
Consider a dedicated high-rate IMU (e.g. VectorNav VN-100) if IMU noise proves to be a sim-to-real gap.

---

## Actuators

All joints: RobStride RS03 (60 Nm peak, 20 Nm rated continuous, gear ratio 9:1).
Reflected rotor inertia: `armature = 0.005 kg·m²` (corroborated by K-Scale K-Bot v2 MJCF).
Full specs: `Actuators/` directory.

---

## Bearings

RS03 actuators have internal bearings, but high-load joints (hips, knees, shoulders) may need external bearings to handle radial/axial loads that the motor bearings aren't designed for — especially side loads from walking dynamics.

**Candidates (crossed roller bearings — handle combined radial + axial + moment loads in compact form):**
- IKO CRBT505AC1 — compact crossed roller, ~50mm OD
- THK RU85-UUCC0 — similar class
- Ideally find cheaper alternatives with equivalent load ratings

**Reference:** K-Scale K-Bot uses SKF 61805 deep groove ball bearings in hips and knees only — no bearings in shoulders or elbows. This is a reasonable approach: legs see much higher loads than arms during locomotion. Deep groove bearings are cheaper than crossed rollers and may be sufficient if moment loads are manageable.

**Decision pending:** Need torque and load analysis from simulation first. Record per-joint forces across terrain types (flat, stairs, slopes) to determine which joints see loads exceeding RS03 internal bearing capacity. See `TODO.md` for analysis tasks.
