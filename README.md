# moveit_pro_kinova_ws

This is a [MoveIt Pro v9.4.1](https://picknik.ai/pro) robot workspace for Kinova Gen3 7DoF arms.

Refer to the [Kinova Gen3 Hardware Setup Guide](https://docs.picknik.ai/hardware_guides/robot_arms/kinova_hardware_setup_guide/) for installation.

## Included configurations

The `main` branch ships a boilerplate Kinova Gen3 7DoF arm with the
arm-integrated Vision Module wrist camera and the Robotiq 85 gripper. The three
configurations form an inheritance chain (per
[robot_and_objective_inheritance](https://docs.picknik.ai/how_to/configuration_tutorials/robot_and_objective_inheritance/)):

```
kinova_gen3_mock  →  kinova_gen3_sim  →  kinova_gen3_hw
```

- `kinova_gen3_mock` — arm with `ros2_control` mock hardware. Owns the
  shared URDF, SRDF, MoveIt configuration and some objectives.
- `kinova_gen3_sim` — MuJoCo-simulated arm. Inherits everything from
  `kinova_gen3_mock`; adds the MuJoCo scene and additional objectives.
- `kinova_gen3_hw` — real Kinova Kortex hardware. Inherits from
  `kinova_gen3_sim`; only overrides `simulated`, `robot_ip`, and the hardware
  driver launch file. Set `robot_ip` for your robot before running.
- `kinova_pstop_manager` — helper node for Kortex protective-stop events,
  loaded by the `_hw` driver launch.
