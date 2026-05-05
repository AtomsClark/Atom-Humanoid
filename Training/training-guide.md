# Training Guide

Self-serve reference for running Isaac Lab training sessions on the Atom Humanoid.

---

## Prerequisites

1. **Activate the conda env** (or use `conda run -n env_isaaclab` for headless commands):
   ```bash
   conda activate env_isaaclab
   ```

2. **Kill stale Isaac processes** — stale processes cause GPU/CPU contention:
   ```bash
   ps aux | grep "env_isaaclab/bin/python"
   # kill any stale PIDs found
   ```

3. **Close heavy desktop apps** — Firefox, VSCode, Obsidian, etc. take GPU scheduler time and ~575 MB display VRAM. Close them before training for cleaner runs.

---

## Train

Run from `atom_isaaclab/`:

```bash
cd /home/atoms/Documents/Robots/atom_isaaclab
conda run -n env_isaaclab bash -c "MPLBACKEND=Agg /home/atoms/IsaacLab/isaaclab.sh -p scripts/train.py --task Isaac-Velocity-Flat-Atom-v0 --num_envs 4096 --headless"
```

- `MPLBACKEND=Agg` is required — omitting it causes a tkinter crash.
- `--headless` omits the GUI renderer; remove it to watch training in real time (slower).
- Logs are written to `logs/rsl_rl/atom_flat/<timestamp>/`.

**Available tasks:**
| Task | Use |
|------|-----|
| `Isaac-Velocity-Flat-Atom-v0` | Walking on flat terrain |
| `Isaac-Standing-Flat-Atom-v0` | Standing specialist policy |
| `Isaac-Velocity-Rough-Atom-v0` | Walking on rough terrain |

---

## Load Weights from a Previous Run

Find existing run IDs:
```bash
ls atom_isaaclab/logs/rsl_rl/atom_flat/
# e.g. 2026-03-10_22-54-02
```

Load weights from a previous checkpoint and continue training:
```bash
cd /home/atoms/Documents/Robots/atom_isaaclab && conda run -n env_isaaclab bash -c "MPLBACKEND=Agg /home/atoms/IsaacLab/isaaclab.sh -p scripts/train.py --task Isaac-Velocity-Flat-Atom-v0 --num_envs 4096 --headless --resume --load_run 2026-03-10_22-54-02"
```

**`--resume` is required** — without it, `--load_run` is silently ignored and training starts from scratch. The iteration counter continues from the loaded checkpoint (cosmetic TensorBoard issue — use TensorBoard's "relative time" X-axis to read per-phase curves cleanly).

---

## Play / Visualize

**Must** use `conda activate` (not `conda run`) and **must** run from `atom_isaaclab/`:

```bash
cd /home/atoms/Documents/Robots/atom_isaaclab
conda activate env_isaaclab
MPLBACKEND=Agg /home/atoms/IsaacLab/isaaclab.sh -p scripts/play.py --task Isaac-Velocity-Flat-Atom-Play-v0 --num_envs 50 --load_run 2026-03-10_22-54-02
```

- Play tasks use the `*-Play-v0` variant (fixed camera, longer episodes, fewer envs).
- Log path resolves relative to CWD — if you're in the wrong directory, the run won't be found.

---

## Monitor

GPU usage:
```bash
watch -n 1 nvidia-smi
# or
nvitop
```

CPU usage (confirm CPU bottleneck):
```bash
htop
```

**Expected behavior**: GPU util ~65%, power ~34% TDP, VRAM ~4–5 GB at 4096 envs. The bottleneck is the CPU-side PhysX data pipeline, not VRAM. Increasing env count beyond 6144 has diminishing returns.

---

## After the Run

Update `Training/training_log.md` with:
- Run ID (timestamp)
- Task and env count
- Final metrics: `mean_reward`, `time_out`, `track_vel_x_exp`
- Qualitative observations (gait quality, issues noticed)
- Config changes from the previous run
