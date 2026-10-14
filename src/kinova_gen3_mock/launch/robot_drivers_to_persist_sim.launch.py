# Copyright 2022 PickNik Inc.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the conditions in the repository's
# BSD 3-Clause LICENSE file are met.


from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    # Mock the UR Dashboard Client
    mock_dashboard_client = Node(
        package="kinova_pstop_manager",
        executable="mock_kinova_client_node",
        name="fault_controller",
        output="both",
    )
    # TODO(livanov93): run kinova's protective_stop_manager_node

    return LaunchDescription([mock_dashboard_client])
