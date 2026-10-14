# kinova_gen3_sim

A MoveIt Pro configuration that simulates a Kinova Gen3 7DoF arm in MuJoCo.

It inherits everything from `kinova_gen3_mock` and changes only the arm's `ros2_control` hardware, selecting `hardware_interface: "mujoco"` so the arm runs on `picknik_mujoco_ros/MujocoSystem` against `description/mujoco/scene.xml`, or `description/mujoco/scene_robotiq_2f_85.xml` when the `gripper` urdf_param selects the Robotiq 2F-85.
`kinova_gen3_hw` inherits from this config.

`gen3_7dof_robotiq_2f_85.xml` repeats `gen3_7dof.xml` with the gripper added, because MJCF cannot include the gripper conditionally.
Make any change to the arm in both files; `test/test_mujoco_models.py` fails when they differ outside the gripper.
Both scenes include the table and floor from `environment.xml`.

Third-party material in `description/mujoco/` is listed in [NOTICE](NOTICE).

For detailed documentation see: [MoveIt Pro Documentation](https://docs.picknik.ai/)
