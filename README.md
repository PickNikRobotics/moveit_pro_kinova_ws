# moveit_pro_kinova_ws

This is a [MoveIt Pro](https://picknik.ai/pro) robot workspace for Kinova Gen3 7DoF arms.

Refer to the [Kinova Gen3 Hardware Setup Guide](https://docs.picknik.ai/hardware_guides/robot_arms/kinova_hardware_setup_guide/) for installation.

## Included configurations

- `kinova_gen3_base_config` — shared base configuration inherited by site and sim configs.
- `kinova_gen3_site_config` — hardware site configuration for a Kinova Gen3 7DoF + Robotiq 2F-85/140 gripper.
- `kinova_sim` — MuJoCo-based simulation configuration of the Kinova Gen3 + Robotiq gripper.
- `space_satellite_sim` — Space-themed satellite manipulation demo built on `kinova_sim`.
- `space_satellite_sim_camera_cal` — Camera-calibration variant of `space_satellite_sim`.
- `moveit_studio_kinova_pstop_manager` — Helper node for handling Kinova hardware protective-stop events.
