#!/usr/bin/env python3

# Copyright 2026 PickNik Inc.
# All rights reserved.
#
# Unauthorized copying of this code base via any medium is strictly prohibited.
# Proprietary and confidential.

"""Tests that every file a robot config references actually exists.

MoveIt Pro resolves a config's {package, path} pairs with
os.path.join(get_package_share_directory(package), path) and no fallback
search, so a pair naming a file that does not exist raises at Agent bringup
rather than at build time. Inheritance makes this easy to get wrong: a child
config that overrides only the `package` half of an inherited pair silently
points at a path that exists in the parent but not in the child.

These tests walk the based_on_package chain and assert each resolved pair
resolves, and that every controller named in controllers_*_at_startup has both a
type declaration and a parameter block in the resolved ros2_control manifest.

Resolution uses the real `merge` from moveit_studio_utils_py.system_config rather
than a local reimplementation. That matters: `merge` treats a list of single-key
dicts (how urdf_params is written) as a per-key merge that appends unmatched
entries, but replaces a list of strings (how controllers_*_at_startup is written)
wholesale. A hand-rolled deep merge gets one or both of those wrong, and would
make these tests agree with each other while disagreeing with the Agent.
"""

import re
from pathlib import Path

import pytest
import yaml
from moveit_studio_utils_py.system_config import merge

SRC_DIR = Path(__file__).resolve().parents[2]

# Controllers that need no top-level parameter block in the manifest.
CONTROLLERS_WITHOUT_PARAMETER_BLOCK = frozenset(
    {"joint_state_broadcaster", "fault_controller"}
)

# Controllers declared in the shared manifest but activated only by the hardware
# config, so they are legitimately absent from the other configs' startup lists.
# test_hardware_config_activates_the_fault_controller pins the other side of this.
HARDWARE_ONLY_CONTROLLERS = frozenset({"fault_controller"})

# Content directories that are knowingly unreachable, mapped to the directories
# expected to be flagged. Compared for equality, not membership, so an entry that
# stops being true fails the test instead of quietly masking a regression. See
# the Known gaps section of the workspace README.
KNOWN_UNREACHABLE_CONTENT = {
    # kinova_gen3_sim is a partly-renamed copy of the old space-satellite demo
    # config. Its Objectives and waypoints belong to that demo, not to the
    # bare-arm boilerplate, and the config deliberately does not load them.
    "kinova_gen3_sim": frozenset({"objectives", "waypoints"}),
}


def _discover_packages(*, submodules: bool) -> dict[str, Path]:
    """Map package name to directory, for either first-party or submodule packages."""
    packages = {}
    for manifest in SRC_DIR.rglob("package.xml"):
        if ("external_dependencies" in manifest.parts) != submodules:
            continue
        match = re.search(
            r"<name>\s*([^<\s]+)\s*</name>", manifest.read_text(encoding="utf-8")
        )
        if match:
            packages[match.group(1)] = manifest.parent
    return packages


# First-party packages only. This map drives the per-package parametrization, so it
# deliberately excludes submodules.
PACKAGES = _discover_packages(submodules=False)

# Packages vendored under src/external_dependencies. A config may legitimately
# reference one — a gripper description from ros2_kortex, for instance — and those
# references are checkable because the package is in this tree. Keeping them out of
# PACKAGES but resolvable here stops them falling through the "supplied by the base
# image" escape hatch unchecked.
SUBMODULE_PACKAGES = _discover_packages(submodules=True)
CONFIG_PACKAGES = sorted(
    name
    for name, path in PACKAGES.items()
    if (path / "config" / "config.yaml").is_file()
)


def _inheritance_chain(package: str) -> list[dict]:
    """Return configs from `package` up to the root, most-derived first."""
    chain = []
    seen = set()
    current = package
    while current:
        assert current not in seen, f"based_on_package cycle through {current}"
        seen.add(current)
        assert current in PACKAGES, f"{current} names a package not in this workspace"
        config = yaml.safe_load(
            (PACKAGES[current] / "config" / "config.yaml").read_text(encoding="utf-8")
        )
        chain.append(config)
        current = config.get("based_on_package")
    return chain


def _resolve(package: str) -> dict:
    """Merge a config's inheritance chain root-first, child values winning."""
    resolved: dict = {}
    for config in reversed(_inheritance_chain(package)):
        resolved = merge(resolved, config)
    return resolved


def _file_locations(node, trail: str = ""):
    """Yield (trail, package, path) for every node holding a package/path pair."""
    if isinstance(node, dict):
        if "package" in node and "path" in node:
            yield trail, node["package"], node["path"]
        if "package_name" in node and "relative_path" in node:
            yield trail, node["package_name"], node["relative_path"]
        for key, value in node.items():
            yield from _file_locations(value, f"{trail}.{key}" if trail else key)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _file_locations(value, f"{trail}[{index}]")


def test_workspace_has_config_packages() -> None:
    """Guard against the discovery helpers silently finding nothing to test."""
    assert CONFIG_PACKAGES, f"no config packages discovered under {SRC_DIR}"


@pytest.mark.parametrize("config_package", CONFIG_PACKAGES)
def test_referenced_files_exist(config_package: str) -> None:
    """Every {package, path} pair in the resolved config points at a real file."""
    misses = []
    for trail, package, relative_path in _file_locations(_resolve(config_package)):
        package_dir = PACKAGES.get(package) or SUBMODULE_PACKAGES.get(package)
        if package_dir is None:
            # Genuinely not in this tree: supplied by the MoveIt Pro base image. This
            # skip is only correct for those — a submodule package resolves above.
            continue
        if not (package_dir / relative_path).exists():
            misses.append(f"{trail} -> {package}/{relative_path}")
    assert not misses, f"{config_package} references missing files: " + ", ".join(
        misses
    )


@pytest.mark.parametrize("config_package", CONFIG_PACKAGES)
def test_no_duplicate_urdf_params(config_package: str) -> None:
    """No urdf_params key survives resolution twice.

    `merge` matches an inherited list entry with `if item.get(key)`, a truthiness
    test rather than a key-presence test. A parent entry whose value is falsy —
    an empty string, 0, False — therefore never matches, so a child's override is
    appended alongside it instead of replacing it. Which value reaches the xacro
    then depends only on list order, via process_mappings_dict's dict update.
    """
    params = (
        _resolve(config_package)
        .get("hardware", {})
        .get("robot_description", {})
        .get("urdf_params", [])
    )
    keys = [key for entry in params for key in entry]
    duplicated = sorted({key for key in keys if keys.count(key) > 1})
    assert not duplicated, (
        f"{config_package} resolves these urdf_params more than once, so which "
        f"value reaches the xacro depends on list order: {duplicated}. A falsy "
        "value in a parent config is the usual cause."
    )


@pytest.mark.parametrize("config_package", CONFIG_PACKAGES)
def test_declared_controllers_are_used(config_package: str) -> None:
    """Every controller declared in the manifest appears in a startup list.

    The inverse of test_startup_controllers_are_configured. A controller declared
    under controller_manager but named in neither startup list is never loaded, so
    its parameters are never validated — which is how a twist_controller survived
    in this manifest with a `joint: tcp` that only the Kortex hardware interface
    exports, and that therefore could never load under the mock hardware this
    shared manifest is also used by.
    """
    resolved = _resolve(config_package)
    ros2_control = resolved.get("ros2_control", {})
    manifest_location = ros2_control.get("config", {})
    manifest_path = PACKAGES[manifest_location["package"]] / manifest_location["path"]
    declared = (
        yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        .get("controller_manager", {})
        .get("ros__parameters", {})
    )

    named = set(ros2_control.get("controllers_active_at_startup") or []) | set(
        ros2_control.get("controllers_inactive_at_startup") or []
    )
    controller_names = {
        name
        for name, entry in declared.items()
        if isinstance(entry, dict) and "type" in entry
    }
    unused = controller_names - named - HARDWARE_ONLY_CONTROLLERS
    assert not unused, (
        f"{config_package} declares controllers that no startup list names, so they "
        f"never load and their parameters are never validated: {sorted(unused)}"
    )


def test_hardware_config_activates_the_fault_controller() -> None:
    """kinova_gen3_hw activates fault_controller, or it boots permanently faulted.

    protective_stop_manager_node, started by the inherited persist launch whenever
    `simulated` is False, watchdogs /fault_controller/internal_fault and reports a
    NONRECOVERABLE_FAULT once it has seen a message and then goes stale. On mock
    that topic comes from mock_kinova_client_node; on hardware only the real
    fault_controller publishes it. This is the invariant the hardware config hinges
    on, and test_declared_controllers_are_used deliberately exempts
    fault_controller, so without this nothing would catch its removal.
    """
    active = (
        _resolve("kinova_gen3_hw")
        .get("ros2_control", {})
        .get("controllers_active_at_startup", [])
    )
    assert "fault_controller" in active, (
        "kinova_gen3_hw must activate fault_controller; resolved "
        f"controllers_active_at_startup is {active}"
    )


@pytest.mark.parametrize("config_package", CONFIG_PACKAGES)
def test_agent_bridge_launch_file_is_present(config_package: str) -> None:
    """Every config package ships a non-empty launch/agent_bridge.launch.xml.

    This file is found by name rather than through a config.yaml key — the compose
    stack runs `ros2 launch ${MOVEIT_CONFIG_PACKAGE} agent_bridge.launch.xml` — so
    none of the reference checks above cover it. A missing or empty one is the same
    failure that a 0-byte bringup.launch.py produced in this workspace.
    """
    launch_file = PACKAGES[config_package] / "launch" / "agent_bridge.launch.xml"
    assert launch_file.is_file(), f"{config_package} is missing {launch_file}"
    assert launch_file.stat().st_size > 0, f"{config_package}: {launch_file} is empty"


@pytest.mark.parametrize("config_package", CONFIG_PACKAGES)
def test_no_unreachable_content_directories(config_package: str) -> None:
    """Objectives and waypoints a config ships are actually loaded by that config.

    A package can ship an objectives/ or waypoints/ directory that its resolved
    config never points into — because the parent's entry was inherited rather
    than overridden. Nothing errors; the content is just silently ignored, which
    is worse than a missing file because the config appears to work while
    running the parent's Objectives and waypoints instead.
    """
    package_dir = PACKAGES[config_package]
    referenced = {
        (PACKAGES[package] / relative_path).resolve()
        for _, package, relative_path in _file_locations(_resolve(config_package))
        if package in PACKAGES
    }

    unreachable = set()
    for directory in ("objectives", "waypoints"):
        candidate = package_dir / directory
        if not candidate.is_dir():
            continue
        # Reachable if the directory itself, or anything inside it, is referenced.
        if not any(
            path == candidate.resolve() or candidate.resolve() in path.parents
            for path in referenced
        ):
            unreachable.add(directory)

    expected = KNOWN_UNREACHABLE_CONTENT.get(config_package, frozenset())
    assert unreachable == expected, (
        f"{config_package} unreachable content directories changed: "
        f"expected {sorted(expected) or 'none'}, found {sorted(unreachable) or 'none'}. "
        "Either point the config at them, delete them, or update "
        "KNOWN_UNREACHABLE_CONTENT if this is a deliberate gap."
    )


@pytest.mark.parametrize("config_package", CONFIG_PACKAGES)
def test_startup_controllers_are_configured(config_package: str) -> None:
    """Controllers listed at startup have a type and a parameter block."""
    resolved = _resolve(config_package)
    ros2_control = resolved.get("ros2_control", {})
    manifest_location = ros2_control.get("config", {})
    manifest_package = manifest_location.get("package")
    assert manifest_package in PACKAGES, (
        f"{config_package} resolves ros2_control.config to "
        f"{manifest_package!r}, which is not a package in this workspace"
    )

    manifest_path = PACKAGES[manifest_package] / manifest_location["path"]
    assert (
        manifest_path.is_file()
    ), f"{config_package}: missing manifest {manifest_path}"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    declared = manifest.get("controller_manager", {}).get("ros__parameters", {})

    named = list(ros2_control.get("controllers_active_at_startup") or []) + list(
        ros2_control.get("controllers_inactive_at_startup") or []
    )
    assert named, f"{config_package} names no startup controllers"

    problems = []
    for controller in named:
        entry = declared.get(controller)
        if not isinstance(entry, dict) or "type" not in entry:
            problems.append(f"{controller}: no type declared in controller_manager")
        elif (
            controller not in manifest
            and controller not in CONTROLLERS_WITHOUT_PARAMETER_BLOCK
        ):
            problems.append(f"{controller}: no top-level parameter block")
    assert not problems, f"{config_package} controller issues: " + ", ".join(problems)
