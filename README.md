# moveit_pro_kinova_ws

This is a [MoveIt Pro](https://picknik.ai/pro) robot workspace for Kinova Gen3 7DoF arms.

Refer to the [Kinova Gen3 Hardware Setup Guide](https://docs.picknik.ai/hardware_guides/robot_arms/kinova_hardware_setup_guide/) for installation.

## Included configurations

The `main` branch ships a boilerplate Kinova Gen3 7DoF arm with the
arm-integrated Vision Module wrist camera and no gripper. The three
configurations form an inheritance chain (per
[robot_and_objective_inheritance](https://docs.picknik.ai/how_to/configuration_tutorials/robot_and_objective_inheritance/)):

```
kinova_gen3_mock  →  kinova_gen3_sim  →  kinova_gen3_hw
```

- `kinova_gen3_mock` — bare arm with `ros2_control` mock hardware. Owns the
  shared URDF, SRDF, MoveIt configuration, ros2_control config, and Objectives.
- `kinova_gen3_sim` — MuJoCo-simulated arm. Inherits everything from
  `kinova_gen3_mock`; only adds the MuJoCo scene and simulator launch file.
- `kinova_gen3_hw` — real Kinova Kortex hardware. Inherits from
  `kinova_gen3_sim`; only overrides `simulated`, `robot_ip`, and the hardware
  driver launch file. Set `robot_ip` for your robot before running.
- `kinova_pstop_manager` — helper node for Kortex protective-stop events,
  loaded by the `_hw` driver launch.

Add-ons such as a Robotiq gripper, an external RealSense, or full demos belong
on their own branches that diverge from this boilerplate. See:

- `space-satellite` — full satellite manipulation demo with Robotiq, external
  RealSense, AprilTag tracking, and Fuse state estimation.
