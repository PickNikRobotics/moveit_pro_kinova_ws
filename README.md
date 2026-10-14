# moveit_pro_kinova_ws

This is a [MoveIt Pro](https://picknik.ai/pro) robot workspace for Kinova Gen3 7DoF arms.
The `main` branch targets MoveIt Pro 10.x; for MoveIt Pro 9.4, use the [`v9.4`](#branches) branch.

Refer to the [Kinova Gen3 Hardware Setup Guide](https://docs.picknik.ai/hardware_guides/robot_arms/kinova_hardware_setup_guide/) for installation.

## Included configurations

The `main` branch ships a boilerplate Kinova Gen3 7DoF arm with the arm-integrated Vision Module wrist camera.
It mounts no gripper by default; the Robotiq 2F-85, which Kinova sells as a Gen3 option, can be [switched on](#robotiq-2f-85-gripper).
The three configurations form an inheritance chain (per [robot_and_objective_inheritance](https://docs.picknik.ai/how_to/configuration_tutorials/robot_and_objective_inheritance/)):

```
kinova_gen3_mock  →  kinova_gen3_sim  →  kinova_gen3_hw
```

They share one URDF, `kinova_gen3_mock/description/picknik_kinova_gen3.xacro`, and differ in its `hardware_interface` urdf_param, which selects the arm's `<ros2_control>` hardware: `mock`, `mujoco`, or `physical`.

- `kinova_gen3_mock` — bare arm on `ros2_control` mock hardware (`hardware_interface: "mock"`).
  Owns the shared URDF, SRDF, MoveIt configuration, `ros2_control` manifest, driver launch files, and Objectives.
- `kinova_gen3_sim` — the arm simulated in MuJoCo (`hardware_interface: "mujoco"`), on a table matching the URDF's.
  Inherits from `kinova_gen3_mock` and adds only the MuJoCo scene in `description/mujoco/`.
- `kinova_gen3_hw` — real Kinova Kortex hardware (`hardware_interface: "physical"`).
  Inherits from `kinova_gen3_sim` and overrides only `additional_driver_launch_file`, `robot_ip`, `hardware_interface`, `fake_sensor_commands`, the startup controller list (to activate `fault_controller`), and `joint_limits` (which caps every joint at 1.0 rad/s rather than the datasheet maximum).
  Set `robot_ip` for your robot before running.
- `kinova_pstop_manager` — helper node for Kortex protective-stop events, started by `kinova_gen3_mock`'s `launch/robot_drivers_to_persist.launch.py`, which only `kinova_gen3_hw` selects as its `additional_driver_launch_file`.

## Robotiq 2F-85 gripper

The configurations can mount a Robotiq 2F-85 on the wrist, wired through the Kinova internal bus as Kinova sells it.
It is off by default, so `grasp_link` sits at the wrist flange and the `open_gripper` / `close_gripper` Objectives have no controller to command.

To switch it on, edit `kinova_gen3_mock/config/config.yaml`, or your own copy of it:

1. Set the `gripper` urdf_param to `robotiq_2f_85`:

   ```yaml
   hardware:
     robot_description:
       urdf_params:
         - gripper: "robotiq_2f_85"
   ```

2. Add `robotiq_gripper_controller` to `controllers_active_at_startup`.
   `kinova_gen3_hw` replaces that list with its own, so add it in `kinova_gen3_hw/config/config.yaml` too.

The `gripper` urdf_param does the rest, in every configuration:

- The URDF adds `robotiq_description`'s 2F-85 links and moves `grasp_link` between the fingertips, 0.15 m out from the gripper base.
  Every config file that names the tool point uses `grasp_link`, so none of them change.
- The SRDF (`config/moveit/picknik_kinova_gen3.srdf.xacro`, which MoveIt Pro processes with the same urdf_params) adds the `gripper` group, `open` and `close` states, the end effector, the mimic joints as passive joints, and collision exclusions for the gripper against itself and the bracelet it is bolted to.
- The gripper joint's hardware follows `hardware_interface`: mock hardware for `mock`, the MuJoCo model `kinova_gen3_sim` names in `mujoco_model_robotiq_2f_85` for `mujoco`, and the Kortex driver over the internal bus for `physical`.

`robotiq_description` comes from the `ros2_robotiq_gripper` submodule, along with the Robotiq serial driver and `serial`, which this boilerplate does not use.

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
  The Robotiq 2F-85's linkage meshes, from MuJoCo Menagerie, are likewise 41–57% of their hulls.
  A convex decomposition of each link, used only by the MJCF, would fix this.
- **`fanuc` is checked out as its own submodule** under `src/external_dependencies/`, even though no Kinova config uses it.
  It is a separate entry rather than only a nested one so `catkin_pkg.find_packages` can reach `fanuc_lrmate200id_support`, which `picknik_accessories` declares a rosdep on; see the comment in `.gitmodules`.
- **No force-torque sensor.** The pinned `ros2_kortex` declares no `<sensor>`, so JTAC and VFC run with `ft_sensor_names` unset.
  They degrade gracefully into a trajectory controller and a Cartesian jog controller, which is what PoseJog and JointJog need, but any Behavior port that depends on force sensing — `absolute_force_torque_threshold` stop-on-contact in particular — is a silent no-op.
  No Objective shipped here sets one; if you add one, it will not protect you.
- **`grasp_link` sits on the wrist flange face** while no gripper is mounted, so a Cartesian goal placed flat on a surface puts `bracelet_link` geometry in contact with it and reports the goal state in collision.
  Switch on the [Robotiq 2F-85](#robotiq-2f-85-gripper) rather than inventing a fake offset.
- **The `reactivate_gripper` Objective calls `/robotiq_activation_controller/reactivate_gripper`**, a controller for the Robotiq serial driver that no configuration starts, so it fails even with the 2F-85 switched on.
- **Nothing in CI builds or tests this workspace.** `.github/workflows/format.yaml` runs `pre-commit` only, so `colcon build` and `colcon test` — including `test_config_references.py`, which guards exactly the class of bug that reached this boilerplate — run only when someone runs them locally.
