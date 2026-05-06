"""Locomotion velocity-tracking environment configs for the Atom Humanoid.

Inherits from LocomotionVelocityRoughEnvCfg and overrides only Atom-specific parts.
Reference: IsaacLab H1 rough/flat env configs.
"""

from isaaclab.envs import ViewerCfg
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg, TerminationTermCfg
from isaaclab.utils import configclass
from isaaclab.utils.noise import AdditiveUniformNoiseCfg as Unoise

import isaaclab_tasks.manager_based.locomotion.velocity.mdp as mdp
import isaaclab.envs.mdp as base_mdp
import atom_isaaclab.tasks.locomotion.velocity.mdp as atom_mdp
from isaaclab_tasks.manager_based.locomotion.velocity.velocity_env_cfg import (
    LocomotionVelocityRoughEnvCfg,
    RewardsCfg,
)

from atom_isaaclab.robots.atom_humanoid import ATOM_HUMANOID_CFG

# Body name constants — single source of truth for contact/reward configs
FOOT_BODIES = "Foot_.*_1"
LEG_BODIES = ["Femur_.*", "Shin_.*"]
UNDESIRED_CONTACT_BODIES = [
    "Femur_.*",
    "Shin_.*",
    "Upper_Arm_.*",
    "Mid_Arm_.*",
    "Lower_Arm_.*",
    "Hip_.*",
    "Shoulder_.*",
]


@configclass
class AtomRewards(RewardsCfg):
    """Reward terms for the Atom Humanoid locomotion MDP.

    Defines terms shared by both rough and flat configs. Terms that differ between
    terrain types (undesired_contacts, feet_contact_at_rest, foot_clearance) are
    set to None here and defined in the terrain-specific subclasses.
    """

    termination_penalty = RewTerm(func=mdp.is_terminated, weight=-200.0)
    lin_vel_z_l2 = None

    track_lin_vel_xy_exp = RewTerm(
        func=mdp.track_lin_vel_xy_yaw_frame_exp,
        weight=1.0,
        params={"command_name": "base_velocity", "std": 0.5},
    )
    track_ang_vel_z_exp = RewTerm(
        func=mdp.track_ang_vel_z_world_exp,
        weight=1.0,
        params={"command_name": "base_velocity", "std": 0.5},
    )
    feet_air_time = RewTerm(
        func=mdp.feet_air_time_positive_biped,
        weight=0.25,
        params={
            "command_name": "base_velocity",
            "sensor_cfg": SceneEntityCfg("contact_forces", body_names=FOOT_BODIES),
            "threshold": 0.4,
        },
    )
    feet_slide = RewTerm(
        func=mdp.feet_slide,
        weight=-0.25,
        params={
            "sensor_cfg": SceneEntityCfg("contact_forces", body_names=FOOT_BODIES),
            "asset_cfg": SceneEntityCfg("robot", body_names=FOOT_BODIES),
        },
    )
    dof_pos_limits = RewTerm(
        func=mdp.joint_pos_limits,
        weight=-1.0,
        params={"asset_cfg": SceneEntityCfg("robot", joint_names=["dof_ankle_pitch_.*", "dof_knee_pitch_.*"])},
    )
    joint_deviation_arms = RewTerm(
        func=mdp.joint_deviation_l1,
        weight=-0.2,
        params={
            "asset_cfg": SceneEntityCfg(
                "robot",
                joint_names=["dof_shoulder_.*", "dof_arm_upper_yaw_.*", "dof_elbow_pitch_.*"],
            )
        },
    )
    joint_deviation_hip_roll = RewTerm(
        func=mdp.joint_deviation_l1,
        weight=-0.2,
        params={"asset_cfg": SceneEntityCfg("robot", joint_names=["dof_hip_roll_.*"])},
    )
    knee_singularity = RewTerm(
        func=atom_mdp.knee_singularity_barrier,
        weight=-0.5,
        params={
            "asset_cfg": SceneEntityCfg("robot", joint_names=["dof_knee_pitch_.*"]),
            "soft_limit": 0.15,
            "steepness": 20.0,
        },
    )
    base_height = RewTerm(
        func=atom_mdp.base_height_terrain_relative,
        weight=-2.0,
        params={
            "asset_cfg": SceneEntityCfg("robot"),
            "sensor_cfg": SceneEntityCfg("height_scanner"),
            "target_height": 0.75,
        },
    )

    # Terrain-specific terms — None in base, defined in subclasses
    feet_contact_at_rest = None
    undesired_contacts = None
    foot_clearance = None


@configclass
class AtomRoughEnvCfg(LocomotionVelocityRoughEnvCfg):
    """Rough-terrain locomotion env for Atom Humanoid (with terrain curriculum + height scanner)."""

    rewards: AtomRewards = AtomRewards()

    def __post_init__(self):
        super().__post_init__()

        # Robot
        self.scene.robot = ATOM_HUMANOID_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
        if self.scene.height_scanner:
            self.scene.height_scanner.prim_path = "{ENV_REGEX_NS}/Robot/base_link"
        self.observations.policy.height_scan = ObsTerm(
            func=atom_mdp.height_scan_forward_only,
            params={"sensor_cfg": SceneEntityCfg("height_scanner")},
            noise=Unoise(n_min=-0.1, n_max=0.1),
            clip=(-1.0, 1.0),
        )

        # Randomization — disabled for initial convergence (H1 also disables them)
        self.events.push_robot = None
        self.events.add_base_mass = None
        self.events.base_com = None
        self.events.reset_robot_joints.params["position_range"] = (1.0, 1.0)
        self.events.base_external_force_torque.params["asset_cfg"].body_names = ["base_link"]
        self.events.physics_material.params["static_friction_range"] = (0.8, 0.8)
        self.events.physics_material.params["dynamic_friction_range"] = (0.6, 0.6)
        self.events.reset_base.params = {
            "pose_range": {"x": (-0.5, 0.5), "y": (-0.5, 0.5), "yaw": (-3.14, 3.14)},
            "velocity_range": {
                "x": (0.0, 0.0),
                "y": (0.0, 0.0),
                "z": (0.0, 0.0),
                "roll": (0.0, 0.0),
                "pitch": (0.0, 0.0),
                "yaw": (0.0, 0.0),
            },
        }

        # Rough-terrain reward overrides
        self.rewards.foot_clearance = RewTerm(
            func=atom_mdp.foot_clearance_terrain_relative,
            weight=0.5,
            params={
                "asset_cfg": SceneEntityCfg("robot", body_names=FOOT_BODIES),
                "sensor_cfg": SceneEntityCfg("height_scanner"),
                "target_height": 0.15,
                "std": 0.05,
                "tanh_mult": 2.0,
                "num_nearest": 6,
            },
        )
        self.rewards.flat_orientation_l2.weight = -1.0
        self.rewards.dof_torques_l2.weight = 0.0
        self.rewards.action_rate_l2.weight = -0.0005  # prevents bang-bang control without NaN
        self.rewards.dof_acc_l2.weight = -1.25e-7

        # Commands: forward only, no yaw — Atom lacks hip yaw DoF
        self.commands.base_velocity.ranges.lin_vel_x = (0.0, 1.0)
        self.commands.base_velocity.ranges.lin_vel_y = (0.0, 0.0)
        self.commands.base_velocity.ranges.ang_vel_z = (0.0, 0.0)

        # Terminations
        self.terminations.base_contact.params["sensor_cfg"].body_names = "base_link"
        self.terminations.bad_orientation = TerminationTermCfg(
            func=base_mdp.bad_orientation,
            params={"limit_angle": 1.0},
        )
        self.terminations.root_height = None  # world Z not valid on rough terrain
        # leg_contact: 200N catches leg-sitting (body weight ~300N across femurs ~150N each)
        # while allowing brief shin scrapes on step edges (~10-30N)
        self.terminations.leg_contact = TerminationTermCfg(
            func=base_mdp.illegal_contact,
            params={
                "sensor_cfg": SceneEntityCfg("contact_forces", body_names=LEG_BODIES),
                "threshold": 200.0,
            },
        )
        self.scene.height_scanner.debug_vis = False


def _apply_play_defaults(cfg):
    """Shared play-mode overrides for all _PLAY env configs."""
    cfg.scene.num_envs = 50
    cfg.scene.env_spacing = 2.5
    cfg.episode_length_s = 40.0
    cfg.observations.policy.enable_corruption = False
    cfg.events.base_external_force_torque = None
    cfg.events.push_robot = None


def _apply_hero_defaults(cfg):
    """Shared hero-shot overrides: many envs, random spawn yaw, wide overview camera.

    Atom has no hip yaw DoF, so commanded velocity stays forward-only — the
    visual variety comes from each env spawning with a different yaw, so a
    forward command sends robots in every direction from a top-down view.
    """
    cfg.scene.num_envs = 64
    cfg.scene.env_spacing = 3.0
    cfg.episode_length_s = 40.0
    cfg.observations.policy.enable_corruption = False
    cfg.events.base_external_force_torque = None
    cfg.events.push_robot = None
    cfg.events.reset_base.params["pose_range"]["yaw"] = (-3.14, 3.14)
    cfg.viewer = ViewerCfg(
        eye=(18.0, 18.0, 14.0),
        lookat=(0.0, 0.0, 1.0),
        origin_type="world",
        resolution=(1920, 1080),
    )


@configclass
class AtomRoughEnvCfg_PLAY(AtomRoughEnvCfg):
    """Play variant: smaller scene, fixed forward command, no randomization."""

    def __post_init__(self):
        super().__post_init__()
        _apply_play_defaults(self)
        self.scene.terrain.max_init_terrain_level = None
        if self.scene.terrain.terrain_generator is not None:
            self.scene.terrain.terrain_generator.num_rows = 5
            self.scene.terrain.terrain_generator.num_cols = 5
            self.scene.terrain.terrain_generator.curriculum = False
        self.commands.base_velocity.ranges.lin_vel_x = (1.0, 1.0)


@configclass
class AtomFlatEnvCfg(AtomRoughEnvCfg):
    """Flat-terrain locomotion env — H1-matched rewards for initial training.

    Matches H1 flat reward structure exactly: strong feet_air_time, moderate smoothness
    penalties, no extra custom penalties. Custom terms (knee_singularity, base_height,
    foot_clearance, etc.) are zeroed out here but preserved in rough config for later use.
    """

    def __post_init__(self):
        super().__post_init__()
        self.scene.terrain.terrain_type = "plane"
        self.scene.terrain.terrain_generator = None
        self.curriculum.terrain_levels = None

        # Match H1 flat exactly: feet_air_time=1.0, threshold=0.6
        self.rewards.feet_air_time.weight = 1.0
        self.rewards.feet_air_time.params["threshold"] = 0.6

        # H1-matched smoothness weights
        self.rewards.flat_orientation_l2.weight = -1.0  # H1 uses -1.0 (we had -5.0)
        self.rewards.dof_torques_l2.weight = 0.0        # H1 disables torque penalty
        self.rewards.action_rate_l2.weight = -0.001     # H1 uses -0.005 but that crashed at iter 1700 (Run 56)
        self.rewards.dof_acc_l2.weight = -1.25e-7       # H1 value

        # Disable custom terms — H1 doesn't use any of these
        self.rewards.knee_singularity.weight = 0.0
        self.rewards.base_height.weight = 0.0

        self.terminations.root_height = TerminationTermCfg(
            func=base_mdp.root_height_below_minimum,
            params={"minimum_height": 0.4},  # lowered for deep squat spawn (0.68m)
        )


@configclass
class AtomFlatEnvCfg_PLAY(AtomFlatEnvCfg):
    """Play variant for flat env."""

    def __post_init__(self):
        super().__post_init__()
        _apply_play_defaults(self)
        self.commands.base_velocity.ranges.lin_vel_x = (1.0, 1.0)
        self.commands.base_velocity.ranges.ang_vel_z = (0.0, 0.0)
        self.events.reset_base.params["pose_range"]["yaw"] = (0.0, 0.0)


@configclass
class AtomFlatEnvCfg_HERO(AtomFlatEnvCfg):
    """Hero-shot variant for flat env: many robots, random yaw spawns, wide camera.

    Command range is biased toward the easier middle of the training distribution
    (0.3-0.7 m/s) so policies aren't pushed into upper-edge territory they may not
    have generalized to.
    """

    def __post_init__(self):
        super().__post_init__()
        _apply_hero_defaults(self)
        self.commands.base_velocity.ranges.lin_vel_x = (0.3, 0.7)
        self.commands.base_velocity.ranges.ang_vel_z = (0.0, 0.0)


@configclass
class AtomRoughEnvCfg_HERO(AtomRoughEnvCfg):
    """Hero-shot variant for rough env: many robots spread across varied terrain."""

    def __post_init__(self):
        super().__post_init__()
        _apply_hero_defaults(self)
        self.scene.terrain.max_init_terrain_level = None
        if self.scene.terrain.terrain_generator is not None:
            self.scene.terrain.terrain_generator.num_rows = 8
            self.scene.terrain.terrain_generator.num_cols = 8
            self.scene.terrain.terrain_generator.curriculum = False
        self.commands.base_velocity.ranges.lin_vel_x = (0.3, 0.7)
        self.commands.base_velocity.ranges.ang_vel_z = (0.0, 0.0)


@configclass
class AtomRoughEnvCfg_HERO_SIT(AtomRoughEnvCfg):
    """Rough hero variant tuned for visualizing the leg-sitting reward exploit.

    Matches the original PLAY review config (5×5 terrain grid, no curriculum,
    higher commanded speed) so policies trained with leg_contact disabled
    reproduce the femur-sitting equilibrium they originally exhibited.
    """

    def __post_init__(self):
        super().__post_init__()
        _apply_hero_defaults(self)
        self.scene.terrain.max_init_terrain_level = None
        if self.scene.terrain.terrain_generator is not None:
            self.scene.terrain.terrain_generator.num_rows = 5
            self.scene.terrain.terrain_generator.num_cols = 5
            self.scene.terrain.terrain_generator.curriculum = False
        self.commands.base_velocity.ranges.lin_vel_x = (1.0, 1.0)
        self.commands.base_velocity.ranges.ang_vel_z = (0.0, 0.0)


@configclass
class AtomFlatStandingEnvCfg(AtomFlatEnvCfg):
    """Standing-specialist policy — trained separately from the walking policy.

    Deployment architecture: switch between standing and walking policies at runtime
    based on commanded velocity magnitude. Suggested threshold: |v_cmd| < 0.05 m/s.

    Key differences from walking policy:
    - Zero command only — no locomotion required
    - feet_air_time removed — no tension between stepping reward and standing penalty
    - feet_contact_at_rest unconditional (threshold=0.0) and heavily weighted
    - Stronger orientation penalty — standing demands stricter upright posture

    NOTE: Not yet trained. Train after walking + rough terrain curriculum is complete.
    """

    def __post_init__(self):
        super().__post_init__()
        self.commands.base_velocity.ranges.lin_vel_x = (0.0, 0.0)
        self.commands.base_velocity.ranges.lin_vel_y = (0.0, 0.0)
        self.commands.base_velocity.ranges.ang_vel_z = (0.0, 0.0)
        self.rewards.feet_air_time.weight = 0.0
        self.rewards.feet_contact_at_rest = RewTerm(
            func=atom_mdp.feet_contact_at_rest,
            weight=-5.0,
            params={
                "command_name": "base_velocity",
                "sensor_cfg": SceneEntityCfg("contact_forces", body_names=FOOT_BODIES),
                "threshold": 0.0,
            },
        )
        self.rewards.flat_orientation_l2.weight = -10.0


@configclass
class AtomFlatStandingEnvCfg_PLAY(AtomFlatStandingEnvCfg):
    """Play variant for standing policy evaluation."""

    def __post_init__(self):
        super().__post_init__()
        _apply_play_defaults(self)
        self.events.reset_base.params["pose_range"]["yaw"] = (0.0, 0.0)
