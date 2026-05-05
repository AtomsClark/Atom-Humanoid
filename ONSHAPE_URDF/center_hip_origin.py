"""
center_hip_origin.py — Post-processing step 3 for the Atom URDF pipeline.

Centers base_link laterally over the robot's stance midpoint by adjusting
the base_to_torso fixed joint origin.

Background
----------
The OnShape URDF exporter places the torso body origin at the location of one
hip joint rather than at the midpoint between both hips. In the V0.7 export:

  dof_hip_pitch_left  origin y = -0.15 m  (in Torso_With_Motors_1 frame)
  dof_hip_pitch_right origin y =  0.00 m  (in Torso_With_Motors_1 frame)

The base_to_torso fixed joint has a 180 deg yaw rotation, so in the world /
base_link frame those positions become:

  left  hip y = +0.15 m
  right hip y =  0.00 m
  midpoint  y = +0.075 m  <- 7.5 cm off-centre

This script computes the required correction from the actual hip joint positions
in the URDF (no hardcoded numbers) and writes a corrected copy where base_link
is centred over the stance midpoint. The height scanner, policy observations,
and terrain curriculum all reference base_link, so this matters for training.

Usage
-----
    python3 center_hip_origin.py <input.urdf> [output.urdf]

    If output path is omitted the input file is overwritten in-place.

Pipeline position
-----------------
    1. clean_urdf.py        ->  _clean.urdf
    2. set_joint_limits.py  ->  _clean_limits.urdf
    3. center_hip_origin.py ->  _clean_limits.urdf  (in-place, or new path)
"""

import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def rpy_to_matrix(roll: float, pitch: float, yaw: float) -> list[list[float]]:
    """Return the 3x3 rotation matrix for URDF RPY (extrinsic XYZ: Rz * Ry * Rx)."""
    cx, sx = math.cos(roll),  math.sin(roll)
    cy, sy = math.cos(pitch), math.sin(pitch)
    cz, sz = math.cos(yaw),   math.sin(yaw)
    return [
        [cy*cz,  cz*sx*sy - cx*sz,  cx*cz*sy + sx*sz],
        [cy*sz,  cx*cz + sx*sy*sz,  cx*sy*sz - cz*sx],
        [-sy,    cy*sx,             cx*cy            ],
    ]


def rotate(R: list[list[float]], v: list[float]) -> list[float]:
    """Apply 3x3 rotation matrix R to vector v."""
    return [
        R[0][0]*v[0] + R[0][1]*v[1] + R[0][2]*v[2],
        R[1][0]*v[0] + R[1][1]*v[1] + R[1][2]*v[2],
        R[2][0]*v[0] + R[2][1]*v[1] + R[2][2]*v[2],
    ]


def parse_origin(joint_el: ET.Element) -> tuple[list[float], list[float]]:
    """Return (xyz, rpy) from a joint's <origin> element. Defaults to zeros."""
    origin = joint_el.find("origin")
    if origin is None:
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    xyz = [float(v) for v in origin.get("xyz", "0 0 0").split()]
    rpy = [float(v) for v in origin.get("rpy", "0 0 0").split()]
    return xyz, rpy


def center_hip_origin(input_path: str, output_path: str | None = None) -> str:
    input_path = Path(input_path)
    output_path = Path(output_path) if output_path else input_path

    tree = ET.parse(input_path)
    root = tree.getroot()

    # Index all joints by name for quick lookup.
    joints = {j.get("name"): j for j in root.iter("joint")}

    required = {"base_to_torso", "dof_hip_pitch_left", "dof_hip_pitch_right"}
    missing = required - joints.keys()
    if missing:
        raise ValueError(f"URDF is missing expected joints: {missing}")

    # --- 1. Get base_to_torso transform (parent = base_link, child = torso) ---
    bt_xyz, bt_rpy = parse_origin(joints["base_to_torso"])
    R_bt = rpy_to_matrix(*bt_rpy)

    # --- 2. Get hip positions in the torso (child) frame ---
    left_xyz,  _ = parse_origin(joints["dof_hip_pitch_left"])
    right_xyz, _ = parse_origin(joints["dof_hip_pitch_right"])

    # --- 3. Transform hip positions into the base_link (parent) frame ---
    # p_parent = bt_xyz + R_bt @ p_torso
    left_in_base  = [bt_xyz[i] + rotate(R_bt, left_xyz)[i]  for i in range(3)]
    right_in_base = [bt_xyz[i] + rotate(R_bt, right_xyz)[i] for i in range(3)]

    # --- 4. Compute the lateral (Y) midpoint and required correction ---
    midpoint_y = (left_in_base[1] + right_in_base[1]) / 2.0
    correction_y = -midpoint_y  # shift so midpoint lands at y = 0

    if abs(correction_y) < 1e-6:
        print("Hip origin already centred — no change needed.")
    else:
        print(f"  Left  hip Y in base_link frame : {left_in_base[1]:+.4f} m")
        print(f"  Right hip Y in base_link frame : {right_in_base[1]:+.4f} m")
        print(f"  Midpoint Y                     : {midpoint_y:+.4f} m")
        print(f"  Applying correction            : {correction_y:+.4f} m to base_to_torso origin Y")

    # --- 5. Apply the correction ---
    new_y = bt_xyz[1] + correction_y
    origin_el = joints["base_to_torso"].find("origin")
    new_xyz_str = f"{bt_xyz[0]} {new_y} {bt_xyz[2]}"
    origin_el.set("xyz", new_xyz_str)

    # --- 6. Write output ---
    ET.indent(tree, space="  ")
    tree.write(str(output_path), encoding="unicode", xml_declaration=True)
    print(f"Written: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    input_urdf  = sys.argv[1]
    output_urdf = sys.argv[2] if len(sys.argv) > 2 else None
    center_hip_origin(input_urdf, output_urdf)
