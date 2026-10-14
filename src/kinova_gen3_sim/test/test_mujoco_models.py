#!/usr/bin/env python3

# Copyright 2026 PickNik Inc.
# All rights reserved.
#
# Unauthorized copying of this code base via any medium is strictly prohibited.
# Proprietary and confidential.

"""Tests for the MuJoCo models kinova_gen3_sim simulates.

MJCF has no conditional include, so the arm with the Robotiq 2F-85
(gen3_7dof_robotiq_2f_85.xml) repeats the arm-only model (gen3_7dof.xml) with
the gripper added. These tests fail when a change to one arm is not made to the
other, check that both scenes compile and start at their keyframe, and check
that the simulated gripper's links sit where the URDF puts them for the joint
positions MuJoCo publishes.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np
import pytest
import xacro
from ament_index_python.packages import get_package_share_directory

MUJOCO_DIR = Path(__file__).resolve().parents[1] / "description" / "mujoco"
GRIPPER_CLASS = "2f85"
GRIPPER_NAME_PREFIX = "robotiq_85_"

# Top-level sections whose entries name gripper bodies, joints, or tendons.
SECTIONS_WITH_GRIPPER_ENTRIES = ("contact", "tendon", "equality", "actuator")


def _is_gripper_element(element: ET.Element) -> bool:
    if GRIPPER_CLASS in (element.get("class"), element.get("childclass")):
        return True
    return any(
        value.startswith(GRIPPER_NAME_PREFIX) or value == "split"
        for value in element.attrib.values()
    ) or any(_is_gripper_element(child) for child in element)


def _remove_gripper(root: ET.Element) -> None:
    """Remove every element the 2F-85 adds to the arm model, in place."""
    for parent in list(root.iter()):
        for child in list(parent):
            if GRIPPER_CLASS in (child.get("class"), child.get("childclass")):
                parent.remove(child)
    for tag in SECTIONS_WITH_GRIPPER_ENTRIES:
        for section in root.findall(tag):
            for entry in list(section):
                if _is_gripper_element(entry):
                    section.remove(entry)
            if len(section) == 0:
                root.remove(section)


def _canonical(root: ET.Element) -> str:
    root.attrib.pop("model", None)
    return ET.canonicalize(ET.tostring(root, encoding="unicode"), strip_text=True)


def test_gripper_model_repeats_the_arm_model_exactly():
    arm = ET.parse(MUJOCO_DIR / "gen3_7dof.xml").getroot()
    arm_with_gripper = ET.parse(MUJOCO_DIR / "gen3_7dof_robotiq_2f_85.xml").getroot()
    _remove_gripper(arm_with_gripper)
    assert _canonical(arm_with_gripper) == _canonical(arm), (
        "gen3_7dof_robotiq_2f_85.xml differs from gen3_7dof.xml outside the "
        "gripper; make the same change to both files"
    )


@pytest.mark.parametrize(
    ("scene", "gripper_actuators"),
    [("scene.xml", 0), ("scene_robotiq_2f_85.xml", 1)],
)
def test_scene_holds_its_default_keyframe(scene, gripper_actuators):
    model = mujoco.MjModel.from_xml_path(str(MUJOCO_DIR / scene))
    data = mujoco.MjData(model)
    assert model.nu == 7 + gripper_actuators
    mujoco.mj_resetDataKeyframe(model, data, model.key("default").id)
    start = np.array([data.joint(f"joint_{i}").qpos[0] for i in range(1, 8)])
    for _ in range(1000):
        mujoco.mj_step(model, data)
    end = np.array([data.joint(f"joint_{i}").qpos[0] for i in range(1, 8)])
    np.testing.assert_allclose(end, start, atol=1e-3)
    assert data.ncon == 0, "the arm touches the table or itself at its keyframe"


def _urdf_joints(urdf: ET.Element) -> dict[str, dict]:
    """URDF joints keyed by child link: parent link, origin transform, type, axis."""
    joints = {}
    for joint in urdf.findall("joint"):
        origin = joint.find("origin")
        xyz = [float(v) for v in origin.get("xyz", "0 0 0").split()]
        roll, pitch, yaw = (float(v) for v in origin.get("rpy", "0 0 0").split())
        transform = np.eye(4)
        transform[:3, :3] = (
            _rotation_about([0, 0, 1], yaw)
            @ _rotation_about([0, 1, 0], pitch)
            @ _rotation_about([1, 0, 0], roll)
        )
        transform[:3, 3] = xyz
        axis = joint.find("axis")
        joints[joint.find("child").get("link")] = {
            "name": joint.get("name"),
            "parent": joint.find("parent").get("link"),
            "origin": transform,
            "type": joint.get("type"),
            "axis": (
                [float(v) for v in axis.get("xyz").split()]
                if axis is not None
                else None
            ),
        }
    return joints


def _rotation_about(axis, angle: float) -> np.ndarray:
    axis = np.asarray(axis, dtype=float) / np.linalg.norm(axis)
    skew = np.array(
        [[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]]
    )
    return np.eye(3) + np.sin(angle) * skew + (1 - np.cos(angle)) * skew @ skew


def _body_pose(data: mujoco.MjData, model: mujoco.MjModel, name: str) -> np.ndarray:
    body = model.body(name).id
    pose = np.eye(4)
    pose[:3, :3] = data.xmat[body].reshape(3, 3)
    pose[:3, 3] = data.xpos[body]
    return pose


@pytest.mark.parametrize("gripper_command", [0.0, 0.4, 0.77])
def test_simulated_gripper_matches_the_urdf(gripper_command):
    urdf_file = (
        Path(get_package_share_directory("kinova_gen3_mock"))
        / "description"
        / "picknik_kinova_gen3.xacro"
    )
    urdf = ET.fromstring(
        xacro.process_file(
            str(urdf_file),
            mappings={"hardware_interface": "mujoco", "gripper": "robotiq_2f_85"},
        ).toxml()
    )
    joints = _urdf_joints(urdf)

    model = mujoco.MjModel.from_xml_path(str(MUJOCO_DIR / "scene_robotiq_2f_85.xml"))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, model.key("default").id)
    data.ctrl[model.actuator("robotiq_85_left_knuckle_joint").id] = gripper_command
    for _ in range(3000):
        mujoco.mj_step(model, data)
    # What MuJoCo publishes on /joint_states, and robot_state_publisher applies to the URDF.
    published = {
        model.joint(i).name: data.qpos[model.jnt_qposadr[i]] for i in range(model.njnt)
    }

    def urdf_pose(link: str) -> np.ndarray:
        if link == "bracelet_link":
            return _body_pose(data, model, "bracelet_link")
        joint = joints[link]
        pose = urdf_pose(joint["parent"]) @ joint["origin"]
        if joint["type"] == "revolute":
            motion = np.eye(4)
            motion[:3, :3] = _rotation_about(joint["axis"], published[joint["name"]])
            pose = pose @ motion
        return pose

    gripper_links = [link for link in joints if link.startswith("robotiq_85_")]
    assert len(gripper_links) == 9
    for link in gripper_links:
        expected = urdf_pose(link)
        simulated = _body_pose(data, model, link)
        position_error = np.linalg.norm(simulated[:3, 3] - expected[:3, 3])
        rotation_error = np.arccos(
            np.clip((np.trace(simulated[:3, :3].T @ expected[:3, :3]) - 1) / 2, -1, 1)
        )
        assert (
            position_error < 1e-3
        ), f"{link} is {position_error:.4f} m from where the URDF puts it"
        assert (
            rotation_error < 0.02
        ), f"{link} is rotated {rotation_error:.4f} rad from the URDF"
