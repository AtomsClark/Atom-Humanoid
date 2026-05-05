# Early Planning Notes

Original concept notes from project kickoff. Some details have been refined since (see `hardware-notes.md`, `robot-kinematics.md`, and `Actuators/humanoid-actuator-research.md` for current state).

## Initial Goals

- Design a humanoid robot from scratch
- Run the model in Isaac Lab and train walking
- Select and characterize motors/actuators (small, high torque)
- Include motor characterization in the simulation

**Original target:** working, walking robot by 2026-08-15

## Robot Characteristics

- 5'6" tall (168 cm)
- 5 kg payload at fully extended arm
- As few degrees of freedom as possible
- As few different actuator types as possible
- Walks up and down stairs
- Can reach high cabinets

## Anthropometric Limb Lengths (5'6" reference)

### Leg

| Segment   | Joint-to-Joint  | cm    | inches |
|-----------|-----------------|-------|--------|
| Foot      | heel to ankle   | 7 cm  | 2.8"   |
| Lower leg | ankle to knee   | 38 cm | 15"    |
| Upper leg | knee to hip     | 40 cm | 15.7"  |

### Torso

| Segment     | Joint-to-Joint         | cm    | inches |
|-------------|------------------------|-------|--------|
| Lower torso | hip to lumbar          | 12 cm | 4.7"   |
| Upper torso | lumbar to shoulder     | 40 cm | 15.7"  |
| Neck        | shoulder to skull base | 9 cm  | 3.5"   |
| Head        | skull base to crown    | 22 cm | 8.7"   |

### Arm

| Segment   | Joint-to-Joint     | cm    | inches |
|-----------|--------------------|-------|--------|
| Upper arm | shoulder to elbow  | 29 cm | 11.4"  |
| Forearm   | elbow to wrist     | 24 cm | 9.4"   |
| Hand      | wrist to fingertip | 17 cm | 6.7"   |

### Width

| Measure        | cm    | inches |
|----------------|-------|--------|
| Shoulder width | 37 cm | 14.6"  |
| Hip width      | 28 cm | 11"    |

### Sanity Check

- Total height: 7+38+40+12+40+9+22 = 168 cm ✓
- Shoulder height: 137 cm (81.7%) ✓
- Max upward reach: 137+29+24+17 = 207 cm (6'9") ✓ — comfortably reaches top cabinets

## Initial Torque Estimates

For 20 kg robot + 3 kg payload = 23 kg effective:

| Joint           | Nominal | Design for |
|-----------------|---------|------------|
| Ankle           | ~39 Nm  | 55 Nm      |
| Knee            | ~35 Nm  | 55 Nm      |
| Hip (abduction) | ~32 Nm  | 45 Nm      |
| Hip (flex/ext)  | ~23 Nm  | 35 Nm      |
| Waist           | ~32 Nm  | 45 Nm      |
| Shoulder        | ~24 Nm  | 35 Nm      |
| Elbow           | ~13 Nm  | 20 Nm      |
| Wrist           | ~5 Nm   | 10 Nm      |
| Neck            | ~2 Nm   | 8 Nm       |

### Actuator Tiering (initial concept)

| Type  | Peak Torque | Use At                            |
|-------|-------------|-----------------------------------|
| Large | ~60 Nm      | Ankle, knee, hip (×2 axes), waist |
| Small | ~40 Nm      | Shoulder, elbow, wrist, neck      |

> **Update:** Final V0.7 build settled on a single-SKU RS03 BOM (60 Nm peak, 9:1 gear ratio) for all 16 joints. See `Actuators/humanoid-actuator-research.md` for the full tradeoff analysis (Option A mixed RS02/RS03 vs. Option B all-RS03).

## Joint Range Reference (K-Scale K-Bot)

Used as a starting point for joint limit selection. See `joint-limits-comparison.md` for current Atom limits.

| Joint Name (KD)             | Min Angle (deg) | Max Angle (deg) |
|-----------------------------|-----------------|-----------------|
| dof_left_shoulder_pitch_03  | -60.000         | 200.000         |
| dof_left_shoulder_roll_03   | -25.000         | 95.000          |
| dof_left_shoulder_yaw_02    | -95.792         | 95.792          |
| dof_left_elbow_02           | -142.000        | 0.000           |
| dof_left_wrist_00           | -79.000         | 79.000          |
| dof_right_shoulder_pitch_03 | -200.000        | 60.000          |
| dof_right_shoulder_roll_03  | -95.000         | 25.000          |
| dof_right_shoulder_yaw_02   | -95.792         | 95.792          |
| dof_right_elbow_02          | -0.000          | 142.000         |
| dof_right_wrist_00          | -79.000         | 79.000          |
| dof_left_hip_pitch_04       | -60.000         | 127.000         |
| dof_left_hip_roll_03        | -130.000        | 12.000          |
| dof_left_hip_yaw_03         | -90.000         | 90.000          |
| dof_left_knee_04            | -0.000          | 155.000         |
| dof_left_ankle_00           | -15.000         | 65.000          |
| dof_right_hip_pitch_04      | -127.000        | 60.000          |
| dof_right_hip_roll_03       | -12.000         | 130.000         |
| dof_right_hip_yaw_03        | -90.000         | 90.000          |
| dof_right_knee_04           | -155.000        | 0.000           |
| dof_right_ankle_00          | -65.000         | 15.000          |

## Future Features (wishlist)

- Joystick control
- VR teleoperation
- App control
- Voice commands

## Compute & Sensors (initial shortlist)

- NVIDIA Jetson Orin NX — ~$1100
- Intel RealSense D435i (depth + IMU) — ~$500
- NVIDIA Jetson Orin Nano — ~$250

> **Update:** D435i selected. See `hardware-notes.md` for the perception stack discussion (forward-only height-scan masking, D435i/D405 tradeoffs, Livox Mid-360 alternative).
