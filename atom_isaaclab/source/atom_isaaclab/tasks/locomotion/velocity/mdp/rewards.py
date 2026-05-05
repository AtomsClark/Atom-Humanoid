"""Custom reward functions for the Atom Humanoid locomotion tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch

from isaaclab.assets import Articulation, RigidObject
from isaaclab.managers import SceneEntityCfg
from isaaclab.sensors import ContactSensor, RayCaster

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedRLEnv


def feet_contact_at_rest(
    env: ManagerBasedRLEnv,
    command_name: str,
    sensor_cfg: SceneEntityCfg,
    threshold: float = 0.1,
) -> torch.Tensor:
    """Penalize foot air time when the velocity command is near zero (standing).

    At zero command the robot should keep both feet planted. This term returns
    the total foot air time (sum across both feet) gated by whether the commanded
    speed is below `threshold`. It is intended to be used with a negative weight
    so that lifting feet while standing is penalized.

    When the command speed exceeds `threshold` (i.e. the robot is supposed to walk)
    this term returns zero and has no effect on the walking reward structure.

    Args:
        command_name: Name of the velocity command in the command manager.
        sensor_cfg: Config for the contact sensor, body_names should match the feet.
        threshold: Command speed (m/s) below which the robot is considered to be
            in stance / standing mode. Default: 0.1 m/s (matches feet_air_time gating).
    """
    contact_sensor: ContactSensor = env.scene.sensors[sensor_cfg.name]
    air_time = contact_sensor.data.current_air_time[:, sensor_cfg.body_ids].sum(dim=1)
    cmd_speed = torch.norm(env.command_manager.get_command(command_name)[:, :2], dim=1)
    return air_time * (cmd_speed < threshold)


def _swing_clearance_reward(
    clearance: torch.Tensor,
    foot_vel_xy: torch.Tensor,
    target_height: float,
    std: float,
    tanh_mult: float,
) -> torch.Tensor:
    """Shared core for foot clearance rewards (flat and terrain-relative).

    Computes a Gaussian reward for feet reaching a target clearance height,
    gated by horizontal foot velocity (swing phase only).

    Args:
        clearance: Foot height above reference surface. Shape: (N, num_feet).
        foot_vel_xy: Horizontal foot velocity. Shape: (N, num_feet, 2).
        target_height: Desired clearance during swing (meters).
        std: Gaussian kernel width.
        tanh_mult: Sensitivity to horizontal foot velocity for swing detection.
    """
    height_error = torch.square(clearance - target_height)
    swing_gate = torch.tanh(tanh_mult * torch.norm(foot_vel_xy, dim=2))
    return torch.exp(-torch.sum(height_error * swing_gate, dim=1) / std)


def foot_clearance_reward(
    env: ManagerBasedRLEnv,
    asset_cfg: SceneEntityCfg,
    target_height: float,
    std: float,
    tanh_mult: float,
) -> torch.Tensor:
    """Reward swinging feet for reaching a target clearance height (flat terrain).

    Uses absolute world Z, which works on flat terrain. For rough terrain, use
    ``foot_clearance_terrain_relative`` instead.

    Args:
        asset_cfg: Config with body_names matching the feet (e.g. "Foot_.*_1").
        target_height: Desired foot Z during swing (meters). 0.08-0.15m typical.
        std: Gaussian kernel width — smaller = sharper reward around target height.
        tanh_mult: Sensitivity to horizontal foot velocity. Higher = sharper swing detection.
    """
    asset: RigidObject = env.scene[asset_cfg.name]
    clearance = asset.data.body_pos_w[:, asset_cfg.body_ids, 2]
    foot_vel_xy = asset.data.body_lin_vel_w[:, asset_cfg.body_ids, :2]
    return _swing_clearance_reward(clearance, foot_vel_xy, target_height, std, tanh_mult)


def knee_singularity_barrier(
    env: ManagerBasedRLEnv,
    asset_cfg: SceneEntityCfg,
    soft_limit: float = 0.15,
    steepness: float = 20.0,
) -> torch.Tensor:
    """Exponential barrier penalty that grows as knee joints approach full extension.

    Full knee extension (angle=0) is a kinematic singularity — the leg has no leverage
    to push the body forward or absorb impacts. This barrier keeps the knees slightly
    bent by penalizing with an exponential that grows sharply near zero.

    Penalty per knee: exp(-steepness * |knee_angle|) — equals 1.0 at full extension,
    decays to ~0.05 at |angle| = soft_limit (with default steepness=20).

    Use with a negative weight (e.g. -1.0). The penalty is summed across both knees.

    Args:
        asset_cfg: Config with joint_names matching knee joints.
        soft_limit: Angle (rad) below which the barrier becomes significant. Default 0.15 rad (~8.6 deg).
        steepness: Controls how sharply the barrier grows near zero. Default 20.0.
    """
    asset: Articulation = env.scene[asset_cfg.name]
    knee_pos = asset.data.joint_pos[:, asset_cfg.joint_ids]
    return torch.exp(-steepness * knee_pos.abs()).sum(dim=-1)


def base_height_terrain_relative(
    env: ManagerBasedRLEnv,
    asset_cfg: SceneEntityCfg,
    sensor_cfg: SceneEntityCfg,
    target_height: float,
) -> torch.Tensor:
    """L2 penalty on base height relative to local terrain.

    Estimates ground height under the robot by averaging all height scanner ray-hit Z
    values, then penalizes deviation from the target height above that estimate.

    Returns squared error: (base_z - ground_z - target_height)^2. Use with a negative
    weight to penalize deviation from the target crouch height.

    Args:
        asset_cfg: Config for the robot articulation (uses root position).
        sensor_cfg: Config for the height scanner ray caster.
        target_height: Desired base height above terrain (meters). ~0.80m for a
            slight squat (robot is 0.9m at full extension).
    """
    asset: RigidObject = env.scene[asset_cfg.name]
    sensor: RayCaster = env.scene.sensors[sensor_cfg.name]
    ground_z = sensor.data.ray_hits_w[..., 2].mean(dim=-1)
    base_z = asset.data.root_pos_w[:, 2]
    return torch.square(base_z - ground_z - target_height)


def foot_clearance_terrain_relative(
    env: ManagerBasedRLEnv,
    asset_cfg: SceneEntityCfg,
    sensor_cfg: SceneEntityCfg,
    target_height: float,
    std: float,
    tanh_mult: float,
    num_nearest: int = 6,
) -> torch.Tensor:
    """Reward swinging feet for reaching a target clearance height above local terrain.

    Estimates ground height under each foot by averaging the K nearest height scanner
    ray-hit points around the foot's XY position. This mirrors real hardware where the
    foot occludes the terrain directly beneath it and only surrounding points from a
    body-mounted depth camera are available.

    Args:
        asset_cfg: Config with body_names matching the feet (e.g. "Foot_.*_1").
        sensor_cfg: Config for the height scanner ray caster (e.g. "height_scanner").
        target_height: Desired foot height above terrain during swing (meters).
        std: Gaussian kernel width — smaller = sharper reward around target height.
        tanh_mult: Sensitivity to horizontal foot velocity. Higher = sharper swing detection.
        num_nearest: Number of nearest scanner points to average for ground estimate.
    """
    asset: RigidObject = env.scene[asset_cfg.name]
    sensor: RayCaster = env.scene.sensors[sensor_cfg.name]

    foot_pos = asset.data.body_pos_w[:, asset_cfg.body_ids, :]
    num_feet = foot_pos.shape[1]
    ray_hits = sensor.data.ray_hits_w

    # KNN ground estimation: find K nearest scanner points by XY distance per foot
    foot_xy = foot_pos[:, :, :2].unsqueeze(2)   # (N, num_feet, 1, 2)
    ray_xy = ray_hits[:, :, :2].unsqueeze(1)     # (N, 1, num_rays, 2)
    dist_sq = torch.sum((foot_xy - ray_xy) ** 2, dim=-1)
    _, nearest_idx = torch.topk(dist_sq, num_nearest, dim=-1, largest=False)

    ray_z = ray_hits[:, :, 2]
    ray_z_expanded = ray_z.unsqueeze(1).expand(-1, num_feet, -1)
    ground_z = torch.gather(ray_z_expanded, 2, nearest_idx).mean(dim=-1)

    clearance = foot_pos[:, :, 2] - ground_z
    foot_vel_xy = asset.data.body_lin_vel_w[:, asset_cfg.body_ids, :2]
    return _swing_clearance_reward(clearance, foot_vel_xy, target_height, std, tanh_mult)
