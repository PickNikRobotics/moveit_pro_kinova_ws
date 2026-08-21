// Copyright 2022 PickNik Inc.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the conditions in the repository's
// BSD 3-Clause LICENSE file are met.

#include <kinova_pstop_manager/mock_kinova_client.hpp>

int main(int argc, char* argv[])
{
  rclcpp::init(argc, argv);

  auto node = std::make_shared<moveit_studio::kinova_pstop_manager::MockKinovaClient>();

  rclcpp::executors::MultiThreadedExecutor exec;
  exec.add_node(node);
  exec.spin();
  exec.remove_node(node);

  rclcpp::shutdown();
}
