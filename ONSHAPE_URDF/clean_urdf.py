"""
clean_urdf.py — Post-process an exported OnShape URDF.

Removes frame_ reference links/joints added in OnShape (IMU, foot, hand frames)
that are not needed for simulation. Writes a _clean.urdf alongside the original,
sharing the same meshes/ directory.

Usage:
    python3 clean_urdf.py <path/to/robot.urdf>

Output:
    <path/to/robot_clean.urdf>  (original is untouched)
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def clean_urdf(input_path: str) -> str:
    input_path = Path(input_path)
    output_path = input_path.with_name(input_path.stem + "_clean.urdf")

    tree = ET.parse(input_path)
    root = tree.getroot()

    # Remove all <link> and <joint> elements whose name starts with "frame_"
    to_remove = [el for el in root if el.get("name", "").startswith("frame_")]
    for el in to_remove:
        root.remove(el)
        print(f"  Removed: <{el.tag} name=\"{el.get('name')}\">")

    ET.indent(tree, space="  ")
    tree.write(output_path, xml_declaration=True, encoding="unicode")
    print(f"\nWritten: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    clean_urdf(sys.argv[1])
