# Copyright 2023 PickNik Inc.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the conditions in the repository's
# BSD 3-Clause LICENSE file are met.

import unittest
import yaml
import os
from moveit_studio_utils_py.jsonschema_wrapper import validate_waypoints_yaml


class TestYamlValidation(unittest.TestCase):
    def test_validate_yaml_with_schema(self):
        # Verify if ../waypoints/waypoints.yaml exists
        yaml_file_path = os.path.join(
            os.path.dirname(__file__), "../waypoints/waypoints.yaml"
        )
        self.assertTrue(os.path.exists(yaml_file_path))

        # Convert Waypoints Yaml to JSON
        yaml_file = open(yaml_file_path, "r")
        waypoints_yaml = yaml.full_load(yaml_file)

        self.assertTrue(validate_waypoints_yaml(waypoints_yaml))
