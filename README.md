# moveit_pro_kinova_ws — `picknik_006_gen3` branch

This branch holds the [MoveIt Pro](https://picknik.ai/pro) robot configuration
for the **picknik_006_gen3** asset: a Kinova Gen3 7DoF arm + Robotiq 2F-85
(via the Kinova internal bus) + a wrist-mounted RealSense D415. The
arm-integrated Vision Module is also enabled.

Refer to the [Kinova Gen3 Hardware Setup Guide](https://docs.picknik.ai/hardware_guides/robot_arms/kinova_hardware_setup_guide/)
for installation.

## Asset-ID naming

Per the [robot config naming guidance](https://docs.picknik.ai/how_to/configuration_tutorials/robot_and_objective_inheritance/#robot-naming-conventions),
this branch's packages carry the `picknik_006_gen3_` prefix to mark them as
the configuration of a specific physical robot. New asset-ID branches should
fork `main` (which holds the bare-arm boilerplate `kinova_gen3_{mock,sim,hw}`)
rather than this one.

## Configurations on this branch

```
picknik_006_gen3_mock  →  picknik_006_gen3_sim  →  picknik_006_gen3_hw
```

- `picknik_006_gen3_mock` — trunk. Carries the URDF (arm + Robotiq 2F-85 +
  wrist RealSense + integrated Vision Module), SRDF, MoveIt configuration,
  and `ros2_control` config that the other two inherit. Runs ros2_control
  fake hardware so you can dev-test gripper and motion workflows without a
  physical arm.
- `picknik_006_gen3_sim` — MuJoCo. Inherits from `_mock` and overrides
  `urdf_params` to drop the gripper and wrist RealSense, so the URDF matches
  the bare-arm `description/mujoco/scene.xml` carried over from `main`. Use
  this for motion-only sim validation.
- `picknik_006_gen3_hw` — real hardware. Inherits from `_sim` and overrides
  `simulated`, `robot_ip`, `use_fake_hardware`, the driver launch file, and
  the `controllers_active_at_startup` list. Re-enables the gripper and wrist
  RealSense and uncomments the `cameras.launch.xml` include for the wrist
  RealSense driver. Set `robot_ip` to your robot's IP before running.
- `kinova_pstop_manager` — protective-stop helper, used by `_hw`.

## Relation to `main`

This branch does not merge back into `main`. `main` holds the bare-arm
boilerplate (`kinova_gen3_mock` → `kinova_gen3_sim` → `kinova_gen3_hw`); use
that as the reference when starting a new asset-ID branch.
