# Joint Limits Comparison — Atom Humanoid vs H1 vs K-Bot v2

Reference data for joint limit decisions. All values in degrees. "Range" = upper - lower.

Sources:
- Atom: `ONSHAPE_URDF/Atom_Humanoid_V0.7/Atom_Humanoid_V0.7_clean.urdf` (original OnShape export)
- H1: `~/mujoco_menagerie/unitree_h1/h1.xml` (MuJoCo menagerie)
- K-Bot v2: `~/kbot/ksim-kbot/ksim_kbot/kscale-assets/kbot-v2-lw/robot.urdf`

Note: Atom and K-Bot use mirrored sign conventions (left positive, right negated). H1 MuJoCo model uses the same limits for both sides. Table shows left-side values for consistency; right-side is mirrored.

---

## Leg Joints

| Joint | Atom (original) | Atom (revised) | H1 | K-Bot v2 | Notes |
|-------|-----------------|----------------|-----|----------|-------|
| **hip_pitch** | -30° / +145° (175°) | **-90°** / +145° (**235°**) | -90° / +90° (180°) | -60° / +127° (187°) | Atom's -30° severely limited backward extension; revised to match H1's -90° |
| **hip_roll** | -60° / +30° (90°) | -60° / +30° (90°) | -24.6° / +24.6° (49°) | -12° / +130° (142°) | Atom's -60° = abduction (outward), +30° = adduction (inward). H1 is symmetric and much tighter. K-Bot has unusual 130° range. |
| **knee** | +8.6° / +160° (151°) | **0°** / +160° (**160°**) | -14.9° / +117.5° (132°) | 0° / +155° (155°) | Minimum bend opened from 8.6° to 0° (full extension). H1 allows slight hyperextension (-14.9°). |
| **ankle** | -70° / +30° (100°) | -70° / +30° (100°) | -49.8° / +29.8° (80°) | -45° / +17° (62°) | Atom has the most ankle range of all three — no change needed. |

## Arm Joints

| Joint | Atom | H1 | K-Bot v2 | Notes |
|-------|------|-----|----------|-------|
| **shoulder_pitch** | -180° / +80° (260°) | -164° / +164° (329°) | -60° / +200° (260°) | Atom matches K-Bot range. H1 has more symmetric range. |
| **shoulder_roll** | 0° / +180° (180°) | -19.5° / +178° (198°) | -22° / +95° (117°) | Atom is generous. H1 allows slight negative. K-Bot is tighter. |
| **arm_upper_yaw** | -90° / +100° (190°) | -74.5° / +255° (330°) | -95° / +95° (190°) | Atom matches K-Bot range. H1 has much larger (shoulder_yaw). |
| **elbow** | 0° / +160° (160°) | -71.6° / +149.5° (221°) | 0° / +142° (142°) | Atom allows more extension than K-Bot. H1 allows negative (hyperextension). |

## Additional Joints (H1 and K-Bot only)

| Joint | H1 | K-Bot v2 | Notes |
|-------|-----|----------|-------|
| **hip_yaw** | -24.6° / +24.6° (49°) | -90° / +90° (180°) | Atom has no hip yaw joint |
| **torso** | -134.6° / +134.6° (269°) | N/A | Atom has no torso joint |
| **wrist** | N/A | -100° / +100° (200°) | Atom has no wrist joint |

---

## Key Design Differences

1. **Atom has no hip yaw** — H1 and K-Bot both have hip yaw for turning. Atom compensates with hip roll for lateral movement, but turning must come from differential stride length or ankle/hip pitch asymmetry.

2. **All Atom joints use axis `0 0 -1`** — the OnShape export maps all motor rotation axes to local -Z. The `base_to_torso` 180° fixed joint remaps into world frame.

3. **Effort limits**: Atom = 60 Nm (RS03), H1 = 300 Nm (legs) / 100 Nm (ankles), K-Bot = RS03 (same as Atom). Atom and K-Bot share the same motors; H1 has much stronger actuators.

4. **Ankle range**: Atom has the most generous ankle range (100°), which is important since it has no hip yaw — ankle compliance compensates for missing DoF.
