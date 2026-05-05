# TODO

Project backlog items not tied to a specific training phase.

---

## Video & Media

- [ ] Identify best training runs to record play sessions from (one robot, clean forward walk)
- [ ] Record play session videos for Phase 1, 2, 2.5d, 3, and standing policy once trained
- [ ] Convert videos to GIFs showing training progression (one GIF per phase milestone)

## Joint Torque & Load Analysis

Script: `scripts/log_hardware.py` — combined torque + reaction force logger. One command to assess motor and bearing suitability.

- [x] Write combined hardware logging script (torques + joint reaction forces)
- [ ] Run `log_hardware.py` on a converged policy and verify output correctness — check that body-to-joint index mapping is accurate (Isaac Sim may merge fixed-joint bodies, shifting indices by 1). Flag any suspicious mismatches.
- [ ] Record hardware profiles across terrain types: flat ground, stairs up, stairs down, slopes — 1-2 gait cycles each
- [ ] Verify all joints stay within safe envelope: peak < 60 Nm, RMS < 20 Nm continuous rating
- [ ] Analyze per-joint radial/axial/moment loads to determine bearing requirements — especially hip pitch/roll, knee pitch, shoulder pitch/roll, and elbow pitch
- [ ] Evaluate bearing options for high-load joints: SKF 61805 (deep groove, used by K-Scale K-Bot for hips/knees), IKO CRBT505AC1 / THK RU85-UUCC0 (crossed roller, better moment load handling), or cheaper alternatives. Decision depends on load analysis results.

## Sim-to-Real Pipeline

- [ ] Train depth→height-scan estimator CNN (supervised, sim data): RealSense D435i depth image → 187-dim height scan matching the ray-cast grid used in training. Reference: Cheng et al. "Extreme Parkour" approach.
- [ ] Train velocity estimator MLP/RNN (supervised, sim data): proprioceptive history (joint pos/vel, IMU) → base linear velocity estimate. Needed because ground-truth velocity is unavailable on real hardware.
- [ ] Validate full inference pipeline on Orin Nano: policy MLP + velocity estimator + depth→height-scan CNN at 50Hz control rate (height scan CNN can run at 10-30Hz)

## Website / Documentation

- [ ] Plan and build a website documenting the Atom Humanoid development process (training curriculum, design decisions, video evidence)
