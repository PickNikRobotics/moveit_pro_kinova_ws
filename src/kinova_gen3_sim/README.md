# kinova_gen3_sim

A MoveIt Pro configuration that simulates a Kinova Gen3 7DoF arm in MuJoCo.

It inherits everything from `kinova_gen3_mock` and changes only the arm's `ros2_control` hardware, selecting `hardware_interface: "mujoco"` so the arm runs on `picknik_mujoco_ros/MujocoSystem` against `description/mujoco/scene.xml`.
`kinova_gen3_hw` inherits from this config.

The arm's collision meshes are loaded from `kortex_description` with `package://` URIs, which MoveIt Pro's MuJoCo resolves through ament; MuJoCo uses their convex hulls (see Known gaps in the workspace README).

Third-party material in `description/mujoco/` is listed in [NOTICE](NOTICE).

For detailed documentation see: [MoveIt Pro Documentation](https://docs.picknik.ai/)
