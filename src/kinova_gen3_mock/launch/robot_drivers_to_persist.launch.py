# Copyright 2022 PickNik Inc.
# All rights reserved.
#
# Unauthorized copying of this code base via any medium is strictly prohibited.
# Proprietary and confidential.


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
                # How long the fault controller may not have published yet before
                # the node reports a non-recoverable fault. This launch file starts
                # before the controller manager, so some grace is always needed.
                # Raise it if your controller manager starts more slowly; do not set
                # it to zero, which the node rejects.
                "startup_grace_period_sec": 30.0,
            }
        ],
    )

    nodes_to_launch = [
        protective_stop_manager_node,
    ]

    return LaunchDescription(nodes_to_launch)
