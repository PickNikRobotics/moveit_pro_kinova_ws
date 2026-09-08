// Copyright 2022 PickNik Inc.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the conditions in the repository's
// BSD 3-Clause LICENSE file are met.

// Implementing this feature as a node that provides a service that calls other ROS services is not ideal.  Please see
// the README for a discussion of alternatives.

#pragma once

#include <controller_manager_msgs/srv/switch_controller.hpp>
#include <example_interfaces/msg/bool.hpp>
#include <example_interfaces/srv/trigger.hpp>
#include <moveit_studio_agent_msgs/msg/fault_status.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_srvs/srv/trigger.hpp>

namespace moveit_studio::kinova_pstop_manager
{
class ProtectiveStopManager : public rclcpp::Node
{
public:
  ProtectiveStopManager(const rclcpp::NodeOptions& options = rclcpp::NodeOptions());

private:
  using SwitchController = controller_manager_msgs::srv::SwitchController;

  /**
   * @brief This is the callback for the "recover_from_protective_stop" service.  It unlocks the protective stop, stops
   * the program currently running on the arm, and re-sends the control program.
   *
   * @param request An empty request.
   * @param response Indicates whether the protective stop was successfully released.
   */
  void recoverFromProtectiveStop(const std_srvs::srv::Trigger::Request::SharedPtr request,
                                 std_srvs::srv::Trigger::Response::SharedPtr response);

  /**
   * @brief Helper function to check whether a service is unavailable.  If the service is unavailable, this function
   * also sets displays the appropriate error message and sets the Response.
   *
   * @param client The client for the service we are checking.
   * @param response The response object, which will indicate success or failure.
   * @return true The service is unavailable.
   * @return false The service is available.
   */
  bool indicateUnavailableService(rclcpp::ClientBase::SharedPtr client,
                                  std_srvs::srv::Trigger::Response::SharedPtr response = nullptr);

  /**
   * @brief Callback function that publishes the current fault status of the robot.
   *
   */
  void publishFaultStatus();

  /**
   * @brief Determines whether the Kinova robot is in fault.
   *
   * @return true The robot is in fault.
   * @return false The robot is not in fault.
   * @return std::nullopt An error occurred when attempting to call the service.
   */
  bool isRobotInFault();

  std::vector<std::string> all_controller_names;
  std::vector<std::string> active_controller_names;

  rclcpp::CallbackGroup::SharedPtr reentrant_callback_group_;
  rclcpp::Service<std_srvs::srv::Trigger>::SharedPtr recovery_service_;
  rclcpp::Client<SwitchController>::SharedPtr switch_controller_client_;

  // generic moveit studio fault publisher
  rclcpp::Publisher<moveit_studio_agent_msgs::msg::FaultStatus>::SharedPtr fault_status_publisher_;
  rclcpp::TimerBase::SharedPtr fault_status_timer_;
  std::atomic<bool> in_fault_;

  // Whether the fault controller has published at least once. Until it has, the
  // staleness watchdog in publishFaultStatus() has no baseline to compare against,
  // and it is suppressed for at most kStartupGracePeriodSec.
  std::atomic<bool> fault_status_received_;

  // How long after startup the fault controller may not have published yet, from
  // the startup_grace_period_sec parameter.
  double startup_grace_period_sec_;

  // Steady clock for the startup grace period only. Deliberately not the node
  // clock: a simulated clock that never advances would leave the grace period
  // permanently unexpired.
  rclcpp::Clock steady_clock_;
  rclcpp::Time start_time_;

  // Stamped by the fault topic subscription with the node clock, so the staleness
  // comparison in publishFaultStatus() must use the node clock too.
  //
  // Written only by that subscription and read only by the fault status timer. Both
  // run in this node's default mutually exclusive callback group, so they never
  // overlap even under a multi-threaded executor and no synchronization is
  // required. The neighbouring atomics are belt-and-braces on the same invariant;
  // do not read their presence as evidence that this one races.
  rclcpp::Time last_fault_status_update_;

  // connect to the fault_controller that is communication pipe to/from the driver
  rclcpp::Subscription<example_interfaces::msg::Bool>::SharedPtr fault_ctrl_sub_;
  rclcpp::Client<example_interfaces::srv::Trigger>::SharedPtr fault_reset_client_;
};
}  // namespace moveit_studio::kinova_pstop_manager
