import glob
import os
import re

from onshape_robotics_toolkit.utilities import setup_default_logging
from onshape_robotics_toolkit.connect import Client
from onshape_robotics_toolkit.parse import CAD
from onshape_robotics_toolkit.graph import KinematicGraph
from onshape_robotics_toolkit.robot import Robot
from onshape_robotics_toolkit.formats import URDFSerializer

ASSEMBLY_URL = (
 #   "https://cad.onshape.com/documents/acf2ac35a525e41fdf671576"
 #   "/w/96fdfb5f576a64ee80f133e7"
 #   "/e/46d07101bbeb1f9346490291"
    "https://cad.onshape.com/documents/acf2ac35a525e41fdf671576"
    "/w/834211a204eb052abf64f55a"
    "/e/46d07101bbeb1f9346490291"
)

# Update this to match your OnShape assembly name
ROBOT_NAME = "Atom_Humanoid_V0"


def next_version_name(base_name):
    """Find existing *_V* directories and return the next version incremented by 0.1.

    Guarantees the returned name does not already exist as a directory, so an
    in-progress conversion never clobbers a prior output.
    """
    # Match base prefix up to and including _V, e.g. "Atom_Humanoid_V"
    match = re.match(r"^(.+_V)([\d.]+)$", base_name)
    if not match:
        # No recognizable version suffix; fall back to base_name only if free.
        if not os.path.isdir(base_name):
            return base_name
        # Otherwise append a _V0.1-style suffix and bump until unused.
        candidate_ver = 0.1
        while os.path.isdir(f"{base_name}_V{candidate_ver:g}"):
            candidate_ver = round(candidate_ver + 0.1, 1)
        return f"{base_name}_V{candidate_ver:g}"

    prefix = match.group(1)

    max_ver = -1.0
    for d in glob.glob(f"{prefix}*"):
        m = re.match(rf"^{re.escape(prefix)}([\d.]+)$", d)
        if m and os.path.isdir(d):
            max_ver = max(max_ver, float(m.group(1)))

    # If nothing matches the versioned pattern AND base_name itself is free, use it.
    if max_ver < 0 and not os.path.isdir(base_name):
        return base_name

    # Otherwise bump past the highest existing version, skipping any that already exist.
    new_ver = round(max(max_ver, 0.0) + 0.1, 1)
    candidate = f"{prefix}{new_ver:g}"
    while os.path.isdir(candidate):
        new_ver = round(new_ver + 0.1, 1)
        candidate = f"{prefix}{new_ver:g}"
    return candidate


def main():
    setup_default_logging()

    robot_dir = next_version_name(ROBOT_NAME)
    robot_name = robot_dir
    urdf_output = f"{robot_dir}/{robot_name}.urdf"
    mesh_dir = f"{robot_dir}/meshes"

    print(f"Output directory: {robot_dir}/")

    client = Client(env=".env")

    cad = CAD.from_url(
        url=ASSEMBLY_URL,
        client=client,
        max_depth=1,
    )

    kinematic_graph = KinematicGraph.from_cad(cad, use_user_defined_root=True)

    os.makedirs(robot_dir, exist_ok=True)
    kinematic_graph.show(f"{robot_dir}/{robot_name}_kinematic_graph.png")

    robot = Robot.from_graph(
        kinematic_graph=kinematic_graph,
        client=client,
        name=robot_name,
    )

    robot.show_tree()

    serializer = URDFSerializer()
    serializer.save(robot, urdf_output, download_assets=True, mesh_dir=mesh_dir)

    print(f"\nSaved: {urdf_output}")
    print(f"Meshes: {mesh_dir}/")


if __name__ == "__main__":
    main()
