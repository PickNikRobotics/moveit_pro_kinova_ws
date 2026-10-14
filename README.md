# moveit_pro_kinova_ws

This is a [MoveIt Pro](https://picknik.ai/pro) robot workspace for Kinova Gen3 7DoF arms.
The `main` branch targets MoveIt Pro 10.x; for MoveIt Pro 9.4, use the [`v9.4`](#branches) branch.

Refer to the [Kinova Gen3 Hardware Setup Guide](https://docs.picknik.ai/hardware_guides/robot_arms/kinova_hardware_setup_guide/) for installation.

## Included configurations

The `main` branch ships a boilerplate Kinova Gen3 7DoF arm with the arm-integrated Vision Module wrist camera and no gripper.
The three configurations form an inheritance chain (per [robot_and_objective_inheritance](https://docs.picknik.ai/how_to/configuration_tutorials/robot_and_objective_inheritance/)):

```
kinova_gen3_mock  →  kinova_gen3_sim  →  kinova_gen3_hw
```

They share one URDF, `kinova_gen3_mock/description/picknik_kinova_gen3.xacro`, and differ in its `hardware_interface` urdf_param, which selects the arm's `<ros2_control>` hardware: `mock`, `mujoco`, or `physical`.

- `kinova_gen3_mock` — bare arm on `ros2_control` mock hardware (`hardware_interface: "mock"`).
  Owns the shared URDF, SRDF, MoveIt configuration, `ros2_control` manifest, driver launch files, and Objectives.
- `kinova_gen3_sim` — the arm simulated in MuJoCo (`hardware_interface: "mujoco"`), mounted on the floor as in the URDF.
  Inherits from `kinova_gen3_mock` and adds only the MuJoCo scene in `description/mujoco/`.
- `kinova_gen3_hw` — real Kinova Kortex hardware (`hardware_interface: "physical"`).
  Inherits from `kinova_gen3_sim` and overrides only `additional_driver_launch_file`, `robot_ip`, `hardware_interface`, `fake_sensor_commands`, the startup controller list (to activate `fault_controller`), and `joint_limits` (which caps every joint at 1.0 rad/s rather than the datasheet maximum).
  Set `robot_ip` for your robot before running.
- `kinova_pstop_manager` — helper node for Kortex protective-stop events, started by `kinova_gen3_mock`'s `launch/robot_drivers_to_persist.launch.py`, which only `kinova_gen3_hw` selects as its `additional_driver_launch_file`.

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

`main` targets MoveIt Pro 10.x. Earlier releases live on `v<major>.<minor>` branches:

| Branch | MoveIt Pro | Base image |
| --- | --- | --- |
| `main` | 10.x | `picknikciuser/moveit-pro`, Jazzy |
| `v9.4` | 9.4 | `picknikciuser/moveit-studio`, Humble |

To check out an earlier release:

```bash
git clone -b v9.4 --recurse-submodules https://github.com/PickNikRobotics/moveit_pro_kinova_ws.git
```

The `picknik_*` branches are public examples of complete systems built on this boilerplate, with grippers, cameras, and Objectives that `main` does not carry.
Check one out if you want to build that full system and are willing to fetch its extra dependencies.
They stay on the MoveIt Pro release they were built for and are not migrated when `main` moves to a new major:

- `picknik_006_gen3` (MoveIt Pro 9.x) — the PickNik office arm: Gen3 7DoF + Robotiq 2F-85 on the internal bus + wrist-mounted RealSense D415.
- `picknik_006_gen3-quest-teleop` (MoveIt Pro 9.x) — the above plus Meta Quest teleoperation over an ADB reverse tunnel and a Stereolabs ZED 2i scene camera.

## Known gaps

- **MuJoCo collides against convex hulls of the arm links.** `kinova_gen3_sim` reuses the URDF's collision meshes from `kortex_description`, which are not convex: their volume is 28–47% of their convex hull's, except `base_link` at 89%.
  MuJoCo replaces each with its convex hull, so contacts in the elbow and wrist bends happen early, and the simulation is coarser than MoveIt's collision checking.
  A convex decomposition of each link, used only by the MJCF, would fix this.
- **No force-torque sensor.** The pinned `ros2_kortex` declares no `<sensor>`, so JTAC and VFC run with `ft_sensor_names` unset.
  They degrade gracefully into a trajectory controller and a Cartesian jog controller, which is what PoseJog and JointJog need, but any Behavior port that depends on force sensing — `absolute_force_torque_threshold` stop-on-contact in particular — is a silent no-op.
  No Objective shipped here sets one; if you add one, it will not protect you.
- **`grasp_link` sits on the wrist flange face** while no gripper is mounted, so a Cartesian goal placed flat on a surface puts `bracelet_link` geometry in contact with it and reports the goal state in collision.
  Mount a gripper (above) rather than inventing a fake offset.
- **Nothing in CI builds or tests this workspace.** `.github/workflows/format.yaml` runs `pre-commit` only, so `colcon build` and `colcon test` — including `test_config_references.py`, which guards exactly the class of bug that reached this boilerplate — run only when someone runs them locally.
