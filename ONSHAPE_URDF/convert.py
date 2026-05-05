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
    """Find existing *_V* directories and return the next version incremented by 0.1."""
    # Match base prefix up to and including _V, e.g. "Atom_Humanoid_V"
    match = re.match(r"^(.+_V)([\d.]+)$", base_name)
    if not match:
        return base_name
    prefix = match.group(1)

    existing = glob.glob(f"{prefix}*")
    if not existing:
        return base_name

    max_ver = -1.0
    for d in existing:
        m = re.match(rf"^{re.escape(prefix)}([\d.]+)$", d)
        if m:
            max_ver = max(max_ver, float(m.group(1)))

    if max_ver < 0:
        return base_name

    new_ver = round(max_ver + 0.1, 1)
    return f"{prefix}{new_ver:g}"


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
