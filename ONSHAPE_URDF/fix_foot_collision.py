"""
fix_foot_collision.py — Post-processing step 4 for the Atom URDF pipeline.

Replaces foot link collision meshes with flat box primitives.

Background
----------
The foot STL meshes are convex solids with a flat central patch and curved edges
around the toe, heel, and sides. When the foot lands with any tilt, it contacts
the terrain on a curved edge, giving line (or point) contact rather than a 2D
patch. PhysX friction force scales with contact area, so line contact produces
far less effective friction than the material friction coefficient implies —
causing the robot to slide even with "correct" friction values.

Replacing the collision geometry with a flat box matching the plantar (sole)
region gives stable 2D patch contact across the full footprint. The box must
be thick enough (≥ 2 cm) to avoid PhysX thin-box edge-contact artefacts and
to prevent the contact solver from generating degenerate manifolds on rough
terrain triangle meshes over long training runs.

NOTE: Capsule (cylinder) collision was tested but caused PhysX contact data
accumulation on rough terrain trimesh at ~350M steps, leading to CUDA crashes.
Box collision at ≥ 2 cm thickness is the stable choice.

Box dimensions and sole position are derived from the foot mesh bounding box:
  Foot mesh bounds: X [-0.145, 0.055] (0.20 m), Y ±0.085 (0.085 m), Z [-0.0625, 0.0325]
  Box: 0.18 × 0.07 × 0.03 m  (slightly inside curved edges; 3 cm thick for stability)
  Sole bottom: z = -0.0625 m → box centre z = -0.0625 + 0.015 = -0.0475 m

The visual mesh is unchanged.

Usage
-----
    python3 fix_foot_collision.py <input.urdf> [output.urdf]

    If output path is omitted the input file is overwritten in-place.

Pipeline position
-----------------
    1. clean_urdf.py        ->  _clean.urdf
    2. set_joint_limits.py  ->  _clean_limits.urdf
    3. center_hip_origin.py ->  _clean_limits.urdf  (in-place)
    4. fix_foot_collision.py -> _clean_limits.urdf  (in-place)
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Box sole geometry — update these if the foot CAD changes.
# 3 cm thickness avoids PhysX thin-box edge artefacts and CUDA crashes on rough terrain.
BOX_X  = 0.18    # fore-aft length (m) — slightly inside the 0.20 m mesh length
BOX_Y  = 0.07    # lateral width (m)  — slightly inside the 0.085 m mesh width
BOX_Z  = 0.03    # thickness (m)      — 3 cm: stable on rough terrain trimesh
SOLE_Z = -0.0625 # z of the bottom of the foot mesh (link frame)

# Foot link name → (cx, cy) centre offsets (link frame); z is computed from SOLE_Z.
FOOT_CENTRES = {
    "Foot_Left_1":  (-0.045, -0.0276),
    "Foot_Right_1": (-0.045,  0.0276),
}


def fix_foot_collision(input_path: str, output_path: str | None = None) -> str:
    input_path  = Path(input_path)
    output_path = Path(output_path) if output_path else input_path

    tree = ET.parse(input_path)
    root = tree.getroot()

    centre_z = SOLE_Z + BOX_Z / 2
    replaced  = []

    for link in root.iter("link"):
        name = link.get("name", "")
        if name not in FOOT_CENTRES:
            continue
        cx, cy = FOOT_CENTRES[name]

        # Remove all existing collision elements.
        for col in link.findall("collision"):
            link.remove(col)

        # Insert new box collision.
        col    = ET.SubElement(link, "collision")
        origin = ET.SubElement(col, "origin")
        origin.set("xyz", f"{cx} {cy} {centre_z:.4f}")
        origin.set("rpy", "0 0 0")
        geo = ET.SubElement(col, "geometry")
        box = ET.SubElement(geo, "box")
        box.set("size", f"{BOX_X} {BOX_Y} {BOX_Z}")
        replaced.append(name)
        print(f"  {name}: mesh -> box {BOX_X}×{BOX_Y}×{BOX_Z} m  (centre z={centre_z:.4f} m)")

    if not replaced:
        print("No foot links found — check FOOT_CENTRES names match the URDF.")
        sys.exit(1)

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
    fix_foot_collision(input_urdf, output_urdf)
