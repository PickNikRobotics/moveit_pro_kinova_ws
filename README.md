# moveit_pro_kinova_ws

This is a [MoveIt Pro](https://picknik.ai/pro) robot workspace for Kinova Gen3 7DoF arms.

Refer to the [Kinova Gen3 Hardware Setup Guide](https://docs.picknik.ai/hardware_guides/robot_arms/kinova_hardware_setup_guide/) for installation.

## Included configurations

The `main` branch ships a boilerplate Kinova Gen3 7DoF arm with the arm-integrated Vision Module wrist camera and no gripper.
The two supported configurations form an inheritance chain (per [robot_and_objective_inheritance](https://docs.picknik.ai/how_to/configuration_tutorials/robot_and_objective_inheritance/)):

```
kinova_gen3_mock  →  kinova_gen3_hw
```

- `kinova_gen3_mock` — bare arm on `ros2_control` mock hardware.
  Owns the shared URDF, SRDF, MoveIt configuration, `ros2_control` manifest, persist launch files, and Objectives.
- `kinova_gen3_hw` — real Kinova Kortex hardware.
  Inherits from `kinova_gen3_mock` and overrides only `simulated`, `robot_ip`, `use_fake_hardware`, `fake_sensor_commands`, the startup controller list (to activate `fault_controller`), and `joint_limits` (which caps every joint at 1.0 rad/s rather than the datasheet maximum).
  Set `robot_ip` for your robot before running.
- `kinova_pstop_manager` — helper node for Kortex protective-stop events, started by the inherited `robot_drivers_to_persist.launch.py` whenever `simulated` is `False`.

`kinova_gen3_sim` is present but **not functional** — see [Known gaps](#known-gaps).

## Adding a Robotiq gripper

The boilerplate deliberately mounts no gripper, so `grasp_link` sits at the wrist flange and the `open_gripper` / `close_gripper` / `reactivate_gripper` Objectives have no controller to command.

**Setting the `gripper` urdf_params is not sufficient on its own.**
`gripper`, `gripper_joint_name`, and `use_internal_bus_gripper_comm` are forwarded to `ros2_kortex`'s `load_arm`, which uses them for the Kortex hardware block and adds the gripper joint to `<ros2_control>` — but they add no links and no kinematic joint.
Setting only these yields a model whose `ros2_control` block references a joint the kinematic model does not contain, and a gripper absent from collision checking.

A complete gripper overlay needs four pieces:

1. The urdf_params, so the driver drives the gripper and `ros2_control` exposes its joint:

   ```yaml
   hardware:
     robot_description:
       urdf_params:
         - gripper: "robotiq_2f_85"
         - gripper_joint_name: "robotiq_85_left_knuckle_joint"
         - use_internal_bus_gripper_comm: "true"
   ```

2. A gripper description included from your own URDF xacro, adding the gripper's links and kinematic joint and moving `grasp_link` from the wrist flange to the gripper's tool center point.
   Because `sensor_frames` / `ee_frames` and the SRDF `tip_link` all name `grasp_link`, moving the alias is enough — none of them need editing.
3. A `robotiq_gripper_controller` of type `position_controllers/GripperActionController`, `joint` set to the same `gripper_joint_name`, in your own `ros2_control` manifest and listed under `controllers_active_at_startup`.
4. A gripper group and end-effector in your SRDF — `config/moveit/picknik_kinova_gen3_base.srdf` declares only `manipulator` — plus `disable_collisions` entries for the gripper's links.
   Scope those to genuinely adjacent pairs; do not blanket-disable the gripper against the wrist and bracelet.

The `picknik_006_gen3` branch implements all four; use it as the reference rather than assembling this from scratch.

## Robot credentials and network

`kinova_gen3_mock` ships Kinova's factory-default `username: "admin"` / `password: "admin"` as `urdf_params`, and `kinova_gen3_hw` inherits them.
On the hardware path these are rendered into the `<hardware>` block of the generated URDF and published on `/robot_description`, where every node on the DDS domain and every web UI session can read them. They are also in this repository's git history.

Before putting an arm into service:

- Change the credentials in the arm's own Kortex web interface, and override `username` and `password` in your own configuration package's `urdf_params`.
- Keep the arm on an isolated robot subnet that is not routable from your general network. Anyone who can reach `robot_ip` can log into the Kortex interface and command the arm directly, bypassing MoveIt Pro's joint limits and the protective-stop manager.
- Pin `MOVEIT_DOCKER_TAG` when you build. The `Dockerfile` defaults to the floating `main` tag, so an unpinned rebuild months later gets a different product image under an unchanged robot configuration.

## Branches

Add-ons such as a gripper, an external RealSense, or full demos belong on their own branches that diverge from this boilerplate:

- `picknik_006_gen3` — the PickNik office arm: Gen3 7DoF + Robotiq 2F-85 on the internal bus + wrist-mounted RealSense D415.
- `picknik_006_gen3-quest-teleop` — the above plus Meta Quest teleoperation over an ADB reverse tunnel and a Stereolabs ZED 2i scene camera.

## Known gaps

- **`kinova_gen3_sim` cannot start.** It fails during URDF generation with `Xacro conditional "${use_fake_hardware}" evaluated to "%>> hardware.simulated", which is not a boolean expression`.
  The `%>>` cross-reference syntax its `use_fake_hardware` uses was removed in MoveIt Pro 6.0.0 and nothing implements it any more, so the literal string reaches a xacro conditional. It fails loudly rather than mis-launching.
- **`kinova_gen3_sim` would not run MuJoCo even once that is fixed.** Its `mujoco_model` / `mujoco_keyframe` / `mujoco_viewer` params are declared as xacro args but never consumed, so nothing emits a `<ros2_control>` block with the `picknik_mujoco_ros/MujocoSystem` plugin.
  Wiring it up means suppressing the `<ros2_control>` block that `ros2_kortex`'s `load_arm` macro emits unconditionally — the pinned `main-picknik` SHA has no `include_ros2_control` argument.
- **`kinova_gen3_sim` still carries space-satellite demo content**: landsat and rafti MuJoCo scenes and assets in `description/mujoco/`, AprilTag registration / compliant-grasp / force-torque Objectives in `objectives/`, an unused `config/moveit/` (its `config.yaml` declares no `moveit_params`), and 20 Franka Panda meshes in `meshes/`.
  None of it is loaded by the bare-arm boilerplate, and it belongs on a demo branch rather than on `main`.
- **`fanuc` is checked out as its own submodule** under `src/external_dependencies/`, even though no Kinova config uses it.
  It is a separate entry rather than only a nested one so `catkin_pkg.find_packages` can reach `fanuc_lrmate200id_support`, which `picknik_accessories` declares a rosdep on; see the comment in `.gitmodules`.
- **No force-torque sensor.** The pinned `ros2_kortex` declares no `<sensor>`, so JTAC and VFC run with `ft_sensor_name` unset.
  They degrade gracefully into a trajectory controller and a Cartesian jog controller, which is what PoseJog and JointJog need, but any Behavior port that depends on force sensing — `absolute_force_torque_threshold` stop-on-contact in particular — is a silent no-op.
  No Objective shipped here sets one; if you add one, it will not protect you.
- **`grasp_link` sits on the wrist flange face** while no gripper is mounted, so a Cartesian goal placed flat on a surface puts `bracelet_link` geometry in contact with it and reports the goal state in collision.
  Mount a gripper (above) rather than inventing a fake offset.
- **Nothing in CI builds or tests this workspace.** `.github/workflows/format.yaml` runs `pre-commit` only, so `colcon build` and `colcon test` — including `test_config_references.py`, which guards exactly the class of bug that reached this boilerplate — run only when someone runs them locally.
