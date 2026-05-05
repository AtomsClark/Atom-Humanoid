"""Post-process a URDF file to set joint limits from a YAML config.

Reads joint_limits.yaml and applies the specified lower/upper limits (in degrees)
to the corresponding joints in the URDF. Writes the result alongside the original
with a _limits suffix.

Usage:
    python3 ONSHAPE_URDF/set_joint_limits.py ONSHAPE_URDF/Atom_Humanoid_V0.7/Atom_Humanoid_V0.7_clean.urdf
"""

import argparse
import math
import os
import xml.etree.ElementTree as ET

import yaml


def main():
    parser = argparse.ArgumentParser(description="Apply joint limits from YAML config to URDF.")
    parser.add_argument("urdf", help="Path to the input URDF file.")
    parser.add_argument("--config", default=None, help="Path to joint_limits.yaml (default: same dir as script).")
    parser.add_argument("--output", default=None, help="Output URDF path (default: <name>_limits.urdf).")
    args = parser.parse_args()

    if args.config is None:
        args.config = os.path.join(os.path.dirname(os.path.abspath(__file__)), "joint_limits.yaml")

    with open(args.config) as f:
        limits_cfg = yaml.safe_load(f)

    tree = ET.parse(args.urdf)
    root = tree.getroot()

    modified = []
    for joint in root.findall("joint"):
        name = joint.get("name")
        if name not in limits_cfg:
            continue
        cfg = limits_cfg[name]
        limit_el = joint.find("limit")
        if limit_el is None:
            continue

        old_lo = float(limit_el.get("lower", 0))
        old_hi = float(limit_el.get("upper", 0))
        new_lo = math.radians(cfg["lower"])
        new_hi = math.radians(cfg["upper"])

        limit_el.set("lower", str(round(new_lo, 7)))
        limit_el.set("upper", str(round(new_hi, 7)))
        modified.append(name)

        lo_changed = abs(old_lo - new_lo) > 1e-4
        hi_changed = abs(old_hi - new_hi) > 1e-4
        changes = []
        if lo_changed:
            changes.append(f"lower {math.degrees(old_lo):.1f}° -> {cfg['lower']:.1f}°")
        if hi_changed:
            changes.append(f"upper {math.degrees(old_hi):.1f}° -> {cfg['upper']:.1f}°")
        if changes:
            print(f"  {name}: {', '.join(changes)}")
        else:
            print(f"  {name}: unchanged")

    if args.output is None:
        base, ext = os.path.splitext(args.urdf)
        # Remove existing _limits or _clean suffixes to avoid stacking
        for suffix in ("_limits", "_clean"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
        args.output = f"{base}_clean_limits{ext}"

    tree.write(args.output, xml_declaration=True, encoding="unicode")
    print(f"\n[INFO] Written: {args.output}")
    print(f"[INFO] Modified {len(modified)} joints.")


if __name__ == "__main__":
    main()
