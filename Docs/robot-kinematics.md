# Robot Kinematics — Joint Lengths & Range of Motion

**Configuration:** 5'6" (167.6 cm), 16 DoF humanoid, human female proportions

---

## Segment Lengths

### Legs

| Segment | Joint-to-Joint | cm | inches |
|---|---|---|---|
| Foot | Heel to ankle | 7 cm | 2.8" |
| Lower leg | Ankle to knee | 38 cm | 15.0" |
| Upper leg | Knee to hip | 40 cm | 15.7" |

### Torso

| Segment | Joint-to-Joint | cm | inches |
|---|---|---|---|
| Lower torso | Hip to lumbar | 12 cm | 4.7" |
| Upper torso | Lumbar to shoulder | 40 cm | 15.7" |
| Neck | Shoulder to skull base | 9 cm | 3.5" |
| Head | Skull base to crown | 22 cm | 8.7" |

### Arms

| Segment | Joint-to-Joint | cm | inches |
|---|---|---|---|
| Upper arm | Shoulder to elbow | 29 cm | 11.4" |
| Forearm | Elbow to wrist | 24 cm | 9.4" |
| Hand | Wrist to fingertip | 17 cm | 6.7" |

### Width Reference

| Measure | cm | inches |
|---|---|---|
| Shoulder width (biacromial) | 37 cm | 14.6" |
| Hip width (biiliac) | 28 cm | 11.0" |

### Sanity Checks

- **Total height:** 7 + 38 + 40 + 12 + 40 + 9 + 22 = **168 cm ✓**
- **Shoulder height:** 7 + 38 + 40 + 12 + 40 = **137 cm (81.7% of height) ✓**
- **Max upward reach:** 137 + 29 + 24 + 17 = **207 cm (6'9") ✓** — comfortably reaches top of standard kitchen cabinets (183–213 cm)

---

## Degrees of Freedom

16 DoF total — 4 per limb, bilateral.

| # | Joint | Motion | Count |
|---|---|---|---|
| 1–2 | Hip flex/ext | Sagittal — forward/back | ×2 |
| 3–4 | Hip abduction | Frontal — side to side | ×2 |
| 5–6 | Knee flex | Sagittal — bend/straighten | ×2 |
| 7–8 | Ankle flex | Sagittal — dorsi/plantarflexion | ×2 |
| 9–10 | Shoulder flex/ext | Sagittal — forward/back | ×2 |
| 11–12 | Shoulder abduction | Frontal — side raise | ×2 |
| 13–14 | Shoulder yaw | Transverse — internal/external rotation | ×2 |
| 15–16 | Elbow flex | Sagittal — bend/straighten | ×2 |

---

## Range of Motion

**Sign convention:** negative = extension / adduction / internal rotation, positive = flexion / abduction / external rotation

| Joint | Motion | Functional Range | Full Passive Range | Key Activities |
|---|---|---|---|---|
| **Hip flex/ext** | Forward/back | −20° to +120° | −30° to +145° | Walking: ±15°, Stairs: +70°, Floor pickup: +120° |
| **Hip abduction** | Side to side | −20° to +45° | −30° to +60° | Walking: ±10°, Single-leg balance: +15° |
| **Knee flex** | Bend/straighten | 0° to +140° | 0° to +160° | Walking: +60°, Stairs: +90°, Full squat: +140° |
| **Ankle flex** | Dorsi/plantarflexion | −20° to +50° | −30° to +70° | Walking: ±15°, Stair push-off: +40° |
| **Shoulder flex/ext** | Forward/back | −60° to +180° | −80° to +180° | Reach overhead: +180°, Reach behind: −60° |
| **Shoulder abduction** | Side raise | 0° to +180° | 0° to +180° | Carry at side: 0°, Full overhead: +180° |
| **Shoulder yaw** | Internal/external rotation | −70° to +90° | −90° to +100° | Doorknob: ±45°, Pouring: −60°, Tool use: full range |
| **Elbow flex** | Bend/straighten | 0° to +145° | 0° to +160° | Carry: +90°, Reach to mouth: +145° |

### Notes

- **Knee** is modeled as a pure hinge — passive axial rotation exists anatomically but is not actuated
- **Ankle** dorsiflexion (+20°) is far more limited than plantarflexion (−50°); the calf is the dominant push-off muscle
- **Shoulder yaw** (internal/external rotation) is critical for manipulation — turning a doorknob, pouring, screwing — and was selected over wrist flex for the 16 DoF configuration
- **Hip extension** (negative hip flex) is limited by ligament tension — the pelvis restricts backward leg travel to ~20° active, ~30° passive
- For stair climbing, the critical minimums are: **knee +90°** and **hip flex +70°**

---

## Reach Envelope Summary

| Target | Height | Achievable? |
|---|---|---|
| Bottom of upper cabinets | 137 cm | At shoulder height — trivial |
| Mid upper cabinet shelf | 152 cm | Arm partially raised |
| Top of upper cabinets (low) | 183 cm | Arm ~75% raised |
| Top of upper cabinets (high) | 213 cm | Near full extension — achievable |
| Max overhead reach | 207 cm | Full arm extension from 137 cm shoulder |
