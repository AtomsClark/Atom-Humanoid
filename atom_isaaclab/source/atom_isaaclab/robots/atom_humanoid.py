"""ArticulationCfg for the Atom Humanoid robot.

Reference: unitree.py H1_CFG pattern from IsaacLab.
URDF source: ONSHAPE_URDF pipeline (convert.py), V0.7 output.
"""

import isaaclab.sim as sim_utils
from isaaclab.actuators import ImplicitActuatorCfg
from isaaclab.assets import ArticulationCfg

ATOM_URDF_PATH = "/home/atoms/Documents/Robots/ONSHAPE_URDF/Atom_Humanoid_V0.7/Atom_Humanoid_V0.7_clean_limits.urdf"

ATOM_HUMANOID_CFG = ArticulationCfg(
    spawn=sim_utils.UrdfFileCfg(
        asset_path=ATOM_URDF_PATH,
        activate_contact_sensors=True,
        fix_base=False,
        joint_drive=None,  # ImplicitActuatorCfg handles joint drives; disable URDF-level defaults
        rigid_props=sim_utils.RigidBodyPropertiesCfg(
            disable_gravity=False,
            retain_accelerations=False,
            linear_damping=0.0,
            angular_damping=0.0,
            max_linear_velocity=1000.0,
            max_angular_velocity=1000.0,
            max_depenetration_velocity=1.0,
        ),
        articulation_props=sim_utils.ArticulationRootPropertiesCfg(
            enabled_self_collisions=False,
            solver_position_iteration_count=4,
            solver_velocity_iteration_count=4,
        ),
    ),
    init_state=ArticulationCfg.InitialStateCfg(
        pos=(0.0, 0.0, 0.75),   # moderate squat (50° knee bend), height from compute_spawn_pose.py
        rot=(1.0, 0.0, 0.0, 0.0),  # identity: base_to_torso fixed joint in URDF handles 180° reorientation
        joint_pos={
            # Moderate squat at 50° knee bend — enough to bias exploration toward bent-knee
            # gaits without being so deep that sumo-walking becomes the path of least resistance.
            "dof_hip_pitch_left": 0.425,
            "dof_hip_pitch_right": -0.425,
            "dof_hip_roll_.*": 0.0,
            "dof_knee_pitch_left": 0.873,   # 50° bend
            "dof_knee_pitch_right": -0.873,
            "dof_ankle_pitch_left": 0.448,
            "dof_ankle_pitch_right": -0.448,
            # Arms at sides — upper arm hanging, elbow bent ~69°, forearm forward
            "dof_shoulder_pitch_left": 0.0,
            "dof_shoulder_pitch_right": 0.0,
            "dof_shoulder_roll_left": 0.3,   # ~17° outward
            "dof_shoulder_roll_right": -0.3,
            "dof_arm_upper_yaw_.*": 0.0,
            "dof_elbow_pitch_left": 1.2,   # ~69° bend — arms bent at sides
            "dof_elbow_pitch_right": -1.2,
        },
        joint_vel={".*": 0.0},
    ),
    soft_joint_pos_limit_factor=0.9,
    actuators={
        # PD gains match H1/G1 exactly. effort_limit_sim raised to 300 Nm (match H1/G1 training)
        # to prevent PD saturation artifacts. Real hardware limit is 60 Nm (RS03) — enforce via
        # dof_torques_l2 penalty post-convergence, not sim clipping during training.
        # armature=0.005 kg·m²: reflected rotor inertia for RS03 (gear ratio 9:1).
        "legs": ImplicitActuatorCfg(
            joint_names_expr=["dof_hip_pitch_.*", "dof_hip_roll_.*", "dof_knee_pitch_.*"],
            effort_limit_sim=300,
            armature=0.005,
            stiffness={
                "dof_hip_pitch_.*": 200.0,
                "dof_hip_roll_.*": 150.0,
                "dof_knee_pitch_.*": 200.0,
            },
            damping={
                "dof_hip_pitch_.*": 5.0,
                "dof_hip_roll_.*": 5.0,
                "dof_knee_pitch_.*": 5.0,
            },
        ),
        "ankles": ImplicitActuatorCfg(
            joint_names_expr=["dof_ankle_pitch_.*"],
            effort_limit_sim=100,  # match H1 ankle limit
            armature=0.005,
            stiffness={"dof_ankle_pitch_.*": 20.0},
            damping={"dof_ankle_pitch_.*": 4.0},
        ),
        "arms": ImplicitActuatorCfg(
            joint_names_expr=["dof_shoulder_.*", "dof_arm_upper_yaw_.*", "dof_elbow_pitch_.*"],
            effort_limit_sim=300,
            armature=0.005,
            stiffness={
                "dof_shoulder_.*": 40.0,
                "dof_arm_upper_yaw_.*": 40.0,
                "dof_elbow_pitch_.*": 40.0,
            },
            damping={
                "dof_shoulder_.*": 10.0,
                "dof_arm_upper_yaw_.*": 10.0,
                "dof_elbow_pitch_.*": 10.0,
            },
        ),
    },
)
