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
            }
        ],
    )

    # Meta Quest TCP endpoint. Lives in the persist launch so the headset's
    # TCP socket survives agent_bridge restarts. Edit ROS_IP to your host
    # machine's IP before running.
    ros_tcp_endpoint_node = Node(
        package="ros_tcp_endpoint",
        executable="default_server_endpoint",
        name="ros_tcp_endpoint",
        emulate_tty=True,
        parameters=[
            {"ROS_IP": "10.6.1.94"},
        ],
        output="screen",
    )

    # Debug-only static TF linking the disjoint quest TF root into the robot tree
    # at the world frame. The numerical values are wrong — quest and world have
    # no real geometric relationship — but the link satisfies the canTransform()
    # check inside marker_utils::transformPoseToBaseFrame() so VisualizePose calls
    # against quest-frame poses (controller markers in v11) can render.
    #
    # No control path uses this transform: the v11 kinematic math composes the
    # controller delta in quest and applies it to the EE in world directly,
    # bypassing TF entirely. The lie is contained to RViz markers.
    #
    # Before shipping v11, remove the quest-frame VisualizePose calls from the
    # objective and delete this node — neither will be needed.
    static_tf_world_to_quest = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_transform_world_to_quest",
        output="log",
        arguments=[
            "0", "0", "0",  # x y z (identity translation; the link is geometrically meaningless)
            "0", "0", "0",  # yaw pitch roll
            "world", "quest",
        ],
    )

    nodes_to_launch = [
        protective_stop_manager_node,
        ros_tcp_endpoint_node,
        static_tf_world_to_quest,
    ]

    return LaunchDescription(nodes_to_launch)
