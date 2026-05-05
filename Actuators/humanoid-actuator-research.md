# Humanoid Robot Actuator Research

## Robot Specs

- **Height:** 5'6" (168 cm)
- **DoF:** 16 total (4 per limb)

### Degrees of Freedom

| Limb | Joints |
|---|---|
| Each leg (×2) | Hip flex, Hip abduction, Knee flex, Ankle flex |
| Each arm (×2) | Shoulder flex, Shoulder abduction, Elbow flex, Wrist |

---

## Torque Requirements

Calculated for 20 kg robot + 3 kg payload = 23 kg effective.

| Joint | Count | Nominal | Design For |
|---|---|---|---|
| Ankle flex | ×2 | ~39 Nm | **55 Nm** |
| Knee flex | ×2 | ~35 Nm | **55 Nm** |
| Hip abduction | ×2 | ~32 Nm | **45 Nm** |
| Hip flex | ×2 | ~23 Nm | **35 Nm** |
| Shoulder flex | ×2 | ~24 Nm | **35 Nm** |
| Shoulder abduction | ×2 | ~24 Nm | **35 Nm** |
| Elbow flex | ×2 | ~13 Nm | **20 Nm** |
| Wrist | ×2 | ~5 Nm | **10 Nm** |

### Two Actuator Tiers

| Tier | Peak Target | Joints | Count |
|---|---|---|---|
| Large | ~60 Nm | Ankle, knee, hip abduction | 6 |
| Small | ~40 Nm | Hip flex, shoulder (×2), elbow, wrist | 10 |

---

## Actuator Comparison

| Actuator | Peak (Nm) | Cont. (Nm) | Weight (g) | Size (mm) | Price (USD) | Type |
|---|---|---|---|---|---|---|
| T-Motor AK70-10 | 24.8 | 8.3 | 521 | Ø89 × 50 | ~$399 | QDD 10:1 |
| T-Motor AK80-9 | 22 | 9 | 490 | Ø98 × 38.5 | ~$480 | QDD 9:1 |
| T-Motor AK80-6 | 12 | 6 | 485 | Ø98 × 38.5 | ~$470 | QDD 6:1 |
| myActuator RMD-X8 Pro | 25 | 13 | 710 | Ø98 × 49 | ~$460 | Servo 9:1 |
| myActuator RMD-X6 V3 | 8 | 4.5 | 490 | ~Ø86 × 45* | ~$250 | Servo 8:1 |
| Dynamixel PH54-200 | 73 | 44.7 | 855 | 54×126×54 | $3,542 | Servo 501:1 |
| Dynamixel PH54-100 | 67 | 25.3 | 740 | 54×108×54 | $3,289 | Servo 501:1 |
| Robstride 01 | 17 | — | — | — | ~$140 | QDD |
| Robstride 02 | 17 | 6 | 405 | 78.5×78.5×45.5 | ~$160 | QDD 7.75:1 |
| Robstride 03 | 60 | 20 | 880 | 106×106×56 | ~$250 | QDD 9:1 |
| Robstride 04 | 120 | 40 | 1,420 | 120×120×56 | ~$280 | QDD 9:1 |
| Damiao DM4310 | 7 | 3 | ~300 | Ø57 × 46 | ~$120 | QDD 10:1 |
| Damiao DM8009 | 40 | 20 | ~900* | —* | ~$385 | QDD |
| Damiao DM10010L | 150 | 40 | 1,485 | Ø112 × 62 | ~$360 | QDD 10:1 |

\* dimensions/weight uncertain — verify against datasheet

---

## Build Options & Cost Analysis

### Option A: RS03 (×6) + RS02 (×10) — Mixed

Use Robstride 03 for high-load joints, Robstride 02 for the rest.

**Actuator weight:** (6 × 880g) + (10 × 405g) = 9,330g = 9.3 kg

| Component | Qty | Unit | Subtotal |
|---|---|---|---|
| Robstride 03 (ankle, knee, hip abd) | 6 | $250 | $1,500 |
| Robstride 02 (hip flex, shoulders, elbow, wrist) | 10 | $160 | $1,600 |
| Carbon fiber frame | 1 | $1,500 | $1,500 |
| 48V 10Ah Li-ion battery (~480 Wh) | 1 | $300 | $300 |
| BMS + power distribution | 1 | $150 | $150 |
| Jetson Orin NX 16GB + carrier board | 1 | $700 | $700 |
| Intel RealSense D435i (×2) | 2 | $200 | $400 |
| IMU | 1 | $150 | $150 |
| Wiring, connectors, fasteners | — | — | $400 |
| 3D printed brackets, misc | — | — | $200 |
| **Total** | | | **$6,900** |

**Robot weight breakdown:**

| Component | Weight |
|---|---|
| Actuators | 9.3 kg |
| Carbon fiber frame | 2.0 kg |
| Battery | 2.0 kg |
| Compute + sensors | 0.8 kg |
| Wiring, misc | 0.7 kg |
| **Total** | **~15 kg** |

**Effective payload: ~2 kg**
- Shoulder is the bottleneck — RS02 peaks at 17 Nm, limiting arm payload to ~2 kg
- Hip flex is marginally undersized (17 Nm vs ~20 Nm needed) — stair climbing possible but gait must be slower and more deliberate

---

### Option B: RS03 (×16) — All Same

Use Robstride 03 across all 16 joints for a single-SKU actuator BOM.

**Actuator weight:** 16 × 880g = 14,080g = 14.1 kg

| Component | Qty | Unit | Subtotal |
|---|---|---|---|
| Robstride 03 (all joints) | 16 | $250 | $4,000 |
| Carbon fiber frame | 1 | $1,500 | $1,500 |
| 48V 10Ah Li-ion battery (~480 Wh) | 1 | $300 | $300 |
| BMS + power distribution | 1 | $150 | $150 |
| Jetson Orin NX 16GB + carrier board | 1 | $700 | $700 |
| Intel RealSense D435i (×2) | 2 | $200 | $400 |
| IMU | 1 | $150 | $150 |
| Wiring, connectors, fasteners | — | — | $400 |
| 3D printed brackets, misc | — | — | $200 |
| **Total** | | | **$7,800** |

**Robot weight breakdown:**

| Component | Weight |
|---|---|
| Actuators | 14.1 kg |
| Carbon fiber frame | 2.0 kg |
| Battery | 2.0 kg |
| Compute + sensors | 0.8 kg |
| Wiring, misc | 0.7 kg |
| **Total** | **~20 kg** |

**Effective payload: ~3 kg**
- All joints fully within spec — shoulder has 60 Nm available vs 35 Nm needed
- Hip flex constraint fully resolved — normal stair climbing gait
- RS03 is significantly oversized at elbow and wrist — torque is wasted but simplifies BOM and spares

---

### Option Comparison

| | Option A (Mixed) | Option B (All RS03) |
|---|---|---|
| Actuator SKUs | 2 | 1 |
| Actuator cost | $3,100 | $4,000 |
| Total BOM | **$6,900** | **$7,800** |
| Premium | — | +$900 (+13%) |
| Robot mass | ~15 kg | ~20 kg |
| Max payload | ~2 kg | ~3 kg |
| Stair climbing | Reduced pace | Full capability |
| Spares complexity | 2 part numbers | 1 part number |

**Recommendation:** Option B is the stronger engineering choice — the $900 premium buys restored payload, full stair climbing, and a much simpler spare parts story. Option A makes sense only if mass budget is tight.

---

## General Notes

- All prices are approximate single-unit western retail as of early 2025
- Direct Chinese sourcing typically 20–40% cheaper — actuator costs could drop to ~$2,800 (A) or ~$3,200 (B)
- At 10 units, total BOM likely falls to ~$5,500 (A) or ~$6,200 (B)
- Hands/end effectors not included — add $300–800 for a simple gripper, $2,000+ for a dexterous hand
- QDD (quasi-direct drive) is strongly preferred for legged robots — backdrivability is critical for impact tolerance and fall recovery
- Robstride 01 full specs (weight, dimensions) not publicly available
- Damiao DM8009 dimensions unconfirmed — verify before designing mounts
- Dynamixel P-series ruled out: not backdrivable and extremely expensive ($3,000+ each)
