"""RSL-RL PPO runner configs for the Atom Humanoid locomotion tasks.

Reference: H1 PPO config from IsaacLab (rsl_rl_ppo_cfg.py).
"""

from isaaclab.utils import configclass
from isaaclab_rl.rsl_rl import RslRlOnPolicyRunnerCfg, RslRlPpoActorCriticCfg, RslRlPpoAlgorithmCfg


@configclass
class AtomRoughPPORunnerCfg(RslRlOnPolicyRunnerCfg):
    """PPO config for rough-terrain training (large network)."""

    num_steps_per_env = 24
    max_iterations = 10000
    save_interval = 50
    experiment_name = "atom_rough"
    policy = RslRlPpoActorCriticCfg(
        init_noise_std=1.0,
        actor_obs_normalization=False,
        critic_obs_normalization=False,
        actor_hidden_dims=[512, 256, 128],
        critic_hidden_dims=[512, 256, 128],
        activation="elu",
    )
    algorithm = RslRlPpoAlgorithmCfg(
        value_loss_coef=1.0,
        use_clipped_value_loss=True,
        clip_param=0.2,
        entropy_coef=0.01,
        num_learning_epochs=5,
        num_mini_batches=4,
        learning_rate=1.0e-3,
        schedule="adaptive",
        gamma=0.99,
        lam=0.95,
        desired_kl=0.01,
        max_grad_norm=1.0,
    )


@configclass
class AtomFlatPPORunnerCfg(AtomRoughPPORunnerCfg):
    """PPO config for flat-terrain training (same architecture as rough for transfer)."""

    def __post_init__(self):
        super().__post_init__()
        self.max_iterations = 10000
        self.experiment_name = "atom_flat"
        # Use same [512,256,128] network as rough — consistent architecture for transfer
