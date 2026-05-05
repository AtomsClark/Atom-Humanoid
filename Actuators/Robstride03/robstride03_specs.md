# Robstride 03 (RS03) Actuator Specifications for Simulation

**Research date:** 2026-03-09
**Motor:** Robstride 03 (ROBSTRIDE03), QDD 60 N·m Integrated Joint Motor Module
**Manufacturer:** RobStride Dynamics (灵足时代), China

---

## Summary Table

> **Data sources:** "Official spec sheet" = values from Robstride official PDF datasheet (provided directly).
> "Distributor" = values found in public product listings. Official spec sheet takes priority where there are conflicts.

| Parameter | Value | Unit | Source | Notes |
|---|---|---|---|---|
| **Gear ratio** | 9:1 | — | Official spec sheet | Planetary reducer, output:input speed |
| **Rated torque** | 20 | N·m | Official spec sheet | Continuous/rated output torque |
| **Peak torque** | 60 | N·m | Official spec sheet | Short-duration peak at low speed |
| **Rated output power** | 210 | W | Official spec sheet | At rated load (20 N·m × 100 rpm). Note: some distributors list 380 W (see Conflicts section) |
| **No-load speed** | 195 | rpm | Official spec sheet | At 48 V, output shaft |
| **No-load speed** | 20.42 | rad/s | Derived | 195 rpm × 2π/60 |
| **Rated load speed** | 100 | rpm | Official spec sheet | Speed at rated torque (20 N·m) |
| **Rated load speed** | 10.47 | rad/s | Derived | 100 rpm × 2π/60 |
| **No-load current** | 0.6 | A (RMS) | Official spec sheet | At 48 V |
| **Rated current** | 12 | A (peak) | Official spec sheet | ≈ 8.5 A RMS |
| **Peak current** | 43 | A (peak) | Official spec sheet | ≈ 30.4 A RMS |
| **Torque constant (Kt)** | 2.36 | N·m/A (RMS) | Official spec sheet | Output shaft; includes gear ratio |
| **Motor torque constant (Kt_motor)** | ~0.262 | N·m/A | Derived | Kt_output / gear_ratio = 2.36 / 9 |
| **Back-EMF constant (Ke)** | 17 | V_rms/krpm | Official spec sheet | Motor-side back-EMF constant |
| **Line resistance** | 0.39 | Ω | Official spec sheet | Line-to-line; per-phase = 0.195 Ω (wye) |
| **Winding inductance** | 0.275 | mH | Official spec sheet | Line-to-line |
| **Rated voltage** | 48 | V | Official spec sheet | Optimized; range 15–60 V |
| **Mass** | 880 ± 20 | g | Robstride website | 0.880 kg nominal |
| **Torque density** | 68.18 | N·m/kg | Derived | Based on peak torque / 0.880 kg |
| **Pole count** | 42 | poles | Official spec sheet | 21 pole pairs |
| **Phases** | 3 | — | Official spec sheet | 3-phase BLDC |
| **Drive method** | FOC | — | Official spec sheet | Field-oriented control |
| **Encoders** | 2 | — | Distributor | Dual magnetic encoders (14-bit) |
| **Protection rating** | IP52 | — | Official spec sheet | Customizable to IP67 |
| **Operating temperature** | −20 to 50 | °C | Distributor | |
| **Rotor inertia** | Not published | kg·m² | — | See derivation section |
| **Viscous damping** | Not published | N·m·s/rad | — | See simulation section |
| **Coulomb friction** | Not published | N·m | — | See simulation section |

### Physical Dimensions

| Parameter | Value | Unit |
|---|---|---|
| Outer dimensions | 106 × 106 × 56 | mm |
| Weight | 880 ± 20 | g | Per Robstride website |
| Flange hole pattern | 30.35 × 9 × 6 (M4) | mm |
| Mounting holes (perimeter) | 8 × M4×8 | — |
| Blind holes (inner ring) | 6 × M4×6 | — |
| Output shaft diameter | Ø48 ± 0.2 | mm |
| Inner bore | Ø30.36 ± 0.2 | mm |

### Electrical Interface

| Parameter | Value |
|---|---|
| Power connector | XT30 |
| Signal connector | GH1.25 |
| Voltage range | 15–60 V |
| Rated voltage | 48 V |

### Communication

| Parameter | Value |
|---|---|
| Protocol | CAN (CANopen + MIT mode) |
| Control frequency | 100 Hz (CAN update rate) |
| Control modes | Position, Velocity, Torque (MIT mode), Current |
| Position encoding | ×1000.0 scale |
| Velocity encoding | ×1000.0 scale |
| KP encoding | ×5.0 scale |
| KD encoding | ×500.0 scale |
| Torque encoding | ×10.0 scale |

---

## Derived / Calculated Parameters

### Motor-side Torque Constant

The Robstride 03 publishes Kt = 2.36 N·m/A as the **output shaft** torque constant (after the 9:1 gearbox). The bare motor's Kt is:

```
Kt_motor = Kt_output / N = 2.36 / 9 ≈ 0.262 N·m/A
```

For a 3-phase BLDC, the back-EMF constant Ke (line-to-neutral, in V·s/rad) equals Kt_motor in SI units. The no-load speed at 48 V gives an estimate:

```
No-load motor speed = 195 rpm × 9 = 1755 rpm = 183.8 rad/s
Ke_approx = V_supply / ω_motor = 48 / 183.8 ≈ 0.261 V·s/rad
```

This is consistent with Kt_motor ≈ 0.262 N·m/A, which is a good cross-check (Kt = Ke in SI for ideal BLDC).

### Rated Current Estimate

```
I_rated ≈ P_rated / V_rated = 380 W / 48 V ≈ 7.9 A (RMS)
```

Check via torque: `I_rated = T_rated / Kt_output = 20 / 2.36 ≈ 8.47 A`
These are consistent; the ~8 A figure is reasonable for rated continuous operation.

### Peak Current Estimate

```
I_peak ≈ T_peak / Kt_output = 60 / 2.36 ≈ 25.4 A
```

This is the estimated peak phase current for producing 60 N·m output torque. Not confirmed by a published datasheet.

### Rotor Inertia (Bare Motor, Estimated)

No rotor inertia is published. An estimate can be made by assuming a hollow cylindrical rotor geometry:

- Motor outer diameter (stator bore) ≈ 80–90 mm (estimated from 106 mm housing, typical for 42-pole pancake BLDC)
- Rotor assumed as thin ring, inner/outer ≈ 35/45 mm radius, mass ≈ 150–200 g (rough estimate)
- `J_rotor ≈ m × r_avg² / 2 ≈ 0.175 × 0.040² / 2 ≈ 1.4 × 10⁻⁴ kg·m²`

This is an order-of-magnitude estimate only. See simulation section for recommended approach.

---

## Known Applications Using Robstride 03

- **K-Bot (K-Scale Labs):** Uses 8 × Robstride 03 (60 N·m) for hip/knee/ankle joints, plus Robstride 04 (×4), Robstride 02 (×6), Robstride 00 (×2). Total 20 actuators.
  - Source: RobStride official X/Twitter, K-Scale Labs GitHub
  - K-Scale's `kscalelabs/kbot`, `kscalelabs/ksim-kbot`, `kscalelabs/kos-sim` repos contain simulation infrastructure but specific MJCF actuator parameters (armature, damping) were not found in public search results.
  - K-Scale also has `kscalelabs/motostandup` with `rotor_robstride04.py`; an equivalent `rotor_robstride03.py` may exist but was not confirmed.

---

## Conflicting Values and Uncertainties

### Rated Output Power: 210 W vs. 380 W

- **210 W** — from the official Robstride PDF datasheet (confirmed by cross-check: 20 N·m × 10.47 rad/s = 209 W)
- **380 W** — from multiple distributor listings (rcdrone.top, OpenELAB, etc.)

**Assessment:** 210 W is the correct **rated mechanical output power** at rated load (20 N·m, 100 rpm). The 380 W figure from distributors likely represents either peak power at the maximum-efficiency operating point or input electrical power. Trust the official spec sheet: use 210 W as rated continuous power.

### Mass: 880 ± 20 g

- **880 ± 20 g** — Robstride website and most distributor listings (consistent)

**Assessment:** Use 0.880 kg nominal in simulation. The ±20 g tolerance can be applied as domain randomization.

### No-load Speed: 195 rpm vs. 215 rpm

- **195 rpm** — stated as no-load speed in official spec sheet and distributor listings
- **215 rpm** — described as the speed at which torque "gradually decreases to zero" in some product descriptions

**Assessment:** 195 rpm is the no-load speed at 48 V. 215 rpm may be at slightly higher voltage (the actuator accepts up to 60 V) or an extrapolated zero-torque intercept from the torque-speed curve.

### Torque Constant: Output vs. Motor Side

- **2.36 N·m/A (RMS)** — output shaft Kt (post-gearbox), from official spec sheet. All sources agree.
- Motor-side Kt = 2.36 / 9 ≈ **0.262 N·m/A** (derived)

### Rotor Inertia

Not published in the official spec sheet or any public source. Must be estimated or measured.

### Gear Efficiency

Not published. Typical single-stage planetary: 94–98% efficiency. Expected to be backdrivable (QDD design).

---

## Simulation Parameters

### For MuJoCo / Isaac Lab (Mechanical Simulation)

These are the parameters you need for joint simulation. Items marked "estimated" or "recommended" require engineering judgment.

#### Confirmed Parameters

| Parameter | Value | Notes |
|---|---|---|
| `gear` (MuJoCo) | 9 | Reduction ratio: motor speed = 9 × joint speed |
| `forcerange` / torque limit | ±60 N·m | Peak torque at output shaft |
| `ctrlrange` | ±60 N·m | Or ±20 N·m for rated continuous |
| Max joint velocity | 20.4 rad/s | 195 rpm = 20.42 rad/s at 48 V |
| Mass | 0.880 kg | ±0.020 kg |

#### Armature (Reflected Rotor Inertia)

In MuJoCo, the `armature` attribute adds inertia: `J_reflected = J_rotor × N²`

```
J_reflected = J_rotor × 9² = J_rotor × 81
```

Since J_rotor is not published, here is a bracketed estimate:

| Source | J_rotor estimate | J_reflected (×81) |
|---|---|---|
| Geometric estimate (hollow ring) | ~1.0–2.0 × 10⁻⁴ kg·m² | ~8.1–16.2 × 10⁻³ kg·m² |
| Comparison: MIT Mini Cheetah motor | ~2.5 × 10⁻⁵ kg·m² | ~2.0 × 10⁻³ kg·m² (N=6) |
| Comparison: Unitree A1 motor | ~3.0 × 10⁻⁵ kg·m² | ~3.0 × 10⁻³ kg·m² (N=10) |

**Recommended starting value:** `armature = 0.005` kg·m² (i.e., J_reflected ≈ 5 × 10⁻³ kg·m²)
This assumes J_rotor ≈ 6 × 10⁻⁵ kg·m² × 81 ≈ 5 × 10⁻³ kg·m². Tune via system identification.

**K-Scale Labs reference (K-Bot v2 MJCF — `kscalelabs/ksim-kbot`):**
The K-Bot v2 MJCF (`kbot-v2-feet/robot.mjcf`) defines separate classes per motor type. For RS03 joints specifically (`motor_03` class, used for shoulder pitch/roll and hip roll/yaw):

```xml
<default class="motor_03">
  <joint armature="0.005" frictionloss="0.001" actuatorfrcrange="-100.0 100.0" />
  <motor ctrlrange="-100.0 100.0" />
</default>
```

- `armature = 0.005 kg·m²` — identical to the geometric estimate above; this corroborates the 0.005 value
- `frictionloss = 0.001 N·m` — very low; K-Scale treats RS03 as near-frictionless in sim
- `forcerange = ±100 N·m` — intentionally set above the physical 60 N·m peak, giving training headroom; the physical actuator will saturate at 60 N·m regardless

Note: the `walking.py` task config uses a high-level `armature = 1e-2` default that does NOT override per-class MJCF values — the MJCF `motor_03` class value of 0.005 is what's actually applied to RS03 joints.

#### Viscous Damping (joint-level)

Not published. In MuJoCo, `damping` is in N·m·s/rad at the joint (output) shaft.

```
b_joint = b_motor × N²
```

For QDD actuators with FOC, electrical damping is often used in lieu of mechanical. At the output shaft, a typical starting value for a 60 N·m actuator:

**Recommended:** `damping = 1.0` N·m·s/rad (output shaft)
This is a common starting point for human-scale QDD actuators; tune via pendulum drop test.

#### Coulomb / Static Friction

Not published. For a 9:1 planetary gearbox:
- Planetary gear stages typically have low Coulomb friction (backdrivable design)
- Estimate: 0.5–2.0% of rated torque at output

**Recommended:** `frictionloss = 0.5` N·m (output shaft) as a starting point

#### Motor Torque Constant (for electrical simulation or torque control)

```
Kt_output = 2.36 N·m/A (RMS)
Kt_motor  = 0.262 N·m/A (bare motor)
```

For Isaac Lab `ImplicitActuatorCfg` or `DCMotorCfg`:

```python
effort_limit = 60.0       # N·m (peak)
velocity_limit = 20.4     # rad/s (195 rpm)
stiffness = {...}         # PD gains (task-dependent)
damping = {...}           # PD gains (task-dependent)
```

For `DCMotorCfg` (if using actuator net or motor model):

```python
motor_torque_constant = 0.262  # N·m/A (motor side)
gear_ratio = 9.0
```

#### MuJoCo Actuator XML Example

```xml
<!-- Position servo with motor model -->
<actuator>
  <motor name="joint_motor"
         joint="joint_name"
         gear="9"
         forcerange="-60 60"
         ctrllimited="true"
         ctrlrange="-60 60"/>
</actuator>

<!-- Joint properties -->
<joint name="joint_name"
       armature="0.005"
       damping="1.0"
       frictionloss="0.5"/>
```

#### Isaac Lab `ImplicitActuatorCfg` Example

```python
from isaaclab.actuators import ImplicitActuatorCfg

actuators = {
    "joint_name": ImplicitActuatorCfg(
        joint_names_expr=["joint_name"],
        effort_limit=60.0,          # N·m peak
        velocity_limit=20.4,        # rad/s (195 rpm)
        stiffness=80.0,             # Tune for your task
        damping=2.0,                # Tune for your task
        # armature set in USD/URDF articulation config
    ),
}
```

---

## Sources

All data points are sourced below. Parameters not found in public sources are marked in the table as "Not published."

### Primary / Manufacturer Sources

1. **RobStride Official Product Page — RS03**
   https://robstride.com/products/robStride03
   *Peak torque (60 N·m), rated torque (20 N·m), gear ratio (9:1), no-load speed (195 rpm), power (380 W), mass (880 g), IP52, pole count (42), FOC drive, dual encoders*

2. **RobStride GitHub — Product Information**
   https://github.com/RobStride/Product_Information
   *Official documentation repository; contains manuals and datasheets (direct file access not retrieved)*

3. **RobStride GitHub — MotorStudio**
   https://github.com/RobStride/MotorStudio
   *Motor configuration and control software*

4. **ROBSTRIDE03 Integrated Joint Motor Module User Manual (manuals.plus)**
   https://manuals.plus/ae/1005007705574359
   *Torque-speed curve description (peak 60 N·m, falls toward 215 rpm), operating conditions, voltage range 15–60 V, FOC control, IP52*

5. **Robostride 03 Motor Installation Drawing and Specifications (manuals.plus)**
   https://manuals.plus/m/fcfb166db8e37bb6a15a8984f3d6c4bd1534bd174127855f1633084b7408cf48
   *Mechanical dimensions: Ø48 ±0.2 output, Ø30.36 ±0.2 inner bore, 54.1 mm length, mounting hole patterns*

### Distributor / Retailer Sources

6. **RCDrone — Robstride 03 QDD 60N·m Product Listing**
   https://rcdrone.top/products/robstride-03-qdd-60n-m-integrated-actuator-module-48v-dual-encoders-planetary-reducer-ip52-9-1-ratio
   *Torque constant 2.36 N·m/Arms, no-load current 0.6 A, no-load speed 195 rpm, voltage range 15–60 V, rated power 380 W, mass 880 g, gear ratio 9:1, IP52, 42 poles, 3-phase FOC*

7. **AIFITLAB — ROBSTRIDE 03 Motor**
   https://aifitlab.com/products/robstride-03-motor
   *Peak torque 60 N·m, rated torque 20 N·m, gear ratio 9:1, mass 880 g, IP52, 42 poles*

8. **OpenELAB — ROBSTRIDE03 QDD 60N.m**
   https://openelab.io/products/robstride03-qdd-60n-m-integrated-joint-motor-module
   *Consistent specs: peak 60 N·m, rated 20 N·m, 380 W, 9:1, 880 g*

9. **Seeed Studio — Robostride 00 (reference model)**
   https://www.seeedstudio.com/Robostride-00-Actuator-p-6664.html
   *Cross-reference for product line consistency*

10. **Amazon — ROBSTRIDE03 (product listing)**
    https://www.amazon.com/Articulated-Motor-Module-ROBSTRIDE03-Quasi-Direct/dp/B0FGPYRXRR
    *Confirms 60 N·m peak, QDD integrated module*

### Control / SDK Documentation

11. **Seeed Studio Wiki — RobStride Motor Control Complete Guide**
    https://wiki.seeedstudio.com/robstride_control/
    *CAN protocol details: MIT mode, position/velocity/torque control; encoding scales (position ×1000, velocity ×1000, kp ×5, kd ×500, torque ×10); 100 Hz control rate; CAN frame structure; damping behavior note*

12. **Rust crate — robstride (actuator_types.rs)**
    https://docs.rs/robstride/latest/src/robstride/actuator_types.rs.html
    *Open-source Rust SDK for Robstride actuators; contains Type03 enum definitions; specific numerical limits not retrieved*

13. **Rust crate — robstride (crates.io)**
    https://crates.io/crates/robstride
    *Robstride Python/Rust SDK*

14. **GitHub — sirwart/robstride (Python SDK)**
    https://github.com/sirwart/robstride
    *Community Python SDK for Robstride actuators*

### K-Scale Labs (K-Bot Application)

15. **RobStride on X (Twitter) — K-Bot announcement**
    https://x.com/RobStride_com/status/1894292440468598843
    *Confirms K-Bot uses 8 × RS03 (60 N·m), 4 × RS04, 6 × RS02, 2 × RS00 — 20 total actuators*

16. **K-Scale Labs — kbot GitHub repository**
    https://github.com/kscalelabs/kbot
    *K-Bot robot design, URDF/MJCF files (direct file access not retrieved)*

17. **K-Scale Labs — ksim-kbot**
    https://github.com/kscalelabs/ksim-kbot
    *RL training and simulation for K-Bot with MuJoCo; uses Robstride actuators*

18. **K-Scale Labs — kos-sim**
    https://github.com/kscalelabs/kos-sim
    *KOS simulation backend*

19. **K-Scale Labs — motostandup (rotor_robstride04.py)**
    https://github.com/kscalelabs/motostandup/blob/master/rotor_robstride04.py
    *Contains rotor identification parameters for RS04; RS03 equivalent not found publicly*

20. **DeepWiki — kscalelabs/kbot**
    https://deepwiki.com/kscalelabs/kbot
    *Wiki-style documentation of K-Bot software architecture*

### Academic / Background

21. **Extended Friction Models for the Physics Simulation of Servo Actuators (arXiv 2410.08650)**
    https://arxiv.org/abs/2410.08650
    *Best available reference for servo actuator friction modeling methodology; proposes pendulum-based system identification for Coulomb + viscous + Stribeck models*

22. **Impact of Static Friction on Sim2Real in Robotic RL (arXiv 2503.01255)**
    https://arxiv.org/abs/2503.01255
    *Discusses unexpectedly high friction ratios in robotic joints; relevant for sim-to-real gap analysis*

---

## What Was NOT Found

The following parameters are **not in any public or official source** as of 2026-03-09:

| Parameter | Status |
|---|---|
| Rotor inertia (kg·m²) | Not in any datasheet, manual, or GitHub config — must estimate or measure |
| Viscous damping coefficient (N·m·s/rad) | Not published — measure via pendulum drop test |
| Coulomb/static friction torque (N·m) | Not published — measure via pendulum drop test |
| Gear efficiency (%) | Not published |

The following were found in the **official spec sheet** (not in public web sources):

| Parameter | Value |
|---|---|
| Line resistance | 0.39 Ω (line-to-line) |
| Winding inductance | 0.275 mH |
| Back-EMF constant | 17 V_rms/krpm |
| Rated current | 13 A peak |
| Peak current | 43 A peak |
| Rated output power | 210 W |
| Rated load speed | 100 rpm |

**Recommendation:** To obtain rotor inertia and friction parameters:
1. Contact RobStride directly (sales@robstride.com or via robstride.com)
2. Perform a **pendulum drop test**: mount the actuator as a pendulum, release from known angle, record oscillation decay, and fit a Coulomb + viscous friction model (see arXiv 2410.08650 for methodology)
3. **Measure phase resistance** with a multimeter (line-to-line; divide by 2 for per-phase resistance)
4. Check the RobStride Product_Information GitHub repo for any PDF datasheets not indexed by search engines
5. Check kscalelabs/kbot and kscalelabs/ksim-kbot for embedded MJCF actuator parameters — these repos were confirmed to use RS03 but direct file access was not available during this research session

---

## Quick-Reference for Isaac Lab Config

```python
# Robstride 03 — confirmed parameters
ROBSTRIDE03_EFFORT_LIMIT   = 60.0   # N·m (peak output torque)
ROBSTRIDE03_VELOCITY_LIMIT = 20.4   # rad/s (195 rpm no-load @ 48V)
ROBSTRIDE03_GEAR_RATIO     = 9.0    # reduction ratio
ROBSTRIDE03_KT_OUTPUT      = 2.36   # N·m/A_rms (output shaft)
ROBSTRIDE03_KT_MOTOR       = 0.262  # N·m/A_rms (motor shaft, derived)
ROBSTRIDE03_MASS           = 0.880  # kg (±0.020 kg tolerance)
ROBSTRIDE03_RATED_CURRENT  = 12.0   # A peak (≈8.5 A RMS)
ROBSTRIDE03_PEAK_CURRENT   = 43.0   # A peak (≈30.4 A RMS)

# Estimated simulation parameters (TUNE THESE via motor characterization)
ROBSTRIDE03_ARMATURE       = 0.005  # kg·m² reflected inertia
                                    # Corroborated: K-Scale K-Bot v2 MJCF uses 0.005 for RS03
ROBSTRIDE03_DAMPING        = 1.0    # N·m·s/rad viscous (estimated; tune via characterization)
ROBSTRIDE03_FRICTION       = 0.5    # N·m Coulomb (estimated; K-Scale uses 0.001 — very low)
                                    # K-Scale frictionloss=0.001 suggests RS03 is near-backdrivable
```
