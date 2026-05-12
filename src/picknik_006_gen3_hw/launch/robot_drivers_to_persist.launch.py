# Copyright 2026 PickNik Inc.
# All rights reserved.
#
# Unauthorized copying of this code base via any medium is strictly prohibited.
# Proprietary and confidential.

# Persistent driver-side processes for picknik_006_gen3_hw. Lives in the
# "drivers to persist" lifecycle so it survives agent_bridge restarts —
# matters because the Meta Quest headset holds a TCP socket open against
# ros_tcp_endpoint, and tearing that down would force the user to reconnect
# from the headset.

from launch import LaunchDescription
from launch_ros.actions import Node

from moveit_studio_utils_py.launch_common import empty_gen
from moveit_studio_utils_py.system_config import (
    SystemConfigParser,
)


def generate_launch_description():
    system_config_parser = SystemConfigParser()
    controller_config = system_config_parser.get_ros2_control_config()

    protective_stop_manager_node = Node(
        package="kinova_pstop_manager",
        executable="protective_stop_manager_node",
        name="protective_stop_manager_node",
        output="both",
        parameters=[
            {
                "controllers_default_active": controller_config.get(
                    "controllers_active_at_startup", empty_gen()
                ),
                "controllers_default_not_active": controller_config.get(
                    "controllers_inactive_at_startup", empty_gen()
                ),
            }
        ],
    )

    # Meta Quest TCP endpoint. Edit ROS_IP to your host machine's IP before
    # running. No static_tf_world_to_quest on real hardware; the URDF and
    # the real world frame are real, the sim-only TF hack would be
    # incorrect here.
    ros_tcp_endpoint_node = Node(
        package="ros_tcp_endpoint",
        executable="default_server_endpoint",
        name="ros_tcp_endpoint",
        emulate_tty=True,
        parameters=[
            {"ROS_IP": "192.168.1.34"},
        ],
        output="screen",
    )

    return LaunchDescription([
        protective_stop_manager_node,
        ros_tcp_endpoint_node,
    ])
