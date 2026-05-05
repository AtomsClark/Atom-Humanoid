"""
Atom Humanoid Isaac Lab extension.

Registers locomotion RL environments for the Atom Humanoid robot.
"""

import os

# Convenience: package root
ATOM_ISAACLAB_EXT_DIR = os.path.dirname(os.path.abspath(__file__))

# Import tasks so gym.register() calls run on import
from atom_isaaclab.tasks import *  # noqa: F401, F403
