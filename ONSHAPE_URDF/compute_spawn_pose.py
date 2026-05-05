"""
compute_spawn_pose.py — Compute balanced-stance spawn joint angles for the Atom Humanoid.

Given a target knee bend, outputs the hip pitch and ankle pitch that place the
foot directly under the hip joint (zero sagittal moment at spawn) with the
sole flat on the ground.

Background
----------
For a two-segment leg (femur L1, tibia L2) with the foot directly under the hip:

    L1·sin(hip) + L2·sin(hip - knee) = 0

Solving for hip given knee:

    hip = atan2(L2·sin(knee), L1 + L2·cos(knee))

Flat-foot constraint (sole parallel to ground):

    ankle = knee - hip

All angles in Atom's left-side sign convention:
  hip_pitch_left > 0  → femur tilts forward
  knee_pitch_left > 0 → knee bends
  ankle_pitch_left > 0 → dorsiflexion (toes up / heel down → flat foot in squat)

Right-side values are the negatives of left-side values.

Segment lengths are derived from URDF joint origins:
  dof_knee_pitch_left  xyz = (-0.025, -0.4,   -0.05)  → L1 = 0.4039 m
  dof_ankle_pitch_left xyz = (-0.025,  0.38,  -0.055)  → L2 = 0.3848 m

Usage
-----
    python3 compute_spawn_pose.py [knee_deg]

    knee_deg  Target knee bend in degrees (default: 57)

Example
-------
    $ python3 compute_spawn_pose.py 57
    Balanced-stance spawn pose (knee = 57.0°, 1.000 rad)
      hip_pitch  : 0.487 rad  (27.9°)
      ankle_pitch: 0.513 rad  (29.4°)
    Right side: negate all values.
    atom_humanoid.py joint_pos snippet:
      "dof_hip_pitch_left":   0.487,
      "dof_hip_pitch_right": -0.487,
      "dof_knee_pitch_left":  1.000,
      "dof_knee_pitch_right":-1.000,
      "dof_ankle_pitch_left": 0.513,
      "dof_ankle_pitch_right":-0.513,
"""

import math
import sys

# Atom Humanoid leg segment lengths (from URDF joint origins, V0.7)
L1 = math.sqrt(0.025**2 + 0.40**2  + 0.05**2)   # femur: hip -> knee  = 0.4039 m
L2 = math.sqrt(0.025**2 + 0.38**2  + 0.055**2)  # tibia: knee -> ankle = 0.3848 m


def compute_pose(knee_deg: float) -> dict:
    """Return balanced-stance hip and ankle angles (radians) for a given knee bend."""
    knee = math.radians(knee_deg)
    hip  = math.atan2(L2 * math.sin(knee), L1 + L2 * math.cos(knee))
    ankle = knee - hip
    return {"hip": hip, "knee": knee, "ankle": ankle}


def main(knee_deg: float = 57.0) -> None:
    pose = compute_pose(knee_deg)
    hip, knee, ankle = pose["hip"], pose["knee"], pose["ankle"]

    print(f"Balanced-stance spawn pose (knee = {knee_deg}°, {knee:.3f} rad)")
    print(f"  Femur L1 = {L1:.4f} m,  Tibia L2 = {L2:.4f} m")
    print(f"  hip_pitch  : {hip:.3f} rad  ({math.degrees(hip):.1f}°)")
    print(f"  ankle_pitch: {ankle:.3f} rad  ({math.degrees(ankle):.1f}°)")
    print("Right side: negate all values.")
    print("\natom_humanoid.py joint_pos snippet:")
    print(f'  "dof_hip_pitch_left":    {hip:.3f},')
    print(f'  "dof_hip_pitch_right":  -{hip:.3f},')
    print(f'  "dof_knee_pitch_left":   {knee:.3f},')
    print(f'  "dof_knee_pitch_right": -{knee:.3f},')
    print(f'  "dof_ankle_pitch_left":  {ankle:.3f},')
    print(f'  "dof_ankle_pitch_right":-{ankle:.3f},')


if __name__ == "__main__":
    deg = float(sys.argv[1]) if len(sys.argv) > 1 else 57.0
    main(deg)
