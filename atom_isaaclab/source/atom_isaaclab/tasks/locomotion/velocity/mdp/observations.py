"""Custom observation functions for the Atom Humanoid locomotion tasks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch

from isaaclab.managers import SceneEntityCfg
from isaaclab.sensors import RayCaster

if TYPE_CHECKING:
    from isaaclab.envs import ManagerBasedEnv


def height_scan_forward_only(
    env: ManagerBasedEnv,
    sensor_cfg: SceneEntityCfg,
    offset: float = 0.5,
    grid_cols: int = 17,
    grid_rows: int = 11,
    rear_cols: int = 8,
) -> torch.Tensor:
    """Height scan with rear columns zeroed out (forward-camera-only deployment).

    The simulated height scanner uses a 17x11 grid (1.6m x 1.0m, 0.1m resolution)
    centered on base_link. With "xy" ordering, each of the 11 Y-rows contains 17
    X-points from -0.8m (rear) to +0.8m (forward).

    This function zeros the first `rear_cols` X-indices in each row (x < 0), simulating
    a forward-facing depth camera that cannot see behind the robot. The obs dimension
    stays at 187 so the network architecture is unchanged — if rear vision hardware is
    added later, training can resume without reshaping.

    Args:
        sensor_cfg: Config for the height scanner ray caster.
        offset: Height offset subtracted from raw scan values. Default: 0.5.
        grid_cols: Number of X-points per row (17 for 1.6m at 0.1m res). Default: 17.
        grid_rows: Number of Y-rows (11 for 1.0m at 0.1m res). Default: 11.
        rear_cols: Number of rear X-columns to zero (x < 0). Default: 8.
    """
    sensor: RayCaster = env.scene.sensors[sensor_cfg.name]
    scan = sensor.data.pos_w[:, 2].unsqueeze(1) - sensor.data.ray_hits_w[..., 2] - offset
    scan = scan.reshape(scan.shape[0], grid_rows, grid_cols)
    scan[:, :, :rear_cols] = 0.0
    return scan.reshape(scan.shape[0], -1)
